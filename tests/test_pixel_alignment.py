"""Pixel-ish UI alignment checks (DOM geometry).

Goal: Catch subtle regressions where buttons in the same visual row drift by 1–3px
because of font metrics, padding, line-height, or SVG sizing.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from playwright.sync_api import Page, expect


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0


def _rects(page: Page, selectors: list[str]) -> dict[str, Rect]:
    return page.evaluate(
        """(sels) => {
      const out = {};
      for (const sel of sels) {
        const el = document.querySelector(sel);
        if (!el) { out[sel] = null; continue; }
        const r = el.getBoundingClientRect();
        out[sel] = { x: r.x, y: r.y, w: r.width, h: r.height };
      }
      return out;
    }""",
        selectors,
    )


def assert_row_center_aligned(page: Page, selectors: list[str], tol_px: float = 1.0) -> None:
    rect_map = _rects(page, selectors)
    missing = [s for s, r in rect_map.items() if r is None]
    assert not missing, f"missing elements: {missing}"
    rects = {s: Rect(**rect_map[s]) for s in selectors}
    cys = [rects[s].cy for s in selectors]
    lo, hi = min(cys), max(cys)
    assert (hi - lo) <= tol_px, f"row misaligned by {(hi - lo):.2f}px (tol {tol_px}px): {dict(zip(selectors, cys))}"


def assert_centers_aligned_within_each_row(
    page: Page,
    selectors: list[str],
    *,
    row_merge_px: float = 6.0,
    tol_px: float = 1.25,
) -> None:
    """Allow wrapping: elements can be split into multiple rows; each row must be aligned."""
    rect_map = _rects(page, selectors)
    missing = [s for s, r in rect_map.items() if r is None]
    assert not missing, f"missing elements: {missing}"
    rects = {s: Rect(**rect_map[s]) for s in selectors}
    items = sorted(((s, rects[s].cy) for s in selectors), key=lambda t: t[1])
    rows: list[list[tuple[str, float]]] = []
    for s, cy in items:
        if not rows or abs(cy - rows[-1][0][1]) > row_merge_px:
            rows.append([(s, cy)])
        else:
            rows[-1].append((s, cy))
    for r in rows:
        cys = [cy for _, cy in r]
        lo, hi = min(cys), max(cys)
        assert (hi - lo) <= tol_px, f"row misaligned by {(hi - lo):.2f}px (tol {tol_px}px): {dict(r)}"


# Key viewports around the topbar breakpoint
_VPS: list[tuple[int, int, str]] = [
    (390, 820, "mobile"),
    (768, 900, "tablet"),
    (899, 900, "below_topbar_breakpoint"),
    (1100, 900, "desktop"),
]


@pytest.mark.parametrize("w,h,name", _VPS)
def test_topbar_action_buttons_share_row_alignment(page: Page, base_url: str, w: int, h: int, name: str) -> None:
    page.set_viewport_size({"width": w, "height": h})
    page.goto(base_url)
    expect(page.locator(".topbar")).to_be_visible()

    # On desktop (>=900) bell and actions are in one row. Below that, topbar stacks and
    # bell is intentionally on its own row. We still enforce alignment within each row.
    if w >= 900:
        assert_row_center_aligned(
            page,
            ["#btnNotify", "#btnTour", "#btnHelp", "#btnSettings", "#btnStartStop"],
            tol_px=1.25,
        )
    else:
        assert_row_center_aligned(page, ["#btnTour", "#btnHelp", "#btnSettings", "#btnStartStop"], tol_px=1.25)


@pytest.mark.parametrize("w,h,name", _VPS)
def test_graph_toolbar_buttons_align(page: Page, base_url: str, w: int, h: int, name: str) -> None:
    page.set_viewport_size({"width": w, "height": h})
    page.goto(base_url)
    expect(page.locator(".graph-toolbar")).to_be_visible()
    # Toolbar can wrap on narrow widths; alignment must hold within each row.
    assert_centers_aligned_within_each_row(
        page,
        ["#btnYScale", "#btnLive", "#btnCopyPng", "#btnCopyTsv"],
        row_merge_px=8.0,
        tol_px=1.25,
    )

