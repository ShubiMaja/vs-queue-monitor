#!/usr/bin/env python3
"""
Vintage Story Queue Monitor GUI
Version: 1.0.0

Cross-platform Tkinter app that watches a Vintage Story client log for queue
position changes and raises configurable threshold alerts (popup + sound).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

VERSION = "1.0.0"
QUEUE_RE = re.compile(
    r"(?:"
    r"client\s+is\s+in\s+connect\s+queue\s+at\s+position"
    r"|your\s+position\s+in\s+the\s+queue\s+is"
    r")\D*(\d+)",
    re.IGNORECASE,
)


def queue_position_match(line: str) -> Optional[re.Match[str]]:
    """Best queue-index match on this line, or None.

    If the phrase appears more than once (wrapped / duplicated fragments), the *first* ``re.search``
    can latch onto a stale number (e.g. 110) while a later clause on the same line has the real
    position — we take the *last* non-percentage match. Skip digits immediately followed by ``%``.
    """
    matches = list(QUEUE_RE.finditer(line))
    for m in reversed(matches):
        tail = line[m.end(1) :].lstrip()
        if tail.startswith("%"):
            continue
        return m
    return None


# Lines matching these (but not queue position lines) start a new "queue run" for segmentation
# and threshold resets. Empirically from v1.22 client-main.log (e.g. VSL Unstable):
#   "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at..."
#   "9.4.2026 22:30:53 [Notification] Initialized Server Connection"
#   "9.4.2026 22:30:54 [Notification] Connected to server, downloading data..."
#   "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 113"
#   (sometimes wrapped with "You are in the connection queue." / " Your position in the queue is: N")
# Do NOT treat mid-queue notices like "Server is currently full" as a boundary (not in this list).
# Log line patterns for connection loss vs reconnect (see classify_tail_connection_state).
DISCONNECTED_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bdisconnected\s+by\s+the\s+server\b"),
    re.compile(r"(?i)\bexiting\s+current\s+game\s+to\s+disconnected\s+screen\b"),
    re.compile(r"(?i)\bconnection\s+closed\s+unexpectedly\b"),
    re.compile(r"(?i)\bforcibly\s+closed\s+by\s+the\s+remote\s+host\b"),
    re.compile(r"(?i)\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b"),
    re.compile(r"(?i)\b(?:lost|closed)\s+connection\b"),
    re.compile(r"(?i)\bdisconnect(?:ed|ing)?\b"),
    re.compile(r"(?i)\bconnection\s+kicked\b"),
    re.compile(r"(?i)\bkicked\s+from\b"),
    re.compile(r"(?i)\b(?:was|been)\s+disconnected\b"),
)
# TCP/game teardown often logs errors first, then a definitive session-destroy line. Until that
# final line, treat drop as a reconnect grace window (see classify_tail_connection_state).
GRACE_DISCONNECT_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bconnection\s+closed\s+unexpectedly\b"),
    re.compile(r"(?i)\bforcibly\s+closed\s+by\s+the\s+remote\s+host\b"),
    re.compile(r"(?i)\b(?:lost|closed)\s+connection\b"),
    re.compile(
        r"(?i)\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?"
        r"(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b"
    ),
)
FINAL_CRASH_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)destroying\s+game\s+session"),
    re.compile(r"(?i)waiting\s+up\s+to\s+\d+\s*ms\s+for\s+client\s+threads\s+to\s+exit"),
)
RECONNECTING_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bconnecting\s+to\s+"),
    re.compile(r"(?i)\binitialized\s+server\s+connection\b"),
    re.compile(r"(?i)\bopening\s+connection\b"),
    re.compile(r"(?i)\btrying\s+to\s+connect\b"),
)
QUEUE_RUN_BOUNDARY_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\breconnect(?:ing|ed)?\b"),
    re.compile(r"(?i)\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b"),
    re.compile(r"(?i)\b(?:lost|closed)\s+connection\b"),
    re.compile(r"(?i)\bdisconnect(?:ed|ing)?\b"),
    re.compile(r"(?i)\bopening\s+connection\b"),
    re.compile(r"(?i)\bconnecting\s+to\s+"),
    re.compile(r"(?i)\binitialized\s+server\s+connection\b"),
    re.compile(r"(?i)\btrying\s+to\s+connect\b"),
    re.compile(r"(?i)\breturned\s+to\s+(?:the\s+)?main\s+menu\b"),
    re.compile(r"(?i)\b(?:server|client)\s+shut\s+down\b"),
)
DEFAULT_PATH = "$APPDATA/VintagestoryData/client-main.log"
TAIL_BYTES = 128 * 1024
POPUP_TIMEOUT_MS = 12_000
MAX_GRAPH_POINTS = 5000
MAX_DRAW_POINTS = 1200
DEFAULT_PREDICTION_WINDOW_POINTS = 10
DEFAULT_ALERT_THRESHOLDS = "10, 5, 3, 2, 1"
SEED_LOG_TAIL_BYTES = 2 * 1024 * 1024
QUEUE_RESET_JUMP_THRESHOLD = 10
# After reaching the front (position ≤1), a single +10 jump often re-reads stale lines (e.g. 1→11);
# do not treat that alone as a new queue run (which would clear thresholds and re-alert all).
# Minimum time between popup/sound alerts to suppress duplicate fires from log noise.
ALERT_MIN_INTERVAL_SEC = 12.0
GRAPH_LOG_GAMMA = 1.15
# UI refresh for remaining / weighted avg (ms). Faster than poll so values feel live.
ESTIMATE_TICK_MS = 100
# Exponential recency weight for segment rates (seconds); weights shift as time passes.
SPEED_WEIGHT_TAU_SEC = 90.0
# Vintage Story queue lines typically update about every 30s.
QUEUE_UPDATE_INTERVAL_SEC = 30.0
# If no new queue line is observed for this multiple of the expected update interval, treat as interrupted (stale).
QUEUE_STALE_TIMEOUT_MULT = 2.0
# Server emits log traffic frequently (~2s pings). No file growth/mtime change for this long ⇒ Reconnecting…
LOG_SILENCE_RECONNECT_SEC = 30.0

# UI palette: Grafana-inspired dark (canvas/panel tones, series-style accents, readable contrast).
UI_BG_APP = "#111217"
UI_BG_CARD = "#181b1f"
UI_TEXT_PRIMARY = "#d8d9da"
UI_TEXT_MUTED = "#8e9ba3"
UI_SUMMARY_BG = "#0d0f14"
UI_SUMMARY_VALUE = "#f0f4f8"
UI_ACCENT_POSITION = "#5794f2"
UI_ACCENT_STATUS = "#73bf69"
UI_ACCENT_ELAPSED = "#b877d9"
UI_ACCENT_REMAINING = "#ff9830"
UI_DANGER = "#f2495c"
UI_ENTRY_FIELD = "#0d0f12"
UI_SEPARATOR = "#2e3742"
UI_PROGRESS_TROUGH = "#2e3742"
UI_BUTTON_BG = "#2e3742"
UI_BUTTON_BG_ACTIVE = "#384556"
UI_GRAPH_BG = "#0d0f12"
# Filled plot area: slightly lifted from canvas margin — contrast without a stroked border.
UI_GRAPH_PLOT = "#141820"
UI_GRAPH_GRID = "#1e232c"
UI_GRAPH_AXIS = "#4a5260"
UI_GRAPH_TEXT = "#9fa7b3"
UI_GRAPH_LINE = "#5794f2"
UI_GRAPH_MARKER = "#6b9bd6"
UI_GRAPH_EMPTY = "#6e7680"
UI_TOOLTIP_BG = "#1f2329"
UI_TOOLTIP_FG = "#d8d9da"


def parse_alert_thresholds(raw: str) -> list[int]:
    """Comma-separated queue positions (default 10, 5, 3, 2, 1); each fires at most once per
    downward crossing until a new queue run (log boundary lines and/or large upward jump; see poll + compute_alert).
    """
    out: list[int] = []
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    if not out:
        raise ValueError("Add at least one alert threshold (e.g. 10, 5, 3, 2, 1).")
    for t in out:
        if t < 1:
            raise ValueError(f"Alert threshold {t} must be >= 1.")
    return sorted(set(out), reverse=True)


def expand_path(raw: str) -> Path:
    expanded = os.path.expandvars(raw.strip())
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def get_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "vs-q-monitor" / "config.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vs-q-monitor" / "config.json"


def load_config() -> dict:
    path = get_config_path()
    try:
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_config(data: dict) -> None:
    path = get_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        tmp.replace(path)
    except Exception:
        pass


def resolve_log_file(raw: str) -> Optional[Path]:
    path = expand_path(raw)

    if path.is_file():
        return path

    if not path.exists() or not path.is_dir():
        return None

    candidate_paths: list[Path] = [
        path / "client-main.log",
        path / "Logs" / "client-main.log",
        path / "logs" / "client-main.log",
        path / "client.log",
        path / "Logs" / "client.log",
        path / "logs" / "client.log",
    ]

    for candidate in candidate_paths:
        if candidate.is_file():
            return candidate

    matches: list[Path] = []
    patterns = ["client-main.log", "*client-main*.log", "*client*.log"]
    for pattern in patterns:
        try:
            matches.extend(path.rglob(pattern))
        except Exception:
            pass

    file_matches = [m for m in matches if m.is_file()]
    if not file_matches:
        return None

    file_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return file_matches[0]


def read_log_file_tail_text(log_file: Path, tail_bytes: int) -> Optional[str]:
    try:
        with log_file.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - tail_bytes)
            handle.seek(start)
            raw = handle.read()
    except Exception:
        return None
    return decode_log_bytes(raw, start_offset=start)


def is_queue_run_boundary_line(line: str) -> bool:
    """True for log lines that indicate a new connection attempt / queue run (not position updates)."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    for pat in QUEUE_RUN_BOUNDARY_RES:
        if pat.search(s):
            return True
    return False


def is_disconnected_line(line: str) -> bool:
    """Log line indicates the client is no longer in the connect queue (failure / drop)."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    for pat in DISCONNECTED_LINE_RES:
        if pat.search(s):
            return True
    return False


def is_grace_disconnect_line(line: str) -> bool:
    """Mid-teardown errors before the game logs a definitive session-destroy line."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    for pat in GRACE_DISCONNECT_LINE_RES:
        if pat.search(s):
            return True
    return False


def is_final_crash_line(line: str) -> bool:
    """Definitive crash / teardown after grace (then we treat as Interrupted)."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    for pat in FINAL_CRASH_LINE_RES:
        if pat.search(s):
            return True
    return False


def is_hard_disconnect_line(line: str) -> bool:
    """Disconnect that is not grace-period noise (kick, menu, explicit disconnect, …)."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    if is_grace_disconnect_line(s) or is_final_crash_line(s):
        return False
    return is_disconnected_line(s)


def is_reconnecting_line(line: str) -> bool:
    """Log line indicates a new connection attempt is in progress (after disconnect or cold start)."""
    s = line.strip()
    if not s or queue_position_match(s):
        return False
    for pat in RECONNECTING_LINE_RES:
        if pat.search(s):
            return True
    return False


def classify_tail_connection_state(data: str) -> tuple[str, Optional[int]]:
    """Scan log tail in order; last relevant line wins.

    Returns (kind, last_queue_position) where kind is
    'disconnected' | 'reconnecting' | 'grace' | 'queue' | 'unknown'.

    Grace-period TCP errors match `GRACE_DISCONNECT_LINE_RES` and yield ``grace`` until
    `FINAL_CRASH_LINE_RES` (e.g. destroying game session) marks a definitive teardown (disconnected).
    """
    last_kind = "unknown"
    last_pos: Optional[int] = None
    for line in data.splitlines():
        s = line.strip()
        if not s:
            continue
        m = queue_position_match(s)
        if m:
            try:
                last_pos = int(m.group(1))
                last_kind = "queue"
            except Exception:
                pass
            continue
        if is_reconnecting_line(s):
            last_kind = "reconnecting"
            continue
        if is_final_crash_line(s):
            last_kind = "disconnected"
            continue
        if is_grace_disconnect_line(s):
            last_kind = "grace"
            continue
        if is_hard_disconnect_line(s):
            last_kind = "disconnected"
            continue
    return last_kind, last_pos


def walk_queue_position_events(data: str) -> list[tuple[float, int, int]]:
    """Parse queue position events as (time, position, queue_run_session); sorted by time."""
    out: list[tuple[float, int, int]] = []
    session = 0
    last_t: Optional[float] = None
    last_pos: Optional[int] = None
    for line in data.splitlines():
        if is_queue_run_boundary_line(line):
            session += 1
            continue
        m = queue_position_match(line)
        if not m:
            continue
        try:
            pos = int(m.group(1))
        except Exception:
            continue
        if last_pos is not None and pos == last_pos:
            continue
        t = parse_log_timestamp_epoch(line)
        if t is None:
            t = (last_t + 1.0) if last_t is not None else time.time()
        last_t = t
        last_pos = pos
        out.append((t, pos, session))
    out.sort(key=lambda x: x[0])
    return out


def parse_tail_last_queue_reading(data: str) -> tuple[Optional[int], int]:
    """Latest queue position in the buffer and its run session (0 = no boundary seen in tail)."""
    ev = walk_queue_position_events(data)
    if not ev:
        return None, 0
    _t, pos, sess = ev[-1]
    return pos, sess


def parse_tail_last_queue_line_epoch(data: str) -> Optional[float]:
    """Last timestamp (epoch seconds) of any raw queue line in the buffer.

    Unlike `walk_queue_position_events`, this does NOT de-duplicate repeated positions; it is used
    for liveness (are new queue lines still arriving?).
    """
    last_t: Optional[float] = None
    for line in data.splitlines():
        if not queue_position_match(line):
            continue
        t = parse_log_timestamp_epoch(line)
        if t is None:
            # If the log line has no timestamp, treat presence as "fresh" (we saw it in the tail).
            t = time.time()
        last_t = t
    return last_t


def decode_log_bytes(raw: bytes, start_offset: int = 0) -> str:
    # Vintage Story logs are typically UTF-8, but some environments can produce UTF-16.
    # Heuristic: if the buffer has many NUL bytes, try UTF-16.
    if not raw:
        return ""

    sample = raw[:4096]
    nul_ratio = sample.count(b"\x00") / max(1, len(sample))
    if nul_ratio > 0.05:
        # If we sliced from the middle of a UTF-16 file, ensure 2-byte alignment.
        if start_offset % 2 == 1 and len(raw) > 1:
            raw = raw[1:]
        for enc in ("utf-16-le", "utf-16-be", "utf-16"):
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:
                pass

    return raw.decode("utf-8", errors="ignore")


def extract_recent_positions_from_log(log_file: Path, tail_bytes: int) -> list[int]:
    try:
        with log_file.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - tail_bytes)
            handle.seek(start)
            raw = handle.read()
    except Exception:
        return []

    data = decode_log_bytes(raw, start_offset=start)
    out: list[int] = []
    for line in data.splitlines():
        m = queue_position_match(line)
        if not m:
            continue
        try:
            out.append(int(m.group(1)))
        except Exception:
            pass
    return out


TS_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\b")


def parse_log_timestamp_epoch(line: str) -> Optional[float]:
    m = TS_RE.match(line)
    if not m:
        return None
    try:
        d, mo, y, hh, mm, ss = (int(m.group(i)) for i in range(1, 7))
        return datetime(y, mo, d, hh, mm, ss).timestamp()
    except Exception:
        return None


def extract_recent_points_with_sessions_from_log(
    log_file: Path, tail_bytes: int,
) -> list[tuple[float, int, int]]:
    text = read_log_file_tail_text(log_file, tail_bytes)
    if text is None:
        return []
    return walk_queue_position_events(text)


def extract_recent_points_from_log(log_file: Path, tail_bytes: int) -> list[tuple[float, int]]:
    return [(t, p) for t, p, _s in extract_recent_points_with_sessions_from_log(log_file, tail_bytes)]


def find_current_queue_segment_start_index(positions: list[int]) -> int:
    if len(positions) < 2:
        return 0
    for i in range(len(positions) - 1, 0, -1):
        if positions[i] - positions[i - 1] >= QUEUE_RESET_JUMP_THRESHOLD:
            return i
    return 0


def segment_queue_points(points: list[tuple[float, int, int]]) -> list[tuple[float, int]]:
    """Current queue run: prefer log-derived session id, else large upward jump in positions."""
    if not points:
        return []
    max_sess = max(s for _t, _p, s in points)
    if max_sess > 0:
        seg = [(t, p) for t, p, s in points if s == max_sess]
        if seg:
            return seg
    flat = [(t, p) for t, p, _s in points]
    pos_list = [p for _t, p in flat]
    start_idx = find_current_queue_segment_start_index(pos_list)
    return flat[start_idx:]


def compute_seed_graph_from_log(
    log_file: Path,
) -> Optional[tuple[list[tuple[float, int]], int, int, float, int, int, int]]:
    """Read and parse the log off the UI thread. Returns None if no queue segment was found.

    Last int is queue_run_session_id from the log tail (incremented when boundary lines appear).
    """
    tail_bytes = SEED_LOG_TAIL_BYTES
    points3: list[tuple[float, int, int]] = []
    positions: list[int] = []
    segment_tuples: list[tuple[float, int]] = []
    segment_positions: list[int] = []

    while True:
        points3 = extract_recent_points_with_sessions_from_log(log_file, tail_bytes)
        positions = [p for _t, p, _s in points3]
        segment_tuples = segment_queue_points(points3)
        segment_positions = [p for _t, p in segment_tuples]

        try:
            file_size = log_file.stat().st_size
        except Exception:
            file_size = tail_bytes

        scanned_all = tail_bytes >= file_size
        boundary_found = len(segment_positions) > 0 and len(segment_positions) < len(positions)

        if boundary_found or scanned_all:
            break
        tail_bytes = tail_bytes * 2

    if not segment_positions:
        return None

    text = read_log_file_tail_text(log_file, tail_bytes)
    _, queue_run_session_id = parse_tail_last_queue_reading(text) if text else (None, 0)

    segment_points = segment_tuples[-MAX_GRAPH_POINTS:]
    return (
        segment_points,
        len(segment_positions),
        len(positions),
        tail_bytes / (1024 * 1024),
        min(segment_positions),
        max(segment_positions),
        queue_run_session_id,
    )


class QueueMonitorApp(tk.Tk):
    def __init__(self, initial_path: str = "", auto_start: bool = False) -> None:
        super().__init__()
        self.title(f"Vintage Story Queue Monitor v{VERSION}")
        self.geometry("960x700")
        self.minsize(880, 580)

        self.config: dict = load_config()
        self.source_path_var = tk.StringVar(
            value=initial_path or self.config.get("source_path", "") or DEFAULT_PATH,
        )
        self.resolved_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")
        self.position_var = tk.StringVar(value="—")
        self.last_change_var = tk.StringVar(value="—")
        self.last_alert_var = tk.StringVar(value="—")
        self.elapsed_var = tk.StringVar(value="—")
        self.predicted_remaining_var = tk.StringVar(value="—")
        self.queue_rate_var = tk.StringVar(value="—")
        _at_cfg = self.config.get("alert_thresholds")
        if isinstance(_at_cfg, str) and _at_cfg.strip():
            _alert_default = _at_cfg.strip()
        elif "alert_at" in self.config:
            _alert_default = str(self.config.get("alert_at", "10"))
        else:
            _alert_default = DEFAULT_ALERT_THRESHOLDS
        self.alert_thresholds_var = tk.StringVar(value=_alert_default)
        self.poll_sec_var = tk.StringVar(value=str(self.config.get("poll_sec", "2")))
        self.avg_window_var = tk.StringVar(
            value=str(self.config.get("avg_window_points", DEFAULT_PREDICTION_WINDOW_POINTS)),
        )
        self.show_log_var = tk.BooleanVar(value=bool(self.config.get("show_log", True)))
        self.graph_log_scale_var = tk.BooleanVar(value=bool(self.config.get("graph_log_scale", True)))
        self.popup_enabled_var = tk.BooleanVar(value=bool(self.config.get("popup_enabled", True)))
        self.sound_enabled_var = tk.BooleanVar(value=bool(self.config.get("sound_enabled", True)))
        self.show_every_change_var = tk.BooleanVar(value=bool(self.config.get("show_every_change", False)))

        self.running = False
        self.monitor_start_epoch: Optional[float] = None
        self.timer_job_id: Optional[str] = None
        self.job_id: Optional[str] = None
        self.current_log_file: Optional[Path] = None
        self.last_position: Optional[int] = None
        self.last_alert_position: Optional[int] = None
        self.last_alert_epoch: float = 0.0
        self._alert_thresholds_fired: set[int] = set()
        self.active_popup: Optional[tk.Toplevel] = None
        self.graph_points: deque[tuple[float, int]] = deque(maxlen=MAX_GRAPH_POINTS)
        self.graph_canvas: Optional[tk.Canvas] = None
        self.current_point: Optional[tuple[float, int]] = None
        self.graph_points_drawn: list[tuple[float, int]] = []
        self.graph_tooltip: Optional[tk.Toplevel] = None
        self.history_frame: Optional[ttk.LabelFrame] = None
        self.panes: Optional[tk.PanedWindow] = None
        self.start_stop_button: Optional[ttk.Button] = None
        self._settings_win: Optional[tk.Toplevel] = None
        # When the queue stalls longer than the median rate suggests, reduce this
        # (prediction was optimistic; effective speed for ETA and display).
        self._pred_speed_scale: float = 1.0
        self._stale_slots_accounted: int = 0
        self._starting: bool = False
        self._start_seq: int = 0
        self._loading_spinner: Optional[ttk.Progressbar] = None
        self._queue_progress: Optional[ttk.Progressbar] = None
        self._status_value_label: Optional[tk.Label] = None
        # Wall time when we first observed position ≤1 this run; used to freeze "queue total" elapsed.
        self._position_one_reached_at: Optional[float] = None
        self._persist_config_job: Optional[str] = None
        # Log-derived queue run id (see QUEUE_RUN_BOUNDARY_RES); resets threshold state when it increases.
        self._last_queue_run_session: int = -1
        # Liveness: last time queue *position number* changed (used for dwell/avg caps).
        self._last_queue_position_change_epoch: Optional[float] = None
        # Liveness: last time we observed ANY queue line in the tail (raw sampling; includes repeats).
        self._last_queue_line_epoch: Optional[float] = None
        # Log file st_size + st_mtime; bumps when either changes (new writes or rotation).
        self._last_log_stat: Optional[tuple[int, float]] = None
        self._last_log_growth_epoch: Optional[float] = None
        self._queue_stale_latched: bool = False
        self._queue_stale_logged_once: bool = False
        # Minutes/position dwell cap: min/pos may drop anytime, but may only rise once we've already
        # waited at least the expected minutes for the current position.
        self._mpp_floor_position: Optional[int] = None
        self._mpp_floor_value: Optional[float] = None
        # Interrupted: freeze elapsed but keep polling the log; offer to load a new queue run when detected.
        self._interrupted_mode: bool = False
        self._interrupt_baseline_session: int = -1
        self._dismissed_new_queue_session: Optional[int] = None
        self._interrupted_elapsed_sec: Optional[float] = None

        self._build_ui()
        self.avg_window_var.trace_add("write", self._on_avg_window_write)
        self._bind_config_persist_traces()
        self.start_timer()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.write_history(f"App started. Waiting for a path. Parser looks for queue lines like 'Client is in connect queue at position: N'.")

        # Graph history is seeded from the log when monitoring starts.

        try:
            geometry = self.config.get("window_geometry", "")
            if isinstance(geometry, str) and geometry:
                self.geometry(geometry)
        except Exception:
            pass

        if auto_start:
            self.after(250, self.start_monitoring)

    def _configure_ttk_theme(self, style: ttk.Style) -> None:
        """Apply app-wide background and text colors (clam, Grafana-style dark)."""
        # Clam draws many widgets with lightcolor/darkcolor; if left default, borders read as white on Windows.
        _bd = UI_SEPARATOR
        _card = UI_BG_CARD
        self.configure(bg=UI_BG_APP)
        style.configure("App.TFrame", background=UI_BG_APP)
        style.configure("TFrame", background=_card, borderwidth=0)
        style.configure("Card.TFrame", background=_card)
        style.configure("TLabel", background=_card, foreground=UI_TEXT_PRIMARY)
        style.configure(
            "TLabelframe",
            background=_card,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=_bd,
            lightcolor=_bd,
            relief="flat",
            borderwidth=1,
        )
        style.configure("TLabelframe.Label", background=_card, foreground=UI_TEXT_MUTED)
        style.configure(
            "TCheckbutton",
            background=_card,
            foreground=UI_TEXT_PRIMARY,
            focuscolor=_card,
        )
        style.map("TCheckbutton", background=[("active", _card)])
        style.configure(
            "TButton",
            padding=(10, 4),
            background=UI_BUTTON_BG,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=UI_BUTTON_BG,
            lightcolor=UI_BUTTON_BG_ACTIVE,
            focuscolor=UI_BUTTON_BG,
        )
        style.map(
            "TButton",
            background=[("active", UI_BUTTON_BG_ACTIVE), ("pressed", UI_BUTTON_BG_ACTIVE)],
            darkcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
            lightcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
        )
        style.configure(
            "TEntry",
            fieldbackground=UI_ENTRY_FIELD,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=UI_ENTRY_FIELD,
            lightcolor=UI_ENTRY_FIELD,
            insertcolor=UI_TEXT_PRIMARY,
        )
        style.map("TEntry", focuscolor=[("!focus", UI_ENTRY_FIELD), ("focus", _bd)])
        style.configure("TSeparator", background=UI_SEPARATOR)
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=UI_PROGRESS_TROUGH,
            background=UI_ACCENT_POSITION,
            thickness=8,
            bordercolor=_bd,
            darkcolor=UI_PROGRESS_TROUGH,
            lightcolor=UI_PROGRESS_TROUGH,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=_card,
            troughcolor=UI_BG_APP,
            bordercolor=_bd,
            darkcolor=_bd,
            lightcolor=_bd,
            arrowcolor=UI_TEXT_MUTED,
            arrowsize=12,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", UI_BUTTON_BG), ("pressed", UI_BUTTON_BG_ACTIVE)],
            darkcolor=[("active", _bd)],
            lightcolor=[("active", _bd)],
        )

    def _build_ui(self) -> None:
        try:
            style = ttk.Style()
            if "clam" in style.theme_names():
                style.theme_use("clam")
            self._configure_ttk_theme(style)
        except Exception:
            pass

        outer = ttk.Frame(self, padding=(16, 14), style="App.TFrame")
        outer.pack(fill="both", expand=True)

        # Top bar: log path + transport + history panel toggle. Other options in Settings (gear).
        top = ttk.Frame(outer, style="Card.TFrame", padding=(0, 0, 0, 10))
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Log file or folder").grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=(0, 4))
        path_row = ttk.Frame(top, style="Card.TFrame")
        path_row.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        path_row.columnconfigure(0, weight=1)
        entry = ttk.Entry(path_row, textvariable=self.source_path_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(path_row, text="Browse file", command=self.browse_file).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(path_row, text="Browse folder", command=self.browse_folder).grid(row=0, column=2)

        ttk.Separator(top, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        actions_row = ttk.Frame(top, style="Card.TFrame")
        actions_row.grid(row=2, column=0, columnspan=2, sticky="ew")
        actions_row.columnconfigure(0, weight=1)
        actions = ttk.Frame(actions_row, style="Card.TFrame")
        actions.grid(row=0, column=0, sticky="w")
        self.start_stop_button = ttk.Button(actions, text="Start", command=self.toggle_monitoring)
        self.start_stop_button.pack(side="left", padx=(0, 10))
        self._loading_spinner = ttk.Progressbar(actions, mode="indeterminate", length=100)
        ttk.Button(actions, text="Resolve path", command=self.resolve_and_show).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(
            actions,
            text="History panel",
            variable=self.show_log_var,
            command=self.update_log_visibility,
        ).pack(side="left", padx=(16, 0))
        ttk.Button(
            actions_row,
            text="\u2699  Settings",
            command=self.open_settings,
        ).grid(row=0, column=1, sticky="e")

        # Classic tk.PanedWindow: visible, grabbable sashes (ttk’s are often too thin on Windows).
        # PanedWindow does not support highlightthickness on all Tk builds (e.g. Windows + Python 3.14).
        panes = tk.PanedWindow(
            outer,
            orient=tk.VERTICAL,
            sashwidth=6,
            sashrelief=tk.FLAT,
            sashpad=2,
            bd=0,
        )
        try:
            panes.configure(opaqueresize=True)
        except Exception:
            pass
        try:
            panes.configure(background=UI_BG_APP)
        except Exception:
            pass
        self.panes = panes
        panes.pack(fill="both", expand=True, pady=(14, 0))

        graph_frame = ttk.LabelFrame(panes, text="Queue graph", padding=(4, 6, 4, 4))
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=1)
        self.graph_canvas = tk.Canvas(
            graph_frame, height=200, highlightthickness=0, background=UI_GRAPH_BG, bd=0, highlightbackground=UI_GRAPH_BG
        )
        self.graph_canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.graph_canvas.bind("<Configure>", lambda _evt: self.redraw_graph())
        self.graph_canvas.bind("<Motion>", self.on_graph_motion)
        self.graph_canvas.bind("<Leave>", lambda _evt: self.hide_graph_tooltip())

        status = ttk.LabelFrame(panes, text="Status", padding=(4, 6, 4, 2))
        status.columnconfigure(0, weight=1)

        # Summary bar: Position + Status; Elapsed + Remaining grouped side by side on the right
        summary = tk.Frame(status, bg=UI_SUMMARY_BG, padx=14, pady=12)
        summary.grid(row=0, column=0, sticky="ew")
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)

        tk.Label(
            summary, text="POSITION", bg=UI_SUMMARY_BG, fg=UI_ACCENT_POSITION, font=("TkDefaultFont", 9, "bold")
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            summary,
            textvariable=self.position_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=("TkDefaultFont", 24, "bold"),
        ).grid(row=1, column=0, sticky="w")

        tk.Label(
            summary, text="STATUS", bg=UI_SUMMARY_BG, fg=UI_ACCENT_STATUS, font=("TkDefaultFont", 9, "bold")
        ).grid(row=0, column=1, sticky="w", padx=(18, 0))
        self._status_value_label = tk.Label(
            summary,
            textvariable=self.status_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=("TkDefaultFont", 13, "bold"),
        )
        self._status_value_label.grid(row=1, column=1, sticky="w", padx=(18, 0))

        time_pair = tk.Frame(summary, bg=UI_SUMMARY_BG)
        time_pair.grid(row=0, column=2, rowspan=2, sticky="e", padx=(24, 0))
        tk.Label(
            time_pair, text="ELAPSED", bg=UI_SUMMARY_BG, fg=UI_ACCENT_ELAPSED, font=("TkDefaultFont", 9, "bold")
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            time_pair,
            textvariable=self.elapsed_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=1, column=0, sticky="w")
        tk.Label(
            time_pair,
            text="REMAINING",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_REMAINING,
            font=("TkDefaultFont", 9, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(20, 0))
        tk.Label(
            time_pair,
            textvariable=self.predicted_remaining_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=1, column=1, sticky="w", padx=(20, 0))

        pbar_frame = tk.Frame(summary, bg=UI_SUMMARY_BG)
        pbar_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        pbar_frame.columnconfigure(0, weight=1)
        rate_row = tk.Frame(pbar_frame, bg=UI_SUMMARY_BG)
        rate_row.grid(row=0, column=0, sticky="ew")
        tk.Label(
            rate_row,
            text="MIN/POS",
            bg=UI_SUMMARY_BG,
            fg=UI_TEXT_MUTED,
            font=("TkDefaultFont", 8, "bold"),
        ).pack(side="left")
        tk.Label(
            rate_row,
            textvariable=self.queue_rate_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=("TkDefaultFont", 11),
        ).pack(side="left", padx=(8, 0))
        self._queue_progress = ttk.Progressbar(
            pbar_frame,
            mode="determinate",
            maximum=100.0,
        )
        self._queue_progress.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.history_frame = ttk.LabelFrame(panes, text="History", padding=(4, 6, 4, 4))
        self.history_frame.rowconfigure(0, weight=1)
        self.history_frame.columnconfigure(0, weight=1)

        # stretch: extra vertical space goes mostly to graph + history; status stays content-sized.
        panes.add(graph_frame, minsize=120, stretch="always")
        panes.add(status, minsize=200, stretch="never")
        panes.add(self.history_frame, minsize=100, stretch="always")

        details = ttk.Frame(status, padding=(12, 8, 12, 10), style="Card.TFrame")
        details.grid(row=1, column=0, sticky="ew")
        details.columnconfigure(1, weight=1)
        details.columnconfigure(3, weight=1)

        wrap = 420
        ttk.Label(details, text="Last change").grid(row=0, column=0, sticky="nw", padx=(0, 10), pady=5)
        ttk.Label(details, textvariable=self.last_change_var, wraplength=wrap).grid(
            row=0, column=1, sticky="nw", pady=5
        )
        ttk.Label(details, text="Last threshold alert").grid(row=0, column=2, sticky="nw", padx=(0, 10), pady=5)
        ttk.Label(details, textvariable=self.last_alert_var, wraplength=wrap).grid(
            row=0, column=3, sticky="nw", pady=5
        )
        ttk.Label(details, text="Resolved log path").grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=5)
        ttk.Label(details, textvariable=self.resolved_path_var, wraplength=wrap * 2).grid(
            row=1, column=1, columnspan=3, sticky="nw", pady=5
        )

        self.history_text = tk.Text(
            self.history_frame,
            height=18,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 9) if sys.platform.startswith("win") else ("TkDefaultFont", 10),
            padx=8,
            pady=8,
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
            insertbackground=UI_TEXT_PRIMARY,
            highlightthickness=0,
            borderwidth=0,
        )
        self.history_text.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=4)
        scrollbar = ttk.Scrollbar(self.history_frame, orient="vertical", command=self.history_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_text.configure(yscrollcommand=scrollbar.set)

        self.update_log_visibility()
        self.update_start_stop_button()

    def open_settings(self) -> None:
        """Alerts, polling, and display options — kept out of the main layout (Material-style gear entry)."""
        if self._settings_win is not None:
            try:
                if self._settings_win.winfo_exists():
                    self._settings_win.lift()
                    self._settings_win.focus_force()
                    return
            except Exception:
                pass
            self._settings_win = None

        win = tk.Toplevel(self)
        self._settings_win = win
        win.title("Settings")
        win.configure(bg=UI_BG_CARD)
        try:
            win.transient(self)
        except Exception:
            pass
        win.minsize(440, 360)
        win.geometry("480x400")

        outer = ttk.Frame(win, padding=(16, 14), style="Card.TFrame")
        outer.pack(fill="both", expand=True)

        alerts_fr = ttk.LabelFrame(outer, text="Alerts & polling", padding=(10, 8))
        alerts_fr.pack(fill="x", pady=(0, 8))
        alerts_fr.columnconfigure(1, weight=1)

        ttk.Label(alerts_fr, text="Thresholds (comma-separated)").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(alerts_fr, textvariable=self.alert_thresholds_var, width=36).grid(
            row=0, column=1, sticky="ew", padx=(0, 12)
        )
        ttk.Label(alerts_fr, text="Poll (s)").grid(row=0, column=2, sticky="w", padx=(0, 6))
        ttk.Entry(alerts_fr, width=6, textvariable=self.poll_sec_var).grid(row=0, column=3, sticky="w")

        checks1 = ttk.Frame(alerts_fr, style="Card.TFrame")
        checks1.grid(row=1, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Checkbutton(checks1, text="Alert popup", variable=self.popup_enabled_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(checks1, text="Alert sound", variable=self.sound_enabled_var).pack(side="left", padx=(0, 14))
        ttk.Checkbutton(checks1, text="Log every position change", variable=self.show_every_change_var).pack(
            side="left", padx=(0, 0)
        )

        display_fr = ttk.LabelFrame(outer, text="Graph & prediction", padding=(10, 8))
        display_fr.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(
            display_fr,
            text="Log scale on graph Y axis",
            variable=self.graph_log_scale_var,
            command=self.redraw_graph,
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Label(display_fr, text="Prediction window (points)").grid(row=0, column=1, sticky="w", padx=(0, 8))
        ttk.Entry(display_fr, width=8, textvariable=self.avg_window_var).grid(row=0, column=2, sticky="w")

        bottom = ttk.Frame(outer, style="Card.TFrame")
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Reset defaults", command=self.reset_defaults).pack(side="left")

        def close_settings() -> None:
            try:
                win.grab_release()
            except Exception:
                pass
            self._settings_win = None
            try:
                win.destroy()
            except Exception:
                pass
            self.persist_config()
            self.update_log_visibility()
            self.redraw_graph()

        ttk.Button(bottom, text="Close", command=close_settings).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", close_settings)

        try:
            win.grab_set()
        except Exception:
            pass

        win.update_idletasks()
        try:
            self.update_idletasks()
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            ww = win.winfo_width()
            wh = win.winfo_height()
            win.geometry(f"+{px + max(0, (pw - ww) // 2)}+{py + max(0, (ph - wh) // 2)}")
        except Exception:
            pass

    def _on_avg_window_write(self, *_args: object) -> None:
        """Recompute avg speed / remaining when the rolling window size changes."""
        self.update_time_estimates()

    def update_start_stop_button(self) -> None:
        if self.start_stop_button is None:
            return
        self.start_stop_button.configure(text=("Stop" if self.running else "Start"))

    def toggle_monitoring(self) -> None:
        if self._starting:
            return
        if self.running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def get_config_snapshot(self) -> dict:
        return {
            "source_path": self.source_path_var.get(),
            "alert_thresholds": self.alert_thresholds_var.get(),
            "poll_sec": self.poll_sec_var.get(),
            "avg_window_points": self.avg_window_var.get(),
            "show_log": bool(self.show_log_var.get()),
            "graph_log_scale": bool(self.graph_log_scale_var.get()),
            "popup_enabled": bool(self.popup_enabled_var.get()),
            "sound_enabled": bool(self.sound_enabled_var.get()),
            "show_every_change": bool(self.show_every_change_var.get()),
            "window_geometry": self.geometry(),
            "version": VERSION,
        }

    def persist_config(self) -> None:
        save_config(self.get_config_snapshot())

    def _schedule_config_persist(self, *_args: object) -> None:
        if self._persist_config_job is not None:
            try:
                self.after_cancel(self._persist_config_job)
            except Exception:
                pass
        self._persist_config_job = self.after(450, self._flush_config_persist)

    def _flush_config_persist(self) -> None:
        self._persist_config_job = None
        try:
            self.persist_config()
        except Exception:
            pass

    def _bind_config_persist_traces(self) -> None:
        """Save config.json shortly after any setting change (debounced)."""
        for var in (
            self.source_path_var,
            self.alert_thresholds_var,
            self.poll_sec_var,
            self.avg_window_var,
            self.show_log_var,
            self.graph_log_scale_var,
            self.popup_enabled_var,
            self.sound_enabled_var,
            self.show_every_change_var,
        ):
            var.trace_add("write", self._schedule_config_persist)

    def reset_defaults(self) -> None:
        self.stop_monitoring()

        self.source_path_var.set(DEFAULT_PATH)
        self.alert_thresholds_var.set(DEFAULT_ALERT_THRESHOLDS)
        self.poll_sec_var.set("2")
        self.avg_window_var.set(str(DEFAULT_PREDICTION_WINDOW_POINTS))
        self.show_log_var.set(True)
        self.graph_log_scale_var.set(True)
        self.popup_enabled_var.set(True)
        self.sound_enabled_var.set(True)
        self.show_every_change_var.set(False)

        self.resolved_path_var.set("")
        self._set_status_line("Idle")
        self.position_var.set("—")
        self.elapsed_var.set("—")
        self.predicted_remaining_var.set("—")
        self.queue_rate_var.set("—")
        self.last_change_var.set("—")
        self.last_alert_var.set("—")
        if self._queue_progress is not None:
            self._queue_progress.configure(value=0.0)

        self._position_one_reached_at = None
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
        self._interrupted_mode = False
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self.graph_points.clear()
        self.current_point = None
        self._alert_thresholds_fired.clear()
        self.redraw_graph()

        self.persist_config()
        self.write_history("Settings reset to defaults.")

        self.update_log_visibility()

    def update_log_visibility(self) -> None:
        if self.history_frame is None or self.panes is None:
            return
        panes = self.panes
        history = self.history_frame
        # tk.PanedWindow.panes() returns Tcl_Obj refs — not hashable; normalize to str for set lookup.
        pane_widgets = {str(p) for p in panes.panes()}

        if self.show_log_var.get():
            if str(history) not in pane_widgets:
                panes.add(history, minsize=100, stretch="always")
        else:
            if str(history) in pane_widgets:
                panes.forget(history)

    def write_history(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history_text.configure(state="normal")
        self.history_text.insert("end", f"[{timestamp}] {message}\n")
        self.history_text.see("end")
        self.history_text.configure(state="disabled")

    def _set_status_line(self, text: str, *, danger: bool = False) -> None:
        self.status_var.set(text)
        if self._status_value_label is not None:
            self._status_value_label.configure(fg=UI_DANGER if danger else UI_SUMMARY_VALUE)

    def browse_file(self) -> None:
        selected = filedialog.askopenfilename(title="Select client log")
        if selected:
            self.source_path_var.set(selected)

    def browse_folder(self) -> None:
        selected = filedialog.askdirectory(title="Select folder to search")
        if selected:
            self.source_path_var.set(selected)

    def resolve_and_show(self) -> None:
        resolved = resolve_log_file(self.source_path_var.get())
        if resolved:
            self.resolved_path_var.set(str(resolved))
            self.write_history(f"Resolved path to: {resolved}")
            messagebox.showinfo("Resolved", f"Using log file:\n\n{resolved}")
        else:
            self.resolved_path_var.set("")
            messagebox.showerror("Not found", "Could not find client-main.log from that file or directory.")

    def parse_int(self, raw: str, name: str, minimum: int = 0) -> int:
        try:
            value = int(float(raw))
        except Exception as exc:
            raise ValueError(f"{name} must be a number") from exc
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    def parse_float(self, raw: str, name: str, minimum: float = 0.1) -> float:
        try:
            value = float(raw)
        except Exception as exc:
            raise ValueError(f"{name} must be a number") from exc
        if value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    def _show_start_loading(self, show: bool) -> None:
        if self._loading_spinner is None or self.start_stop_button is None:
            return
        if show:
            self.start_stop_button.configure(state="disabled")
            self._loading_spinner.pack(side="left", padx=(0, 8), after=self.start_stop_button)
            self._loading_spinner.start(12)
        else:
            self._loading_spinner.stop()
            self._loading_spinner.pack_forget()
            self.start_stop_button.configure(state="normal")

    def start_monitoring(self) -> None:
        if self._starting:
            return
        try:
            resolved = resolve_log_file(self.source_path_var.get())
            if not resolved:
                raise ValueError("Could not find client-main.log from that file or directory.")

            try:
                parse_alert_thresholds(self.alert_thresholds_var.get())
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            self._alert_thresholds_fired.clear()
            self._position_one_reached_at = None
            self._last_queue_run_session = -1
            self._last_queue_position_change_epoch = None
            self._queue_stale_latched = False
            self._queue_stale_logged_once = False
            self._mpp_floor_position = None
            self._mpp_floor_value = None
            self.last_alert_epoch = 0.0
            self.poll_sec = self.parse_float(self.poll_sec_var.get(), "Poll sec", 0.2)
        except Exception as exc:
            self._set_status_line("Error")
            messagebox.showerror("Start failed", str(exc))
            return

        self._starting = True
        self._start_seq += 1
        seq = self._start_seq
        self._show_start_loading(True)
        self._set_status_line("Loading log…")

        def worker() -> None:
            try:
                seed_data = compute_seed_graph_from_log(resolved)
            except Exception as exc:
                self.after(0, lambda e=exc: self._finish_start_monitoring(seq, resolved, None, e))
                return
            self.after(0, lambda d=seed_data: self._finish_start_monitoring(seq, resolved, d, None))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_start_monitoring(
        self,
        seq: int,
        resolved: Path,
        seed_data: Optional[tuple[list[tuple[float, int]], int, int, float, int, int, int]],
        error: Optional[Exception],
    ) -> None:
        if seq != self._start_seq:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        self._starting = False
        self._show_start_loading(False)

        if error is not None:
            self._set_status_line("Error")
            self.update_start_stop_button()
            messagebox.showerror("Start failed", str(error))
            return

        self.current_log_file = resolved
        self.resolved_path_var.set(str(resolved))
        self.running = True
        self.monitor_start_epoch = time.time()
        self._interrupted_elapsed_sec = None
        self._interrupted_mode = False
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self._set_status_line("Monitoring")
        self.write_history(f"Monitoring started. Log file: {resolved}")
        self.persist_config()
        self.update_start_stop_button()

        self._apply_seed_result(seed_data)

        self.start_timer()

        if self.job_id is not None:
            self.after_cancel(self.job_id)
            self.job_id = None

        self.poll_once()

    def _last_queue_position_is_connected(self) -> bool:
        """True when the last read position is ≤1 (connected in client-main.log semantics)."""
        pos = self.last_position
        if pos is None and self.current_point is not None:
            pos = self.current_point[1]
        return pos is not None and pos <= 1

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

    def enter_interrupted_state(self, detail: str = "") -> None:
        """Freeze elapsed and show Interrupted, but keep polling the log (no stop)."""
        if self._interrupted_mode:
            return
        self._interrupted_mode = True
        self._interrupted_elapsed_sec = self._snapshot_elapsed_seconds_at_interrupt()
        self._interrupt_baseline_session = self._last_queue_run_session
        self._dismissed_new_queue_session = None
        self._set_status_line("Interrupted", danger=True)
        msg = "Queue interrupted; still watching the log. A new queue run can be loaded when detected."
        if detail:
            msg += f" ({detail})"
        self.write_history(msg)

    def _handle_interrupted_tail(self, position: Optional[int], queue_sess: int) -> None:
        """While interrupted, detect a newer queue session and offer to load it."""
        if (
            position is not None
            and queue_sess > self._interrupt_baseline_session
            and queue_sess != self._dismissed_new_queue_session
        ):
            if messagebox.askyesno(
                "New queue detected",
                "A new queue run was detected in the log.\n\n"
                "Load it? This will reset the graph and threshold alerts for the new run.",
                parent=self,
            ):
                self._accept_new_queue_from_log()
            else:
                self._dismissed_new_queue_session = queue_sess

    def _accept_new_queue_from_log(self) -> None:
        """Leave interrupted state and seed the graph from the current log (new queue run)."""
        self._interrupted_mode = False
        self._interrupted_elapsed_sec = None
        self._dismissed_new_queue_session = None
        self._interrupt_baseline_session = -1
        path = self.current_log_file
        if path is None or not path.is_file():
            self.write_history("Cannot load new queue: log file missing.")
            return
        data = compute_seed_graph_from_log(path)
        if data is None:
            self.write_history("Could not find queue data in the log for the new run.")
            self._set_status_line("Watching log, queue line not found yet")
            return
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._position_one_reached_at = None
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        self._alert_thresholds_fired.clear()
        self._apply_seed_result(data)
        self._set_status_line("Monitoring")

    def stop_monitoring(self) -> None:
        self._interrupted_mode = False
        self._interrupted_elapsed_sec = None
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
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
        if self._last_queue_position_is_connected():
            self._set_status_line("Completed")
            self.write_history("Monitoring stopped (completed).")
        else:
            self._set_status_line("Stopped")
            self.write_history("Monitoring stopped.")
        if self.job_id is not None:
            self.after_cancel(self.job_id)
            self.job_id = None
        self.update_start_stop_button()

    def start_timer(self) -> None:
        if self.timer_job_id is not None:
            try:
                self.after_cancel(self.timer_job_id)
            except Exception:
                pass
            self.timer_job_id = None
        self.tick_timer()

    def stop_timer(self) -> None:
        if self.timer_job_id is not None:
            try:
                self.after_cancel(self.timer_job_id)
            except Exception:
                pass
            self.timer_job_id = None

    def tick_timer(self) -> None:
        self.update_time_estimates()
        self.timer_job_id = self.after(ESTIMATE_TICK_MS, self.tick_timer)

    def _apply_seed_result(
        self,
        data: Optional[tuple[list[tuple[float, int]], int, int, float, int, int, int]],
    ) -> None:
        if data is None:
            return
        segment_points, segment_len, positions_len, tail_mb, seg_min, seg_max, queue_run_session_id = data
        self._last_queue_run_session = queue_run_session_id
        self.graph_points.clear()
        for item in segment_points:
            self.graph_points.append(item)
        self.current_point = segment_points[-1] if segment_points else None
        if self.current_point is not None:
            _t, pos = self.current_point
            self.last_position = pos
            self.position_var.set(str(pos))
        self._pred_speed_scale = 1.0
        self._stale_slots_accounted = 0
        self.redraw_graph()
        self.update_time_estimates()
        self.write_history(
            "Seeded graph from log: "
            f"{min(segment_len, MAX_GRAPH_POINTS)} points "
            f"(segment {segment_len} total, window {positions_len} total, "
            f"min={seg_min}, max={seg_max}, scanned ~{tail_mb:.1f} MB)."
        )

    def seed_graph_from_log(self, log_file: Path) -> None:
        self._apply_seed_result(compute_seed_graph_from_log(log_file))

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
                    self._last_queue_position_change_epoch = None
                    self._queue_stale_latched = False
                    self._queue_stale_logged_once = False
                    self._last_log_stat = None
                    self._last_log_growth_epoch = None
                    self._interrupted_mode = False
                    self._interrupted_elapsed_sec = None
                    self._interrupt_baseline_session = -1
                    self._dismissed_new_queue_session = None
                    self.write_history(f"Now watching: {resolved}")

            if not self.current_log_file or not self.current_log_file.is_file():
                self._set_status_line("Waiting for log file")
            else:
                self._bump_log_activity_if_changed(self.current_log_file)
                text = read_log_file_tail_text(self.current_log_file, TAIL_BYTES)
                if text is None:
                    self._set_status_line("Waiting for log file")
                else:
                    kind, _tail_pos = classify_tail_connection_state(text)
                    position, queue_sess = parse_tail_last_queue_reading(text)
                    last_queue_line_epoch = parse_tail_last_queue_line_epoch(text)
                    if last_queue_line_epoch is not None:
                        self._last_queue_line_epoch = last_queue_line_epoch

                    now = time.time()
                    log_silent = (
                        self._last_log_growth_epoch is not None
                        and now - self._last_log_growth_epoch >= LOG_SILENCE_RECONNECT_SEC
                    )

                    if self._interrupted_mode:
                        self._handle_interrupted_tail(position, queue_sess)
                    elif kind == "disconnected":
                        self.enter_interrupted_state("Connection lost (final teardown).")
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        self.position_var.set("—")
                        self.last_position = None
                    elif kind in ("reconnecting", "grace") or log_silent:
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        if log_silent or kind == "grace":
                            self._set_status_line("Reconnecting…")
                        else:
                            self._set_status_line("Connecting…")
                        self.position_var.set("—")
                        self.last_position = None
                    elif position is not None and not log_silent:
                        prev_pos = self.last_position
                        now = time.time()
                        stale_limit = QUEUE_UPDATE_INTERVAL_SEC * QUEUE_STALE_TIMEOUT_MULT

                        if self._queue_stale_latched:
                            if self._last_queue_line_epoch is not None and now - self._last_queue_line_epoch <= stale_limit:
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                            else:
                                self.enter_interrupted_state("Stale latch (queue lines did not recover).")

                        if not self._interrupted_mode:
                            if position > 1:
                                if prev_pos is None or position != prev_pos:
                                    self._last_queue_position_change_epoch = now
                                    self._queue_stale_logged_once = False
                                elif self._last_queue_position_change_epoch is None:
                                    self._last_queue_position_change_epoch = now
                                if (
                                    self._last_queue_line_epoch is None
                                    or now - self._last_queue_line_epoch > stale_limit
                                ):
                                    self._queue_stale_latched = True
                                    if not self._queue_stale_logged_once:
                                        self.write_history(
                                            f"No new queue log lines for {stale_limit:.0f}s "
                                            f"({QUEUE_STALE_TIMEOUT_MULT:.0f}× expected "
                                            f"{QUEUE_UPDATE_INTERVAL_SEC:.0f}s updates); treating as interrupted."
                                        )
                                        self._queue_stale_logged_once = True
                                    self.enter_interrupted_state("No new queue log lines (stale).")
                            else:
                                self._last_queue_position_change_epoch = None
                                self._queue_stale_logged_once = False

                        if not self._interrupted_mode:
                            if (
                                self._last_queue_run_session >= 0
                                and queue_sess > self._last_queue_run_session
                            ):
                                self._alert_thresholds_fired.clear()
                                self._position_one_reached_at = None
                                self._last_queue_position_change_epoch = time.time()
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                                self._mpp_floor_position = None
                                self._mpp_floor_value = None
                                self.write_history("New queue run (from log).")
                            self._last_queue_run_session = queue_sess
                            self._set_status_line("Completed" if position <= 1 else "Monitoring")
                            self.position_var.set(str(position))
                            self.append_graph_point(position)
                            self.update_time_estimates()

                            if position != prev_pos:
                                # Dwell cap baseline: take a snapshot of min/pos at the moment we enter a position.
                                self._mpp_floor_position = position
                                self._mpp_floor_value = self._minutes_per_position_from_window()
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                                self.last_change_var.set(timestamp)
                                if self.show_every_change_var.get() or prev_pos is None:
                                    self.write_history(f"Queue position: {position}")
                                else:
                                    self.write_history(f"Queue changed: {prev_pos} → {position}")

                            should_alert, reason = self.compute_alert(prev_pos, position)
                            if should_alert:
                                self.raise_alert(position, reason)
                    elif not log_silent:
                        self._set_status_line("Watching log, queue line not found yet")
        except Exception as exc:
            self._set_status_line("Error")
            self.write_history(f"Error: {exc}")
            self.write_history(traceback.format_exc().splitlines()[-1])
        finally:
            if self.running:
                self.job_id = self.after(int(self.poll_sec * 1000), self.poll_once)

    def append_graph_point(self, position: int) -> None:
        now = time.time()
        if self.current_point is not None and self.current_point[1] == position:
            return
        self.current_point = (now, position)
        self.last_position = position
        self._pred_speed_scale = 1.0
        self._stale_slots_accounted = 0
        self.graph_points.append(self.current_point)
        self.redraw_graph()

    def format_duration(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        total = int(round(seconds))
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:d}:{secs:02d}"

    def format_duration_remaining(self, seconds: float) -> str:
        """Remaining ETA with sub-second resolution so the display updates smoothly."""
        seconds = max(0.0, float(seconds))
        if seconds <= 0:
            return "—"
        # Show at least ~1s so the UI does not sit on 0:00.00 while time is left.
        if seconds < 1:
            seconds = 1.0
        if seconds >= 3600:
            total = int(round(seconds))
            hours = total // 3600
            minutes = (total % 3600) // 60
            secs = total % 60
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        m = int(seconds // 60)
        s = seconds % 60.0
        return f"{m:d}:{s:05.2f}"

    @staticmethod
    def _format_queue_rate(mpp: Optional[float]) -> str:
        """Window estimate: average minutes per queue position advanced."""
        if mpp is not None and mpp > 0:
            return f"{mpp:.2f} min/pos"
        return "—"

    def estimate_seconds_remaining(self) -> Optional[float]:
        current_pos = self.last_position
        if current_pos is None and self.current_point is not None:
            current_pos = self.current_point[1]
        # Position 1 in client-main.log means connected, not "next in queue"; no queue ETA.
        if current_pos is None or current_pos <= 1:
            return None

        remaining_positions = max(0, current_pos - 1)

        v_emp = self.compute_empirical_pos_per_sec()
        if v_emp is not None and v_emp > 0:
            speed = v_emp
        else:
            w, nw, _trail_w = self.compute_weighted_speed()
            if w is not None and nw > 0 and w > 0:
                speed = w
            else:
                speed, _n, _trail = self.compute_moving_average_speed()
                if speed is None or speed <= 0:
                    return None

        expected_sec_per_pos = 1.0 / speed
        expected_update_sec = max(QUEUE_UPDATE_INTERVAL_SEC, expected_sec_per_pos)

        # Live countdown even when the log repeats the same position, but clamp so we
        # never display 0:00 while still in queue.
        if self.running and self.current_point is not None and current_pos > 1:
            dt = time.time() - self.current_point[0]
            # Between expected 30s game updates we still want a smooth countdown. Only
            # after we exceed the expected update interval do we treat it as stale.
            if dt >= expected_update_sec:
                missed_count = int(dt / expected_update_sec)
                if missed_count > self._stale_slots_accounted:
                    extra = missed_count - self._stale_slots_accounted
                    self._pred_speed_scale *= 0.92**extra
                    self._pred_speed_scale = max(0.05, self._pred_speed_scale)
                    self._stale_slots_accounted = missed_count
            else:
                self._stale_slots_accounted = 0

            v_eff = speed * self._pred_speed_scale
            base = remaining_positions / v_eff
            # Always smooth countdown (never freeze on stale); correction is in v_eff.
            return max(1.0, base - dt)

        v_eff = speed * self._pred_speed_scale
        return remaining_positions / v_eff

    def compute_moving_average_speed(self) -> tuple[Optional[float], int, list[int]]:
        points = list(self.graph_points)
        if len(points) < 2:
            return None, 0, [p for _t, p in points]

        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10_000, window_points))

        recent = points[-(window_points + 1) :]
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
            return None, 0, trail
        if len(rates) < 3:
            speed = sum(rates) / len(rates)
            if speed <= 0:
                return None, 0, trail
            return speed, len(rates), trail

        rates.sort()
        speed = rates[len(rates) // 2]  # median positions per second
        if speed <= 0:
            return None, 0, trail
        return speed, len(rates), trail

    def compute_weighted_speed(self) -> tuple[Optional[float], int, list[int]]:
        """Recency-weighted mean of segment rates; shifts as wall time passes so the value is live."""
        points = list(self.graph_points)
        if len(points) < 2:
            return None, 0, [p for _t, p in points]

        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10_000, window_points))

        recent = points[-(window_points + 1) :]
        trail = [p for _t, p in recent]
        now = time.time()
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
            return None, 0, trail
        speed = r_sum / w_sum
        if speed <= 0:
            return None, 0, trail
        return speed, n_seg, trail

    def _window_recent_points(self) -> list[tuple[float, int]]:
        """Last N graph points per prediction window setting (same slice as speed helpers)."""
        points = list(self.graph_points)
        if len(points) < 2:
            return []
        try:
            window_points = int(float(self.avg_window_var.get()))
        except Exception:
            window_points = DEFAULT_PREDICTION_WINDOW_POINTS
        window_points = max(2, min(10_000, window_points))
        return points[-(window_points + 1) :]

    def compute_empirical_pos_per_sec(self) -> Optional[float]:
        """Net positions per second over the prediction window.

        While monitoring, time uses wall clock from the window's first point to *now*, so
        dwell at the current queue position (including position 1 before connect) is not
        dropped from the average. Stopped mode uses only log timestamps (snapshot).
        """
        recent = self._window_recent_points()
        if len(recent) < 2:
            return None
        t0, p0 = float(recent[0][0]), float(recent[0][1])
        t1, p1 = float(recent[-1][0]), float(recent[-1][1])
        drop = p0 - p1
        if drop <= 0:
            return None
        if self.running:
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
        if w is not None and nw > 0 and w > 0:
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
        # If we're faster than expected, show it immediately.
        if mpp_raw <= self._mpp_floor_value:
            return mpp_raw
        # Slower than expected: only allow the rise once we've already exceeded the expectation.
        if self._last_queue_position_change_epoch is None:
            return self._mpp_floor_value
        dwell = max(0.0, time.time() - self._last_queue_position_change_epoch)
        if dwell < self._mpp_floor_value * 60.0:
            return self._mpp_floor_value
        return mpp_raw

    def _current_queue_position(self) -> Optional[int]:
        pos = self.last_position
        if pos is None and self.current_point is not None:
            pos = self.current_point[1]
        return pos

    def _queue_elapsed_start_epoch(self) -> Optional[float]:
        """Start of the current queue segment for elapsed: first graph point time, else monitor start."""
        if self.graph_points:
            return self.graph_points[0][0]
        return self.monitor_start_epoch

    def _snapshot_elapsed_seconds_at_interrupt(self) -> Optional[float]:
        """Wall-clock queue elapsed at interrupt (same basis as the live elapsed timer)."""
        start_t = self._queue_elapsed_start_epoch()
        if start_t is None:
            return None
        pos = self._current_queue_position()
        if pos is not None and pos <= 1 and self._position_one_reached_at is not None:
            return max(0.0, self._position_one_reached_at - start_t)
        return max(0.0, time.time() - start_t)

    def update_time_estimates(self) -> None:
        points = list(self.graph_points)
        pos = self._current_queue_position()

        if self._interrupted_elapsed_sec is not None:
            elapsed_sec = self._interrupted_elapsed_sec
            self.elapsed_var.set(self.format_duration(elapsed_sec))
            self.predicted_remaining_var.set("—")
            mpp_raw = self._minutes_per_position_from_window()
            mpp = self._minutes_per_position_capped_for_dwell(mpp_raw, pos)
            self.queue_rate_var.set(self._format_queue_rate(mpp))
            if self._queue_progress is not None:
                self._queue_progress["value"] = 0.0
            return

        if self.running and pos is not None:
            if pos <= 1:
                if self._position_one_reached_at is None:
                    self._position_one_reached_at = time.time()
            else:
                self._position_one_reached_at = None

        start_t = self._queue_elapsed_start_epoch()
        elapsed_sec: Optional[float] = None

        if self.running and self.monitor_start_epoch is not None:
            if start_t is None:
                self.elapsed_var.set("—")
            elif pos is not None and pos <= 1 and self._position_one_reached_at is not None:
                elapsed_sec = max(0.0, self._position_one_reached_at - start_t)
                self.elapsed_var.set(self.format_duration(elapsed_sec))
            else:
                elapsed_sec = max(0.0, time.time() - start_t)
                self.elapsed_var.set(self.format_duration(elapsed_sec))
        elif not self.running and self._position_one_reached_at is not None and len(points) >= 1:
            st = points[0][0]
            elapsed_sec = max(0.0, self._position_one_reached_at - st)
            self.elapsed_var.set(self.format_duration(elapsed_sec))
        elif len(points) >= 2:
            start_t2 = points[0][0]
            end_t = self.current_point[0] if self.current_point is not None else points[-1][0]
            elapsed_sec = max(0.0, end_t - start_t2)
            self.elapsed_var.set(self.format_duration(elapsed_sec))
        else:
            self.elapsed_var.set("—")

        # ETA updates _pred_speed_scale; min/pos prefers empirical window throughput, else model.
        mpp_raw = self._minutes_per_position_from_window()
        mpp = self._minutes_per_position_capped_for_dwell(mpp_raw, pos)
        self.queue_rate_var.set(self._format_queue_rate(mpp))

        # Remaining must use estimate_seconds_remaining() while monitoring so wall time (base − dt)
        # ticks between log lines. A plain (pos−1)*mpp*60 snapshot freezes until the next poll.
        seconds_remaining = self.estimate_seconds_remaining()
        if seconds_remaining is None and pos is not None and pos > 1 and mpp is not None and mpp > 0:
            seconds_remaining = max(0.0, float(pos - 1) * mpp * 60.0)

        if seconds_remaining is None:
            self.predicted_remaining_var.set("—")
        else:
            self.predicted_remaining_var.set(self.format_duration_remaining(seconds_remaining))

        if self._queue_progress is not None:
            if pos is not None and pos <= 1:
                self._queue_progress["value"] = 100.0
            elif elapsed_sec is not None and seconds_remaining is not None:
                total = elapsed_sec + max(0.0, float(seconds_remaining))
                if total > 1e-6:
                    self._queue_progress["value"] = min(
                        100.0, max(0.0, 100.0 * elapsed_sec / total)
                    )
                else:
                    self._queue_progress["value"] = 0.0
            else:
                self._queue_progress["value"] = 0.0

    def redraw_graph(self) -> None:
        canvas = self.graph_canvas
        if canvas is None:
            return
        canvas.delete("all")

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return

        # Leave space for axis labels (especially X time labels).
        pad_left = 58
        pad_right = 12
        pad_top = 10
        pad_bottom = 28
        plot_w = max(1, width - pad_left - pad_right)
        plot_h = max(1, height - pad_top - pad_bottom)

        x0 = pad_left
        y0 = pad_top
        x1 = pad_left + plot_w
        y1 = pad_top + plot_h
        canvas.create_rectangle(x0, y0, x1, y1, fill=UI_GRAPH_PLOT, outline="")

        points = list(self.graph_points)
        if len(points) > MAX_DRAW_POINTS:
            step = max(1, len(points) // MAX_DRAW_POINTS)
            points = points[::step]
        self.graph_points_drawn = points
        if len(points) < 2:
            if len(points) == 1:
                _t, pos = points[0]
                canvas.create_text(x0 + 6, y0 + 6, anchor="nw", text=f"{pos}", fill=UI_GRAPH_TEXT)
            else:
                canvas.create_text(x0 + 6, y0 + 6, anchor="nw", text="No data yet", fill=UI_GRAPH_EMPTY)
            return

        t0 = points[0][0]
        t1 = points[-1][0]
        if t1 <= t0:
            t1 = t0 + 1e-6

        vals = [p for _t, p in points]
        vmin = min(vals)
        vmax = max(vals)
        if vmax == vmin:
            vmax = vmin + 1
        vmin = max(0, vmin)

        def x_of(t: float) -> float:
            return pad_left + (t - t0) / (t1 - t0) * plot_w

        def y_of(v: int) -> float:
            # Smaller queue positions should appear "lower" on the graph.
            vv = max(vmin, min(vmax, v))
            if not self.graph_log_scale_var.get():
                frac = (vmax - vv) / max(1, (vmax - vmin))  # 0 at vmax, 1 at vmin
                return pad_top + frac * plot_h

            # Log scale (with gamma) so low values get more visual resolution.
            lvmin = math.log(vmin + 1.0)
            lvmax = math.log(vmax + 1.0)
            lv = math.log(vv + 1.0)
            if lvmax <= lvmin:
                frac = 0.0
            else:
                frac = (lvmax - lv) / (lvmax - lvmin)  # 0 at vmax, 1 at vmin

            frac = max(0.0, min(1.0, frac))
            frac = frac ** GRAPH_LOG_GAMMA
            return pad_top + frac * plot_h

        # Axes & ticks (grid/axes are soft lines on the solid plot fill — no frame stroke)
        axis_color = UI_GRAPH_AXIS
        text_color = UI_GRAPH_TEXT
        canvas.create_line(x0, y0, x0, y1, fill=axis_color)
        canvas.create_line(x0, y1, x1, y1, fill=axis_color)

        # Y ticks (positions)
        tick_step = 5
        tick_vals: list[int] = []

        # Primary ticks every 5 positions.
        start = (vmin // tick_step) * tick_step
        end = ((vmax + tick_step - 1) // tick_step) * tick_step
        for val in range(start, end + 1, tick_step):
            if vmin <= val <= vmax:
                if val == 0 and vmin > 0:
                    continue
                tick_vals.append(val)

        # When zoomed in low, label 1..5 individually.
        if vmin <= 5 <= vmax:
            tick_vals.extend([1, 2, 3, 4, 5])

        # Ensure endpoints are always labeled.
        tick_vals.extend([vmin, vmax])

        tick_vals = sorted(set(tick_vals), reverse=True)

        last_y_label: Optional[float] = None
        min_label_dy = 16
        for idx, val in enumerate(tick_vals):
            y = y_of(val)
            canvas.create_line(x0 - 4, y, x0, y, fill=axis_color)
            if last_y_label is None or abs(y - last_y_label) >= min_label_dy:
                canvas.create_text(x0 - 6, y, anchor="e", text=str(val), fill=text_color)
                last_y_label = y
            if 0 < idx < len(tick_vals) - 1:
                canvas.create_line(x0, y, x1, y, fill=UI_GRAPH_GRID)

        # X ticks (time) - fixed interval ("5 per tick" style)
        span = t1 - t0
        if span <= 0:
            span = 1.0

        # Prefer intervals that are multiples of 5.
        candidates = [
            5,
            10,
            15,
            30,
            60,
            5 * 60,
            10 * 60,
            15 * 60,
            30 * 60,
            60 * 60,
            2 * 60 * 60,
            6 * 60 * 60,
        ]
        target_ticks = 8
        interval = candidates[-1]
        for c in candidates:
            if span / c <= target_ticks:
                interval = c
                break

        fmt = "%H:%M:%S" if interval < 60 * 60 else "%H:%M"

        first_tick = math.ceil(t0 / interval) * interval
        last_tick = math.floor(t1 / interval) * interval
        tick_times: list[float] = []
        t = first_tick
        while t <= last_tick + 1e-6:
            tick_times.append(t)
            t += interval

        # Ensure endpoints are labeled too.
        if not tick_times or tick_times[0] - t0 > interval * 0.4:
            tick_times.insert(0, t0)
        if tick_times[-1] < t1 - interval * 0.4:
            tick_times.append(t1)

        last_x_label: Optional[float] = None
        min_label_dx = 58
        for idx, t in enumerate(tick_times):
            x = x_of(t)
            label = datetime.fromtimestamp(t).strftime(fmt)
            canvas.create_line(x, y1, x, y1 + 4, fill=axis_color)
            if last_x_label is None or abs(x - last_x_label) >= min_label_dx:
                canvas.create_text(x, y1 + 14, anchor="n", text=label, fill=text_color)
                last_x_label = x
            if 0 < idx < len(tick_times) - 1:
                canvas.create_line(x, y0, x, y1, fill=UI_GRAPH_GRID)

        canvas.create_text(x0 + 6, y0 + 6, anchor="nw", text=f"min {vmin}  max {vmax}", fill=text_color)

        # Step chart: hold position until the next log time, then jump. Raw points are only sampled at
        # log lines — connecting them with diagonals implied fake motion and looked like spikes.
        step_vertices: list[tuple[float, int]] = []
        for i, (t, p) in enumerate(points):
            t_f = float(t)
            p_i = int(p)
            if i == 0:
                step_vertices.append((t_f, p_i))
                continue
            t_prev = float(points[i - 1][0])
            p_prev = int(points[i - 1][1])
            if t_f <= t_prev:
                continue
            if p_i != p_prev:
                step_vertices.append((t_f, p_prev))
            step_vertices.append((t_f, p_i))

        line: list[float] = []
        for t, v in step_vertices:
            line.extend([x_of(t), y_of(v)])

        if len(line) >= 4:
            canvas.create_line(*line, fill=UI_GRAPH_LINE, width=2, smooth=False)

        marker = self.current_point or points[-1]
        last_t, last_v = marker
        lx = x_of(last_t)
        ly = y_of(last_v)
        canvas.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, outline="", fill=UI_GRAPH_MARKER)
        canvas.create_text(lx + 10, ly, anchor="w", text=str(last_v), fill=UI_GRAPH_TEXT)

    def on_graph_motion(self, evt: tk.Event) -> None:
        points = self.graph_points_drawn
        canvas = self.graph_canvas
        if canvas is None or len(points) < 2:
            return

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return

        pad_x = 12
        pad_y = 10
        plot_w = max(1, width - 2 * pad_x)
        plot_h = max(1, height - 2 * pad_y)

        x = max(pad_x, min(pad_x + plot_w, evt.x))
        t0 = points[0][0]
        t1 = points[-1][0]
        if t1 <= t0:
            return
        target_t = t0 + (x - pad_x) / plot_w * (t1 - t0)

        # Find nearest point by time
        best = points[0]
        best_dt = abs(best[0] - target_t)
        for pt in points[1:]:
            dt = abs(pt[0] - target_t)
            if dt < best_dt:
                best = pt
                best_dt = dt

        t, pos = best
        ts = datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
        self.show_graph_tooltip(evt.x_root, evt.y_root, f"{ts}\npos {pos}")

    def show_graph_tooltip(self, x_root: int, y_root: int, text: str) -> None:
        if self.graph_tooltip is None or not self.graph_tooltip.winfo_exists():
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)
            tip.attributes("-topmost", True)
            label = tk.Label(
                tip, text=text, justify="left", background=UI_TOOLTIP_BG, foreground=UI_TOOLTIP_FG, padx=10, pady=8
            )
            label.pack()
            self.graph_tooltip = tip
        else:
            label = self.graph_tooltip.winfo_children()[0]
            if isinstance(label, tk.Label):
                label.configure(text=text)

        self.graph_tooltip.geometry(f"+{x_root + 12}+{y_root + 12}")

    def hide_graph_tooltip(self) -> None:
        if self.graph_tooltip is not None and self.graph_tooltip.winfo_exists():
            try:
                self.graph_tooltip.destroy()
            except Exception:
                pass
        self.graph_tooltip = None

    def compute_alert(self, prev_pos: Optional[int], curr_pos: int) -> tuple[bool, str]:
        """Alert once per CSV threshold when crossing downward (e.g. first time at ≤10, ≤5, …).

        Fired thresholds also reset when poll_once detects a new queue run from log boundary lines.
        Remaining resets: large upward jump (or marginal +10 from front — see code), not small bumps.
        """
        try:
            thresholds = parse_alert_thresholds(self.alert_thresholds_var.get())
        except ValueError:
            return False, ""

        if prev_pos is None:
            return False, ""

        # No new threshold crossings while sitting at the front between polls.
        if prev_pos <= 1 and curr_pos <= 1:
            return False, ""

        jump_up = curr_pos - prev_pos
        if jump_up >= QUEUE_RESET_JUMP_THRESHOLD:
            marginal_spike_from_front = prev_pos <= 1 and jump_up == QUEUE_RESET_JUMP_THRESHOLD
            if not marginal_spike_from_front:
                self._alert_thresholds_fired.clear()

        crossed: list[int] = []
        for t in thresholds:
            if prev_pos > t and curr_pos <= t and t not in self._alert_thresholds_fired:
                crossed.append(t)
                self._alert_thresholds_fired.add(t)

        if not crossed:
            return False, ""

        crossed.sort(reverse=True)
        parts = ", ".join(str(x) for x in crossed)
        return True, f"crossed threshold(s): {parts}"

    def raise_alert(self, position: int, reason: str) -> None:
        now = time.time()
        if self.last_alert_epoch > 0.0 and (now - self.last_alert_epoch) < ALERT_MIN_INTERVAL_SEC:
            return

        self.last_alert_position = position
        self.last_alert_epoch = now
        self.last_alert_var.set(time.strftime("%Y-%m-%d %H:%M:%S"))
        self.write_history(f"Threshold alert: position {position} ({reason})")

        if self.sound_enabled_var.get():
            self.play_sound()
        if self.popup_enabled_var.get():
            self.show_popup(position, reason)

    def play_sound(self) -> None:
        if winsound is not None and sys.platform.startswith("win"):
            for _ in range(6):
                try:
                    winsound.Beep(1400, 180)
                    winsound.Beep(1000, 180)
                except Exception:
                    break
        else:
            self._ring_bell(0)

    def _ring_bell(self, count: int) -> None:
        if count >= 6:
            return
        try:
            self.bell()
        except Exception:
            pass
        self.after(220, lambda: self._ring_bell(count + 1))

    def show_popup(self, position: int, reason: str) -> None:
        if self.active_popup is not None and self.active_popup.winfo_exists():
            try:
                self.active_popup.destroy()
            except Exception:
                pass

        popup = tk.Toplevel(self)
        self.active_popup = popup
        popup.title("Threshold alert")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18, bg=UI_BG_CARD)

        try:
            popup.transient(self)
        except Exception:
            pass

        ttk.Label(
            popup,
            text=f"Queue position is now {position}",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            popup,
            text=f"Reason: {reason}",
            wraplength=360,
        ).pack(anchor="w", pady=(0, 12))
        ttk.Button(popup, text="Dismiss", command=popup.destroy).pack(anchor="e")

        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(40, screen_w - width - 50)
        y = max(40, screen_h - height - 90)
        popup.geometry(f"+{x}+{y}")

        popup.after(POPUP_TIMEOUT_MS, lambda: popup.winfo_exists() and popup.destroy())

    def on_close(self) -> None:
        if self._settings_win is not None:
            try:
                self._settings_win.grab_release()
            except Exception:
                pass
            try:
                self._settings_win.destroy()
            except Exception:
                pass
            self._settings_win = None
        self.persist_config()
        self.stop_monitoring()
        self.stop_timer()
        self.destroy()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vintage Story Queue Monitor GUI")
    parser.add_argument("--path", dest="path", default="", help="Initial file or directory path")
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Do not auto-start monitoring when the app opens",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    app = QueueMonitorApp(initial_path=args.path, auto_start=not args.no_start)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
