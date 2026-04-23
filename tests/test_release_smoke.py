from __future__ import annotations

import shutil
import threading
from pathlib import Path

from vs_queue_monitor.engine import QueueMonitorEngine
from vs_queue_monitor.web.hooks_web import WebMonitorHooks
from vs_queue_monitor.core import compute_seed_graph_from_log
from vs_queue_monitor.web.server import _queue_sessions_for_engine


class SmokeHooks(WebMonitorHooks):
    """Deterministic hooks for engine smoke tests: no background timers or UI side effects."""

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


def _engine_for_log_dir(log_dir: Path) -> tuple[QueueMonitorEngine, SmokeHooks]:
    lock = threading.RLock()
    hooks = SmokeHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path=str(log_dir), auto_start=False)
    hooks.attach_engine(engine)
    engine.completion_sound_enabled_var.set(False)
    engine.failure_sound_enabled_var.set(False)
    engine.sound_enabled_var.set(False)
    engine.running = True
    engine.current_log_file = log_dir / "client-main.log"
    engine.source_path_var.set(str(log_dir))
    return engine, hooks


def _write_log(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_completion_then_disconnect_then_requeue() -> None:
    root = Path(".tmp-release-smoke-tests")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    base_lines = [
        "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
        "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 2",
        "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 1",
    ]
    _write_log(log_path, base_lines)

    engine, hooks = _engine_for_log_dir(log_dir)
    engine.poll_sec = 2.0

    engine.poll_once()
    assert engine.status_var.get() == "At front"
    assert engine.position_var.get() == "1"
    assert hooks._completion_notify_seq == 0
    assert hooks._failure_notify_seq == 0

    completed_lines = base_lines + [
        "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
    ]
    _write_log(log_path, completed_lines)

    engine.poll_once()
    assert engine.status_var.get() == "Completed"
    assert engine.position_var.get() == "0"
    assert hooks._completion_notify_seq == 1
    assert engine._left_connect_queue_detected is True

    disconnected_lines = completed_lines + [
        "9.4.2026 22:31:40 [Error] Connection closed unexpectedly",
    ]
    _write_log(log_path, disconnected_lines)

    engine.poll_once()
    assert engine._interrupted_mode is True
    assert engine.status_var.get() == "Interrupted"
    assert hooks._failure_notify_seq == 1

    requeue_lines = disconnected_lines + [
        "9.4.2026 22:32:00 [Notification] Connecting to tops.vintagestory.at...",
        "9.4.2026 22:32:05 [Notification] Client is in connect queue at position: 12",
    ]
    _write_log(log_path, requeue_lines)

    engine.poll_once()
    assert engine._pending_new_queue_session is not None

    engine.resolve_new_queue_offer(True)
    assert engine._interrupted_mode is False
    assert engine.status_var.get() == "Monitoring"
    assert engine.position_var.get() == "12"
    assert engine.last_position == 12


def test_active_session_zero_not_listed_as_failed_history() -> None:
    root = Path(".tmp-release-smoke-tests-session-list")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 10",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine._last_queue_run_session = 0

    sessions, _active_id = _queue_sessions_for_engine(engine)
    assert sessions == [], sessions


def test_live_session_fallback_filter_hides_latest_incomplete_entry() -> None:
    root = Path(".tmp-release-smoke-tests-live-fallback")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 10",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine.running = True
    engine._interrupted_mode = False
    engine._last_queue_run_session = 99
    engine.last_position = 10
    engine.current_point = (1775763085.0, 10)
    engine.graph_points = [(1775763055.0, 12), (1775763085.0, 10)]

    sessions, _active_id = _queue_sessions_for_engine(engine)
    assert sessions == [], sessions


def test_startup_seeded_interrupted_run_keeps_elapsed() -> None:
    root = Path(".tmp-release-smoke-tests-startup-interrupted")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 4",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 3",
            "9.4.2026 22:31:55 [Notification] Client is in connect queue at position: 2",
            "9.4.2026 22:32:25 [Error] Connection closed unexpectedly",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine._apply_seed_result(compute_seed_graph_from_log(log_path))
    engine._adopt_interrupted_tail_on_start(log_path)

    assert engine._interrupted_mode is True
    assert engine.status_var.get() == "Interrupted"
    assert engine.elapsed_var.get() == "1:02"
    assert engine.queue_rate_var.get() == "—"
    assert engine.global_rate_var.get() == "—"
    assert engine.predicted_remaining_var.get() == "—"


def test_startup_seeded_post_queue_disconnect_keeps_elapsed() -> None:
    root = Path(".tmp-release-smoke-tests-startup-postqueue-disconnect")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 2",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 1",
            "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
            "9.4.2026 22:31:40 [Error] Connection closed unexpectedly",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine._apply_seed_result(compute_seed_graph_from_log(log_path))
    engine._adopt_interrupted_tail_on_start(log_path)

    assert engine._interrupted_mode is True
    assert engine.status_var.get() == "Interrupted"
    assert engine.elapsed_var.get() == "0:32"
    assert engine.queue_rate_var.get() == "—"
    assert engine.global_rate_var.get() == "—"
    assert engine.predicted_remaining_var.get() == "—"
