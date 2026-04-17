# VS Queue Monitor — product & UX design

This document describes **intended** behavior from a **product** and **UI/UX** perspective: vision, who we serve, strategic goals, journeys, information architecture, and feature-level intent. It stays **high level**—no API keys, storage keys, or line-by-line parsing rules.

**Layers:** **Product** = why the tool exists and what success means. **Features** = what surfaces do (dashboard, alerts, settings). **UI/UX** = how it should feel (progressive disclosure, honest copy, recovery). **Visual design** = dark dashboard look, color tokens, type, and layout (see **§2.1**). **Implementation** (exact strings, edge cases, build steps) lives in code and in [`README.md`](../README.md).

---

## 1. Product intent

**One-line product.** A **local-first, browser-based assistant** that reads the Vintage Story **client log** on the user’s machine and turns it into a **small dashboard**: queue position, movement over time, rough wait estimates, and **optional** alerts — **without** uploading logs or requiring a server.

**Problem.** Players joining a busy Vintage Story server often wait in a **connect queue**. The game log contains queue position updates, but the game UI does not always surface wait time, rate of progress, or reliable “you are done waiting” feedback in one place.

**Solution.** A **local, browser-only** companion that **tails the client log**, derives **queue position**, **elapsed wait**, **estimated remaining time**, and **progress**, and optionally **alerts** at chosen thresholds and when the wait is **actually over** (per log semantics—not only “position 1”).

**Who it’s for**

- Players who **queue via the client** and want **visibility** (position, pace, rough ETA) without digging through raw logs.
- Users who care about **privacy** (log stays on device; no backend in this product).
- People who accept that **inference from log text** can be wrong or incomplete when formats or edge cases change.

**Primary surface**

| Surface | Role |
|--------|------|
| **Web app** (e.g. `dist/index.html` in Chromium) | **Primary** and **only** shipped UI in this repository: pick log, monitor, settings, help, notifications as supported by the browser. |

Behavior should assume **File System Access** constraints (picker, permissions, protected paths): the product must **recover gracefully** and never imply we can read paths the browser cannot expose (see **§5.6**).

### 1.1 Graphical UI vs terminal UI (parity and justified differences)

**Scope of this repo.** The codebase here implements the **web** client only. There is **no** separate desktop (Tk) or terminal (Textual/curses) UI in-tree to “match” or diff against. Any **GUI vs TUI** discussion below is a **design contract** for forks, future surfaces, or legacy branches so that differences are either **justified** or treated as **bugs**.

**What must stay aligned (behavioral parity)** — any alternate UI should present the **same product truth**:

- **Queue semantics:** Position, “at front,” **completed** (past queue wait), **interrupted**, and **no queue detected** mean the **same thing** as in the shared rules (see README).
- **Numbers:** Rolling rate, global rate, elapsed, ETA, progress **percent**, and threshold list behavior — **same formulas and firing rules** (downward crossings, once per threshold per run, completion not equal to “threshold at 0”).
- **Settings meaning:** Poll interval, thresholds, rolling window, alert toggles, “log every change” — **same defaults and effect on History**.
- **Vocabulary:** Reuse the **same status strings and KPI labels** where space allows so users can switch surfaces without relearning.

**Justified differences (presentation and platform)** — these do **not** need pixel parity:

| Area | Why a TUI (or other CLI) may differ | Requirement |
|------|--------------------------------------|-------------|
| **Chart** | Terminals use braille blocks, ASCII, or simplified sparklines instead of a canvas. | Same **time series for the current session**; fidelity can be lower; axis labels may be compressed. |
| **Color** | Limited palette (16/256 colors) vs full CSS. | Map **roles**: accent ≈ primary data, muted ≈ labels, danger ≈ error — not necessarily the same hex. |
| **Layout** | Fixed character grid, no drag-resize panes. | Same **information order** where possible: control → KPIs → graph → detail (Info/History). |
| **File access** | Direct filesystem path or `stdin` vs browser file picker and permission tokens. | Same **outcome**: user points at the log (or folder) the engine reads; recovery paths differ (symlink docs vs `?` overlay). |
| **Help** | Inline text, man-page style, or link to README vs modal + command generator. | Same **substance**: why picks fail, how to expose logs on disk. |
| **Notifications** | Bell, OSC 9, or OS APIs vs **Notification** API. | Same **events** (threshold, completion) when the user enables alerts. |
| **Settings UI** | Modal form vs tabbed panels vs config file only. | Persisted **fields** should map 1:1 to the web app’s settings model. |

**Not justified (should be fixed or documented as debt):**

- Different **math** or **alert firing** for the same log input.
- Hiding a **core KPI** (position, status, rate, elapsed, remaining, progress) without a **hard terminal size** constraint — if the terminal is too narrow, truncation or a single “summary line” is OK; **silently omitting** semantics is not.
- **Contradictory copy** for the same state (e.g. “Completed” in one UI vs “Stopped” in another for the same tail).

**Summary:** **Match behavior and language; vary chrome.** If a terminal UI is added alongside this web app, treat it as **another skin** on the same monitor, not a second product with different rules.

**Strategic goals**

1. **Glanceable truth (within limits):** One screen answers: *Where am I? Is the queue moving? Roughly how long? Anything I should react to?*
2. **Trust:** No hidden upload; **honest** copy about estimates and log-derived inference.
3. **Low ceremony:** Happy path is *open → pick log* (monitoring starts automatically); **Stop** / **Start** pauses and resumes; depth (Info, History, settings) is **optional**, not mandatory reading.
4. **Resilience:** Picker cancel, permission denial, and “system file” blocks are **expected**; the UI always offers a **next step** (retry, Help, copyable commands), not a dead end.

**Success looks like**

- The user can **glance** at one screen and understand: *where they are in queue*, *whether monitoring is active*, *how long they have been waiting*, and *roughly how much longer* (when the model can say).
- The user is **never stranded**: permission issues, canceled pickers, and blocked paths come with **clear next steps** (in-context help, actions, copyable commands—not only prose).
- The tool is **honest**: estimates and statuses are labeled as such; **completion** aligns with **log-backed “past queue wait”**, not wishful UI.

**Non-goals**

- **No backend**, no account, no uploading logs—by design.
- **Not** a guarantee of server behavior: ETAs and positions are **derived from the log** and can be wrong if the log or game behavior changes.
- **Not** an official Vintage Story product; log formats can change.
- **Not** a general-purpose log analyzer — scope stays **connect queue** and closely related client status.

---

## 2. UX principles (what “good” feels like)

These align with [`.cursor/rules/ux-seamless-flow.mdc`](../.cursor/rules/ux-seamless-flow.mdc) and should guide UI decisions:

| Principle | Desired behavior |
|-----------|------------------|
| **Low friction** | Few steps to go from “open page” to “monitoring,” with **remembered log** and **autostart** when the browser allows. |
| **In-context guidance** | Help, recovery, and “next action” live **where the user already is** (toasts, banners, `?` overlay)—not only in external docs. |
| **Actionable errors** | Cancellation or denial is **not a dead end**: offer **retry**, **guide**, or **copy command** paths. |
| **Calm dashboard** | Primary view stays **readable at a glance**: big KPIs, one chart, optional detail collapsed by default. |
| **Honest states** | Distinguish **still in queue at front** vs **completed past queue**, **interrupted** vs **still monitoring**, **waiting for file** vs **no queue in log**. |
| **No fake precision** | ETAs and rates are **estimates**; copy and UI should not imply scientific certainty. |
| **Gesture-safe** | Anything that must follow a user gesture (e.g. file picker) is a **button**, not an automatic popup on load. |
| **Consistent vocabulary** | Same words for the same states across KPIs, graph, History, and alerts. |

---

## 2.1 Visual design: colors, typography, and layout

The web UI follows a **dark, dashboard-style** look: low-glare backgrounds, **muted labels** with **high-contrast values**, and a **single accent** for links, focus, chart series, and progress—similar in spirit to monitoring tools (e.g. Grafana-like dark UIs), tuned for **long sessions** without harsh contrast.

### Color system (CSS tokens)

Implementation lives in [`styles.css`](../styles.css) on `:root`. Tokens are **semantic**: use them for meaning, not one-off hex in new UI.

| Token | Typical use |
|-------|-------------|
| **`--bg-app`**, **`--bg-app-mid`** | Page background: cool dark base plus **radial** highlights (subtle blue/green wash) and a vertical blend for depth—not a flat fill. |
| **`--bg-card`**, **`--bg-card-2`**, **`--bg-inset`** | Card surfaces (often **gradient**), inset panels (history, inputs). |
| **`--text`**, **`--text-bright`** | Primary copy vs KPI / titles (slightly brighter for scan). |
| **`--muted`** | Labels, hints, footer—**scan hierarchy** with uppercase micro-labels on cards. |
| **`--sep`**, **`--border-card`** | Dividers and card hairlines (soft rgba, not harsh lines). |
| **`--shadow-card`** | Card/modal elevation: soft outer shadow + **inset** top highlight. |
| **`--accent`**, **`--accent-soft`** | **Primary accent** (links, progress, chart); soft variant for focus rings. |
| **`--link`** | Hyperlinks (hover brightens slightly). |
| **`--btn`**, **`--btn-active`** | Default buttons: neutral slate; hover brightens. |
| **`--btn-primary`**, **`--btn-primary-active`** | **Positive / go** actions (e.g. grant access, primary confirmations)—green, not the same as the blue accent. |
| **`--btn-stop-*`**, **`btn--stop`** | **Stop** while monitoring is live: warm dark gradient + amber border—visually distinct from green **Start**, so pause/stop is not mistaken for another “go”. |
| **`--danger`** (`#f2495c`) | Errors, destructive emphasis, danger text (e.g. `.danger` on status). |
| **`--ok`** (`#73bf69`) | Success-adjacent accents where used (e.g. positive framing in banners). |

**State overlays (not always separate tokens):**

- **Restore / resume banner:** Green-tinted gradient over the app bar so “you can continue” reads as **opportunity**, not alarm (`restoreBanner` in CSS).
- **Toasts:** Gradient card panels; **error** / **warn** / **ok** border tints; backdrop blur on the stack—**noticeable but not full-screen**.

### Chart (canvas)

The queue **graph** is drawn in [`app.js`](../app.js) with colors aligned to the same system: **vertical gradient** plot fill, soft grid lines, axis labels near **`--muted`**, cyan-tinted **series** line and marker—so the chart **matches** the KPI strip and progress bar.

### Typography

- **UI:** `system-ui` stack (`--sans`) for labels, buttons, and prose.
- **Data:** **Monospace** (`--mono`) for paths, history, numeric settings, and code blocks—signals **machine-sourced** content and improves alignment when scanning columns.

### Layout and shape

- **Max width** (~1280px) keeps the dashboard readable on ultrawide monitors; content stays **centered**, not edge-to-edge chaos.
- **Cards:** Rounded corners (~14px), **`--border-card`** + **`--shadow-card`**; **sticky top bar** with blur/saturation and shadow so controls stay reachable while scrolling.
- **Density:** KPI row is **compact but legible**; graph is the **largest** visual anchor below KPIs—reinforces “position over time” as the main story.

### Design principles (visual)

- **One accent family:** Blue/cyan for **data + progress + links**; green for **primary affirmative** actions; red only for **problems**—avoid rainbow KPIs.
- **Calm defaults:** No animation required for trust; optional subtle transitions in CSS are fine; **no** flashy effects that distract from numbers during a queue wait.
- **Accessibility:** Relies on **color + label** (e.g. danger class on status, not color alone); focus rings use visible blue-tinted outlines on inputs (`--link` / accent family).

When adding features, **extend tokens** or reuse existing ones before introducing new hex values—keeps the product visually coherent as the README and help content grow.

---

## 3. Information architecture (high level)

The app is a **single-page dashboard** with a stable mental model:

1. **Header** — identity, **Pick log**, **help** (`?` placed adjacent to picking), optional **notifications** enablement. Help is a **working surface** (short picker guidance, command generator, load actions); **README** holds full troubleshooting.
2. **Control strip** — pick log (and optionally folder where supported), **Start / Stop**, and when needed **permission / grant access** flows. This is the **gate** between “configured” and “live.”
3. **KPI strip** — **at-a-glance** numbers: position, status, rate, warnings (thresholds remain readable even when the list overflows: subtle motion only when an alert fires, plus user-controlled horizontal pan), elapsed, ETA, progress. This answers “what’s happening now?” without scrolling.
4. **Chart** — **time series** of position for the **current queue session**, so the user sees **trend**, not only a snapshot.
5. **Info (collapsible)** — **secondary** detail: last changes, global averages, resolved label for the log source—**supporting** the KPIs, not competing with them.
6. **History (collapsible)** — **narrative log** of app events and optional per-step queue lines (when enabled). For debugging and reassurance, not the primary readout.
7. **Settings (advanced)** — should trend toward **advanced overrides**, not a primary workflow surface. Prefer **inline customization** where effects are visible (e.g. warning thresholds edited from the WARNINGS KPI via a contextual popover). Keep debounced save; explicit save remains for validation and “I’m done” reassurance.

**Layout:** Dense but readable; **Info** and **History** stay secondary so the **graph and KPIs** remain primary during active monitoring.

**Progressive disclosure:** First-time users need **control strip + KPI + chart**; power users open **Info** and **History** and tune **Settings**.

---

## 4. Core user journeys (desired behavior)

### Journey at a glance

| Phase | What the user should experience |
|--------|----------------------------------|
| **First open** | Clear primary path: **Pick log file** (or equivalent). Monitoring **starts** when a log is chosen successfully; **Stop** / **Start** controls pause and resume. |
| **After pick** | Path/state is visible enough that the user knows *what* is being watched. Tail/poll behavior begins automatically; status reflects reality (idle → monitoring, errors explained). |
| **While monitoring** | KPIs and graph update on a **sensible cadence**; **status** vocabulary matches log-derived states (e.g. in queue, at front, completed, interrupted, waiting for file, error). |
| **Alerts** | Threshold and completion signals are **noticeable** (optional sound / system notification where enabled) but **not hostile**; History records what happened in plain language. |
| **Return visit** | If the browser still allows access to the same file, **resume** should be low-friction; if a new grant is needed, the UI says so explicitly (**no** silent failure). |
| **Something goes wrong** | Short, actionable feedback; **Help** explains platform limits and offers **generated commands** when the browser cannot open AppData-like paths directly. |

### 4.1 First-time setup

1. User opens the app (file or dev server).
2. User chooses **Pick log file** and selects `client-main.log` (or equivalent); monitoring **starts** when the pick succeeds.
3. If the browser requires **permission** or a **gesture** to resume after reload, the UI shows a **clear bar or toast** with **one obvious action** (e.g. grant / allow)—not a silent failure.
4. KPIs and chart **populate** from the **current queue session** in the log (same seeding rules as any monitoring start).

**Desired emotion:** *I know what to click; nothing scary happened.*

### 4.2 Returning user

1. **Saved handle** and config allow **restore** when policy allows.
2. If permission is already granted, monitoring can **resume with minimal clicks** (autostart path).

**Desired emotion:** *It remembered me.*

### 4.3 Active monitoring (the “happy path”)

1. **Position** updates as new log lines arrive; **chart** steps.
2. **Elapsed** tracks **wait in this session** from log-anchored timestamps, not wall clock alone.
3. **ETA** and **rate** update from empirical and windowed models; at **position 1** (at front), ETA should **remain meaningful** (e.g. one-step-to-done framing)—not “blank” while the log still says `1` for a long time.
4. **Progress** advances toward completion but should **not claim 100%** until the product definition of **done** (past-queue / position `0` in UI terms).

**Desired emotion:** *I trust the direction of travel; I’m not fooled into thinking I’m done at 1.*

### 4.4 Threshold alerts

1. User configures **warning thresholds** (e.g. when position drops through 10, 5, 1).
2. Each threshold should fire **once per queue run** when crossed **downward**, with optional sound/popup/browser notification.
3. Thresholds are **warnings about position**, not the same as **completion**.

**Desired emotion:** *Tell me when I cross lines I care about—without spam.*

### 4.5 Completion (past queue wait)

1. **Completion** is **not** “threshold at 0.”
2. It fires when the log indicates **post-queue-wait** activity **after** the last queue line (connecting/loading patterns as defined by the product)—so long stalls at position **1** do not prematurely celebrate **done**.
3. UI: **Completed**, **100% progress**, completion sound/popup align with this moment.

**Desired emotion:** *That was the real finish line.*

### 4.6 Interrupted or stale queue

1. If the run is **interrupted** (disconnect, staleness, or equivalent), the UI shows **Interrupted** (or similar) clearly.
2. **Elapsed** (and rate display where applicable) should **freeze** in a way that **does not lie**—not keep ticking as if still in a healthy queue.
3. Tailing may **continue** so the user can recover when new lines appear.

**Desired emotion:** *Something went wrong or stalled; the UI isn’t pretending everything is fine.*

### 4.7 New queue after interrupt

1. If a **new** queue appears in the log while interrupted, the product may offer to **adopt** that run and **re-seed** graph/alerts.
2. User should **confirm** intentional reset vs accidental jump.

**Implementation (web):** While **Interrupted**, if the log tail shows a **new** queue-run session (session index increased since interrupt), a **modal** offers **Adopt new run** (re-seeds graph + alerts from the current-session slice) or **Not now** (stays interrupted; prompt can repeat if the session changes). If the session is unchanged, recovery is **automatic** without the modal.

**Desired emotion:** *I can recover without losing my mind.*

---

## 5. Feature areas (product-level intent)

### 5.0 Feature requests (captured from prompts)

This section turns the project’s ad-hoc prompts into durable **feature requests** and records the **decision** the product adopted. Treat these as the “why” behind recent UX changes.

#### Visualization & graph (Grafana-inspired)

- **FR: Grafana-inspired graph panel polish**
  - **Request**: Learn what a good graph UI looks like from Grafana and improve this chart.
  - **Decision**: Adopt a monitoring-panel look: framed plot area, readable grid, compact axes, hover crosshair, and an area-under-line fill.
  - **Shipped**: Panel frame, horizontal + vertical grid, X time ticks, Y label, gradient fill under the step line, hover crosshair.

- **FR: Show time on the X axis**
  - **Request**: The axis should show time.
  - **Decision**: Render compact time ticks (HH:MM:SS) along the bottom so the user can read cadence at a glance.
  - **Shipped**: Bottom time ticks.

- **FR: Scroll the graph each poll tick (fixed time window)**
  - **Request**: The graph can move every tick; use the last tick vs current tick.
  - **Decision**: Prefer a Grafana-like “last \(N\) seconds” window so the plot scrolls forward each tick, rather than constantly rescaling the full session.
  - **Shipped**: Live window mode exists, but **full-session view remains the default**; live window is an explicit toggle.

- **FR: Default graph should be zoomed out (whole session)**
  - **Request**: Zoom out fully by default; show the whole graph.
  - **Decision**: Default to full-session context (trust + narrative). Provide an explicit “live window” toggle for users who want a scrolling time window.
  - **Shipped**: Default full-history view + a window toggle (full vs live).

#### Alerts, sounds, and history verbosity

- **FR: Log every position change by default**
  - **Request**: Enable logging every position change by default.
  - **Decision**: Default should favor auditability; users can turn it off to reduce History noise.
  - **Shipped**: Default on (web config) while preserving user overrides.

- **FR: Sound sources should be visible and configurable**
  - **Request**: Show which sounds are being used; allow URL or local file; provide nice defaults.
  - **Decision**: Each alert channel should expose (a) default shipped clip, (b) URL, (c) local file stored in browser, and (d) built-in tones as fallback.
  - **Shipped**: Settings show active sound source and provide URL/local/built-in/default controls.

- **FR: Sound preview button in Settings**
  - **Request**: A play button to preview in Settings.
  - **Decision**: Preview should always play regardless of whether the channel is enabled (to avoid “why didn’t it play?” confusion).
  - **Shipped**: “Play” preview per channel that ignores enable toggles.

- **FR: Separate disconnected/interrupted alert channel**
  - **Request**: A separate disconnected or interrupted sound/notification alert.
  - **Decision**: Treat Interrupted as its own alert channel (popup + sound + desktop notify) distinct from threshold and completion.
  - **Shipped**: Dedicated Interrupt alert toggles and sound source configuration; fires when the app enters Interrupted.

#### KPI polish and motion discipline

- **FR: Warnings should not slide unless a warning just fired**
  - **Request**: The warning list marquee should not animate continuously.
  - **Decision**: Motion is a “just happened” cue. Only marquee briefly after an alert fires (and only if overflow requires it).
  - **Shipped**: Marquee gate window triggered by threshold alerts.

- **FR: Warnings should be side-scrollable**
  - **Request**: Warnings is side scrollable; scrolling over it moves it left or right.
  - **Decision**: Prefer direct manipulation over animation: let the user pan the threshold strip horizontally (mouse wheel/trackpad) when it overflows.
  - **Shipped**: Warnings viewport is horizontally scrollable; wheel/trackpad pans left/right on hover.

- **FR: Warning thresholds should be editable inline (without a weird edit mode)**
  - **Request**: Make thresholds customizable without dumping users into a “settings screen”.
  - **Decision**: Keep the KPI strip calm: show thresholds as a read-only rail, and open a **small contextual editor** from the WARNINGS label (⚙/✎). In the editor, thresholds are **chips** with remove (×) and an “Add…” input that accepts CSV. No “hover-to-delete” surprises on the main rail.
  - **Shipped**: WARNINGS opens a popover editor with removable chips + CSV add; the rail remains read-only.

- **FR: Status should be color-coded**
  - **Request**: Make Status glanceable with color.
  - **Decision**: Map status to semantic roles: connecting/info, at-front/warn, completed/done, interrupted/error/danger, monitoring/ok.
  - **Shipped**: Status KPI class mapping and colors.

#### Tail activity indicator

- **FR: Tail pulse should be subtle and placed near the graph**
  - **Request**: Make tail pulse less bright and more subtle; maybe on bottom right of the graph.
  - **Decision**: Keep a quiet “tailing” affordance near the chart, not a bright centerpiece.
  - **Shipped**: Tail indicator docked to the graph; softer styling.

- **FR: If the graph scrolls each tick, the light doesn’t need to pulse**
  - **Request**: With per-tick motion, remove the pulse.
  - **Decision**: Avoid redundant motion; prefer the graph itself as the activity signal.
  - **Shipped**: Pulse disabled (indicator remains as a subtle “armed” state).

#### Settings as a modal

- **FR: Settings should be a top-right button with a popup dialog**
  - **Request**: Settings should be a button in the top right with a popup.
  - **Decision**: Settings is secondary; move it out of the main scroll into a modal overlay (like Help) to keep the dashboard focused.
  - **Shipped**: Settings modal opened from top-right button.

### 5.1 Dashboard (main view)

- **At a glance:** Position, status, rate (with rolling-window context where applicable), warnings/thresholds, elapsed time, estimated remaining (when meaningful), and **progress** aligned with “how much of the wait is behind you”—not a fake precision meter.
- **Graph:** Queue position over time for the **current session**; scale/mode (e.g. log vs linear Y) should support “seeing movement” during long waits.
- Collapsible or secondary regions for Info/History so monitoring stays **scannable**.

### 5.2 Queue position and “done”

- **Position** is derived from log lines; **0** in the UI means **past connect-queue wait** (post-queue signals), not merely “number ≤ 1.”
- **At front** and **Completed** must remain **visually and semantically distinct**.

### 5.3 Visualization

- **Chart:** **Recent history** for the **current session** so users see **trend and volatility**, not only the latest integer.
- **KPI strip:** Optimized for **numeric scan**; chart for **shape of the wait**.

### 5.4 Monitoring lifecycle

- Monitoring **starts** when the user successfully **picks** a log (or restores/grants access), or when they press **Start** after **Stop**; it begins reading/tailing the log on a **user-configurable poll interval** (within sensible bounds).
- **Stop** ends polling; state settles to a clear **stopped** (or **completed** when log semantics say so)—not an ambiguous limbo.
- The first read after any **start** should seed enough recent context for a **meaningful graph and timers** for the **current queue session** (session boundaries as documented in the README).
- **Interrupted / stale / reconnecting** states must be **visible** in status (and reflected in estimates where the design freezes or dampens values)—**no** silent pretense that the queue is still advancing.

### 5.5 Alerts: warnings vs completion

- **Warnings:** User-configured **milestones** on the way down the queue; fire on **downward crossings**, **once per threshold per run** (idempotent)—not on every poll tick.
- **Completion:** **Log-backed** end-of-queue-wait—**not** driven by the threshold list; triggers completion UX (notification/sound) in line with the **Completed** state.
- **Surface:** **In-page toasts** when alert toggles are on (works without notification permission); **desktop notifications** optional. Sounds are **optional** and user-controlled; defaults err toward **informative**, not alarming.

### 5.6 Estimation (ETA, rate, progress)

- **Rate** and **ETA** derive from recent steps and optional longer history; they **degrade gracefully** when data is thin.
- At **position 1**, remaining time should still be **meaningful** where the model allows (e.g. one-step-to-done), without implying second-level accuracy.
- **Progress** reaches **full** only when the run is **completed** in the log-derived sense—not merely after sitting at position 1.
- Communicate **rolling** and **global** notions of speed without duplicating jargon in the primary KPI row; **Info** can hold the longer explanation.
- Prefer **stable, understandable** numbers over noisy flicker; **dwell** and windowing exist to serve that.

### 5.7 History verbosity

- **Log every position change** off: reduce noise—routine steps **omitted** from History, not merely relabeled.
- On: full step-by-step narrative for users who want auditability.

### 5.8 Settings & persistence

- Settings persist **locally** (browser storage) without uploading paths or log content.
- Changes feel **safe**: debounced save, validation with clear errors, **reset to defaults** without hunting.

### 5.9 Help and path friction (browser reality)

- When the OS/browser blocks paths, the product should **not** pretend to know paths it cannot read.
- Some users **cannot** pick logs under protected locations. Desired UX:
  - Explain **why** (browser/OS policy), not “your fault.”
  - Offer **Help** with **Windows vs Mac/Linux** paths where behavior differs.
  - Provide **generated commands** from a user-pasted path so they can create a **reachable** file or junction and pick that—**copy/paste friendly**, minimal jargon in-app; **README** for long-form edge cases.

---

## 6. Constraints we design around

- **No server:** all state is **local** (storage APIs in the browser).
- **Security:** file access **requires user gestures** where the platform demands it; flows must **teach** that, not fight it silently.
- **Privacy:** logs stay on device; the README disclaimer remains the legal/expectation anchor.
- **Deploys:** Optional **static** `version.json` (same semver as the bundle) lets the client **compare** against a fetched copy and **nudge** reloads without a backend—**non-blocking** toast only.

---

## 7. How this doc relates to others

| Doc | Role |
|-----|------|
| **[`README.md`](../README.md)** | How to build, run, configure, and troubleshoot—**operator-facing** detail and **precise** behavioral notes for contributors. |
| **[`ux-seamless-flow.mdc`](../.cursor/rules/ux-seamless-flow.mdc)** | **Implementation bias** for agents: seamless flows, actionable UI. |
| **This file** | **Product and UX intent**—what we want users to experience and why. |
| **Source / `app.js`** | Exact parsing rules, state machines, and strings. |

When behavior changes in ways users would notice, update **README** (and this doc if the **intent** or **journeys** change) in the same change set, per project rules.
