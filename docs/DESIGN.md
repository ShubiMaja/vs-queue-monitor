# VS Queue Monitor — product & UX design (web)

This is the **design contract** for VS Queue Monitor: product intent, UX principles, information architecture, journeys, and feature-level decisions. It is intentionally **lossless**: it preserves the full set of decisions captured from prompts, but rewrites the document into a more maintainable, professional design format.

**Scope.** This repository ships a **browser-only web app** (no backend). The design assumes the constraints of the **File System Access API** and browser notifications. Exact implementation details (storage keys, parsing edge cases, build steps) live in source and in [`README.md`](../README.md).

---

## 1. Product definition

### 1.1 One-line product

A **local-first, browser-based assistant** that reads the Vintage Story **client log** and turns it into a **glanceable dashboard**: queue position, movement over time, rough wait estimates, and optional alerts — **without uploading logs** or requiring a server.

### 1.2 Problem statement

When connecting to a busy server, players often wait in a **connect queue**. The client log contains position updates, but users don’t get a single surface that reliably communicates:

- **Where am I** (position)?
- **Is it moving** (trend/rate)?
- **How long have I waited** and **roughly how much longer**?
- **When am I actually done waiting** (not merely “at 1”)?

### 1.3 Solution (what we provide)

A browser UI that:

- **Tails** the chosen log file and derives queue KPIs (position, elapsed, ETA, progress).
- Visualizes the **current run** as a **time series** (step chart).
- Fires optional **threshold** and **completion** alerts (toast + sound + desktop notifications where supported).
- Provides in-context **help and recovery** for browser/OS file access limitations.

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
| **Web app** (e.g. `dist/index.html` in Chromium) | The **primary and only** shipped UI: pick log, monitor, settings, help, and notifications as supported by the browser. |

Design must assume File System Access constraints (picker availability, secure origin, permissions, protected paths): the product should **recover gracefully** and never imply we can read paths the browser cannot expose.

---

## 2. Parity contract (GUI vs TUI / alternate clients)

This repo implements the **web** client only. If alternate UIs exist in forks or future work, parity is defined as **behavior + language**, not pixels.

---

## Regressions & lessons learned

Operational notes, regressions, and verification recipes live in [`docs/REGRESSIONS.md`](./REGRESSIONS.md) to keep this document focused on product/UX design intent.

### Must stay aligned (behavioral parity)

- **Queue semantics:** Position, “at front,” **completed** (past queue wait), **interrupted**, and **no queue detected** mean the same thing.
- **Numbers:** Rolling rate, global rate, elapsed, ETA, progress percent, and alert firing rules (downward crossings; once per threshold per run; completion ≠ “threshold at 0”).
- **Settings meaning:** Poll interval, thresholds, rolling window, alert toggles, “log every change” defaults and effects on History.
- **Vocabulary:** Same status strings/KPI labels where space allows.

### Justified differences (presentation/platform)

| Area | Why it may differ | Requirement |
|------|--------------------|-------------|
| Chart | Terminal charts differ (ASCII/braille). | Same **time series for the current session**; labels may be compressed. |
| Color | Limited palettes. | Map semantic roles (accent/muted/danger), not hex parity. |
| Layout | Fixed grids, no drag-resize. | Preserve information order: control → KPIs → graph → detail. |
| File access | Direct paths vs browser picker tokens. | Same user outcome; recovery differs (symlink docs vs in-app Help). |
| Help | Modal vs inline text. | Same substance: why picks fail + how to expose logs safely. |
| Notifications | Different OS mechanisms. | Same events (threshold, completion, interrupt) when enabled. |
| Settings UI | Modal vs config file. | Same persisted fields and defaults. |

### Not justified (bugs or explicit debt)

- Different math or alert rules for the same input.
- Silently omitting core KPIs without hard size constraints.
- Contradictory copy for the same state.

---

## 3. Product goals and success metrics

### 3.1 Strategic goals

1. **Glanceable truth:** One screen answers “where, moving, how long, what next.”
2. **Trust:** Honest copy about estimates and log-derived inference.
3. **Low ceremony:** Open → pick log; monitoring starts; Stop/Start pauses/resumes; depth (Info/History/Settings) is optional.
4. **Resilience:** Cancellation/denial/protected paths are expected; UI always offers the next step.

### 3.2 Success looks like

- Users understand **position**, **monitoring state**, **elapsed**, and **rough remaining** at a glance.
- No dead ends: blocked picks include actionable recovery (Help, copyable commands, retry).
- Completion UX aligns with **log-backed “past queue wait”**, not “position 1”.

---

## 4. UX principles (how “good” feels)

Aligned with [`.cursor/rules/ux-seamless-flow.mdc`](../.cursor/rules/ux-seamless-flow.mdc).

| Principle | What it means here |
|-----------|--------------------|
| **Low friction** | Minimal steps from open page → monitoring; remember last log when policy allows. |
| **In-context guidance** | Recovery lives in toasts/banners/help modal (not only README). |
| **Actionable errors** | Cancel/deny/protected path always offers retry/guide/copy-command route. |
| **Calm dashboard** | KPIs + one chart are primary; detail is collapsible. |
| **Honest states** | At front ≠ completed; interrupted ≠ monitoring; missing file ≠ no queue. |
| **No fake precision** | ETAs/rates are estimates; UI copy must not oversell accuracy. |
| **Gesture-safe** | Picker/permission actions are explicit (buttons), not auto-popups. |
| **Consistent vocabulary** | Same words for the same states across KPIs/graph/history/alerts. |

---

## 5. Visual design system (web)

The UI uses a **dark monitoring dashboard** aesthetic (Grafana-inspired spirit): low glare, muted labels, high-contrast values, one accent family for data/progress/links, and semantic success/danger colors.

### 5.1 Tokens (CSS variables)

Tokens live in [`styles.css`](../styles.css) on `:root` and are semantic:

| Token | Typical use |
|-------|-------------|
| `--bg-app`, `--bg-app-mid` | Page background: cool base + subtle radial highlights. |
| `--bg-card`, `--bg-card-2`, `--bg-inset` | Cards and inset panels (history, inputs). |
| `--text`, `--text-bright` | Copy vs KPI values/titles. |
| `--muted` | Labels/hints/footer; scan hierarchy via uppercase micro-labels. |
| `--sep`, `--border-card` | Dividers and card hairlines (soft rgba). |
| `--shadow-card` | Elevation + inset highlight (cards/modals/toasts). |
| `--accent`, `--accent-soft` | Primary accent (links/progress/chart); focus rings. |
| `--link` | Links. |
| `--btn`, `--btn-active` | Neutral buttons. |
| `--btn-primary`, `--btn-primary-active` | Positive “go” actions (green). |
| `btn--stop` / stop tokens | Stop while monitoring: warm/amber distinct from Start. |
| `--danger` | Errors/danger emphasis. |
| `--ok` | Success-adjacent accents. |

### 5.2 Typography

- UI: `system-ui` (`--sans`)
- Data: monospace (`--mono`) for paths, history, numeric settings/code-like text

### 5.3 Chart styling

Canvas graph uses the same system: framed plot, soft grids, muted axis labels, cyan-tinted series line and markers, gradient fill under the step series.

### 5.4 Layout

- Max width ~1280px; centered to avoid ultrawide sprawl.
- Cards with rounded corners and soft elevation.
- Sticky top bar keeps primary controls reachable.

---

## 6. Information architecture (one-page app)

Mental model (stable and scan-friendly):

1. **Header:** identity, Pick log, Help, Settings, notification enablement.
2. **Control strip:** Start/Stop, permission/grant flows.
3. **KPI strip:** position, status, rate, warnings, elapsed, remaining, progress.
4. **Graph:** time series for the current session/run.
5. **Info (secondary):** supporting context.
6. **History (secondary):** narrative events + optional per-step queue changes.
7. **Settings (advanced):** rarely used; prefer inline edits for frequent tweaks.

Progressive disclosure: first-time users need (1–4); power users expand (5–7).

---

## 7. Core user journeys (desired behavior)

### Journey at a glance

| Phase | Experience |
|------|------------|
| First open | One clear action: **Pick log**. Monitoring starts after a successful pick. |
| After pick | Status explains what’s being watched; chart + KPIs seed from the current session. |
| While monitoring | KPIs + chart update on a sensible cadence; states are honest and consistent. |
| Alerts | Noticeable but non-hostile; recorded in History. |
| Return visit | Restore is low-friction when permissions allow; otherwise one obvious “grant/allow” action. |
| Something goes wrong | Actionable recovery: toasts/banners + Help generator. |

### 7.1 First-time setup

1. Open the app.
2. Pick `client-main.log`.
3. If a gesture/permission is required on reload, show one obvious action (grant/allow).
4. Seed KPIs + chart from the current run.

Desired emotion: “I know what to click; nothing scary happened.”

### 7.2 Returning user

- Restore the saved handle when policy allows; otherwise request permission with clear UI.

Desired emotion: “It remembered me.”

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

- If a new session appears, offer **Adopt new run** (re-seed) vs Not now.

---

## 8. Feature decisions captured from prompts (lossless)

This section converts ad-hoc prompts into durable feature requests, with **request → decision → shipped**.

### 8.1 KPI tooltips & inline edits (reduce trips to Settings)

- **FR: Progress bar should show exact percent**
  - **Request**: Add informative tooltips, e.g. percentage over the progress bar.
  - **Decision**: Keep a simple bar; hover reveals exact percent (plus minimal context).
  - **Shipped**: Tooltip with current percent; must not obscure controls.

- **FR: Make key KPI settings editable in-place**
  - **Request**: Make relevant settings interactive (warnings, rolling window, refresh).
  - **Decision**: Use contextual KPI popovers for frequently tuned values; keep Settings modal for advanced items.
  - **Shipped**:
    - WARNINGS: inline popover CSV editor.
    - RATE: inline popover editor for AVG window points.
    - STATUS: inline popover editor for refresh/poll seconds (shown in label).

- **FR: Inline popover actions should be icon-only**
  - **Request**: Use save/cancel icons in popovers.
  - **Decision**: Compact ✓/× with `title`/`aria-label`.
  - **Shipped**: ✓/× instead of Save/Cancel text.

### 8.2 Visualization & graph (Grafana-inspired)

- **FR: Grafana-inspired panel polish**
  - **Request**: Improve the chart with Grafana-like readability.
  - **Decision**: Framed plot, readable grid, compact axes, hover crosshair, area fill.
  - **Shipped**: Frame + grid + ticks + gradient fill + hover crosshair.

- **FR: Show time on the X axis**
  - **Request**: X axis should show time.
  - **Decision**: Compact HH:MM:SS ticks.
  - **Shipped**: Bottom time ticks.

- **FR: One “Live view” toggle (X-axis motion only), default on**
  - **Request**: Single toggle; live view on by default; “constant motion”.
  - **Decision**: Full-session history remains the data range; live view advances X-axis to “now” while monitoring.
  - **Shipped**: `Live view: on/off`, default on; affects X-axis motion only.

- **FR: Hover should reveal real update points (no crosshair snapping)**
  - **Request**: Crosshair stays under mouse; the traveling dot snaps; only show when near a real update; snap to minor dots too.
  - **Decision**: Crosshair follows pointer; hover marker snaps to nearest real point only within a small radius. Every log-derived update line is a point (even unchanged position).
  - **Shipped**: Pointer crosshair + proximity-based point snapping; minor updates recorded as points.

- **FR: Graph must not “jump” over intermediate updates**
  - **Request**: Avoid 40 → 34 style jumps.
  - **Decision**: Parse poll deltas and append each reading as its own point (monotonic timestamps).
  - **Shipped**: Poll delta parsing appends all readings.

- **FR: Graph hover must work reliably on HiDPI**
  - **Request**: Hover/snap unreliable on some displays.
  - **Decision**: Hit-testing uses CSS-pixel radius scaled by DPR.
  - **Shipped**: DPI-safe hit radius.

- **FR: Graph should be resizable (at least vertically)**
  - **Request**: Vertical resize.
  - **Decision**: Resizable card; immediate redraw via resize observation.
  - **Shipped**: Vertical resize + redraw.

- **FR: Copy a snapshot of the graph**
  - **Request**: Copy graph image to clipboard.
  - **Decision**: Copy PNG when supported; download fallback with clear messaging.
  - **Shipped**: Snapshot action with clipboard PNG + download fallback.

### 8.3 Alerts, sounds, and History verbosity

- **FR: Log every position change by default**
  - **Request**: Enable by default.
  - **Decision**: Default favors auditability; user can reduce noise.
  - **Shipped**: Default on (web config), respecting user overrides.

- **FR: Sound sources should be visible and configurable**
  - **Request**: Show current source; allow URL/local/default/built-in.
  - **Decision**: Each alert channel supports default shipped clip, URL, local file stored in browser, and built-in tones fallback.
  - **Shipped**: Per-channel controls in Settings.

- **FR: Sound preview should toggle Play/Stop**
  - **Request**: Preview must stop and not overlap.
  - **Decision**: Preview is independent of enable toggles; Play toggles to Stop and halts playback cleanly.
  - **Shipped**: Stateful preview with Play/Stop behavior.

- **FR: Separate disconnected/interrupted alert channel**
  - **Request**: Dedicated alert for Interrupted.
  - **Decision**: Interrupt is a distinct channel (toast + sound + desktop notification when enabled).
  - **Shipped**: Dedicated interrupt toggles and sound source.

### 8.4 KPI polish and motion discipline

- **FR: Warnings should not animate unless something happened**
  - **Request**: No continuous marquee.
  - **Decision**: Motion is an event cue; marquee briefly after alert fires (and only if overflow requires it).
  - **Shipped**: Gated marquee.

- **FR: Warnings should be side-scrollable**
  - **Request**: Pan left/right with wheel/trackpad.
  - **Decision**: Prefer direct manipulation; keep scroll arrows discoverable on hover.
  - **Shipped**: Horizontal pan + hover-revealed arrows.

- **FR: Warning thresholds editable inline**
  - **Request**: No weird edit mode; keep main rail calm.
  - **Decision**: Read-only rail; open a small contextual editor with chips + CSV add.
  - **Shipped**: WARNINGS popover editor.

- **FR: Status should be color-coded**
  - **Request**: Make status glanceable.
  - **Decision**: Map states to semantic roles: info/warn/done/danger/ok.
  - **Shipped**: Status value styling classes.

### 8.5 Tail activity indicator

- **FR: Tail indicator should be subtle**
  - **Request**: Softer, near graph; avoid redundant motion.
  - **Decision**: Quiet “armed” indicator; pulse minimized/disabled when graph already conveys motion.
  - **Shipped**: Subtle indicator; pulse disabled.

### 8.6 Settings as a modal

- **FR: Settings should be a top-right modal**
  - **Request**: Settings in a popup dialog.
  - **Decision**: Keep dashboard focused; settings are secondary.
  - **Shipped**: Settings modal opened from top-right.

### 8.7 Onboarding & guidance

- **FR: First-run guided tutorial**
  - **Request**: Gated steps; require log pick; guide warnings + rate; start monitoring on completion; skippable; persistent.
  - **Decision**: First-run onboarding with resume behavior (minimize to complete actions, then resume).
  - **Shipped**: Tutorial overlay with gating + “resume tutorial” affordance.

### 8.8 Notifications clarity

- **FR: Desktop notifications should be actionable**
  - **Request**: Indicate click-to-focus; include action button when possible.
  - **Decision**: Copy must tell the user they can click; action label like “Open monitor” where supported; click focuses existing tab or opens app.
  - **Shipped**: Click-to-open copy + service worker click focus/open handling.

### 8.9 Help generator (copy/paste quality)

- **FR: Remove Windows `/J` guidance**
  - **Request**: Use only hard links for a file.
  - **Decision**: Windows generator produces only `mklink /H` for a file; no folder links.
  - **Shipped**: `/H` only.

- **FR: Command output should be clean (no `REM` noise)**
  - **Request**: Copy buffer should be runnable.
  - **Decision**: Keep guidance minimal; avoid comment spam.
  - **Shipped**: Clean command output.

### 8.10 Secure origin requirement (browser reality)

- **FR: “Non-packed index.html is not usable”**
  - **Request**: File picking doesn’t work when opened directly.
  - **Decision**: Be explicit: picking and service-worker-backed notifications may be unavailable on `file://` / non-secure origins; instruct `http://localhost` (or `https://`) and avoid silent failure.
  - **Shipped**: Clear guidance and toasts to open via localhost for picker reliability.

---

## 9. Feature-level intent (product surfaces)

### 9.1 Dashboard (main view)

- At a glance: position, status, rate, warnings, elapsed, estimated remaining, progress.
- Graph: time series for the current session; log/linear Y improves readability during long waits.
- Info/History are secondary and collapsible.

### 9.2 Queue semantics (“done”)

- Position is derived from log lines.
- UI position **0** means **past connect-queue wait** (post-queue signals), not merely “<= 1”.
- At front and completed must remain visually and semantically distinct.

### 9.3 Monitoring lifecycle

- Monitoring starts on successful pick or explicit Start after Stop.
- Stop ends polling; state resolves clearly.
- Seeding after start should produce meaningful history/graph for the current run.
- Interrupted/stale/reconnecting states are visible and do not pretend the queue is advancing.

### 9.4 Alerts

- Warnings: downward crossings; once per threshold per run.
- Completion: log-backed end-of-queue-wait; distinct from thresholds.
- Toasts work without notification permission; desktop notifications are optional; sounds are optional and user-controlled.

### 9.5 Estimation (ETA, rate, progress)

- ETA/rate degrade gracefully when data is thin.
- At position 1, remaining time stays meaningful where the model supports it.
- Progress reaches full only at true completion (past queue).
- Prefer stability and comprehensibility over noisy flicker (dwell/windowing serve this).

### 9.6 History verbosity

- “Log every position change” off: routine steps omitted (not just re-labeled).
- On: step-by-step narrative for auditability.

### 9.7 Settings & persistence

- Local persistence only (browser storage).
- Changes feel safe: debounced save, validation, easy recovery.

### 9.8 Help & path friction

- Explain “why” when blocked: browser/OS policy, not user blame.
- Provide Windows vs macOS/Linux guidance.
- Offer generated commands from user-pasted paths; keep in-app copy/paste friendly.

---

## 10. Constraints we design around

- **No server:** all state local.
- **Security:** user gestures and secure origins are required for some features; flows must teach this.
- **Privacy:** log stays on device.
- **Deploys:** optional `version.json` enables a lightweight “update available” nudge without a backend.

---

## 11. How this doc relates to other docs

| Doc | Role |
|-----|------|
| [`README.md`](../README.md) | Setup, run, troubleshooting, precise behavior for contributors. |
| `.cursor/rules/ux-seamless-flow.mdc` | Implementation bias for agents (seamless flows, actionable UI). |
| This file | Product and UX intent: what the user experiences and why. |
| `app.js` | Exact parsing, state machine, strings, and edge cases. |

When user-visible behavior changes, update **README** (and this doc if intent/journeys change) in the same change set.
