"""Smoke tests: real browser against the local web UI."""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_dashboard_loads(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.locator(".brand__title")).to_contain_text("VS Queue Monitor")
    # Visible label (path button uses aria-label from JS, so it is not named only "Log source")
    expect(page.locator("label[for='pathSummary']")).to_be_visible()
    expect(page.locator("#pathSummaryText")).to_be_visible()
    expect(page.locator("#btnStartStop")).to_be_visible()
