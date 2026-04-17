# VS Queue Monitor (Web)

One-page **web app** that tails the **Vintage Story** client log, tracks **connect queue position**, estimates **wait time**, and raises alerts at configurable thresholds — all **in your browser** (no backend).

## Disclaimer (read this)

**No warranty — use at your own risk.** **Not affiliated with Vintage Story** or its developers. You must validate paths, alerts, ETAs, and time-sensitive decisions yourself.

- **Work in progress:** Features, UI, saved settings, and behavior can change at any time. Expect bugs and incomplete polish.
- **AI-assisted code:** A large share of this project was written or refactored with AI / coding assistants. That means **more risk of subtle mistakes** (logic, edge cases, platform quirks). You are responsible for validating paths, alerts, ETAs, and anything safety- or time-sensitive.
- **Not official:** Not affiliated with Vintage Story or its developers. **No warranty** — use at your own risk.

## Requirements

- **Microsoft Edge or Google Chrome** (Chromium).
  - **Live tail requires** the File System Access API (`showOpenFilePicker`), which is not reliably available in Firefox/Safari.
- **No backend and no local server**: the app is shipped as a **single HTML file** you open directly.

## Quick start

Open the built one-page app:

- Open `dist/index.html` in **Edge/Chrome**

## Using it

1. Click **Pick log file…** and select your `client-main.log` (or `client.log`).
2. Click **Start**.
3. Optional: click **Enable notifications** so threshold/completion popups can appear even when the tab is in the background.

The app stores settings in **`localStorage`** (on your machine in the browser profile). It does not upload your log anywhere.

**Picker default folder:** browsers do not allow preselecting arbitrary paths like `%APPDATA%` or `$HOME`. The file picker will start in a safe well-known location (typically **Documents**) and may remember your last choice depending on browser behavior.

**Settings persistence:** settings are saved automatically (debounced) to `localStorage` as you edit them. The **Save** button is still available to validate inputs and force an immediate save.

### If the browser blocks your log file (permissions)

Chrome/Edge can refuse access to some protected “system” folders. If the file picker says it **can’t open** the file/folder due to **system files**, use one of these:

**Windows (junction via Documents):**

```bat
mkdir "%USERPROFILE%\Documents\VintagestoryData"
mklink /J "%USERPROFILE%\Documents\VintagestoryData" "%APPDATA%\VintagestoryData"
```

Then pick: `Documents\VintagestoryData\Logs\client-main.log`

**Linux (symlink into ~/VSLogs):**

```bash
mkdir -p ~/VSLogs
ln -s ~/.config/VintagestoryData/Logs/client-main.log ~/VSLogs/client-main.log
```

Then pick: `~/VSLogs/client-main.log`

## Open-source hosted assets

The app can use hosted assets (no backend). If you want everything to work fully offline, you’ll need to embed/inline assets instead; this section is specifically for **hosted** open-source assets.

### Image (favicon)

- Twemoji (MIT): `https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f4c1.svg`

### Sounds (free hosted examples)

These are hosted on Wikimedia. Use them as defaults or as examples of “public URLs that work everywhere”:

- **Warning** (CC BY-SA 4.0): `https://upload.wikimedia.org/wikipedia/commons/f/f6/En-us-notification.oga`
- **Completion** (Public Domain): `https://upload.wikimedia.org/wikipedia/commons/1/1b/Clapping_hurray_%28cropped%29.oga`

If you use CC BY/CC BY-SA sounds, you must provide attribution (Wikimedia file pages list author/license).

### Host your own assets for free

If you prefer stable URLs under your control:

- **GitHub Pages**: commit files to a repo → Settings → Pages → Deploy from branch → use `https://<user>.github.io/<repo>/path/to/file.ogg`.\n- **Cloudflare Pages**: connect a GitHub repo in Cloudflare Pages → deploy → use `https://<project>.pages.dev/path/to/file.ogg`.\n- **Netlify Drop** (quickest): drag a folder with your files + an `index.html` into Netlify Drop to get a public URL.

## Log file

The game writes queue lines similar to:

- `Client is in connect queue at position: N`
- `Your position in the queue is: N`

This web app currently expects you to pick the log file directly (recommended). Folder picking only checks the top-level for `client-main.log` / `client.log`.

## Features

### Window layout

- One-page dashboard: KPIs + graph + info + settings + history.

### Picking the log

- **Pick log file…** is required for **live tail**.
- **Pick folder…** is optional and may be hidden/unsupported depending on your browser context.

### Monitoring

- **Play / Stop** toggles tailing the log on an interval (**poll**, configurable in Settings).
- On start, the app can **seed the graph** from a larger tail of the log (with a loading indicator) so you see recent queue history immediately.
- **Elapsed** time is anchored to the log: it uses the first **connecting / connection attempt** line in the current queue session when that line appears in the scanned log, otherwise the first **queue position** line in the graph. Reaching the **front** (position ≤1) freezes elapsed using **log line timestamps**, not the moment you opened the monitor.
- **Timer (~10 Hz)** refreshes elapsed time, remaining ETA, and rate between log polls so values feel live.

### Graph pane (top)

- **KPI strip (one header row, one value row):** **Position** (queue index from the log, or **0** when a post-queue line shows you are **not** still waiting in queue — e.g. loading mods), **Status** (connection/monitoring state — not the Info panel name), **Rate** (column title **`RATE (Rolling N)`** — **N** comes from **Settings → Estimation → Rolling window (points)**; the value row is just minutes per position, e.g. `6.20 min/pos`), **Warnings** (configured threshold numbers; each value appears muted once your position is at or below that threshold, or after that alert fired), **Elapsed**, **EST. REMAINING** (ETA), **Progress** (thin bar: share of estimated total wait elapsed; **100%** at **position 0**).
- **Chart:** step plot of queue position vs time (**0** = past queue wait); hover near the line for timestamp and position.
- **Y → log / Y → linear** toggles **log-scale** vs **linear** vertical axis (helps when position spans a wide range).
- Graph preferences persist (see **Configuration file**).

### Info pane (collapsible)

- Click the **Info** header bar or chevron to expand or collapse details.
- When expanded, pane height fits **full content** (path, labels, wrapping text).
- Shows **Last change**, **Last threshold alert**, **Resolved log path**, and **Global Rate** — average minutes per position over every forward queue step in the **full** graph (all segments), distinct from the KPI **Rate** line which uses the rolling window from **Estimation** and dwell caps.

### History pane (collapsible)

- Click **History** to show or hide the scrollable session log.
- Logs path changes, optional **queue position lines** (only when **Log every position change** is on), alerts, seed messages, errors, and warnings.

### Alerts

- **Warning thresholds** — comma-separated positions (default `10, 5, 1`): a warning can fire when you **cross downward** through each value (once per value per queue run).
- **Completion** — **not threshold-based**: it fires when the log tail shows a **post-queue** line **after** the last queue position line. This maps the UI position to **0** (Completed) and is the trigger for the completion popup/sound.
- **Browser notifications**: optional; click **Enable notifications** and allow permission. Sounds are simple built-in beeps (browser-safe).

### ETA, rate, and progress

- **EST. REMAINING** uses position and a **speed model**: empirical throughput from recent log updates when possible, otherwise a **recency-weighted** estimate from the **rolling window** (points under **Estimation**). At **position 1** (at the front) it still shows an ETA by treating **one** remaining step to connecting; it is only an estimate — the log may repeat **1** for a long time.
- **Minutes per position** for the rolling window appears in the **Rate** value row; the column header shows **`RATE (Rolling N)`** (**N** = **Rolling window (points)** under **Estimation** in Settings — same idea as a “last N” average). The full-graph average stays under **Info → Global Rate**. Dwell caps apply to the windowed KPI value. At **position 0** (queue finished), **Rate** and **Global Rate** stay fixed — derived from log timestamps only, not a clock that keeps running after you finish.
- **Progress** bar uses elapsed ÷ (elapsed + estimated remaining) when both are known; caps below **100%** while at **position 1** (at front) until the log shows past-queue-wait activity; **100%** once **position 0** is shown; empty when interrupted or ETA unknown.
- **Stale queue detection:** if no new queue lines arrive for too long relative to the expected update cadence, the run can be treated as **Interrupted**.

### Connection and status line

The status string reflects tail-of-log classification, for example:

- **Monitoring** — queue line present, in queue (`position > 1`).
- **At front** — log still shows **position 1** and the tail does not yet show a post-queue line after it (you may still wait a long time).
- **Completed** — **position 0**: a post-queue line appeared after the last queue line (connecting / loading — not only fully connected); KPI shows **0**.
- **Interrupted** — definitive disconnect / stale queue; **elapsed time freezes** but the log **keeps** being read.
- **Reconnecting…** / **Connecting…** / **Waiting for log file** / **Error** as appropriate.
- **Log silence:** no file growth for a long interval can show reconnect-style status (with guards so **At front** (1) / **Completed** (0) is not clobbered when appropriate).

### New queue after interrupt

- If a **new queue run** appears in the log while in **Interrupted**, a dialog can offer to **load** it and **re-seed** the graph and alert state for that run.

### Settings (gear)

- **Polling** — **Poll (s)** between log reads.
- **Warning Alerts** — comma-separated **thresholds**, **Warning popup** / **Warning sound** / **Warning sound file**.
- **Completion Alerts** — **on/off only** when the log shows past-queue-wait lines (no threshold list); **Completion popup**, **Completion sound**, **Completion sound file**.
- **History** — **Log every position change**: when **off**, routine queue steps are **not** written to History (alerts, completion, start/stop, and errors still are). Show or hide the panel from the main window **History** bar (still saved in config).
- **Estimation** — **Rolling window (points)**: how many recent queue steps to use for rolling rate and ETA.
- **Reset defaults** — restores built-in defaults and clears local session state tied to that flow.
- **Close** or **Escape** saves config (same debounced persistence as the rest of the app).

### Keyboard shortcuts

- **Space** — start/stop monitoring (ignored when typing in a text field).
- **Ctrl+M** — start/stop monitoring.

### Command-line interface

| Argument | Meaning |
|----------|---------|
| `--path PATH` | Initial **Logs folder** path (directory; same rules as the main window field). |
| `--no-start` | Open the UI **without** auto-starting monitoring. |

### Tooltips

- Most controls on the main window have **hover tooltips** (short explanations).

## Settings storage

Settings are saved in your browser’s **`localStorage`** under the key `vsqm_web_config_v1`.

## License / game

This project is an independent tool for reading **your** client log. It is not affiliated with Vintage Story or its authors.
