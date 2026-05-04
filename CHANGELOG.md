# Changelog

All notable changes to VS Queue Monitor are documented here.

---

## v1.2.10 — 2026-05-04

### New features
- **Delayed connect** — "in: N min" field next to the Connect button. Set any number of minutes; clicking Connect starts a live countdown shown in the button ("Connect in 4:32"). A Cancel button aborts the countdown at any time.

---

## v1.2.9 — 2026-05-04

### New features
- **ngrok session survives app close** — ngrok is launched in its own terminal window on Windows (close it to stop the tunnel) and as a detached process on Unix. The tunnel keeps running if you restart or close the monitor.

### Fixes
- **Detect existing ngrok session** — status and Start both query the ngrok local API, so a tunnel started by a previous app session is correctly shown as running on restart.
- **Stop works across sessions** — PID is saved to `ngrok.pid` in the config dir; Stop tunnel kills the process even when the Popen handle is gone.
- **ngrok guide copy** — clarified that the URL is random on each start and that the Google email field restricts who can authenticate, not just "share with friends".

---

## v1.2.8 — 2026-05-04

### New features
- **Client panel** — monitor icon in the topbar opens a panel to set your VS install folder, pick a favourite server from your VS server list, and Connect / Disconnect the game client.
- **ngrok tunnel** — built-in Start/Stop tunnel controls in the client panel; publishes a shareable HTTPS URL with one click; optional Google account email restriction to gate access to your queue view.
- **Recent VS paths** — clock icon next to the VS install folder field works the same as the log-folder recent paths.

### Fixes
- **Interrupt fires after 60 s** (was 90 s) — log silence threshold reduced so the engine leaves "Reconnecting…" sooner after the game drops.
- **Adopt-new-run loop** — after accepting a new queue run from a `reconnecting` tail, the engine no longer immediately re-enters interrupted state and locks out future run detection.
- **Selected server and ngrok email remembered** between sessions via `localStorage`.

---

## v1.1.189 — 2026-05-03

### New features
- **Brand icon** — V-chevron + queue-dot mark replaces the generic bell favicon and About monitor icon. Reads clearly at 16 px browser tab size and scales to the About dialog.
- **What's New banner** — one-time dismissable banner shown on first page load after an upgrade. Bullet-lists what changed. Saved to `localStorage` per version so it only appears once.
- **Recent paths** — clock icon in the header path row shows the last few monitored folders; click any entry to switch instantly; per-entry × button to remove.

### Fixes
- **Auto-interrupt on long log silence** (v1.1.188) — after 90 s of no log activity while in queue the engine transitions from the perpetual "Reconnecting…" state to Interrupted. Graph is trimmed to the last real data point so disconnection dwell doesn't inflate rate metrics.
- **Loading bar on path select / Start** (v1.1.187) — bar now appears immediately on click instead of waiting for the first state snapshot.
- **Animated top loading bar** (v1.1.186) — 3 px shimmer bar at page top during initial load and folder switches.
- **Spurious interrupted alerts on slow queues** (v1.1.185) — stale detection now guards against firing when the log itself is still growing; VS only writes queue lines on position change, not every 30 s.
- **Silent byte-drop on UTF-16 logs** (v1.1.178) — `errors="ignore"` replaced with strict-first decode + `errors="replace"` fallback with a logged warning.

### UI polish (v1.1.181–1.1.184)
- Path field editing converted from a blocking modal to an inline popover.
- Update installation is fully user-gated — confirm dialog shows release name + GitHub link.
- Quick-start hint in empty state; improved Start/Stop button sizing; clickable alert thresholds.

### Session history (v1.1.111–1.1.165)
- Global cross-folder session list merged from all `session_history.jsonl` records.
- 26+ bug fixes: ghost suppression, duplicate entries, cross-folder visibility, outcome assignment, position-0 graph points, session numbering, in-progress vs unknown rank.
- Session history size cap (default 100 MB) configurable in Settings → General.

### Infrastructure (v1.1.174–1.1.176)
- Added `LICENSE`, `pyproject.toml`, CI workflow (GitHub Actions), pre-commit hooks, pinned `requirements.txt`.
- Security hardening: CSP headers, HTTPS-only release fetch, exponential WebSocket backoff, narrowed exception handlers.

---

## Earlier versions

See [GitHub Releases](https://github.com/ShubiMaja/vs-queue-monitor/releases) for v1.0.x – v1.1.110.
