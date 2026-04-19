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
    gui = os.environ.get("VSQM_WEBVIEW_GUI", "edgechromium").strip()
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
    fp = os.environ.get("VSQM_BUILD_FINGERPRINT", "").strip()
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
    """Open default browser once, then block so the uvicorn daemon thread keeps running."""

    def _open() -> None:
        time.sleep(0.3)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
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


def create_app(engine: QueueMonitorEngine, hooks: WebMonitorHooks, lock: threading.RLock) -> Starlette:
    routes = [
        Route("/api/meta", _api_meta, methods=["GET"]),
        Route("/api/state", _api_state, methods=["GET"]),
        Route("/api/pick_path", _api_pick_path, methods=["POST"]),
        Route("/api/config", _api_config, methods=["POST"]),
        Route("/api/monitoring/toggle", _api_toggle, methods=["POST"]),
        Route("/api/reset_defaults", _api_reset, methods=["POST"]),
        Route("/api/new_queue", _api_new_queue, methods=["POST"]),
        WebSocketRoute("/ws", _ws_endpoint),
        Mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static"),
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

    By default opens an **embedded** desktop window (pywebview) instead of a separate browser.
    Pass ``open_external_browser=True`` (CLI: ``--web-browser``) to restore the old behavior.
    """
    import uvicorn

    lock = threading.RLock()
    hooks = WebMonitorHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path=initial_path, auto_start=False)
    hooks.attach_engine(engine)
    if auto_start:
        hooks.schedule(300, engine.start_monitoring)

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))

    app = create_app(engine, hooks, lock)
    url = f"http://127.0.0.1:{p}/"

    if open_external_browser:

        def _open() -> None:
            time.sleep(0.35)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="warning")
        return 0

    try:
        import webview

        # pywebview probes Win32/pythonnet backends and can log long tracebacks; keep stderr quiet.
        logging.getLogger("webview").setLevel(logging.CRITICAL)
    except ImportError:
        print(
            "Embedded web UI requires pywebview. Install:\n"
            "  pip install pywebview\n"
            "Or open your system browser instead:\n"
            "  python monitor.py --web-browser\n"
            f"Serving at {url} (Ctrl+C to stop).",
            file=sys.stderr,
        )
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="warning")
        return 0

    if not _gui_display_available():
        print(
            "No desktop display detected (headless or SSH without X11/Wayland). "
            "Skipping embedded window.\n"
            f"  Server: {url}\n"
            f"  Remote access: ssh -L {p}:127.0.0.1:{p} user@host  then open that URL in a browser.\n"
            "  Local browser on this machine: python monitor.py --web-browser",
            file=sys.stderr,
        )
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="warning")
        return 0

    def _serve() -> None:
        uvicorn.run(app, host="127.0.0.1", port=p, log_level="warning")

    th = threading.Thread(target=_serve, daemon=True, name="vsqm-uvicorn")
    th.start()
    if not _wait_for_tcp("127.0.0.1", p):
        print("ERROR: Local web server did not become ready in time.", file=sys.stderr)
        return 1

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
