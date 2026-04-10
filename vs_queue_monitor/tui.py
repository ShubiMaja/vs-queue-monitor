"""Terminal UI (Textual). Uses :class:`~vs_queue_monitor.engine.QueueMonitorEngine` only (no Tk)."""

from __future__ import annotations

import math
import sys
from typing import Optional

from . import APP_DISPLAY_NAME, VERSION
from .core import DEFAULT_PATH, GRAPH_LOG_GAMMA, save_config
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

    def _queue_ascii_graph(
        points: list[tuple[float, int]],
        *,
        width: int = 60,
        height: int = 10,
        log_scale: bool = True,
    ) -> str:
        """Htop-style mini chart (filled bars, multi-line)."""
        if len(points) < 1:
            return "—"

        # Step function (GUI draws steps).
        step_vals: list[int] = []
        prev: Optional[int] = None
        for _t, p in points:
            v = int(p)
            if prev is None:
                step_vals.append(v)
                prev = v
                continue
            if v != prev:
                step_vals.append(prev)
            step_vals.append(v)
            prev = v

        if not step_vals:
            return "—"

        # Resample to fixed width from the end (most recent).
        if len(step_vals) <= width:
            ys = step_vals
        else:
            start = len(step_vals) - width
            ys = step_vals[start:]

        lo, hi = min(ys), max(ys)
        if lo == hi:
            # A single flat run: show a solid bottom bar.
            w = max(10, int(width))
            dot = "·"
            inner_h = max(3, int(height))
            inner = [" " * w for _ in range(inner_h - 1)] + [dot * w]
            return "\n".join(["┌" + ("─" * w) + "┐", *("│" + row + "│" for row in inner), "└" + ("─" * w) + "┘"])

        def frac_for(v: int) -> float:
            vv = max(lo, min(hi, int(v)))
            if not log_scale:
                # 0 at lo (best), 1 at hi (worst)
                return (float(vv) - float(lo)) / (float(hi) - float(lo))
            lvmin = math.log(float(lo) + 1.0)
            lvmax = math.log(float(hi) + 1.0)
            lv = math.log(float(vv) + 1.0)
            if lvmax <= lvmin:
                frac = 0.0
            else:
                # 0 at lo (best), 1 at hi (worst)
                frac = (lv - lvmin) / (lvmax - lvmin)
            frac = max(0.0, min(1.0, frac))
            return frac**GRAPH_LOG_GAMMA

        # Canvas: dot plot (one dot per column), htop-style history.
        h = max(3, int(height))
        w = max(10, int(width))
        canvas: list[list[str]] = [[" " for _ in range(w)] for _ in range(h)]
        dot = "·"

        n = min(w, len(ys))
        offset = len(ys) - n
        for x in range(n):
            v = ys[offset + x]
            frac = frac_for(v)
            row = int(round(frac * float(h - 1)))
            row = max(0, min(h - 1, row))
            canvas[h - 1 - row][x] = dot

        inner_lines = ["".join(r) for r in canvas]
        # Add borders so Textual doesn't trim trailing spaces; makes “full width” visible.
        top = "┌" + ("─" * w) + "┐"
        bot = "└" + ("─" * w) + "┘"
        boxed = [top, *("│" + row + "│" for row in inner_lines), bot]
        return "\n".join(boxed)

    class VSQueueTui(App[None]):
        """Textual front-end; drives :class:`QueueMonitorEngine` without Tk."""

        CSS = """
    Screen { align: left top; }
    #metrics { height: auto; min-height: 12; width: 100%; }
    #log { height: 1fr; border: solid $primary; width: 100%; }
    #pathrow { height: auto; margin-top: 1; width: 100%; }
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
                # Stretch graph to the actual widget width (not just terminal width).
                # Leave a small margin to avoid wrap jitter.
                term_w = int(getattr(self, "size").width) if hasattr(self, "size") else 80
                try:
                    metrics_w = int(self.query_one("#metrics", Static).size.width)
                except Exception:
                    metrics_w = term_w
                # Account for box borders (left+right / top+bottom).
                graph_w = max(30, metrics_w - 4)
                graph_h = 10

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
                graph = _queue_ascii_graph(
                    pts,
                    width=graph_w,
                    height=graph_h,
                    log_scale=bool(eng.graph_log_scale_var.get()),
                )
                prog = float(getattr(eng, "_queue_progress_value", 0.0))
                text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (headless engine, no Tk)\n\n"
                    f"Position: [cyan]{pos}[/]    Status: [green]{st}[/]\n"
                    f"{hdr}: [yellow]{rate}[/]    Global: [yellow]{glo}[/]\n"
                    f"Elapsed: {elapsed}    Est. remaining: {rem}    Progress: {prog:.0f}%\n"
                    f"Log: {path}\n"
                    f"Queue graph:\n{graph}\n"
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
