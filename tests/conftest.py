"""Pytest fixtures: local Starlette app for Playwright."""

from __future__ import annotations

import socket
import threading
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
def live_server_url() -> Generator[str, None, None]:
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
