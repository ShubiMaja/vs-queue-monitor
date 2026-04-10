#!/usr/bin/env python3
"""
VS Queue Monitor — Vintage Story client log queue monitor (project id: vs-queue-monitor).
Version: 1.0.66

Cross-platform Tkinter app that watches a Vintage Story client log for queue
position changes and raises configurable threshold alerts (popup + sound).

This file is a thin entrypoint; implementation lives in the ``vs_queue_monitor`` package.

WARNING — WORK IN PROGRESS: Behavior, UI, and saved settings may change without notice.

WARNING — AI-ASSISTED DEVELOPMENT: Much of this codebase was produced or refactored with
AI / coding assistants. Treat paths, alerts, ETAs, and log interpretation as unverified
until you confirm them against your client and logs.

WARNING — NO WARRANTY: Not affiliated with Vintage Story. Use at your own risk.
"""

from vs_queue_monitor.cli import main

# Re-export for tests and ``import monitor`` compatibility
from vs_queue_monitor import APP_DISPLAY_NAME, GITHUB_REPO_URL, VERSION  # noqa: E402
from vs_queue_monitor.gui import QueueMonitorApp  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
