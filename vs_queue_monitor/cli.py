"""CLI entry: GUI vs terminal UI."""

from __future__ import annotations

import argparse
import os
import sys

from .gui import QueueMonitorApp


def _should_use_tui_auto() -> bool:
    """Prefer terminal UI when no GUI display is available (e.g. Unix headless)."""
    env = (os.environ.get("VS_QUEUE_MONITOR_UI") or "").strip().lower()
    if env in ("gui", "tk", "window", "windows"):
        return False
    if env in ("tui", "text", "terminal", "term"):
        return True
    if sys.platform == "win32":
        return False
    display = (os.environ.get("DISPLAY") or "").strip()
    if not display:
        return True
    return False


def run_gui(initial_path: str = "", auto_start: bool = True) -> int:
    app = QueueMonitorApp(initial_path=initial_path, auto_start=auto_start)
    app.mainloop()
    return 0


def run_tui(initial_path: str = "", auto_start: bool = True) -> int:
    from .tui import run_tui as _run_tui

    return _run_tui(initial_path=initial_path, auto_start=auto_start)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VS Queue Monitor — Vintage Story queue monitor (GUI or terminal UI)",
    )
    ui = parser.add_mutually_exclusive_group()
    ui.add_argument(
        "--gui",
        action="store_true",
        help="Force the graphical window (Tk). Default on Windows and when DISPLAY is set.",
    )
    ui.add_argument(
        "--tui",
        "--text",
        dest="tui",
        action="store_true",
        help="Force the terminal UI (Textual). Implied when no GUI display (e.g. headless Linux).",
    )
    ui.add_argument(
        "--web",
        action="store_true",
        help="Local web UI: embedded desktop window (pywebview) on 127.0.0.1; use --web-browser for your default external browser.",
    )
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
    parser.add_argument(
        "--web-port",
        type=int,
        default=None,
        metavar="PORT",
        help="TCP port for --web (default: 8765 or VS_QUEUE_MONITOR_WEB_PORT).",
    )
    parser.add_argument(
        "--web-browser",
        action="store_true",
        help="With --web: open the UI in your default external browser instead of an embedded window.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.web:
        from .web import run_web_server

        return run_web_server(
            initial_path=args.path,
            auto_start=not args.no_start,
            port=args.web_port,
            open_external_browser=bool(args.web_browser),
        )
    auto_tui = _should_use_tui_auto()
    use_tui = bool(args.tui) or (not args.gui and auto_tui)
    if use_tui:
        return run_tui(initial_path=args.path, auto_start=not args.no_start)
    return run_gui(initial_path=args.path, auto_start=not args.no_start)
