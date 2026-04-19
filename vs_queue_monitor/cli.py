"""CLI entry: default embedded web UI, optional Tk or Textual."""

from __future__ import annotations

import argparse

from .gui import QueueMonitorApp


def run_gui(initial_path: str = "", auto_start: bool = True) -> int:
    app = QueueMonitorApp(initial_path=initial_path, auto_start=auto_start)
    app.mainloop()
    return 0


def run_tui(initial_path: str = "", auto_start: bool = True) -> int:
    from .tui import run_tui as _run_tui

    return _run_tui(initial_path=initial_path, auto_start=auto_start)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VS Queue Monitor — Vintage Story queue monitor (default: embedded web UI on 127.0.0.1)",
    )
    ui = parser.add_mutually_exclusive_group()
    ui.add_argument(
        "--gui",
        action="store_true",
        help="Tk desktop window instead of the default embedded web UI.",
    )
    ui.add_argument(
        "--tui",
        "--text",
        dest="tui",
        action="store_true",
        help="Textual terminal UI instead of the default embedded web UI.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Same as default: local web UI (embedded window). Kept for scripts and clarity.",
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
        help="TCP port for the web UI (default: 8765 or VS_QUEUE_MONITOR_WEB_PORT).",
    )
    parser.add_argument(
        "--web-browser",
        action="store_true",
        help="Open the web UI in your default external browser instead of an embedded window.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.web and (args.gui or args.tui):
        parser.error("--web cannot be combined with --gui or --tui")
    if args.web_browser and (args.gui or args.tui):
        parser.error("--web-browser only applies to the default web UI (omit --gui and --tui)")

    if args.gui:
        return run_gui(initial_path=args.path, auto_start=not args.no_start)
    if args.tui:
        return run_tui(initial_path=args.path, auto_start=not args.no_start)

    from .web import run_web_server

    return run_web_server(
        initial_path=args.path,
        auto_start=not args.no_start,
        port=args.web_port,
        open_external_browser=bool(args.web_browser),
    )
