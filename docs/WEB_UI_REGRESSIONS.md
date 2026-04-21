# Web UI Regression Notes

This note captures a few web-client behaviors that have already regressed once and should be treated as guardrails during future UI changes.

## Startup safety

The web UI must not fail hard just because one initializer or one DOM node is missing.

Rules:
- Startup hooks in `vs_queue_monitor/web/static/app.js` should fail soft.
- Element lookups must be guarded before assigning handlers or reading properties.
- New toolbar or settings controls must be optional at runtime so a stale cached HTML/JS pair does not blank the page.

Why:
- Browsers can briefly run a stale `app.js` or stale `index.html` after a change.
- A single unguarded `$("...").onclick = ...` can prevent the whole page from loading.

Current protection:
- `safeInit(...)` wraps major setup functions.
- Recent high-risk DOM bindings in `setupChrome()` and settings sync were made null-safe.

## Desktop notifications

Browser desktop notifications are fragile in Chrome and Edge and must be handled conservatively.

Rules:
- Use the plain `Notification` API path in the web client unless there is a proven reason to change it.
- Test/sample/example notifications must use unique `tag` values.
- When a repeated sample notification should still visibly re-alert, include `renotify: true`.
- Do not switch back to fixed tags like `vsqm-test` or `vsqm-setup-grant`; Chrome/Edge may collapse them and appear "broken".
- Header-toggle notification enable flow must request permission directly from the click path.

Why:
- Chrome/Edge can suppress banners for repeated notifications that reuse the same tag.
- Permission requests may fail or behave inconsistently if moved outside the direct user gesture path.

Related files:
- `vs_queue_monitor/web/static/app.js`
- `vs_queue_monitor/web/server.py` only for permission-reset support in embedded Chromium mode

## Graph settings contract

The graph now has two persisted modes:
- `graph_log_scale`: boolean, default `false` (`Linear`)
- `graph_time_mode`: `"relative"` or `"absolute"`, default `"relative"`

Rules:
- If UI labels or controls change, keep the backend contract stable unless there is a migration plan.
- Toolbar quick toggles and Settings modal must stay in sync with server state.
- Graph redraw should happen immediately after local state is updated.

Server requirements:
- `build_snapshot(...)` must include both fields.
- `/api/config` must accept and validate both fields.
- engine config snapshot and reset-defaults must include both fields.

## Graph overlay

The graph overlay should stay compact, readable, and non-redundant.

Rules:
- One metric per line.
- Use consistent language:
  - `Start pos`
  - `Current pos`
  - `Min pos`
  - `Max pos`
  - `Position delta`
  - `Duration`
  - `Average rate`
- Hide `Min pos` / `Max pos` when they add no information beyond `Start pos` / `Current pos`.
- Overlay code must fail soft and never break graph rendering.

Why:
- Overlay logic runs inside the canvas draw path; an exception there can make the graph appear broken.

## KPI fallback behavior

`Rate` and `Remaining` should show useful values as early as possible on reload.

Rules:
- If backend live estimates are still empty, the client may derive fallback values from graph history.
- Fallback ETA must tolerate `position` arriving as a display string and fall back to the last graph point when needed.
- If there is still not enough data, loading UI is acceptable, but it must be clearly visible.

## Before merging web UI changes

Quick manual checklist:
- Page still loads on a hard refresh.
- Page still loads in a new tab.
- Graph renders with and without data.
- Settings modal opens and values do not snap back while editing.
- Toolbar graph toggles work and persist.
- Header notification toggle still enables/disables browser notifications.
- `Send test notification` still shows a real banner in Chrome/Edge when permission is granted.

