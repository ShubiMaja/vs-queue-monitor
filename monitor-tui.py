#!/usr/bin/env python3
"""
Legacy entry: the Textual TUI was removed; this script starts the default web UI.

Use: ``python monitor.py`` (or this file for old shortcuts).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    print(
        "monitor-tui.py: Textual TUI removed — starting the web UI (python monitor.py).",
        file=sys.stderr,
    )
    root = Path(__file__).resolve().parent
    script = root / "monitor.py"
    argv = [sys.executable, str(script)]
    argv.extend(a for a in sys.argv[1:] if a not in ("--tui", "--text"))
    return int(subprocess.call(argv, env=os.environ.copy()))


if __name__ == "__main__":
    raise SystemExit(main())
