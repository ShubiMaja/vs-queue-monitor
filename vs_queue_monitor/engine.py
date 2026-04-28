"""Headless queue monitor logic. Used by the local web UI (``vs_queue_monitor.web``)."""

from __future__ import annotations

import json
import math
import re
import subprocess
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
    # Serializes JSONL writes across all backfill threads so concurrent log-switches
    # cannot race to append duplicates before any thread has finished writing.
    _backfill_lock = threading.Lock()

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
        self.hist_global_rate_var = hooks.string_var("—")
        self.show_log_var = hooks.boolean_var(bool(self.config.get("show_log", True)))
        self.show_status_var = hooks.boolean_var(bool(self.config.get("show_status", True)))
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
        self._session_start_epoch: Optional[float] = None
        self._session_start_position: Optional[int] = None
        self._session_record_written: bool = False
        self._last_progress_write: float = 0.0
        _hp = self.config.get("history_path", "")
        self.history_path_var = hooks.string_var(str(_hp).strip() if _hp else "")
        self._history_sessions_cache: Optional[tuple[str, float, list[dict]]] = None

        self.avg_window_var.trace_add("write", self._on_avg_window_write)
        self.show_log_var.trace_add("write", self._schedule_config_persist)
        self.show_status_var.trace_add("write", self._schedule_config_persist)
        self._bind_config_persist_traces()
        self._migrate_session_history()
        self._recover_crashed_session()
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
        return {'source_path': self.source_path_var.get(), 'alert_thresholds': self.alert_thresholds_var.get(), 'poll_sec': self.poll_sec_var.get(), 'avg_window_points': self.avg_window_var.get(), 'show_log': bool(self.show_log_var.get()), 'show_status': bool(self.show_status_var.get()), 'popup_enabled': bool(self.popup_enabled_var.get()), 'sound_enabled': bool(self.sound_enabled_var.get()), 'alert_sound_path': self.alert_sound_path_var.get().strip(), 'completion_popup_enabled': bool(self.completion_popup_enabled_var.get()), 'completion_sound_enabled': bool(self.completion_sound_enabled_var.get()), 'completion_sound_path': self.completion_sound_path_var.get().strip(), 'failure_popup_enabled': bool(self.failure_popup_enabled_var.get()), 'failure_sound_enabled': bool(self.failure_sound_enabled_var.get()), 'failure_sound_path': self.failure_sound_path_var.get().strip(), 'show_every_change': bool(self.show_every_change_var.get()), 'tutorial_done': bool(self.tutorial_done_var.get()), 'history_path': self.history_path_var.get().strip(), 'window_geometry': self._hooks.window_geometry_for_save(), 'version': VERSION}

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
        for var in (self.source_path_var, self.alert_thresholds_var, self.poll_sec_var, self.avg_window_var, self.show_log_var, self.show_status_var, self.popup_enabled_var, self.sound_enabled_var, self.alert_sound_path_var, self.completion_popup_enabled_var, self.completion_sound_enabled_var, self.completion_sound_path_var, self.failure_popup_enabled_var, self.failure_sound_enabled_var, self.failure_sound_path_var, self.show_every_change_var, self.tutorial_done_var, self.history_path_var):
            var.trace_add('write', self._schedule_config_persist)

    def reset_defaults(self) -> None:
        self.stop_monitoring()
        self.source_path_var.set(DEFAULT_PATH)
        self.alert_thresholds_var.set(DEFAULT_ALERT_THRESHOLDS)
        self.poll_sec_var.set('2')
        self.avg_window_var.set(str(DEFAULT_PREDICTION_WINDOW_POINTS))
        self.show_log_var.set(True)
        self.show_status_var.set(True)
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
        tail_text = read_log_file_tail_text(log_file, TAIL_BYTES)
        target = parse_tail_latest_connect_target(tail_text or "", session_id)
        if target is None and TAIL_BYTES < SEED_LOG_TAIL_BYTES:
            seed_text = read_log_file_tail_text(log_file, SEED_LOG_TAIL_BYTES)
            target = parse_tail_latest_connect_target(seed_text or "", session_id)
        if target:
            self.server_target_var.set(target)

    def _refresh_warnings_kpi(self) -> None:
        """Warnings rail is driven by the web snapshot; no desktop widgets to refresh."""
        return

    def _try_start_after_browse(self) -> None:
        if self._starting:
            return
        if self.running:
            self.stop_monitoring(folder_switch=True)
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
        self._session_start_epoch = None
        self._session_start_position = None
        self._session_record_written = False
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
        # Write an immediate in_progress record for active seeded sessions so cross-folder
        # views can see them before the 30 s throttle fires.  Interrupted sessions are
        # already handled by _write_seeded_session_discovery inside _adopt_interrupted_tail_on_start.
        if not self._interrupted_mode and self._last_queue_run_session >= 0 and self.graph_points:
            self._write_session_progress(force=True)
        threading.Thread(target=lambda: self._backfill_sessions_from_log(resolved), daemon=True).start()
        threading.Thread(target=self._backfill_other_known_log_files, daemon=True).start()
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
            self._write_seeded_session_discovery()

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
        self._write_session_record("interrupted")
        msg = 'Queue interrupted; still watching the log. A new queue run can be loaded when detected.'
        if detail:
            msg += f' ({detail})'
        self.write_history(msg)
        want_failure_popup = bool(self.failure_popup_enabled_var.get())
        want_web_failure_event = bool(getattr(self._hooks, "browser_client_notifications", False))
        if want_failure_popup or want_web_failure_event:
            self._hooks.show_failure_popup(detail)
        if want_failure_popup:
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

    @staticmethod
    def _normalize_log_path_for_dedup(p: str) -> str:
        return normalize_log_path_for_dedup(p)

    def _backfill_sessions_from_log(self, log_file: Path, _source_path_override: Optional[str] = None, include_active: bool = False) -> None:
        """Write history records for past sessions in the log not already in session_history.jsonl."""
        try:
            source_path = _source_path_override if _source_path_override is not None else str(self.config.get("source_path", "") or "")
            records = extract_all_session_records_from_log(
                log_file,
                source_path=source_path,
                vsqm_version=VERSION,
                include_active=include_active,
            )
            if not records:
                return
            hist = self._effective_history_path()
            norm_log_file = self._normalize_log_path_for_dedup(str(log_file))
            stored_log_file = normalize_log_path_for_storage(str(log_file))
            # Serialize the read-check-write block so concurrent backfill threads
            # (triggered by rapid log-folder switches) cannot all read the same
            # pre-write JSONL and then each append the same session records.
            with QueueMonitorEngine._backfill_lock:
                # Track the best outcome rank seen per key so backfill can upgrade
                # discovery records (e.g. "interrupted") to terminal records ("completed").
                # "completed with point-0" (rank 5) beats "completed without point-0" (rank 4)
                # so that old records written before position-0 tracking was added get upgraded.
                def _bfrank(rec: dict) -> int:
                    base = {"completed": 4, "unknown": 3, "interrupted": 2, "abandoned": 1, "crashed": 0, "in_progress": -1}
                    rnk = base.get(rec.get("outcome") or "", -1)
                    if rnk == 4:  # completed
                        pts = rec.get("points") or []
                        if pts and int(pts[-1][1]) == 0:
                            rnk = 5  # completed + has point-0
                    return rnk
                existing_sid: dict[tuple[str, int, int], int] = {}  # key → best rank
                existing_sig: dict[tuple[str, int, Any], int] = {}
                try:
                    if hist.exists():
                        for line in hist.read_text(encoding="utf-8").splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                rec = json.loads(line)
                                lf = self._normalize_log_path_for_dedup(str(rec.get("log_file", "")))
                                sid = rec.get("session_id")
                                se = rec.get("start_epoch")
                                sp = rec.get("start_position")
                                rnk = _bfrank(rec)
                                if lf and sid is not None and se is not None:
                                    k = (lf, int(sid), int(se))
                                    existing_sid[k] = max(existing_sid.get(k, -2), rnk)
                                if lf and se is not None:
                                    k2 = (lf, int(se), sp)
                                    existing_sig[k2] = max(existing_sig.get(k2, -2), rnk)
                            except Exception:
                                pass
                except Exception:
                    pass
                to_write = [
                    r for r in records
                    if _bfrank(r) > existing_sid.get((norm_log_file, r["session_id"], int(r.get("start_epoch") or 0)), -2)
                    and _bfrank(r) > existing_sig.get((norm_log_file, int(r.get("start_epoch") or 0), r.get("start_position")), -2)
                ]
                if not to_write:
                    return
                hist.parent.mkdir(parents=True, exist_ok=True)
                with open(hist, "a", encoding="utf-8") as fh:
                    for r in to_write:
                        r_stored = dict(r)
                        r_stored["log_file"] = stored_log_file
                        fh.write(json.dumps(r_stored) + "\n")
            self._invalidate_history_cache()
        except Exception:
            pass

    def _backfill_other_known_log_files(self) -> None:
        """Backfill sessions from log files referenced in JSONL history that we aren't monitoring now.

        Runs on a background thread at startup so that cross-folder session records remain
        up-to-date even when the user's current folder view differs from where the sessions
        were recorded.  Uses the source_path already stored in JSONL for each foreign log
        so that the attribution in the Path field stays correct.
        """
        try:
            current_norm = normalize_log_path_for_dedup(str(self.current_log_file)) if self.current_log_file else ""
            hist = self._effective_history_path()
            if not hist.exists():
                return
            foreign: dict[str, tuple[str, str]] = {}  # norm_path → (stored_lf_token, source_path)
            try:
                for line in hist.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        raw_lf = str(rec.get("log_file") or "")
                        if not raw_lf:
                            continue
                        norm = normalize_log_path_for_dedup(raw_lf)
                        if norm == current_norm or norm in foreign:
                            continue
                        sp = str(rec.get("source_path") or "")
                        foreign[norm] = (raw_lf, sp)
                    except Exception:
                        pass
            except Exception:
                return
            for norm, (raw_lf, source_path) in foreign.items():
                try:
                    lf_path = Path(normalize_log_path_for_dedup(raw_lf))
                    if not lf_path.is_file():
                        continue
                    # include_active=True: also emit an in_progress record for the last
                    # (potentially still-live) session so cross-folder views see it without
                    # the user having to visit that folder.
                    self._backfill_sessions_from_log(lf_path, source_path, include_active=True)
                except Exception:
                    pass
        except Exception:
            pass

    def load_history_sessions(self) -> list[dict]:
        """Return parsed session_history.jsonl records, cached for 30 s."""
        now = time.time()
        hist = self._effective_history_path()
        hist_key = str(hist.resolve()) if hist.exists() else str(hist)
        if self._history_sessions_cache is not None:
            cached_key, cached_at, records = self._history_sessions_cache
            if cached_key == hist_key and now - cached_at < 30.0:
                return records
        records = []
        try:
            if hist.exists():
                for line in hist.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass
        self._history_sessions_cache = (hist_key, now, records)
        return records

    def _invalidate_history_cache(self) -> None:
        self._history_sessions_cache = None

    def _effective_history_path(self) -> Path:
        raw = (self.history_path_var.get() or "").strip()
        if raw:
            return Path(raw) / "session_history.jsonl"
        return get_history_path()

    def _effective_checkpoint_path(self) -> Path:
        raw = (self.history_path_var.get() or "").strip()
        if raw:
            return Path(raw) / "current_session.json"
        return get_checkpoint_path()

    _MIGRATION_DEDUP_PATHS = "dedup_paths_v1"
    _MIGRATION_NORMALIZE_PATHS = "normalize_paths_v1"

    def _migrate_session_history(self) -> None:
        """Run one-time JSONL migrations gated by markers in config["migrations_done"]."""
        try:
            done: list = list(self.config.get("migrations_done") or [])
            dirty = False

            # --- Migration 1: dedup records with path-format mismatches ---
            if self._MIGRATION_DEDUP_PATHS not in done:
                hist = self._effective_history_path()
                if hist.exists():
                    lines = hist.read_text(encoding="utf-8").splitlines()
                    records = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except Exception:
                            pass

                    if records:
                        outcome_rank = {"completed": 4, "unknown": 3, "interrupted": 2, "abandoned": 1, "crashed": 0}

                        def _rank(rec: dict) -> tuple:
                            pts = rec.get("points") or []
                            return (outcome_rank.get(rec.get("outcome", ""), -1), len(pts))

                        primary: dict[tuple[str, int], dict] = {}
                        no_id: list[dict] = []
                        for rec in records:
                            sid = rec.get("session_id")
                            lf = self._normalize_log_path_for_dedup(str(rec.get("log_file") or ""))
                            if sid is not None:
                                pk = (lf, int(sid))
                                prev = primary.get(pk)
                                if prev is None or _rank(rec) > _rank(prev):
                                    primary[pk] = rec
                            else:
                                no_id.append(rec)

                        deduped = list(primary.values()) + no_id
                        if len(deduped) < len(records):
                            deduped.sort(key=lambda r: float(r.get("start_epoch") or 0))
                            hist.write_text("\n".join(json.dumps(r) for r in deduped) + "\n", encoding="utf-8")
                            self._invalidate_history_cache()

                done.append(self._MIGRATION_DEDUP_PATHS)
                dirty = True

            # --- Migration 2: normalize log_file paths to portable tokens ---
            if self._MIGRATION_NORMALIZE_PATHS not in done:
                hist = self._effective_history_path()
                if hist.exists():
                    lines = hist.read_text(encoding="utf-8").splitlines()
                    records = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except Exception:
                            pass

                    if records:
                        changed = False
                        normalized: list[dict] = []
                        for rec in records:
                            raw_lf = str(rec.get("log_file") or "")
                            normed = normalize_log_path_for_storage(raw_lf)
                            if normed != raw_lf:
                                rec = dict(rec)
                                rec["log_file"] = normed
                                changed = True
                            normalized.append(rec)
                        if changed:
                            hist.write_text(
                                "\n".join(json.dumps(r) for r in normalized) + "\n", encoding="utf-8"
                            )
                            self._invalidate_history_cache()

                done.append(self._MIGRATION_NORMALIZE_PATHS)
                dirty = True

            if dirty:
                self.config["migrations_done"] = done
                save_config(self.config)
        except Exception:
            pass

    def _recover_crashed_session(self) -> None:
        """On startup, recover any session left behind by a hard crash."""
        try:
            cp = self._effective_checkpoint_path()
            if not cp.exists():
                return
            data = json.loads(cp.read_text(encoding="utf-8"))
            # If the checkpoint was written by a different engine (different source_path),
            # we never witnessed it crash — keep it as "in_progress" so it shows ? and
            # remains visible, rather than stamping it crashed (✕) or unknown (which can
            # be collided away by adjacent backfill records and disappear entirely).
            my_sp = normalize_log_path_for_dedup(str(self.config.get("source_path", "") or ""))
            cp_sp = normalize_log_path_for_dedup(str(data.get("source_path", "") or ""))
            data["outcome"] = "crashed" if (not cp_sp or cp_sp == my_sp) else "in_progress"
            hist = self._effective_history_path()
            hist.parent.mkdir(parents=True, exist_ok=True)
            with open(hist, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(data) + "\n")
            cp.unlink(missing_ok=True)
        except Exception:
            try:
                self._effective_checkpoint_path().unlink(missing_ok=True)
            except Exception:
                pass

    def _build_session_record(self, outcome: str) -> dict:
        """Build the session record dict (shared by checkpoint and final write)."""
        pts = list(self.graph_points)
        change_pts: list[tuple[float, int]] = []
        last_pos: Optional[int] = None
        for t, p in pts:
            if p != last_pos:
                change_pts.append((t, p))
                last_pos = p
        start_epoch = self._session_start_epoch or (pts[0][0] if pts else time.time())
        server = self.server_target_var.get()
        raw_lf = str(self.current_log_file) if self.current_log_file else None
        return {
            "session_id": self._last_queue_run_session,
            "source_path": str(self.config.get("source_path", "") or ""),
            "log_file": normalize_log_path_for_storage(raw_lf) if raw_lf else None,
            "server": server if server and server != "—" else None,
            "start_epoch": start_epoch,
            "end_epoch": time.time(),
            "outcome": outcome,
            "start_position": self._session_start_position,
            "end_position": self.last_position,
            "points": change_pts,
            "vsqm_version": VERSION,
        }

    def _checkpoint_session(self) -> None:
        """Overwrite current_session.json with live session state (crash recovery)."""
        try:
            record = self._build_session_record("in_progress")
            path = self._effective_checkpoint_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record), encoding="utf-8")
        except Exception:
            pass

    def _write_session_record(self, outcome: str) -> None:
        """Append one completed/interrupted session record to session_history.jsonl."""
        if self._session_record_written:
            return
        try:
            record = self._build_session_record(outcome)
            path = self._effective_history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            self._session_record_written = True
            self._invalidate_history_cache()
        except Exception:
            pass
        try:
            self._effective_checkpoint_path().unlink(missing_ok=True)
        except Exception:
            pass

    def _write_seeded_session_discovery(self) -> None:
        """Append a cross-folder discovery record without setting _session_record_written.

        Called when adopting a seeded-interrupted session at startup.  Ensures the session
        is visible in other folder views regardless of the 100 MB backfill cap, while
        leaving _session_record_written=False so future terminal writes (completed, etc.)
        can still fire for the same monitoring lifetime.
        """
        if self._last_queue_run_session < 0 or not self.graph_points:
            return
        try:
            record = self._build_session_record("interrupted")
            path = self._effective_history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            self._invalidate_history_cache()
        except Exception:
            pass

    _PROGRESS_WRITE_INTERVAL = 30.0  # seconds between in-progress JSONL writes

    def _write_session_progress(self, *, force: bool = False) -> None:
        """Append an in-progress snapshot to JSONL so other folder views see live progress.

        Throttled to at most once per _PROGRESS_WRITE_INTERVAL seconds.  Pass force=True
        to bypass the throttle (e.g. on folder switch, to guarantee at least one record
        exists even if the session just started).  The final _write_session_record call
        supersedes these via server-side Pass A dedup (completed/interrupted rank higher).
        """
        if self._session_record_written:
            return
        if self._last_queue_run_session < 0 or not self.graph_points:
            return
        now = time.time()
        if not force and now - self._last_progress_write < self._PROGRESS_WRITE_INTERVAL:
            return
        try:
            record = self._build_session_record("in_progress")
            path = self._effective_history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            self._last_progress_write = now
            self._invalidate_history_cache()
        except Exception:
            pass

    def _handle_interrupted_tail(self, position: Optional[int], queue_sess: int, last_queue_line_epoch: Optional[float] = None, total_queue_boundaries: Optional[int] = None, kind: str = '', left: bool = False) -> None:
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
        # If the queue already completed (post-queue lines present after the last queue line),
        # don't offer to adopt — the run already ended.
        if left and position is not None and position <= 1:
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
            self._set_status_line('⚠ No Queue!', danger=True)
            self.graph_points.clear()
            self.current_point = None
            self.last_position = None
            self._set_position_display(None)
            self._hooks.request_redraw_graph()

    def stop_monitoring(self, *, folder_switch: bool = False) -> None:
        # Skip the abandoned write for interrupted sessions: enter_interrupted_state already
        # wrote "interrupted" (live case, _session_record_written=True → no-op anyway), and
        # for seeded-interrupted sessions _adopt_interrupted_tail_on_start deliberately skips
        # the write so the backfill can record the correct terminal outcome.
        #
        # On a folder switch the game session may still be live; write a forced in_progress
        # snapshot (bypassing the 30 s throttle) so cross-folder views can see the session
        # as Unknown (?).  Writing abandoned would show it as dead; writing nothing at all
        # would make it invisible if the throttle hasn't fired yet in this session.
        # The backfill below still captures completed outcomes from the full log scan.
        if self._last_queue_run_session >= 0 and self.graph_points and not self._interrupted_mode:
            if folder_switch:
                self._write_session_progress(force=True)
            else:
                self._write_session_record("abandoned")
        # Backfill the log being stopped so completed sessions are captured in the
        # global JSONL before we switch to a different folder.  This ensures
        # cross-folder history survives a folder switch even if the sessions were
        # never individually written (e.g. the app was opened after they completed).
        if self.current_log_file is not None and self.current_log_file.is_file():
            _log_to_backfill = self.current_log_file
            threading.Thread(
                target=lambda: self._backfill_sessions_from_log(_log_to_backfill),
                daemon=True,
            ).start()
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
        # Store the true session start BEFORE the deque truncates segment_points to MAX_GRAPH_POINTS.
        # Without this, _build_session_record falls back to graph_points[0][0] which is a
        # mid-session timestamp, causing epoch mismatches in JSONL dedup.
        if segment_points:
            self._session_start_epoch = segment_points[0][0]
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
        # Seed last_change_var from the last position-change in the graph so
        # "Last change" is not stuck at — after a restart on a completed run.
        _lc_t: Optional[float] = None
        _lc_prev: Optional[int] = None
        for _pt, _pp in self.graph_points:
            if _pp != _lc_prev:
                _lc_t = _pt
                _lc_prev = _pp
        if _lc_t is not None:
            self.last_change_var.set(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_lc_t)))
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
                    # Finalize the old session before switching log files.
                    if self._last_queue_run_session >= 0 and self.graph_points and not self._session_record_written:
                        self._write_session_record("unknown")
                    # Reset session tracking so the new file's sessions can be recorded.
                    self._session_record_written = False
                    self._session_start_epoch = None
                    self._session_start_position = None
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
                        self._handle_interrupted_tail(position, queue_sess, last_queue_line_epoch, total_queue_boundaries, kind, left)
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
                                # Old session ended without clean detection (log blanked / VS restarted).
                                if not self._session_record_written and self.graph_points:
                                    self._write_session_record("unknown")
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
                                self._session_start_epoch = last_queue_line_epoch or time.time()
                                self._session_start_position = position
                                self._session_record_written = False
                                self.write_history('New queue run (from log).')
                                if self.current_log_file is not None:
                                    self._reseed_graph_for_new_run(self.current_log_file)
                            self._last_queue_run_session = queue_sess
                            if position == 0:
                                self._set_status_line('Completed')
                                # Anchor the graph at position 0 using the log-backed timestamp
                                # so the stored record always ends with an explicit (t, 0) point.
                                self.append_graph_point(0, last_queue_line_epoch)
                                self._write_session_record("completed")
                            elif position is not None and position <= 1:
                                self._set_status_line('At front')
                            else:
                                self._set_status_line('Monitoring')
                            self._set_position_display(position)
                            if position is not None and position <= 1 and (self._position_one_reached_at is None):
                                self._position_one_reached_at = last_queue_line_epoch or now
                            # Keep completed queues anchored to the last real log-backed sample.
                            # Appending heartbeat samples after position 0 can distort rolling rate
                            # on stop/start of an already-finished run.
                            if position != 0:
                                # Wall-clock samples every poll so the chart shows heartbeat / flat
                                # segments, not only log-line times, while the queue is still live.
                                self.append_graph_point(position, None)
                            self.update_time_estimates()
                            if position != prev_pos:
                                self._checkpoint_session()
                                self._write_session_progress()
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
                        self._set_status_line('⚠ No Queue!', danger=True)
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

    def _window_recent_points_and_trail(self) -> tuple[list[tuple[float, int]], list[int]]:
        """Return the last N position-change events and their position trail.

        Filters heartbeat duplicates first so the window size (N) counts actual
        position changes, matching the client-side rolling-window calculation.
        """
        points = list(self.graph_points)
        if len(points) < 2:
            return (points, [p for _t, p in points])
        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10000, window_points))
        changes = self._position_change_events(points)
        recent = changes[-(window_points + 1):]
        return (recent, [p for _t, p in recent])

    def _position_change_events(self, points: list[tuple[float, int]]) -> list[tuple[float, int]]:
        """Filter a point list to only the first reading at each new position level."""
        changes: list[tuple[float, int]] = []
        last_p: Optional[int] = None
        for t, p in points:
            if p != last_p:
                changes.append((t, p))
                last_p = p
        return changes

    def compute_moving_average_speed(self) -> tuple[Optional[float], int, list[int]]:
        recent, trail = self._window_recent_points_and_trail()
        if len(recent) < 2:
            return (None, 0, trail)
        changes = self._position_change_events(recent)
        if len(changes) < 2:
            return (None, 0, trail)
        rates: list[float] = []
        for (t0, p0), (t1, p1) in zip(changes, changes[1:]):
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
        """Recency-weighted mean of per-change-event segment rates.

        At **position 0** (queue finished in the log), weights use the last sample time so the
        value does not drift after completion.
        """
        recent, trail = self._window_recent_points_and_trail()
        if len(recent) < 2:
            return (None, 0, trail)
        changes = self._position_change_events(recent)
        if len(changes) < 2:
            return (None, 0, trail)
        now = time.time()
        if self._current_queue_position() == 0:
            now = float(changes[-1][0])
        w_sum = 0.0
        r_sum = 0.0
        n_seg = 0
        for (t0, p0), (t1, p1) in zip(changes, changes[1:]):
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
        recent, _trail = self._window_recent_points_and_trail()
        return recent if len(recent) >= 2 else []

    def compute_empirical_pos_per_sec(self) -> Optional[float]:
        """Net positions per second anchored to position-change events.

        t0 is the first position-change timestamp in the window (not a heartbeat).
        While monitoring and still in queue, dt extends to wall-clock now so the
        current open position's dwell is counted. Position 0 and stopped mode use
        only the span between actual change events.
        """
        recent = self._window_recent_points()
        if len(recent) < 2:
            return None
        changes = self._position_change_events(recent)
        if len(changes) < 2:
            return None
        t0, p0 = float(changes[0][0]), float(changes[0][1])
        t_last, p_last = float(changes[-1][0]), float(changes[-1][1])
        drop = p0 - p_last
        if drop <= 0:
            return None
        pos = self._current_queue_position()
        if self.running and pos != 0:
            dt = time.time() - t0
        else:
            dt = t_last - t0
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
        """Hold rate at floor until expected dwell elapsed, then blend linearly toward mpp_raw.

        Phase 1 (dwell < floor_time): return floor — optimistic, unchanged.
        Phase 2 (dwell in [floor_time, 2*floor_time]): blend from floor → mpp_raw.
        Phase 3 (dwell >= 2*floor_time): return mpp_raw — full observed rate.
        This keeps the display near the lower edge as dwell stretches, not snapping high.
        """
        if mpp_raw is None or pos is None or pos <= 1:
            return mpp_raw
        if self._mpp_floor_position != pos or self._mpp_floor_value is None or self._mpp_floor_value <= 0:
            return mpp_raw
        if mpp_raw <= self._mpp_floor_value:
            return mpp_raw
        if self._last_queue_position_change_epoch is None:
            return self._mpp_floor_value
        dwell = max(0.0, time.time() - self._last_queue_position_change_epoch)
        floor_secs = self._mpp_floor_value * 60.0
        if dwell < floor_secs:
            return self._mpp_floor_value
        t = min(1.0, (dwell - floor_secs) / max(floor_secs, 1.0))
        return self._mpp_floor_value + t * (mpp_raw - self._mpp_floor_value)

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

    def _hist_sessions_global_avg_mpp(self) -> tuple[Optional[float], int]:
        """Mean m/p averaged across all historical sessions (all outcomes). Returns (mpp, total_segments)."""
        session_avgs: list[float] = []
        total_segments = 0
        for rec in self.load_history_sessions():
            pts = rec.get("points") or []
            if len(pts) < 2:
                continue
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
            if mpps:
                session_avgs.append(sum(mpps) / len(mpps))
                total_segments += len(mpps)
        if not session_avgs:
            return (None, 0)
        return (sum(session_avgs) / len(session_avgs), total_segments)

    @staticmethod
    def _format_hist_global_rate(mpp: Optional[float], count: int) -> str:
        if mpp is not None and mpp > 0 and count > 0:
            return f'{mpp:.2f} m/p ({count})'
        return '—'

    def _refresh_queue_and_global_rate(self, pos: Optional[int]) -> Optional[float]:
        """KPI Rate value + Global Rate in Info. Header shows RATE (Rolling N). Returns capped mpp for ETA."""
        mpp_raw = self._minutes_per_position_from_window()
        mpp = self._minutes_per_position_capped_for_dwell(mpp_raw, pos)
        g_mpp = self._global_avg_minutes_per_position()
        h_mpp, h_count = self._hist_sessions_global_avg_mpp()
        self.queue_rate_var.set(self._format_queue_rate(mpp))
        self.global_rate_var.set(self._format_queue_rate(g_mpp))
        self.hist_global_rate_var.set(self._format_hist_global_rate(h_mpp, h_count))
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
                h_mpp, h_count = self._hist_sessions_global_avg_mpp()
                self.hist_global_rate_var.set(self._format_hist_global_rate(h_mpp, h_count))
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
        want_web_completion_event = bool(getattr(self._hooks, "browser_client_notifications", False))
        if not want_sound and (not want_popup) and (not want_web_completion_event):
            return
        self._queue_completion_notified_this_run = True
        self._last_queue_completion_notify_epoch = now
        self.write_history('Queue completion: past queue wait — connecting (position 0).')
        if want_sound:
            self.play_completion_sound()
        if want_popup or want_web_completion_event:
            self._hooks.show_completion_popup()
        if want_popup:
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
