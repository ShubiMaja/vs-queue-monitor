"""Layout and design checks: overflow, viewports, IA from UI-UX-PARITY."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Narrow phone, tablet, just below / above CSS topbar breakpoint (900px), desktop
_VIEWPORTS: list[tuple[int, int, str]] = [
    (390, 820, "mobile"),
    (768, 900, "tablet"),
    (899, 900, "below_topbar_breakpoint"),
    (1100, 900, "desktop"),
]


def _doc_horizontal_overflow_px(page: Page) -> float:
    return page.evaluate(
        """() => {
      const d = document.documentElement;
      return d.scrollWidth - d.clientWidth;
    }""",
    )


def _el_horizontal_overflow_px(page: Page, selector: str) -> float | None:
    return page.evaluate(
        """(sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      return el.scrollWidth - el.clientWidth;
    }""",
        selector,
    )


def assert_no_horizontal_overflow(page: Page, tol: float = 2.0) -> None:
    """Body/document should not scroll horizontally (within tolerance)."""
    px = _doc_horizontal_overflow_px(page)
    assert px <= tol, f"document horizontal overflow {px}px (expected <= {tol})"


@pytest.mark.parametrize("width,height,name", _VIEWPORTS)
def test_dashboard_no_horizontal_overflow(
    page: Page,
    base_url: str,
    width: int,
    height: int,
    name: str,
) -> None:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(base_url)
    expect(page.locator(".topbar")).to_be_visible()
    assert_no_horizontal_overflow(page)
    # Top bar path row should not spill past the viewport
    tb = _el_horizontal_overflow_px(page, ".topbar")
    assert tb is not None
    assert tb <= 2.0, f".topbar overflow {tb}px at {name} {width}x{height}"


@pytest.mark.parametrize("width,height,name", _VIEWPORTS)
def test_ia_structure_visible(
    page: Page,
    base_url: str,
    width: int,
    height: int,
    name: str,
) -> None:
    """Top bar, KPI strip, graph, Info / History (per UI-UX-PARITY)."""
    page.set_viewport_size({"width": width, "height": height})
    page.goto(base_url)
    expect(page.locator("#btnStartStop")).to_be_visible()
    expect(page.locator("#btnNotify")).to_be_visible()
    expect(page.locator("#secKpi")).to_be_visible()
    expect(page.locator(".kpi__label", has_text="POSITION")).to_be_visible()
    expect(page.locator(".kpi__label", has_text="STATUS")).to_be_visible()
    expect(page.locator("#kpiRateHdr")).to_contain_text("RATE")
    expect(page.locator(".kpi__label", has_text="WARNINGS")).to_be_visible()
    expect(page.locator(".kpi__label", has_text="ELAPSED")).to_be_visible()
    expect(page.locator(".kpi__label", has_text="REMAINING")).to_be_visible()
    expect(page.locator(".kpi__label", has_text="PROGRESS")).to_be_visible()
    expect(page.locator("#graphCanvas")).to_be_visible()
    expect(page.locator(".info-history__title", has_text="Info")).to_be_visible()
    expect(page.locator(".info-history__title", has_text="History")).to_be_visible()


def test_long_source_path_does_not_break_layout(page: Page, base_url: str) -> None:
    """Stress: very long folder + filename; summary truncates, layout stays within width."""
    long_path = (
        "C:\\Users\\Someone\\AppData\\Roaming\\"
        + ("VeryLongFolderName\\" * 12)
        + ("x" * 90)
        + ".log"
    )
    r = page.context.request.post(
        f"{base_url.rstrip('/')}/api/config",
        data=json.dumps({"source_path": long_path}),
        headers={"Content-Type": "application/json"},
    )
    assert r.ok, r.text()
    page.set_viewport_size({"width": 390, "height": 900})
    page.goto(base_url)
    expect(page.locator("#pathSummaryText")).not_to_have_text("Not set", timeout=15000)
    assert_no_horizontal_overflow(page)
    path_overflow = _el_horizontal_overflow_px(page, "#pathSummary")
    assert path_overflow is not None
    assert path_overflow <= 2.0, f"path summary button overflow {path_overflow}px"


def test_optional_full_page_screenshots(
    page: Page,
    base_url: str,
    tmp_path: Path,
) -> None:
    """Set VSQM_PLAYWRIGHT_SCREENSHOTS=1 to write PNGs under test-results/ for manual review."""
    if os.environ.get("VSQM_PLAYWRIGHT_SCREENSHOTS", "").strip() not in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("Set VSQM_PLAYWRIGHT_SCREENSHOTS=1 to capture screenshots")
    # Stable path so the agent/user can review artifacts after the run.
    # pytest tmp_path is great for CI, but hard to locate in interactive work.
    out_dir = Path("test-results") / "ui-shots"
    out_dir.mkdir(parents=True, exist_ok=True)
    for width, height, name in _VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.goto(base_url)
        assert_no_horizontal_overflow(page)
        page.screenshot(
            path=str(out_dir / f"dashboard-{name}-{width}x{height}.png"),
            full_page=True,
        )
        # Key panels for quick visual diffing.
        page.locator(".topbar").screenshot(path=str(out_dir / f"topbar-{name}-{width}.png"))
        page.locator("#secKpi").screenshot(path=str(out_dir / f"kpi-{name}-{width}.png"))
        page.locator(".graph-panel").screenshot(path=str(out_dir / f"graph-{name}-{width}.png"))
