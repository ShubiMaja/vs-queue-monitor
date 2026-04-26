"""Pure helpers: parsing, config, log I/O (no UI)."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Union

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover
    winsound = None

QUEUE_RE = re.compile(
    r"(?:"
    r"client\s+is\s+in\s+connect\s+queue\s+at\s+position"
    r"|your\s+position\s+in\s+the\s+queue\s+is"
    r")\D*(\d+)",
    re.IGNORECASE,
)

CONNECTING_TO_TARGET_RE = re.compile(r"(?i)\bconnecting\s+to\s+(.+?)(?:\.\.\.|$)")


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
# Lines after the *last* "connect queue position" line in the tail that show we are **not** still
# waiting in the connect queue — e.g. connecting, loading mods, download, world load (not only
# fully "connected"). Patterns must not rely on queue_position_match — those are handled by scan
# order. The same phrase can appear before queue lines on a cold connect (README), so we only
# count matches in lines strictly after the final queue line in the buffer.
POST_QUEUE_PROGRESS_LINE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)loading\s+and\s+pre-starting\s+client\s*-?\s*side\s+mods"),
    re.compile(r"(?i)\bpre-starting\s+client\s*-?\s*side\s+mods\b"),
    re.compile(r"(?i)\bloading\s+client\s*-?\s*side\s+mods\b"),
    re.compile(r"(?i)connected\s+to\s+server.*download"),
    re.compile(r"(?i)\bdownloading\s+(?:data|assets|world|chunks|map|mod)\b"),
    re.compile(r"(?i)\b(?:world|game)\s+loaded\b"),
    re.compile(r"(?i)\bentering\s+(?:the\s+)?(?:world|game)\b"),
    re.compile(r"(?i)\bjoined\s+(?:the\s+)?(?:world|game|server)\b"),
    re.compile(r"(?i)\b(?:ok|okay),?\s+spawn"),
    re.compile(r"(?i)\bspawn(?:ed|ing)?\s+(?:at|in|near)\b"),
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

TAIL_BYTES = 128 * 1024

def get_default_vintagestory_path() -> Path:
    if sys.platform == "win32":
        base_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base_dir / "VintagestoryData"
DEFAULT_PATH = str(get_default_vintagestory_path())

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
# Canvas downsample cap (must be >= typical graph_points length so poll heartbeats are drawable).
MAX_DRAW_POINTS = MAX_GRAPH_POINTS
# When only one sample exists, map X across this span so axes and the marker are visible (not a sliver).
SINGLE_POINT_GRAPH_SPAN_SEC = 60.0
DEFAULT_PREDICTION_WINDOW_POINTS = 10
DEFAULT_ALERT_THRESHOLDS = "15, 10, 5, 3, 2, 1"
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
DEFAULT_FAILURE_WIN_MEDIA_NAME = "Windows Critical Stop.wav"
DEFAULT_ALERT_MAC_NAME = "Basso.aiff"
DEFAULT_COMPLETION_MAC_NAME = "Hero.aiff"
DEFAULT_FAILURE_MAC_NAME = "Sosumi.aiff"
DEFAULT_ALERT_LINUX_RELATIVE = "sounds/freedesktop/stereo/dialog-warning.oga"
DEFAULT_COMPLETION_LINUX_RELATIVE = "sounds/freedesktop/stereo/complete.oga"
DEFAULT_FAILURE_LINUX_RELATIVE = "sounds/freedesktop/stereo/dialog-error.oga"
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
UI_GRAPH_EMPTY = "#9fa7b3"
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
GRAPH_CANVAS_PAD_LEFT = 40
GRAPH_CANVAS_PAD_RIGHT = 30
GRAPH_CANVAS_PAD_TOP = 22
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
    """Comma-separated queue positions (default 10, 5, 1); each fires at most once per
    downward crossing until a new queue run (log boundary lines and/or large upward jump; see poll + compute_alert).

    Supports inclusive ranges like ``3-1`` or ``8-10`` (expanded to individual integers), matching the web client.
    """
    out: list[int] = []
    for part in raw.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            if a < 1 or b < 1:
                raise ValueError(f"Alert threshold must be >= 1 (got {part}).")
            step = 1 if a <= b else -1
            x = a
            while (step > 0 and x <= b) or (step < 0 and x >= b):
                out.append(x)
                x += step
            continue
        out.append(int(part))
    if not out:
        raise ValueError("Add at least one alert threshold (e.g. 10, 5, 1).")
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


def iter_default_failure_sound_paths() -> list[Path]:
    """Default failure/interrupted sound: one path per OS."""
    if sys.platform.startswith("win"):
        return [_windows_media_dir() / DEFAULT_FAILURE_WIN_MEDIA_NAME]
    if sys.platform == "darwin":
        return [MACOS_SYSTEM_SOUNDS_DIR / DEFAULT_FAILURE_MAC_NAME]
    if sys.platform.startswith("linux"):
        return _linux_sound_paths_from_relatives((DEFAULT_FAILURE_LINUX_RELATIVE,))
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


def default_failure_sound_path_for_display() -> str:
    """First existing default failure sound path for Settings, or empty string."""
    for p in iter_default_failure_sound_paths():
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


def play_default_failure_system_sound() -> bool:
    """Play OS default failure/interrupted tone."""
    if try_play_first_existing_sound(iter_default_failure_sound_paths()):
        return True

    if winsound is not None and sys.platform.startswith("win"):
        for alias in ("SystemHand", "SystemExclamation", "SystemDefault"):
            try:
                winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
                return True
            except Exception:
                continue
        try:
            winsound.MessageBeep(winsound.MB_ICONHAND)
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


def normalize_log_path_for_dedup(p: str) -> str:
    """Normalize a log file path so raw and token-masked variants compare equal."""
    if not p:
        return p
    for env_var, token in (("APPDATA", "%APPDATA%"), ("LOCALAPPDATA", "%LOCALAPPDATA%")):
        val = os.environ.get(env_var, "")
        if val:
            p = p.replace(token, val)
    try:
        home = str(Path.home())
        p = p.replace("$HOME", home)
    except Exception:
        pass
    if sys.platform == "win32":
        p = p.replace("/", "\\").lower()
    return p


def normalize_log_path_for_storage(p: str) -> str:
    """Replace raw user-path prefixes with portable tokens for JSONL storage.

    Inverse of ``normalize_log_path_for_dedup``: raw ``C:\\Users\\...`` becomes
    ``%APPDATA%\\...`` (or ``$HOME/...`` on non-Windows) so stored records are
    portable and don't accumulate multiple formats.
    """
    if not p:
        return p
    for env_var, token in (("APPDATA", "%APPDATA%"), ("LOCALAPPDATA", "%LOCALAPPDATA%")):
        val = os.environ.get(env_var, "")
        if val:
            # Case-insensitive on Windows; paths may have mixed casing.
            if sys.platform == "win32":
                if p.lower().startswith(val.lower()):
                    return token + p[len(val):]
            else:
                if p.startswith(val):
                    return token + p[len(val):]
    try:
        home = str(Path.home())
        if p.startswith(home):
            return "$HOME" + p[len(home):]
    except Exception:
        pass
    return p


def get_history_path() -> Path:
    """JSONL file that accumulates completed/interrupted session records."""
    return get_config_path().parent / "session_history.jsonl"


def get_checkpoint_path() -> Path:
    """Live session checkpoint — exists only while a session is in progress."""
    return get_config_path().parent / "current_session.json"


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
    """Resolve the Vintage Story **client** log from a **folder** path (or legacy saved file path → parent).

    Searches fixed paths and *client*.log-style names only — does not accept arbitrary *.log files.
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
        return None

    file_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return file_matches[0]


def expand_logs_folder_path(raw: str) -> Path:
    """Resolve the Logs folder field to an existing directory (legacy file path → parent)."""
    path = expand_path((raw or "").strip())
    if not path.exists():
        raise ValueError(
            "That path does not exist. Set Logs folder to your Vintage Story data directory "
            "(or the Logs folder inside it)."
        )
    if path.is_file():
        return path.parent
    if path.is_dir():
        return path
    raise ValueError("That path is not a usable folder.")


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


def queue_sessions_for_log_tail(
    log_file: Path,
    tail_bytes: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Group :func:`walk_queue_position_events` by queue run session id for the web session dropdown.

    Keys mirror the static ``feature/change-to-web-ui`` client (``t:<floor(first_epoch)>`` with ``#N`` on collisions).
    """
    if tail_bytes is None:
        tail_bytes = SEED_LOG_TAIL_BYTES
    text = read_log_file_tail_text(log_file, tail_bytes)
    if not text:
        return []
    by_sess: dict[int, list[tuple[float, int]]] = defaultdict(list)
    last_t: Optional[float] = None
    last_pos_by_sess: dict[int, Optional[int]] = {}
    completed_by_sess: dict[int, bool] = defaultdict(bool)
    saw_any = False
    for session, line, is_boundary in iter_session_log_lines(text):
        if is_boundary:
            continue
        m = queue_position_match(line)
        if m:
            try:
                pos = int(m.group(1))
            except Exception:
                continue
            if last_pos_by_sess.get(session) == pos:
                continue
            t = parse_log_timestamp_epoch(line)
            if t is None:
                t = (last_t + 1.0) if last_t is not None else time.time()
            last_t = t
            last_pos_by_sess[session] = pos
            by_sess[session].append((t, pos))
            saw_any = True
            continue
        if (
            is_post_queue_progress_line(line)
            and by_sess.get(session)
            and not completed_by_sess.get(session, False)
        ):
            last_pos = last_pos_by_sess.get(session)
            if last_pos is None or last_pos > 1:
                continue
            t = parse_log_timestamp_epoch(line)
            prev_t = by_sess[session][-1][0]
            if t is None:
                t = prev_t + 1.0
            if t <= prev_t:
                t = prev_t + 1e-3
            by_sess[session].append((t, 0))
            last_t = t
            last_pos_by_sess[session] = 0
            completed_by_sess[session] = True
            saw_any = True
    if not saw_any:
        return []
    sessions: list[dict[str, Any]] = []
    key_counts: dict[str, int] = {}
    for sess_id in sorted(by_sess.keys()):
        pts = sorted(by_sess[sess_id], key=lambda x: x[0])
        base = f"t:{int(math.floor(pts[0][0]))}" if pts else f"s:{sess_id}"
        seen = key_counts.get(base, 0)
        key_counts[base] = seen + 1
        key = base if seen == 0 else f"{base}#{seen + 1}"
        sessions.append(
            {
                "key": key,
                "session_id": sess_id,
                "label": "",
                "start_epoch": pts[0][0],
                "end_epoch": pts[-1][0],
                "start_pos": pts[0][1],
                "end_pos": pts[-1][1],
                "points": [[float(t), int(p)] for t, p in pts],
            }
        )
    for i, sess in enumerate(sessions):
        sess["label"] = f"Session {i + 1}"
    return sessions


def walk_queue_position_events(data: str) -> list[tuple[float, int, int]]:
    """Parse queue position events as (time, position, queue_run_session); sorted by time."""
    out: list[tuple[float, int, int]] = []
    last_t: Optional[float] = None
    last_pos: Optional[int] = None
    for session, line, is_boundary in iter_session_log_lines(data):
        if is_boundary:
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
    last_sess = 0
    for session, line, is_boundary in iter_session_log_lines(data):
        if is_boundary:
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


def iter_session_log_lines(data: str) -> Iterator[tuple[int, str, bool]]:
    """Yield stripped log lines with the current queue-session id and boundary flag."""
    session = 0
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        is_boundary = is_queue_run_boundary_line(line)
        if is_boundary:
            session += 1
        yield session, line, is_boundary


def parse_tail_latest_connect_target(data: str, session_id: Optional[int] = None) -> Optional[str]:
    """Latest ``Connecting to ...`` target in the tail, optionally scoped to one queue session."""
    latest_target: Optional[str] = None
    target_by_session: dict[int, str] = {}
    pending_target: Optional[str] = None
    for session, line, is_boundary in iter_session_log_lines(data):
        m = CONNECTING_TO_TARGET_RE.search(line)
        if m:
            target = m.group(1).strip().rstrip(".")
            if target:
                latest_target = target
                pending_target = target
        if is_boundary:
            continue
        if pending_target and queue_position_match(line):
            target_by_session.setdefault(session, pending_target)
    if session_id is None:
        return latest_target
    return target_by_session.get(session_id)


def count_queue_run_boundaries(data: str) -> int:
    return sum(1 for line in data.splitlines() if is_queue_run_boundary_line(line))


def parse_latest_session_boundary_epoch(data: str) -> Optional[float]:
    """Timestamp of the last queue-run boundary line (= when the newest session started)."""
    last_t: Optional[float] = None
    for _session, line, is_boundary in iter_session_log_lines(data):
        if is_boundary:
            t = parse_log_timestamp_epoch(line)
            if t is not None:
                last_t = t
    return last_t


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


def is_post_queue_progress_line(s: str) -> bool:
    """Non-queue log line that suggests we are past queue wait (connecting/loading — see module comment)."""
    s = s.strip()
    if not s or queue_position_match(s):
        return False
    for r in POST_QUEUE_PROGRESS_LINE_RES:
        if r.search(s):
            return True
    return False


def tail_has_post_queue_after_last_queue_line(data: str) -> bool:
    """True if a past-queue-wait pattern appears on any line strictly after the last queue line in *data*."""
    lines = data.splitlines()
    last_q = -1
    for i, line in enumerate(lines):
        if queue_position_match(line):
            last_q = i
    if last_q < 0:
        return False
    for line in lines[last_q + 1 :]:
        if is_post_queue_progress_line(line):
            return True
    return False


def completion_would_fire_for_tail(tail_text: str) -> bool:
    """True when the tail matches ``_maybe_notify_queue_completion`` (mapped position 0 + post-queue).

    Mirrors ``poll_once``: last queue reading ≤1 and a post-queue line after it ⇒ UI position 0.
    Used so we do not play completion popups/sounds on load for an already-finished queue.
    """
    if not tail_has_post_queue_after_last_queue_line(tail_text):
        return False
    raw, _ = parse_tail_last_queue_reading(tail_text)
    if raw is None:
        return False
    return raw <= 1


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


def first_position_at_or_before_front_epoch(segment: list[tuple[float, int]]) -> Optional[float]:
    """Earliest time in the segment where the log shows position ≤1 (at front or past-queue)."""
    for t, p in segment:
        if p <= 1:
            return t
    return None


def first_reconnecting_epoch_for_session(data: str, session_id: int) -> Optional[float]:
    """Earliest log timestamp for a reconnect-in-progress line in the given queue run session.

    Session counting matches ``walk_queue_position_events`` (increment on ``is_queue_run_boundary_line``).
    """
    if session_id < 0:
        return None
    session = 0
    for line in data.splitlines():
        s = line.strip()
        if not s:
            continue
        if is_queue_run_boundary_line(line):
            session += 1
            if session == session_id and is_reconnecting_line(s):
                t = parse_log_timestamp_epoch(line)
                if t is not None:
                    return t
            continue
        if session == session_id and is_reconnecting_line(s):
            t = parse_log_timestamp_epoch(line)
            if t is not None:
                return t
    return None


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
            Optional[float],
            Optional[float],
        ]
    ]:
    """Read and parse the log off the UI thread. Returns None if no queue segment was found.

    Second-to-last int: queue_run_session_id. Second int from end: authoritative queue position from
    the same tail parse as ``parse_tail_last_queue_reading`` (must match UI — segment last point
    alone can drift). Last two floats: first time position ≤1 in the segment, and first
    (re)connect line time for that session (both from log lines when present).
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
    # Map to position 0 if post-queue signal already in the tail (same logic as poll_once).
    if (
        authoritative_pos is not None
        and authoritative_pos <= 1
        and text
        and tail_has_post_queue_after_last_queue_line(text)
    ):
        authoritative_pos = 0

    segment_points = segment_tuples[-MAX_GRAPH_POINTS:]
    first_le_one_epoch = first_position_at_or_before_front_epoch(segment_tuples)
    connect_phase_started_epoch = (
        first_reconnecting_epoch_for_session(text, queue_run_session_id) if text else None
    )
    return (
        segment_points,
        len(segment_positions),
        len(positions),
        tail_bytes / (1024 * 1024),
        min(segment_positions),
        max(segment_positions),
        queue_run_session_id,
        authoritative_pos,
        first_le_one_epoch,
        connect_phase_started_epoch,
    )


def extract_all_session_records_from_log(
    log_file: Path,
    source_path: str = "",
    vsqm_version: str = "",
) -> list[dict]:
    """Extract one history record per completed historical queue session from the full log.

    The most recent session (currently active or just finished) is excluded — the engine
    handles that one via live monitoring.  Reads the whole file (capped at 100 MB).
    """
    try:
        file_size = log_file.stat().st_size
    except Exception:
        return []
    max_read = min(file_size, 100 * 1024 * 1024)
    try:
        with log_file.open("rb") as fh:
            fh.seek(max(0, file_size - max_read))
            raw = fh.read()
    except Exception:
        return []
    text = decode_log_bytes(raw)
    if not text.strip():
        return []

    events = walk_queue_position_events(text)
    if not events:
        return []

    # Group position events by session_id
    by_session: dict[int, list[tuple[float, int]]] = {}
    for t, pos, sess in events:
        by_session.setdefault(sess, []).append((t, pos))

    # Collect per-session log lines (for post-queue detection) and server targets
    lines_by_session: dict[int, list[str]] = {}
    targets: dict[int, str] = {}
    pending_target: Optional[str] = None
    for sess, line, is_boundary in iter_session_log_lines(text):
        lines_by_session.setdefault(sess, []).append(line)
        m = CONNECTING_TO_TARGET_RE.search(line)
        if m:
            pending_target = m.group(1).strip().rstrip(".")
        if not is_boundary and pending_target and queue_position_match(line):
            targets.setdefault(sess, pending_target)

    max_sess = max(by_session.keys())
    records: list[dict] = []

    for sess_id in sorted(by_session.keys()):
        if sess_id == max_sess:
            continue  # active session — handled by live monitoring

        pts = sorted(by_session[sess_id])
        if not pts:
            continue

        change_pts: list[tuple[float, int]] = []
        last_p: Optional[int] = None
        for t, p in pts:
            if p != last_p:
                change_pts.append((t, p))
                last_p = p

        start_epoch = pts[0][0]
        end_epoch = pts[-1][0]
        start_pos = pts[0][1]
        end_pos = pts[-1][1]

        sess_text = "\n".join(lines_by_session.get(sess_id, []))
        completed = end_pos <= 1 and tail_has_post_queue_after_last_queue_line(sess_text)
        if completed:
            end_pos = 0
            outcome = "completed"
        else:
            outcome = "unknown"

        records.append({
            "session_id": sess_id,
            "source_path": source_path,
            "log_file": str(log_file),
            "server": targets.get(sess_id),
            "start_epoch": start_epoch,
            "end_epoch": end_epoch,
            "outcome": outcome,
            "start_position": start_pos,
            "end_position": end_pos,
            "points": change_pts,
            "vsqm_version": vsqm_version,
        })

    return records


