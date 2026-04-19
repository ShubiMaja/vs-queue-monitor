"""Playwright checks for desktop notification UI (modal + bell, no hint span)."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from conftest import NOTIFICATION_STUB_DEFAULT_GRANT


def test_no_notify_hint_element_beside_bell(page: Page, base_url: str) -> None:
    """#notifyHint was removed — only the bell control should carry status (aria-label)."""
    page.goto(base_url)
    expect(page.locator("#notifyHint")).to_have_count(0)


def test_bell_opens_notification_permission_modal(page: Page, base_url: str) -> None:
    """Suppress auto modal, then bell opens the dialog (stub keeps permission at default)."""
    page.add_init_script(NOTIFICATION_STUB_DEFAULT_GRANT)
    page.add_init_script("try { sessionStorage.setItem('vsqm_notify_auto_shown', '1'); } catch (e) {}")
    page.goto(base_url)
    modal = page.locator("#modalNotifyPerm")
    expect(modal).to_be_hidden()
    page.locator("#btnNotify").click()
    expect(modal).to_be_visible(timeout=5000)
    expect(page.get_by_role("heading", name="Desktop notifications")).to_be_visible()
    expect(page.locator("#btnNotifyPermAllow")).to_be_visible()
    expect(page.locator("#btnNotifyPermLater")).to_be_visible()


def test_notification_modal_auto_offer_after_load(page: Page, base_url: str) -> None:
    """In-app dialog opens ~1.4s after load when permission is still default (stub)."""
    page.add_init_script(NOTIFICATION_STUB_DEFAULT_GRANT)
    page.goto(base_url)
    expect(page.locator("#modalNotifyPerm")).to_be_visible(timeout=6000)
