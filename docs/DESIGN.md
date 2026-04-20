# VS Queue Monitor — product & UX design

This is the **design contract** for VS Queue Monitor: product intent, UX principles, information architecture, journeys, and feature-level decisions. It is intentionally **lossless**: it preserves the full set of decisions captured from prompts, but rewrites the document into a maintainable format.

**Scope.** The shipping product is a **Python** application with a **local web UI** (Starlette on loopback + static client), sharing one engine (`vs_queue_monitor/engine.py`). Exact implementation details (storage keys, parsing edge cases, build steps) live in source and in [`README.md`](../README.md).

---

## 1. Product definition

### 1.1 One-line product

A **local-first** assistant that reads the Vintage Story **client log** and turns it into a **glanceable dashboard**: queue position, movement over time, rough wait estimates, and optional alerts — **without uploading logs** or requiring a network service.

### 1.2 Problem statement

When connecting to a busy server, players often wait in a **connect queue**. The client log contains position updates, but users don’t get a single surface that reliably communicates:

- **Where am I** (position)?
- **Is it moving** (trend/rate)?
- **How long have I waited** and **roughly how much longer**?
- **When am I actually done waiting** (not merely “at 1”)?

### 1.3 Solution (what we provide)

A local web UI that:

- **Tails** the resolved client log and derives queue KPIs (position, elapsed, ETA, progress).
- Visualizes the **current run** as a **time series** (step chart in the web client).
- Fires optional **threshold** and **completion** alerts (in-app messages, sound, OS notifications where enabled).
- Uses **native folder/file access** (browse dialog, `--path`, environment) so users can point at Vintage Story data paths without browser sandbox limits.

### 1.4 Audience

- Players who want **visibility** (position, pace, rough ETA) without reading raw logs.
- Users who value **privacy** (no upload; no backend).
- Users who accept that inference from logs can be imperfect if formats change.

### 1.5 Non-goals

- No backend, account, or upload.
- Not an official Vintage Story product; log formats may change.
- Not a general-purpose log analyzer; scope is **connect queue** + closely related states.

### 1.6 Primary surface

| Surface | Role |
|--------|------|
| **Web UI** (`monitor.py` default, optional `--web`) | Embedded desktop window (pywebview) or browser + local HTTP on `127.0.0.1`; folder path, KPIs, graph, settings, tour. SSH: port-forward and open the same URL. |

### 1.7 Third-party code (open source)

The product **relies on open-source stacks** where practical: Python stdlib for core logic, **Starlette** and **uvicorn** for the local web server, **pywebview** for the optional desktop host. The web client may ship **vendored** MIT/BSD bundles under `vs_queue_monitor/web/static/vendor/` (documented in `vendor/README.md`) when a small, maintained library beats ad-hoc code and a no-build-step install is required. Prefer **mature OSS on PyPI** for the Python side when the tradeoff is reasonable. Do not introduce **proprietary SDKs** or closed, undocumented components as required dependencies.

---

## 2. Parity contract (engine vs web client)

Behavior and vocabulary come from the **shared engine**; the web client implements presentation and controls.

| Concern | Where |
|--------|--------|
| REST + WebSocket state | `vs_queue_monitor/web/server.py` |
| Engine hooks (timers, history, alerts) | `vs_queue_monitor/web/hooks_web.py` |
| Graph (step series, ticks, grids, hover tooltip) | `web/static/graph_canvas.js` + `GET /api/meta` → `graph_theme` |
| Queue session graph scope | `core.queue_sessions_for_log_tail` · `app.js buildDisplayState` |
| Native **folder** / **log file** browse dialogs | `POST /api/pick_path` — Tk dialog on the Python host |
| Threshold ranges (`3-1`, `8-10`) | `parse_alert_thresholds` in `core.py` + `mergeAlertThresholdsString` in `app.js` |
| Build fingerprint / version | `GET /api/meta`; env `VS_QUEUE_MONITOR_BUILD_FINGERPRINT` (legacy: `VSQM_BUILD_FINGERPRINT`) |
| Dashboard theme from Python | `GET /api/meta` → `graph_theme`, `chrome_theme` (`vs_queue_monitor/web/theme.py`) |
| Keyboard shortcuts | `Space` start/stop · `F1` help · `o` settings · `c` copy graph TSV · `v` copy session history |

---

## Regression log (prevent repeat debugging)

This section exists to avoid re-discovering the same failures. When a bug/regression is found and fixed, add an entry with the **symptom**, the **root cause**, the **fix**, and a **verification recipe** (what to do / what to look for). Keep entries short and actionable.

### Entry template (copy/paste)

- **Title**: \<short name\>
- **Symptom**: \<what the user sees\>
- **Trigger**: \<when it happens / log conditions / UI conditions\>
- **Root cause**: \<the actual bug, not the visible effect\>
- **Fix**: \<what code changed and why\>
- **Verify**:
  - **Steps**: \<repro steps\>
  - **Expected**: \<the correct outcome\>
- **Notes**: \<gotchas, follow-ups, links to commits/PRs\>

### What to prioritize logging

- **Session boundaries** (graph spans multiple sessions, “new run” not detected, stale values after reconnect)
- **Seeding/replay** (initial load shows wrong start/current, missing timestamps causing insane rates, duplicate points)
- **Live view / time axis** (empty runaway, frozen axis, jumpy scaling)
- **Interrupted/stale detection** (false interruptions, stuck status, recovery behavior)
- **History verbosity/perf** (too many points/lines, UI stalls, “log every position change” behavior)

### Must stay aligned (behavioral parity)

- **Queue semantics:** Position, “at front,” **completed** (past queue wait), **interrupted**, and **no queue detected** mean the same thing.
- **Numbers:** Rolling rate, global rate, elapsed, ETA, progress percent, and alert firing rules (downward crossings; once per threshold per run; completion ≠ “threshold at 0”).
- **Settings meaning:** Poll interval, thresholds, rolling window, alert toggles, “log every change” defaults and effects on History.
- **Vocabulary:** Same status strings/KPI labels where space allows.

### Justified differences (presentation/platform)

| Area | Why it may differ | Requirement |
|------|--------------------|-------------|
| Chart | Canvas vs future renderers. | Same **time series for the current session**. |
| Color | Theme constraints. | Map semantic roles (accent/muted/danger). |
| Layout | Responsive web layout. | Preserve information order: control → KPIs → graph → detail. |
| File access | Text field (paste path). | Same resolution rules (`resolve_log_file`); same outcomes. |
| Help | Modal in browser. | Same substance when explaining errors or paths. |
| Notifications | Browser **Notification** API vs inline toasts; header switch toggles persisted **popup** flag; Settings holds **Send test**. | Same events (threshold, completion, interrupt) when enabled. |
| Settings UI | Web modal + inline editors. | Same persisted fields and defaults. |

### Not justified (bugs or explicit debt)

- Different math or alert rules for the same input.
- Silently omitting core KPIs without hard size constraints.
- Contradictory copy for the same state.

---

## 3. Product goals and success metrics

### 3.1 Strategic goals

1. **Glanceable truth:** One screen answers “where, moving, how long, what next.”
2. **Trust:** Honest copy about estimates and log-derived inference.
3. **Low ceremony:** Launch → set **Logs folder** (or browse); monitoring starts; Stop/Start pauses/resumes; depth (Info/History/Settings) is optional.
4. **Resilience:** Missing log file, wrong folder, or unreadable paths are expected early; the UI stays actionable until `client-main.log` appears.

### 3.2 Success looks like

- Users understand **position**, **monitoring state**, **elapsed**, and **rough remaining** at a glance.
- No dead ends: invalid paths show clear errors; **Waiting for log file** is understandable.
- Completion UX aligns with **log-backed “past queue wait”**, not “position 1”.

---

## 4. UX principles (how “good” feels)

Aligned with [`.cursor/rules/ux-seamless-flow.mdc`](../.cursor/rules/ux-seamless-flow.mdc).

| Principle | What it means here |
|-----------|--------------------|
| **Low friction** | Minimal steps from launch → monitoring; remember last folder path in config when possible. |
| **In-context guidance** | Errors and status lines point to what to change (path, Start, Settings). |
| **Actionable errors** | Bad paths and missing files are explained with next steps (browse, fix path). |
| **Calm dashboard** | KPIs + one chart are primary; detail is collapsible. |
| **Honest states** | At front ≠ completed; interrupted ≠ monitoring; missing file ≠ no queue. |
| **No fake precision** | ETAs/rates are estimates; UI copy must not oversell accuracy. |
| **Explicit control** | Start/Stop and browse actions are deliberate; no mystery automation. |
| **Consistent vocabulary** | Same words for the same states across KPIs/graph/history/alerts. |

---

## 5. Visual design system (web UI)

The web client uses a **dark monitoring dashboard** aesthetic (Grafana-inspired spirit): low glare, muted labels, high-contrast values, accent colors for data/progress, and semantic success/danger colors. Styling lives in `vs_queue_monitor/web/static/styles.css` and structure in `index.html`.

### 5.1 Semantic roles

- **Background / cards:** layered dark surfaces for panels and history.
- **Text:** primary copy vs bright values for KPIs.
- **Muted:** labels, footnotes, secondary timestamps.
- **Accent:** graph line, progress, primary actions.
- **Danger / OK:** threshold warnings vs completed-positive states.

### 5.2 Typography

- System UI fonts for chrome; monospaced font for paths, history lines, and numeric detail where it aids scanning.

### 5.3 Chart styling

Framed plot area, time axis, step series for queue position; log/linear Y where available; on hover, a **tooltip** shows at least **timestamp and position** near the pointer (additional lines for sample index, scale, session, and deltas are allowed).

### 5.4 Layout

- Resizable panes (sashes) where implemented; graph sized for readability on typical displays.
- Primary actions and KPI strip remain visible while scrolling history.

---

## 6. Information architecture (main dashboard)

Mental model (stable and scan-friendly):

1. **Path / browse:** set Vintage Story data folder (or legacy file path → parent).
2. **Control strip:** Start/Stop, optional status.
3. **KPI strip:** position, status, rate, warnings, elapsed, remaining, progress.
4. **Graph:** time series for the current session/run.
5. **Info (secondary):** supporting context.
6. **History (secondary):** narrative events + optional per-step queue changes.
7. **Settings (advanced):** rarely used; inline edits for frequent tweaks where implemented.

Progressive disclosure: first-time users need (1–4); power users expand (5–7).

---

## 7. Core user journeys (desired behavior)

### Journey at a glance

| Phase | Experience |
|------|------------|
| First launch | Set **Logs folder** (browse or paste); Start monitoring; or wait until `client-main.log` exists. |
| After path resolves | Status shows resolved file; chart + KPIs seed from the current session. |
| While monitoring | KPIs + chart update on the poll interval; states are honest and consistent. |
| Alerts | Noticeable but non-hostile; recorded in History. |
| Return visit | Restored path from config; monitoring can auto-start per settings. |
| Something goes wrong | Clear status (Interrupted, missing file, no queue lines) and recovery by reconnect or path fix. |

### 7.1 First-time setup

1. Launch the app.
2. Choose the Vintage Story **data** folder (or pass `--path`).
3. If `client-main.log` is not there yet, stay in **Waiting for log file** until it appears.
4. Seed KPIs + chart from the current run when the log is readable.

Desired emotion: “I know what to set; nothing scary happened.”

### 7.2 Returning user

- Config restores the last folder path; user can browse again if the install moved.

Desired emotion: “It remembered my folder.”

### 7.3 Active monitoring

- Position steps, chart updates.
- Elapsed tracks this session (log-anchored when available).
- ETA/rate remain meaningful, including at position 1 (one-step framing).
- Progress reaches 100% only at true completion (past queue).

Desired emotion: “I trust the direction of travel.”

### 7.4 Threshold alerts

- Fire once per threshold per run on downward crossings.
- Thresholds are position milestones, not completion.

### 7.5 Completion (past queue wait)

- Completion is not “position <= 1”.
- It triggers when post-queue progress appears **after** the last queue line.
- Completed status + 100% progress + completion alert align to that moment.

### 7.6 Interrupted/stale queue

- Interrupted is explicit; elapsed/rate freeze appropriately.
- Continue watching the log for recovery.

### 7.7 New queue after interrupt

- If a new session appears, offer to **adopt** the new run (re-seed) vs dismiss.

---

## 8. Feature decisions captured from prompts (lossless)

This section converts ad-hoc prompts into durable feature requests, with **request → decision → shipped**. The **implementation** is Python (`vs_queue_monitor/`). Some items originated from an earlier browser prototype; behavior is consolidated here and **shipped in the web UI** where applicable.

### 8.1 KPI tooltips & inline edits (reduce trips to Settings)

- **FR: Progress should show exact percent**
  - **Decision**: Tooltip or label shows percent; bar stays simple.
  - **Shipped**: Web UI shows percent next to the progress bar.

- **FR: Key KPI settings editable in-place**
  - **Decision**: Contextual editors for warnings, rolling window, poll interval in the web UI.
  - **Shipped**: Inline or popover editors; **o** opens Settings.

- **FR: Compact save/cancel actions**
  - **Decision**: Small confirm/cancel affordances where inline edit exists.

### 8.2 Visualization & graph (Grafana-inspired)

- **FR: Readable chart**
  - **Decision**: Framed plot, grid, time axis, step series, optional fill.
  - **Shipped**: HTML canvas graph in the web client.

- **FR: Live view behavior**
  - **Decision**: Session data retained; view can follow “now” while monitoring when enabled.
  - **Shipped**: `graph_live_view` in saved config (default on). Web client extends the X-axis to the current time while monitoring when enabled. Toggle on chart and in Settings → Graph.

- **FR: Hover / point feedback**
  - **Decision**: Nearest-point feedback on mouse move; **HiDPI**: canvas uses device pixel ratio.

- **FR: Poll deltas**
  - **Decision**: Append each parsed queue reading as its own point with monotonic timestamps.

- **FR: Graph resize**
  - **Decision**: Window resize triggers canvas redraw.

### 8.3 Alerts, sounds, and History verbosity

- **FR: Log every position change by default**
  - **Decision**: Default **on** for auditability; user can reduce noise.
  - **Shipped**: Default `show_every_change` true in engine config unless overridden.

- **FR: Sound sources configurable**
  - **Decision**: Default WAVs, optional file paths, platform sounds where wired.
  - **Shipped**: Per-channel options in Settings (same persisted fields as engine).

- **FR: Sound preview**
  - **Decision**: Preview respects Play/Stop semantics without overlapping alerts.

- **FR: Interrupted as distinct alerts**
  - **Decision**: Interrupt channel separate from threshold/completion when enabled.

### 8.4 KPI polish and motion discipline

- **FR: Warnings rail**
  - **Decision**: Avoid gratuitous animation; scroll/pan when thresholds overflow.

- **FR: Status color-coded**
  - **Decision**: Semantic colors for monitoring / at front / completed / interrupted / danger.

### 8.5 Tail activity

- **FR: Subtle activity indicator**
  - **Decision**: Optional log-activity line tied to new log bytes (web client).

### 8.6 Settings

- **FR: Settings grouped**
  - **Decision**: Modal or dedicated screen; not mixed into primary KPI row unnecessarily.

### 8.7 Onboarding

- **FR: First-run clarity**
  - **Decision**: Path field + short help text; optional guided tour in web client.

### 8.8 Notifications

- **FR: Desktop notifications**
  - **Decision**: Browser **Notification** API where permitted; inline toasts always; mirror threshold/completion events.
  - **Decision (header switch)**: The top-bar control is a **real on/off** for the same persisted **`popup_enabled`** flag as **Settings → Warning popup** (toast + desktop notification when the browser allows). It is **not** only a permission prompt: when the browser has already **granted** permission and the switch is **on** (live), another click **turns alerts off** by patching config; when **off** but permission is still **granted**, a click can turn alerts **back on** without opening Settings. Browser permission cannot be revoked from JS; the switch reflects **app intent** plus **permission state** (e.g. blocked vs pending vs live).
  - **Decision (test banner)**: **Send test notification** lives in **Settings** (near Warning popup) so the header control stays a clear power toggle, not a mixed “test + toggle” action.
  - **Decision (visual language)**: The switch uses the same **small corner radius** as other top-bar **buttons** (not a full pill), so the chrome reads as one family of controls.

---

## 9. Feature-level intent (product surfaces)

### 9.1 Dashboard (main view)

- At a glance: position, status, rate, warnings, elapsed, **remaining** (rough estimate; KPI label **REMAINING**), progress.
- Graph: time series for the current session; log/linear Y where available.
- Info/History are secondary sections in the web layout.

### 9.2 Queue semantics (“done”)

- Position is derived from log lines.
- UI position **0** means **past connect-queue wait** (post-queue signals), not merely “<= 1”.
- At front and completed must remain visually and semantically distinct.

### 9.3 Monitoring lifecycle

- Monitoring starts on successful start with resolved log, or waits for file creation.
- Stop ends polling; state resolves clearly.
- Seeding after start should produce meaningful history/graph for the current run.
- Interrupted/stale/reconnecting states are visible and do not pretend the queue is advancing.

### 9.4 Alerts

- Warnings: downward crossings; once per threshold per run.
- Completion: log-backed end-of-queue-wait; distinct from thresholds.
- In-app messages always available; OS notifications and sounds optional.

### 9.5 Estimation (ETA, rate, progress)

- ETA/rate degrade gracefully when data is thin.
- At position 1, remaining time stays meaningful where the model supports it.
- Progress reaches full only at true completion (past queue).

### 9.6 History verbosity

- “Log every position change” off: routine steps omitted (not just re-labeled).
- On: step-by-step narrative for auditability.

### 9.7 Settings & persistence

- Local persistence only (`config.json` via `vs_queue_monitor.core`).
- Changes feel safe: validation and explicit save where applicable.

### 9.8 Paths

- Prefer **folder** paths; resolve `client-main.log` with `resolve_log_file`.
- Do not require the log file to exist before accepting a valid data directory.

---

## 10. Constraints we design around

- **No server:** all state local on the user’s machine.
- **Privacy:** log stays on device; nothing is uploaded by the app.
- **Cross-platform:** Windows, macOS, Linux; **SSH** via port-forward to the loopback server.

---

## 11. How this doc relates to other docs

| Doc | Role |
|-----|------|
| [`README.md`](../README.md) | Setup, run, troubleshooting, precise behavior. |
| Section 2 above | Web client ↔ engine mapping (shortcuts, APIs, hooks). |
| `.cursor/rules/ux-seamless-flow.mdc` | Implementation bias for agents (seamless flows, actionable UI). |
| This file | Product and UX intent: what the user experiences and why. |
| `vs_queue_monitor/core.py`, `engine.py` | Parsing, queue semantics, tail I/O, config. |

When user-visible behavior changes, update **README** (and this doc if intent/journeys change) in the same change set.
