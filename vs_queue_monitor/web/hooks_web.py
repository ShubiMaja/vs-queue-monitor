"""Hooks for :class:`~vs_queue_monitor.engine.QueueMonitorEngine` when driven by the local web UI."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Callable, Optional

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
        self._failure_notify_seq = 0

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

    def show_completion_popup(self) -> None:
        self._completion_notify_seq += 1
        self.append_history("[completion] Past queue wait — connecting (position 0).")

    def show_failure_popup(self, detail: str = "") -> None:
        self._failure_notify_seq += 1
        msg = "[failure] Queue interrupted - still watching the log."
        if detail:
            msg += f" ({detail})"
        self.append_history(msg)

    def destroy_active_popups(self) -> None:
        pass

    def open_settings_ui(self) -> None:
        pass

    def window_geometry_for_save(self) -> str:
        return ""

    def history_lines(self) -> list[str]:
        return list(self._history)
