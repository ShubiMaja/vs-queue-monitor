"""Local web UI (Starlette) — optional interface alongside Tk/TUI."""

from __future__ import annotations

from .server import run_web_server

__all__ = ["run_web_server"]
