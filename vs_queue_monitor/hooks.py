"""Host hooks for :class:`QueueMonitorEngine` (Tk GUI vs headless TUI)."""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, Union

import tkinter as tk
from tkinter import messagebox


class MonitorHooks(Protocol):
    """Scheduling, dialogs, and optional UI side effects."""

    def string_var(self, value: str) -> Any: ...
    def boolean_var(self, value: bool) -> Any: ...

    def schedule(self, ms: int, fn: Callable[[], None]) -> Optional[str]: ...
    def schedule_cancel(self, job: Optional[str]) -> None: ...
    def schedule_idle(self, fn: Callable[[], None]) -> None: ...

    def winfo_exists(self) -> bool: ...

    def show_error(self, title: str, message: str) -> None: ...
    def ask_yes_no(self, title: str, message: str) -> bool: ...

    def append_history(self, message: str) -> None: ...
    def request_redraw_graph(self) -> None: ...

    def show_start_loading(self, show: bool) -> None: ...

    def bell(self) -> None: ...

    def show_threshold_popup(self, position: int, eta_display: str) -> None: ...
    def show_completion_popup(self) -> None: ...

    def destroy_active_popups(self) -> None: ...

    def window_geometry_for_save(self) -> str: ...

    def open_settings_ui(self) -> None:
        """Open settings (Tk window or TUI modal)."""
        ...


class TkMonitorHooks:
    """Hooks for :class:`QueueMonitorApp` (tk.Tk root)."""

    def __init__(self, app: tk.Tk) -> None:
        self._app = app
        self._history_pending: list[str] = []

    def string_var(self, value: str) -> tk.StringVar:
        return tk.StringVar(master=self._app, value=value)

    def boolean_var(self, value: bool) -> tk.BooleanVar:
        return tk.BooleanVar(master=self._app, value=value)

    def schedule(self, ms: int, fn: Callable[[], None]) -> Optional[str]:
        return self._app.after(ms, fn)

    def schedule_cancel(self, job: Optional[str]) -> None:
        if job is not None:
            try:
                self._app.after_cancel(job)
            except Exception:
                pass

    def schedule_idle(self, fn: Callable[[], None]) -> None:
        self._app.after_idle(fn)

    def winfo_exists(self) -> bool:
        try:
            return bool(self._app.winfo_exists())
        except Exception:
            return False

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self._app)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return bool(messagebox.askyesno(title, message, parent=self._app))

    def append_history(self, message: str) -> None:
        app = self._app
        ht = getattr(app, "history_text", None)
        if ht is None:
            self._history_pending.append(message)
            return
        import time

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        ht.configure(state="normal")
        ht.insert("end", f"[{timestamp}] {message}\n")
        ht.see("end")
        ht.configure(state="disabled")

    def flush_pending_history(self) -> None:
        """Call after ``history_text`` exists (e.g. end of ``_build_ui``)."""
        if not self._history_pending:
            return
        pending = self._history_pending[:]
        self._history_pending.clear()
        for msg in pending:
            self.append_history(msg)

    def request_redraw_graph(self) -> None:
        self._app.redraw_graph()  # type: ignore[attr-defined]

    def show_start_loading(self, show: bool) -> None:
        self._app._show_start_loading(show)  # type: ignore[attr-defined]

    def bell(self) -> None:
        try:
            self._app.bell()
        except Exception:
            pass

    def show_threshold_popup(self, position: int, eta_display: str) -> None:
        self._app.show_popup(position, eta_display)  # type: ignore[attr-defined]

    def show_completion_popup(self) -> None:
        self._app.show_completion_popup()  # type: ignore[attr-defined]

    def destroy_active_popups(self) -> None:
        app = self._app
        for name in ("active_popup", "active_completion_popup"):
            w = getattr(app, name, None)
            if w is not None:
                try:
                    if w.winfo_exists():
                        w.destroy()
                except Exception:
                    pass
                setattr(app, name, None)

    def open_settings_ui(self) -> None:
        self._app.open_settings()  # type: ignore[attr-defined]

    def window_geometry_for_save(self) -> str:
        try:
            return str(self._app.geometry())
        except Exception:
            return ""


class HeadlessMonitorHooks:
    """Hooks for terminal UI: no Tk (SSH-friendly)."""

    def __init__(self, engine: Optional[Any] = None) -> None:
        self._engine = engine
        self._history_boot: list[str] = []
        self._timers: dict[str, Any] = {}
        self._timer_seq = 0
        self.textual_app: Any = None  # set by TUI before timers run

    def attach_engine(self, engine: Any) -> None:
        """Link the live engine (call after :class:`QueueMonitorEngine` is constructed)."""
        self._engine = engine
        boot = self._history_boot
        self._history_boot = []
        for msg in boot:
            self.append_history(msg)

    def string_var(self, value: str) -> Any:
        from .refs import StrRef

        return StrRef(value)

    def boolean_var(self, value: bool) -> Any:
        from .refs import BoolRef

        return BoolRef(value)

    def schedule(self, ms: int, fn: Callable[[], None]) -> Optional[str]:
        self._timer_seq += 1
        tid = f"t{self._timer_seq}"

        def run() -> None:
            self._timers.pop(tid, None)
            try:
                fn()
            except Exception:
                pass

        app = self.textual_app
        delay = max(0.0, ms / 1000.0)
        if app is not None and hasattr(app, "set_timer"):
            try:
                timer = app.set_timer(delay, run, repeat=False)
                self._timers[tid] = timer
                return tid
            except Exception:
                pass
        import threading

        timer = threading.Timer(delay, run)
        timer.daemon = True
        timer.start()
        self._timers[tid] = timer
        return tid

    def schedule_cancel(self, job: Optional[str]) -> None:
        if not job or job not in self._timers:
            return
        entry = self._timers.pop(job, None)
        if entry is None:
            return
        if hasattr(entry, "stop"):
            try:
                entry.stop()
            except Exception:
                pass
        elif hasattr(entry, "cancel"):
            try:
                entry.cancel()
            except Exception:
                pass

    def schedule_idle(self, fn: Callable[[], None]) -> None:
        self.schedule(0, fn)

    def winfo_exists(self) -> bool:
        return True

    def show_error(self, title: str, message: str) -> None:
        self.append_history(f"{title}: {message}")
        app = self.textual_app
        if app is not None and hasattr(app, "notify"):
            try:
                app.notify(f"{title}: {message}", severity="error")
            except Exception:
                pass

    def ask_yes_no(self, title: str, message: str) -> bool:
        # Headless TUI: auto-accept, but show a toast so it doesn't feel “silent”.
        app = self.textual_app
        if app is not None and hasattr(app, "notify"):
            try:
                app.notify(title or "Confirm", severity="warning")
            except Exception:
                pass
        if "New queue detected" in (title or ""):
            self.append_history("[tui] New queue detected — auto-loading new run (graph + thresholds reset).")
            return True
        return True

    def append_history(self, message: str) -> None:
        if self._engine is None:
            self._history_boot.append(message)
            return
        cb = getattr(self._engine, "_headless_append_history", None)
        if callable(cb):
            cb(message)

    def request_redraw_graph(self) -> None:
        pass

    def show_start_loading(self, show: bool) -> None:
        pass

    def bell(self) -> None:
        pass

    def show_threshold_popup(self, position: int, eta_display: str) -> None:
        self.append_history(f"[alert] Position {position} — est. left: {eta_display}")
        app = self.textual_app
        if app is not None and hasattr(app, "notify"):
            try:
                app.notify(f"Queue alert: position {position} (est. left {eta_display})", severity="warning")
            except Exception:
                pass

    def show_completion_popup(self) -> None:
        self.append_history("[completion] Past queue wait — connecting (position 0).")
        app = self.textual_app
        if app is not None and hasattr(app, "notify"):
            try:
                app.notify("Past queue wait (position 0) — connecting", severity="information")
            except Exception:
                pass

    def destroy_active_popups(self) -> None:
        pass

    def open_settings_ui(self) -> None:
        app = self.textual_app
        if app is not None and hasattr(app, "action_open_settings"):
            try:
                app.action_open_settings()
                return
            except Exception:
                pass
        self.append_history("Settings are not available in headless TUI (edit config JSON or use the GUI).")

    def window_geometry_for_save(self) -> str:
        cfg = getattr(self._engine, "config", None)
        if isinstance(cfg, dict):
            g = cfg.get("window_geometry", "")
            return str(g) if isinstance(g, str) else ""
        return ""
