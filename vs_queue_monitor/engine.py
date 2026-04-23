"""Headless queue monitor logic. Used by the local web UI (``vs_queue_monitor.web``)."""

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

try:
    from . import VERSION
    from .core import *
    from .hooks import MonitorHooks
except ImportError as exc:  # pragma: no cover
    if __name__ == "__main__":
        raise SystemExit(
            "Do not run vs_queue_monitor/engine.py directly (it uses package-relative imports).\n"
            "Run one of these from the repo root instead:\n"
            "  - python monitor.py   (embedded web UI on 127.0.0.1)\n"
            "  - python -m vs_queue_monitor\n"
            "  - python monitor.py --web-browser   (external browser instead of embedded window)\n"
        ) from exc
    raise

if TYPE_CHECKING:
    pass


class QueueMonitorEngine:

    def __init__(self, hooks: MonitorHooks, initial_path: str = "", auto_start: bool = True) -> None:
        self._hooks = hooks
        self.push_notifier: Optional[Callable[[str, dict[str, Any]], None]] = None
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
        self.server_target_var = hooks.string_var("—")
        self.last_change_var = hooks.string_var("—")
        self.last_alert_var = hooks.string_var("—")
        self.last_alert_message_var = hooks.string_var("—")
        self._last_alert_seq: int = 0
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
        self.graph_log_scale_var = hooks.boolean_var(bool(self.config.get("graph_log_scale", False)))
        self.graph_live_view_var = hooks.boolean_var(bool(self.config.get("graph_live_view", True)))
        self.graph_time_mode_var = hooks.string_var(str(self.config.get("graph_time_mode", "relative")))
        self.tutorial_done_var = hooks.boolean_var(bool(self.config.get("tutorial_done", False)))
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
        self.failure_sound_enabled_var = hooks.boolean_var(
            bool(self.config.get("failure_sound_enabled", True)),
        )
        _fsp = self.config.get("failure_sound_path")
        if isinstance(_fsp, str) and _fsp.strip():
            _fail_initial = _fsp.strip()
        else:
            _fail_initial = default_failure_sound_path_for_display()
        self.failure_sound_path_var = hooks.string_var(_fail_initial)
        self.completion_popup_enabled_var = hooks.boolean_var(
            bool(self.config.get("completion_popup_enabled", True)),
        )
        self.failure_popup_enabled_var = hooks.boolean_var(
            bool(self.config.get("failure_popup_enabled", True)),
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
        self.current_point: Optional[tuple[float, int]] = None
        self.graph_points_drawn: list[tuple[float, int]] = []
        self._pred_speed_scale: float = 1.0
        self._stale_slots_accounted: int = 0
        self._starting: bool = False
        self._start_seq: int = 0
        self._queue_progress_value: float = 0.0
        self._position_one_reached_at: Optional[float] = None
        self._connect_phase_started_epoch: Optional[float] = None
        self._progress_at_front_entry: Optional[float] = None
        self._left_connect_queue_detected: bool = False
        self._persist_config_job: Optional[str] = None
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
        self._interrupt_entry_queue_line_epoch: Optional[float] = None
        self._dismissed_new_queue_session: Optional[int] = None
        self._interrupted_elapsed_sec: Optional[float] = None
        self._frozen_rates_at_interrupt: Optional[tuple[str, str]] = None
        self._pending_new_queue_session: Optional[int] = None

        self.avg_window_var.trace_add("write", self._on_avg_window_write)
        self.graph_log_scale_var.trace_add(
            "write",
            lambda *_: (self._refresh_kpi_rate_header(), self._hooks.request_redraw_graph()),
        )
        self.graph_time_mode_var.trace_add(
            "write",
            lambda *_: self._hooks.request_redraw_graph(),
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

    def _on_avg_window_write(self, *_args: object) -> None:
        """Recompute avg speed / remaining when the rolling window size changes."""
        self.update_time_estimates()

    def toggle_monitoring(self) -> None:
        if self._starting:
            return
        if self.running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def get_config_snapshot(self) -> dict:
        return {'source_path': self.source_path_var.get(), 'alert_thresholds': self.alert_thresholds_var.get(), 'poll_sec': self.poll_sec_var.get(), 'avg_window_points': self.avg_window_var.get(), 'show_log': bool(self.show_log_var.get()), 'show_status': bool(self.show_status_var.get()), 'graph_log_scale': bool(self.graph_log_scale_var.get()), 'graph_live_view': bool(self.graph_live_view_var.get()), 'graph_time_mode': self.graph_time_mode_var.get(), 'popup_enabled': bool(self.popup_enabled_var.get()), 'sound_enabled': bool(self.sound_enabled_var.get()), 'alert_sound_path': self.alert_sound_path_var.get().strip(), 'completion_popup_enabled': bool(self.completion_popup_enabled_var.get()), 'completion_sound_enabled': bool(self.completion_sound_enabled_var.get()), 'completion_sound_path': self.completion_sound_path_var.get().strip(), 'failure_popup_enabled': bool(self.failure_popup_enabled_var.get()), 'failure_sound_enabled': bool(self.failure_sound_enabled_var.get()), 'failure_sound_path': self.failure_sound_path_var.get().strip(), 'show_every_change': bool(self.show_every_change_var.get()), 'tutorial_done': bool(self.tutorial_done_var.get()), 'window_geometry': self._hooks.window_geometry_for_save(), 'version': VERSION}

    def persist_config(self) -> None:
        save_config(self.get_config_snapshot())

    def _schedule_config_persist(self, *_args: object) -> None:
        if self._persist_config_job is not None:
            try:
                self._hooks.schedule_cancel(self._persist_config_job)
            except Exception:
                pass
        self._persist_config_job = self._hooks.schedule(450, self._flush_config_persist)

    def _flush_config_persist(self) -> None:
        self._persist_config_job = None
        try:
            self.persist_config()
        except Exception:
            pass

    def _bind_config_persist_traces(self) -> None:
        """Save config.json shortly after any setting change (debounced)."""
        for var in (self.source_path_var, self.alert_thresholds_var, self.poll_sec_var, self.avg_window_var, self.show_log_var, self.show_status_var, self.graph_log_scale_var, self.graph_live_view_var, self.graph_time_mode_var, self.popup_enabled_var, self.sound_enabled_var, self.alert_sound_path_var, self.completion_popup_enabled_var, self.completion_sound_enabled_var, self.completion_sound_path_var, self.failure_popup_enabled_var, self.failure_sound_enabled_var, self.failure_sound_path_var, self.show_every_change_var, self.tutorial_done_var):
            var.trace_add('write', self._schedule_config_persist)

    def reset_defaults(self) -> None:
        self.stop_monitoring()
        self.source_path_var.set(DEFAULT_PATH)
        self.alert_thresholds_var.set(DEFAULT_ALERT_THRESHOLDS)
        self.poll_sec_var.set('2')
        self.avg_window_var.set(str(DEFAULT_PREDICTION_WINDOW_POINTS))
        self.show_log_var.set(True)
        self.show_status_var.set(True)
        self.graph_log_scale_var.set(False)
        self.graph_live_view_var.set(True)
        self.graph_time_mode_var.set('relative')
        self.popup_enabled_var.set(True)
        self.sound_enabled_var.set(True)
        self.alert_sound_path_var.set(default_alert_sound_path_for_display())
        self.completion_popup_enabled_var.set(True)
        self.completion_sound_enabled_var.set(True)
        self.completion_sound_path_var.set(default_completion_sound_path_for_display())
        self.failure_popup_enabled_var.set(True)
        self.failure_sound_enabled_var.set(True)
        self.failure_sound_path_var.set(default_failure_sound_path_for_display())
        self.show_every_change_var.set(True)
        self.tutorial_done_var.set(False)
        self.resolved_path_var.set('')
        self._set_status_line('Idle')
        self._set_position_display(None)
        self.server_target_var.set('—')
        self.elapsed_var.set('—')
        self.predicted_remaining_var.set('—')
        self.queue_rate_var.set('—')
        self._refresh_kpi_rate_header()
        self.global_rate_var.set('—')
        self.last_change_var.set('—')
        self.last_alert_var.set('—')
        self.last_alert_message_var.set('—')
        self._last_alert_seq = 0
        if True:
            self._queue_progress_value = 0.0
        self._position_one_reached_at = None
        self._connect_phase_started_epoch = None
        self._progress_at_front_entry = None
        self._left_connect_queue_detected = False
        self._queue_completion_notified_this_run = False
        self._last_queue_completion_notify_epoch = 0.0
        self._last_queue_run_session = -1
        self._last_queue_position_change_epoch = None
        self._last_queue_line_epoch = None
        self._last_log_stat = None
        self._last_log_growth_epoch = None
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        self._interrupted_elapsed_sec = None
        self._frozen_rates_at_interrupt = None
        self._interrupted_mode = False
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self._pending_new_queue_session = None
        self.graph_points.clear()
        self.current_point = None
        self._alert_thresholds_fired.clear()
        self._hooks.request_redraw_graph()
        self.persist_config()
        self.write_history('Settings reset to defaults.')
        self._refresh_warnings_kpi()
        self._starting = False
        self.start_monitoring()

    def write_history(self, message: str) -> None:
        self._hooks.append_history(message)

    def _emit_push_notification(self, kind: str, payload: dict[str, Any]) -> None:
        notifier = self.push_notifier
        if not callable(notifier):
            return
        try:
            notifier(kind, payload)
        except Exception:
            pass


    def _set_status_line(self, text: str, *, danger: bool = False) -> None:
        self.status_var.set(text)

    def _set_position_display(self, pos: Optional[int]) -> None:
        """KPI digits for queue position (web UI reads ``position_var``)."""
        if pos is None:
            self.position_var.set('—')
        else:
            self.position_var.set(str(pos))

    def _refresh_server_target_from_tail_text(self, tail_text: Optional[str], session_id: Optional[int] = None) -> None:
        if not tail_text:
            return
        target = parse_tail_latest_connect_target(tail_text, session_id)
        if target:
            self.server_target_var.set(target)

    def _refresh_server_target_from_log(self, log_file: Path, session_id: Optional[int] = None) -> None:
        self._refresh_server_target_from_tail_text(read_log_file_tail_text(log_file, TAIL_BYTES), session_id)

    def _refresh_warnings_kpi(self) -> None:
        """Warnings rail is driven by the web snapshot; no desktop widgets to refresh."""
        return

    def _try_start_after_browse(self) -> None:
        if self._starting:
            return
        if self.running:
            self.stop_monitoring()
        self.start_monitoring()

    def _apply_browsed_log_path(self, raw: str) -> None:
        """Set log source from a browsed folder; the client log may appear later (e.g. after starting VS)."""
        raw = (raw or '').strip()
        if not raw:
            return
        try:
            folder = expand_logs_folder_path(raw)
        except ValueError as exc:
            self._hooks.show_error('Invalid folder', str(exc))
            return
        except Exception:
            self._hooks.show_error('Invalid path', 'Could not resolve that path.')
            return
        self.source_path_var.set(str(folder))
        self._hooks.schedule(0, self._try_start_after_browse)

    def parse_int(self, raw: str, name: str, minimum: int=0) -> int:
        try:
            value = int(float(raw))
        except Exception as exc:
            raise ValueError(f'{name} must be a number') from exc
        if value < minimum:
            raise ValueError(f'{name} must be >= {minimum}')
        return value

    def parse_float(self, raw: str, name: str, minimum: float=0.1) -> float:
        try:
            value = float(raw)
        except Exception as exc:
            raise ValueError(f'{name} must be a number') from exc
        if value < minimum:
            raise ValueError(f'{name} must be >= {minimum}')
        return value

    def start_monitoring(self) -> None:
        if self._starting:
            return
        try:
            folder = expand_logs_folder_path(self.source_path_var.get())
        except ValueError as exc:
            self._set_status_line('Error')
            self._hooks.show_error('Start failed', str(exc))
            return
        except Exception as exc:
            self._set_status_line('Error')
            self._hooks.show_error('Start failed', str(exc))
            return
        self.source_path_var.set(str(folder))
        try:
            parse_alert_thresholds(self.alert_thresholds_var.get())
        except ValueError as exc:
            self._set_status_line('Error')
            self._hooks.show_error('Start failed', str(exc))
            return
        self._alert_thresholds_fired.clear()
        self._position_one_reached_at = None
        self._connect_phase_started_epoch = None
        self._progress_at_front_entry = None
        self._left_connect_queue_detected = False
        self._queue_completion_notified_this_run = False
        self._last_queue_run_session = -1
        self._last_queue_position_change_epoch = None
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        self.last_alert_epoch = 0.0
        self.poll_sec = self.parse_float(self.poll_sec_var.get(), 'Poll sec', 0.2)
        resolved = resolve_log_file(str(folder))
        self._starting = True
        self._start_seq += 1
        seq = self._start_seq
        if resolved is None:
            self._hooks.show_start_loading(True)
            self._set_status_line('Starting…')
            self._hooks.schedule(0, lambda: self._finish_start_monitoring(seq, None, None, None))
            return
        self._hooks.show_start_loading(True)
        self._set_status_line('Loading log…')

        def worker() -> None:
            try:
                seed_data = compute_seed_graph_from_log(resolved)
            except Exception as exc:
                self._hooks.schedule(0, lambda e=exc: self._finish_start_monitoring(seq, resolved, None, e))
                return
            self._hooks.schedule(0, lambda d=seed_data: self._finish_start_monitoring(seq, resolved, d, None))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_start_monitoring(self, seq: int, resolved: Optional[Path], seed_data: Optional[tuple[list[tuple[float, int]], int, int, float, int, int, int, Optional[int], Optional[float], Optional[float]]], error: Optional[Exception]) -> None:
        if seq != self._start_seq:
            return
        try:
            if not self._hooks.winfo_exists():
                return
        except Exception:
            return
        self._starting = False
        if error is not None:
            self._hooks.show_start_loading(False)
            self._set_status_line('Error')
            self._hooks.show_error('Start failed', str(error))
            return
        if resolved is None:
            self.current_log_file = None
            self.resolved_path_var.set('—')
            self.running = True
            self.monitor_start_epoch = time.time()
            self._interrupted_elapsed_sec = None
            self._frozen_rates_at_interrupt = None
            self._interrupted_mode = False
            self._interrupt_baseline_session = -1
            self._dismissed_new_queue_session = None
            self._set_status_line('Waiting for log file')
            self.write_history('Monitoring started. No client log file yet (e.g. client-main.log) under this folder — watching until it appears (start Vintage Story or check the path).')
            self.persist_config()
            self._hooks.show_start_loading(False)
            self.graph_points.clear()
            self.current_point = None
            self.last_position = None
            self._set_position_display(None)
            self._hooks.request_redraw_graph()
            self.start_timer()
            if self.job_id is not None:
                self._hooks.schedule_cancel(self.job_id)
                self.job_id = None
            self.poll_once()
            return
        self.current_log_file = resolved
        self.resolved_path_var.set(str(resolved))
        self.running = True
        self.monitor_start_epoch = time.time()
        self._interrupted_elapsed_sec = None
        self._frozen_rates_at_interrupt = None
        self._interrupted_mode = False
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self._set_status_line('Monitoring')
        self.write_history(f'Monitoring started. Log file: {resolved}')
        self.persist_config()
        self._hooks.show_start_loading(False)
        self._apply_seed_result(seed_data)
        self._refresh_server_target_from_log(resolved, self._last_queue_run_session if self._last_queue_run_session >= 0 else None)
        self._suppress_completion_notify_if_tail_already_completed(resolved)
        self._adopt_interrupted_tail_on_start(resolved)
        self.start_timer()
        if self.job_id is not None:
            self._hooks.schedule_cancel(self.job_id)
            self.job_id = None
        self.poll_once()

    def _suppress_completion_notify_if_tail_already_completed(self, log_file: Path) -> None:
        """If the tail already shows a completed queue wait, skip the next completion popup/sound."""
        try:
            if not log_file.is_file():
                return
        except OSError:
            return
        t = read_log_file_tail_text(log_file, TAIL_BYTES)
        if t is None or not completion_would_fire_for_tail(t):
            return
        self._queue_completion_notified_this_run = True

    def _adopt_interrupted_tail_on_start(self, log_file: Path) -> None:
        """If startup seeded a run that is already interrupted, keep it as the interrupted baseline."""
        t = read_log_file_tail_text(log_file, TAIL_BYTES)
        if not t:
            return
        kind, _tail_pos = classify_tail_connection_state(t)
        pos, _queue_sess = parse_tail_last_queue_reading(t)
        left = tail_has_post_queue_after_last_queue_line(t)
        should_interrupt = (
            kind == 'disconnected'
            or (kind in ('reconnecting', 'grace') and not (pos is not None and pos <= 1))
            or (kind in ('reconnecting', 'grace') and left and (pos is not None and pos <= 1))
        )
        if should_interrupt:
            self._interrupted_mode = True
            start_t = self._queue_elapsed_start_epoch()
            if start_t is not None and self.current_point is not None:
                if pos is not None and pos <= 1 and self._position_one_reached_at is not None:
                    self._interrupted_elapsed_sec = max(0.0, self._position_one_reached_at - start_t)
                else:
                    self._interrupted_elapsed_sec = max(0.0, self.current_point[0] - start_t)
            else:
                self._interrupted_elapsed_sec = self._snapshot_elapsed_seconds_at_interrupt()
            self._interrupt_baseline_session = self._last_queue_run_session
            self._interrupt_entry_queue_line_epoch = self._last_queue_line_epoch
            self._dismissed_new_queue_session = self._last_queue_run_session
            self._frozen_rates_at_interrupt = ('—', '—')
            self._set_status_line('Interrupted', danger=True)
            self.update_time_estimates()
            self.write_history('Monitoring started on an already-interrupted queue run; still watching the log for a newer run.')

    def _last_queue_position_is_at_front(self) -> bool:
        """True when waiting at the front of the queue (log still shows position 1), not past-queue (0)."""
        pos = self.last_position
        if pos is None and self.current_point is not None:
            pos = self.current_point[1]
        return pos == 1

    def _bump_log_activity_if_changed(self, path: Path) -> None:
        """Update last activity time when the log file grows or its mtime changes."""
        try:
            st = path.stat()
        except OSError:
            return
        key = (st.st_size, st.st_mtime)
        if self._last_log_stat != key:
            self._last_log_stat = key
            self._last_log_growth_epoch = time.time()
        elif self._last_log_growth_epoch is None:
            self._last_log_growth_epoch = time.time()

    def enter_interrupted_state(self, detail: str='') -> None:
        """Freeze elapsed and show Interrupted, but keep polling the log (no stop)."""
        if self._interrupted_mode:
            return
        now = time.time()
        self._interrupted_mode = True
        self._interrupted_elapsed_sec = self._snapshot_elapsed_seconds_at_interrupt()
        self._interrupt_baseline_session = self._last_queue_run_session
        self._interrupt_entry_queue_line_epoch = self._last_queue_line_epoch
        self._dismissed_new_queue_session = None
        self._frozen_rates_at_interrupt = ('—', '—')
        self._set_status_line('Interrupted', danger=True)
        self.update_time_estimates()
        msg = 'Queue interrupted; still watching the log. A new queue run can be loaded when detected.'
        if detail:
            msg += f' ({detail})'
        self.write_history(msg)
        if self.failure_popup_enabled_var.get():
            self._hooks.show_failure_popup(detail)
            self._emit_push_notification(
                "failure",
                {
                    "title": "Queue interrupted",
                    "body": f"Queue interrupted — still watching the log.\nStatus: {self.status_var.get() or 'Interrupted'}\nLast change: {self.last_change_var.get() or '—'}",
                    "tag": f"vsqm-failure-{int(now * 1000)}",
                    "kind": "failure",
                    "renotify": True,
                },
            )
        if self.failure_sound_enabled_var.get():
            self.play_failure_sound()

    def _handle_interrupted_tail(self, position: Optional[int], queue_sess: int, last_queue_line_epoch: Optional[float] = None, total_queue_boundaries: Optional[int] = None, kind: str = '') -> None:
        """While interrupted, detect a newer queue session and offer to load it."""
        # Use total boundary count only when there is also at least one new position line in the
        # new session (queue_sess == total_queue_boundaries), avoiding false triggers from
        # mid-game reconnect lines that appear without an accompanying queue position line.
        effective_sess = queue_sess
        entry_epoch = self._interrupt_entry_queue_line_epoch
        # The small live tail can count queue-session boundaries differently from the larger
        # seed scan used when we accepted the current run. Do not treat the same queue lines
        # as a "new run" again unless the newest queue line is actually newer than the one
        # that put us into interrupted mode.
        if (
            last_queue_line_epoch is not None
            and entry_epoch is not None
            and last_queue_line_epoch <= entry_epoch
        ):
            return
        # If the newest detected run is already interrupted/disconnected by the time we see it,
        # do not offer it as a fresh run to adopt.
        if kind == 'disconnected' or (kind in ('reconnecting', 'grace') and not (position is not None and position <= 1)):
            return
        if position is None and effective_sess <= self._interrupt_baseline_session:
            return
        if effective_sess <= self._interrupt_baseline_session:
            # Session count can appear lower than baseline when the log grew between sessions
            # and old boundary lines scrolled out of the tail window.  If the most recent
            # queue line is provably newer than the epoch we entered interrupted state, it is
            # a new run regardless of the apparent session count.
            if (last_queue_line_epoch is None or entry_epoch is None
                    or last_queue_line_epoch <= entry_epoch):
                return
        if effective_sess == self._dismissed_new_queue_session:
            return
        if self._pending_new_queue_session == effective_sess:
            return
        async_ui = getattr(self._hooks, 'new_queue_dialog_async', None)
        if callable(async_ui) and async_ui():
            self._pending_new_queue_session = effective_sess
            return
        if self._hooks.ask_yes_no(
            'New queue detected',
            'A new queue run was detected in the log.\n\nLoad it? This will reset the graph and threshold alerts for the new run.',
        ):
            self._accept_new_queue_from_log()
        else:
            self._dismissed_new_queue_session = effective_sess

    def resolve_new_queue_offer(self, accept: bool) -> None:
        """Used by the local web UI when ``new_queue_dialog_async`` deferred the dialog."""
        sess = self._pending_new_queue_session
        if sess is None:
            return
        self._pending_new_queue_session = None
        if accept:
            self._accept_new_queue_from_log()
        else:
            self._dismissed_new_queue_session = sess

    def _accept_new_queue_from_log(self) -> None:
        """Leave interrupted state and seed the graph from the current log (new queue run)."""
        self._dismissed_new_queue_session = None
        path = self.current_log_file
        if path is None or not path.is_file():
            self.write_history('Cannot load new queue: log file missing.')
            return
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._position_one_reached_at = None
        self._connect_phase_started_epoch = None
        self._queue_progress_value = 0.0
        self._progress_at_front_entry = None
        self._left_connect_queue_detected = False
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        self._alert_thresholds_fired.clear()
        self._queue_completion_notified_this_run = False
        ok = self._reseed_graph_for_new_run(path)
        if ok:
            tail_text = read_log_file_tail_text(path, TAIL_BYTES)
            adopted_kind = None
            adopted_pos = None
            if tail_text:
                adopted_kind, _tail_pos = classify_tail_connection_state(tail_text)
                adopted_pos, _tail_sess = parse_tail_last_queue_reading(tail_text)
            stays_interrupted = (
                adopted_kind == 'disconnected'
                or (
                    adopted_kind in ('reconnecting', 'grace')
                    and not (adopted_pos is not None and adopted_pos <= 1)
                )
            )
            if stays_interrupted:
                self._interrupted_mode = True
                self._interrupt_baseline_session = self._last_queue_run_session
                self._interrupt_entry_queue_line_epoch = self._last_queue_line_epoch
                self._set_status_line('Interrupted', danger=True)
                self.write_history('Adopted detected queue run; it is already interrupted, still watching the log.')
            else:
                self._interrupted_mode = False
                self._interrupted_elapsed_sec = None
                self._frozen_rates_at_interrupt = None
                self._interrupt_baseline_session = -1
                self._interrupt_entry_queue_line_epoch = None
                self._set_status_line('Monitoring')
        else:
            self.write_history('Could not find queue data in the log for the new run.')
            self._set_status_line('Warning: no queue detected', danger=True)
            self.graph_points.clear()
            self.current_point = None
            self.last_position = None
            self._set_position_display(None)
            self._hooks.request_redraw_graph()

    def stop_monitoring(self) -> None:
        self._interrupted_mode = False
        self._interrupted_elapsed_sec = None
        self._frozen_rates_at_interrupt = None
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self._pending_new_queue_session = None
        self.running = False
        self.monitor_start_epoch = None
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._last_queue_position_change_epoch = None
        self._last_queue_line_epoch = None
        self._last_log_stat = None
        self._last_log_growth_epoch = None
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        if self._left_connect_queue_detected:
            self._set_status_line('Completed')
            self.write_history('Monitoring stopped (completed).')
        elif self._last_queue_position_is_at_front():
            self._set_status_line('Stopped')
            self.write_history('Monitoring stopped (still at queue front; past-queue lines not seen in log tail yet).')
        else:
            self._set_status_line('Stopped')
            self.write_history('Monitoring stopped.')
        if self.job_id is not None:
            self._hooks.schedule_cancel(self.job_id)
            self.job_id = None
        try:
            self._refresh_warnings_kpi()
        except Exception:
            pass

    def start_timer(self) -> None:
        if self.timer_job_id is not None:
            try:
                self._hooks.schedule_cancel(self.timer_job_id)
            except Exception:
                pass
            self.timer_job_id = None
        self.tick_timer()

    def stop_timer(self) -> None:
        if self.timer_job_id is not None:
            try:
                self._hooks.schedule_cancel(self.timer_job_id)
            except Exception:
                pass
            self.timer_job_id = None

    def tick_timer(self) -> None:
        self.update_time_estimates()
        self.timer_job_id = self._hooks.schedule(ESTIMATE_TICK_MS, self.tick_timer)

    def _reseed_graph_for_new_run(self, log_file: Path) -> bool:
        """Replace the graph for a new queue session: full segment from log, or one point from the tail."""
        data = compute_seed_graph_from_log(log_file)
        if data is not None:
            self._apply_seed_result(data)
            self._refresh_server_target_from_log(log_file, self._last_queue_run_session if self._last_queue_run_session >= 0 else None)
            self._suppress_completion_notify_if_tail_already_completed(log_file)
            return True
        text = read_log_file_tail_text(log_file, TAIL_BYTES)
        if text is None:
            return False
        pos, sess = parse_tail_last_queue_reading(text)
        if pos is None:
            return False
        self.graph_points.clear()
        self.current_point = None
        self.last_position = None
        self._last_queue_run_session = sess
        line_t = parse_tail_last_queue_line_epoch(text)
        self._last_queue_line_epoch = line_t
        if pos is not None and pos <= 1:
            self._position_one_reached_at = line_t or time.time()
        self.append_graph_point(pos, line_t)
        self.update_time_estimates()
        self.write_history('Graph reset to current queue position (full history unavailable from log scan).')
        self._suppress_completion_notify_if_tail_already_completed(log_file)
        return True

    def _apply_seed_result(self, data: Optional[tuple[list[tuple[float, int]], int, int, float, int, int, int, Optional[int], Optional[float], Optional[float]]]) -> None:
        if data is None:
            return
        segment_points, segment_len, positions_len, tail_mb, seg_min, seg_max, queue_run_session_id, authoritative_pos, first_le_one_epoch, connect_phase_started_epoch = data
        self._last_queue_run_session = queue_run_session_id
        self._connect_phase_started_epoch = connect_phase_started_epoch
        if authoritative_pos is not None and authoritative_pos <= 1 and (first_le_one_epoch is not None):
            self._position_one_reached_at = first_le_one_epoch
        elif authoritative_pos is not None and authoritative_pos > 1:
            self._position_one_reached_at = None
        self.graph_points.clear()
        for item in segment_points:
            self.graph_points.append(item)
        if authoritative_pos is not None and self.graph_points:
            t_last = self.graph_points[-1][0]
            self.graph_points[-1] = (t_last, authoritative_pos)
        self.current_point = self.graph_points[-1] if self.graph_points else None
        if self.current_point is not None:
            _t, pos = self.current_point
            self._last_queue_line_epoch = _t
            self.last_position = pos
            self._set_position_display(pos)
        else:
            self._last_queue_line_epoch = None
        self._pred_speed_scale = 1.0
        self._stale_slots_accounted = 0
        self._hooks.request_redraw_graph()
        self.update_time_estimates()
        self.write_history(f'Seeded graph from log: {min(segment_len, MAX_GRAPH_POINTS)} points (segment {segment_len} total, window {positions_len} total, min={seg_min}, max={seg_max}, scanned ~{tail_mb:.1f} MB).')

    def seed_graph_from_log(self, log_file: Path) -> None:
        self._apply_seed_result(compute_seed_graph_from_log(log_file))
        self._suppress_completion_notify_if_tail_already_completed(log_file)

    def poll_once(self) -> None:
        if not self.running:
            return
        try:
            self.update_time_estimates()
            resolved = resolve_log_file(self.source_path_var.get())
            if resolved is not None:
                if self.current_log_file != resolved:
                    self.current_log_file = resolved
                    self.resolved_path_var.set(str(resolved))
                    self._last_queue_run_session = -1
                    self._position_one_reached_at = None
                    self._connect_phase_started_epoch = None
                    self._progress_at_front_entry = None
                    self._left_connect_queue_detected = False
                    self._queue_completion_notified_this_run = False
                    self._last_queue_position_change_epoch = None
                    self._queue_stale_latched = False
                    self._queue_stale_logged_once = False
                    self._last_log_stat = None
                    self._last_log_growth_epoch = None
                    self._interrupted_mode = False
                    self._interrupted_elapsed_sec = None
                    self._frozen_rates_at_interrupt = None
                    self._interrupt_baseline_session = -1
                    self._dismissed_new_queue_session = None
                    self.write_history(f'Now watching: {resolved}')
            if not self.current_log_file or not self.current_log_file.is_file():
                self._set_status_line('Waiting for log file')
            else:
                self._bump_log_activity_if_changed(self.current_log_file)
                text = read_log_file_tail_text(self.current_log_file, TAIL_BYTES)
                if text is None:
                    self._set_status_line('Waiting for log file')
                elif not text.strip():
                    self._set_status_line('Log file found — waiting for data')
                else:
                    kind, _tail_pos = classify_tail_connection_state(text)
                    position, queue_sess = parse_tail_last_queue_reading(text)
                    self._refresh_server_target_from_tail_text(text, queue_sess)
                    total_queue_boundaries = count_queue_run_boundaries(text)
                    last_queue_line_epoch = parse_tail_last_queue_line_epoch(text)
                    if last_queue_line_epoch is not None:
                        self._last_queue_line_epoch = last_queue_line_epoch
                    left = tail_has_post_queue_after_last_queue_line(text)
                    now = time.time()
                    log_silent = self._last_log_growth_epoch is not None and now - self._last_log_growth_epoch >= LOG_SILENCE_RECONNECT_SEC
                    if self._interrupted_mode:
                        self._handle_interrupted_tail(position, queue_sess, last_queue_line_epoch, total_queue_boundaries, kind)
                    elif kind == 'disconnected':
                        self.enter_interrupted_state('Connection lost (final teardown).')
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        self._progress_at_front_entry = None
                        self._left_connect_queue_detected = False
                        self._position_one_reached_at = None
                        self._connect_phase_started_epoch = None
                        self._set_position_display(None)
                        self.last_position = None
                    elif self._left_connect_queue_detected and kind in ('reconnecting', 'grace'):
                        self.enter_interrupted_state('Connection lost after queue completion.')
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        self._progress_at_front_entry = None
                        self._left_connect_queue_detected = False
                        self._position_one_reached_at = None
                        self._connect_phase_started_epoch = None
                        self._set_position_display(None)
                        self.last_position = None
                    elif (kind in ('reconnecting', 'grace') or log_silent) and (not (position is not None and position <= 1)):
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        self._progress_at_front_entry = None
                        self._left_connect_queue_detected = False
                        self._position_one_reached_at = None
                        self._connect_phase_started_epoch = None
                        if log_silent or kind == 'grace':
                            self._set_status_line('Reconnecting…')
                        else:
                            self._set_status_line('Connecting…')
                        self._set_position_display(None)
                        self.last_position = None
                    elif position is not None and (not log_silent or position <= 1):
                        prev_pos = self.last_position
                        now = time.time()
                        stale_limit = QUEUE_UPDATE_INTERVAL_SEC * QUEUE_STALE_TIMEOUT_MULT
                        # A new run is normally indicated by a higher session count in the tail.
                        # If the log grew between sessions and old boundaries scrolled out of the
                        # tail window, queue_sess may appear lower; fall back to epoch comparison.
                        new_queue_run = (
                            self._last_queue_run_session >= 0
                            and (
                                queue_sess > self._last_queue_run_session
                                or (
                                    queue_sess < self._last_queue_run_session
                                    and last_queue_line_epoch is not None
                                    and self._last_queue_line_epoch is not None
                                    and last_queue_line_epoch > self._last_queue_line_epoch
                                )
                            )
                        )
                        if not new_queue_run and prev_pos is not None and (position > prev_pos) and (position - prev_pos >= QUEUE_RESET_JUMP_THRESHOLD):
                            position = prev_pos
                        if position is not None and position <= 1 and left:
                            position = 0
                        if position is not None and position > 1:
                            self._left_connect_queue_detected = False
                            self._progress_at_front_entry = None
                        elif position == 0:
                            self._left_connect_queue_detected = True
                        elif position is not None and position <= 1:
                            self._left_connect_queue_detected = False
                        if prev_pos is not None and prev_pos > 1 and (position is not None) and (position <= 1):
                            if True:
                                try:
                                    self._progress_at_front_entry = float(self._queue_progress_value)
                                except (Exception, ValueError, TypeError):
                                    self._progress_at_front_entry = 95.0
                            else:
                                self._progress_at_front_entry = 95.0
                        if self._queue_stale_latched:
                            if self._last_queue_line_epoch is not None and now - self._last_queue_line_epoch <= stale_limit:
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                            else:
                                self.enter_interrupted_state('Stale latch (queue lines did not recover).')
                        if not self._interrupted_mode:
                            if position > 1:
                                self._queue_completion_notified_this_run = False
                                if prev_pos is None or position != prev_pos:
                                    self._last_queue_position_change_epoch = now
                                    self._queue_stale_logged_once = False
                                elif self._last_queue_position_change_epoch is None:
                                    self._last_queue_position_change_epoch = now
                                if self._last_queue_line_epoch is None or now - self._last_queue_line_epoch > stale_limit:
                                    self._queue_stale_latched = True
                                    if not self._queue_stale_logged_once:
                                        self.write_history(f'No new queue log lines for {stale_limit:.0f}s ({QUEUE_STALE_TIMEOUT_MULT:.0f}× expected {QUEUE_UPDATE_INTERVAL_SEC:.0f}s updates); treating as interrupted.')
                                        self._queue_stale_logged_once = True
                                    self.enter_interrupted_state('No new queue log lines (stale).')
                            else:
                                self._last_queue_position_change_epoch = None
                                self._queue_stale_logged_once = False
                        if not self._interrupted_mode:
                            if self._last_queue_run_session >= 0 and queue_sess > self._last_queue_run_session:
                                self._alert_thresholds_fired.clear()
                                self._position_one_reached_at = None
                                self._connect_phase_started_epoch = None
                                self._queue_progress_value = 0.0
                                self._progress_at_front_entry = None
                                self._left_connect_queue_detected = False
                                self._queue_completion_notified_this_run = False
                                self._last_queue_position_change_epoch = time.time()
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                                self._mpp_floor_position = None
                                self._mpp_floor_value = None
                                self.write_history('New queue run (from log).')
                                if self.current_log_file is not None:
                                    self._reseed_graph_for_new_run(self.current_log_file)
                            self._last_queue_run_session = queue_sess
                            if position == 0:
                                self._set_status_line('Completed')
                            elif position is not None and position <= 1:
                                self._set_status_line('At front')
                            else:
                                self._set_status_line('Monitoring')
                            self._set_position_display(position)
                            if position is not None and position <= 1 and (self._position_one_reached_at is None):
                                self._position_one_reached_at = last_queue_line_epoch or now
                            # Wall-clock samples every poll so the chart shows heartbeat / flat segments, not only log-line times.
                            self.append_graph_point(position, None)
                            self.update_time_estimates()
                            if position != prev_pos:
                                self._mpp_floor_position = position
                                self._mpp_floor_value = self._minutes_per_position_from_window()
                                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                                self.last_change_var.set(timestamp)
                                if self.show_every_change_var.get():
                                    if prev_pos is None:
                                        self.write_history(f'Queue position: {position}')
                                    else:
                                        self.write_history(f'Queue changed: {prev_pos} → {position}')
                            should_alert, reason = self.compute_alert(prev_pos, position)
                            if should_alert:
                                self.raise_alert(position, reason)
                            self._maybe_notify_queue_completion(position, text)
                    else:
                        self._set_status_line('Warning: no queue detected', danger=True)
        except Exception as exc:
            self._set_status_line('Error')
            self.write_history(f'Error: {exc}')
            self.write_history(traceback.format_exc().splitlines()[-1])
        finally:
            try:
                self._refresh_warnings_kpi()
            except Exception:
                pass
            if self.running:
                self.job_id = self._hooks.schedule(int(self.poll_sec * 1000), self.poll_once)

    def append_graph_point(self, position: int, line_epoch: Optional[float]=None) -> None:
        """Append one sample to the session graph.

        ``line_epoch`` is used when seeding from a log line timestamp; ``None`` uses wall time so each
        poll adds a point (heartbeat) even when queue position is unchanged, producing a visible flat segment.
        """
        now = time.time()
        if line_epoch is not None:
            t = float(line_epoch)
        else:
            t = now
        if self.graph_points:
            last_t = self.graph_points[-1][0]
            if t <= last_t:
                t = last_t + 1e-6
        self.current_point = (t, position)
        self.last_position = position
        self._pred_speed_scale = 1.0
        self._stale_slots_accounted = 0
        self.graph_points.append(self.current_point)
        self._hooks.request_redraw_graph()

    def format_duration(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        total = int(round(seconds))
        hours = total // 3600
        minutes = total % 3600 // 60
        secs = total % 60
        if hours:
            return f'{hours:d}:{minutes:02d}:{secs:02d}'
        return f'{minutes:d}:{secs:02d}'

    def format_duration_remaining(self, seconds: float) -> str:
        """Remaining ETA with sub-second resolution so the display updates smoothly."""
        seconds = max(0.0, float(seconds))
        if seconds <= 0:
            return '—'
        if seconds < 1:
            seconds = 1.0
        if seconds >= 3600:
            total = int(round(seconds))
            hours = total // 3600
            minutes = total % 3600 // 60
            secs = total % 60
            return f'{hours:d}:{minutes:02d}:{secs:02d}'
        m = int(seconds // 60)
        s = seconds % 60.0
        return f'{m:d}:{s:05.2f}'

    @staticmethod
    def _format_queue_rate(mpp: Optional[float]) -> str:
        """Minutes per queue step for the RATE display."""
        if mpp is not None and mpp > 0:
            return f'{mpp:.2f} min/pos'
        return '—'

    def _rolling_window_points_int(self) -> int:
        """Rolling window size from Estimation → Rolling window in Settings (same cap as speed helpers)."""
        try:
            n = int(float(self.avg_window_var.get()))
        except Exception:
            n = DEFAULT_PREDICTION_WINDOW_POINTS
        return max(2, min(10000, n))

    def _refresh_kpi_rate_header(self) -> None:
        """Header shows ``RATE (Rolling N)``; N is Estimation → Rolling window in Settings."""
        lbl = getattr(self, '_lbl_kpi_rate', None)
        if lbl is None:
            return
        try:
            n = self._rolling_window_points_int()
            lbl.configure(text=f'RATE (Rolling {n})')
        except Exception:
            lbl.configure(text='RATE')

    def estimate_seconds_remaining(self) -> Optional[float]:
        current_pos = self.last_position
        if current_pos is None and self.current_point is not None:
            current_pos = self.current_point[1]
        if current_pos is None or current_pos == 0:
            return None
        if current_pos == 1:
            remaining_positions = 1
        else:
            remaining_positions = max(0, current_pos - 1)
        v_emp = self.compute_empirical_pos_per_sec()
        if v_emp is not None and v_emp > 0:
            speed = v_emp
        else:
            w, nw, _trail_w = self.compute_weighted_speed()
            if w is not None and nw > 0 and (w > 0):
                speed = w
            else:
                speed, _n, _trail = self.compute_moving_average_speed()
                if speed is None or speed <= 0:
                    if current_pos == 1:
                        return float(QUEUE_UPDATE_INTERVAL_SEC)
                    return None
        expected_sec_per_pos = 1.0 / speed
        expected_update_sec = max(QUEUE_UPDATE_INTERVAL_SEC, expected_sec_per_pos)
        if self.running and self.current_point is not None and (current_pos >= 1):
            dt = time.time() - self.current_point[0]
            if dt >= expected_update_sec:
                missed_count = int(dt / expected_update_sec)
                if missed_count > self._stale_slots_accounted:
                    extra = missed_count - self._stale_slots_accounted
                    self._pred_speed_scale *= 0.92 ** extra
                    self._pred_speed_scale = max(0.05, self._pred_speed_scale)
                    self._stale_slots_accounted = missed_count
            else:
                self._stale_slots_accounted = 0
            v_eff = speed * self._pred_speed_scale
            base = remaining_positions / v_eff
            return max(1.0, base - dt)
        v_eff = speed * self._pred_speed_scale
        return remaining_positions / v_eff

    def compute_moving_average_speed(self) -> tuple[Optional[float], int, list[int]]:
        points = list(self.graph_points)
        if len(points) < 2:
            return (None, 0, [p for _t, p in points])
        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10000, window_points))
        recent = points[-(window_points + 1):]
        trail = [p for _t, p in recent]
        rates: list[float] = []
        for (t0, p0), (t1, p1) in zip(recent, recent[1:]):
            dt = t1 - t0
            if dt <= 0:
                continue
            improvement = p0 - p1
            if improvement <= 0:
                continue
            rates.append(improvement / dt)
        if len(rates) == 0:
            return (None, 0, trail)
        if len(rates) < 3:
            speed = sum(rates) / len(rates)
            if speed <= 0:
                return (None, 0, trail)
            return (speed, len(rates), trail)
        rates.sort()
        speed = rates[len(rates) // 2]
        if speed <= 0:
            return (None, 0, trail)
        return (speed, len(rates), trail)

    def compute_weighted_speed(self) -> tuple[Optional[float], int, list[int]]:
        """Recency-weighted mean of segment rates; shifts as wall time passes while still in queue.

        At **position 0** (queue finished in the log), weights use the last sample time so the
        value does not drift after completion.
        """
        points = list(self.graph_points)
        if len(points) < 2:
            return (None, 0, [p for _t, p in points])
        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10000, window_points))
        recent = points[-(window_points + 1):]
        trail = [p for _t, p in recent]
        now = time.time()
        if self._current_queue_position() == 0 and len(recent) >= 2:
            now = float(recent[-1][0])
        w_sum = 0.0
        r_sum = 0.0
        n_seg = 0
        for (t0, p0), (t1, p1) in zip(recent, recent[1:]):
            dt_seg = t1 - t0
            if dt_seg <= 0:
                continue
            improvement = p0 - p1
            if improvement <= 0:
                continue
            rate = improvement / dt_seg
            w = math.exp(-max(0.0, now - t1) / SPEED_WEIGHT_TAU_SEC)
            w_sum += w
            r_sum += rate * w
            n_seg += 1
        if w_sum <= 0 or n_seg < 1:
            return (None, 0, trail)
        speed = r_sum / w_sum
        if speed <= 0:
            return (None, 0, trail)
        return (speed, n_seg, trail)

    def _window_recent_points(self) -> list[tuple[float, int]]:
        """Last N graph points per rolling window setting (same slice as speed helpers)."""
        points = list(self.graph_points)
        if len(points) < 2:
            return []
        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10000, window_points))
        return points[-(window_points + 1):]

    def compute_empirical_pos_per_sec(self) -> Optional[float]:
        """Net positions per second over the rolling window.

        While monitoring **and still in queue** (position not 0), time uses wall clock from the
        window's first point to *now*, so dwell at the current queue position (including
        position 1 before connect) is not dropped from the average. **Position 0** (completed)
        and stopped mode use only log timestamps between window endpoints so the rate stays fixed.
        """
        recent = self._window_recent_points()
        if len(recent) < 2:
            return None
        t0, p0 = (float(recent[0][0]), float(recent[0][1]))
        t1, p1 = (float(recent[-1][0]), float(recent[-1][1]))
        drop = p0 - p1
        if drop <= 0:
            return None
        pos = self._current_queue_position()
        if self.running and pos != 0:
            dt = time.time() - t0
        else:
            dt = t1 - t0
        if dt <= 0:
            return None
        return drop / dt

    def _minutes_per_position_from_window(self) -> Optional[float]:
        """Minutes per position: prefer empirical throughput over the window; else model fallback."""
        v_emp = self.compute_empirical_pos_per_sec()
        if v_emp is not None and v_emp > 0:
            return 1.0 / (v_emp * 60.0)
        w, nw, _trail_w = self.compute_weighted_speed()
        if w is not None and nw > 0 and (w > 0):
            v = w * self._pred_speed_scale
        else:
            speed, n, _trail = self.compute_moving_average_speed()
            if speed is None or n <= 0 or speed <= 0:
                return None
            v = speed * self._pred_speed_scale
        if v <= 0:
            return None
        return 1.0 / (v * 60.0)

    def _minutes_per_position_capped_for_dwell(self, mpp_raw: Optional[float], pos: Optional[int]) -> Optional[float]:
        """Do not allow minutes/position to *rise* until expected time for this position already elapsed."""
        if mpp_raw is None or pos is None or pos <= 1:
            return mpp_raw
        if self._mpp_floor_position != pos or self._mpp_floor_value is None or self._mpp_floor_value <= 0:
            return mpp_raw
        if mpp_raw <= self._mpp_floor_value:
            return mpp_raw
        if self._last_queue_position_change_epoch is None:
            return self._mpp_floor_value
        dwell = max(0.0, time.time() - self._last_queue_position_change_epoch)
        if dwell < self._mpp_floor_value * 60.0:
            return self._mpp_floor_value
        return mpp_raw

    def _global_avg_minutes_per_position(self) -> Optional[float]:
        """Mean minutes/position over every forward (downward) step in the full graph — all segments, all slots."""
        pts = list(self.graph_points)
        if len(pts) < 2:
            return None
        mpps: list[float] = []
        for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
            dt = float(t1) - float(t0)
            if dt <= 0:
                continue
            improvement = int(p0) - int(p1)
            if improvement <= 0:
                continue
            mpp = dt / 60.0 / float(improvement)
            if mpp > 0 and math.isfinite(mpp):
                mpps.append(mpp)
        if not mpps:
            return None
        return sum(mpps) / len(mpps)

    def _refresh_queue_and_global_rate(self, pos: Optional[int]) -> Optional[float]:
        """KPI Rate value + Global Rate in Info. Header shows RATE (Rolling N). Returns capped mpp for ETA."""
        mpp_raw = self._minutes_per_position_from_window()
        mpp = self._minutes_per_position_capped_for_dwell(mpp_raw, pos)
        g_mpp = self._global_avg_minutes_per_position()
        self.queue_rate_var.set(self._format_queue_rate(mpp))
        self.global_rate_var.set(self._format_queue_rate(g_mpp))
        return mpp

    def _current_queue_position(self) -> Optional[int]:
        pos = self.last_position
        if pos is None and self.current_point is not None:
            pos = self.current_point[1]
        return pos

    def _queue_elapsed_start_epoch(self) -> Optional[float]:
        """Start of the current queue segment for elapsed: first connect line in log, else first graph point."""
        if self._connect_phase_started_epoch is not None:
            return self._connect_phase_started_epoch
        if self.graph_points:
            return self.graph_points[0][0]
        return self.monitor_start_epoch

    def _snapshot_elapsed_seconds_at_interrupt(self) -> Optional[float]:
        """Freeze queue elapsed at the last real queue sample when entering Interrupted."""
        start_t = self._queue_elapsed_start_epoch()
        if start_t is None:
            return None
        pos = self._current_queue_position()
        if pos is not None and pos <= 1 and (self._position_one_reached_at is not None):
            return max(0.0, self._position_one_reached_at - start_t)
        if self.current_point is not None:
            return max(0.0, self.current_point[0] - start_t)
        return max(0.0, time.time() - start_t)

    def _sync_queue_progress_widget(self) -> None:
        """Progress value is exposed via WebSocket snapshot; no desktop widget."""
        return

    def update_time_estimates(self) -> None:
        self._refresh_kpi_rate_header()
        points = list(self.graph_points)
        pos = self._current_queue_position()
        if self._interrupted_elapsed_sec is not None:
            elapsed_sec = self._interrupted_elapsed_sec
            self.elapsed_var.set(self.format_duration(elapsed_sec))
            self.predicted_remaining_var.set('—')
            if self._frozen_rates_at_interrupt is not None:
                self.queue_rate_var.set(self._frozen_rates_at_interrupt[0])
                self.global_rate_var.set(self._frozen_rates_at_interrupt[1])
            else:
                self._refresh_queue_and_global_rate(pos)
            if pos is not None and len(points) >= 1:
                start_pos = points[0][1]
                if start_pos > 0 and pos <= start_pos:
                    self._queue_progress_value = min(100.0, max(0.0, 100.0 * (start_pos - pos) / start_pos))
                else:
                    self._queue_progress_value = 0.0
            else:
                self._queue_progress_value = 0.0
            self._sync_queue_progress_widget()
            return
        if self.running and pos is not None and (pos > 1):
            self._position_one_reached_at = None
        start_t = self._queue_elapsed_start_epoch()
        elapsed_sec: Optional[float] = None
        if self.running and self.monitor_start_epoch is not None:
            if start_t is None:
                self.elapsed_var.set('—')
            elif pos is not None and pos <= 1 and (self._position_one_reached_at is not None):
                elapsed_sec = max(0.0, self._position_one_reached_at - start_t)
                self.elapsed_var.set(self.format_duration(elapsed_sec))
            else:
                elapsed_sec = max(0.0, time.time() - start_t)
                self.elapsed_var.set(self.format_duration(elapsed_sec))
        elif not self.running and self._position_one_reached_at is not None and (len(points) >= 1):
            st = points[0][0]
            elapsed_sec = max(0.0, self._position_one_reached_at - st)
            self.elapsed_var.set(self.format_duration(elapsed_sec))
        elif len(points) >= 2:
            start_t2 = points[0][0]
            end_t = self.current_point[0] if self.current_point is not None else points[-1][0]
            elapsed_sec = max(0.0, end_t - start_t2)
            self.elapsed_var.set(self.format_duration(elapsed_sec))
        else:
            self.elapsed_var.set('—')
        mpp = self._refresh_queue_and_global_rate(pos)
        seconds_remaining = self.estimate_seconds_remaining()
        if seconds_remaining is None and pos is not None and (mpp is not None) and (mpp > 0):
            if pos > 1:
                seconds_remaining = max(0.0, float(pos - 1) * mpp * 60.0)
            elif pos == 1:
                seconds_remaining = max(0.0, float(mpp) * 60.0)
        if seconds_remaining is None:
            self.predicted_remaining_var.set('—')
        else:
            self.predicted_remaining_var.set(self.format_duration_remaining(seconds_remaining))
        if True:
            _prev_progress = self._queue_progress_value
            if pos is not None and pos <= 1:
                if self._left_connect_queue_detected:
                    self._queue_progress_value = 100.0
                else:
                    base = self._progress_at_front_entry
                    if base is None:
                        base = 90.0
                    self._queue_progress_value = min(99.0, base)
            elif elapsed_sec is not None and seconds_remaining is not None:
                total = elapsed_sec + max(0.0, float(seconds_remaining))
                if total > 1e-06:
                    p = min(100.0, max(0.0, 100.0 * elapsed_sec / total))
                    # Clamp: ETA fluctuations must not make the bar go backwards.
                    self._queue_progress_value = max(_prev_progress, p)
                else:
                    self._queue_progress_value = 0.0
            elif pos is not None and len(points) >= 1:
                start_pos = points[0][1]
                if start_pos > 0 and pos <= start_pos:
                    self._queue_progress_value = min(100.0, max(0.0, 100.0 * (start_pos - pos) / start_pos))
                else:
                    self._queue_progress_value = 0.0
            else:
                self._queue_progress_value = 0.0
        self._sync_queue_progress_widget()

    def compute_alert(self, prev_pos: Optional[int], curr_pos: int) -> tuple[bool, str]:
        """Alert once per CSV threshold when crossing downward (e.g. first time at ≤10, then ≤5, …).

        Fired thresholds also reset when poll_once detects a new queue run from log boundary lines.
        Remaining resets: large upward jump (or marginal +10 from front — see code), not small bumps.
        """
        try:
            thresholds = parse_alert_thresholds(self.alert_thresholds_var.get())
        except ValueError:
            return (False, '')
        if prev_pos is None:
            return (False, '')
        if prev_pos <= 1 and curr_pos <= 1:
            return (False, '')
        jump_up = curr_pos - prev_pos
        if jump_up >= QUEUE_RESET_JUMP_THRESHOLD:
            marginal_spike_from_front = prev_pos <= 1 and jump_up == QUEUE_RESET_JUMP_THRESHOLD
            if not marginal_spike_from_front:
                self._alert_thresholds_fired.clear()
        crossed: list[int] = []
        for t in thresholds:
            if prev_pos > t and curr_pos <= t and (t not in self._alert_thresholds_fired):
                crossed.append(t)
                self._alert_thresholds_fired.add(t)
        if not crossed:
            return (False, '')
        crossed.sort(reverse=True)
        parts = ', '.join((str(x) for x in crossed))
        return (True, f'crossed threshold(s): {parts}')

    def raise_alert(self, position: int, reason: str) -> None:
        now = time.time()
        if self.last_alert_epoch > 0.0 and now - self.last_alert_epoch < ALERT_MIN_INTERVAL_SEC:
            return
        self.last_alert_position = position
        self.last_alert_epoch = now
        self.last_alert_var.set(time.strftime('%Y-%m-%d %H:%M:%S'))
        self.last_alert_message_var.set(f"Threshold alert: position {position} ({reason})")
        self._last_alert_seq += 1
        sec_rem = self.estimate_seconds_remaining()
        eta_display = self.format_duration_remaining(sec_rem) if sec_rem is not None else '—'
        hist_extra = f'; remaining {eta_display}' if sec_rem is not None else ''
        self.write_history(f'Threshold alert: position {position} ({reason}){hist_extra}')
        if self.sound_enabled_var.get():
            self.play_sound()
        if self.popup_enabled_var.get():
            self._hooks.show_threshold_popup(position, eta_display)
            self._emit_push_notification(
                "warning",
                {
                    "title": "Threshold alert",
                    "body": f"Threshold alert: position {position} ({reason})\nEstimated remaining: {eta_display}\nStatus: {self.status_var.get() or 'Monitoring'}",
                    "tag": f"vsqm-threshold-{self._last_alert_seq}",
                    "kind": "warning",
                    "renotify": True,
                },
            )

    def play_sound(self) -> None:
        """Threshold / warning alert sound."""
        raw = (self.alert_sound_path_var.get() or '').strip()
        if raw:
            p = expand_path(raw)
            if p.is_file() and play_alert_sound_file(p):
                return
        if play_default_system_alert_sound():
            return
        try:
            self._hooks.bell()
        except Exception:
            pass

    def play_completion_sound(self) -> None:
        """Completion sound when the log shows past queue wait (see POST_QUEUE_PROGRESS_LINE_RES)."""
        raw = (self.completion_sound_path_var.get() or '').strip()
        if raw:
            p = expand_path(raw)
            if p.is_file() and play_alert_sound_file(p):
                return
        if play_default_completion_system_sound():
            return
        try:
            self._hooks.bell()
        except Exception:
            pass

    def play_failure_sound(self) -> None:
        """Interrupted/failure sound when queue monitoring drops out of the active queue flow."""
        raw = (self.failure_sound_path_var.get() or '').strip()
        if raw:
            p = expand_path(raw)
            if p.is_file() and play_alert_sound_file(p):
                return
        if play_default_failure_system_sound():
            return
        try:
            self._hooks.bell()
        except Exception:
            pass

    def _maybe_notify_queue_completion(self, position: int, tail_text: str) -> None:
        """Optional sound/popup when we map to position 0 (past queue wait — see POST_QUEUE_PROGRESS_LINE_RES)."""
        if position != 0:
            return
        if not tail_has_post_queue_after_last_queue_line(tail_text):
            return
        if self._queue_completion_notified_this_run:
            return
        now = time.time()
        if self._last_queue_completion_notify_epoch > 0.0 and now - self._last_queue_completion_notify_epoch < COMPLETION_NOTIFY_MIN_INTERVAL_SEC:
            return
        want_sound = bool(self.completion_sound_enabled_var.get())
        want_popup = bool(self.completion_popup_enabled_var.get())
        if not want_sound and (not want_popup):
            return
        self._queue_completion_notified_this_run = True
        self._last_queue_completion_notify_epoch = now
        self.write_history('Queue completion: past queue wait — connecting (position 0).')
        if want_sound:
            self.play_completion_sound()
        if want_popup:
            self._hooks.show_completion_popup()
            self._emit_push_notification(
                "completion",
                {
                    "title": "Queue completion",
                    "body": f"Queue completion: past queue wait — connecting (position 0).\nStatus: {self.status_var.get() or 'Connecting'}",
                    "tag": f"vsqm-completion-{int(now * 1000)}",
                    "kind": "completion",
                    "renotify": True,
                },
            )
