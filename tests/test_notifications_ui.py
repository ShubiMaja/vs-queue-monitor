"""Playwright checks: notifications use the standard web API only (no custom modal)."""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect

from conftest import NOTIFICATION_STUB_DEFAULT_GRANT


def _disable_tour(page: Page, base_url: str) -> None:
    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({"tutorial_done": True}),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()


def test_no_notify_hint_element_beside_bell(page: Page, base_url: str) -> None:
    _disable_tour(page, base_url)
    page.goto(base_url)
    expect(page.locator("#notifyHint")).to_have_count(0)


def test_no_custom_notification_modal_markup(page: Page, base_url: str) -> None:
    """Permission is via Notification.requestPermission() only — no extra dialog in the page."""
    _disable_tour(page, base_url)
    page.goto(base_url)
    expect(page.locator("#modalNotifyPerm")).to_have_count(0)


def test_bell_triggers_standard_permission_flow(page: Page, base_url: str) -> None:
    """Stub keeps permission at default; bell click runs requestPermission → granted in tests."""
    page.add_init_script(NOTIFICATION_STUB_DEFAULT_GRANT)
    _disable_tour(page, base_url)
    page.goto(base_url)
    page.locator("#btnNotify").click()
    expect(page.locator("#btnNotify")).to_have_attribute("data-state", "live", timeout=5000)


def test_completion_and_failure_test_notifications_follow_saved_settings(page: Page, base_url: str) -> None:
    page.add_init_script(
        """
        (function () {
          window.__notifications = [];
          function FakeNotification(title, opts) {
            window.__notifications.push({
              title: title || "",
              body: opts && opts.body ? opts.body : "",
              tag: opts && opts.tag ? opts.tag : "",
            });
          }
          FakeNotification.permission = "granted";
          FakeNotification.requestPermission = function () {
            return Promise.resolve("granted");
          };
          window.Notification = FakeNotification;
        })();
        """
    )
    _disable_tour(page, base_url)
    page.goto(base_url)

    page.locator("#btnSettings").click()
    expect(page.locator("#modalSettings")).not_to_have_class(r".*\bhidden\b.*")
    page.locator("#tabCompletion").click()
    page.locator("#chkCompPop").check()
    page.locator("#tabFailure").click()
    page.locator("#chkFailPop").check()
    page.locator("#btnSaveSettings").click()
    expect(page.locator("#modalSettings")).to_have_attribute("aria-hidden", "true")

    page.locator("#btnSettings").click()
    page.locator("#tabWarning").click()
    page.locator("#btnTestWarnNotify").click()
    page.locator("#tabCompletion").click()
    page.locator("#btnTestCompNotify").click()
    page.locator("#tabFailure").click()
    page.locator("#btnTestFailNotify").click()

    notifications = page.evaluate("window.__notifications")
    titles = [entry["title"] for entry in notifications]
    assert "Threshold alert" in titles
    assert "Queue completion" in titles
    assert "Queue interrupted" in titles
