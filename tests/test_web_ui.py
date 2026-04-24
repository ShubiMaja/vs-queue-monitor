"""Smoke tests: real browser against the local web UI."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Page, expect


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
        data=json.dumps({"source_path": str(log_dir)}),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()

    r = page.context.request.post(f"{base_url.rstrip('/')}/api/monitoring/toggle")
    assert r.ok, r.text()
    r = page.context.request.post(f"{base_url.rstrip('/')}/api/monitoring/toggle")
    assert r.ok, r.text()

    page.goto(base_url)
    opts = page.locator("#selSession option")
    expect(opts).to_have_count(1)
    expect(page.locator("#selSession")).to_have_value("latest")
    expect(opts.nth(0)).to_contain_text("Session 1")
