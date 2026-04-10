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

    def _queue_braille_line(
        points: list[tuple[float, int]],
        *,
        width: int = 80,
        log_scale: bool = True,
    ) -> str:
        """Single-line graph using Unicode braille (2×4 dots per cell)."""
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

        # Braille cells are 2 columns wide. We'll plot one dot per column.
        cols = max(10, int(width))
        x_cols = cols * 2

        # Resample to fixed width from the end (most recent).
        if len(step_vals) <= x_cols:
            ys = step_vals
        else:
            ys = step_vals[-x_cols:]

        lo, hi = min(ys), max(ys)
        if lo == hi:
            # Flat line: show a baseline of low dots across.
            return "⠤" * cols

        def frac_for(v: int) -> float:
            vv = max(lo, min(hi, int(v)))
            if not log_scale:
                return (float(vv) - float(lo)) / (float(hi) - float(lo))
            lvmin = math.log(float(lo) + 1.0)
            lvmax = math.log(float(hi) + 1.0)
            lv = math.log(float(vv) + 1.0)
            if lvmax <= lvmin:
                frac = 0.0
            else:
                frac = (lv - lvmin) / (lvmax - lvmin)
            frac = max(0.0, min(1.0, frac))
            return frac**GRAPH_LOG_GAMMA

        # Build braille cells.
        # Braille dot mapping for 2×4:
        # left column:  1,2,3,7  (top→bottom)
        # right column: 4,5,6,8  (top→bottom)
        DOTS = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
        cells = [0 for _ in range(cols)]

        # Pad left with first value so we always draw full width.
        if len(ys) < x_cols:
            ys = [ys[0]] * (x_cols - len(ys)) + ys

        for x in range(x_cols):
            v = ys[x]
            frac = frac_for(v)  # 0..1 (low..high)
            # Map to 4 vertical levels. Higher queue position => higher dot.
            level = int(round(frac * 3.0))
            level = max(0, min(3, level))
            row = 3 - level  # 0 top .. 3 bottom
            cell_idx = x // 2
            col_idx = x % 2
            cells[cell_idx] |= DOTS[col_idx][row]

        out = []
        for mask in cells:
            out.append(chr(0x2800 + mask) if mask else " ")
        return "".join(out).rstrip() or "—"

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

        def on_resize(self) -> None:
            # Force an immediate redraw on terminal resize (GUI-like behavior).
            try:
                self._refresh_metrics()
            except Exception:
                pass

        def _refresh_metrics(self) -> None:
            eng = self._engine
            if eng is None:
                return
            try:
                # Stretch graph to the actual widget width (not just terminal width).
                term_w = int(getattr(self, "size").width) if hasattr(self, "size") else 80
                try:
                    metrics = self.query_one("#metrics", Static)
                    # Prefer content region (excludes padding/borders) when available.
                    if hasattr(metrics, "content_region"):
                        metrics_w = int(metrics.content_region.size.width)  # type: ignore[attr-defined]
                    else:
                        metrics_w = int(metrics.size.width)
                except Exception:
                    metrics_w = term_w
                # Leave a little room for the label; braille line itself is full width.
                graph_w = max(30, metrics_w - 2)

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
                graph = _queue_braille_line(
                    pts,
                    width=graph_w,
                    log_scale=bool(eng.graph_log_scale_var.get()),
                )
                prog = float(getattr(eng, "_queue_progress_value", 0.0))
                text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (headless engine, no Tk)\n\n"
                    f"Position: [cyan]{pos}[/]    Status: [green]{st}[/]\n"
                    f"{hdr}: [yellow]{rate}[/]    Global: [yellow]{glo}[/]\n"
                    f"Elapsed: {elapsed}    Est. remaining: {rem}    Progress: {prog:.0f}%\n"
                    f"Log: {path}\n"
                    f"Queue graph: {graph}\n"
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
