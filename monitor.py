#!/usr/bin/env python3
"""
VS Queue Monitor — Vintage Story client log queue monitor (project id: vs-queue-monitor).
Version: 1.0.22

Cross-platform Tkinter app that watches a Vintage Story client log for queue
position changes and raises configurable threshold alerts (popup + sound).

WARNING — WORK IN PROGRESS: Behavior, UI, and saved settings may change without notice.

WARNING — AI-ASSISTED DEVELOPMENT: Much of this codebase was produced or refactored with
AI / coding assistants. Treat paths, alerts, ETAs, and log interpretation as unverified
until you confirm them against your client and logs.

WARNING — NO WARRANTY: Not affiliated with Vintage Story. Use at your own risk.
"""

from __future__ import annotations

import argparse
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
from typing import Any, Callable, Optional, Union

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

VERSION = "1.0.22"
APP_DISPLAY_NAME = "VS Queue Monitor"
APP_TAGLINE = "Vintage Story client log queue monitor"
GITHUB_REPO_URL = "https://github.com/ShubiMaja/vs-queue-monitor"

# Window icon: embedded GIF so ``monitor.py`` ships as one file. Repo copy: ``assets/app_icon.gif`` (same bytes).
_APP_ICON_GIF_B64 = (
    "R0lGODdhQABAAIQAABEUGxUYIAsLEi3H1i/U5CWYpRItNSByfRMwOB9yfBdHUCB5hB5ocyq2wxpTXSmntBU4QSSG"
    "kzLm9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAQABAAEAI/wADABhIsKDBgwgT"
    "Kly4MIDAgQ8TChAAYKLFiQMtZrzIkSLDjw4XYtzIsaJHARAGEGhg4OTIgxE/yiw4kuKDAQMeVCxAQGUCjxVnFhTo"
    "sKjRkABiEhSg4AGDiQZw4mzJU+UBoBBDIk16tKvXohIP9CRQQAACqQOojr26lOvXt3C1ZjSokeLFpRiBUiQat29X"
    "oYC5uo2bNalhhA+9IjYqOHHgw0L12u24ke7kx49fdsS6c+zPoJxlMuYrGLLIqFIRCKhKgK1dhkcHa317UECCsWXP"
    "pl69Vq/srUQb+wWrdwFus2hVs17gOzHh4VsZhob9G7r154av00Y8VClm7o8dD/+tvbm8eY3eG2aPHlwk3qDwsWqE"
    "OP67QpeSYda2H9nyS5qssWUSfzPhVxlFCiiQUYC+EfhRg0uhNhVvVkEImHOD0RdSfhEmR2FrzYFVWGkatgeWUnox"
    "MFYEAkiY1ocCBqXUbF+t91dYx7moXG9tRUfQiXD9hqNKZbmolk+hiciXdowhtJoEDQgkgAMEEOAARg1IUJZ+1V3n"
    "1oOVCeUckzU6uFiXZLZn5o9ptukmdD9+yWZ638l1mGOk0WhnVqPRWZ9p9cVEZ2xqduenfREdyqVI5zVKWWAm0icR"
    "eSS5ZJKBBimaGU015TVgfJet+WBenbY1X5iIAkoXqHfVFsEAT5H3JOp9km22FIOozroqp6eCxtpnver63qWXtgoj"
    "h5lKaiaHTFWpwES4zrUmnZzVpBtOO1Y4rJiqYtYiWkeC2Bakd8YmJ010GXksaJBhuOS7ZU5al47rzhWpcIlm+KWf"
    "NvXUkrrRskkivtpJW5FxRH67W8B7IfUXk6raliO49QpsmpLWoZuRWAnTy3B1aA43JFnISRVujIUF52Wf41bEMckA"
    "exbibHymWRuVKjFnQAM4sSQAwlZyNuabItIFwQLPBsUAA6ApsAAESYYMcYHTKUT0jTJpBlKJRLfsnnRS2ywswV0b"
    "/Kl8GsMn49WKNTkTe2GzLffcdJMZEAA7"
)
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
DEFAULT_PATH = "$APPDATA/VintagestoryData"
TAIL_BYTES = 128 * 1024


def initial_logs_folder_path(cli_path: str, config_source_path: str) -> str:
    """Path shown in Logs folder: always a directory string. Saved or CLI paths to a file become its parent."""
    raw = (cli_path or "").strip()
    if not raw:
        raw = (config_source_path or "").strip()
    if not raw:
        raw = DEFAULT_PATH
    try:
        p = expand_path(raw)
        if p.is_file():
            return str(p.parent)
    except Exception:
        pass
    return raw
POPUP_TIMEOUT_MS = 12_000
POPUP_COMPLETION_TIMEOUT_MS = 14_000
# Threshold vs completion popups: large glyph + title (color emoji when the OS font supports it).
ALERT_POPUP_EMOJI_THRESHOLD = "\u26a0\ufe0f"  # ⚠️
ALERT_POPUP_EMOJI_COMPLETION = "\U0001f389"  # 🎉


def _alert_popup_emoji_font(size: int = 42) -> tuple[str, int, str]:
    if sys.platform.startswith("win"):
        return ("Segoe UI Emoji", size, "normal")
    if sys.platform == "darwin":
        return ("Apple Color Emoji", size, "normal")
    return ("TkDefaultFont", size, "normal")


MAX_GRAPH_POINTS = 5000
MAX_DRAW_POINTS = 1200
# When only one sample exists, map X across this span so axes and the marker are visible (not a sliver).
SINGLE_POINT_GRAPH_SPAN_SEC = 60.0
DEFAULT_PREDICTION_WINDOW_POINTS = 10
DEFAULT_ALERT_THRESHOLDS = "10, 5"
SEED_LOG_TAIL_BYTES = 2 * 1024 * 1024
QUEUE_RESET_JUMP_THRESHOLD = 10
# After reaching the front (position ≤1), a single +10 jump often re-reads stale lines (e.g. 1→11);
# do not treat that alone as a new queue run (which would clear thresholds and re-alert all).
# Minimum time between popup/sound alerts to suppress duplicate fires from log noise.
ALERT_MIN_INTERVAL_SEC = 12.0
# Debounce for queue-front completion (sound and/or popup; independent of threshold alerts).
COMPLETION_NOTIFY_MIN_INTERVAL_SEC = 2.0
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

# One default clip per OS per kind (warning vs completion). Pre-filled in Settings; tried before registry/bell fallbacks.
# Windows: %SystemRoot%\\Media or %WINDIR%\\Media, else C:\\Windows\\Media. macOS: MACOS_SYSTEM_SOUNDS_DIR.
# Linux: XDG_DATA_DIRS + relative path, plus /usr/share and /usr/local/share (see _linux_sound_paths_from_relatives).
DEFAULT_ALERT_WIN_MEDIA_NAME = "Windows Background.wav"
DEFAULT_COMPLETION_WIN_MEDIA_NAME = "tada.wav"
DEFAULT_ALERT_MAC_NAME = "Basso.aiff"
DEFAULT_COMPLETION_MAC_NAME = "Hero.aiff"
DEFAULT_ALERT_LINUX_RELATIVE = "sounds/freedesktop/stereo/dialog-warning.oga"
DEFAULT_COMPLETION_LINUX_RELATIVE = "sounds/freedesktop/stereo/complete.oga"
# macOS: no standard env for system UI sounds; Apple documents this directory.
MACOS_SYSTEM_SOUNDS_DIR = Path("/System/Library/Sounds")
# Windows: use env when set; last resort explicit path (see _windows_media_dir).
_FALLBACK_WINDOWS_SYSTEM_ROOT = Path(r"C:\Windows")

# UI palette: Grafana-inspired dark (canvas/panel tones, series-style accents, readable contrast).
UI_BG_APP = "#111217"
UI_BG_CARD = "#181b1f"
UI_TEXT_PRIMARY = "#d8d9da"
UI_TEXT_MUTED = "#8e9ba3"
UI_LINK = "#58a6ff"
UI_SUMMARY_BG = "#0d0f14"
UI_SUMMARY_VALUE = "#f0f4f8"
UI_ACCENT_POSITION = "#5794f2"
UI_ACCENT_STATUS = "#73bf69"
UI_ACCENT_ELAPSED = "#b877d9"
UI_ACCENT_REMAINING = "#ff9830"
UI_ACCENT_RATE = "#96d9f8"
UI_ACCENT_WARNINGS = "#f0b429"
UI_ACCENT_PROGRESS = "#8be9fd"
KPI_VALUE_FONT = ("TkDefaultFont", 18, "bold")
UI_DANGER = "#f2495c"
UI_ENTRY_FIELD = "#0d0f12"
UI_SEPARATOR = "#2e3742"
# ttk Entry stroke (clam); focus uses UI_GRAPH_AXIS — single-color edges avoid bright corner pixels.
UI_ENTRY_BORDER = UI_SEPARATOR
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
# Hover: vertical time cursor (drawn on top of the series).
UI_GRAPH_HOVER_CURSOR = "#f0f4f8"
# X-axis small marks between major time labels (minute-scale; step widens when too dense).
UI_GRAPH_MINOR_TICK = "#3a4250"
UI_GRAPH_EMPTY = "#6e7680"
UI_TOOLTIP_BG = "#1f2329"
UI_TOOLTIP_FG = "#d8d9da"
# Primary transport: large play (green) / stop (red) control, top-left.
UI_PLAY_BTN_BG = "#1f883d"
UI_PLAY_BTN_ACTIVE = "#2ea043"
UI_STOP_BTN_BG = "#cf222e"
UI_STOP_BTN_ACTIVE = "#f85149"
# Main panes (graph, status, history) and key inner blocks.
UI_SECTION_PAD = 12
# Text / controls inset inside a pane’s client area (after LabelFrame padding). One rhythm for the whole UI.
UI_INNER_PAD_X = 10
# tk.Entry inside a bordered Frame; inset text from the frame edge.
UI_ENTRY_INNER_PAD = 3
UI_INNER_PAD_Y_SM = 8
UI_INNER_PAD_Y_MD = 10
# tk.PanedWindow vertical dividers (must match _fit_history_pane_collapsed math). Flat strip — no showhandle (avoids harsh 3D boxes on Windows).
UI_PANE_SASH_WIDTH = 6
UI_PANE_SASH_PAD = 3
# PanedWindow sash: auto-open collapsed panes when stretched past header + margin; auto-collapse
# expanded panes when squeezed to at/below these heights (expanded minsize must stay ≤ threshold).
PANE_DRAG_OPEN_EXTRA_PX = 28
UI_STATUS_DRAG_AUTO_COLLAPSE_MAX_H = 118
UI_HISTORY_DRAG_AUTO_COLLAPSE_MAX_H = 158
# Main paned LabelFrames (Queue graph, Status): labelmargins (L,T,R,B); padding is the client area (clam).
UI_PANE_LABELFRAME_LABEL_MARGINS = (10, 8, 10, 6)
UI_PANE_LABELFRAME_PAD = (10, 10, 10, 10)
# Queue graph: align with Status pane titles; slightly tighter top under the label.
UI_GRAPH_LABELFRAME_PAD = (10, 8, 10, 10)
# Black graph_stack: full width; symmetric vertical gap to summary and bottom edge.
UI_GRAPH_STACK_PAD = (0, UI_INNER_PAD_Y_SM, 0, UI_INNER_PAD_Y_SM)
# Plot canvas inside graph_stack (tight left — Y-axis margin is pad_left inside redraw_graph).
UI_GRAPH_DARK_INNER_PAD = (4, UI_INNER_PAD_Y_SM, 8, 10)
# Plot area inside graph canvas (must match redraw_graph — same numbers for axis labels + Y-scale button).
GRAPH_CANVAS_PAD_LEFT = 46
GRAPH_CANVAS_PAD_RIGHT = 22
GRAPH_CANVAS_PAD_TOP = 12
GRAPH_CANVAS_PAD_BOTTOM = 32
# Y-scale toggle: inset from top-right corner of plot rectangle (not canvas edge).
GRAPH_Y_SCALE_BTN_INSET_X = 8
GRAPH_Y_SCALE_BTN_INSET_Y = 8
# Gap only — details frame supplies the rest (avoid double top spacing in Status).
UI_STATUS_BODY_PAD_TOP = UI_INNER_PAD_Y_SM
# KPI strip: one horizontal gutter; balanced vertical padding.
UI_SUMMARY_INNER_PAD_X = UI_INNER_PAD_X
UI_SUMMARY_INNER_PAD_Y_TOP = UI_INNER_PAD_Y_MD
UI_SUMMARY_INNER_PAD_Y_BOTTOM = UI_INNER_PAD_Y_MD
# History: align with pane LabelFrame L/R; even vertical padding.
UI_HISTORY_FRAME_PAD_EXPANDED = (10, UI_INNER_PAD_Y_MD, 10, UI_INNER_PAD_Y_MD)
UI_HISTORY_FRAME_PAD_COLLAPSED = (10, 4, 10, 0)
UI_HISTORY_PANE_MIN_EXPANDED = 140
# Collapsible Status strip (same padding rhythm as History).
UI_STATUS_PANE_MIN_EXPANDED = 100
# PanedWindow minsize when a pane is collapsed: must cover tab row (chevron + title), not 1px.
UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK = 44
UI_HISTORY_TEXT_PAD = UI_INNER_PAD_Y_SM


def parse_alert_thresholds(raw: str) -> list[int]:
    """Comma-separated queue positions (default 10, 5); each fires at most once per
    downward crossing until a new queue run (log boundary lines and/or large upward jump; see poll + compute_alert).
    """
    out: list[int] = []
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    if not out:
        raise ValueError("Add at least one alert threshold (e.g. 10, 5).")
    for t in out:
        if t < 1:
            raise ValueError(f"Alert threshold {t} must be >= 1.")
    return sorted(set(out), reverse=True)


def expand_path(raw: str) -> Path:
    expanded = os.path.expandvars(raw.strip())
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def browse_initialdir_from_path(raw: str) -> str:
    """Folder to open native pickers in: uses the path already in the field (file → its parent, dir → itself)."""
    raw = (raw or "").strip()
    if not raw:
        return str(Path.home())
    try:
        p = expand_path(raw)
    except Exception:
        return str(Path.home())
    try:
        if p.is_file():
            return str(p.resolve().parent)
        if p.is_dir():
            return str(p.resolve())
        parent = p.parent
        if parent.is_dir():
            return str(parent.resolve())
    except Exception:
        pass
    return str(Path.home())


def _windows_media_dir() -> Path:
    """%SystemRoot%\\Media or %WINDIR%\\Media when set; else explicit C:\\Windows\\Media."""
    for key in ("SystemRoot", "WINDIR"):
        v = os.environ.get(key)
        if v:
            return Path(v) / "Media"
    return _FALLBACK_WINDOWS_SYSTEM_ROOT / "Media"


def _linux_xdg_data_dirs() -> list[Path]:
    """XDG Base Directory: default for XDG_DATA_DIRS is /usr/local/share:/usr/share when unset."""
    raw = os.environ.get("XDG_DATA_DIRS")
    if raw:
        return [Path(p.strip()) for p in raw.split(":") if p.strip()]
    return [Path("/usr/local/share"), Path("/usr/share")]


def _linux_sound_paths_from_relatives(relatives: tuple[str, ...]) -> list[Path]:
    """Try each path under XDG_DATA_DIRS, then explicit /usr/share and /usr/local/share (deduped)."""
    roots: list[Path] = []
    seen_r: set[str] = set()
    for b in list(_linux_xdg_data_dirs()) + [Path("/usr/share"), Path("/usr/local/share")]:
        try:
            key = str(b.resolve())
        except Exception:
            key = str(b)
        if key not in seen_r:
            seen_r.add(key)
            roots.append(b)
    out: list[Path] = []
    seen_p: set[str] = set()
    for rel in relatives:
        for root in roots:
            p = root / rel
            try:
                pk = str(p.resolve())
            except Exception:
                pk = str(p)
            if pk not in seen_p:
                seen_p.add(pk)
                out.append(p)
    return out


def iter_default_alert_sound_paths() -> list[Path]:
    """Default warning sound: one path per OS (may expand to several candidates on Linux for XDG roots)."""
    if sys.platform.startswith("win"):
        return [_windows_media_dir() / DEFAULT_ALERT_WIN_MEDIA_NAME]
    if sys.platform == "darwin":
        return [MACOS_SYSTEM_SOUNDS_DIR / DEFAULT_ALERT_MAC_NAME]
    if sys.platform.startswith("linux"):
        return _linux_sound_paths_from_relatives((DEFAULT_ALERT_LINUX_RELATIVE,))
    return []


def iter_default_completion_sound_paths() -> list[Path]:
    """Default completion sound: one path per OS."""
    if sys.platform.startswith("win"):
        return [_windows_media_dir() / DEFAULT_COMPLETION_WIN_MEDIA_NAME]
    if sys.platform == "darwin":
        return [MACOS_SYSTEM_SOUNDS_DIR / DEFAULT_COMPLETION_MAC_NAME]
    if sys.platform.startswith("linux"):
        return _linux_sound_paths_from_relatives((DEFAULT_COMPLETION_LINUX_RELATIVE,))
    return []


def try_play_first_existing_sound(paths: list[Path]) -> bool:
    for p in paths:
        if p.is_file() and play_alert_sound_file(p):
            return True
    return False


def default_alert_sound_path_for_display() -> str:
    """First existing default alert file path for Settings, or empty string."""
    for p in iter_default_alert_sound_paths():
        if p.is_file():
            return str(p)
    return ""


def default_completion_sound_path_for_display() -> str:
    """First existing default completion sound path for Settings, or empty string."""
    for p in iter_default_completion_sound_paths():
        if p.is_file():
            return str(p)
    return ""


def play_alert_sound_file(path: Path) -> bool:
    """Try to play an audio file; return True if playback was started (async where supported)."""
    sp = str(path)
    if winsound is not None and sys.platform.startswith("win"):
        try:
            winsound.PlaySound(sp, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            try:
                winsound.PlaySound(sp, winsound.SND_FILENAME)
                return True
            except Exception:
                pass
    if sys.platform == "darwin":
        try:
            subprocess.Popen(
                ["afplay", sp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except Exception:
            pass
    if sys.platform.startswith("linux"):
        for cmd in (["paplay", sp], ["aplay", sp]):
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except Exception:
                continue
    return False


def play_default_system_alert_sound() -> bool:
    """Play OS default alert: same files as Settings pre-fill, then Windows registry/MessageBeep fallback."""
    if try_play_first_existing_sound(iter_default_alert_sound_paths()):
        return True

    if winsound is not None and sys.platform.startswith("win"):
        for alias in ("SystemNotification", "SystemAsterisk", "SystemExclamation", "SystemDefault"):
            try:
                winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
                return True
            except Exception:
                continue
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return True
        except Exception:
            try:
                winsound.MessageBeep()
                return True
            except Exception:
                pass
    return False


def play_default_completion_system_sound() -> bool:
    """Play OS default queue-completion tone; softer Windows fallbacks than threshold alert."""
    if try_play_first_existing_sound(iter_default_completion_sound_paths()):
        return True

    if winsound is not None and sys.platform.startswith("win"):
        for alias in ("SystemNotification", "SystemDefault", "SystemAsterisk"):
            try:
                winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
                return True
            except Exception:
                continue
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return True
        except Exception:
            try:
                winsound.MessageBeep()
                return True
            except Exception:
                pass
    return False


def get_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "vs-queue-monitor" / "config.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vs-queue-monitor" / "config.json"


def _legacy_config_path() -> Path:
    """Previous config location before the project was renamed to vs-queue-monitor."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "vs-q-monitor" / "config.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "vs-q-monitor" / "config.json"


def load_config() -> dict:
    path = get_config_path()
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    legacy = _legacy_config_path()
    try:
        if legacy.is_file():
            with legacy.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                save_config(data)
                return data
    except Exception:
        pass
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
    """Resolve the client log file from a **folder** path (or legacy saved file path → parent folder).

    The app always searches for the correct filename (e.g. client-main.log) under that tree — users
    should not pick a specific .log file in the UI.
    """
    path = expand_path(raw)

    if path.is_file():
        path = path.parent

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
        # Last resort: any *.log under the folder (newest wins). Names like server.log do not match *client*.log.
        try:
            file_matches = [p for p in path.rglob("*.log") if p.is_file()]
        except OSError:
            file_matches = []

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
    """Latest queue position in the buffer and its run session (0 = no boundary seen in tail).

    Uses the *last* queue phrase in **file order** (bottom of tail). ``walk_queue_position_events``
    sorts by parsed line timestamps, which can reorder events and yield the wrong ``ev[-1]``
    (e.g. 108) when the log order is the ground truth for “current” position.
    """
    last_pos: Optional[int] = None
    session = 0
    last_sess = 0
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
        last_pos = pos
        last_sess = session
    return last_pos, last_sess


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
) -> Optional[
        tuple[
            list[tuple[float, int]],
            int,
            int,
            float,
            int,
            int,
            int,
            Optional[int],
        ]
    ]:
    """Read and parse the log off the UI thread. Returns None if no queue segment was found.

    Second-to-last int: queue_run_session_id. Last: authoritative queue position from the same tail
    parse as ``parse_tail_last_queue_reading`` (must match UI — segment last point alone can drift).
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
    authoritative_pos, queue_run_session_id = (
        parse_tail_last_queue_reading(text) if text else (None, 0)
    )

    segment_points = segment_tuples[-MAX_GRAPH_POINTS:]
    return (
        segment_points,
        len(segment_positions),
        len(positions),
        tail_bytes / (1024 * 1024),
        min(segment_positions),
        max(segment_positions),
        queue_run_session_id,
        authoritative_pos,
    )


class QueueMonitorApp(tk.Tk):
    def __init__(self, initial_path: str = "", auto_start: bool = True) -> None:
        super().__init__()
        self.title(f"VS Queue Monitor v{VERSION}")
        self.geometry("960x700")
        self.minsize(880, 580)
        self._app_icon_image: Optional[tk.PhotoImage] = None
        self._apply_window_icon()

        self.config: dict = load_config()
        _cfg_src = self.config.get("source_path", "")
        _cfg_src = _cfg_src.strip() if isinstance(_cfg_src, str) else ""
        _initial_logs = initial_logs_folder_path(initial_path, _cfg_src)
        self.source_path_var = tk.StringVar(value=_initial_logs)
        if _initial_logs != _cfg_src:
            self.after_idle(self.persist_config)
        self.resolved_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")
        self.position_var = tk.StringVar(value="—")
        self.last_change_var = tk.StringVar(value="—")
        self.last_alert_var = tk.StringVar(value="—")
        self.elapsed_var = tk.StringVar(value="—")
        self.predicted_remaining_var = tk.StringVar(value="—")
        self.queue_rate_var = tk.StringVar(value="—")
        self.global_rate_var = tk.StringVar(value="—")
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
        self.show_status_var = tk.BooleanVar(value=bool(self.config.get("show_status", True)))
        self.graph_log_scale_var = tk.BooleanVar(value=bool(self.config.get("graph_log_scale", True)))
        self.popup_enabled_var = tk.BooleanVar(value=bool(self.config.get("popup_enabled", True)))
        self.sound_enabled_var = tk.BooleanVar(value=bool(self.config.get("sound_enabled", True)))
        _asp = self.config.get("alert_sound_path")
        if isinstance(_asp, str) and _asp.strip():
            _sound_initial = _asp.strip()
        else:
            _sound_initial = default_alert_sound_path_for_display()
        self.alert_sound_path_var = tk.StringVar(value=_sound_initial)
        self.completion_sound_enabled_var = tk.BooleanVar(
            value=bool(self.config.get("completion_sound_enabled", True)),
        )
        _csp = self.config.get("completion_sound_path")
        if isinstance(_csp, str) and _csp.strip():
            _comp_initial = _csp.strip()
        else:
            _comp_initial = default_completion_sound_path_for_display()
        self.completion_sound_path_var = tk.StringVar(value=_comp_initial)
        self.completion_popup_enabled_var = tk.BooleanVar(
            value=bool(self.config.get("completion_popup_enabled", True)),
        )
        self.show_every_change_var = tk.BooleanVar(value=bool(self.config.get("show_every_change", False)))

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
        self.active_popup: Optional[tk.Toplevel] = None
        self.active_completion_popup: Optional[tk.Toplevel] = None
        self.graph_points: deque[tuple[float, int]] = deque(maxlen=MAX_GRAPH_POINTS)
        self.graph_canvas: Optional[tk.Canvas] = None
        self.current_point: Optional[tuple[float, int]] = None
        self.graph_points_drawn: list[tuple[float, int]] = []
        self._graph_hover_point: Optional[tuple[float, int]] = None  # (epoch, pos) nearest sample for tooltip ring
        self.graph_tooltip: Optional[tk.Toplevel] = None
        self.status_frame: Optional[ttk.Frame] = None
        self._status_body_wrap: Optional[ttk.Frame] = None
        self._status_sep: Optional[ttk.Separator] = None
        self._status_tab_btn: Optional[ttk.Button] = None
        self._fit_status_collapsed_job: Optional[str] = None
        self.history_frame: Optional[ttk.Frame] = None
        self._history_body: Optional[tk.Frame] = None
        self._history_sep: Optional[ttk.Separator] = None
        self.panes: Optional[tk.PanedWindow] = None
        self.start_stop_button: Optional[ttk.Button] = None
        self._settings_win: Optional[tk.Toplevel] = None
        self._about_win: Optional[tk.Toplevel] = None
        self._graph_y_scale_btn: Optional[ttk.Button] = None
        self._history_tab_btn: Optional[ttk.Button] = None
        self._fit_history_collapsed_job: Optional[str] = None
        self._pane_drag_threshold_job: Optional[str] = None
        # When the queue stalls longer than the median rate suggests, reduce this
        # (prediction was optimistic; effective speed for ETA and display).
        self._pred_speed_scale: float = 1.0
        self._stale_slots_accounted: int = 0
        self._starting: bool = False
        self._start_seq: int = 0
        self._loading_spinner: Optional[ttk.Progressbar] = None
        self._settings_btn: Optional[ttk.Button] = None
        self._queue_progress: Optional[ttk.Progressbar] = None
        self._status_value_label: Optional[tk.Label] = None
        self._position_emoji_label: Optional[tk.Label] = None
        # Wall time when we first observed position ≤1 this run; used to freeze "queue total" elapsed.
        self._position_one_reached_at: Optional[float] = None
        self._persist_config_job: Optional[str] = None
        self._configure_resize_job: Optional[str] = None
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
        self._bind_keyboard_shortcuts()
        self.bind("<Configure>", self._schedule_resize_refresh, add=True)
        self.avg_window_var.trace_add("write", self._on_avg_window_write)
        self.graph_log_scale_var.trace_add("write", lambda *_: self._update_graph_y_scale_button_text())
        self.show_log_var.trace_add("write", self._on_show_log_write)
        self.show_status_var.trace_add("write", self._on_show_status_write)
        self._bind_config_persist_traces()
        self.start_timer()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.write_history(
            "WARNING — Work in progress; AI-assisted code. Expect bugs and rough edges. "
            "Verify log paths, queue readings, and alerts yourself; do not rely on this tool as a sole source of truth."
        )
        self.write_history(
            "VS Queue Monitor started. Waiting for a path. Parser looks for queue lines like "
            "'Client is in connect queue at position: N'."
        )

        # Graph history is seeded from the log when monitoring starts.

        try:
            geometry = self.config.get("window_geometry", "")
            if isinstance(geometry, str) and geometry:
                self.geometry(geometry)
        except Exception:
            pass

        if auto_start:
            self.after(250, self.start_monitoring)

    def _apply_window_icon(self) -> None:
        """Load window icon from embedded GIF (no external files)."""
        try:
            self._app_icon_image = tk.PhotoImage(data=_APP_ICON_GIF_B64)
        except tk.TclError:
            self._app_icon_image = None
            return
        self.iconphoto(True, self._app_icon_image)

    def _about_parent_toplevel(self) -> tk.Misc:
        """Prefer Settings as parent when open so About stacks above it."""
        try:
            w = self._settings_win
            if w is not None and w.winfo_exists():
                return w
        except Exception:
            pass
        return self

    def show_about(self) -> None:
        """Modal About: name, short description, version, project link, disclaimer."""
        if self._about_win is not None:
            try:
                if self._about_win.winfo_exists():
                    self._about_win.lift()
                    self._about_win.focus_force()
                    return
            except Exception:
                pass
            self._about_win = None

        parent = self._about_parent_toplevel()
        about = tk.Toplevel(parent)
        self._about_win = about
        about.title(f"About {APP_DISPLAY_NAME}")
        about.configure(bg=UI_BG_CARD)
        try:
            about.transient(parent)
        except Exception:
            pass
        about.resizable(False, False)
        if self._app_icon_image is not None:
            try:
                about.iconphoto(True, self._app_icon_image)
            except tk.TclError:
                pass

        outer = tk.Frame(about, bg=UI_BG_CARD, padx=22, pady=20)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=UI_BG_CARD)
        header.pack(fill="x", anchor="w")

        if self._app_icon_image is not None:
            icon_lbl = tk.Label(header, image=self._app_icon_image, bg=UI_BG_CARD)
            icon_lbl.pack(side="left", padx=(0, 14))

        text_col = tk.Frame(header, bg=UI_BG_CARD)
        text_col.pack(side="left", fill="y")

        tk.Label(
            text_col,
            text=APP_DISPLAY_NAME,
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
            font=("Segoe UI", 14, "bold") if sys.platform.startswith("win") else ("TkDefaultFont", 14, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text_col,
            text=APP_TAGLINE,
            bg=UI_BG_CARD,
            fg=UI_TEXT_MUTED,
            font=("Segoe UI", 10) if sys.platform.startswith("win") else ("TkDefaultFont", 10),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            outer,
            text=f"Version {VERSION}",
            bg=UI_BG_CARD,
            fg=UI_TEXT_MUTED,
            font=("Segoe UI", 10) if sys.platform.startswith("win") else ("TkDefaultFont", 10),
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

        link_wrap = tk.Frame(outer, bg=UI_BG_CARD)
        link_wrap.pack(anchor="w", pady=(12, 0))
        tk.Label(link_wrap, text="Website: ", bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY, anchor="w").pack(side="left")
        link_lbl = tk.Label(
            link_wrap,
            text="GitHub project page",
            bg=UI_BG_CARD,
            fg=UI_LINK,
            cursor="hand2",
            font=("Segoe UI", 10, "underline") if sys.platform.startswith("win") else ("TkDefaultFont", 10, "underline"),
        )
        link_lbl.pack(side="left")

        def open_repo(_evt: object = None) -> None:
            try:
                webbrowser.open(GITHUB_REPO_URL)
            except Exception:
                pass

        link_lbl.bind("<Button-1>", open_repo)
        tk.Label(
            outer,
            text="Not affiliated with Vintage Story or its developers.",
            bg=UI_BG_CARD,
            fg=UI_TEXT_MUTED,
            wraplength=400,
            justify="left",
            anchor="w",
            font=("Segoe UI", 9) if sys.platform.startswith("win") else ("TkDefaultFont", 9),
        ).pack(anchor="w", pady=(12, 0))

        btn_row = ttk.Frame(outer, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(18, 0))

        def close_about() -> None:
            self._about_win = None
            try:
                about.grab_release()
            except Exception:
                pass
            try:
                about.destroy()
            except Exception:
                pass
            try:
                sw = self._settings_win
                if sw is not None and sw.winfo_exists() and parent is sw:
                    sw.grab_set()
            except Exception:
                pass

        ttk.Button(btn_row, text="OK", width=10, command=close_about).pack(side="right")

        about.protocol("WM_DELETE_WINDOW", close_about)
        about.bind("<Escape>", lambda _e: close_about())
        about.bind("<Return>", lambda _e: close_about())

        try:
            about.grab_set()
        except Exception:
            pass

        about.update_idletasks()
        try:
            parent.update_idletasks()
            w = int(about.winfo_reqwidth())
            h = int(about.winfo_reqheight())
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            about.geometry(f"+{x}+{y}")
        except Exception:
            pass

        try:
            about.focus_force()
        except Exception:
            pass

    def _configure_ttk_theme(self, style: ttk.Style) -> None:
        """Apply app-wide background and text colors (clam, Grafana-style dark)."""
        # Clam draws many widgets with lightcolor/darkcolor; if left default, borders read as white on Windows.
        _bd = UI_SEPARATOR
        _card = UI_BG_CARD
        self.configure(bg=UI_BG_APP)
        style.configure("App.TFrame", background=UI_BG_APP)
        style.configure("TFrame", background=_card, borderwidth=0)
        style.configure("Card.TFrame", background=_card)
        # Match Queue graph / Status pane surface so the History header is not a floating strip on app bg.
        style.configure("HistoryTabStrip.TFrame", background=UI_BG_CARD)
        style.configure(
            "HistoryTab.TButton",
            padding=(4, 4),
            background=_card,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=_card,
            lightcolor=UI_BUTTON_BG_ACTIVE,
            focuscolor=_card,
            borderwidth=1,
            relief="flat",
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "HistoryTab.TButton",
            background=[("active", UI_BUTTON_BG_ACTIVE), ("pressed", UI_BUTTON_BG_ACTIVE)],
            darkcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
            lightcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
        )
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
        # Graph + Status panes: default TLabelframe draws the title flush to the border; labelmargins fixes that (clam).
        style.configure(
            "Pane.TLabelframe",
            background=_card,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=_bd,
            lightcolor=_bd,
            relief="flat",
            borderwidth=1,
            labelmargins=UI_PANE_LABELFRAME_LABEL_MARGINS,
        )
        style.configure("Pane.TLabelframe.Label", background=_card, foreground=UI_TEXT_MUTED)
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
        # Overlay on graph canvas: sized to longest label ("Y → linear"); extra vertical padding avoids clipped text.
        style.configure(
            "GraphYScale.TButton",
            padding=(10, 6),
            background=UI_BUTTON_BG,
            foreground=UI_TEXT_PRIMARY,
            bordercolor=_bd,
            darkcolor=UI_BUTTON_BG,
            lightcolor=UI_BUTTON_BG_ACTIVE,
            focuscolor=UI_BUTTON_BG,
        )
        style.map(
            "GraphYScale.TButton",
            background=[("active", UI_BUTTON_BG_ACTIVE), ("pressed", UI_BUTTON_BG_ACTIVE)],
            darkcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
            lightcolor=[("pressed", UI_BUTTON_BG_ACTIVE)],
        )
        # Same padding as TButton (e.g. Settings); green / red transport control.
        style.configure(
            "PlayStopPlay.TButton",
            padding=(10, 4),
            background=UI_PLAY_BTN_BG,
            foreground="#ffffff",
            bordercolor=_bd,
            darkcolor=UI_PLAY_BTN_BG,
            lightcolor=UI_PLAY_BTN_ACTIVE,
            focuscolor=UI_PLAY_BTN_BG,
        )
        style.map(
            "PlayStopPlay.TButton",
            background=[
                ("disabled", UI_PLAY_BTN_BG),
                ("active", UI_PLAY_BTN_ACTIVE),
                ("pressed", UI_PLAY_BTN_ACTIVE),
            ],
            foreground=[("disabled", "#ffffff")],
            darkcolor=[("pressed", UI_PLAY_BTN_ACTIVE)],
            lightcolor=[("pressed", UI_PLAY_BTN_ACTIVE)],
        )
        style.configure(
            "PlayStopStop.TButton",
            padding=(10, 4),
            background=UI_STOP_BTN_BG,
            foreground="#ffffff",
            bordercolor=_bd,
            darkcolor=UI_STOP_BTN_BG,
            lightcolor=UI_STOP_BTN_ACTIVE,
            focuscolor=UI_STOP_BTN_BG,
        )
        style.map(
            "PlayStopStop.TButton",
            background=[
                ("disabled", UI_STOP_BTN_BG),
                ("active", UI_STOP_BTN_ACTIVE),
                ("pressed", UI_STOP_BTN_ACTIVE),
            ],
            foreground=[("disabled", "#ffffff")],
            darkcolor=[("pressed", UI_STOP_BTN_ACTIVE)],
            lightcolor=[("pressed", UI_STOP_BTN_ACTIVE)],
        )
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
        # Horizontal progressbars resolve style "Thin.TProgressbar" to layout "Horizontal.Thin.TProgressbar";
        # that layout must exist (copy from Horizontal.TProgressbar); -parent alone does not create it on Windows.
        _thin_pb_style = "Horizontal.Thin.TProgressbar"
        style.layout(_thin_pb_style, style.layout("Horizontal.TProgressbar"))
        style.configure(
            _thin_pb_style,
            troughcolor=UI_PROGRESS_TROUGH,
            background=UI_ACCENT_POSITION,
            thickness=3,
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

    @staticmethod
    def _make_dark_entry(parent: tk.Misc, **kwargs: Any) -> tk.Frame:
        """Flat tk.Entry inside a Frame-drawn border (ttk/clam TEntry draws bad corner pixels on Windows).

        Border color is our highlight ring (no theme “dots”). Rounded corners are not supported by stock Tk.
        """
        pad = UI_ENTRY_INNER_PAD
        wrap = tk.Frame(
            parent,
            bg=UI_ENTRY_FIELD,
            bd=0,
            highlightthickness=1,
            highlightbackground=UI_ENTRY_BORDER,
            highlightcolor=UI_ENTRY_BORDER,
        )
        entry = tk.Entry(
            wrap,
            bg=UI_ENTRY_FIELD,
            fg=UI_TEXT_PRIMARY,
            insertbackground=UI_TEXT_PRIMARY,
            selectbackground=UI_BUTTON_BG_ACTIVE,
            selectforeground=UI_TEXT_PRIMARY,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=("TkDefaultFont", 10),
            **kwargs,
        )
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        entry.grid(row=0, column=0, sticky="nsew", padx=pad, pady=pad)

        def _border_focus(_in: bool) -> None:
            c = UI_GRAPH_AXIS if _in else UI_ENTRY_BORDER
            try:
                wrap.configure(highlightbackground=c, highlightcolor=c)
            except tk.TclError:
                pass

        entry.bind("<FocusIn>", lambda _e: _border_focus(True), add=True)
        entry.bind("<FocusOut>", lambda _e: _border_focus(False), add=True)

        return wrap

    def _build_ui(self) -> None:
        try:
            style = ttk.Style()
            if "clam" in style.theme_names():
                style.theme_use("clam")
            self._configure_ttk_theme(style)
        except Exception:
            pass

        outer = ttk.Frame(self, padding=(12, 12), style="App.TFrame")
        outer.pack(fill="both", expand=True)

        # Top: play/stop + one line: label, path entry, file/folder browse, settings (no separator — avoids bright rule on Windows).
        top = ttk.Frame(
            outer,
            style="Card.TFrame",
            padding=(0, 0, 0, UI_INNER_PAD_Y_SM),
        )
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        play_wrap = ttk.Frame(top, style="Card.TFrame")
        play_wrap.grid(row=0, column=0, sticky="nw", padx=(0, UI_INNER_PAD_Y_MD), pady=(0, 0))
        self.start_stop_button = ttk.Button(
            play_wrap,
            text="\u25b6",
            style="PlayStopPlay.TButton",
            command=self.toggle_monitoring,
            cursor="hand2",
        )
        self.start_stop_button.pack()
        self.update_start_stop_button()

        path_row = ttk.Frame(top, style="Card.TFrame")
        path_row.grid(row=0, column=1, sticky="ew", pady=(0, 0))
        path_row.columnconfigure(0, weight=1)
        path_left = ttk.Frame(path_row, style="Card.TFrame")
        path_left.grid(row=0, column=0, sticky="ew")
        path_left.columnconfigure(1, weight=1)
        self._lbl_log_path = ttk.Label(path_left, text="Logs folder")
        self._lbl_log_path.grid(row=0, column=0, sticky="w", padx=(0, UI_INNER_PAD_Y_SM))
        self._path_entry = self._make_dark_entry(path_left, textvariable=self.source_path_var)
        self._path_entry.grid(row=0, column=1, sticky="ew", padx=(0, UI_INNER_PAD_Y_SM))

        path_actions = ttk.Frame(path_row, style="Card.TFrame")
        path_actions.grid(row=0, column=1, sticky="e")
        self._btn_browse_logs = ttk.Button(
            path_actions,
            text="\U0001f4c1  Browse…",
            command=self.browse_logs_folder,
        )
        self._btn_browse_logs.pack(side="left", padx=(0, 4))
        self._loading_spinner = ttk.Progressbar(path_actions, mode="indeterminate", length=120)
        self._settings_btn = ttk.Button(
            path_actions,
            text="\u2699  Settings",
            command=self.open_settings,
        )
        self._settings_btn.pack(side="left", padx=(4, 0))

        # Classic tk.PanedWindow: flat sash + resize cursor. showhandle/GROOVE draws light-bordered Motif boxes on Windows.
        panes = tk.PanedWindow(
            outer,
            orient=tk.VERTICAL,
            sashwidth=UI_PANE_SASH_WIDTH,
            sashrelief=tk.FLAT,
            sashpad=UI_PANE_SASH_PAD,
            sashcursor="sb_v_double_arrow",
            bd=0,
            proxyrelief=tk.FLAT,
            proxyborderwidth=0,
            proxybackground=UI_BG_APP,
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
        panes.pack(fill="both", expand=True, pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
        panes.bind("<Configure>", self._schedule_pane_fits, add=True)
        panes.bind("<B1-Motion>", self._schedule_pane_drag_thresholds, add=True)

        self._graph_labelframe = ttk.LabelFrame(
            panes,
            text="Queue graph",
            style="Pane.TLabelframe",
            padding=UI_GRAPH_LABELFRAME_PAD,
        )
        graph_frame = self._graph_labelframe
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=0)
        graph_frame.rowconfigure(1, weight=1)

        # POSITION / STATUS / RATE / WARNINGS | spacer | ELAPSED / EST. REMAINING / PROGRESS — row 0 = keys, row 1 = values.
        summary = tk.Frame(graph_frame, bg=UI_SUMMARY_BG)
        summary.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        for _c in range(8):
            summary.columnconfigure(_c, weight=0)
        summary.columnconfigure(4, weight=1)

        _spx = UI_SUMMARY_INNER_PAD_X
        _spy = UI_SUMMARY_INNER_PAD_Y_TOP
        _hdr_py = (_spy, 4)
        _val_py = (0, UI_SUMMARY_INNER_PAD_Y_BOTTOM)
        _kpi_font_val = KPI_VALUE_FONT
        if sys.platform.startswith("win"):
            _kpi_emoji_font: tuple[str, int, str] = ("Segoe UI Emoji", 14, "normal")
        elif sys.platform == "darwin":
            _kpi_emoji_font = ("Apple Color Emoji", 14, "normal")
        else:
            _kpi_emoji_font = ("TkDefaultFont", 14, "normal")

        self._lbl_kpi_position = tk.Label(
            summary,
            text="POSITION",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_POSITION,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_kpi_position.grid(row=0, column=0, sticky="w", padx=(_spx, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._lbl_kpi_status = tk.Label(
            summary,
            text="STATUS",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_STATUS,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_kpi_status.grid(row=0, column=1, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._lbl_kpi_rate = tk.Label(
            summary,
            text="RATE",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_RATE,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_kpi_rate.grid(row=0, column=2, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._lbl_kpi_warnings = tk.Label(
            summary,
            text="WARNINGS",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_WARNINGS,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_kpi_warnings.grid(row=0, column=3, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        _summary_mid_spacer = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _summary_mid_spacer.grid(row=0, column=4, rowspan=2, sticky="nsew")
        self._lbl_elapsed_header = tk.Label(
            summary,
            text="ELAPSED",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_ELAPSED,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_elapsed_header.grid(row=0, column=5, sticky="w", padx=(UI_INNER_PAD_Y_MD, 4), pady=_hdr_py)
        self._lbl_remaining_header = tk.Label(
            summary,
            text="EST. REMAINING",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_REMAINING,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_remaining_header.grid(row=0, column=6, sticky="w", padx=(UI_INNER_PAD_Y_MD, 0), pady=_hdr_py)
        self._lbl_progress_header = tk.Label(
            summary,
            text="PROGRESS",
            bg=UI_SUMMARY_BG,
            fg=UI_ACCENT_PROGRESS,
            font=("TkDefaultFont", 9, "bold"),
            anchor="w",
        )
        self._lbl_progress_header.grid(row=0, column=7, sticky="w", padx=(UI_INNER_PAD_Y_MD, _spx), pady=_hdr_py)

        _pos_cell = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _pos_cell.grid(row=1, column=0, sticky="w", padx=(_spx, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._position_value_label = tk.Label(
            _pos_cell,
            textvariable=self.position_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_font_val,
            anchor="w",
        )
        self._position_value_label.pack(side="left")
        self._position_emoji_label = tk.Label(
            _pos_cell,
            text="",
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_emoji_font,
            anchor="w",
        )
        self._position_emoji_label.pack(side="left", padx=(3, 0))
        self._status_value_label = tk.Label(
            summary,
            textvariable=self.status_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_font_val,
            anchor="w",
        )
        self._status_value_label.grid(row=1, column=1, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._queue_rate_value_label = tk.Label(
            summary,
            textvariable=self.queue_rate_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_font_val,
            anchor="w",
        )
        self._queue_rate_value_label.grid(row=1, column=2, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)

        self._warnings_kpi_frame = tk.Frame(summary, bg=UI_SUMMARY_BG)
        self._warnings_kpi_frame.grid(row=1, column=3, sticky="w", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)

        self._elapsed_value_label = tk.Label(
            summary,
            textvariable=self.elapsed_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_font_val,
            anchor="e",
        )
        self._elapsed_value_label.grid(row=1, column=5, sticky="ew", padx=(UI_INNER_PAD_Y_MD, 4), pady=_val_py)
        self._remaining_value_label = tk.Label(
            summary,
            textvariable=self.predicted_remaining_var,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            font=_kpi_font_val,
            anchor="e",
        )
        self._remaining_value_label.grid(row=1, column=6, sticky="ew", padx=(UI_INNER_PAD_Y_MD, 0), pady=_val_py)
        _prog_cell = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _prog_cell.grid(row=1, column=7, sticky="e", padx=(UI_INNER_PAD_Y_MD, _spx), pady=_val_py)
        self._queue_progress = ttk.Progressbar(
            _prog_cell,
            style="Thin.TProgressbar",
            mode="determinate",
            maximum=100.0,
            length=96,
        )
        self._queue_progress.pack(anchor="e", pady=(0, 0))
        self._bind_static_tooltip(self._lbl_progress_header, self._progress_tooltip_text)
        self._bind_static_tooltip(self._queue_progress, self._progress_tooltip_text)

        _gsp_l, _gsp_t, _gsp_r, _gsp_b = UI_GRAPH_STACK_PAD
        self._graph_stack_frame = tk.Frame(graph_frame, bg=UI_GRAPH_BG, bd=0, highlightthickness=0)
        graph_stack = self._graph_stack_frame
        graph_stack.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(_gsp_l, _gsp_r),
            pady=(_gsp_t, _gsp_b),
        )
        graph_stack.rowconfigure(0, weight=1)
        graph_stack.columnconfigure(0, weight=1)
        self.graph_canvas = tk.Canvas(
            graph_stack, height=200, highlightthickness=0, background=UI_GRAPH_BG, bd=0, highlightbackground=UI_GRAPH_BG
        )
        _gdp_l, _gdp_t, _gdp_r, _gdp_b = UI_GRAPH_DARK_INNER_PAD
        self.graph_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(_gdp_l, _gdp_r),
            pady=(_gdp_t, _gdp_b),
        )
        # Child of the canvas so the control sits inset on the plot, not in the outer stack margin.
        self._graph_y_scale_btn = ttk.Button(
            self.graph_canvas,
            text="Y \u2192 log",
            style="GraphYScale.TButton",
            command=self._toggle_graph_y_scale,
        )
        self._graph_y_scale_btn.lift()
        self._update_graph_y_scale_button_text()
        self._bind_static_tooltip(
            self._graph_y_scale_btn,
            "Linear: even spacing by position. Log: zoom the lower numbers on the chart.",
        )
        self.graph_canvas.bind("<Configure>", self._on_graph_canvas_configure)
        self.graph_canvas.bind("<Motion>", self.on_graph_motion)
        self.graph_canvas.bind("<Leave>", lambda _evt: self.hide_graph_tooltip())

        self.status_frame = ttk.Frame(
            panes,
            style="HistoryTabStrip.TFrame",
            padding=UI_HISTORY_FRAME_PAD_EXPANDED,
        )
        self.status_frame.columnconfigure(0, weight=1)
        self.status_frame.rowconfigure(2, weight=1)

        self._status_tab_strip = ttk.Frame(self.status_frame, style="HistoryTabStrip.TFrame")
        self._status_tab_strip.grid(row=0, column=0, sticky="ew")
        self._status_tab_btn = ttk.Button(
            self._status_tab_strip,
            text="\u25bc",
            width=3,
            style="HistoryTab.TButton",
            command=self._toggle_status_panel,
        )
        self._status_tab_btn.pack(side="left", padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._lbl_status_section_title = ttk.Label(
            self._status_tab_strip, text="Info", style="Pane.TLabelframe.Label"
        )
        self._lbl_status_section_title.pack(side="left", padx=(0, 0), pady=(0, 0))

        self._status_sep = ttk.Separator(self.status_frame, orient=tk.HORIZONTAL)
        self._status_sep.grid(row=1, column=0, sticky="ew", pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))

        self._status_body_wrap = ttk.Frame(self.status_frame, style="Card.TFrame")
        self._status_body_wrap.grid(row=2, column=0, sticky="nsew")
        self._status_body_wrap.columnconfigure(0, weight=1)

        status_body = ttk.Frame(
            self._status_body_wrap,
            style="Card.TFrame",
            padding=(0, UI_STATUS_BODY_PAD_TOP, 0, 0),
        )
        status_body.grid(row=0, column=0, sticky="nsew")
        status_body.columnconfigure(0, weight=1)

        self.history_frame = ttk.Frame(
            panes,
            style="HistoryTabStrip.TFrame",
            padding=UI_HISTORY_FRAME_PAD_EXPANDED,
        )
        self.history_frame.columnconfigure(0, weight=1)
        self.history_frame.rowconfigure(2, weight=1)

        self._history_tab_strip = ttk.Frame(self.history_frame, style="HistoryTabStrip.TFrame")
        self._history_tab_strip.grid(row=0, column=0, sticky="ew")
        self._history_tab_btn = ttk.Button(
            self._history_tab_strip,
            text="\u25bc",
            width=3,
            style="HistoryTab.TButton",
            command=self._toggle_history_panel,
        )
        self._history_tab_btn.pack(side="left", padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._lbl_history_section_title = ttk.Label(
            self._history_tab_strip, text="History", style="Pane.TLabelframe.Label"
        )
        self._lbl_history_section_title.pack(side="left", padx=(0, 0), pady=(0, 0))

        self._wire_collapsible_header(self._status_tab_strip, self._lbl_status_section_title, self._toggle_status_panel)
        self._wire_collapsible_hand_cursor(self._status_tab_btn)
        self._wire_collapsible_header(self._history_tab_strip, self._lbl_history_section_title, self._toggle_history_panel)
        self._wire_collapsible_hand_cursor(self._history_tab_btn)

        self._history_sep = ttk.Separator(self.history_frame, orient=tk.HORIZONTAL)
        self._history_sep.grid(row=1, column=0, sticky="ew", pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))

        self._history_body = tk.Frame(self.history_frame, bg=UI_SUMMARY_BG, bd=0, highlightthickness=0)
        self._history_body.rowconfigure(0, weight=1)
        self._history_body.columnconfigure(0, weight=1)

        # stretch: extra vertical space goes mostly to graph + history; status stays content-sized.
        panes.add(graph_frame, minsize=120, stretch="always")
        panes.add(self.status_frame, minsize=UI_STATUS_PANE_MIN_EXPANDED, stretch="never")
        panes.add(self.history_frame, minsize=UI_HISTORY_PANE_MIN_EXPANDED, stretch="always")

        details = ttk.Frame(
            status_body,
            padding=(
                UI_SUMMARY_INNER_PAD_X,
                UI_INNER_PAD_Y_MD,
                UI_SUMMARY_INNER_PAD_X,
                UI_INNER_PAD_Y_MD,
            ),
            style="Card.TFrame",
        )
        details.grid(row=0, column=0, sticky="ew", pady=(0, 0))
        # Only the first value column grows so “Last threshold alert” stays near its value.
        details.columnconfigure(1, weight=1)
        details.columnconfigure(3, weight=0)

        wrap = 420
        _dpy = (UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM)
        _g = 6
        self._lbl_det_last_change = ttk.Label(details, text="Last change")
        self._lbl_det_last_change.grid(row=0, column=0, sticky="nw", padx=(0, _g), pady=_dpy)
        self._lbl_det_last_change_val = ttk.Label(details, textvariable=self.last_change_var, wraplength=wrap)
        self._lbl_det_last_change_val.grid(row=0, column=1, sticky="nw", padx=(0, UI_INNER_PAD_Y_MD), pady=_dpy)
        self._lbl_det_alert = ttk.Label(details, text="Last threshold alert")
        self._lbl_det_alert.grid(row=0, column=2, sticky="nw", padx=(UI_INNER_PAD_Y_MD, _g), pady=_dpy)
        self._lbl_det_alert_val = ttk.Label(details, textvariable=self.last_alert_var, wraplength=wrap)
        self._lbl_det_alert_val.grid(row=0, column=3, sticky="nw", padx=(0, 0), pady=_dpy)
        self._lbl_det_path = ttk.Label(details, text="Resolved log path")
        self._lbl_det_path.grid(row=1, column=0, sticky="nw", padx=(0, _g), pady=_dpy)
        self._lbl_det_path_val = ttk.Label(details, textvariable=self.resolved_path_var, wraplength=wrap * 2)
        self._lbl_det_path_val.grid(row=1, column=1, columnspan=3, sticky="nw", padx=(0, UI_INNER_PAD_Y_SM), pady=_dpy)
        self._lbl_det_global_rate = ttk.Label(details, text="Global Rate")
        self._lbl_det_global_rate.grid(row=2, column=0, sticky="nw", padx=(0, _g), pady=_dpy)
        self._lbl_det_global_rate_val = ttk.Label(details, textvariable=self.global_rate_var, wraplength=wrap * 2)
        self._lbl_det_global_rate_val.grid(row=2, column=1, columnspan=3, sticky="nw", padx=(0, UI_INNER_PAD_Y_SM), pady=_dpy)

        self.history_text = tk.Text(
            self._history_body,
            height=18,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 9) if sys.platform.startswith("win") else ("TkDefaultFont", 10),
            padx=UI_HISTORY_TEXT_PAD,
            pady=UI_HISTORY_TEXT_PAD,
            bg=UI_SUMMARY_BG,
            fg=UI_SUMMARY_VALUE,
            insertbackground=UI_SUMMARY_VALUE,
            highlightthickness=0,
            borderwidth=0,
        )
        self.history_text.grid(row=0, column=0, sticky="nsew", padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._history_scrollbar = ttk.Scrollbar(self._history_body, orient="vertical", command=self.history_text.yview)
        self._history_scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_text.configure(yscrollcommand=self._history_scrollbar.set)

        self._bind_main_tooltips()

        self._on_show_log_write()
        self._on_show_status_write()
        self.update_start_stop_button()
        # First real layout pass: sash positions and pane heights can be wrong until the window maps.
        self.after_idle(self._sync_collapsible_panes_after_map)
        self.after_idle(self._refresh_warnings_kpi)

    def _sync_collapsible_panes_after_map(self) -> None:
        try:
            self._on_show_log_write()
            self._on_show_status_write()
        except (tk.TclError, RuntimeError):
            pass

    def open_settings(self) -> None:
        """Polling, Warning Alerts, Completion Alerts, History, prediction — gear entry."""
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
        win.minsize(440, 1)

        outer = ttk.Frame(win, padding=(16, 14), style="Card.TFrame")
        outer.pack(fill="x")

        poll_fr = ttk.LabelFrame(outer, text="Polling", padding=(10, 8))
        poll_fr.pack(fill="x", pady=(0, 8))
        _poll_lbl = ttk.Label(poll_fr, text="Poll (s)")
        _poll_lbl.grid(row=0, column=0, sticky="w", padx=(0, 8))
        _poll_entry = self._make_dark_entry(poll_fr, width=6, textvariable=self.poll_sec_var)
        _poll_entry.grid(row=0, column=1, sticky="w")
        self._bind_static_tooltip(_poll_lbl, "How often the log is read.")
        self._bind_static_tooltip(_poll_entry, "How often the log is read.")

        warn_fr = ttk.LabelFrame(outer, text="Warning Alerts", padding=(10, 8))
        warn_fr.pack(fill="x", pady=(0, 8))
        warn_fr.columnconfigure(0, weight=1)

        thr_row = ttk.Frame(warn_fr, style="Card.TFrame")
        thr_row.grid(row=0, column=0, sticky="ew")
        thr_row.columnconfigure(1, weight=1)
        _thr_lbl = ttk.Label(thr_row, text="Thresholds (comma-separated)")
        _thr_lbl.grid(row=0, column=0, sticky="e", padx=(0, 8))
        _thr_entry = self._make_dark_entry(thr_row, textvariable=self.alert_thresholds_var, width=36)
        _thr_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self._bind_static_tooltip(_thr_lbl, "Alert when your position drops past each number (e.g. 10, 5).")
        self._bind_static_tooltip(_thr_entry, "Alert when your position drops past each number (e.g. 10, 5).")

        checks1 = ttk.Frame(warn_fr, style="Card.TFrame")
        checks1.grid(row=1, column=0, sticky="w", pady=(10, 0))
        _cb_warn_pop = ttk.Checkbutton(checks1, text="Warning popup", variable=self.popup_enabled_var)
        _cb_warn_pop.pack(side="left", padx=(0, 14))
        self._bind_static_tooltip(_cb_warn_pop, "Popup when a threshold is crossed.")
        _cb_warn_snd = ttk.Checkbutton(checks1, text="Warning sound", variable=self.sound_enabled_var)
        _cb_warn_snd.pack(side="left", padx=(0, 14))
        self._bind_static_tooltip(_cb_warn_snd, "Sound when a threshold is crossed.")

        sound_row = ttk.Frame(warn_fr, style="Card.TFrame")
        sound_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        sound_row.columnconfigure(1, weight=1)
        _lbl_warn_sound = ttk.Label(sound_row, text="Warning sound file")
        _lbl_warn_sound.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._bind_static_tooltip(_lbl_warn_sound, "Optional file; default sound if empty.")
        _sound_entry = self._make_dark_entry(sound_row, textvariable=self.alert_sound_path_var)
        _sound_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        _sound_actions = ttk.Frame(sound_row, style="Card.TFrame")
        _sound_actions.grid(row=0, column=2, sticky="e")
        _sound_browse = ttk.Button(_sound_actions, text="Browse…", command=self.browse_alert_sound, width=8)
        _sound_browse.pack(side="left", padx=(0, 6))
        _sound_preview = ttk.Button(_sound_actions, text="Preview", command=self.preview_alert_sound, width=8)
        _sound_preview.pack(side="left")
        self._bind_static_tooltip(_sound_entry, "Optional file; default sound if empty.")
        self._bind_static_tooltip(_sound_browse, "Choose a sound file.")
        self._bind_static_tooltip(_sound_preview, "Play the warning sound once.")

        comp_fr = ttk.LabelFrame(outer, text="Completion Alerts", padding=(10, 8))
        comp_fr.pack(fill="x", pady=(0, 8))
        comp_fr.columnconfigure(0, weight=1)
        _comp_intro = ttk.Label(
            comp_fr,
            text="Fires once when you reach the front (position ≤1). Not threshold-based — only on/off below "
            "(and optional sound file).",
            wraplength=440,
        )
        _comp_intro.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._bind_static_tooltip(_comp_intro, "When you reach the front of the line.")

        checks2 = ttk.Frame(comp_fr, style="Card.TFrame")
        checks2.grid(row=1, column=0, sticky="w", pady=(0, 0))
        _cb_comp_pop = ttk.Checkbutton(checks2, text="Completion popup", variable=self.completion_popup_enabled_var)
        _cb_comp_pop.pack(side="left", padx=(0, 14))
        self._bind_static_tooltip(_cb_comp_pop, "Popup when you reach the front.")
        _cb_comp_snd = ttk.Checkbutton(checks2, text="Completion sound", variable=self.completion_sound_enabled_var)
        _cb_comp_snd.pack(side="left", padx=(0, 0))
        self._bind_static_tooltip(_cb_comp_snd, "Sound when you reach the front.")

        comp_sound_row = ttk.Frame(comp_fr, style="Card.TFrame")
        comp_sound_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        comp_sound_row.columnconfigure(1, weight=1)
        _lbl_comp_sound = ttk.Label(comp_sound_row, text="Completion sound file")
        _lbl_comp_sound.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._bind_static_tooltip(_lbl_comp_sound, "Optional file; default sound if empty.")
        _comp_entry = self._make_dark_entry(comp_sound_row, textvariable=self.completion_sound_path_var)
        _comp_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        _comp_actions = ttk.Frame(comp_sound_row, style="Card.TFrame")
        _comp_actions.grid(row=0, column=2, sticky="e")
        _comp_browse = ttk.Button(_comp_actions, text="Browse…", command=self.browse_completion_sound, width=8)
        _comp_browse.pack(side="left", padx=(0, 6))
        _comp_preview = ttk.Button(_comp_actions, text="Preview", command=self.preview_completion_sound, width=8)
        _comp_preview.pack(side="left")
        self._bind_static_tooltip(_comp_entry, "Optional file; default sound if empty.")
        self._bind_static_tooltip(_comp_browse, "Choose a sound file.")
        self._bind_static_tooltip(_comp_preview, "Play the completion sound once.")

        history_fr = ttk.LabelFrame(outer, text="History", padding=(10, 8))
        history_fr.pack(fill="x", pady=(0, 8))
        _cb_log_every = ttk.Checkbutton(
            history_fr, text="Log every position change", variable=self.show_every_change_var
        )
        _cb_log_every.pack(anchor="w")
        self._bind_static_tooltip(_cb_log_every, "Log every line from the client, or only important changes.")

        display_fr = ttk.LabelFrame(outer, text="Prediction", padding=(10, 8))
        display_fr.pack(fill="x", pady=(0, 10))

        _win_lbl = ttk.Label(display_fr, text="Window (points)")
        _win_lbl.grid(row=0, column=0, sticky="w", padx=(0, 8))
        _win_entry = self._make_dark_entry(display_fr, width=8, textvariable=self.avg_window_var)
        _win_entry.grid(row=0, column=1, sticky="w")
        _avg_tip = "More points: smoother time estimates (uses recent queue history)."
        self._bind_static_tooltip(_win_lbl, _avg_tip)
        self._bind_static_tooltip(_win_entry, _avg_tip)

        bottom = ttk.Frame(outer, style="Card.TFrame")
        bottom.pack(fill="x", pady=(8, 0))
        _btn_reset = ttk.Button(bottom, text="Reset defaults", command=self.reset_defaults)
        _btn_reset.pack(side="left")
        self._bind_static_tooltip(_btn_reset, "Reset all settings here to defaults.")
        _btn_about = ttk.Button(bottom, text="About…", command=self.show_about)
        _btn_about.pack(side="left", padx=(10, 0))
        self._bind_static_tooltip(_btn_about, "Version and project website.")

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
            self._on_show_log_write()
            self._on_show_status_write()
            self.redraw_graph()
            self._refresh_warnings_kpi()

        _btn_close = ttk.Button(bottom, text="Close", command=close_settings)
        _btn_close.pack(side="right")
        self._bind_static_tooltip(_btn_close, "Save and close.")
        win.protocol("WM_DELETE_WINDOW", close_settings)
        win.bind("<Escape>", lambda _e: close_settings())

        try:
            win.grab_set()
        except Exception:
            pass

        win.update_idletasks()
        try:
            self.update_idletasks()
            w = max(380, int(win.winfo_reqwidth()))
            h = int(win.winfo_reqheight())
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _on_avg_window_write(self, *_args: object) -> None:
        """Recompute avg speed / remaining when the rolling window size changes."""
        self.update_time_estimates()

    def update_start_stop_button(self) -> None:
        if self.start_stop_button is None:
            return
        if self.running:
            self.start_stop_button.configure(text="\u25a0", style="PlayStopStop.TButton")
        else:
            self.start_stop_button.configure(text="\u25b6", style="PlayStopPlay.TButton")

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
            "show_status": bool(self.show_status_var.get()),
            "graph_log_scale": bool(self.graph_log_scale_var.get()),
            "popup_enabled": bool(self.popup_enabled_var.get()),
            "sound_enabled": bool(self.sound_enabled_var.get()),
            "alert_sound_path": self.alert_sound_path_var.get().strip(),
            "completion_popup_enabled": bool(self.completion_popup_enabled_var.get()),
            "completion_sound_enabled": bool(self.completion_sound_enabled_var.get()),
            "completion_sound_path": self.completion_sound_path_var.get().strip(),
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
            self.show_status_var,
            self.graph_log_scale_var,
            self.popup_enabled_var,
            self.sound_enabled_var,
            self.alert_sound_path_var,
            self.completion_popup_enabled_var,
            self.completion_sound_enabled_var,
            self.completion_sound_path_var,
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
        self.show_status_var.set(True)
        self.graph_log_scale_var.set(True)
        self.popup_enabled_var.set(True)
        self.sound_enabled_var.set(True)
        self.alert_sound_path_var.set(default_alert_sound_path_for_display())
        self.completion_popup_enabled_var.set(True)
        self.completion_sound_enabled_var.set(True)
        self.completion_sound_path_var.set(default_completion_sound_path_for_display())
        self.show_every_change_var.set(False)

        self.resolved_path_var.set("")
        self._set_status_line("Idle")
        self._set_position_display(None)
        self.elapsed_var.set("—")
        self.predicted_remaining_var.set("—")
        self.queue_rate_var.set("—")
        self.global_rate_var.set("—")
        self.last_change_var.set("—")
        self.last_alert_var.set("—")
        if self._queue_progress is not None:
            self._queue_progress.configure(value=0.0)

        self._position_one_reached_at = None
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
        self._interrupted_mode = False
        self._interrupt_baseline_session = -1
        self._dismissed_new_queue_session = None
        self.graph_points.clear()
        self.current_point = None
        self._alert_thresholds_fired.clear()
        self.redraw_graph()

        self.persist_config()
        self.write_history("Settings reset to defaults.")

        self._on_show_log_write()
        self._on_show_status_write()
        self._refresh_warnings_kpi()

    def _update_history_tab_button_text(self) -> None:
        btn = self._history_tab_btn
        if btn is None:
            return
        if self.show_log_var.get():
            btn.configure(text="\u25bc")
        else:
            btn.configure(text="\u25b2")

    def _update_status_tab_button_text(self) -> None:
        btn = self._status_tab_btn
        if btn is None:
            return
        if self.show_status_var.get():
            btn.configure(text="\u25bc")
        else:
            btn.configure(text="\u25b2")

    def _schedule_pane_fits(self, _event: object = None) -> None:
        """Window/pane resize: refit collapsed History and Status so empty bands don’t linger."""
        self._schedule_fit_history_collapsed(_event)
        self._schedule_fit_status_collapsed(_event)
        self._schedule_pane_drag_thresholds()

    def _schedule_pane_drag_thresholds(self, _event: object = None) -> None:
        """Debounced: apply sash open/close thresholds during drag (Configure + B1-Motion), not only on release."""
        if self._pane_drag_threshold_job is not None:
            try:
                self.after_cancel(self._pane_drag_threshold_job)
            except Exception:
                pass
        self._pane_drag_threshold_job = self.after_idle(self._run_pane_drag_thresholds)

    def _run_pane_drag_thresholds(self) -> None:
        self._pane_drag_threshold_job = None
        self._apply_pane_drag_thresholds()

    def _apply_pane_drag_thresholds(self) -> None:
        """Stretch past header + margin opens a collapsed pane; squeeze past max height collapses expanded."""
        if self.panes is None:
            return
        try:
            self.update_idletasks()
        except tk.TclError:
            return
        sf = self.status_frame
        hf = self.history_frame
        if sf is not None:
            try:
                h = int(sf.winfo_height())
            except (tk.TclError, ValueError):
                h = 0
            if self.show_status_var.get():
                if h <= UI_STATUS_DRAG_AUTO_COLLAPSE_MAX_H:
                    self.show_status_var.set(False)
            else:
                try:
                    need = self._collapsed_status_pane_minsize()
                except Exception:
                    need = UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
                open_min = max(
                    need + PANE_DRAG_OPEN_EXTRA_PX,
                    UI_STATUS_PANE_MIN_EXPANDED + 24,
                )
                if h >= open_min:
                    self.show_status_var.set(True)
        if hf is not None:
            try:
                h = int(hf.winfo_height())
            except (tk.TclError, ValueError):
                h = 0
            if self.show_log_var.get():
                if h <= UI_HISTORY_DRAG_AUTO_COLLAPSE_MAX_H:
                    self.show_log_var.set(False)
            else:
                try:
                    need = self._collapsed_history_pane_minsize()
                except Exception:
                    need = UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
                open_min = max(
                    need + PANE_DRAG_OPEN_EXTRA_PX,
                    UI_HISTORY_PANE_MIN_EXPANDED + 24,
                )
                if h >= open_min:
                    self.show_log_var.set(True)

    def _collapsed_status_pane_minsize(self) -> int:
        """Minimum PanedWindow height for Status when details are hidden (clickable header only)."""
        if self.status_frame is None:
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
        try:
            self.update_idletasks()
            self.status_frame.update_idletasks()
            h = int(self.status_frame.winfo_reqheight())
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK

    def _collapsed_history_pane_minsize(self) -> int:
        """Minimum PanedWindow height for History when log body is hidden (clickable header only)."""
        if self.history_frame is None:
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
        try:
            self.update_idletasks()
            self.history_frame.update_idletasks()
            h = int(self.history_frame.winfo_reqheight())
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK

    def _status_pane_min_for_layout(self) -> int:
        """Reserved height for Status pane when positioning sashes (expanded min or header-only)."""
        if self.status_frame is None:
            return UI_STATUS_PANE_MIN_EXPANDED
        try:
            self.update_idletasks()
            self.status_frame.update_idletasks()
            h = int(self.status_frame.winfo_reqheight())
            if self.show_status_var.get():
                return max(UI_STATUS_PANE_MIN_EXPANDED, h)
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return (
                UI_STATUS_PANE_MIN_EXPANDED
                if self.show_status_var.get()
                else UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
            )

    def _wire_collapsible_header(
        self,
        strip: tk.Misc,
        title: tk.Misc,
        toggle: Callable[[], None],
    ) -> None:
        """Whole header bar + title toggle; chevron keeps its own command (no double toggle).

        Pack an expanding tk.Frame after the chevron + title so the full row receives clicks
        (ttk strip alone often only sizes to its packed children).
        """

        def on_click(_evt: object) -> None:
            toggle()

        filler = tk.Frame(strip, bg=UI_BG_CARD, cursor="hand2", highlightthickness=0, bd=0)
        filler.pack(side="left", fill=tk.BOTH, expand=True)

        for w in (strip, title, filler):
            try:
                w.configure(cursor="hand2")
            except tk.TclError:
                pass
            w.bind("<Button-1>", on_click, add=True)

    @staticmethod
    def _wire_collapsible_hand_cursor(widget: tk.Misc) -> None:
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass

    def _toggle_history_panel(self) -> None:
        self.show_log_var.set(not self.show_log_var.get())

    def _toggle_status_panel(self) -> None:
        self.show_status_var.set(not self.show_status_var.get())

    def _on_show_log_write(self, *_args: object) -> None:
        self.update_log_visibility()
        self._update_history_tab_button_text()

    def _on_show_status_write(self, *_args: object) -> None:
        self.update_status_visibility()
        self._update_status_tab_button_text()

    def update_status_visibility(self) -> None:
        """Show or hide Status details; header + chevron stay like History."""
        if self.status_frame is None or self.panes is None or self._status_body_wrap is None:
            return
        panes = self.panes
        sf = self.status_frame
        body = self._status_body_wrap
        sep = self._status_sep

        if self.show_status_var.get():
            sf.configure(padding=UI_HISTORY_FRAME_PAD_EXPANDED)
            # Hug content height: no extra vertical stretch inside the pane; width still fills.
            body.grid(row=2, column=0, sticky="new")
            if sep is not None:
                sep.grid(row=1, column=0, sticky="ew", pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            sf.rowconfigure(2, weight=0)
            try:
                panes.paneconfigure(sf, minsize=UI_STATUS_PANE_MIN_EXPANDED, stretch="never")
            except Exception:
                pass
            self.after(1, self._fit_status_pane_expanded)
            self.after(50, self._fit_status_pane_expanded)
            self.after(200, self._fit_status_pane_expanded)
        else:
            sf.configure(padding=UI_HISTORY_FRAME_PAD_COLLAPSED)
            body.grid_remove()
            if sep is not None:
                sep.grid_remove()
            sf.rowconfigure(2, weight=0)
            try:
                self.update_idletasks()
                need = self._collapsed_status_pane_minsize()
                panes.paneconfigure(sf, minsize=need, stretch="never")
                panes.paneconfigure(sf, height=need)
            except Exception:
                pass
            self._schedule_fit_status_collapsed()
            self.after(50, self._fit_status_pane_collapsed)
            self.after(200, self._fit_status_pane_collapsed)

    def _schedule_fit_status_collapsed(self, _event: object = None) -> None:
        if self.show_status_var.get():
            return
        if self._fit_status_collapsed_job is not None:
            try:
                self.after_cancel(self._fit_status_collapsed_job)
            except Exception:
                pass
        self._fit_status_collapsed_job = self.after(50, self._fit_status_collapsed_run)

    def _fit_status_collapsed_run(self) -> None:
        self._fit_status_collapsed_job = None
        self._fit_status_pane_collapsed()

    def _fit_status_pane_expanded(self) -> None:
        """Set the Status pane height to fit all visible content (no clipping, no wasted band)."""
        if self.panes is None or self.status_frame is None or not self.show_status_var.get():
            return
        try:
            self.update_idletasks()
            sf = self.status_frame
            need = max(UI_STATUS_PANE_MIN_EXPANDED, int(sf.winfo_reqheight()))
            self.panes.paneconfigure(sf, height=need)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

    def _fit_status_pane_collapsed(self) -> None:
        """Shrink the middle pane so only the Status tab row shows when content is hidden."""
        if self.panes is None or self.status_frame is None or self.show_status_var.get():
            return
        try:
            self.update_idletasks()
            pw = self.panes
            sf = self.status_frame
            sf.update_idletasks()
            need = self._collapsed_status_pane_minsize()
            try:
                ah = int(sf.winfo_height())
                open_min = max(
                    need + PANE_DRAG_OPEN_EXTRA_PX,
                    UI_STATUS_PANE_MIN_EXPANDED + 24,
                )
                if ah >= open_min:
                    self.show_status_var.set(True)
                    return
            except (tk.TclError, ValueError):
                pass
            # Fixed height when collapsed (header row only); need is refreshed on resize via _schedule_pane_fits.
            try:
                pw.paneconfigure(sf, minsize=need, stretch="never")
                pw.paneconfigure(sf, height=need)
            except (tk.TclError, ValueError):
                pass
            ph = max(1, pw.winfo_height())
            sash_w = UI_PANE_SASH_WIDTH
            sashpad = UI_PANE_SASH_PAD
            try:
                sp1 = int(float(pw.sashpos(1)))
            except (tk.TclError, ValueError):
                sp1 = max(200, ph * 2 // 3)
            target0 = sp1 - need - sash_w - 2 * sashpad
            graph_min = 120
            target0 = max(target0, graph_min)
            hist_min = (
                UI_HISTORY_PANE_MIN_EXPANDED
                if self.show_log_var.get()
                else self._collapsed_history_pane_minsize()
            )
            target0 = min(target0, sp1 - hist_min - sash_w - 2 * sashpad)
            pw.sashpos(0, target0)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

    def update_log_visibility(self) -> None:
        """Show or hide history *content*; header bar stays between Status and the text area."""
        if self.history_frame is None or self.panes is None or self._history_body is None:
            return
        panes = self.panes
        history = self.history_frame
        body = self._history_body
        sep = self._history_sep

        if self.show_log_var.get():
            history.configure(padding=UI_HISTORY_FRAME_PAD_EXPANDED)
            body.grid(row=2, column=0, sticky="nsew")
            if sep is not None:
                sep.grid(row=1, column=0, sticky="ew", pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            history.rowconfigure(2, weight=1)
            try:
                panes.paneconfigure(history, minsize=UI_HISTORY_PANE_MIN_EXPANDED, stretch="always")
            except Exception:
                pass
            try:
                panes.paneconfigure(history, height="")
            except Exception:
                pass
        else:
            history.configure(padding=UI_HISTORY_FRAME_PAD_COLLAPSED)
            body.grid_remove()
            if sep is not None:
                sep.grid_remove()
            history.rowconfigure(2, weight=0)
            try:
                self.update_idletasks()
                need = self._collapsed_history_pane_minsize()
                panes.paneconfigure(history, minsize=need, stretch="never")
                panes.paneconfigure(history, height=need)
            except Exception:
                pass
            self._schedule_fit_history_collapsed()
            self.after(50, self._fit_history_pane_collapsed)
            self.after(200, self._fit_history_pane_collapsed)

    def _schedule_fit_history_collapsed(self, _event: object = None) -> None:
        """Debounced: keep bottom pane minimal when History content is hidden (also on window resize)."""
        if self.show_log_var.get():
            return
        if self._fit_history_collapsed_job is not None:
            try:
                self.after_cancel(self._fit_history_collapsed_job)
            except Exception:
                pass
        self._fit_history_collapsed_job = self.after(50, self._fit_history_collapsed_run)

    def _fit_history_collapsed_run(self) -> None:
        self._fit_history_collapsed_job = None
        self._fit_history_pane_collapsed()

    def _fit_history_pane_collapsed(self) -> None:
        """Shrink the bottom PanedWindow pane so only the History tab row shows (no empty band)."""
        if self.panes is None or self.history_frame is None or self.show_log_var.get():
            return
        try:
            self.update_idletasks()
            pw = self.panes
            hf = self.history_frame
            hf.update_idletasks()
            need = self._collapsed_history_pane_minsize()
            try:
                ah = int(hf.winfo_height())
                open_min = max(
                    need + PANE_DRAG_OPEN_EXTRA_PX,
                    UI_HISTORY_PANE_MIN_EXPANDED + 24,
                )
                if ah >= open_min:
                    self.show_log_var.set(True)
                    return
            except (tk.TclError, ValueError):
                pass

            try:
                pw.paneconfigure(hf, minsize=need, stretch="never")
                pw.paneconfigure(hf, height=need)
            except (tk.TclError, ValueError):
                pass

            ph = max(1, pw.winfo_height())
            sash_w = UI_PANE_SASH_WIDTH
            sashpad = UI_PANE_SASH_PAD
            status_min = self._status_pane_min_for_layout()
            target = ph - need - sash_w - 2 * sashpad - 1
            s0 = int(float(pw.sashpos(0)))
            lo = s0 + sash_w + 2 * sashpad + status_min
            target = max(int(target), lo)
            target = min(target, ph - 4)
            pw.sashpos(1, target)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

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

    def _set_position_display(self, pos: Optional[int]) -> None:
        """KPI digits at full size; front-of-queue celebration emoji slightly smaller."""
        if pos is None:
            self.position_var.set("—")
        else:
            self.position_var.set(str(pos))
        if self._position_emoji_label is not None:
            self._position_emoji_label.configure(text=("\U0001f389" if pos == 1 else ""))

    def _refresh_warnings_kpi(self) -> None:
        """Configured CSV thresholds; mute each value once position ≤ that threshold (or alert already fired)."""
        fr = getattr(self, "_warnings_kpi_frame", None)
        if fr is None:
            return
        try:
            if not fr.winfo_exists():
                return
        except tk.TclError:
            return
        for w in fr.winfo_children():
            w.destroy()
        try:
            thresholds = parse_alert_thresholds(self.alert_thresholds_var.get())
        except ValueError:
            tk.Label(
                fr,
                text="—",
                bg=UI_SUMMARY_BG,
                fg=UI_TEXT_MUTED,
                font=KPI_VALUE_FONT,
                anchor="w",
            ).pack(side="left")
            return
        if not thresholds:
            tk.Label(
                fr,
                text="—",
                bg=UI_SUMMARY_BG,
                fg=UI_TEXT_MUTED,
                font=KPI_VALUE_FONT,
                anchor="w",
            ).pack(side="left")
            return
        pos: Optional[int] = self.last_position
        if pos is None and self.current_point is not None:
            pos = self.current_point[1]
        fired = self._alert_thresholds_fired
        for i, t in enumerate(thresholds):
            if i > 0:
                tk.Label(
                    fr,
                    text="\u00b7",
                    bg=UI_SUMMARY_BG,
                    fg=UI_TEXT_MUTED,
                    font=KPI_VALUE_FONT,
                    anchor="w",
                ).pack(side="left", padx=(3, 3))
            # Mute when we've already crossed in a poll, or current position is at/below the threshold
            # (covers joining mid-run without a recorded crossing, e.g. already at 6 vs threshold 10).
            passed = (pos is not None and pos <= t) or (t in fired)
            fg = UI_TEXT_MUTED if passed else UI_SUMMARY_VALUE
            tk.Label(
                fr,
                text=str(t),
                bg=UI_SUMMARY_BG,
                fg=fg,
                font=KPI_VALUE_FONT,
                anchor="w",
            ).pack(side="left")

    def _apply_browsed_log_path(self, raw: str) -> None:
        """Set log source from a browsed folder path (resolve_log_file picks the log file inside)."""
        raw = (raw or "").strip()
        if not raw:
            return
        try:
            p = expand_path(raw)
        except Exception:
            self.source_path_var.set(raw)
            self.after(0, self._try_start_after_browse)
            return
        if p.is_dir():
            self.source_path_var.set(str(p))
        elif p.is_file():
            self.source_path_var.set(str(p.parent))
        else:
            self.source_path_var.set(raw)
        self.after(0, self._try_start_after_browse)

    def browse_logs_folder(self) -> None:
        """Pick the Vintage Story data or Logs folder; the app resolves client-main.log (etc.) inside."""
        initialdir = browse_initialdir_from_path(self.source_path_var.get())
        selected = filedialog.askdirectory(
            parent=self,
            title="Select Logs folder (Vintage Story data directory)",
            initialdir=initialdir,
        )
        if selected:
            self._apply_browsed_log_path(selected)

    def _try_start_after_browse(self) -> None:
        """Begin monitoring with the path chosen via Browse… (restarts if already running)."""
        if self._starting:
            return
        if self.running:
            self.stop_monitoring()
        self.start_monitoring()

    def browse_alert_sound(self) -> None:
        parent = self._settings_win
        try:
            if parent is None or not parent.winfo_exists():
                parent = self
        except Exception:
            parent = self
        initialdir = browse_initialdir_from_path(self.alert_sound_path_var.get())
        selected = filedialog.askopenfilename(
            parent=parent,
            title="Select warning sound file",
            initialdir=initialdir,
            filetypes=[
                ("Audio", "*.wav *.mp3 *.aiff *.aif *.flac *.ogg"),
                ("WAV", "*.wav"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.alert_sound_path_var.set(selected)

    def browse_completion_sound(self) -> None:
        parent = self._settings_win
        try:
            if parent is None or not parent.winfo_exists():
                parent = self
        except Exception:
            parent = self
        initialdir = browse_initialdir_from_path(self.completion_sound_path_var.get())
        selected = filedialog.askopenfilename(
            parent=parent,
            title="Select completion sound file",
            initialdir=initialdir,
            filetypes=[
                ("Audio", "*.wav *.mp3 *.aiff *.aif *.flac *.ogg"),
                ("WAV", "*.wav"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.completion_sound_path_var.set(selected)

    def preview_alert_sound(self) -> None:
        """Play the configured warning sound once (for Settings); ignores the Warning sound checkbox."""
        self.play_sound()

    def preview_completion_sound(self) -> None:
        """Play the configured completion sound once; ignores the Completion sound checkbox."""
        self.play_completion_sound()

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
            self.start_stop_button.state(["disabled"])
            if self._settings_btn is not None:
                self._loading_spinner.pack(side="left", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), before=self._settings_btn)
            else:
                self._loading_spinner.pack(side="left", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            self._loading_spinner.start(12)
        else:
            self._loading_spinner.stop()
            self._loading_spinner.pack_forget()
            self.start_stop_button.state(["!disabled"])
            self.update_start_stop_button()

    def start_monitoring(self) -> None:
        if self._starting:
            return
        try:
            resolved = resolve_log_file(self.source_path_var.get())
            if not resolved:
                raise ValueError(
                    "Could not find a client log under that folder. Set Logs folder to your Vintage Story "
                    "data directory (or the Logs folder inside it), or use Browse…."
                )

            try:
                parse_alert_thresholds(self.alert_thresholds_var.get())
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            self._alert_thresholds_fired.clear()
            self._position_one_reached_at = None
            self._queue_completion_notified_this_run = False
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
        seed_data: Optional[
            tuple[
                list[tuple[float, int]],
                int,
                int,
                float,
                int,
                int,
                int,
                Optional[int],
            ]
        ],
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

        if error is not None:
            self._show_start_loading(False)
            self._set_status_line("Error")
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

        self._show_start_loading(False)

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
        self._queue_stale_latched = False
        self._queue_stale_logged_once = False
        self._position_one_reached_at = None
        self._mpp_floor_position = None
        self._mpp_floor_value = None
        self._alert_thresholds_fired.clear()
        self._queue_completion_notified_this_run = False
        ok = self._reseed_graph_for_new_run(path)
        if ok:
            self._set_status_line("Monitoring")
        else:
            self.write_history("Could not find queue data in the log for the new run.")
            self._set_status_line("Watching log, queue line not found yet")
            self.graph_points.clear()
            self.current_point = None
            self.last_position = None
            self._set_position_display(None)
            self.redraw_graph()

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
        try:
            self._refresh_warnings_kpi()
        except Exception:
            pass

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

    def _reseed_graph_for_new_run(self, log_file: Path) -> bool:
        """Replace the graph for a new queue session: full segment from log, or one point from the tail."""
        data = compute_seed_graph_from_log(log_file)
        if data is not None:
            self._apply_seed_result(data)
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
        self.append_graph_point(pos)
        self.update_time_estimates()
        self.write_history(
            "Graph reset to current queue position (full history unavailable from log scan)."
        )
        return True

    def _apply_seed_result(
        self,
        data: Optional[
            tuple[
                list[tuple[float, int]],
                int,
                int,
                float,
                int,
                int,
                int,
                Optional[int],
            ]
        ],
    ) -> None:
        if data is None:
            return
        (
            segment_points,
            segment_len,
            positions_len,
            tail_mb,
            seg_min,
            seg_max,
            queue_run_session_id,
            authoritative_pos,
        ) = data
        self._last_queue_run_session = queue_run_session_id
        self.graph_points.clear()
        for item in segment_points:
            self.graph_points.append(item)
        # Segment last point can disagree with walk's last event (e.g. stale duplicate clause).
        # Always align the plotted tail and POSITION with parse_tail_last_queue_reading.
        if authoritative_pos is not None and self.graph_points:
            t_last = self.graph_points[-1][0]
            self.graph_points[-1] = (t_last, authoritative_pos)
        self.current_point = self.graph_points[-1] if self.graph_points else None
        if self.current_point is not None:
            _t, pos = self.current_point
            self.last_position = pos
            self._set_position_display(pos)
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
                    self._queue_completion_notified_this_run = False
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
                        self._set_position_display(None)
                        self.last_position = None
                    elif (kind in ("reconnecting", "grace") or log_silent) and not (
                        position is not None and position <= 1
                    ):
                        # At queue front (≤1), tail lines often still look "connecting"; keep Completed/Monitoring.
                        self._queue_stale_latched = False
                        self._queue_stale_logged_once = False
                        self._last_queue_position_change_epoch = None
                        self._last_queue_line_epoch = None
                        if log_silent or kind == "grace":
                            self._set_status_line("Reconnecting…")
                        else:
                            self._set_status_line("Connecting…")
                        self._set_position_display(None)
                        self.last_position = None
                    elif position is not None and (not log_silent or position <= 1):
                        prev_pos = self.last_position
                        now = time.time()
                        stale_limit = QUEUE_UPDATE_INTERVAL_SEC * QUEUE_STALE_TIMEOUT_MULT

                        new_queue_run = (
                            self._last_queue_run_session >= 0
                            and queue_sess > self._last_queue_run_session
                        )
                        if (
                            not new_queue_run
                            and prev_pos is not None
                            and position > prev_pos
                            and (position - prev_pos) >= QUEUE_RESET_JUMP_THRESHOLD
                        ):
                            # Same queue run: big upward jumps are usually stale log lines (e.g. 108),
                            # not real position — the queue normally moves down. New runs are handled
                            # via queue_sess above; small bumps (+1..9) can happen when others join.
                            position = prev_pos

                        if self._queue_stale_latched:
                            if self._last_queue_line_epoch is not None and now - self._last_queue_line_epoch <= stale_limit:
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                            else:
                                self.enter_interrupted_state("Stale latch (queue lines did not recover).")

                        if not self._interrupted_mode:
                            if position > 1:
                                self._queue_completion_notified_this_run = False
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
                                self._queue_completion_notified_this_run = False
                                self._last_queue_position_change_epoch = time.time()
                                self._queue_stale_latched = False
                                self._queue_stale_logged_once = False
                                self._mpp_floor_position = None
                                self._mpp_floor_value = None
                                self.write_history("New queue run (from log).")
                                if self.current_log_file is not None:
                                    self._reseed_graph_for_new_run(self.current_log_file)
                            self._last_queue_run_session = queue_sess
                            self._set_status_line("Completed" if position <= 1 else "Monitoring")
                            self._set_position_display(position)
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
                            self._maybe_notify_queue_completion(prev_pos, position)
                    elif not log_silent:
                        self._set_status_line("Watching log, queue line not found yet")
        except Exception as exc:
            self._set_status_line("Error")
            self.write_history(f"Error: {exc}")
            self.write_history(traceback.format_exc().splitlines()[-1])
        finally:
            try:
                self._refresh_warnings_kpi()
            except Exception:
                pass
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
        """Minutes per queue step for the RATE display."""
        if mpp is not None and mpp > 0:
            return f"{mpp:.2f} min/pos"
        return "—"

    def _schedule_resize_refresh(self, evt: Optional[tk.Event] = None) -> None:
        if evt is not None and getattr(evt, "widget", None) is not self:
            return
        if self._configure_resize_job is not None:
            try:
                self.after_cancel(self._configure_resize_job)
            except Exception:
                pass
        self._configure_resize_job = self.after(150, self._on_resize_refresh_done)

    def _on_resize_refresh_done(self) -> None:
        self._configure_resize_job = None
        self.update_time_estimates()

    def _progress_tooltip_text(self) -> str:
        """Progress bar hover: percent of estimated wait so far."""
        p = 0.0
        if self._queue_progress is not None:
            try:
                p = float(self._queue_progress["value"])
            except (tk.TclError, TypeError, ValueError):
                pass
        return f"Estimated wait so far: {p:.0f}%."

    def _clamp_tooltip_in_host(
        self, host: tk.Misc, tip: tk.Toplevel, x_left: int, y_top: int, margin: int = 6
    ) -> tuple[int, int]:
        """Keep overrideredirect tooltip top-left inside the host toplevel (main or Settings)."""
        try:
            host.update_idletasks()
            tip.update_idletasks()
            tw = int(tip.winfo_reqwidth())
            th = int(tip.winfo_reqheight())
            rx = int(host.winfo_rootx())
            ry = int(host.winfo_rooty())
            rw = int(host.winfo_width())
            rh = int(host.winfo_height())
            if rw < 40 or rh < 40:
                return x_left, y_top
            x_left = max(rx + margin, min(x_left, rx + rw - tw - margin))
            y_top = max(ry + margin, min(y_top, ry + rh - th - margin))
        except (tk.TclError, ValueError):
            pass
        return x_left, y_top

    def _bind_static_tooltip(self, widget: tk.Misc, text: Union[str, Callable[[], str]]) -> None:
        state: dict[str, Optional[object]] = {"win": None, "job": None}

        def hide(_evt: object = None) -> None:
            jid = state["job"]
            if jid is not None:
                try:
                    self.after_cancel(jid)
                except Exception:
                    pass
                state["job"] = None
            tw = state["win"]
            if tw is not None:
                try:
                    if isinstance(tw, tk.Toplevel) and tw.winfo_exists():
                        tw.destroy()
                except Exception:
                    pass
                state["win"] = None

        def show_delayed(_evt: object) -> None:
            hide()

            def show() -> None:
                state["job"] = None
                try:
                    if not widget.winfo_exists():
                        return
                except Exception:
                    return
                resolved = text() if callable(text) else text
                x = int(widget.winfo_rootx() + widget.winfo_width() // 2)
                y = int(widget.winfo_rooty() + widget.winfo_height() + 6)
                try:
                    host = widget.winfo_toplevel()
                except tk.TclError:
                    host = self
                tip = tk.Toplevel(host)
                tip.wm_overrideredirect(True)
                try:
                    tip.attributes("-topmost", True)
                except Exception:
                    pass
                tk.Label(
                    tip,
                    text=resolved,
                    justify="left",
                    background=UI_TOOLTIP_BG,
                    foreground=UI_TOOLTIP_FG,
                    padx=10,
                    pady=8,
                    wraplength=340,
                ).pack()
                state["win"] = tip
                tip.update_idletasks()
                tw = tip.winfo_reqwidth()
                x_left = int(x - tw // 2)
                y_top = int(y)
                x_left, y_top = self._clamp_tooltip_in_host(host, tip, x_left, y_top)
                tip.geometry(f"+{x_left}+{y_top}")

            state["job"] = self.after(420, show)

        widget.bind("<Enter>", show_delayed, add=True)
        widget.bind("<Leave>", hide, add=True)

    def _bind_main_tooltips(self) -> None:
        """Hover help for the main window (uses the same delayed toplevel as _bind_static_tooltip)."""
        bt = self._bind_static_tooltip
        bt(self.start_stop_button, "Start or stop monitoring.")
        bt(
            self._lbl_log_path,
            "Folder to search (not a .log file). The app opens client-main.log when present, then other client log names.",
        )
        bt(
            self._path_entry,
            "VintagestoryData or Logs folder path. Resolution prefers client-main.log under common layouts.",
        )
        bt(
            self._btn_browse_logs,
            "Pick a folder only. The app resolves client-main.log (or another matching client log) inside.",
        )
        bt(self._settings_btn, "Settings")
        bt(self._loading_spinner, "Loading…")
        bt(self._graph_labelframe, "Queue position over time.")
        bt(self._position_value_label, "Smaller number = closer to the front.")
        bt(self._status_value_label, "What the app is doing.")
        bt(self._queue_rate_value_label, "Rough minutes to move one spot in line.")
        bt(
            self._lbl_kpi_warnings,
            "Warning thresholds from Settings; muted when your position is at or below that number (or already alerted).",
        )
        bt(
            self._warnings_kpi_frame,
            "Same: a value grays out once your queue position is ≤ that threshold, or after that alert fired.",
        )
        bt(self._elapsed_value_label, "Time in queue this run.")
        bt(self._remaining_value_label, "Estimated wait left (hidden at the front).")
        bt(self._graph_stack_frame, "Drag edges to resize panels. Y: chart scale.")
        bt(self.graph_canvas, "Move the mouse for time and position.")
        bt(self._status_tab_strip, "Show or hide Info panel.")
        bt(self._lbl_status_section_title, "Show or hide Info panel.")
        bt(self._status_tab_btn, "Show or hide Info panel.")
        bt(
            self._lbl_det_global_rate,
            "Average minutes per position over every queue advance in the graph (full session).",
        )
        bt(self._lbl_det_global_rate_val, "Same — mean over all downward steps; KPI Rate uses the prediction window.")
        bt(self._lbl_det_last_change_val, "When your position last changed.")
        bt(self._lbl_det_alert_val, "Last threshold alert.")
        bt(self._lbl_det_path_val, "Log file in use.")
        bt(self._history_tab_strip, "Show or hide History.")
        bt(self._lbl_history_section_title, "Show or hide History.")
        bt(self._history_tab_btn, "Show or hide History.")
        bt(self.history_text, "Session log.")

    def _bind_keyboard_shortcuts(self) -> None:
        self.bind("<Control-m>", self._shortcut_toggle_monitoring)
        self.bind("<Control-M>", self._shortcut_toggle_monitoring)

        def on_space(evt: tk.Event) -> str | None:
            w = self.focus_get()
            if w is not None:
                cls = getattr(w, "winfo_class", lambda: "")()
                if cls in ("Text", "TEntry", "Entry", "TCombobox", "Spinbox", "TSpinbox"):
                    return None
            self.toggle_monitoring()
            return "break"

        self.bind("<space>", on_space)

    def _shortcut_toggle_monitoring(self, _evt: tk.Event) -> str:
        self.toggle_monitoring()
        return "break"

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
            mpp = (dt / 60.0) / float(improvement)
            if mpp > 0 and math.isfinite(mpp):
                mpps.append(mpp)
        if not mpps:
            return None
        return sum(mpps) / len(mpps)

    def _refresh_queue_and_global_rate(self, pos: Optional[int]) -> Optional[float]:
        """KPI Rate (window / dwell model) and Info Global Rate (mean over full history segments). Returns capped mpp for ETA fallback."""
        mpp_raw = self._minutes_per_position_from_window()
        mpp = self._minutes_per_position_capped_for_dwell(mpp_raw, pos)
        self.queue_rate_var.set(self._format_queue_rate(mpp))
        g_mpp = self._global_avg_minutes_per_position()
        self.global_rate_var.set(self._format_queue_rate(g_mpp))
        return mpp

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
            self._refresh_queue_and_global_rate(pos)
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

        # ETA updates _pred_speed_scale; KPI Rate + Info Global Rate from window model vs full history.
        mpp = self._refresh_queue_and_global_rate(pos)

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
                    p = min(100.0, max(0.0, 100.0 * elapsed_sec / total))
                    self._queue_progress["value"] = p
                else:
                    self._queue_progress["value"] = 0.0
            else:
                self._queue_progress["value"] = 0.0

    def _update_graph_y_scale_button_text(self) -> None:
        btn = self._graph_y_scale_btn
        if btn is None:
            return
        if self.graph_log_scale_var.get():
            btn.configure(text="Y \u2192 log")
        else:
            btn.configure(text="Y \u2192 linear")

    def _toggle_graph_y_scale(self) -> None:
        self.graph_log_scale_var.set(not self.graph_log_scale_var.get())
        self.redraw_graph()

    def _position_graph_y_scale_button(self, _evt: object | None = None) -> None:
        """Place Y-scale control at top-right inside the plot area (not canvas corner — avoids top margin clip)."""
        canvas = self.graph_canvas
        btn = self._graph_y_scale_btn
        if canvas is None or btn is None:
            return
        try:
            w = int(canvas.winfo_width())
        except tk.TclError:
            return
        if w <= 10:
            return
        x_right = w - GRAPH_CANVAS_PAD_RIGHT - GRAPH_Y_SCALE_BTN_INSET_X
        y_top = GRAPH_CANVAS_PAD_TOP + GRAPH_Y_SCALE_BTN_INSET_Y
        btn.place_configure(x=x_right, y=y_top, anchor="ne")

    def _on_graph_canvas_configure(self, _evt: object) -> None:
        self._position_graph_y_scale_button()
        self.redraw_graph()

    def redraw_graph(self) -> None:
        canvas = self.graph_canvas
        if canvas is None:
            return
        canvas.delete("all")

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return

        # Leave space for axis labels (especially X time labels) and the Y-scale overlay.
        pad_left = GRAPH_CANVAS_PAD_LEFT
        pad_right = GRAPH_CANVAS_PAD_RIGHT
        pad_top = GRAPH_CANVAS_PAD_TOP
        pad_bottom = GRAPH_CANVAS_PAD_BOTTOM
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
        if len(points) == 0:
            self._graph_hover_point = None
            canvas.create_text(x0 + 6, y0 + 6, anchor="nw", text="No data yet", fill=UI_GRAPH_EMPTY)
            return

        if len(points) == 1:
            t_mid = float(points[0][0])
            half = SINGLE_POINT_GRAPH_SPAN_SEC / 2.0
            t0 = t_mid - half
            t1 = t_mid + half
        else:
            t0 = float(points[0][0])
            t1 = float(points[-1][0])
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
        # Fewer major divisions than raw "≤8 intervals" so tick marks do not pack tighter than labels.
        target_ticks = 6
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

        # Drop times that map to the same pixel column (stacked labels when span is tiny).
        _dedup: list[float] = []
        for tv in sorted(tick_times):
            xv = x_of(tv)
            if not _dedup or abs(xv - x_of(_dedup[-1])) > 2.0:
                _dedup.append(tv)
        tick_times = _dedup

        # "HH:MM:SS" needs more horizontal room than min_label_dx alone; cap count by plot width.
        min_label_dx = max(76.0, min(130.0, plot_w / 7.5))
        last_x_label: Optional[float] = None
        for idx, t in enumerate(tick_times):
            x = x_of(t)
            label = datetime.fromtimestamp(t).strftime(fmt)
            canvas.create_line(x, y1, x, y1 + 4, fill=axis_color)
            if last_x_label is None or abs(x - last_x_label) >= min_label_dx:
                canvas.create_text(x, y1 + 14, anchor="n", text=label, fill=text_color)
                last_x_label = x
            if 0 < idx < len(tick_times) - 1:
                canvas.create_line(x, y0, x, y1, fill=UI_GRAPH_GRID)

        # Minor X ticks: minute-scale marks on the axis only; spacing adapts so ticks do not pile up.
        span_sec = t1 - t0
        if span_sec > 1e-6:
            major_xs = [x_of(float(tv)) for tv in tick_times]
            minor_candidates = (60, 120, 300, 600, 900, 1800, 3600, 7200)
            minor_step_sec = 60.0
            for step in minor_candidates:
                minor_step_sec = float(step)
                n_divs = span_sec / minor_step_sec
                if n_divs < 1.5:
                    continue
                px_per_div = plot_w / n_divs
                if px_per_div >= 5.0:
                    break
            else:
                minor_step_sec = max(60.0, span_sec / max(1.0, plot_w / 5.0))

            major_clear_px = 6.0

            def _too_close_to_major(xm: float) -> bool:
                for xa in major_xs:
                    if abs(xm - xa) <= major_clear_px:
                        return True
                return False

            m_start = math.ceil(t0 / minor_step_sec) * minor_step_sec
            m = m_start
            last_minor_x: Optional[float] = None
            while m <= t1 + 1e-6:
                xm = x_of(m)
                if x0 <= xm <= x1 and not _too_close_to_major(xm):
                    if last_minor_x is None or abs(xm - last_minor_x) >= 4.0:
                        canvas.create_line(xm, y1, xm, y1 + 3, fill=UI_GRAPH_MINOR_TICK, width=1)
                        last_minor_x = xm
                m += minor_step_sec

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
        elif len(points) == 1 and step_vertices:
            _ts, _pv = step_vertices[0]
            _lx = x_of(_ts)
            _ly = y_of(_pv)
            canvas.create_line(x0, _ly, _lx, _ly, fill=UI_GRAPH_LINE, width=2, smooth=False)

        marker = self.current_point or points[-1]
        last_t, last_v = marker
        lx = x_of(last_t)
        ly = y_of(last_v)
        canvas.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, outline="", fill=UI_GRAPH_MARKER)
        canvas.create_text(lx + 10, ly, anchor="w", text=str(last_v), fill=UI_GRAPH_TEXT)

        hp = self._graph_hover_point
        if hp is not None:
            ht, hv = hp
            hx = x_of(ht)
            hy = y_of(hv)
            canvas.create_line(hx, y0, hx, y1, fill=UI_GRAPH_HOVER_CURSOR, width=1)
            canvas.create_oval(
                hx - 5,
                hy - 5,
                hx + 5,
                hy + 5,
                outline=UI_GRAPH_LINE,
                width=2,
                fill=UI_GRAPH_PLOT,
            )

    def on_graph_motion(self, evt: tk.Event) -> None:
        points = self.graph_points_drawn
        canvas = self.graph_canvas
        if canvas is None or len(points) < 1:
            return

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return

        pad_left = GRAPH_CANVAS_PAD_LEFT
        pad_right = GRAPH_CANVAS_PAD_RIGHT
        plot_w = max(1, width - pad_left - pad_right)

        x = max(pad_left, min(pad_left + plot_w, evt.x))
        t0 = float(points[0][0])
        t1 = float(points[-1][0])
        if len(points) == 1:
            half = SINGLE_POINT_GRAPH_SPAN_SEC / 2.0
            t0 = t0 - half
            t1 = t1 + half
        elif t1 <= t0:
            t1 = t0 + 1e-6
        target_t = t0 + (x - pad_left) / plot_w * (t1 - t0)

        # Find nearest point by time
        best = points[0]
        best_dt = abs(best[0] - target_t)
        for pt in points[1:]:
            dt = abs(pt[0] - target_t)
            if dt < best_dt:
                best = pt
                best_dt = dt

        t, pos = best
        hover = (float(t), int(pos))
        if self._graph_hover_point != hover:
            self._graph_hover_point = hover
            self.redraw_graph()
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

        tip = self.graph_tooltip
        tip.update_idletasks()
        x = int(x_root + 12)
        y = int(y_root + 12)
        x, y = self._clamp_tooltip_in_host(self, tip, x, y)
        tip.geometry(f"+{x}+{y}")

    def hide_graph_tooltip(self) -> None:
        if self.graph_tooltip is not None and self.graph_tooltip.winfo_exists():
            try:
                self.graph_tooltip.destroy()
            except Exception:
                pass
        self.graph_tooltip = None
        if self._graph_hover_point is not None:
            self._graph_hover_point = None
            self.redraw_graph()

    def compute_alert(self, prev_pos: Optional[int], curr_pos: int) -> tuple[bool, str]:
        """Alert once per CSV threshold when crossing downward (e.g. first time at ≤10, then ≤5, …).

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

        sec_rem = self.estimate_seconds_remaining()
        eta_display = self.format_duration_remaining(sec_rem) if sec_rem is not None else "—"
        hist_extra = f"; est. remaining {eta_display}" if sec_rem is not None else ""
        self.write_history(f"Threshold alert: position {position} ({reason}){hist_extra}")

        if self.sound_enabled_var.get():
            self.play_sound()
        if self.popup_enabled_var.get():
            self.show_popup(position, eta_display)

    def play_sound(self) -> None:
        """Threshold / warning alert sound."""
        raw = (self.alert_sound_path_var.get() or "").strip()
        if raw:
            p = expand_path(raw)
            if p.is_file() and play_alert_sound_file(p):
                return
        if play_default_system_alert_sound():
            return
        try:
            self.bell()
        except Exception:
            pass

    def play_completion_sound(self) -> None:
        """Queue front (position ≤1) completion sound."""
        raw = (self.completion_sound_path_var.get() or "").strip()
        if raw:
            p = expand_path(raw)
            if p.is_file() and play_alert_sound_file(p):
                return
        if play_default_completion_system_sound():
            return
        try:
            self.bell()
        except Exception:
            pass

    def _maybe_notify_queue_completion(self, prev_pos: Optional[int], position: int) -> None:
        """Once per approach to queue front (≤1): optional sound/popup only — no configurable completion threshold."""
        if prev_pos is None or prev_pos <= 1:
            return
        if position > 1:
            return
        if self._queue_completion_notified_this_run:
            return
        now = time.time()
        if (
            self._last_queue_completion_notify_epoch > 0.0
            and (now - self._last_queue_completion_notify_epoch) < COMPLETION_NOTIFY_MIN_INTERVAL_SEC
        ):
            return

        want_sound = bool(self.completion_sound_enabled_var.get())
        want_popup = bool(self.completion_popup_enabled_var.get())
        if not want_sound and not want_popup:
            return

        self._queue_completion_notified_this_run = True
        self._last_queue_completion_notify_epoch = now
        self.write_history("Queue completion: reached front of queue (position ≤1).")
        if want_sound:
            self.play_completion_sound()
        if want_popup:
            self.show_completion_popup(position)

    def show_popup(self, position: int, eta_display: str) -> None:
        """Warning threshold popup: position + ETA only (details stay in the session log)."""
        if self.active_popup is not None and self.active_popup.winfo_exists():
            try:
                self.active_popup.destroy()
            except Exception:
                pass

        popup = tk.Toplevel(self)
        self.active_popup = popup
        popup.title(f"{ALERT_POPUP_EMOJI_THRESHOLD} Queue alert")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18, bg=UI_BG_CARD)

        try:
            popup.transient(self)
        except Exception:
            pass

        row = tk.Frame(popup, bg=UI_BG_CARD)
        row.pack(fill="x", pady=(0, 4))
        tk.Label(
            row,
            text=ALERT_POPUP_EMOJI_THRESHOLD,
            font=_alert_popup_emoji_font(42),
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
        ).pack(side="left", anchor="nw", padx=(0, 12))
        txt = tk.Frame(row, bg=UI_BG_CARD)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(
            txt,
            text=f"Position {position}",
            font=("TkDefaultFont", 15, "bold"),
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            txt,
            text=f"Est. left: {eta_display}",
            justify="left",
            wraplength=360,
            bg=UI_BG_CARD,
            fg=UI_ACCENT_REMAINING,
            font=("TkDefaultFont", 11, "bold"),
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

    def show_completion_popup(self, position: int) -> None:
        """Queue front — visually distinct from the threshold warning popup."""
        if self.active_completion_popup is not None and self.active_completion_popup.winfo_exists():
            try:
                self.active_completion_popup.destroy()
            except Exception:
                pass

        popup = tk.Toplevel(self)
        self.active_completion_popup = popup
        popup.title(f"{ALERT_POPUP_EMOJI_COMPLETION} Front of queue")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18, bg=UI_BG_CARD)

        try:
            popup.transient(self)
        except Exception:
            pass

        row = tk.Frame(popup, bg=UI_BG_CARD)
        row.pack(fill="x", pady=(0, 4))
        tk.Label(
            row,
            text=ALERT_POPUP_EMOJI_COMPLETION,
            font=_alert_popup_emoji_font(46),
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
        ).pack(side="left", anchor="nw", padx=(0, 12))
        txt = tk.Frame(row, bg=UI_BG_CARD)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(
            txt,
            text="Front of the queue",
            font=("TkDefaultFont", 15, "bold"),
            bg=UI_BG_CARD,
            fg=UI_ACCENT_STATUS,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            txt,
            text=f"Position {position}. Connect when the game assigns you.",
            justify="left",
            wraplength=360,
            bg=UI_BG_CARD,
            fg=UI_TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 12))
        ttk.Button(popup, text="Dismiss", command=popup.destroy).pack(anchor="e")

        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(40, screen_w - width - 50)
        y = max(40, screen_h - height - 140)
        popup.geometry(f"+{x}+{y}")

        popup.after(POPUP_COMPLETION_TIMEOUT_MS, lambda: popup.winfo_exists() and popup.destroy())

    def on_close(self) -> None:
        if self._about_win is not None:
            try:
                self._about_win.grab_release()
            except Exception:
                pass
            try:
                self._about_win.destroy()
            except Exception:
                pass
            self._about_win = None
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
        if self.active_popup is not None:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None
        if self.active_completion_popup is not None:
            try:
                self.active_completion_popup.destroy()
            except Exception:
                pass
            self.active_completion_popup = None
        self.persist_config()
        self.stop_monitoring()
        self.stop_timer()
        self.destroy()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VS Queue Monitor — Vintage Story queue monitor GUI")
    parser.add_argument(
        "--path",
        dest="path",
        default="",
        help="Initial Logs folder path (directory containing or under the client log; not a .log file path)",
    )
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
