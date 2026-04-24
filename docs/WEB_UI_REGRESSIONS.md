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
- Each alert type must keep its own visual identity:
  - warning uses the warning icon and includes estimated remaining time when available
  - completion uses the completion icon and makes it explicit that queue wait is over
  - failure uses the failure icon and explains that monitoring is still watching the log
- Keep notification bodies structured and scan-friendly with one fact per line instead of a loose paragraph.
- Test buttons in Settings should mirror the real alert type they belong to.

Why:
- Chrome/Edge can suppress banners for repeated notifications that reuse the same tag.
- Permission requests may fail or behave inconsistently if moved outside the direct user gesture path.

Related files:
- `vs_queue_monitor/web/static/app.js`
- `vs_queue_monitor/web/server.py` only for permission-reset support in embedded Chromium mode

## Alert settings parity

Warning, Completion, and Failure settings should behave like one family of controls.

Rules:
- Keep all three tabs structurally aligned: popup toggle, inline test action, sound toggle, and sound-file field.
- `Failure popup` defaults to on, the same way Warning and Completion popups do.
- Sound-file inputs should provide an embedded file-picker button on the right instead of forcing manual path entry.
- Avoid reintroducing one-off controls that exist in only one alert tab unless the product explicitly calls for it.

Why:
- These tabs drifted repeatedly and confused users about which alert types actually support popup, sound, and testing.

## Tutorial overlay

The guided tour must own scrolling while it is open.

Rules:
- Opening the tutorial should lock background page scrolling.
- The tour card must stay clamped within the visible viewport.
- If the card content is taller than the viewport, the card itself should scroll instead of the page behind it.
- Reposition logic should use the card's actual rendered size, not a hard-coded height guess.

Why:
- Background-only scrolling makes the tour feel broken and can hide the `Next` button off-screen.

Related files:
- `vs_queue_monitor/web/static/app.js`
- `vs_queue_monitor/web/static/styles.css`

## Help and tour copy parity

Help text and guided tour copy must describe the controls that are actually on screen.

Rules:
- Update the Help modal and guided tour when button labels, icons, or placement change.
- Do not let Help or the tour reference removed controls, old button names, or outdated settings locations.
- When a compact icon-only control is introduced, keep its purpose discoverable through Help, the tour, `title`, and `aria-label`.

Why:
- Onboarding text is part of the product surface. Stale copy makes the UI feel broken even when the code works.

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
  - `Pos Change`
  - `Duration`
  - `Rate`
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

## Recent UI decisions from this thread

These are intentional UX choices, not accidents. Do not casually undo them.

- The graph toolbar uses compact controls:
  - `Live` is an icon-only lightning toggle.
  - History copy is icon-only.
  - History settings live behind the small gear popover.
- Turning `Live` on should switch graph scope back to `Latest session (auto)`.
- Settings should not duplicate graph toolbar controls like time mode or scale mode.
- Alert tabs should stay parallel in structure and wording.
- History should fill available desktop height and become internally scrollable instead of leaving blank space or growing forever.
- Info stats should pack upward instead of spacing themselves out vertically.
- `Cur Pos` is the preferred wording over `End Pos`.
- Warning threshold editors must accept and preserve CSV plus range forms like `10, 5, 1` and `8-10`.
- Warning threshold hints should be visible near the editor so the accepted format is discoverable.
- The graph overlay should use one metric per line and avoid redundant `Min/Max` rows when they repeat `Start/Current`.
- Commit coherent feature changes instead of letting multiple UI fixes pile up uncommitted.
