"""Smoke tests: real browser against the local web UI."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import Page, expect


def _wait_for_state(page: Page, base_url: str, predicate, timeout_sec: float = 15.0) -> dict:
    deadline = time.time() + timeout_sec
    last = None
    while time.time() < deadline:
        r = page.context.request.get(f"{base_url.rstrip('/')}/api/state")
        assert r.ok, r.text()
        last = r.json()
        if predicate(last):
            return last
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for expected state. Last state: {last}")


def _goto_fresh(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.evaluate(
        """async () => {
            if ('serviceWorker' in navigator) {
                const regs = await navigator.serviceWorker.getRegistrations();
                await Promise.all(regs.map((reg) => reg.unregister()));
            }
            if ('caches' in window) {
                const keys = await caches.keys();
                await Promise.all(keys.map((key) => caches.delete(key)));
            }
            localStorage.clear();
            sessionStorage.clear();
        }"""
    )
    page.goto(f"{base_url}?fresh=1")


def test_web_tests_use_isolated_config(page: Page, base_url: str) -> None:
    r = page.context.request.get(f"{base_url.rstrip('/')}/api/meta")
    assert r.ok, r.text()
    meta = r.json()
    assert ".tmp-playwright-config" in meta["config_path"]


def test_dashboard_loads(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.locator(".brand__title")).to_contain_text("VS Queue Monitor")
    # Label is hidden above 900px (wide layout collapses it); check the path input itself instead
    expect(page.locator("#pathSummaryText")).to_be_visible()
    expect(page.locator("#btnStartStop")).to_be_visible()
    expect(page.locator("#infoServer")).to_be_visible()


def test_server_target_renders_for_seeded_log(page: Page, base_url: str, tmp_path: Path) -> None:
    log_dir = tmp_path / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    filler = "9.4.2026 22:31:00 [Debug] filler " + ("x" * 240)
    lines = [
        "9.4.2026 22:30:53 [Notification] Connecting to gamma.example.net...",
        "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 12",
    ] + [filler for _ in range(700)] + [
        "9.4.2026 22:40:00 [Notification] Client is in connect queue at position: 11",
    ]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({"source_path": str(log_dir)}),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()

    page.goto(base_url)
    expect(page.locator("#infoServer")).to_have_text("gamma.example.net", timeout=15000)


def test_completed_latest_session_is_not_duplicated_in_dropdown(page: Page, base_url: str, tmp_path: Path) -> None:
    log_dir = tmp_path / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    lines = [
        "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
        "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 3",
        "9.4.2026 22:31:15 [Notification] Client is in connect queue at position: 2",
        "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 1",
        "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
    ]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({
            "source_path": str(log_dir),
            "history_path": str(tmp_path / "history"),
        }),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()

    r = page.context.request.post(f"{base_url.rstrip('/')}/api/monitoring/toggle")
    assert r.ok, r.text()
    _wait_for_state(
        page,
        base_url,
        lambda s: (
            s.get("source_path") == str(log_dir)
            and not s.get("running")
            and len(s.get("graph_points") or []) >= 1
        ),
    )

    _goto_fresh(page, base_url)
    page.wait_for_timeout(2500)
    opts = page.locator("#selSession option")
    expect(opts).to_have_count(1, timeout=15000)
    expect(page.locator("#selSession")).to_have_value("latest")
    expect(opts.nth(0)).to_contain_text("Session 1", timeout=15000)


def test_completed_running_session_is_not_duplicated_in_dropdown(page: Page, base_url: str, tmp_path: Path) -> None:
    log_dir = tmp_path / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    lines = [
        "9.4.2026 22:30:53 [Notification] Connecting to tops.vintagestory.at...",
        "9.4.2026 22:30:55 [Notification] Client is in connect queue at position: 3",
        "9.4.2026 22:31:15 [Notification] Client is in connect queue at position: 2",
        "9.4.2026 22:31:25 [Notification] Client is in connect queue at position: 1",
        "9.4.2026 22:31:26 [Notification] Connected to server, downloading data...",
    ]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({
            "source_path": str(log_dir),
            "history_path": str(tmp_path / "history"),
        }),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()
    _wait_for_state(
        page,
        base_url,
        lambda s: (
            s.get("source_path") == str(log_dir)
            and bool(s.get("running"))
            and len(s.get("graph_points") or []) >= 1
        ),
    )

    _goto_fresh(page, base_url)
    page.wait_for_timeout(2500)
    opts = page.locator("#selSession option")
    expect(opts).to_have_count(1, timeout=15000)
    expect(page.locator("#selSession")).to_have_value("latest")
    expect(opts.nth(0)).to_contain_text("Session 1", timeout=15000)


def test_history_session_id_collision_does_not_hide_unrelated_past_session(
    page: Page, base_url: str, tmp_path: Path
) -> None:
    log_dir = tmp_path / "VintagestoryData"
    log_dir.mkdir(parents=True)
    log_path = log_dir / "client-main.log"
    now = datetime.now().replace(microsecond=0)
    t0 = now - timedelta(seconds=25)
    t1 = now - timedelta(seconds=5)
    log_path.write_text(
        "\n".join(
            [
                f"{t0.day}.{t0.month}.{t0.year} {t0:%H:%M:%S} [Notification] Connecting to tops.vintagestory.at...",
                f"{t0.day}.{t0.month}.{t0.year} {t0:%H:%M:%S} [Notification] Client is in connect queue at position: 12",
                f"{t1.day}.{t1.month}.{t1.year} {t1:%H:%M:%S} [Notification] Client is in connect queue at position: 10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True)
    (history_dir / "session_history.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": 1,
                        "source_path": "D:/OldInstall/Logs",
                        "log_file": "D:/OldInstall/Logs/client-main.log",
                        "server": "alpha.example.net",
                        "start_epoch": 1775760000.0,
                        "end_epoch": 1775760060.0,
                        "outcome": "completed",
                        "start_position": 9,
                        "end_position": 0,
                        "points": [[1775760000.0, 9], [1775760030.0, 5], [1775760060.0, 0]],
                    }
                ),
                json.dumps(
                    {
                        "session_id": 2,
                        "source_path": "D:/OtherInstall/Logs",
                        "log_file": "D:/OtherInstall/Logs/client-main.log",
                        "server": "beta.example.net",
                        "start_epoch": 1775761000.0,
                        "end_epoch": 1775761090.0,
                        "outcome": "completed",
                        "start_position": 14,
                        "end_position": 0,
                        "points": [[1775761000.0, 14], [1775761050.0, 8], [1775761090.0, 0]],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({
            "source_path": str(log_dir),
            "history_path": str(history_dir),
        }),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()
    _wait_for_state(
        page,
        base_url,
        lambda s: (
            s.get("source_path") == str(log_dir)
            and bool(s.get("running"))
            and len(s.get("graph_points") or []) >= 1
        ),
    )

    _goto_fresh(page, base_url)
    page.wait_for_timeout(2500)
    opts = page.locator("#selSession option")
    expect(opts).to_have_count(3, timeout=15000)
    expect(opts.nth(0)).to_contain_text("Session 3", timeout=15000)
    expect(opts.nth(1)).to_contain_text("Session 2", timeout=15000)
    expect(opts.nth(2)).to_contain_text("Session 1", timeout=15000)
