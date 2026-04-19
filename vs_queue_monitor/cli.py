"""CLI entry: local web UI (Starlette + static client; optional embedded window)."""

from __future__ import annotations

import argparse


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="VS Queue Monitor — Vintage Story queue monitor (local web UI on 127.0.0.1)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Same as default: local web UI (embedded window when supported). Kept for scripts.",
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

    from .web import run_web_server

    return run_web_server(
        initial_path=args.path,
        auto_start=not args.no_start,
        port=args.web_port,
        open_external_browser=bool(args.web_browser),
    )
