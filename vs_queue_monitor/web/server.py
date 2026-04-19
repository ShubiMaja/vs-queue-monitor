"""Local Starlette app: static SPA + REST + WebSocket state sync."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import webbrowser
from pathlib import Path
from typing import Any, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from .. import VERSION
from ..core import get_config_path, parse_alert_thresholds
from ..engine import QueueMonitorEngine
from .hooks_web import WebMonitorHooks

_STATIC = Path(__file__).resolve().parent / "static"


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
    }


def _api_meta(request: Request) -> JSONResponse:
    return JSONResponse({"config_path": str(get_config_path())})


def _api_state(request: Request) -> JSONResponse:
    engine: QueueMonitorEngine = request.app.state.engine
    hooks: WebMonitorHooks = request.app.state.hooks
    lock: threading.RLock = request.app.state.lock
    with lock:
        snap = build_snapshot(engine, hooks)
    return JSONResponse(snap)


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
        Route("/api/config", _api_config, methods=["POST"]),
        Route("/api/monitoring/toggle", _api_toggle, methods=["POST"]),
        Route("/api/reset_defaults", _api_reset, methods=["POST"]),
        WebSocketRoute("/ws", _ws_endpoint),
        Mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static"),
    ]
    app = Starlette(routes=routes)
    app.state.engine = engine
    app.state.hooks = hooks
    app.state.lock = lock
    return app


def run_web_server(initial_path: str = "", auto_start: bool = True, port: Optional[int] = None, open_browser: bool = True) -> int:
    lock = threading.RLock()
    hooks = WebMonitorHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path=initial_path, auto_start=False)
    hooks.attach_engine(engine)
    if auto_start:
        hooks.schedule(300, engine.start_monitoring)

    p = port or int(os.environ.get("VS_QUEUE_MONITOR_WEB_PORT", "8765"))

    app = create_app(engine, hooks, lock)

    if open_browser:

        def _open() -> None:
            import time

            time.sleep(0.35)
            webbrowser.open(f"http://127.0.0.1:{p}/")

        threading.Thread(target=_open, daemon=True).start()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=p, log_level="warning")
    return 0
