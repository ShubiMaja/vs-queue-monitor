"""Unit tests for session-history dedup, ghost suppression, and cross-folder display.

Run with:  pytest tests/test_session_history.py -v
"""
from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from vs_queue_monitor.core import (
    get_newer_session_attempt,
    normalize_log_path_for_dedup,
    tail_has_post_queue_after_last_queue_line,
)
from vs_queue_monitor.web.server import _queue_sessions_for_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = 1_745_600_000.0  # arbitrary epoch anchor


def _ep(offset_sec: float = 0.0) -> float:
    return _T0 + offset_sec


def _ts(offset_sec: float = 0.0) -> str:
    """Format epoch as VS log timestamp string."""
    import datetime
    dt = datetime.datetime.utcfromtimestamp(_ep(offset_sec))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _queue_line(position: int, offset_sec: float) -> str:
    return f"{_ts(offset_sec)} [Client] [Info] Connect queue position {position}"


def _loading_line(offset_sec: float) -> str:
    return f"{_ts(offset_sec)} [Client] [Info] Loading and pre-starting client-side mods"


def _connecting_line(offset_sec: float, host: str = "tops.vintagestory.at:42421") -> str:
    return f"{_ts(offset_sec)} [Client] [Info] Connecting to {host}"


def _disconnect_line(offset_sec: float) -> str:
    return f"{_ts(offset_sec)} [Client] [Info] Disconnected by server"


def _jsonl_record(
    *,
    log_file: str,
    session_id: int,
    start_epoch: float,
    outcome: str = "completed",
    end_epoch: Optional[float] = None,
    points: Optional[list] = None,
    server: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "log_file": log_file,
        "start_epoch": start_epoch,
        "end_epoch": end_epoch or start_epoch + 600,
        "outcome": outcome,
        "start_position": None,
        "end_position": 0 if outcome == "completed" else None,
        "points": points or [],
        "server": server,
        "source_path": "",
    }


def _make_engine(
    *,
    log_file: Optional[Path] = None,
    running: bool = True,
    interrupted: bool = False,
    last_session_id: int = -1,
    session_start_epoch: Optional[float] = None,
    graph_points: Optional[list[tuple[float, int]]] = None,
    hist_records: Optional[list[dict]] = None,
) -> MagicMock:
    eng = MagicMock()
    eng.running = running
    eng._interrupted_mode = interrupted
    eng._last_queue_run_session = last_session_id
    eng._session_start_epoch = session_start_epoch
    eng.graph_points = deque(graph_points or [], maxlen=500)
    eng.current_log_file = log_file
    eng.load_history_sessions.return_value = hist_records or []
    return eng


# ---------------------------------------------------------------------------
# get_newer_session_attempt — false positive regression
# ---------------------------------------------------------------------------

class TestGetNewerSessionAttempt:
    def test_returns_false_with_no_lines_after_queue(self):
        tail = _queue_line(5, 0)
        has, _ = get_newer_session_attempt(tail)
        assert not has

    def test_returns_true_for_genuine_reconnect_after_disconnect(self):
        tail = "\n".join([
            _queue_line(5, 0),
            _disconnect_line(10),
            _connecting_line(20),   # genuine new attempt
        ])
        has, _ = get_newer_session_attempt(tail)
        assert has

    def test_returns_false_for_post_queue_world_join(self):
        """'Connecting to' after loading-mods is the post-queue world join, not a new session."""
        tail = "\n".join([
            _queue_line(1, 0),
            _loading_line(10),           # post-queue progress
            _connecting_line(15),        # world join — must NOT trigger has_newer
        ])
        has, _ = get_newer_session_attempt(tail)
        assert not has, (
            "Connecting-to after post-queue loading line is the world join, not a new session"
        )

    def test_returns_false_for_connecting_then_loading_then_interrupted(self):
        """'Connecting to' before loading mods but still post-queue — must not trigger."""
        tail = "\n".join([
            _queue_line(1, 0),
            _connecting_line(5),         # game world join (before loading mods line)
            _loading_line(10),           # post-queue progress arrives after
        ])
        # post-queue line exists in the after-queue section → treat as world join
        has, _ = get_newer_session_attempt(tail)
        assert not has

    def test_returns_true_when_no_post_queue_just_reconnect(self):
        """Queue → straight reconnect with no loading lines = genuine new attempt."""
        tail = "\n".join([
            _queue_line(5, 0),
            _connecting_line(10),        # no loading lines — genuine new attempt
        ])
        has, _ = get_newer_session_attempt(tail)
        assert has


# ---------------------------------------------------------------------------
# _queue_sessions_for_engine — ghost suppression
# ---------------------------------------------------------------------------

class TestGhostSuppressionRunningSession:
    """Ghost suppression must work for a normally-running session whose queue lines
    are outside the 2 MB tail window (lots of game log accumulated after queue exit).
    Before the fix, the fallback was guarded by ``engine._interrupted_mode``, so a
    running (non-interrupted) session with an empty tail silently skipped the
    ``seed_active_id`` resolution and ghost suppression never fired."""

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_ghost_suppressed_when_tail_has_no_queue_positions(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        log = tmp_path / "vtdata" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None   # no queue positions visible in tail
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        session_start = _ep(0)
        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=False,   # NOT interrupted — the formerly-failing case
            last_session_id=5,
            session_start_epoch=session_start,
            graph_points=[(session_start, 10), (session_start + 30, 5)],
            hist_records=[
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=5,
                    start_epoch=session_start,
                    outcome="in_progress",
                ),
            ],
        )

        sessions, seed_id, active_epoch = _queue_sessions_for_engine(eng)

        session_starts = [s["start_epoch"] for s in sessions]
        assert session_start not in session_starts, (
            "Running session ghost must be suppressed even when queue lines "
            "have scrolled past the 2 MB tail window"
        )
        assert seed_id == 5
        assert active_epoch is not None


class TestGhostSuppression:
    """Session 6 should NOT appear in all_sessions when it is the loaded session."""

    def _vtdata_log(self, tmp_path: Path) -> Path:
        p = tmp_path / "vtdata" / "client-main.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        # Tail: session at position 1 → post-queue loading → connecting (world join)
        p.write_text("\n".join([
            _queue_line(1, 0),
            _loading_line(60),
            _connecting_line(65),
            _disconnect_line(120),
        ]))
        return p

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_ghost_suppressed_for_interrupted_completed_session(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        log = self._vtdata_log(tmp_path)
        lf_norm = normalize_log_path_for_dedup(str(log))

        tail_text = log.read_text()
        mock_tail.return_value = tail_text
        mock_live.return_value = []  # no live sessions from tail parse
        mock_parse.return_value = (1, 6)  # last queue pos=1, session_id=6
        # After fix: post-queue world join must NOT set _has_newer
        mock_newer.return_value = (False, None)

        session_start = _ep(0)
        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=True,
            last_session_id=6,
            session_start_epoch=session_start,
            graph_points=[(session_start, 5), (session_start + 30, 3), (session_start + 60, 1)],
            hist_records=[
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=6,
                    start_epoch=session_start,
                    outcome="interrupted",
                ),
            ],
        )

        sessions, seed_id, active_epoch = _queue_sessions_for_engine(eng)

        session_keys = [s["key"] for s in sessions]
        session_starts = [s["start_epoch"] for s in sessions]
        assert session_start not in session_starts, (
            f"Session 6 (the loaded session) must not appear in dropdown. "
            f"Got: {sessions}"
        )
        assert seed_id == 6
        assert active_epoch is not None

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_ghost_not_suppressed_when_has_newer_is_true(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """When a genuine newer session exists, the old session record must stay visible."""
        log = tmp_path / "unstable" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        # Must be non-empty so the `if tail_text:` branch executes and mocks are called
        mock_tail.return_value = _queue_line(5, 0)
        mock_live.return_value = []
        mock_parse.return_value = (5, 3)   # session 3 still in queue
        mock_newer.return_value = (True, _ep(300))  # genuine new attempt after session 3

        session_start = _ep(0)
        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=True,
            last_session_id=3,
            session_start_epoch=session_start,
            graph_points=[(session_start, 10), (session_start + 60, 5)],
            hist_records=[
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=3,
                    start_epoch=session_start,
                    outcome="interrupted",
                ),
            ],
        )

        sessions, seed_id, active_epoch = _queue_sessions_for_engine(eng)

        # With has_newer=True the interrupted session record must appear as a historical entry
        session_starts = [s["start_epoch"] for s in sessions]
        assert session_start in session_starts, (
            "Interrupted session must remain visible when a newer attempt exists"
        )


    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_ghost_suppressed_interrupted_no_queue_in_tail(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """VTData regression: interrupted mode where the 2 MB tail has no queue positions.

        seed_active_id=-1 (tail gives nothing) so ghost suppression must fall back to
        epoch-based matching against engine._session_start_epoch regardless of session_id.
        """
        log = tmp_path / "vtdata" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        session_start = _ep(0)
        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=True,
            last_session_id=-1,
            session_start_epoch=session_start,
            graph_points=[(session_start, 10), (session_start + 30, 5)],
            hist_records=[
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=5,
                    start_epoch=session_start,
                    outcome="interrupted",
                ),
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=6,
                    start_epoch=_ep(50000),
                    outcome="completed",
                ),
            ],
        )

        sessions, seed_id, active_epoch = _queue_sessions_for_engine(eng)

        session_starts = [s["start_epoch"] for s in sessions]
        labels = [s["label"] for s in sessions]
        assert session_start not in session_starts, (
            "Ghost must be suppressed by epoch match when session_id unavailable. "
            f"Got labels: {labels}"
        )
        assert _ep(50000) in session_starts, "Post-interrupt session must remain visible"
        assert "Session 2" in labels, f"Label shift wrong after ghost suppression. Got: {labels}"

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_ghost_suppressed_when_jsonl_has_wrong_session_id(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """VTData regression: JSONL ghost has sid=0 (from old bug) but engine._last_queue_run_session=8.

        The hist_by_sig dedup may keep the sid=0 record over sid=8 when both are 'completed'
        and have the same point count.  The session_id match (0 != 8) then fails.
        Epoch-based matching in interrupted mode must suppress it regardless of session_id.
        """
        log = tmp_path / "vtdata" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        session_start = _ep(0)
        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=True,
            last_session_id=8,           # engine knows the correct absolute session_id
            session_start_epoch=session_start,
            graph_points=[(session_start, 10), (session_start + 30, 5)],
            hist_records=[
                # sid=0: written by old bug when _last_queue_run_session was wrong
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=0,
                    start_epoch=session_start,
                    outcome="completed",
                ),
                # sid=8: correct record for the same session (same epoch)
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=8,
                    start_epoch=session_start,
                    outcome="completed",
                ),
                _jsonl_record(
                    log_file=lf_norm,
                    session_id=9,
                    start_epoch=_ep(50000),
                    outcome="completed",
                ),
            ],
        )

        sessions, seed_id, active_epoch = _queue_sessions_for_engine(eng)

        session_starts = [s["start_epoch"] for s in sessions]
        labels = [s["label"] for s in sessions]
        assert session_start not in session_starts, (
            "Ghost with wrong session_id must be suppressed by epoch match in interrupted mode. "
            f"Got labels: {labels}"
        )
        assert _ep(50000) in session_starts, "Post-interrupt session must remain visible"
        assert "Session 2" in labels, f"Label shift wrong. Got: {labels}"


# ---------------------------------------------------------------------------
# Pass A2 — stale-record collapse
# ---------------------------------------------------------------------------

class TestPassA2StaleRecordCollapse:
    """Pre-fix runs wrote abandoned records with wrong start_epochs; A2 must collapse them."""

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_stale_abandoned_does_not_duplicate_completed(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        log = tmp_path / "unstable" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        correct_start = _ep(0)
        stale_start_1 = _ep(400)   # mid-session, from pre-fix truncated deque
        stale_start_2 = _ep(600)   # another stale write

        eng = _make_engine(
            log_file=log,
            running=False,   # engine stopped; terminal record written
            interrupted=False,
            last_session_id=5,
            session_start_epoch=correct_start,
            hist_records=[
                # Correct backfill record
                _jsonl_record(log_file=lf_norm, session_id=5, start_epoch=correct_start, outcome="completed"),
                # Stale abandoned records from pre-fix runs
                _jsonl_record(log_file=lf_norm, session_id=5, start_epoch=stale_start_1, outcome="abandoned"),
                _jsonl_record(log_file=lf_norm, session_id=5, start_epoch=stale_start_2, outcome="abandoned"),
            ],
        )

        sessions, _, _ = _queue_sessions_for_engine(eng)

        # Session 5 must appear exactly once
        s5 = [s for s in sessions if s.get("session_id") == 5]
        assert len(s5) == 1, f"Session 5 must appear once, got {len(s5)}: {s5}"
        assert s5[0]["outcome"] == "completed", f"Expected completed, got {s5[0]['outcome']}"

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_cross_folder_sessions_not_collapsed_together(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """Sessions from different log files must not collapse even if session_id matches."""
        log_a = tmp_path / "folderA" / "client-main.log"
        log_b = tmp_path / "folderB" / "client-main.log"
        for p in (log_a, log_b):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")
        lf_a = normalize_log_path_for_dedup(str(log_a))
        lf_b = normalize_log_path_for_dedup(str(log_b))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        eng = _make_engine(
            log_file=log_a,
            running=False,
            interrupted=False,
            last_session_id=-1,
            hist_records=[
                _jsonl_record(log_file=lf_a, session_id=3, start_epoch=_ep(0), outcome="completed"),
                _jsonl_record(log_file=lf_b, session_id=3, start_epoch=_ep(3600), outcome="completed"),
            ],
        )

        sessions, _, _ = _queue_sessions_for_engine(eng)
        assert len(sessions) == 2, (
            f"Sessions from different log files must both appear: got {len(sessions)}"
        )


    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_in_progress_beats_stale_abandoned_by_recency(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """Unstable regression: live in_progress record must beat stale abandoned records.

        Same (lf, sid, floor_epoch) for all records.  The abandoned records were written
        earlier (lower end_epoch); the in_progress was written later (higher end_epoch).
        Old code ranked abandoned (1) above in_progress (-1) unconditionally, so the live
        session appeared as 'abandoned' in cross-folder views.
        """
        log = tmp_path / "unstable" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        start = _ep(0)
        early = start + 30    # abandoned records written 30 s after session start
        later = start + 120   # in_progress written 120 s after start (more recent)

        eng = _make_engine(
            log_file=log,
            running=True,
            interrupted=False,
            last_session_id=-1,
            hist_records=[
                _jsonl_record(log_file=lf_norm, session_id=4, start_epoch=start,
                              outcome="abandoned", end_epoch=early),
                _jsonl_record(log_file=lf_norm, session_id=4, start_epoch=start,
                              outcome="abandoned", end_epoch=early),
                _jsonl_record(log_file=lf_norm, session_id=4, start_epoch=start,
                              outcome="in_progress", end_epoch=later),
            ],
        )

        sessions, _, _ = _queue_sessions_for_engine(eng)

        matched = [s for s in sessions if abs(float(s.get("start_epoch", 0)) - start) < 2]
        assert len(matched) == 1, f"Expected one record for this session, got {len(matched)}"
        assert matched[0]["outcome"] == "in_progress", (
            f"Most-recent in_progress must beat stale abandoned. Got: {matched[0]['outcome']}"
        )

    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_abandoned_beats_in_progress_when_abandoned_is_more_recent(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """When abandoned is written AFTER in_progress (truly failed session), abandoned wins."""
        log = tmp_path / "unstable" / "client-main.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("")
        lf_norm = normalize_log_path_for_dedup(str(log))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        start = _ep(0)
        progress_time = start + 60   # in_progress written during session
        abandon_time = start + 120   # abandoned written later when session failed

        eng = _make_engine(
            log_file=log,
            running=False,
            interrupted=False,
            last_session_id=-1,
            hist_records=[
                _jsonl_record(log_file=lf_norm, session_id=4, start_epoch=start,
                              outcome="in_progress", end_epoch=progress_time),
                _jsonl_record(log_file=lf_norm, session_id=4, start_epoch=start,
                              outcome="abandoned", end_epoch=abandon_time),
            ],
        )

        sessions, _, _ = _queue_sessions_for_engine(eng)

        matched = [s for s in sessions if abs(float(s.get("start_epoch", 0)) - start) < 2]
        assert len(matched) == 1
        assert matched[0]["outcome"] == "abandoned", (
            f"More-recent abandoned must win over earlier in_progress. Got: {matched[0]['outcome']}"
        )


# ---------------------------------------------------------------------------
# Cross-folder visibility
# ---------------------------------------------------------------------------

class TestCrossFolder:
    @patch("vs_queue_monitor.web.server.read_log_file_tail_text")
    @patch("vs_queue_monitor.web.server.queue_sessions_for_log_tail")
    @patch("vs_queue_monitor.web.server.parse_tail_last_queue_reading")
    @patch("vs_queue_monitor.web.server.get_newer_session_attempt")
    def test_interrupted_session_from_other_folder_is_visible(
        self, mock_newer, mock_parse, mock_live, mock_tail, tmp_path: Path
    ):
        """A discovery record for an interrupted session must appear in other folders' views."""
        log_vtdata = tmp_path / "vtdata" / "client-main.log"
        log_unstable = tmp_path / "unstable" / "client-main.log"
        for p in (log_vtdata, log_unstable):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")
        lf_vtdata = normalize_log_path_for_dedup(str(log_vtdata))

        mock_tail.return_value = None
        mock_live.return_value = []
        mock_parse.return_value = (None, -1)
        mock_newer.return_value = (False, None)

        vtdata_session_start = _ep(0)
        # Unstable is the current folder, not running any session
        eng = _make_engine(
            log_file=log_unstable,
            running=True,
            interrupted=False,
            last_session_id=-1,
            hist_records=[
                # Discovery record written by _write_seeded_session_discovery for VTData session
                _jsonl_record(
                    log_file=lf_vtdata,
                    session_id=6,
                    start_epoch=vtdata_session_start,
                    outcome="interrupted",
                ),
            ],
        )

        sessions, _, _ = _queue_sessions_for_engine(eng)

        vtdata_sessions = [s for s in sessions if normalize_log_path_for_dedup(str(s.get("log_file", ""))) == lf_vtdata]
        assert len(vtdata_sessions) == 1, (
            f"VTData's interrupted session must appear in Unstable's cross-folder view: {sessions}"
        )
