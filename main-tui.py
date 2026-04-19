#!/usr/bin/env python3
"""
Legacy entry: forwards to ``monitor-tui.py`` (which runs the web UI).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    script = root / "monitor-tui.py"
    argv = [sys.executable, str(script)]
    argv.extend(sys.argv[1:])
    return int(subprocess.call(argv, env=os.environ.copy()))


if __name__ == "__main__":
    raise SystemExit(main())
