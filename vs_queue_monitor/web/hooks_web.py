"""Hooks for :class:`~vs_queue_monitor.engine.QueueMonitorEngine` when driven by the local web UI."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Optional

from .. import APP_DISPLAY_NAME
from ..desktop_notify import try_notify
from ..refs import BoolRef, StrRef


class WebMonitorHooks:
    """Threading timers + StrRef/BoolRef; all scheduled work runs under ``lock``."""

    def __init__(self, lock: threading.RLock) -> None:
        self._lock = lock
        self._engine: Any = None
        self._timers: dict[str, threading.Timer] = {}
        self._timer_seq = 0
        self._history: deque[str] = deque(maxlen=4000)
        self._completion_notify_seq = 0

    def attach_engine(self, engine: Any) -> None:
        self._engine = engine

    def string_var(self, value: str) -> StrRef:
        return StrRef(value)

    def boolean_var(self, value: bool) -> BoolRef:
        return BoolRef(value)

    def schedule(self, ms: int, fn: Callable[[], None]) -> Optional[str]:
        self._timer_seq += 1
        tid = f"w{self._timer_seq}"
        delay = max(0.0, ms / 1000.0)

        def wrapped() -> None:
            self._timers.pop(tid, None)
            with self._lock:
                try:
                    fn()
                except Exception:
                    pass

        t = threading.Timer(delay, wrapped)
        t.daemon = True
        t.start()
        self._timers[tid] = t
        return tid

    def schedule_cancel(self, job: Optional[str]) -> None:
        if not job or job not in self._timers:
            return
        t = self._timers.pop(job, None)
        if t is None:
            return
        try:
            t.cancel()
        except Exception:
            pass

    def schedule_idle(self, fn: Callable[[], None]) -> None:
        self.schedule(0, fn)

    def winfo_exists(self) -> bool:
        return True

    def show_error(self, title: str, message: str) -> None:
        self.append_history(f"{title}: {message}")

    def ask_yes_no(self, title: str, message: str) -> bool:
        return True

    def new_queue_dialog_async(self) -> bool:
        """Engine defers to :meth:`~vs_queue_monitor.engine.QueueMonitorEngine.resolve_new_queue_offer`."""
        return True

    def append_history(self, message: str) -> None:
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._history.append(f"[{ts}] {message}")

    def request_redraw_graph(self) -> None:
        pass

    def show_start_loading(self, show: bool) -> None:
        pass

    def bell(self) -> None:
        pass

    def show_threshold_popup(self, position: int, eta_display: str) -> None:
        self.append_history(f"[alert] Position {position} — est. left: {eta_display}")
        try_notify(
            APP_DISPLAY_NAME,
            f"Threshold alert: position {position} — est. remaining {eta_display}",
            app_name=APP_DISPLAY_NAME,
        )

    def show_completion_popup(self) -> None:
        self._completion_notify_seq += 1
        self.append_history("[completion] Past queue wait — connecting (position 0).")
        try_notify(
            APP_DISPLAY_NAME,
            "Past queue wait — connecting (position 0).",
            app_name=APP_DISPLAY_NAME,
        )

    def destroy_active_popups(self) -> None:
        pass

    def open_settings_ui(self) -> None:
        pass

    def window_geometry_for_save(self) -> str:
        return ""

    def history_lines(self) -> list[str]:
        return list(self._history)
