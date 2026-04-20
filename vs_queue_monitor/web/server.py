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
import webbrowser
from pathlib import Path
from typing import Any, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from .. import APP_DISPLAY_NAME, VERSION
from ..core import get_config_path, parse_alert_thresholds, queue_sessions_for_log_tail
from ..engine import QueueMonitorEngine
from .hooks_web import WebMonitorHooks
from .theme import chrome_theme_css_vars, graph_theme_dict

_STATIC = Path(__file__).resolve().parent / "static"
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _package_install_parent() -> Path:
    """Directory containing the ``vs_queue_monitor`` package (project root or ``site-packages``)."""
    return _REPO_ROOT


def _windows_server_child_command(
    port: int,
    initial_path: str,
    auto_start: bool,
) -> tuple[list[str], str]:
    """Build ``argv`` and **cwd** for the uvicorn child so ``-m vs_queue_monitor`` resolves even when
    the parent process was started with an unrelated working directory (e.g. Win+R, Explorer).
    """
    parent = _package_install_parent()
    monitor_py = parent / "monitor.py"
    if monitor_py.is_file():
        cmd: list[str] = [
            sys.executable,
            str(monitor_py),
            "--vs-queue-monitor-server-only",
            "--web-port",
            str(port),
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "vs_queue_monitor",
            "--vs-queue-monitor-server-only",
            "--web-port",
            str(port),
        ]
    if initial_path:
        cmd.extend(["--path", initial_path])
    if not auto_start:
        cmd.append("--no-start")
    return cmd, str(parent)


def _popen_windows_server_console(cmd: list[str], cwd: str) -> subprocess.Popen:
    """Run ``cmd`` in a **new** console. On non-zero exit, ``pause`` so tracebacks stay readable."""
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    joined = subprocess.list2cmdline(cmd)
    # ``|| pause`` keeps the window open if Python exits with an error (e.g. ImportError). Clean
    # shutdown (Ctrl+C handled inside uvicorn) typically exits 0, so pause does not run.
    shell_line = f"{joined} || pause"
    return subprocess.Popen(
        ["cmd.exe", "/c", shell_line],
        cwd=cwd,
        creationflags=creationflags,
    )


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


def _webview_profile_dir() -> str:
    """Persistent WebView2 user data (permissions, like a browser profile)."""
    p = get_config_path().parent / "webview_profile"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return str(p)


def _pywebview_start_kwargs() -> dict[str, Any]:
    """Prefer Edge WebView2 on Windows so the page gets Chromium + Web Notifications API."""
    if sys.platform != "win32":
        return {}
    gui = _env_pref("VS_QUEUE_MONITOR_WEBVIEW_GUI", "VSQM_WEBVIEW_GUI", default="edgechromium").strip()
    kw: dict[str, Any] = {"private_mode": False}
    if gui:
        kw["gui"] = gui
    try:
        kw["storage_path"] = _webview_profile_dir()
    except Exception:
        pass
    return kw


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


def _queue_sessions_for_engine(engine: QueueMonitorEngine) -> list[dict[str, Any]]:
    path = engine.current_log_file
    if path is None or not path.is_file():
        return []
    try:
        return queue_sessions_for_log_tail(path)
    except Exception:
        return []


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
                [exe, f"--app={url}", f"--user-data-dir={user_data_dir}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(sys.platform != "win32"),
            )
        except Exception:
            continue
    return None


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


def _open_browser_and_block(url: str) -> None:
    """Open app window (--app mode if Chromium available, else default browser), then block.

    Blocks until Ctrl+C. On exit, terminates the spawned --app process if any.
    Closing the window without Ctrl+C leaves the server running (tray icon stays).
    """
    time.sleep(0.3)
    proc = _open_app_window(url)
    if proc is None:
        webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()


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
        "resolved_path": engine.resolved_path_var.get(),
        "source_path": engine.source_path_var.get(),
        "graph_points": pts,
        "current_point": cur,
        "graph_log_scale": bool(engine.graph_log_scale_var.get()),
        "graph_live_view": bool(engine.graph_live_view_var.get()),
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
        "tutorial_done": bool(engine.tutorial_done_var.get()),
        "last_log_growth_epoch": engine._last_log_growth_epoch,
        "history_tail": hooks.history_lines()[-400:],
        "pending_new_queue_session": engine._pending_new_queue_session,
        "completion_notify_seq": int(getattr(hooks, "_completion_notify_seq", 0)),
        "queue_sessions": _queue_sessions_for_engine(engine),
        "build_fingerprint": _build_fingerprint(),
    }


def _api_meta(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "config_path": str(get_config_path()),
            "version": VERSION,
            "build_fingerprint": _build_fingerprint(),
            "graph_theme": graph_theme_dict(),
            "chrome_theme": chrome_theme_css_vars(),
        }
    )


def _api_state(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    hooks: WebMonitorHooks = request.app.state.hooks
    lock: threading.RLock = request.app.state.lock
    with lock:
        snap = build_snapshot(engine, hooks)
    return JSONResponse(snap)


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
            if "tutorial_done" in body:
                engine.tutorial_done_var.set(bool(body["tutorial_done"]))
            engine.persist_config()
            # Match native folder browse: re-resolve the log and seed the graph so ``current_log_file``
            # and ``queue_sessions`` update (otherwise path is saved but monitoring never restarts).
            if "source_path" in body:
                engine._try_start_after_browse()
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True})


def _api_toggle(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    with lock:
        engine.toggle_monitoring()
    return JSONResponse({"ok": True})


def _api_reset(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    lock: threading.RLock = request.app.state.lock
    with lock:
        engine.reset_defaults()
    return JSONResponse({"ok": True})


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
    hooks.attach_engine(engine)
    if auto_start:
        hooks.schedule(300, engine.start_monitoring)

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))

    app = create_app(engine, hooks, lock)
    url = f"http://127.0.0.1:{p}/"
    return app, engine, hooks, lock, p, url


def create_app(engine: QueueMonitorEngine, hooks: WebMonitorHooks, lock: threading.RLock) -> Starlette:
    routes = [
        Route("/api/meta", _api_meta, methods=["GET"]),
        Route("/api/state", _api_state, methods=["GET"]),
        Route("/api/pick_path", _api_pick_path, methods=["POST"]),
        Route("/api/config", _api_config, methods=["POST"]),
        Route("/api/monitoring/toggle", _api_toggle, methods=["POST"]),
        Route("/api/reset_defaults", _api_reset, methods=["POST"]),
        Route("/api/new_queue", _api_new_queue, methods=["POST"]),
        Route("/api/clear_notification_permission", _api_clear_notification_permission, methods=["POST"]),
        WebSocketRoute("/ws", _ws_endpoint),
        Mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static"),
    ]
    app = Starlette(routes=routes)
    app.state.engine = engine
    app.state.hooks = hooks
    app.state.lock = lock
    return app


def run_web_server_process(
    initial_path: str = "",
    auto_start: bool = True,
    port: Optional[int] = None,
) -> int:
    """Foreground uvicorn only (used by the Windows server console subprocess)."""
    import uvicorn

    from .tray import start_tray

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))
    url = f"http://127.0.0.1:{p}/"
    if not _handle_port_conflict(p, url):
        return 0

    app, _engine, _hooks, _lock, p, url = _init_web_stack(initial_path, auto_start, port)
    print(
        "VS Queue Monitor — server (this window shows HTTP logs; Ctrl+C stops)\n"
        f"Listening on {url}\n",
        flush=True,
    )
    start_tray(url)
    try:
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="info")
    except KeyboardInterrupt:
        return 0
    return 0


def _run_windows_split_console_webview(
    initial_path: str,
    auto_start: bool,
    port: Optional[int],
    p: int,
    url: str,
) -> int:
    """Windows: separate CMD window runs uvicorn; this process runs only pywebview."""
    import webview

    logging.getLogger("webview").setLevel(logging.CRITICAL)

    cmd, child_cwd = _windows_server_child_command(p, initial_path, auto_start)

    try:
        proc = _popen_windows_server_console(cmd, child_cwd)
    except OSError as exc:
        print(f"Could not start server console process: {exc}", file=sys.stderr)
        return 1

    if not _wait_for_tcp("127.0.0.1", p):
        print("ERROR: Local web server did not become ready in time.", file=sys.stderr)
        early = proc.poll()
        if early is not None:
            print(
                f"The server subprocess exited immediately (code {early}). "
                "Check the other console window for ImportError or missing dependencies, "
                "or run: python monitor.py --vs-queue-monitor-server-only",
                file=sys.stderr,
            )
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        return 1

    print(
        "Opening embedded window — HTTP server logs are in the other console window (Ctrl+C there stops the server).",
        flush=True,
    )
    try:
        from .webview_win import schedule_webview2_notification_permission

        webview.create_window(APP_DISPLAY_NAME, url, width=1120, height=780)
        start_kw = _pywebview_start_kwargs()
        schedule_webview2_notification_permission()
        try:
            webview.start(**start_kw)
        except Exception as inner_exc:
            logging.getLogger(__name__).warning(
                "webview.start(%s) failed (%s); retrying with pywebview defaults",
                start_kw,
                inner_exc,
            )
            webview.start()
    except Exception:
        print(
            "Embedded window unavailable (install pythonnet or pywin32 for pywebview on Windows, "
            "or use a Python version with working wheels). Opening your default browser instead.\n"
            f"  {url}\n"
            "  Leave the server console window open while you use the app.",
            file=sys.stderr,
        )
        webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            if proc.poll() is None:
                proc.terminate()
        return 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


def run_web_server(
    initial_path: str = "",
    auto_start: bool = True,
    port: Optional[int] = None,
    *,
    open_external_browser: bool = False,
) -> int:
    """Serve the static web client on loopback.

    By default opens an **embedded** desktop window (pywebview) instead of a separate browser.
    Pass ``open_external_browser=True`` (CLI: ``--web-browser``) to restore the old behavior.

    On **Windows**, embedded mode uses a **second console** process for uvicorn (visible server
    logs) and this process runs only pywebview. Set ``VS_QUEUE_MONITOR_DISABLE_SPLIT_CONSOLE=1`` (legacy: ``VSQM_DISABLE_SPLIT_CONSOLE``) to use a
    single process (uvicorn thread + webview) instead.
    """
    import uvicorn

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))
    url = f"http://127.0.0.1:{p}/"

    if not _handle_port_conflict(p, url):
        return 0

    if open_external_browser:
        from .tray import start_tray

        app, _e, _h, _l, p2, url2 = _init_web_stack(initial_path, auto_start, port)
        p, url = p2, url2

        def _open() -> None:
            time.sleep(0.35)
            if not _open_app_window(url):
                webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()
        start_tray(url)
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="info")
        return 0

    _webview_ok = False
    try:
        import webview

        # pywebview probes Win32/pythonnet backends and can log long tracebacks; keep stderr quiet.
        logging.getLogger("webview").setLevel(logging.CRITICAL)

        # Require pywebview 4.x — earlier releases have an incompatible API.
        _wv_ver = getattr(webview, "version", None) or getattr(webview, "__version__", None) or ""
        if not _wv_ver:
            # 4.x exposes webview.version; fall back to importlib metadata.
            try:
                from importlib.metadata import version as _pkg_version
                _wv_ver = _pkg_version("pywebview")
            except Exception:
                pass
        _wv_major = int(str(_wv_ver).split(".")[0]) if _wv_ver else 0
        if _wv_major < 4:
            raise ImportError(
                f"pywebview {_wv_ver or '?'} is installed but version 4.4+ is required. "
                "Run:  pip install --upgrade 'pywebview>=4.4'"
            )
        _webview_ok = True
    except ImportError as _wv_err:
        from .tray import start_tray

        app, _e, _h, _l, p2, url2 = _init_web_stack(initial_path, auto_start, port)
        p, url = p2, url2
        print(
            f"Embedded web UI unavailable: {_wv_err}\n"
            f"Opening app window at {url}\n",
            file=sys.stderr,
        )
        start_tray(url)
        _wv_config = uvicorn.Config(app, host="127.0.0.1", port=p, log_level="info")
        _wv_server = uvicorn.Server(_wv_config)
        _app_proc: "subprocess.Popen[bytes] | None" = None

        def _open_delayed() -> None:
            nonlocal _app_proc
            time.sleep(0.35)
            _app_proc = _open_app_window(url)
            if _app_proc is None:
                webbrowser.open(url)

        threading.Thread(target=_open_delayed, daemon=True).start()
        try:
            _wv_server.run()
        finally:
            if _app_proc is not None and _app_proc.poll() is None:
                _app_proc.terminate()
        return 0

    if not _gui_display_available():
        app, _e, _h, _l, p2, url2 = _init_web_stack(initial_path, auto_start, port)
        p, url = p2, url2
        print(
            "No desktop display detected (headless or SSH without X11/Wayland). "
            "Skipping embedded window.\n"
            f"  Server: {url}\n"
            f"  Remote access: ssh -L {p}:127.0.0.1:{p} user@host  then open that URL in a browser.\n"
            "  Local browser on this machine: python monitor.py --web-browser",
            file=sys.stderr,
        )
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="info")
        return 0

    if (
        sys.platform == "win32"
        and _env_pref("VS_QUEUE_MONITOR_DISABLE_SPLIT_CONSOLE", "VSQM_DISABLE_SPLIT_CONSOLE").lower()
        not in ("1", "true", "yes", "y")
    ):
        return _run_windows_split_console_webview(initial_path, auto_start, port, p, url)

    from .tray import start_tray

    app, _engine, _hooks, _lock, p, url = _init_web_stack(initial_path, auto_start, port)

    def _serve() -> None:
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="info")

    th = threading.Thread(target=_serve, daemon=True, name="vs-queue-monitor-uvicorn")
    th.start()
    if not _wait_for_tcp("127.0.0.1", p):
        print("ERROR: Local web server did not become ready in time.", file=sys.stderr)
        return 1

    start_tray(url)
    try:
        from .webview_win import schedule_webview2_notification_permission

        webview.create_window(APP_DISPLAY_NAME, url, width=1120, height=780)
        start_kw = _pywebview_start_kwargs()
        schedule_webview2_notification_permission()
        try:
            webview.start(**start_kw)
        except Exception as inner_exc:
            logging.getLogger(__name__).warning(
                "webview.start(%s) failed (%s); retrying with pywebview defaults",
                start_kw,
                inner_exc,
            )
            webview.start()
    except Exception as exc:
        print(
            "Embedded window unavailable (install pythonnet or pywin32 for pywebview on Windows, "
            "or use a Python version with working wheels). Opening your default browser instead.\n"
            f"  {url}\n"
            "  Ctrl+C in this terminal stops the server.",
            file=sys.stderr,
        )
        _open_browser_and_block(url)
        return 0
    return 0
