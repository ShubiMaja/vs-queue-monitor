"""Terminal UI (Textual). Uses :class:`~vs_queue_monitor.engine.QueueMonitorEngine` only (no Tk)."""

from __future__ import annotations

import math
import sys
from datetime import datetime
from typing import Optional

from . import APP_DISPLAY_NAME, VERSION
from .core import (
    DEFAULT_PATH,
    GRAPH_LOG_GAMMA,
    UI_ACCENT_ELAPSED,
    UI_ACCENT_POSITION,
    UI_ACCENT_PROGRESS,
    UI_ACCENT_RATE,
    UI_ACCENT_REMAINING,
    UI_ACCENT_STATUS,
    UI_ACCENT_WARNINGS,
    UI_GRAPH_AXIS,
    UI_GRAPH_GRID,
    UI_GRAPH_HOVER_CURSOR,
    UI_GRAPH_LINE,
    UI_GRAPH_TEXT,
    UI_SUMMARY_VALUE,
    UI_TEXT_MUTED,
    parse_alert_thresholds,
    save_config,
)
from .engine import QueueMonitorEngine
from .hooks import HeadlessMonitorHooks


def _gui_graph_y_tick_values(vmin: int, vmax: int) -> list[int]:
    """Same tick set as ``gui.redraw_graph`` (reverse-sorted)."""
    tick_step = 5
    tick_vals: list[int] = []
    start = vmin // tick_step * tick_step
    end = (vmax + tick_step - 1) // tick_step * tick_step
    for val in range(start, end + 1, tick_step):
        if vmin <= val <= vmax:
            if val == 0 and vmin > 0:
                continue
            tick_vals.append(val)
    if vmin <= 5 <= vmax:
        tick_vals.extend([1, 2, 3, 4, 5])
    tick_vals.extend([vmin, vmax])
    return sorted(set(tick_vals), reverse=True)


def _gui_graph_time_ticks(t0: float, t1: float, plot_cols: int) -> tuple[list[float], str]:
    """Major x tick times + label format; dedup matches ``gui.redraw_graph`` pixel rule (≈2 columns)."""
    span = t1 - t0
    if span <= 0:
        span = 1.0
    candidates = [5, 10, 15, 30, 60, 5 * 60, 10 * 60, 15 * 60, 30 * 60, 60 * 60, 2 * 60 * 60, 6 * 60 * 60]
    target_ticks = 6
    interval = candidates[-1]
    for c in candidates:
        if span / c <= target_ticks:
            interval = c
            break
    fmt = "%H:%M:%S" if interval < 60 * 60 else "%H:%M"
    first_tick = math.ceil(t0 / interval) * interval
    last_tick = math.floor(t1 / interval) * interval
    tick_times: list[float] = []
    t = first_tick
    while t <= last_tick + 1e-06:
        tick_times.append(t)
        t += interval
    if not tick_times or tick_times[0] - t0 > interval * 0.4:
        tick_times.insert(0, t0)
    if tick_times[-1] < t1 - interval * 0.4:
        tick_times.append(t1)
    plot_w = float(max(1, plot_cols))
    _dedup: list[float] = []
    for tv in sorted(tick_times):
        xv = (tv - t0) / span * plot_w
        if not _dedup or abs(xv - (_dedup[-1] - t0) / span * plot_w) > 2.0:
            _dedup.append(tv)
    return _dedup, fmt


def _tui_warnings_kpi_markup(engine: QueueMonitorEngine) -> str:
    """Threshold list with muted “passed” styling (mirrors ``_refresh_warnings_kpi``)."""
    try:
        thresholds = parse_alert_thresholds(engine.alert_thresholds_var.get())
    except ValueError:
        return f"[{UI_TEXT_MUTED}]—[/]"
    if not thresholds:
        return f"[{UI_TEXT_MUTED}]—[/]"
    pos = engine.last_position
    if pos is None and engine.current_point is not None:
        pos = engine.current_point[1]
    fired = engine._alert_thresholds_fired
    parts: list[str] = []
    for i, t in enumerate(thresholds):
        if i > 0:
            parts.append(f"[{UI_TEXT_MUTED}] · [/]")
        passed = pos is not None and pos <= t or t in fired
        col = UI_TEXT_MUTED if passed else UI_SUMMARY_VALUE
        parts.append(f"[{col}]{t}[/]")
    return "".join(parts)


def run_tui(initial_path: str = "", auto_start: bool = True) -> int:
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, Vertical
        from textual.screen import ModalScreen
        from textual.widgets import Button, Input, RichLog, Static
        try:
            from textual.widgets import Rule  # type: ignore
        except Exception:  # pragma: no cover
            Rule = None  # type: ignore[misc,assignment]
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
        cursor_time: Optional[float] = None,
        line_color: str = UI_GRAPH_LINE,
        grid_color: str = UI_GRAPH_GRID,
        label_color: str = UI_GRAPH_TEXT,
    ) -> str:
        """Multi-line graph using stacked Unicode braille (2×4 dots per cell per line)."""
        # Braille cells are 2 columns wide. We'll plot one dot per column.
        cols = max(10, int(width))
        x_cols = cols * 2
        # When labels are enabled we append 2 extra lines (ticks + time labels).
        # Reserve space so those lines are visible within the widget.
        label_extra_lines = 2 if show_labels else 0
        lines_n = max(1, int(height_lines) - label_extra_lines)
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

        # GUI-aligned grid: horizontal lines only at *interior* Y ticks (often none for narrow ranges).
        tick_vals = _gui_graph_y_tick_values(lo, hi)
        h_grid_lines: set[int] = set()
        for idx, val in enumerate(tick_vals):
            if 0 < idx < len(tick_vals) - 1:
                vv = max(lo, min(hi, int(val)))
                lv = int(round(frac_for(vv) * float(y_levels - 1)))
                y_from_top = (y_levels - 1) - lv
                line_idx_g = y_from_top // 4
                h_grid_lines.add(max(0, min(lines_n - 1, line_idx_g)))

        span_t = float(t1 - t0)
        if span_t <= 0:
            span_t = 1.0
        tick_times, fmt = _gui_graph_time_ticks(t0, t1, cols)
        v_grid_cols: set[int] = set()
        for idx, tv in enumerate(tick_times):
            if 0 < idx < len(tick_times) - 1:
                xf = (tv - t0) / span_t
                ci = int(min(cols - 1, max(0, round(xf * float(max(1, cols - 1))))))
                v_grid_cols.add(ci)

        # Build braille cells.
        # Braille dot mapping for 2×4:
        # left column:  1,2,3,7  (top→bottom)
        # right column: 4,5,6,8  (top→bottom)
        DOTS = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
        cells_by_line: list[list[int]] = [[0 for _ in range(cols)] for _ in range(lines_n)]
        grid_by_line: list[list[int]] = [[0 for _ in range(cols)] for _ in range(lines_n)]

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

        # Grid: interior horizontal (see ``h_grid_lines``) + interior vertical major ticks (``v_grid_cols``).
        GRID_DOT_MASK = 0x02
        for line_idx in range(lines_n):
            want_h = line_idx in h_grid_lines
            for i in range(cols):
                want_v = i in v_grid_cols
                if want_h or want_v:
                    grid_by_line[line_idx][i] |= GRID_DOT_MASK

        # Cursor (GUI hover analogue): vertical line at selected time.
        cursor_col: Optional[int] = None
        if cursor_time is not None:
            try:
                xf = (float(cursor_time) - t0) / float(t1 - t0)
                xf = max(0.0, min(1.0, xf))
                cursor_col = int(round(xf * float(max(1, cols - 1))))
                cursor_col = max(0, min(cols - 1, cursor_col))
            except Exception:
                cursor_col = None

        grid_tag_open = f"[{grid_color}]"
        grid_tag_close = f"[/{grid_color}]"
        line_tag_open = f"[{line_color}]"
        line_tag_close = f"[/{line_color}]"
        label_tag_open = f"[{label_color}]"
        label_tag_close = f"[/{label_color}]"
        cursor_tag_open = f"[{UI_GRAPH_HOVER_CURSOR}]"
        cursor_tag_close = f"[/{UI_GRAPH_HOVER_CURSOR}]"

        out_lines: list[str] = []
        for line_idx, line_cells in enumerate(cells_by_line):
            out: list[str] = []
            for i, mask in enumerate(line_cells):
                is_cursor = cursor_col is not None and i == cursor_col
                if mask:
                    ch = f"{line_tag_open}{chr(0x2800 + mask)}{line_tag_close}"
                else:
                    gmask = grid_by_line[line_idx][i]
                    if gmask:
                        ch = f"{grid_tag_open}{chr(0x2800 + gmask)}{grid_tag_close}"
                    else:
                        ch = " "
                if is_cursor:
                    # Highlight the column; if empty, draw a small dot so the line is visible.
                    if ch == " ":
                        ch = f"{cursor_tag_open}⠂{cursor_tag_close}"
                    else:
                        ch = f"{cursor_tag_open}{ch}{cursor_tag_close}"
                out.append(ch)

            body = "".join(out) or "—"
            if show_labels and label_w > 0:
                # Label each row band similar to GUI y-axis ticks.
                if lines_n <= 1:
                    y_label = hi
                else:
                    # Map line index to value (top=hi, bottom=lo).
                    frac_y = line_idx / float(lines_n - 1)
                    y_label = int(round(float(hi) - frac_y * float(hi - lo)))
                prefix = f"{label_tag_open}{y_label:>{label_w-1}}{label_tag_close} "
                out_lines.append(prefix + body)
            else:
                out_lines.append(body)

        if show_labels:
            try:
                # Tick/label lines must align with vertical grid lines.
                # Plot area starts after the y-label gutter (`label_w` digits + trailing space).
                plot_left = (label_w + 1) if label_w > 0 else 0
                total_w = plot_left + cols
                if total_w < 20:
                    total_w = 20
                tick_line = [" "] * total_w
                for tv in tick_times:
                    x_plot = int(round((tv - t0) / span_t * float(max(1, cols - 1))))
                    x_plot = max(0, min(cols - 1, x_plot))
                    xpos = max(0, min(total_w - 1, plot_left + x_plot))
                    tick_line[xpos] = "|"
                out_lines.append(f"[{UI_GRAPH_AXIS}]" + "".join(tick_line).rstrip() + f"[/{UI_GRAPH_AXIS}]")

                min_label_dx = float(max(8, min(20, max(1, cols) // 5)))
                last_x_f: Optional[float] = None
                label_line = [" "] * total_w
                for t in tick_times:
                    x_f = (t - t0) / span_t * float(max(1, cols - 1))
                    if last_x_f is None or abs(x_f - last_x_f) >= min_label_dx:
                        txt = datetime.fromtimestamp(t).strftime(fmt)
                        center = plot_left + int(round(x_f))
                        start = center - len(txt) // 2
                        start = max(0, min(total_w - len(txt), start))
                        for i, ch in enumerate(txt):
                            if 0 <= start + i < total_w:
                                label_line[start + i] = ch
                        last_x_f = x_f
                out_lines.append(f"{label_tag_open}" + "".join(label_line).rstrip() + f"{label_tag_close}")
            except Exception:
                pass

        return "\n".join(out_lines)

    class VSQueueTui(App[None]):
        """Textual front-end; drives :class:`QueueMonitorEngine` without Tk."""

        CSS = """
    Screen { align: left top; }
    #topbar_panel { height: auto; width: 100%; border: solid $primary; }
    #topbar { height: auto; width: 100%; padding: 0 1; }
    #play_btn { width: auto; margin-right: 1; }
    #run_indicator { width: auto; color: $text-muted; margin-right: 2; }
    #path_lbl { margin-right: 1; color: $text-muted; }
    #path_input { width: 1fr; }
    #browse_btn { width: auto; margin-left: 1; }
    #settings_btn { width: auto; margin-left: 1; }
    #metrics { height: auto; width: 100%; }
    #status_graph_panel { height: 1fr; width: 100%; border: solid $primary; }
    #status_graph_title { height: auto; padding: 0 1; color: $text-muted; }
    #status_graph_body { height: 1fr; width: 100%; padding: 0 1; }
    #status_divider { height: auto; color: $text-muted; }
    #graph { height: 1fr; width: 100%; padding: 0 1; }
    #panel_header { height: auto; padding: 0 1; color: $text-muted; background: $panel; }
    #info_panel { height: auto; width: 100%; border: solid $primary; }
    #info_body { height: auto; width: 100%; padding: 0 1; }
    #history_panel { height: auto; width: 100%; border: solid $primary; }
    #log { height: 10; width: 100%; padding: 0 1; }
    """

        BINDINGS = [
            # Priority bindings so keys work even when Input has focus.
            Binding("q", "quit", "Quit", priority=True),
            Binding("space", "toggle_monitor", "Play/Stop", priority=True),
            Binding("o", "open_settings", "Settings", priority=True),
            Binding("r", "refresh_view", "Refresh", priority=True),
            Binding("h", "toggle_history", "History", priority=True),
            Binding("l", "toggle_history", "Logs", priority=True),
            Binding("g", "toggle_graph", "Graph", priority=True),
            Binding("m", "toggle_metrics", "Metrics", priority=True),
            Binding("p", "toggle_path", "Path", priority=True),
            Binding("i", "toggle_info", "Info", priority=True),
            Binding("left", "cursor_left", "Cursor left", priority=True),
            Binding("right", "cursor_right", "Cursor right", priority=True),
        ]

        def __init__(self, initial_path: str = "", auto_start: bool = True) -> None:
            super().__init__()
            self._initial_path = initial_path
            self._auto_start = auto_start
            self._engine: Optional[QueueMonitorEngine] = None
            self._history_collapsed: bool = True
            self._graph_hidden: bool = False
            self._metrics_hidden: bool = False
            self._path_hidden: bool = False
            self._info_collapsed: bool = False
            self._cursor_idx: Optional[int] = None

        def compose(self) -> ComposeResult:
            with Vertical(id="topbar_panel"):
                with Horizontal(id="topbar"):
                    # Compact single-line chips (Buttons are tall and force wrapping).
                    yield Static("[bold white on #2e3742] Play [/]", id="play_btn")
                    yield Static("[#9fa7b3]○ Idle[/]", id="run_indicator")
                    yield Static("Logs folder:", id="path_lbl")
                    yield Input(placeholder="Path", id="path_input")
                    yield Static("[bold white on #2e3742] Browse [/]", id="browse_btn")
                    yield Static("[bold white on #5794f2] Settings [/]", id="settings_btn")

            with Vertical(id="status_graph_panel"):
                yield Static("Status / graph", id="status_graph_title")
                with Vertical(id="status_graph_body"):
                    yield Static("", id="metrics")
                    if Rule is not None:
                        yield Rule(line_style="heavy")
                    else:
                        yield Static("─" * 80, id="status_divider")
                    yield Static("", id="graph")
            with Vertical(id="info_panel"):
                yield Static("▼ Info  (i)", id="info_header")
                yield Static("", id="info_body")
            with Vertical(id="history_panel"):
                yield Static("▶ History  (h/l)", id="history_header")
                yield RichLog(id="log", highlight=True, markup=True)

        def _headless_append_history(self, message: str) -> None:
            try:
                self.query_one("#log", RichLog).write_line(message)
            except Exception:
                pass

        def on_static_clicked(self, event: object) -> None:
            # Clickable collapsible headers (GUI-like chevrons).
            try:
                from textual.events import Click  # type: ignore

                if not isinstance(event, Click):
                    return
                wid = getattr(event, "control", None)
                wid_id = getattr(wid, "id", None)
            except Exception:
                return
            if wid_id == "play_btn":
                self.action_toggle_monitor()
            elif wid_id == "settings_btn":
                self.action_open_settings()
            elif wid_id == "browse_btn":
                try:
                    self.query_one("#path_input", Input).focus()
                except Exception:
                    pass
                self._write_log("Browse: paste a folder path into the Logs folder field and press Enter.")
            elif wid_id == "history_header":
                self.action_toggle_history()
            elif wid_id == "info_header":
                self.action_toggle_info()

        class _SettingsScreen(ModalScreen[None]):
            DEFAULT_CSS = """
            _SettingsScreen {
              align: center middle;
            }
            _SettingsScreen > #dlg {
              width: 90%;
              max-width: 100;
              border: solid $primary;
              padding: 1 2;
              background: $panel;
            }
            _SettingsScreen > #dlg Label {
              margin-top: 1;
            }
            """

            def __init__(self, engine: QueueMonitorEngine) -> None:
                super().__init__()
                self._engine = engine

            def compose(self) -> ComposeResult:
                from textual.containers import Horizontal, Vertical
                from textual.widgets import Checkbox, Label

                from .core import get_config_path

                e = self._engine
                cfg_path = str(get_config_path())
                yield Static(
                    f"Settings (TUI)\n\nConfig file: {cfg_path}\n\n"
                    "Edit below and Save, or change the file / use the GUI.",
                    id="dlg_intro",
                )
                yield Vertical(
                    Label("Poll interval (seconds)"),
                    Input(value=e.poll_sec_var.get(), id="poll_sec"),
                    Label("Alert thresholds (comma-separated)"),
                    Input(value=e.alert_thresholds_var.get(), id="alert_thresholds"),
                    Label("Rolling window (points)"),
                    Input(value=e.avg_window_var.get(), id="avg_window"),
                    Label("Warning sound path"),
                    Input(value=e.alert_sound_path_var.get(), id="alert_sound_path"),
                    Checkbox(
                        "Graph Y log scale",
                        value=bool(e.graph_log_scale_var.get()),
                        id="graph_log_scale",
                    ),
                    Checkbox(
                        "Log every position change in History",
                        value=bool(e.show_every_change_var.get()),
                        id="show_every_change",
                    ),
                    Checkbox(
                        "Warning threshold alerts (notify)",
                        value=bool(e.popup_enabled_var.get()),
                        id="popup_enabled",
                    ),
                    Checkbox(
                        "Warning sound",
                        value=bool(e.sound_enabled_var.get()),
                        id="sound_enabled",
                    ),
                    Checkbox(
                        "Completion notify",
                        value=bool(e.completion_popup_enabled_var.get()),
                        id="completion_popup_enabled",
                    ),
                    Checkbox(
                        "Completion sound",
                        value=bool(e.completion_sound_enabled_var.get()),
                        id="completion_sound_enabled",
                    ),
                    Label("Completion sound path"),
                    Input(value=e.completion_sound_path_var.get(), id="completion_sound_path"),
                    Horizontal(
                        Button("Save", id="save", variant="primary"),
                        Button("Close", id="close", variant="default"),
                    ),
                    id="dlg",
                )

            def _save(self) -> None:
                e = self._engine
                try:
                    from textual.widgets import Checkbox

                    e.poll_sec_var.set(self.query_one("#poll_sec", Input).value.strip())
                    raw_thr = self.query_one("#alert_thresholds", Input).value.strip()
                    parse_alert_thresholds(raw_thr)
                    e.alert_thresholds_var.set(raw_thr)
                    e.avg_window_var.set(self.query_one("#avg_window", Input).value.strip())
                    e.alert_sound_path_var.set(self.query_one("#alert_sound_path", Input).value.strip())
                    e.graph_log_scale_var.set(bool(self.query_one("#graph_log_scale", Checkbox).value))
                    e.show_every_change_var.set(bool(self.query_one("#show_every_change", Checkbox).value))
                    e.popup_enabled_var.set(bool(self.query_one("#popup_enabled", Checkbox).value))
                    e.sound_enabled_var.set(bool(self.query_one("#sound_enabled", Checkbox).value))
                    e.completion_popup_enabled_var.set(
                        bool(self.query_one("#completion_popup_enabled", Checkbox).value),
                    )
                    e.completion_sound_enabled_var.set(
                        bool(self.query_one("#completion_sound_enabled", Checkbox).value),
                    )
                    e.completion_sound_path_var.set(self.query_one("#completion_sound_path", Input).value.strip())
                    save_config(e.get_config_snapshot())
                except ValueError as exc:
                    try:
                        self.app.notify(f"Invalid threshold list: {exc}", severity="error")
                    except Exception:
                        pass
                    return
                try:
                    self.app.notify("Settings saved", severity="information")
                except Exception:
                    pass
                try:
                    refresh = getattr(self.app, "_refresh_metrics", None)
                    if callable(refresh):
                        refresh()
                except Exception:
                    pass

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "close":
                    self.app.pop_screen()
                elif event.button.id == "save":
                    self._save()
                    self.app.pop_screen()

        def on_mount(self) -> None:
            hooks = HeadlessMonitorHooks(None)
            hooks.textual_app = self
            eng = QueueMonitorEngine(hooks, initial_path=self._initial_path, auto_start=False)
            eng._headless_append_history = self._headless_append_history  # type: ignore[attr-defined]
            hooks.attach_engine(eng)
            self._engine = eng

            path_in = self.query_one("#path_input", Input)
            path_in.value = eng.source_path_var.get()
            # Don't trap global keybinds in the input by default.
            try:
                self.set_focus(None)
            except Exception:
                pass
            self.set_interval(0.2, self._refresh_metrics)
            if self._auto_start:
                self.call_later(eng.start_monitoring)
            self._apply_history_collapsed()
            self._apply_panel_visibility()

        def _apply_history_collapsed(self) -> None:
            try:
                log = self.query_one("#log", RichLog)
                log.display = not self._history_collapsed
            except Exception:
                pass
            try:
                hdr = self.query_one("#history_header", Static)
                hdr.update(("▶" if self._history_collapsed else "▼") + " History  (h/l)")
            except Exception:
                pass

        def _apply_info_collapsed(self) -> None:
            try:
                body = self.query_one("#info_body", Static)
                body.display = not self._info_collapsed
            except Exception:
                pass
            try:
                hdr = self.query_one("#info_header", Static)
                hdr.update(("▶" if self._info_collapsed else "▼") + " Info  (i)")
            except Exception:
                pass

        def _apply_panel_visibility(self) -> None:
            try:
                self.query_one("#graph", Static).display = not self._graph_hidden
            except Exception:
                pass
            try:
                self.query_one("#metrics", Static).display = not self._metrics_hidden
            except Exception:
                pass
            try:
                self.query_one("#topbar_panel", Vertical).display = not self._path_hidden
            except Exception:
                pass
            self._apply_info_collapsed()

        def action_toggle_history(self) -> None:
            self._history_collapsed = not self._history_collapsed
            self._apply_history_collapsed()
            try:
                self._refresh_metrics()
            except Exception:
                pass

        def action_toggle_graph(self) -> None:
            self._graph_hidden = not self._graph_hidden
            self._apply_panel_visibility()

        def action_toggle_metrics(self) -> None:
            self._metrics_hidden = not self._metrics_hidden
            self._apply_panel_visibility()

        def action_toggle_path(self) -> None:
            self._path_hidden = not self._path_hidden
            self._apply_panel_visibility()

        def action_toggle_info(self) -> None:
            self._info_collapsed = not self._info_collapsed
            self._apply_panel_visibility()

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
                warn = _tui_warnings_kpi_markup(eng)
                st_low = st.lower()
                st_style = "green" if "monitoring" in st_low else UI_SUMMARY_VALUE
                try:
                    self.query_one("#run_indicator", Static).update(
                        "[#9fa7b3]● Monitoring[/]" if eng.running else "[#9fa7b3]○ Idle[/]",
                    )
                    self.query_one("#play_btn", Static).update(
                        "[bold white on #cf222e] Stop [/]" if eng.running else "[bold white on #2e3742] Play [/]",
                    )
                except Exception:
                    pass
                metrics_text = (
                    f"[bold]{APP_DISPLAY_NAME}[/] v{VERSION}  (headless engine, no Tk)\n"
                    f"[{UI_ACCENT_POSITION}]POSITION[/] [bold]{pos}[/]    "
                    f"[{UI_ACCENT_STATUS}]STATUS[/] [{st_style}]{st}[/]    "
                    f"[{UI_ACCENT_RATE}]{hdr}[/] [bold]{rate}[/]\n"
                    f"[{UI_ACCENT_WARNINGS}]WARNINGS[/] {warn}\n"
                    f"[{UI_ACCENT_ELAPSED}]ELAPSED[/] {elapsed}    "
                    f"[{UI_ACCENT_REMAINING}]EST. REMAINING[/] {rem}    "
                    f"[{UI_ACCENT_PROGRESS}]PROGRESS[/] {prog:.0f}%"
                )
                # Cursor info (GUI hover analogue).
                if pts:
                    idx = self._cursor_idx
                    if idx is not None:
                        idx = max(0, min(len(pts) - 1, int(idx)))
                        ct, cv = pts[idx]
                        cts = datetime.fromtimestamp(float(ct)).strftime("%H:%M:%S")
                        metrics_text += f"\n[{UI_GRAPH_HOVER_CURSOR}]Cursor[/]: {cts}  pos {int(cv)}"
                self.query_one("#metrics", Static).update(metrics_text)

                info_text = (
                    f"[dim]Info[/]\n"
                    f"Last change: {eng.last_change_var.get()}\n"
                    f"Last threshold alert: {eng.last_alert_var.get()}\n"
                    f"Resolved log path: {path}\n"
                    f"Global rate: {glo}"
                )
                self.query_one("#info_body", Static).update(info_text)

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
                    cursor_time=(pts[self._cursor_idx][0] if (pts and self._cursor_idx is not None) else None),
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
                self.push_screen(self._SettingsScreen(eng))

        def action_cursor_left(self) -> None:
            eng = self._engine
            if eng is None:
                return
            pts = list(eng.graph_points)
            if not pts:
                return
            if self._cursor_idx is None:
                self._cursor_idx = len(pts) - 1
            else:
                self._cursor_idx = max(0, int(self._cursor_idx) - 1)
            self._refresh_metrics()

        def action_cursor_right(self) -> None:
            eng = self._engine
            if eng is None:
                return
            pts = list(eng.graph_points)
            if not pts:
                return
            if self._cursor_idx is None:
                self._cursor_idx = len(pts) - 1
            else:
                self._cursor_idx = min(len(pts) - 1, int(self._cursor_idx) + 1)
            self._refresh_metrics()

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
