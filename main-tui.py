#!/usr/bin/env python3
"""
Backward-compatible entry: same as ``python monitor-tui.py``.

Prefer: ``python monitor-tui.py`` (or ``python monitor.py --tui``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    script = root / "monitor-tui.py"
    argv = [sys.executable, str(script)]
    argv.extend(sys.argv[1:])
    return int(subprocess.call(argv))


if __name__ == "__main__":
    raise SystemExit(main())
