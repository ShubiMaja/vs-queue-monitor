"""Terminal UI (Textual). Uses :class:`~vs_queue_monitor.engine.QueueMonitorEngine` only (no Tk)."""

from __future__ import annotations

import sys
from typing import Optional

from . import APP_DISPLAY_NAME, VERSION
from .core import DEFAULT_PATH, save_config
from .engine import QueueMonitorEngine
from .hooks import HeadlessMonitorHooks


def run_tui(initial_path: str = "", auto_start: bool = True) -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal
        from textual.widgets import Footer, Header, Input, RichLog, Static
    except ImportError:
        print(
            "Terminal UI requires Textual. Install: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    def _sparkline(points: list[tuple[float, int]], width: int = 56) -> str:
        if len(points) < 2:
            return "—"
        ys = [p for _t, p in points]
        if len(ys) > width:
            ys = ys[-width:]
        lo, hi = min(ys), max(ys)
        blocks = "▁▂▃▄▅▆▇█"
        if hi == lo:
            return "█" * len(ys)
        out: list[str] = []
        for y in ys:
            frac = (float(y) - float(lo)) / (float(hi) - float(lo))
            out.append(blocks[min(7, max(0, int(frac * 8.0)))])
        return "".join(out)

    class VSQueueTui(App[None]):
        """Textual front-end; drives :class:`QueueMonitorEngine` without Tk."""

        CSS = """
    Screen { align: left middle; }
    #metrics { height: auto; min-height: 12; }
    #log { height: 1fr; border: solid $primary; }
    #pathrow { height: auto; margin-top: 1; }
    """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("space", "toggle_monitor", "Play/Stop"),
            Binding("o", "open_settings", "Settings"),
            Binding("r", "refresh_view", "Refresh"),
        ]

        def __init__(self, initial_path: str = "", auto_start: bool = True) -> None:
            super().__init__()
            self._initial_path = initial_path
            self._auto_start = auto_start
            self._engine: Optional[QueueMonitorEngine] = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Static("", id="metrics")
            yield RichLog(id="log", highlight=True, markup=True)
            with Horizontal(id="pathrow"):
                yield Static("Logs folder: ", id="path_lbl")
                yield Input(placeholder="Path (same as GUI folder picker)", id="path_input")
            yield Footer()

        def _headless_append_history(self, message: str) -> None:
            try:
                self.query_one("#log", RichLog).write_line(message)
            except Exception:
                pass

        def on_mount(self) -> None:
            hooks = HeadlessMonitorHooks(None)
            hooks.textual_app = self
            eng = QueueMonitorEngine(hooks, initial_path=self._initial_path, auto_start=False)
            eng._headless_append_history = self._headless_append_history  # type: ignore[attr-defined]
            hooks.attach_engine(eng)
            self._engine = eng

            self.query_one("#path_input", Input).value = eng.source_path_var.get()
            self.set_interval(0.2, self._refresh_metrics)
            if self._auto_start:
                self.call_later(eng.start_monitoring)

        def _refresh_metrics(self) -> None:
            eng = self._engine
            if eng is None:
                return
            try:
                pos = eng.position_var.get()
                st = eng.status_var.get()
                rate = eng.queue_rate_var.get()
                glo = eng.global_rate_var.get()
                elapsed = eng.elapsed_var.get()
                rem = eng.predicted_remaining_var.get()
                path = eng.resolved_path_var.get() or "—"
                n_roll = eng._rolling_window_points_int()
                hdr = f"RATE (Rolling {n_roll})"
                pts = list(eng.graph_points)
                spark = _sparkline(pts)
                prog = float(getattr(eng, "_queue_progress_value", 0.0))
                text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (headless engine, no Tk)\n\n"
                    f"Position: [cyan]{pos}[/]    Status: [green]{st}[/]\n"
                    f"{hdr}: [yellow]{rate}[/]    Global: [yellow]{glo}[/]\n"
                    f"Elapsed: {elapsed}    Est. remaining: {rem}    Progress: {prog:.0f}%\n"
                    f"Log: {path}\n"
                    f"Queue shape: {spark}\n"
                )
                self.query_one("#metrics", Static).update(text)
            except Exception as exc:
                self.query_one("#metrics", Static).update(f"[red]Display error: {exc}[/]")

        def on_input_submitted(self, event: Input.Submitted) -> None:
            if event.input.id != "path_input":
                return
            eng = self._engine
            if eng is None:
                return
            raw = event.value.strip()
            eng.source_path_var.set(raw or DEFAULT_PATH)
            try:
                save_config(eng.get_config_snapshot())
            except Exception:
                pass
            if eng.running:
                eng.stop_monitoring()
            self.set_timer(0.1, eng.start_monitoring)
            self._write_log(f"Path set to: {raw or DEFAULT_PATH}")

        def _write_log(self, line: str) -> None:
            try:
                self.query_one("#log", RichLog).write_line(line)
            except Exception:
                pass

        def action_toggle_monitor(self) -> None:
            eng = self._engine
            if eng is not None:
                eng.toggle_monitoring()

        def action_open_settings(self) -> None:
            eng = self._engine
            if eng is not None:
                eng._hooks.open_settings_ui()

        def action_refresh_view(self) -> None:
            self._refresh_metrics()

        def action_quit(self) -> None:
            eng = self._engine
            if eng is not None:
                try:
                    eng.stop_monitoring()
                    eng.stop_timer()
                except Exception:
                    pass
            self.exit()

        def on_unmount(self) -> None:
            eng = self._engine
            if eng is not None:
                try:
                    eng.stop_monitoring()
                    eng.stop_timer()
                except Exception:
                    pass

    app = VSQueueTui(initial_path=initial_path, auto_start=auto_start)
    app.run()
    return 0
