"""Playwright checks: notifications use the standard web API only (no custom modal)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from conftest import NOTIFICATION_STUB_DEFAULT_GRANT


def test_no_notify_hint_element_beside_bell(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.locator("#notifyHint")).to_have_count(0)


def test_no_custom_notification_modal_markup(page: Page, base_url: str) -> None:
    """Permission is via Notification.requestPermission() only — no extra dialog in the page."""
    page.goto(base_url)
    expect(page.locator("#modalNotifyPerm")).to_have_count(0)


def test_bell_triggers_standard_permission_flow(page: Page, base_url: str) -> None:
    """Stub keeps permission at default; bell click runs requestPermission → granted in tests."""
    page.add_init_script(NOTIFICATION_STUB_DEFAULT_GRANT)
    page.goto(base_url)
    page.locator("#btnNotify").click()
    expect(page.locator("#btnNotify")).to_have_attribute("data-state", "live", timeout=5000)
