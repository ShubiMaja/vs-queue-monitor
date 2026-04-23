from __future__ import annotations

import threading

from vs_queue_monitor.engine import QueueMonitorEngine
from vs_queue_monitor.web.hooks_web import WebMonitorHooks


class InterruptedHooks(WebMonitorHooks):
    def schedule(self, ms: int, fn):  # type: ignore[override]
        return None

    def schedule_idle(self, fn):  # type: ignore[override]
        return None

    def schedule_cancel(self, job):  # type: ignore[override]
        return None

    def request_redraw_graph(self) -> None:
        return None

    def show_start_loading(self, show: bool) -> None:
        return None


def test_enter_interrupted_state_freezes_elapsed_at_last_queue_sample() -> None:
    lock = threading.RLock()
    hooks = InterruptedHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path="", auto_start=False)
    hooks.attach_engine(engine)
    engine.failure_sound_enabled_var.set(False)
    engine.running = True
    engine.monitor_start_epoch = 1775763053.0
    engine._connect_phase_started_epoch = 1775763053.0
    engine.graph_points = [
        (1775763055.0, 4),
        (1775763085.0, 3),
        (1775763115.0, 2),
    ]
    engine.current_point = engine.graph_points[-1]
    engine.last_position = 2
    engine._set_position_display(2)

    engine.enter_interrupted_state("Connection lost (final teardown).")

    assert engine._interrupted_mode is True
    assert engine.status_var.get() == "Interrupted"
    assert engine._interrupted_elapsed_sec == 62.0
    assert engine.elapsed_var.get() == "1:02"
