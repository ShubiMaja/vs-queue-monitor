# VS Queue Monitor — UI/UX parity (web UI)

This is the **product-level UI/UX spec** for VS Queue Monitor. The shipping UI is the **local web client** (embedded window or browser on `127.0.0.1`).

For implementation mapping (APIs, shortcuts, hooks), see [`UI-PARITY.md`](UI-PARITY.md).

## Goals

- **Same mental model** as the shared engine: state names, KPI meanings, graph semantics, alerts.
- **Parity of outcomes**: what the user can do and what they learn should match the engine contract.

## Shared concepts (definitions)

- **Logs folder**: directory containing client logs; engine resolves a specific log file within it.
- **Position**: connect queue position; `0` means “past queue wait” (post-queue detection).
- **Info pane**: details block (Last change, Last threshold alert, Resolved log path, Global rate).
- **History pane**: chronological log of events and (optionally) every position change.
- **Graph**: step chart over time of queue position; supports linear/log Y scale.

## Information architecture (web)

### Top bar

- **Start / Stop** monitoring
- **Logs folder** path (paste; Python reads the disk — nothing uploaded)
- **Notifications** (browser permission, localhost)
- **Tour**, **Help** (`?`), **Settings** (`⚙`)

### Main area

- **KPI strip**: Position, Status, Rate (rolling header), Warnings, Elapsed, Remaining, Progress
- **Queue graph** (canvas): step series, log/linear Y, live view, hover readout
- **Info** and **History** panes with matching compact column titles (uppercase, single-line), then grid + log (see `web/static/index.html`)

## Interaction spec (web)

- **Start/Stop**: button, **Space** (when not typing in a field).
- **Path**: change event persists via `POST /api/config`.
- **Settings**: modal; **o** opens; same persisted fields as `config.json`.
- **Graph**: **c** copies TSV; **Copy PNG** button; mouse move shows time · position.
- **History**: **v** copies session log text when not in a field.
- **Help**: **F1** opens paths / config location.

## Copy / wording (must match)

- **Graph**: “Queue graph” context in UI copy where used.
- **Completion**: “Past queue wait” semantics (position `0` aligns with post-queue detection).

## Acceptance checklist

- Top bar exposes path, Start/Stop, Help, Settings, optional Tour and Notifications.
- KPIs + graph reflect engine snapshot over WebSocket; alerts and sounds follow engine + settings.
- Info/History use the same labels as the engine’s user-facing strings where applicable.
