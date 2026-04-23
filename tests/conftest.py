"""Pytest fixtures: local Starlette app for Playwright."""

from __future__ import annotations

import os
import shutil
import socket
import threading
from pathlib import Path
from typing import Generator

import pytest
import uvicorn

# Chromium may not start with permission "default". Stub matches the web API: after
# requestPermission() resolves granted, Notification.permission reads as granted.
NOTIFICATION_STUB_DEFAULT_GRANT = """
(function () {
  function FakeNotification(title, opts) {
    this.title = title || "";
    this.body = opts && opts.body ? opts.body : "";
  }
  var perm = "default";
  Object.defineProperty(FakeNotification, "permission", {
    get: function () { return perm; },
    configurable: true
  });
  FakeNotification.requestPermission = function () {
    perm = "granted";
    return Promise.resolve("granted");
  };
  window.Notification = FakeNotification;
})();
"""

from vs_queue_monitor.engine import QueueMonitorEngine
from vs_queue_monitor.web.hooks_web import WebMonitorHooks
from vs_queue_monitor.web.server import _wait_for_tcp, create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def isolated_config_root() -> Generator[Path, None, None]:
    root = Path(".tmp-playwright-config")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    old_appdata = os.environ.get("APPDATA")
    old_xdg = os.environ.get("XDG_CONFIG_HOME")
    os.environ["APPDATA"] = str(root)
    os.environ["XDG_CONFIG_HOME"] = str(root)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
        if old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = old_appdata
        if old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = old_xdg


@pytest.fixture(scope="session")
def live_server_url(isolated_config_root: Path) -> Generator[str, None, None]:
    lock = threading.RLock()
    hooks = WebMonitorHooks(lock)
    engine = QueueMonitorEngine(hooks, initial_path="", auto_start=False)
    hooks.attach_engine(engine)
    app = create_app(engine, hooks, lock)
    port = _free_port()

    def run() -> None:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    thread = threading.Thread(target=run, daemon=True, name="vs-queue-monitor-test-uvicorn")
    thread.start()
    if not _wait_for_tcp("127.0.0.1", port, timeout_sec=30.0):
        pytest.fail("Test server did not start in time")

    yield f"http://127.0.0.1:{port}"


@pytest.fixture(scope="session")
def base_url(live_server_url: str) -> str:
    """Used by pytest-playwright for relative navigations and by our tests."""
    return live_server_url
