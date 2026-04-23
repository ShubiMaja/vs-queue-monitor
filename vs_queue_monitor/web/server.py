"""Local Starlette app: static SPA + REST + WebSocket state sync."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from .. import GITHUB_REPO_URL, VERSION
from ..core import (
    SEED_LOG_TAIL_BYTES,
    expand_path,
    get_config_path,
    parse_alert_thresholds,
    parse_tail_last_queue_reading,
    queue_sessions_for_log_tail,
    read_log_file_tail_text,
)
from ..engine import QueueMonitorEngine
from .hooks_web import WebMonitorHooks
from .push import push_configured, push_status, register_subscription, send_push_to_all, subscription_count, vapid_public_key
from .theme import chrome_theme_css_vars, graph_theme_dict

_STATIC = Path(__file__).resolve().parent / "static"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_pref(primary: str, *legacy: str, default: str = "") -> str:
    """Read env var; prefer ``primary``, then legacy names (e.g. old ``VSQM_*``)."""
    v = os.environ.get(primary, "").strip()
    if v:
        return v
    for leg in legacy:
        v = os.environ.get(leg, "").strip()
        if v:
            return v
    return default


def _build_fingerprint() -> str:
    """Short git SHA, env override, or VERSION (parity with static ``feature/change-to-web-ui`` builds)."""
    fp = _env_pref("VS_QUEUE_MONITOR_BUILD_FINGERPRINT", "VSQM_BUILD_FINGERPRINT").strip()
    if fp:
        return fp
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if r.returncode == 0 and (r.stdout or "").strip():
            return (r.stdout or "").strip()
    except Exception:
        pass
    return VERSION


# Set by the launcher to tell the client what kind of window is hosting it.
# Values: "chromium_app" | "browser" | None (unknown/direct)
_window_mode: str | None = None


def _queue_sessions_for_engine(engine: QueueMonitorEngine) -> tuple[list[dict[str, Any]], int]:
    """Return (past_sessions, active_seed_session_id) using the SEED tail window for both.

    The engine's ``_last_queue_run_session`` is counted against the smaller TAIL_BYTES window
    and disagrees with the session IDs in the SEED window used by ``queue_sessions_for_log_tail``.
    Deriving the active ID directly from the SEED tail keeps all session IDs in the same
    coordinate space, preventing historical sessions from being incorrectly filtered and
    phantom sessions from leaking into the dropdown.
    """
    path = engine.current_log_file
    if path is None or not path.is_file():
        return [], -1
    try:
        tail_text = read_log_file_tail_text(path, SEED_LOG_TAIL_BYTES)
        sessions = queue_sessions_for_log_tail(path, SEED_LOG_TAIL_BYTES)
        seed_active_id = -1
        if tail_text and engine.running:
            _pos, seed_active_id = parse_tail_last_queue_reading(tail_text)
        if seed_active_id >= 0:
            sessions = [s for s in sessions if int(s.get("session_id", -1)) != seed_active_id]
        return sessions, seed_active_id
    except Exception:
        return [], -1


def _wait_for_tcp(host: str, port: int, timeout_sec: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.35):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _find_pid_on_port(port: int) -> Optional[int]:
    """Return the PID of the process listening on *port*, or None."""
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "TCP"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        return int(parts[-1])
        except Exception:
            pass
    else:
        for cmd in (
            ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
            ["fuser", f"{port}/tcp"],
        ):
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                pid_str = out.strip().split()[0]
                if pid_str.isdigit():
                    return int(pid_str)
            except Exception:
                continue
    return None


def _handle_port_conflict(p: int, url: str) -> bool:
    """If port *p* is already bound, prompt the user to kill the existing process.

    Returns True  → port is free; caller should proceed.
    Returns False → user declined or kill failed; caller should abort.
    """
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=0.3):
            pass
    except OSError:
        return True  # port is free

    pid = _find_pid_on_port(p)
    pid_hint = f" (PID {pid})" if pid else ""
    print(
        f"\nPort {p} is already in use{pid_hint}.\n"
        f"Another VS Queue Monitor instance may be running at {url}",
        file=sys.stderr,
    )

    if not sys.stdin.isatty():
        webbrowser.open(url)
        return False

    try:
        answer = input("Kill the existing instance and start fresh? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        return False

    if answer not in ("y", "yes"):
        print(f"  Tip: the running instance is at {url}", file=sys.stderr)
        webbrowser.open(url)
        return False

    if not pid:
        print("  Could not determine PID — close the other instance manually.", file=sys.stderr)
        return False

    try:
        if sys.platform == "win32":
            subprocess.call(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            import signal as _signal

            os.kill(pid, _signal.SIGKILL)
    except Exception as exc:
        print(f"  Could not terminate PID {pid}: {exc}", file=sys.stderr)
        return False

    # Wait for the port to be released (up to 5 s).
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", p), timeout=0.2):
                time.sleep(0.15)
        except OSError:
            print(f"  Stopped. Starting fresh on port {p}…", file=sys.stderr)
            return True

    print(f"  Port {p} still in use after termination.", file=sys.stderr)
    return False


def _gui_display_available() -> bool:
    """Whether a desktop/webview window can plausibly open (cross-platform)."""
    if sys.platform == "win32":
        return True
    if sys.platform == "darwin":
        return True
    if sys.platform.startswith("linux"):
        return bool(
            (os.environ.get("DISPLAY") or "").strip()
            or (os.environ.get("WAYLAND_DISPLAY") or "").strip()
        )
    return True


def _chromium_app_candidates() -> list[str]:
    """Paths to Chrome/Edge/Chromium executables to try for --app mode, best first."""
    if sys.platform == "win32":
        pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local = os.path.expandvars(r"%LOCALAPPDATA%")
        return [
            os.path.join(pf, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(local, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(pf, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
        ]
    if sys.platform == "darwin":
        return [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    # Linux / other
    return ["microsoft-edge", "google-chrome", "chromium-browser", "chromium"]


def _chromium_user_data_dir() -> str:
    """Dedicated Chromium profile dir so permissions persist independently of the user's browser."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    profile = base / "vs-queue-monitor" / "chromium-profile"
    profile.mkdir(parents=True, exist_ok=True)
    return str(profile)


def _open_app_window(url: str) -> "subprocess.Popen[bytes] | None":
    """Try to open *url* in a Chromium --app window (no address bar / tabs).

    Returns the launched Popen object so callers can monitor it, or None if no
    Chromium executable was found.
    """
    user_data_dir = _chromium_user_data_dir()
    for exe in _chromium_app_candidates():
        if sys.platform != "win32" and not os.path.isabs(exe):
            import shutil

            exe = shutil.which(exe) or ""  # type: ignore[assignment]
            if not exe:
                continue
        if not os.path.isfile(exe):
            continue
        try:
            return subprocess.Popen(
                [
                    exe,
                    f"--app={url}",
                    f"--user-data-dir={user_data_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-sync",
                    "--disable-extensions",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(sys.platform != "win32"),
            )
        except Exception:
            continue
    return None


def _find_chromium_exe() -> str | None:
    """Return the first available Chromium/Edge/Chrome executable path, or None."""
    import shutil

    for exe in _chromium_app_candidates():
        if os.path.isabs(exe):
            if os.path.isfile(exe):
                return exe
        else:
            found = shutil.which(exe)
            if found:
                return found
    return None


def _preconfigure_chromium_notification_permission(port: int) -> None:
    """Pre-grant the Web Notifications permission for localhost in the dedicated Chromium profile.

    Writing the allow entry before launching Chrome/Edge means Notification.permission is
    already "granted" when the page loads — no runtime prompt needed.

    We also delete "Secure Preferences" (Edge/Chrome's encrypted shadow copy) so the browser
    falls back to reading our plain Preferences file.  Without this, Edge ignores the plain
    file for security-sensitive settings such as notification permissions.
    """
    import json as _json
    import time as _time

    profile_dir = Path(_chromium_user_data_dir()) / "Default"
    prefs_path = profile_dir / "Preferences"
    try:
        profile_dir.mkdir(parents=True, exist_ok=True)
        # Remove the encrypted shadow so Edge/Chrome reads our plain Preferences.
        secure = profile_dir / "Secure Preferences"
        if secure.exists():
            secure.unlink()
        data: dict = {}
        if prefs_path.exists():
            try:
                data = _json.loads(prefs_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        profile = data.setdefault("profile", {})
        cs = profile.setdefault("content_settings", {})
        exc = cs.setdefault("exceptions", {})
        notif = exc.setdefault("notifications", {})
        ts = str(int(_time.time() * 1_000_000))
        for origin in (f"http://localhost:{port},*", f"http://127.0.0.1:{port},*"):
            notif[origin] = {"last_modified": ts, "setting": 1}  # 1 = ALLOW
        prefs_path.write_text(_json.dumps(data), encoding="utf-8")
    except Exception:
        pass  # best-effort


def _pick_path_sync(mode: str) -> str | None:
    """Native folder or file dialog (Tk). Run via ``asyncio.to_thread`` from the Starlette worker."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        if mode == "file":
            p = filedialog.askopenfilename(
                parent=root,
                title="Select Vintage Story client log",
                filetypes=[("Log files", "*.log"), ("All files", "*.*")],
            )
        else:
            p = filedialog.askdirectory(parent=root, mustexist=True)
        return str(p).strip() if p else None
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def _warnings_rows(engine: QueueMonitorEngine) -> list[dict[str, Any]]:
    try:
        thresholds = parse_alert_thresholds(engine.alert_thresholds_var.get())
    except ValueError:
        thresholds = []
    pos = engine.last_position
    if pos is None and engine.current_point is not None:
        pos = engine.current_point[1]
    fired = engine._alert_thresholds_fired
    out: list[dict[str, Any]] = []
    for t in thresholds:
        passed = pos is not None and pos <= t or t in fired
        out.append({"t": t, "passed": passed})
    return out


def build_snapshot(engine: QueueMonitorEngine, hooks: WebMonitorHooks) -> dict[str, Any]:
    pts = [[float(t), int(p)] for t, p in engine.graph_points]
    cur = None
    if engine.current_point is not None:
        ct, cp = engine.current_point
        cur = [float(ct), int(cp)]
    try:
        n = engine._rolling_window_points_int()
        rate_hdr = f"RATE (Rolling {n})"
    except Exception:
        rate_hdr = "RATE"
    queue_sessions, active_session_id = _queue_sessions_for_engine(engine)
    return {
        "version": VERSION,
        "running": engine.running,
        "interrupted_mode": engine._interrupted_mode,
        "position": engine.position_var.get(),
        "status": engine.status_var.get(),
        "rate_header": rate_hdr,
        "queue_rate": engine.queue_rate_var.get(),
        "global_rate": engine.global_rate_var.get(),
        "elapsed": engine.elapsed_var.get(),
        "remaining": engine.predicted_remaining_var.get(),
        "progress": float(getattr(engine, "_queue_progress_value", 0.0)),
        "last_change": engine.last_change_var.get(),
        "last_alert": engine.last_alert_var.get(),
        "last_alert_message": engine.last_alert_message_var.get(),
        "last_alert_seq": int(getattr(engine, "_last_alert_seq", 0)),
        "server_target": engine.server_target_var.get(),
        "resolved_path": engine.resolved_path_var.get(),
        "source_path": engine.source_path_var.get(),
        "graph_points": pts,
        "current_point": cur,
        "graph_log_scale": bool(engine.graph_log_scale_var.get()),
        "graph_live_view": bool(engine.graph_live_view_var.get()),
        "graph_time_mode": str(engine.graph_time_mode_var.get()),
        "poll_sec": engine.poll_sec_var.get(),
        "avg_window": engine.avg_window_var.get(),
        "alert_thresholds": engine.alert_thresholds_var.get(),
        "warnings": _warnings_rows(engine),
        "show_every_change": bool(engine.show_every_change_var.get()),
        "popup_enabled": bool(engine.popup_enabled_var.get()),
        "sound_enabled": bool(engine.sound_enabled_var.get()),
        "completion_popup": bool(engine.completion_popup_enabled_var.get()),
        "completion_sound": bool(engine.completion_sound_enabled_var.get()),
        "alert_sound_path": engine.alert_sound_path_var.get(),
        "completion_sound_path": engine.completion_sound_path_var.get(),
        "failure_popup": bool(engine.failure_popup_enabled_var.get()),
        "failure_sound": bool(engine.failure_sound_enabled_var.get()),
        "failure_sound_path": engine.failure_sound_path_var.get(),
        "tutorial_done": bool(engine.tutorial_done_var.get()),
        "last_log_growth_epoch": engine._last_log_growth_epoch,
        "history_tail": hooks.history_lines(400),
        "pending_new_queue_session": engine._pending_new_queue_session,
        "completion_notify_seq": int(getattr(hooks, "_completion_notify_seq", 0)),
        "failure_notify_seq": int(getattr(hooks, "_failure_notify_seq", 0)),
        "queue_sessions": queue_sessions,
        "active_queue_session_id": active_session_id,
        "build_fingerprint": _build_fingerprint(),
    }


def _api_meta(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "config_path": str(get_config_path()),
            "version": VERSION,
            "github_url": GITHUB_REPO_URL,
            "build_fingerprint": _build_fingerprint(),
            "graph_theme": graph_theme_dict(),
            "chrome_theme": chrome_theme_css_vars(),
            "window_mode": _window_mode,
            "push_status": push_status(),
        }
    )


def _api_state(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    hooks: WebMonitorHooks = request.app.state.hooks
    lock: threading.RLock = request.app.state.lock
    try:
        with lock:
            snap = build_snapshot(engine, hooks)
        return JSONResponse(snap)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


_BUNDLED_SOUNDS_DIR = Path(__file__).parent / "static" / "sounds"
_KIND_TO_ENGINE_VAR = {"warning": "alert_sound_path_var", "completion": "completion_sound_path_var", "failure": "failure_sound_path_var"}


def _effective_sound_path(engine: QueueMonitorEngine, kind: str) -> Path | None:
    var_name = _KIND_TO_ENGINE_VAR.get(kind)
    if var_name is None:
        return None
    raw = (getattr(engine, var_name).get() or "").strip()
    if raw:
        path = expand_path(raw)
        if path.is_file():
            return path
    bundled = _BUNDLED_SOUNDS_DIR / f"{kind}.wav"
    return bundled if bundled.is_file() else None


def _audio_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".ogg" or suffix == ".oga":
        return "audio/ogg"
    if suffix == ".aiff" or suffix == ".aif":
        return "audio/aiff"
    if suffix == ".m4a":
        return "audio/mp4"
    return "application/octet-stream"


def _api_sound(request: Request) -> Response:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    kind = str(request.path_params.get("kind", "")).strip().lower()
    with lock:
        path = _effective_sound_path(engine, kind)
    if path is None:
        return Response(status_code=404)
    return FileResponse(path, media_type=_audio_media_type(path), filename=path.name)


async def _api_sound_upload(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    kind = str(request.path_params.get("kind", "")).strip().lower()
    var_name = _KIND_TO_ENGINE_VAR.get(kind)
    if var_name is None:
        return JSONResponse({"ok": False, "error": "Unknown sound kind"}, status_code=400)
    try:
        filename = urllib.parse.unquote(str(request.headers.get("x-upload-filename", "")).strip())
        data = await request.body()
        if not data:
            return JSONResponse({"ok": False, "error": "No file provided"}, status_code=400)
        suffix = Path(filename or "sound.wav").suffix.lower() or ".wav"
        allowed = {".wav", ".mp3", ".ogg", ".oga", ".aiff", ".aif", ".m4a"}
        if suffix not in allowed:
            return JSONResponse({"ok": False, "error": f"Unsupported format: {suffix}"}, status_code=400)
        sounds_dir = get_config_path().parent / "sounds"
        sounds_dir.mkdir(parents=True, exist_ok=True)
        dest = sounds_dir / f"{kind}{suffix}"
        dest.write_bytes(data)
        with lock:
            getattr(engine, var_name).set(str(dest))
            engine.persist_config()
        snap = build_snapshot(engine, request.app.state.hooks)
    except Exception as exc:
        logging.getLogger(__name__).exception("sound upload failed")
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True, "path": str(dest), "state": snap})


async def _api_pick_path(request: Request) -> JSONResponse:
    """Open a native folder or file picker on the machine running Python (localhost UI)."""
    if not _gui_display_available():
        return JSONResponse(
            {
                "ok": False,
                "error": "No graphical display available for a native dialog (e.g. headless SSH). Paste the path instead.",
            },
            status_code=503,
        )
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return JSONResponse(
            {
                "ok": False,
                "error": "tkinter is not available (Python built without Tcl/Tk). Paste the path instead.",
            },
            status_code=503,
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    mode = str(body.get("mode", "folder")).strip().lower()
    if mode not in ("folder", "file"):
        return JSONResponse({"ok": False, "error": "mode must be 'folder' or 'file'"}, status_code=400)
    try:
        path = await asyncio.to_thread(_pick_path_sync, mode)
    except Exception as exc:
        logging.getLogger(__name__).exception("pick_path dialog failed")
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
    if not path:
        return JSONResponse({"ok": True, "path": None, "cancelled": True})
    return JSONResponse({"ok": True, "path": path, "cancelled": False})


async def _api_config(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    snap: dict[str, Any] | None = None
    try:
        with lock:
            if "source_path" in body:
                engine.source_path_var.set(str(body["source_path"]))
            if "poll_sec" in body:
                engine.poll_sec_var.set(str(body["poll_sec"]))
            if "avg_window" in body:
                engine.avg_window_var.set(str(body["avg_window"]))
            if "alert_thresholds" in body:
                parse_alert_thresholds(str(body["alert_thresholds"]))
                engine.alert_thresholds_var.set(str(body["alert_thresholds"]))
            if "graph_log_scale" in body:
                engine.graph_log_scale_var.set(bool(body["graph_log_scale"]))
            if "graph_live_view" in body:
                engine.graph_live_view_var.set(bool(body["graph_live_view"]))
            if "graph_time_mode" in body:
                mode = str(body["graph_time_mode"]).strip().lower()
                if mode not in ("relative", "absolute"):
                    raise ValueError("graph_time_mode must be 'relative' or 'absolute'")
                engine.graph_time_mode_var.set(mode)
            if "show_every_change" in body:
                engine.show_every_change_var.set(bool(body["show_every_change"]))
            if "popup_enabled" in body:
                engine.popup_enabled_var.set(bool(body["popup_enabled"]))
            if "sound_enabled" in body:
                engine.sound_enabled_var.set(bool(body["sound_enabled"]))
            if "completion_popup" in body:
                engine.completion_popup_enabled_var.set(bool(body["completion_popup"]))
            if "completion_sound" in body:
                engine.completion_sound_enabled_var.set(bool(body["completion_sound"]))
            if "alert_sound_path" in body:
                engine.alert_sound_path_var.set(str(body["alert_sound_path"]))
            if "completion_sound_path" in body:
                engine.completion_sound_path_var.set(str(body["completion_sound_path"]))
            if "failure_popup" in body:
                engine.failure_popup_enabled_var.set(bool(body["failure_popup"]))
            if "failure_sound" in body:
                engine.failure_sound_enabled_var.set(bool(body["failure_sound"]))
            if "failure_sound_path" in body:
                engine.failure_sound_path_var.set(str(body["failure_sound_path"]))
            if "tutorial_done" in body:
                engine.tutorial_done_var.set(bool(body["tutorial_done"]))
            engine.persist_config()
            # Match native folder browse: re-resolve the log and seed the graph so ``current_log_file``
            # and ``queue_sessions`` update (otherwise path is saved but monitoring never restarts).
            if "source_path" in body:
                engine._try_start_after_browse()
            snap = build_snapshot(engine, request.app.state.hooks)
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True, "state": snap})


def _api_toggle(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    try:
        with lock:
            engine.toggle_monitoring()
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


def _api_reset(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    try:
        with lock:
            engine.reset_defaults()
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


async def _api_new_queue(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    accept = bool(body.get("accept"))
    try:
        with lock:
            engine.resolve_new_queue_offer(accept)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True})


async def _api_clear_notification_permission(request: Request) -> JSONResponse:
    """Clear the localhost notification permission from the Chromium profile Preferences JSON.

    Only touches the notifications exception entry for the current origin so all
    other browser state (localStorage, cookies, zoom, etc.) is preserved.
    """
    import json as _json

    port = request.url.port or 8765
    prefs_path = Path(_chromium_user_data_dir()) / "Default" / "Preferences"
    if not prefs_path.exists():
        return JSONResponse({"ok": True, "note": "no profile yet"})
    try:
        # Also remove Secure Preferences so the browser falls back to reading our plain file.
        secure = prefs_path.parent / "Secure Preferences"
        if secure.exists():
            secure.unlink()
        data = _json.loads(prefs_path.read_text(encoding="utf-8"))
        notif = (
            data.get("profile", {})
            .get("content_settings", {})
            .get("exceptions", {})
            .get("notifications", {})
        )
        keys_removed = [k for k in list(notif) if f"localhost:{port}" in k or f"127.0.0.1:{port}" in k]
        for k in keys_removed:
            del notif[k]
        prefs_path.write_text(_json.dumps(data), encoding="utf-8")
        return JSONResponse({"ok": True, "cleared": keys_removed})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)



def _api_push_public_key(request: Request) -> JSONResponse:
    key = vapid_public_key()
    if not key:
        return JSONResponse({"ok": False, "error": "web push is not configured on the server"}, status_code=503)
    return JSONResponse({"ok": True, "public_key": key, "configured": push_configured(), "subscriptions": subscription_count()})


async def _api_push_subscribe(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "error": "object expected"}, status_code=400)
    subscription = body.get("subscription")
    if not isinstance(subscription, dict):
        return JSONResponse({"ok": False, "error": "subscription object expected"}, status_code=400)
    try:
        result = register_subscription(subscription, user_agent=request.headers.get("user-agent", ""))
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True, **result})


async def _api_push_test(request: Request) -> JSONResponse:
    payload = {
        "title": "VS Queue Monitor test",
        "body": "This test came from the backend web push pipeline.",
        "tag": f"vsqm-test-{int(time.time() * 1000)}",
        "kind": "warning",
        "renotify": True,
        "url": "/",
    }
    try:
        result = await asyncio.to_thread(send_push_to_all, payload)
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True, **result})


async def _ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    engine: QueueMonitorEngine = websocket.app.state.engine
    hooks: WebMonitorHooks = websocket.app.state.hooks
    lock: threading.RLock = websocket.app.state.lock
    try:
        while True:
            def snap() -> dict[str, Any]:
                with lock:
                    return build_snapshot(engine, hooks)

            payload = await asyncio.to_thread(snap)
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


def _init_web_stack(
    initial_path: str = "",
    auto_start: bool = True,
    port: Optional[int] = None,
) -> tuple[Starlette, QueueMonitorEngine, WebMonitorHooks, threading.RLock, int, str]:
    """Build engine + Starlette app; ``auto_start`` schedules monitoring like ``run_web_server``."""
    lock = threading.RLock()
    hooks = WebMonitorHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path=initial_path, auto_start=False)

    def _push_notify(_kind: str, payload: dict[str, Any]) -> None:
        if not push_configured():
            return
        def _worker() -> None:
            try:
                send_push_to_all(payload)
            except Exception:
                logging.getLogger(__name__).exception("web push send failed")
        threading.Thread(target=_worker, daemon=True).start()

    engine.push_notifier = _push_notify
    hooks.attach_engine(engine)
    if auto_start:
        hooks.schedule(300, engine.start_monitoring)

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))

    app = create_app(engine, hooks, lock)
    url = f"http://127.0.0.1:{p}/"
    return app, engine, hooks, lock, p, url


class _NoCacheStaticFiles(StaticFiles):
    """StaticFiles that always returns 200 so reloads never serve stale cached JS/CSS."""

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        # Strip conditional-request headers so StaticFiles never returns 304.
        # Without If-Modified-Since / If-None-Match the handler always serves the full file.
        if scope.get("type") == "http":
            scope = {
                **scope,
                "headers": [
                    (k, v)
                    for k, v in scope.get("headers", [])
                    if k.lower() not in (b"if-modified-since", b"if-none-match")
                ],
            }

        async def _send_no_cache(message: Any) -> None:
            if message["type"] == "http.response.start":
                hdrs = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() not in (b"cache-control", b"pragma", b"expires", b"etag", b"last-modified")
                ]
                hdrs.extend([
                    (b"cache-control", b"no-cache, no-store, must-revalidate"),
                    (b"pragma", b"no-cache"),
                    (b"expires", b"0"),
                ])
                message = {**message, "headers": hdrs}
            await send(message)

        await super().__call__(scope, receive, _send_no_cache)


def create_app(engine: QueueMonitorEngine, hooks: WebMonitorHooks, lock: threading.RLock) -> Starlette:
    routes = [
        Route("/api/meta", _api_meta, methods=["GET"]),
        Route("/api/state", _api_state, methods=["GET"]),
        Route("/api/sound/{kind:str}", _api_sound, methods=["GET"]),
        Route("/api/sound/{kind:str}/upload", _api_sound_upload, methods=["POST"]),
        Route("/api/pick_path", _api_pick_path, methods=["POST"]),
        Route("/api/config", _api_config, methods=["POST"]),
        Route("/api/monitoring/toggle", _api_toggle, methods=["POST"]),
        Route("/api/reset_defaults", _api_reset, methods=["POST"]),
        Route("/api/new_queue", _api_new_queue, methods=["POST"]),
        Route("/api/clear_notification_permission", _api_clear_notification_permission, methods=["POST"]),
        Route("/api/push/public_key", _api_push_public_key, methods=["GET"]),
        Route("/api/push/subscribe", _api_push_subscribe, methods=["POST"]),
        Route("/api/push/test", _api_push_test, methods=["POST"]),
        WebSocketRoute("/ws", _ws_endpoint),
        Mount("/", _NoCacheStaticFiles(directory=str(_STATIC), html=True), name="static"),
    ]
    app = Starlette(routes=routes)
    app.state.engine = engine
    app.state.hooks = hooks
    app.state.lock = lock
    return app


def run_web_server(
    initial_path: str = "",
    auto_start: bool = True,
    port: Optional[int] = None,
    *,
    open_external_browser: bool = False,
) -> int:
    """Serve the static web client on loopback.

    By default opens an embedded Chromium ``--app`` window (Edge or Chrome required).
    Pass ``open_external_browser=True`` (CLI: ``--web-browser``) to open in the default browser instead.
    On headless machines the server runs without a window; use the URL printed to stderr.
    """
    global _window_mode
    import uvicorn

    from .tray import start_tray

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))
    url = f"http://127.0.0.1:{p}/"

    if not _handle_port_conflict(p, url):
        return 0

    app, _e, _h, _l, p, url = _init_web_stack(initial_path, auto_start, port)
    _app_proc: "subprocess.Popen[bytes] | None" = None

    if open_external_browser:
        _window_mode = "browser"
        threading.Thread(
            target=lambda: (time.sleep(0.35), webbrowser.open(url)), daemon=True
        ).start()
    elif not _gui_display_available():
        print(
            "No desktop display detected (headless or SSH without X11/Wayland). "
            "Skipping embedded window.\n"
            f"  Server: {url}\n"
            f"  Remote access: ssh -L {p}:127.0.0.1:{p} user@host  then open that URL in a browser.\n"
            "  Local browser on this machine: python monitor.py --web-browser",
            file=sys.stderr,
        )
    else:
        _chromium_exe = _find_chromium_exe()
        if _chromium_exe:
            _window_mode = "chromium_app"
            _preconfigure_chromium_notification_permission(p)

            def _open_app() -> None:
                nonlocal _app_proc
                time.sleep(0.35)
                _app_proc = _open_app_window(url)
                if _app_proc is None:
                    webbrowser.open(url)

            threading.Thread(target=_open_app, daemon=True).start()
        else:
            _window_mode = "browser"
            threading.Thread(
                target=lambda: (time.sleep(0.35), webbrowser.open(url)), daemon=True
            ).start()

    start_tray(url)
    _log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s %(levelprefix)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "use_colors": None,
            },
        },
        "handlers": {
            "default": {"formatter": "default", "class": "logging.StreamHandler", "stream": "ext://sys.stderr"},
            "access": {"formatter": "access", "class": "logging.StreamHandler", "stream": "ext://sys.stdout"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }
    _wv_server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=p, log_level="info", log_config=_log_config))
    try:
        _wv_server.run()
    finally:
        if _app_proc is not None and _app_proc.poll() is None:
            _app_proc.terminate()
    return 0
