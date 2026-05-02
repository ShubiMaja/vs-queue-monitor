from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

from vs_queue_monitor.engine import QueueMonitorEngine
from vs_queue_monitor.web.hooks_web import WebMonitorHooks
from vs_queue_monitor.core import (
    SEED_LOG_TAIL_BYTES,
    compute_seed_graph_from_log,
    decode_log_bytes,
    parse_tail_latest_connect_target,
    queue_position_match,
    queue_sessions_for_log_tail,
)
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
    engine.poll_sec = 2.0
    engine.running = True
    engine.current_log_file = log_dir / "client-main.log"
    engine.source_path_var.set(str(log_dir))
    history_root = log_dir.parent / ".tmp-session-history"
    history_root.mkdir(parents=True, exist_ok=True)
    engine.history_path_var.set(str(history_root))
    return engine, hooks


def _write_log(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_log_utf16(path: Path, lines: list[str], encoding: str = "utf-16-le") -> None:
    path.write_bytes(("\n".join(lines) + "\n").encode(encoding))


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
    # v1.1.173: post-completion disconnect stays "Completed", does NOT enter interrupted mode
    assert engine._interrupted_mode is False
    assert engine.status_var.get() == "Completed"
    assert hooks._failure_notify_seq == 0

    requeue_lines = disconnected_lines + [
        "9.4.2026 22:32:00 [Notification] Connecting to tops.vintagestory.at...",
        "9.4.2026 22:32:05 [Notification] Client is in connect queue at position: 12",
    ]
    _write_log(log_path, requeue_lines)

    engine.poll_once()
    # v1.1.173: new queue run auto-adopted directly (not via dialog when not in interrupted mode)
    assert engine._pending_new_queue_session is None

    # resolve_new_queue_offer is a no-op when pending is None; state already updated by poll_once
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

    sessions, _active_id, _active_epoch = _queue_sessions_for_engine(engine)
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

    sessions, _active_id, _active_epoch = _queue_sessions_for_engine(engine)
    assert sessions == [], sessions


def test_queue_sessions_merge_cross_file_history_and_dedup_live_start_epoch() -> None:
    root = Path(".tmp-release-smoke-tests-session-history-merge")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:20:53 [Notification] Connecting to alpha.example.net...",
            "9.4.2026 22:20:55 [Notification] Client is in connect queue at position: 5",
            "9.4.2026 22:21:15 [Notification] Client is in connect queue at position: 3",
            "9.4.2026 22:21:25 [Notification] Client is in connect queue at position: 1",
            "9.4.2026 22:21:26 [Notification] Connected to server, downloading data...",
            "9.4.2026 22:30:53 [Notification] Connecting to beta.example.net...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 10",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    history_root = root / "history"
    engine.history_path_var.set(str(history_root))

    live_sessions = queue_sessions_for_log_tail(log_path, SEED_LOG_TAIL_BYTES)
    assert len(live_sessions) == 2
    live_past = min(live_sessions, key=lambda s: float(s.get("start_epoch") or 0))

    hist_path = engine._effective_history_path()
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": 1,
                        "source_path": str(log_dir),
                        "log_file": str(log_path),
                        "server": "alpha.example.net",
                        "start_epoch": live_past["start_epoch"],
                        "end_epoch": live_past["end_epoch"],
                        "outcome": "completed",
                        "start_position": live_past["start_pos"],
                        "end_position": live_past["end_pos"],
                        "points": live_past["points"],
                        "vsqm_version": "1.1.69",
                    }
                ),
                json.dumps(
                    {
                        "session_id": 77,
                        "source_path": "D:/AltVintagestoryData",
                        "log_file": "D:/AltVintagestoryData/client-main.log",
                        "server": "gamma.example.net",
                        "start_epoch": 1775760000.0,
                        "end_epoch": 1775760060.0,
                        "outcome": "completed",
                        "start_position": 9,
                        "end_position": 0,
                        "points": [[1775760000.0, 9], [1775760030.0, 5], [1775760060.0, 0]],
                        "vsqm_version": "1.1.69",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sessions, active_id, _active_epoch = _queue_sessions_for_engine(engine)

    assert active_id >= 0
    assert len(sessions) == 2, sessions
    assert sum(1 for s in sessions if int(float(s.get("start_epoch") or 0)) == int(float(live_past["start_epoch"]))) == 1
    assert [s["label"] for s in sessions] == ["Session 1", "Session 2"]
    gamma = next(s for s in sessions if s.get("server") == "gamma.example.net")
    assert gamma["source_path"] == "D:/AltVintagestoryData"
    assert gamma["outcome"] == "completed"


def test_queue_sessions_dedup_duplicate_history_records() -> None:
    root = Path(".tmp-release-smoke-tests-session-history-dedup")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:53 [Notification] Connecting to beta.example.net...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 10",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    history_root = root / "history"
    engine.history_path_var.set(str(history_root))

    hist_path = engine._effective_history_path()
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    dup_a = {
        "session_id": 41,
        "source_path": "D:/AltVintagestoryData",
        "log_file": "D:/AltVintagestoryData/client-main.log",
        "server": "gamma.example.net",
        "start_epoch": 1775760000.0,
        "end_epoch": 1775760060.0,
        "outcome": "completed",
        "start_position": 9,
        "end_position": 0,
        "points": [[1775760000.0, 9], [1775760060.0, 0]],
        "vsqm_version": "1.1.86",
    }
    dup_b = {
        "session_id": 41,
        "source_path": "D:/AltVintagestoryData",
        "log_file": "D:/AltVintagestoryData/client-main.log",
        "server": "gamma.example.net",
        "start_epoch": 1775760000.4,
        "end_epoch": 1775760060.4,
        "outcome": "completed",
        "start_position": 9,
        "end_position": 0,
        "points": [[1775760000.4, 9], [1775760030.4, 5], [1775760060.4, 0]],
        "vsqm_version": "1.1.86",
    }
    hist_path.write_text(json.dumps(dup_a) + "\n" + json.dumps(dup_b) + "\n", encoding="utf-8")

    sessions, _active_id, _active_epoch = _queue_sessions_for_engine(engine)

    gamma_sessions = [s for s in sessions if s.get("server") == "gamma.example.net"]
    assert len(gamma_sessions) == 1, gamma_sessions
    assert len(gamma_sessions[0]["points"]) == 3


def test_history_session_cache_respects_history_path_changes() -> None:
    root = Path(".tmp-release-smoke-tests-history-cache-switch")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    _write_log(
        log_dir / "client-main.log",
        [
            "9.4.2026 22:30:53 [Notification] Connecting to beta.example.net...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)

    history_a = root / "history-a"
    engine.history_path_var.set(str(history_a))
    hist_a = engine._effective_history_path()
    hist_a.parent.mkdir(parents=True, exist_ok=True)
    hist_a.write_text(
        json.dumps(
            {
                "session_id": 1,
                "source_path": str(log_dir),
                "log_file": str(log_dir / "client-main.log"),
                "server": "alpha.example.net",
                "start_epoch": 1775760000.0,
                "end_epoch": 1775760060.0,
                "outcome": "completed",
                "start_position": 9,
                "end_position": 0,
                "points": [[1775760000.0, 9], [1775760060.0, 0]],
                "vsqm_version": "1.1.91",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    first = engine.load_history_sessions()
    assert [rec.get("server") for rec in first] == ["alpha.example.net"]

    history_b = root / "history-b"
    engine.history_path_var.set(str(history_b))
    hist_b = engine._effective_history_path()
    hist_b.parent.mkdir(parents=True, exist_ok=True)
    hist_b.write_text(
        json.dumps(
            {
                "session_id": 2,
                "source_path": str(log_dir),
                "log_file": str(log_dir / "client-main.log"),
                "server": "beta.example.net",
                "start_epoch": 1775761000.0,
                "end_epoch": 1775761060.0,
                "outcome": "completed",
                "start_position": 6,
                "end_position": 0,
                "points": [[1775761000.0, 6], [1775761060.0, 0]],
                "vsqm_version": "1.1.91",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    second = engine.load_history_sessions()
    assert [rec.get("server") for rec in second] == ["beta.example.net"]


def test_parse_tail_latest_connect_target_picks_current_session() -> None:
    text = "\n".join(
        [
            "9.4.2026 22:30:53 [Notification] Connecting to alpha.example.net...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:32:00 [Notification] Connecting to beta.example.net...",
            "9.4.2026 22:32:05 [Notification] Client is in connect queue at position: 9",
        ]
    )
    assert parse_tail_latest_connect_target(text, 1) == "alpha.example.net"
    assert parse_tail_latest_connect_target(text, 2) == "beta.example.net"
    assert parse_tail_latest_connect_target(text) == "beta.example.net"


def test_parse_tail_latest_connect_target_handles_extra_boundary_before_queue() -> None:
    text = "\n".join(
        [
            "23.4.2026 20:09:17 [Notification] Connecting to tops.vintagestory.at...",
            "23.4.2026 20:09:17 [Notification] Initialized Server Connection",
            "23.4.2026 20:09:20 [Notification] Client is in connect queue at position: 71",
        ]
    )
    assert parse_tail_latest_connect_target(text, 2) == "tops.vintagestory.at"


def test_history_lines_limit_returns_tail_slice() -> None:
    hooks = WebMonitorHooks(threading.RLock())
    for idx in range(5):
        hooks._history.append(f"line-{idx}")
    assert hooks.history_lines(2) == ["line-3", "line-4"]


def test_graph_view_prefs_are_not_persisted_server_side() -> None:
    hooks = WebMonitorHooks(threading.RLock())
    engine = QueueMonitorEngine(hooks, initial_path="", auto_start=False)
    snap = engine.get_config_snapshot()
    assert "graph_log_scale" not in snap
    assert "graph_live_view" not in snap
    assert "graph_time_mode" not in snap


def test_web_client_notification_events_do_not_depend_on_shared_popup_flags() -> None:
    root = Path(".tmp-release-smoke-tests-web-popup-local")
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
    engine.completion_popup_enabled_var.set(False)
    engine.failure_popup_enabled_var.set(False)

    engine.poll_once()
    _write_log(log_path, base_lines + ["9.4.2026 22:31:26 [Notification] Connected to server, downloading data..."])
    engine.poll_once()
    assert hooks._completion_notify_seq == 1

    _write_log(log_path, base_lines + [
        "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
        "9.4.2026 22:31:40 [Error] Connection closed unexpectedly",
    ])
    engine.poll_once()
    # v1.1.173: post-completion disconnect does NOT fire failure notification
    assert hooks._failure_notify_seq == 0


def test_server_target_refresh_falls_back_to_seed_window() -> None:
    root = Path(".tmp-release-smoke-tests-server-target")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    filler = "9.4.2026 22:31:00 [Debug] filler " + ("x" * 240)
    lines = [
        "9.4.2026 22:30:53 [Notification] Connecting to gamma.example.net...",
        "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
    ] + [filler for _ in range(700)] + [
        "9.4.2026 22:40:00 [Notification] Client is in connect queue at position: 11",
    ]
    _write_log(log_path, lines)

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine.server_target_var.set("—")
    engine._refresh_server_target_from_log(log_path, 1)

    assert engine.server_target_var.get() == "gamma.example.net"


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

    # v1.1.173: completed+disconnect at startup does NOT enter interrupted mode
    assert engine._interrupted_mode is False
    assert engine.status_var.get() == "Idle"
    # Elapsed computed from graph points (first queue line → last queue line), not connect phase
    assert engine.elapsed_var.get() == "0:30"
    # Rates are computed from seeded graph points, not frozen at "—"
    assert engine.queue_rate_var.get() != "—"
    assert engine.global_rate_var.get() != "—"
    assert engine.predicted_remaining_var.get() == "—"


def test_completed_queue_restart_does_not_add_post_completion_heartbeat_points() -> None:
    root = Path(".tmp-release-smoke-tests-completed-restart")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log(
        log_path,
        [
            "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
            "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
            "9.4.2026 22:31:05 [Notification] Client is in connect queue at position: 11",
            "9.4.2026 22:31:15 [Notification] Client is in connect queue at position: 10",
            "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 1",
            "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
        ],
    )

    engine, _hooks = _engine_for_log_dir(log_dir)
    seed = compute_seed_graph_from_log(log_path)
    assert seed is not None

    engine._apply_seed_result(seed)
    seeded_points = list(engine.graph_points)
    seeded_rate = engine.queue_rate_var.get()

    engine.poll_once()

    assert engine.status_var.get() == "Completed"
    assert engine.position_var.get() == "0"
    assert list(engine.graph_points) == seeded_points
    assert engine.queue_rate_var.get() == seeded_rate


# ---------------------------------------------------------------------------
# Encoding: UTF-16 log fixture (regression for silent byte-strip via errors="ignore")
# ---------------------------------------------------------------------------

_UTF16_QUEUE_LINES = [
    "12 Jun 2025 09:00:00 [Client] Connecting to example.vs.server:42420",
    "12 Jun 2025 09:00:01 [Client] Client is in connect queue at position: 42",
    "12 Jun 2025 09:00:30 [Client] Client is in connect queue at position: 20",
    "12 Jun 2025 09:01:00 [Client] Client is in connect queue at position: 5",
]


def test_decode_log_bytes_utf16le() -> None:
    raw = ("\n".join(_UTF16_QUEUE_LINES) + "\n").encode("utf-16-le")
    text = decode_log_bytes(raw)
    assert "position: 42" in text
    assert "position: 5" in text


def test_decode_log_bytes_utf16le_with_bom() -> None:
    # utf-16 encoding includes BOM automatically
    raw = ("\n".join(_UTF16_QUEUE_LINES) + "\n").encode("utf-16")
    text = decode_log_bytes(raw)
    assert "position: 42" in text


def test_decode_log_bytes_utf8() -> None:
    raw = ("\n".join(_UTF16_QUEUE_LINES) + "\n").encode("utf-8")
    text = decode_log_bytes(raw)
    assert "position: 42" in text
    assert "position: 5" in text


def test_queue_position_match_survives_utf16_round_trip() -> None:
    raw = ("\n".join(_UTF16_QUEUE_LINES) + "\n").encode("utf-16-le")
    text = decode_log_bytes(raw)
    positions = [int(queue_position_match(ln).group(1)) for ln in text.splitlines() if queue_position_match(ln)]
    assert positions == [42, 20, 5]


def test_decode_log_bytes_utf16le_engine_parses_position() -> None:
    root = Path(".tmp-release-smoke-tests-utf16")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    log_dir = root / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    _write_log_utf16(log_path, _UTF16_QUEUE_LINES)

    engine, _hooks = _engine_for_log_dir(log_dir)
    engine.poll_once()

    assert engine.position_var.get() == "5", f"Expected position 5, got {engine.position_var.get()!r}"
    shutil.rmtree(root, ignore_errors=True)
