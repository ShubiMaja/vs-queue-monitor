"""Local web UI (Starlette + static client)."""

from __future__ import annotations

from .server import run_web_server, run_web_server_process

__all__ = ["run_web_server", "run_web_server_process"]
