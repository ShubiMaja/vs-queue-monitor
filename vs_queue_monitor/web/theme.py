"""Theme tokens from ``vs_queue_monitor.core`` for the static web client (parity with former Tk GUI)."""

from __future__ import annotations

from typing import Any

from .. import core as c


def graph_theme_dict() -> dict[str, Any]:
    """Numeric and hex constants used by ``graph_canvas.js`` (mirrors ``gui.redraw_graph``)."""
    return {
        "max_draw_points": c.MAX_DRAW_POINTS,
        "single_point_graph_span_sec": c.SINGLE_POINT_GRAPH_SPAN_SEC,
        "graph_log_gamma": c.GRAPH_LOG_GAMMA,
        "pad_left": c.GRAPH_CANVAS_PAD_LEFT,
        "pad_right": c.GRAPH_CANVAS_PAD_RIGHT,
        "pad_top": c.GRAPH_CANVAS_PAD_TOP,
        "pad_bottom": c.GRAPH_CANVAS_PAD_BOTTOM,
        "ui_graph_bg": c.UI_GRAPH_BG,
        "ui_graph_plot": c.UI_GRAPH_PLOT,
        "ui_graph_grid": c.UI_GRAPH_GRID,
        "ui_graph_axis": c.UI_GRAPH_AXIS,
        "ui_graph_text": c.UI_GRAPH_TEXT,
        "ui_graph_line": c.UI_GRAPH_LINE,
        "ui_graph_marker": c.UI_GRAPH_MARKER,
        "ui_graph_hover_cursor": c.UI_GRAPH_HOVER_CURSOR,
        "ui_graph_minor_tick": c.UI_GRAPH_MINOR_TICK,
        "ui_graph_empty": c.UI_GRAPH_EMPTY,
    }


def chrome_theme_css_vars() -> dict[str, str]:
    """Map CSS variable names to ``core`` palette (dashboard chrome)."""
    return {
        "--bg": c.UI_BG_APP,
        "--card": c.UI_BG_CARD,
        "--text": c.UI_TEXT_PRIMARY,
        "--muted": c.UI_TEXT_MUTED,
        "--accent": c.UI_ACCENT_POSITION,
        "--line": c.UI_SEPARATOR,
        "--plot": c.UI_GRAPH_BG,
        "--danger": c.UI_DANGER,
        "--graph-line": c.UI_GRAPH_LINE,
    }


if __name__ == "__main__":
    raise SystemExit(
        "Import as part of the package (e.g. python -c \"from vs_queue_monitor.web.theme import graph_theme_dict\")."
    )
