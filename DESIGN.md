# VS Queue Monitor — product & UX design

This document describes **what we want the experience to be** from a product and UI/UX perspective. Operational steps, paths, and implementation details live in [`README.md`](README.md).

---

## Product intent

**VS Queue Monitor** helps **Vintage Story** players who use the **client log** understand **connect-queue position**, **how long the wait might take**, and **when to pay attention** — without sending the log anywhere.

- **Primary outcome:** The user can glance at one screen and know *where they are in queue*, *whether things are moving*, *roughly how much longer*, and *when threshold or completion events happen*.
- **Trust boundary:** The app is **browser-only** and **local-first**. There is **no backend**; the log file is read on the user’s machine under normal web security rules.
- **Honest scope:** The tool **infers** queue state from log text. ETAs and rates are **estimates**; users remain responsible for time-sensitive decisions (see disclaimer in the README).

---

## Core experience (what “good” looks like)

1. **Fast path to value:** Open the app → pick (or restore) the log → **Start** → the dashboard updates as the log grows.
2. **At-a-glance dashboard:** Queue **position**, **status**, **speed/ETA**, **warnings**, **elapsed time**, and **progress** are visible together; a **graph** shows how position changed over time.
3. **Optional depth on demand:** **Info** and **History** expand when the user wants detail; they stay out of the way when not needed.
4. **Recoverable friction:** Browsers restrict file access (gestures, permissions, “protected” folders). The UX should **never dead-end**: explain what happened, offer **the next concrete action** (retry pick, open help, copy a command, choose another path).
5. **Respectful alerts:** Threshold and completion signals should be **noticeable but not hostile** — optional sounds, optional system notifications, and clear copy in History.

---

## Intended user journey

| Stage | Desired behavior (high level) |
|--------|--------------------------------|
| **First open** | User sees a clear primary action: pick the client log (or folder where supported). **Start** stays disabled until a log can be monitored. |
| **After a successful pick** | User can **Start** monitoring. Optional: enable notifications for background alerts. |
| **During monitoring** | KPIs and graph update on a sensible cadence; status text matches what the log implies (in queue, at front, completed, interrupted, waiting for file, etc.). |
| **Return visit** | If the browser still grants access to the last file, the app can **resume** with minimal friction; if permission is needed, the user gets an explicit, one-step **grant / resume** path — not a silent failure. |
| **Blocked or canceled picker** | Short, non-alarming feedback; user can open **Help** for platform-specific workarounds (e.g. hard link / symlink patterns) and **copy exact commands** when paths cannot be revealed by the browser. |
| **Settings** | Changes feel **safe and persistent** (debounced save); **Reset** is available without hunting. |

---

## UX principles (how we design flows)

These align with the project’s seamless-flow guidance:

- **Minimize steps** on the happy path; avoid extra modals for routine actions.
- **Guide in context:** help and recovery live next to the action (toasts with buttons, **?** overlay with **Load file** / copyable commands, platform toggles where Windows vs Mac/Linux differ).
- **Make failures actionable:** cancellation, permission denial, and “system files” blocks should say what to do next, not only what went wrong.
- **Gesture-safe automation:** anything that must follow a user gesture (e.g. opening the file picker) is exposed as a **button**, not a surprise auto-popup.
- **Don’t fake certainty:** if the browser cannot show a path or access a location, say so and offer the documented workaround — don’t pretend we know more than the platform allows.

---

## Feature areas (product behavior, not implementation)

### Monitoring lifecycle

- **Start / Stop** controls whether the app **polls** the log on an interval (user-configurable).
- **Start** should load enough recent log context to **seed** the current queue session’s graph and timers in a way that matches user expectations (same session semantics as described in the README).
- **Interrupted** or **stale** conditions should be visible in status and KPI behavior (e.g. freezing rate where appropriate) without silently pretending the queue is still moving.

### Queue semantics (user-visible)

- **Position** and **Completed** should match **log-derived rules** (including **position `0`** for “past connect-queue wait” when the log supports it — see README).
- **“At front”** vs **“Completed”** must remain distinguishable: waiting at position 1 is not the same as done.

### Estimation and progress

- **ETA** and **rate** are **estimates** from recent and historical steps; at position 1, remaining time should still be meaningful where possible (one-step model), without implying exact real-world timing.
- **Progress** reaches **100%** when the run is **completed** in the log-derived sense, not merely when position is 1 for a long time.

### Alerts

- **Threshold warnings** fire on **downward crossings** of configured positions (per run), not on every tick.
- **Completion** is **not** a threshold list: it follows **post-queue** detection in the log, and drives completion UX (popup/sound) consistently with the **Completed** state.

### Settings and persistence

- Settings persist locally (**localStorage** / config key as documented); sensitive paths are not uploaded.
- **Log every position change** (when off) should **omit** routine queue lines from History — not just relabel them — so History stays high-signal.

### Help and “protected” paths

- The product assumes some users **cannot pick** the real log path inside AppData-like locations. The desired UX is: **Help** explains why, offers **generated commands** for the user’s pasted path, and separates **Windows** vs **Mac/Linux** instructions so users are not left to guess.

---

## Non-goals

- **No server-side processing** of logs or accounts.
- **Not** an official Vintage Story tool; no guarantee of matching future game log formats without updates.
- **Not** a general log analyzer — focus stays on **connect queue** monitoring and related status.

---

## Relationship to other docs

- **[`README.md`](README.md)** — requirements, build, step-by-step usage, troubleshooting, and precise behavioral notes for contributors.
- **[`.cursor/rules/ux-seamless-flow.mdc`](.cursor/rules/ux-seamless-flow.mdc)** — concise UX guardrails for changes in this repo.

When user-visible behavior or flows change, update **this file** if the **intent** or **journey** changes, and update **`README.md`** for **accurate operational detail** in the same change set when users would rely on it.
