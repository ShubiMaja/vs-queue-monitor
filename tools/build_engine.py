"""One-off generator: vs_queue_monitor/engine.py from _engine_raw.py (run from repo root)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "_engine_raw.py"
OUT = ROOT / "vs_queue_monitor" / "engine.py"

HEADER = '''"""Headless queue monitor logic (no Tk). Used by GUI and SSH-safe TUI."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

from . import VERSION
from .core import *
from .hooks import MonitorHooks

if TYPE_CHECKING:
    pass

'''

NEW_INIT = r'''    def __init__(self, hooks: MonitorHooks, initial_path: str = "", auto_start: bool = True) -> None:
        self._hooks = hooks
        self.config: dict = load_config()
        _cfg_src = self.config.get("source_path", "")
        _cfg_src = _cfg_src.strip() if isinstance(_cfg_src, str) else ""
        _initial_logs = initial_logs_folder_path(initial_path, _cfg_src)
        self.source_path_var = hooks.string_var(_initial_logs)
        if _initial_logs != _cfg_src:
            hooks.schedule_idle(self.persist_config)
        self.resolved_path_var = hooks.string_var("")
        self.status_var = hooks.string_var("Idle")
        self.position_var = hooks.string_var("—")
        self.last_change_var = hooks.string_var("—")
        self.last_alert_var = hooks.string_var("—")
        self.elapsed_var = hooks.string_var("—")
        self.predicted_remaining_var = hooks.string_var("—")
        _at_cfg = self.config.get("alert_thresholds")
        if isinstance(_at_cfg, str) and _at_cfg.strip():
            _alert_default = _at_cfg.strip()
        elif "alert_at" in self.config:
            _alert_default = str(self.config.get("alert_at", "10"))
        else:
            _alert_default = DEFAULT_ALERT_THRESHOLDS
        self.alert_thresholds_var = hooks.string_var(_alert_default)
        self.poll_sec_var = hooks.string_var(str(self.config.get("poll_sec", "2")))
        self.avg_window_var = hooks.string_var(
            str(self.config.get("avg_window_points", DEFAULT_PREDICTION_WINDOW_POINTS)),
        )
        self.queue_rate_var = hooks.string_var("—")
        self.global_rate_var = hooks.string_var("—")
        self.show_log_var = hooks.boolean_var(bool(self.config.get("show_log", True)))
        self.show_status_var = hooks.boolean_var(bool(self.config.get("show_status", True)))
        self.graph_log_scale_var = hooks.boolean_var(bool(self.config.get("graph_log_scale", True)))
        self.popup_enabled_var = hooks.boolean_var(bool(self.config.get("popup_enabled", True)))
        self.sound_enabled_var = hooks.boolean_var(bool(self.config.get("sound_enabled", True)))
        _asp = self.config.get("alert_sound_path")
        if isinstance(_asp, str) and _asp.strip():
            _sound_initial = _asp.strip()
        else:
            _sound_initial = default_alert_sound_path_for_display()
        self.alert_sound_path_var = hooks.string_var(_sound_initial)
        self.completion_sound_enabled_var = hooks.boolean_var(
            bool(self.config.get("completion_sound_enabled", True)),
        )
        _csp = self.config.get("completion_sound_path")
        if isinstance(_csp, str) and _csp.strip():
            _comp_initial = _csp.strip()
        else:
            _comp_initial = default_completion_sound_path_for_display()
        self.completion_sound_path_var = hooks.string_var(_comp_initial)
        self.completion_popup_enabled_var = hooks.boolean_var(
            bool(self.config.get("completion_popup_enabled", True)),
        )
        self.show_every_change_var = hooks.boolean_var(bool(self.config.get("show_every_change", True)))

        self.running = False
        self.monitor_start_epoch: Optional[float] = None
        self.timer_job_id: Optional[str] = None
        self.job_id: Optional[str] = None
        self.current_log_file: Optional[Path] = None
        self.last_position: Optional[int] = None
        self.last_alert_position: Optional[int] = None
        self.last_alert_epoch: float = 0.0
        self._last_queue_completion_notify_epoch: float = 0.0
        self._queue_completion_notified_this_run: bool = False
        self._alert_thresholds_fired: set[int] = set()
        self.active_popup: Optional[Any] = None
        self.active_completion_popup: Optional[Any] = None
        self.graph_points: deque[tuple[float, int]] = deque(maxlen=MAX_GRAPH_POINTS)
        self.graph_canvas: Optional[Any] = None
        self.current_point: Optional[tuple[float, int]] = None
        self.graph_points_drawn: list[tuple[float, int]] = []
        self._graph_hover_point: Optional[tuple[float, int]] = None
        self.graph_tooltip: Optional[Any] = None
        self._warnings_kpi_frame: Optional[Any] = None
        self.history_text: Optional[Any] = None
        self.status_frame: Optional[Any] = None
        self._status_body_wrap: Optional[Any] = None
        self._status_sep: Optional[Any] = None
        self._status_tab_btn: Optional[Any] = None
        self._fit_status_collapsed_job: Optional[str] = None
        self.history_frame: Optional[Any] = None
        self._history_body: Optional[Any] = None
        self._history_sep: Optional[Any] = None
        self.panes: Optional[Any] = None
        self.start_stop_button: Optional[Any] = None
        self._settings_win: Optional[Any] = None
        self._about_win: Optional[Any] = None
        self._graph_y_scale_btn: Optional[Any] = None
        self._history_tab_btn: Optional[Any] = None
        self._fit_history_collapsed_job: Optional[str] = None
        self._pane_drag_threshold_job: Optional[str] = None
        self._pred_speed_scale: float = 1.0
        self._stale_slots_accounted: int = 0
        self._starting: bool = False
        self._start_seq: int = 0
        self._loading_spinner: Optional[Any] = None
        self._settings_btn: Optional[Any] = None
        self._queue_progress_value: float = 0.0
        self._status_value_label: Optional[Any] = None
        self._position_emoji_label: Optional[Any] = None
        self._position_one_reached_at: Optional[float] = None
        self._connect_phase_started_epoch: Optional[float] = None
        self._progress_at_front_entry: Optional[float] = None
        self._left_connect_queue_detected: bool = False
        self._persist_config_job: Optional[str] = None
        self._configure_resize_job: Optional[str] = None
        self._last_queue_run_session: int = -1
        self._last_queue_position_change_epoch: Optional[float] = None
        self._last_queue_line_epoch: Optional[float] = None
        self._last_log_stat: Optional[tuple[int, float]] = None
        self._last_log_growth_epoch: Optional[float] = None
        self._queue_stale_latched: bool = False
        self._queue_stale_logged_once: bool = False
        self._mpp_floor_position: Optional[int] = None
        self._mpp_floor_value: Optional[float] = None
        self._interrupted_mode: bool = False
        self._interrupt_baseline_session: int = -1
        self._dismissed_new_queue_session: Optional[int] = None
        self._interrupted_elapsed_sec: Optional[float] = None
        self._frozen_rates_at_interrupt: Optional[tuple[str, str]] = None

        self.avg_window_var.trace_add("write", self._on_avg_window_write)
        self.graph_log_scale_var.trace_add(
            "write",
            lambda *_: (self._refresh_kpi_rate_header(), self._hooks.request_redraw_graph()),
        )
        self.show_log_var.trace_add("write", self._schedule_config_persist)
        self.show_status_var.trace_add("write", self._schedule_config_persist)
        self._bind_config_persist_traces()
        self.start_timer()
        self._hooks.append_history(
            "WARNING — Work in progress; AI-assisted code. Expect bugs and rough edges. "
            "Verify log paths, queue readings, and alerts yourself; do not rely on this tool as a sole source of truth."
        )
        self._hooks.append_history(
            "VS Queue Monitor started. Waiting for a path. Parser looks for queue lines like "
            "'Client is in connect queue at position: N'."
        )
        if auto_start:
            self._hooks.schedule(250, self.start_monitoring)
'''

TRY_BROWSE = '''
    def _try_start_after_browse(self) -> None:
        if self._starting:
            return
        if self.running:
            self.stop_monitoring()
        self.start_monitoring()
'''


def main() -> None:
    text = RAW.read_text(encoding="utf-8")
    # Strip old module docstring and imports — keep only class
    idx = text.index("class QueueMonitorEngine:")
    body = text[idx:]
    # Replace __init__
    body = re.sub(
        r"    def __init__\(self, initial_path:.*?if auto_start:\n            self\.after\(250, self\.start_monitoring\)\n",
        NEW_INIT,
        body,
        count=1,
        flags=re.DOTALL,
    )
    # Global substitutions
    reps = [
        ("messagebox.showerror(", "self._hooks.show_error("),
        ("messagebox.askyesno(", "self._hooks.ask_yes_no("),
        (", parent=self)", ")"),
        ("self.after(", "self._hooks.schedule("),
        ("self.after_idle(", "self._hooks.schedule_idle("),
        ("self.after_cancel(", "self._hooks.schedule_cancel("),
        ("if not self.winfo_exists():", "if not self._hooks.winfo_exists():"),
        ("self.redraw_graph()", "self._hooks.request_redraw_graph()"),
        ("self.bell()", "self._hooks.bell()"),
        ("self.show_popup(", "self._hooks.show_threshold_popup("),
        ("self.show_completion_popup()", "self._hooks.show_completion_popup()"),
        ("'window_geometry': self.geometry()", "'window_geometry': self._hooks.window_geometry_for_save()"),
        ("tk.TclError", "Exception"),
    ]
    for a, b in reps:
        body = body.replace(a, b)
    # Progress bar value
    body = body.replace("if self._queue_progress is not None:", "if True:")
    body = body.replace("self._queue_progress['value']", "self._queue_progress_value")
    body = body.replace("self._queue_progress[\"value\"]", "self._queue_progress_value")
    body = body.replace("float(self._queue_progress_value)", "float(self._queue_progress_value)")
    body = body.replace(
        "self._queue_progress.configure(value=0.0)",
        "self._queue_progress_value = 0.0",
    )
    # write_history
    body = re.sub(
        r"    def write_history\(self, message: str\) -> None:.*?self\.history_text\.configure\(state='disabled'\)\n",
        "    def write_history(self, message: str) -> None:\n        self._hooks.append_history(message)\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # _set_status_line — keep label updates only if labels exist
    body = re.sub(
        r"    def _set_status_line\(self, text: str.*?\n            self\._status_value_label\.configure\(fg=UI_DANGER if danger else UI_SUMMARY_VALUE\)\n",
        "    def _set_status_line(self, text: str, *, danger: bool = False) -> None:\n"
        "        self.status_var.set(text)\n"
        "        if self._status_value_label is not None:\n"
        "            self._status_value_label.configure(fg=UI_DANGER if danger else UI_SUMMARY_VALUE)\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # _refresh_warnings_kpi — no-op without GUI frame
    body = re.sub(
        r"    def _refresh_warnings_kpi\(self\) -> None:.*?tk\.Label\(fr, text=str\(t\).*?\n",
        "    def _refresh_warnings_kpi(self) -> None:\n"
        "        \"\"\"Configured CSV thresholds (GUI builds widgets; headless no-op).\"\"\"\n"
        "        fr = getattr(self, '_warnings_kpi_frame', None)\n"
        "        if fr is None:\n"
        "            return\n"
        "        try:\n"
        "            import tkinter as tk\n"
        "            if not fr.winfo_exists():\n"
        "                return\n"
        "        except Exception:\n"
        "            return\n"
        "        for w in fr.winfo_children():\n"
        "            w.destroy()\n"
        "        try:\n"
        "            thresholds = parse_alert_thresholds(self.alert_thresholds_var.get())\n"
        "        except ValueError:\n"
        "            import tkinter as tk\n"
        "            tk.Label(fr, text='—', bg=UI_SUMMARY_BG, fg=UI_TEXT_MUTED, font=KPI_VALUE_FONT, anchor='w').pack(side='left')\n"
        "            return\n"
        "        if not thresholds:\n"
        "            import tkinter as tk\n"
        "            tk.Label(fr, text='—', bg=UI_SUMMARY_BG, fg=UI_TEXT_MUTED, font=KPI_VALUE_FONT, anchor='w').pack(side='left')\n"
        "            return\n"
        "        pos: Optional[int] = self.last_position\n"
        "        if pos is None and self.current_point is not None:\n"
        "            pos = self.current_point[1]\n"
        "        fired = self._alert_thresholds_fired\n"
        "        import tkinter as tk\n"
        "        for i, t in enumerate(thresholds):\n"
        "            if i > 0:\n"
        "                tk.Label(fr, text='·', bg=UI_SUMMARY_BG, fg=UI_TEXT_MUTED, font=KPI_VALUE_FONT, anchor='w').pack(side='left', padx=(3, 3))\n"
        "            passed = pos is not None and pos <= t or t in fired\n"
        "            fg = UI_TEXT_MUTED if passed else UI_SUMMARY_VALUE\n"
        "            tk.Label(fr, text=str(t), bg=UI_SUMMARY_BG, fg=fg, font=KPI_VALUE_FONT, anchor='w').pack(side='left')\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # _show_start_loading
    body = re.sub(
        r"    def _show_start_loading\(self, show: bool\) -> None:.*?self\.update_start_stop_button\(\)\n",
        "    def _show_start_loading(self, show: bool) -> None:\n        self._hooks.show_start_loading(show)\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    # stop_monitoring: remove update_start_stop_button
    body = body.replace(
        "        self.update_start_stop_button()\n        try:\n            self._refresh_warnings_kpi()",
        "        try:\n            self._refresh_warnings_kpi()",
    )
    # reset_defaults: remove _on_show_log_write
    body = body.replace(
        "        self.write_history('Settings reset to defaults.')\n        self._on_show_log_write()\n        self._on_show_status_write()\n",
        "        self.write_history('Settings reset to defaults.')\n",
    )
    # _apply_browsed — use hooks.schedule
    body = body.replace("self.after(0, self._try_start_after_browse)", "self._hooks.schedule(0, self._try_start_after_browse)")
    # Insert _try_start_after_browse before _apply_browsed if not present
    if "def _try_start_after_browse" not in body:
        body = body.replace(
            "    def _apply_browsed_log_path(self, raw: str) -> None:",
            TRY_BROWSE.strip() + "\n\n    def _apply_browsed_log_path(self, raw: str) -> None:",
        )

    OUT.write_text(HEADER + "\n" + body, encoding="utf-8")
    print("Wrote", OUT, "chars", len(HEADER + body))


if __name__ == "__main__":
    main()
