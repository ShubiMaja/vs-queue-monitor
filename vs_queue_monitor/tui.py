"""Terminal UI (Textual). Uses :class:`~vs_queue_monitor.engine.QueueMonitorEngine` only (no Tk)."""

from __future__ import annotations

import math
import sys
from bisect import bisect_right
from datetime import datetime
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

    def _queue_braille_graph(
        points: list[tuple[float, int]],
        *,
        width: int = 80,
        height_lines: int = 3,
        log_scale: bool = True,
        show_labels: bool = True,
    ) -> str:
        """Multi-line graph using stacked Unicode braille (2×4 dots per cell per line)."""
        # Braille cells are 2 columns wide. We'll plot one dot per column.
        cols = max(10, int(width))
        x_cols = cols * 2
        lines_n = max(1, int(height_lines))
        y_levels = lines_n * 4
        if len(points) < 1:
            return "\n".join(["—"] * lines_n)

        # Time-based resampling (matches GUI x-axis semantics).
        # points are (epoch_seconds, position) in chronological order.
        times = [float(t) for t, _p in points]
        vals = [int(p) for _t, p in points]
        if not times:
            return "\n".join(["—"] * lines_n)
        t0 = times[0]
        t1 = times[-1]
        if t1 <= t0:
            # Degenerate: no span; fall back to constant.
            return "\n".join(["⠤" * cols for _ in range(lines_n)])

        # Determine overall range from samples.
        lo, hi = min(vals), max(vals)
        if lo == hi:
            # Flat line: show a baseline of low dots across.
            return "\n".join(["⠤" * cols for _ in range(lines_n)])

        # Optional labels (like GUI axis hints). Reserve some width for them.
        label_w = 0
        if show_labels:
            label_w = max(len(str(hi)), len(str(lo))) + 1  # trailing space
            cols = max(10, cols - label_w)
            x_cols = cols * 2

        def frac_for(v: int) -> float:
            """Return a 0..1 value where 1 maps to the *top* (worst/highest queue position).

            Matches the GUI y-mapping:
            - linear: gui_frac = (hi - v)/(hi - lo) then invert to make hi -> 1
            - log:    gui_frac = (log(hi+1) - log(v+1)) / (...) then gamma, then invert
            """
            vv = max(lo, min(hi, int(v)))
            denom = float(hi - lo)
            if denom <= 0.0:
                return 0.0
            if not log_scale:
                gui_frac = (float(hi) - float(vv)) / denom  # 0 at hi, 1 at lo
                gui_frac = max(0.0, min(1.0, gui_frac))
                return 1.0 - gui_frac

            lvmin = math.log(float(lo) + 1.0)
            lvmax = math.log(float(hi) + 1.0)
            lv = math.log(float(vv) + 1.0)
            if lvmax <= lvmin:
                gui_frac = 0.0
            else:
                gui_frac = (lvmax - lv) / (lvmax - lvmin)  # 0 at hi, 1 at lo
            gui_frac = max(0.0, min(1.0, gui_frac))
            gui_frac = gui_frac**GRAPH_LOG_GAMMA
            return 1.0 - gui_frac

        # Build braille cells.
        # Braille dot mapping for 2×4:
        # left column:  1,2,3,7  (top→bottom)
        # right column: 4,5,6,8  (top→bottom)
        DOTS = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
        cells_by_line: list[list[int]] = [[0 for _ in range(cols)] for _ in range(lines_n)]

        # Per-column time bins. To avoid “missing” rapid step changes when the terminal is narrow,
        # we draw a small envelope in each bin: min/max + end-of-bin value.
        dt = (t1 - t0) / float(x_cols)
        if dt <= 0.0:
            dt = 1.0

        # Starting value at t0 (step function).
        idx = 0
        v_curr = vals[0]
        while idx + 1 < len(times) and times[idx + 1] <= t0 + 1e-9:
            idx += 1
            v_curr = vals[idx]

        for x in range(x_cols):
            a = t0 + x * dt
            b = a + dt

            v_min = v_curr
            v_max = v_curr
            v_end = v_curr

            # Consume samples in (a, b]; step changes occur at sample times.
            while idx + 1 < len(times) and times[idx + 1] <= b + 1e-9:
                idx += 1
                v_curr = vals[idx]
                v_end = v_curr
                if v_curr < v_min:
                    v_min = v_curr
                if v_curr > v_max:
                    v_max = v_curr

            # Map values to 4 levels and set dots for the range + end marker.
            def level_for(v: int) -> int:
                lv = int(round(frac_for(v) * float(y_levels - 1)))
                return max(0, min(y_levels - 1, lv))

            l0 = level_for(v_min)
            l1 = level_for(v_max)
            le = level_for(v_end)
            lo_lv, hi_lv = sorted((l0, l1))

            cell_idx = x // 2
            col_idx = x % 2

            def set_level(lv: int) -> None:
                # lv: 0..y_levels-1 where 0 is bottom, y_levels-1 is top
                y_from_top = (y_levels - 1) - lv
                line_idx = y_from_top // 4
                row_in_cell = y_from_top % 4  # 0 top .. 3 bottom
                if 0 <= line_idx < lines_n:
                    cells_by_line[line_idx][cell_idx] |= DOTS[col_idx][row_in_cell]

            for lv in range(lo_lv, hi_lv + 1):
                set_level(lv)
            # Ensure end-of-bin is visible (may be inside range; harmless).
            set_level(le)

        out_lines: list[str] = []
        for line_idx, line_cells in enumerate(cells_by_line):
            out = []
            for mask in line_cells:
                out.append(chr(0x2800 + mask) if mask else " ")
            body = ("".join(out).rstrip() or "—")
            if show_labels and label_w > 0:
                if line_idx == 0:
                    prefix = f"{hi:>{label_w-1}} "
                elif line_idx == lines_n - 1:
                    prefix = f"{lo:>{label_w-1}} "
                else:
                    prefix = " " * label_w
                out_lines.append(prefix + body)
            else:
                out_lines.append(body)

        if show_labels:
            try:
                left = datetime.fromtimestamp(t0).strftime("%H:%M:%S")
                right = datetime.fromtimestamp(t1).strftime("%H:%M:%S")
                total_w = (label_w + cols) if label_w > 0 else cols
                if total_w < 20:
                    total_w = 20
                mid_spaces = max(1, total_w - len(left) - len(right))
                out_lines.append(left + (" " * mid_spaces) + right)
            except Exception:
                pass

        return "\n".join(out_lines)

    class VSQueueTui(App[None]):
        """Textual front-end; drives :class:`QueueMonitorEngine` without Tk."""

        CSS = """
    Screen { align: left top; }
    #metrics { height: auto; min-height: 7; width: 100%; }
    #graph { height: 1fr; width: 100%; }
    #log { height: 10; width: 100%; }
    #pathrow { height: auto; margin-top: 1; width: 100%; }
    """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("space", "toggle_monitor", "Play/Stop"),
            Binding("o", "open_settings", "Settings"),
            Binding("r", "refresh_view", "Refresh"),
            Binding("h", "toggle_history", "History"),
        ]

        def __init__(self, initial_path: str = "", auto_start: bool = True) -> None:
            super().__init__()
            self._initial_path = initial_path
            self._auto_start = auto_start
            self._engine: Optional[QueueMonitorEngine] = None
            self._history_collapsed: bool = True

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Static("", id="metrics")
            yield Static("", id="graph")
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
            self._apply_history_collapsed()

        def _apply_history_collapsed(self) -> None:
            # When collapsed, hide the log panel so the graph expands into that space.
            try:
                log = self.query_one("#log", RichLog)
                log.display = not self._history_collapsed
            except Exception:
                pass

        def action_toggle_history(self) -> None:
            self._history_collapsed = not self._history_collapsed
            self._apply_history_collapsed()
            try:
                self._refresh_metrics()
            except Exception:
                pass

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
                prog = float(getattr(eng, "_queue_progress_value", 0.0))
                metrics_text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (headless engine, no Tk)\n\n"
                    f"Position: [cyan]{pos}[/]    Status: [green]{st}[/]\n"
                    f"{hdr}: [yellow]{rate}[/]    Global: [yellow]{glo}[/]\n"
                    f"Elapsed: {elapsed}    Est. remaining: {rem}    Progress: {prog:.0f}%\n"
                    f"Log: {path}\n"
                )
                self.query_one("#metrics", Static).update(metrics_text)

                # Graph fills the middle section; resize-aware.
                term_w = int(getattr(self, "size").width) if hasattr(self, "size") else 80
                try:
                    gw = self.query_one("#graph", Static)
                    if hasattr(gw, "content_region"):
                        graph_w = int(gw.content_region.size.width)  # type: ignore[attr-defined]
                        graph_h = int(gw.content_region.size.height)  # type: ignore[attr-defined]
                    else:
                        graph_w = int(gw.size.width)
                        graph_h = int(gw.size.height)
                except Exception:
                    graph_w = term_w
                    graph_h = 6
                graph_w = max(30, graph_w - 2)
                # Fill the middle pane vertically; keep at least 3 lines so it's readable.
                height_lines = max(3, graph_h)
                graph = _queue_braille_graph(
                    pts,
                    width=graph_w,
                    height_lines=height_lines,
                    log_scale=bool(eng.graph_log_scale_var.get()),
                    show_labels=True,
                )
                self.query_one("#graph", Static).update(graph)
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
