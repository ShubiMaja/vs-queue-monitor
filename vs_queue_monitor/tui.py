"""Terminal UI (Textual). Uses the same ``QueueMonitorApp`` engine as the GUI (withdrawn Tk root)."""

from __future__ import annotations

import sys
import types
from typing import Any, Optional

import tkinter as tk

from . import APP_DISPLAY_NAME, VERSION
from .core import DEFAULT_PATH, save_config
from .gui import QueueMonitorApp


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

    def _patch_messagebox_for_tui() -> None:
        import tkinter.messagebox as mb

        _orig = mb.askyesno

        def _askyesno(title: str, message: str, **kwargs: Any) -> bool:
            if "New queue detected" in (title or ""):
                return True
            return _orig(title, message, **kwargs)

        mb.askyesno = _askyesno  # type: ignore[assignment]

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
        """Textual front-end; drives ``QueueMonitorApp`` via ``update()`` (withdrawn root)."""

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
            self._gui: Optional[QueueMonitorApp] = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Static("", id="metrics")
            yield RichLog(id="log", highlight=True, markup=True)
            with Horizontal(id="pathrow"):
                yield Static("Logs folder: ", id="path_lbl")
                yield Input(placeholder="Path (same as GUI folder picker)", id="path_input")
            yield Footer()

        def on_mount(self) -> None:
            _patch_messagebox_for_tui()
            self._gui = QueueMonitorApp(initial_path=self._initial_path, auto_start=False)
            self._gui.withdraw()
            log = self.query_one("#log", RichLog)
            g = self._gui

            def write_history_tui(self2: QueueMonitorApp, message: str) -> None:
                QueueMonitorApp.write_history(self2, message)
                try:
                    log.write_line(message)
                except Exception:
                    pass

            g.write_history = types.MethodType(write_history_tui, g)  # type: ignore[method-assign]

            self.query_one("#path_input", Input).value = g.source_path_var.get()
            self.set_interval(0.02, self._pump_tk)
            self.set_interval(0.2, self._refresh_metrics)
            if self._auto_start:
                self.call_later(self._start_gui_monitor)

        def _start_gui_monitor(self) -> None:
            g = self._gui
            if g is not None:
                g.start_monitoring()

        def _pump_tk(self) -> None:
            g = self._gui
            if g is None:
                return
            try:
                g.update()
            except tk.TclError:
                self.exit()

        def _refresh_metrics(self) -> None:
            g = self._gui
            if g is None:
                return
            try:
                pos = g.position_var.get()
                st = g.status_var.get()
                rate = g.queue_rate_var.get()
                glo = g.global_rate_var.get()
                elapsed = g.elapsed_var.get()
                rem = g.predicted_remaining_var.get()
                path = g.resolved_path_var.get() or "—"
                n_roll = g._rolling_window_points_int()  # type: ignore[attr-defined]
                hdr = f"RATE (Rolling {n_roll})"
                pts = list(g.graph_points)
                spark = _sparkline(pts)
                prog = 0.0
                if g._queue_progress is not None:
                    try:
                        prog = float(g._queue_progress["value"])
                    except (tk.TclError, TypeError, ValueError):
                        prog = 0.0
                text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (same engine as GUI)\n\n"
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
            g = self._gui
            if g is None:
                return
            raw = event.value.strip()
            g.source_path_var.set(raw or DEFAULT_PATH)
            try:
                save_config(g.get_config_snapshot())
            except Exception:
                pass
            if g.running:
                g.stop_monitoring()
            g.after(100, g.start_monitoring)
            self._write_log(f"Path set to: {raw or DEFAULT_PATH}")

        def _write_log(self, line: str) -> None:
            try:
                self.query_one("#log", RichLog).write_line(line)
            except Exception:
                pass

        def action_toggle_monitor(self) -> None:
            g = self._gui
            if g is not None:
                g.toggle_monitoring()

        def action_open_settings(self) -> None:
            g = self._gui
            if g is not None:
                g.open_settings()

        def action_refresh_view(self) -> None:
            self._refresh_metrics()

        def action_quit(self) -> None:
            g = self._gui
            if g is not None:
                try:
                    g.on_close()
                except Exception:
                    try:
                        g.destroy()
                    except Exception:
                        pass
            self.exit()

        def on_unmount(self) -> None:
            g = self._gui
            if g is not None:
                try:
                    if g.winfo_exists():
                        g.on_close()
                except Exception:
                    pass

    app = VSQueueTui(initial_path=initial_path, auto_start=auto_start)
    app.run()
    return 0
