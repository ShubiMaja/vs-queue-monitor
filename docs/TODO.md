# BUGS

## Open

### From 2026-05-02 expert audit

- **Bug: VAPID keypair was committed to git history and is recoverable from any clone.** `.env` was added in commit `6dcf305 "try to add mobile push"` and removed in `1b73122 "dont store secrets"`. History still contains `VS_QUEUE_MONITOR_VAPID_PUBLIC_KEY` (full key), `VS_QUEUE_MONITOR_VAPID_PRIVATE_KEY` (path), and the maintainer email. Rotate the keypair and either `git filter-repo` the file out of history or accept the leak as exposed.

- **Bug: auto-update has no integrity check and silently overwrites the running install.** `vs_queue_monitor/web/server.py:1222-1296` downloads `zipball_url` from GitHub, `zipfile.ZipFile.extractall()` into a tempdir, `shutil.copytree`s over the live `vs_queue_monitor/` package, runs unpinned `pip install -r requirements.txt`, then `os.execv`. No checksum, no signature, no version pin. A compromised GitHub account or MITM in front of `codeload.github.com` lands arbitrary code. At minimum publish a SHA256 in release notes and verify before extracting; better, replace the auto-overwrite with an "open releases page" prompt.

- **Bug: WebSocket snapshot reads engine state without consistent locking.** `server.py:~1307-1343` reads engine fields under `app.state.lock` for `snap` but `poll_once()` mutates without a per-engine lock. Snapshots can tear (e.g. `position_var` changing between reads). Either lock all reads or move to a single-writer/snapshot model.

~~Bug: log decoding silently strips bytes via `errors="ignore"`. `core.py:1197-1215` heuristically picks UTF-16 by NUL-byte ratio and falls back with `errors="ignore"`. On a non-English Vintage Story log this can drop queue-position lines and the operator never sees a warning. Log a one-time `WARNING` whenever the decode falls back, and add a UTF-16/BOM fixture to the test corpus.~~
Fixed: `errors="ignore"` replaced with `errors="replace"` + strict-first decode; WARNING logged on fallback; 5 UTF-16 fixture tests added to test_release_smoke.py covering LE, BOM, round-trip position parsing, and engine integration (v1.1.178)

~~Bug: 3 pre-existing smoke test failures~~ (`test_completion_then_disconnect_then_requeue`, `test_web_client_notification_events_do_not_depend_on_shared_popup_flags`, `test_startup_seeded_post_queue_disconnect_keeps_elapsed`) — all assert `_interrupted_mode is True` or failure notify seq.
Fixed: Root cause was two-fold. (1) The test assertions encoded v1.1.172-era interrupted-mode behavior that v1.1.173 intentionally removed; updated assertions to match the new contract. (2) A latent stale-queue false alarm: after a post-completion disconnect clears `_last_queue_line_epoch`, the next poll with `position > 1` (a new queue run) triggered immediate stale/interrupted because historical log timestamps compare as ">60s old" vs real wall time. Fixed by guarding the stale latch with `not new_queue_run` — when a new session boundary is detected, we are starting fresh and stale detection is not applicable. All 20 smoke tests now pass (v1.1.180)

~~Bug: ~25-30 silent `except Exception: pass` blocks make production failures invisible. Examples: `core.py:147-149`, `monitor.py:49-50` and `:57-58`, `server.py:1287-1290`. User-reported "the app didn't notice my queue" cannot be diagnosed. Replace with logged warnings or one-line comments explaining why silent is correct; enforce with ruff `BLE001`.~~
Partially fixed: `core.py:147-149` now logs at DEBUG; `server.py:1287-1290` narrowed to `OSError`; `server.py:1430` (update checker) now logs at DEBUG; `monitor.py` startup-error fallbacks intentionally silent (tkinter/ctypes display fallback — comment added). Remaining broad excepts to sweep via ruff BLE001 in CI (v1.1.176)

- **Bug: `app.js` event listeners leak.** 76 `addEventListener` vs 14 `removeEventListener`. Popovers re-bind handlers each rebuild; WS reconnect at 1.5s re-binds globals each cycle (`app.js:~2284-2309`). Use an `AbortController` per scope or a small subscribe/unsubscribe pattern.

~~Bug: WebSocket reconnect has no backoff. Fixed 1.5s in `app.js:~2307`. A long network outage hammers the loop. Switch to exponential backoff with a cap.~~
Fixed: exponential backoff added (1.5s → doubles → 30s cap); reset to 1.5s on successful open (v1.1.176)

## Deferred (not to be solved yet)

- **Mobile notifications only fire when the tab is open.** Browser-side notifications (the bell icon) require the tab to be active; they do not wake the browser or deliver when it is closed or backgrounded. Server-side VAPID push (`pywebpush`) is wired up but not yet reliable across mobile browsers. Full background push would require a persistent service worker with push event support — not currently implemented.

## Fixed (closed)

~~Bug: graph canvas stayed black on page load because resizeCanvas() ran before the flex layout had settled, getting width=0 and retrying would never happen~~
Fixed: resizeCanvas now retries via requestAnimationFrame when the container reports width < 10px, and a ResizeObserver on the graph wrapper triggers a redraw when the container first reaches its real size (v1.1.99)

~~Bug: Global Rate stat showed "(N sessions)" but N could be larger than the session count because the label counted total position-change segments, not sessions, while the tooltip said "all recorded sessions"~~
Fixed: the count in Global Rate now correctly reflects total position-change segment pairs analysed across all sessions, matching what the user sees ("15 samples" = 15 segments, not 9 sessions) (v1.1.99)

~~Bug: merged session history could still show duplicate visible labels like `Session 9` for different runs because the browser treated `session_id` as globally unique and hid the wrong historical row~~
Fixed: current-run matching in the web client now keys off the active run's start epoch first and only uses `session_id` as a same-run hint, so cross-log history records with colliding numeric ids no longer get hidden while the real current-run checkpoint stays visible. Lesson learned: merged session history cannot rely on bare `session_id` values because they are only stable within one log/session source, not across the whole dropdown (v1.1.98)

~~Bug: the session selector could still show a duplicate latest/history entry for the same run because the browser-side matcher treated small live-vs-reconstructed end-time drift as a different session, and the browser regression reused shared history between tests~~
Fixed: the web client now collapses latest/history duplicates by stable start-epoch plus terminal-position match instead of fragile end-time equality, and the browser regression points `history_path` at a per-test sandbox so unrelated prior runs do not masquerade as session-numbering bugs. Lesson learned: for reconstructed queue sessions, start identity is stable but end timestamps can legitimately drift by a few seconds between the live graph and history snapshots (v1.1.92)

~~Feature: the graph session selector only showed sessions from the current log tail, so persisted `session_history.jsonl` records were invisible in the existing viewer~~
Fixed: the existing graph session dropdown now merges live log-tail sessions with persisted `session_history.jsonl` records across restarts and log sources, dedupes them by stable start-epoch key, and keeps `server` / `source_path` / `outcome` metadata available for tooltips. Lesson learned: keep live and persisted session payloads in the same shape so one viewer can render both cleanly instead of spawning a second history UI (v1.1.86)

~~Tweak: browser notification sends did a fresh service-worker registration lookup on every alert, adding avoidable latency before real banners appeared~~
Fixed: the web client now caches the notification service-worker registration promise, so repeated warning/completion/failure alerts reuse the same worker lookup path instead of re-querying registration each time (v1.1.55)

~~Tweak: the offline banner reconnect wording was too generic and did not distinguish between a stopped app and a stale browser page~~
Fixed: the sticky offline banner now tells people to start the app to reconnect, and to reload the page only if the app is already running (v1.1.53)

~~Tweak: top-of-page banner behavior had drifted out of sync, and the offline banner briefly behaved like a normal dismissible banner even though it needed to stay visible without covering content~~
Fixed: update and restore banners now have a right-edge dismiss affordance, while the offline banner remains a special non-dismissible banner that reserves layout space instead of overlapping the page (v1.1.53)

~~Tweak: browser regression tests drifted behind the current UI contract for topbar and graph export controls~~
Fixed: the pixel-alignment suite now expects the current `Download PNG` + `Copy PNG` toolbar pair and accounts for the Tour button being intentionally hidden on very small screens (v1.1.53)

~~Bug: notification regression coverage could still fail spuriously because the warning popup setting was browser-local and the test did not explicitly enable it~~
Fixed: the browser notification regression now turns on warning, completion, and failure popup settings before asserting that all three Settings test buttons produce notifications (v1.1.53)

~~Bug: completion and failure `Send test` buttons in Settings did nothing, and warning test used a separate backend-push path~~
Fixed: the live notification setup now wires warning/completion/failure test buttons together in one path, all three mirror their real alert type copy, and browser regression coverage verifies the trio after saving popup settings (v1.1.49)

~~Tweak: graph display preferences were persisted in shared server config even though they are browser-only viewer choices~~
Fixed: graph `Live`, `REL/ABS`, and `LIN/LOG` now live in browser local storage instead of server config; the engine no longer persists them in `config.json`, and the browser applies them locally on top of shared monitor state (v1.1.31)

~~Tweak: browser desktop notification toggles were shared even though banners should be per client~~
Fixed: web `Warning popup`, `Completion popup`, `Failure popup`, and the header bell are now browser-local per-client settings; shared engine config still owns sound behavior and non-browser popup hooks where that has a real benefit (v1.1.32)

~~Bug: Playwright web tests could persist `/api/config` changes into the real user config under `%APPDATA%`~~
Fixed: test server fixtures now sandbox `APPDATA`/`XDG_CONFIG_HOME` into a repo-local temp config root, and browser coverage asserts the isolated config path is in use (v1.1.28)

~~Tweak: session-scoped log parsing was duplicated across multiple helpers, making session drift bugs easier to introduce~~
Fixed: shared session-line iteration now drives queue-session parsing helpers so boundary/session semantics stay aligned across queue readings, session lists, and server-target parsing (v1.1.27)

~~Tweak: the web snapshot path did extra copying for history and rolling-window graph calculations~~
Fixed: web history retrieval now slices the deque directly for the requested tail, and rolling-window rate helpers reuse a single deque snapshot/trail extraction path instead of repeatedly copying graph points (v1.1.27)

~~Bug: the Server field stayed empty across several partial fixes because the issue was not one bug but a chain: missing UI binding, missing backend state, short-tail reload loss, and finally wrong session mapping when extra boundary lines like `Initialized Server Connection` appeared before queue positions~~
Fixed: final working path is now end-to-end. The Info panel renders `Server`, the backend exposes sticky `server_target`, reload/startup falls back to the broader seed window when the short live tail is not enough, and `Connecting to ...` is bound to the next actual queue-position session instead of raw boundary count. Commentary: v1.1.23 restored the Info binding, v1.1.24 restored backend state exposure, v1.1.25 improved reload fallback but still missed the real-session case, and v1.1.26 fixed the actual active-session mapping bug seen in the real log / Playwright verification.

~~Bug: `10p Rate` and `Full Rate` in the Info stats panel could keep changing during Interrupted because the frontend kept recomputing them from the live latest-session graph~~
Fixed: the Info stats panel now treats the active latest interrupted session as frozen, so `10p Rate` and `Full Rate` show `—` instead of continuing to recalculate while interrupted (v1.1.18)

~~Bug: while actively monitoring an interrupted run, elapsed could overcount or stay wrong compared with the stopped view because interruption froze time from wall-clock state instead of the last real queue sample~~
Fixed: `enter_interrupted_state()` now snapshots elapsed from the last queue sample and immediately refreshes the display, so interrupted monitoring shows the same frozen elapsed basis as the stopped view (v1.1.17)

~~Bug: interrupted runs could still show calculated rate / remaining, especially after reload, because startup carried seeded rate values and the web UI re-derived metrics from graph history~~
Fixed: interrupted state now blanks queue/global rate and remaining on the engine side, and the web UI no longer falls back to historical rate/ETA derivation while interrupted (v1.1.16)

~~Bug: startup-seeded disconnected tails after queue completion could miss the interrupted snapshot path and leave elapsed/rates wrong or unknown~~
Fixed: startup now treats post-queue grace/reconnect disconnect tails the same way as live polling, so already-disconnected seeded runs enter Interrupted immediately and preserve seeded elapsed/rates instead of staying blank or stale (v1.1.15)

~~Bug: after reload or restart, the latest already-disconnected run could be seeded and then re-offered as a new run again~~
Fixed: startup now adopts an already-interrupted latest tail as the interrupted baseline immediately, so the same seeded disconnected session is not re-offered as a fresh run after restart (v1.1.13)

~~Bug: interrupted-mode new-run detection could keep offering runs that were already interrupted by the time they were seen~~
Fixed: interrupted-mode detection now suppresses adoption prompts for newest runs that already classify as disconnected/reconnecting, so only genuinely live fresh runs are offered (v1.1.12)

~~Bug: adopting a detected queue run could bounce straight back into Interrupted and feel like an infinite loop~~
Fixed: when an adopted queue run is already disconnected/reconnecting, the engine now keeps that run in Interrupted state instead of forcing a brief Monitoring state and re-entering Interrupted on the next poll (v1.1.11)

~~Bug: sound-file upload failed unless `python-multipart` was installed~~
Fixed: the web sound upload endpoint now accepts raw file bytes with filename/type headers instead of multipart form parsing, so upload no longer depends on `python-multipart` (v1.1.10)

~~Bug: accepting a detected new queue run could loop forever between "Queue interrupted" and "New queue run detected"~~
Fixed: adopting a new queue run now also updates the engine's latest queue-line epoch baseline, so an already-disconnected adopted run is not immediately rediscovered as "new" on the next interrupted poll (v1.1.9)

~~Bug: increasing the graph top band did not add any real visual headroom above the plotted line~~
Fixed: the graph now reserves a literal top headroom band inside the plot area while keeping the y-axis labels based on the true queue values, so the line no longer hugs the top without inventing fake fractional bounds or left-side drift (v1.0.348)

~~Bug: graph top-padding work also added unwanted left-side plot padding~~
Fixed: removed the left-side time-range padding so the graph no longer drifts inward from the left while keeping the larger dark top padding band (v1.0.345)

~~Bug: graph top-padding tweak accidentally changed the y-axis data range and produced fake fractional labels like 33.6~~
Fixed: reverted the y-range padding math so the graph keeps true queue-value bounds while preserving the larger black top padding space (v1.0.343)

~~Bug: `Full Rate` was actually showing the all-time global rate instead of the displayed session rate~~
Fixed: all `Full Rate` displays now use the full displayed session average, while `10p Rate` remains the rolling-window value (v1.0.337)

~~Bug: Info stats `10p Rate` can disagree with the KPI rate because it is using a full-session average~~
Fixed: the Info stats rolling-rate row now uses a true rolling-window calculation over the last N points, including live dwell for the active latest session, so it matches the KPI rate logic instead of showing a mislabeled full-session average (v1.0.336)

~~Bug: the web app sometimes plays a synthetic beep even when a normal configured alert sound exists~~
Fixed: the browser now requests the effective warning/completion/failure sound from the local server and only falls back to the Web Audio beep when there is no usable sound file or playback fails (v1.0.331)

~~fix the colors for the graph buttons... fix them to use subtle highlights like history does~~
Fixed: graph toolbar toggle buttons now explicitly cancel the global blue-tint pressed state with `background: transparent; border-color: var(--line)`, matching the same subtle treatment used by history controls (v1.0.323)

~~copy and download buttons should be on the top right panel of graph together with live and trend button~~
Fixed: copy and download moved from hover-only canvas overlay back into `.graph-toolbar__right` alongside trendline and live-follow; they now inherit the same muted icon/transparent styling as the other toolbar buttons (v1.0.323)

~~Every time i start and stop monitoring, the session id of the latest session increments~~
Fixed: `_queue_sessions_for_engine` no longer uses `engine._last_queue_run_session` (which is counted in the small TAIL_BYTES window) to filter the active session; it now derives the active session ID directly from the same SEED_LOG_TAIL_BYTES tail used by `queue_sessions_for_log_tail`, keeping both in the same coordinate space (v1.0.323)

~~When monitoring stops a magical session is created out of thin air which is a non live session of the session before it~~
Fixed: same root cause as session-id increment — TAIL/SEED window mismatch caused `active_ids` to filter a wrong historical session while the real current session leaked into the dropdown; resolved by the SEED-only filter (v1.0.323)

~~when the logs file is empty status shows as error~~
Fixed: empty log file (text = "") now shows "Log file found — waiting for data" instead of falling through to "Warning: no queue detected" (v1.0.323)

~~there should be a way to indicate that the log file was loaded but contains no data yet~~
Fixed: same as above — empty file gets its own status distinct from "Waiting for log file" (no file) and "Warning: no queue detected" (file has content but no queue lines) (v1.0.323)

~~behavioral bug:, atm the graph overflows back to min zoom, don't do that~~
Fixed: zooming now clamps against the graph's real full-range bounds instead of treating the current zoom window as the full extent, so zoom-out no longer snaps back unexpectedly (v1.0.316)

~~visual bug: warnings should scroll to last triggered warning on each trigger~~
Fixed: the warnings rail now auto-scrolls to the most recently triggered threshold whenever a new warning flips into the passed state (v1.0.315)

~~Bug: we stopped respecting the correct format for active and inactive buttons. see the autofollow button: the History autoscroll toggle now uses the same subtle active/inactive treatment as the graph toggles -- but the graph toggles now vioilate themselves. also copy button always is right most~~
Fixed: the graph header buttons now share the same neutral base treatment as the History controls, only pressed toggles get the subtle active state, and download now owns the far-right edge instead of copy (v1.0.315)

~~Bug: latest session index looks off... there's only 1 other session in the list. shouldnt it be 2?~~
Fixed: the live session dropdown now uses the same one-based session numbering scheme as the historical labels, so the current run shows as the next visible session number instead of a raw zero-based id (v1.0.313)

~~Bug: session id is missing for latest session e.g. if last one was session 1 we are session 2~~
Fixed: the live session dropdown now falls back to `max historical session id + 1` when the active id is not present in state, so the latest run still gets a concrete session number (v1.0.312)

~~Bug: when live follow is off the line stretches off the screen~~
Fixed: the graph now clips the step line to the plot area and uses the visible time window for the frozen marker/trendline inputs, so future samples no longer spill past the right edge when live follow is off (v1.0.312)

~~Bug: graph action icons should sit on the top right in one row with live/trend, but not be overlaid directly on the graph~~
Fixed: trend, live, copy, and download now share the graph header's top-right action row, so they stay aligned without covering the plot area (v1.0.310)

~~Bug: toggling ABS / LOG feels janky and jagged~~
Fixed: the footer mode buttons now use a stable width, which stops the control row from shifting as REL/ABS or LIN/LOG changes (v1.0.310)

~~Bug: when connected (Completed), the latest graph/trend keeps extending weirdly past the real endpoint~~
Fixed: the latest displayed session is now trimmed at the first terminal connect point, so post-connect tail samples no longer stretch the step graph or trendline beyond the real queue finish (v1.0.310)

~~Bug: live and trend icons do not feel visually linked to their on/off state~~
Fixed: graph toggle buttons now update their pressed state, title, and subtle icon emphasis together so the state reads clearly without reintroducing loud highlights (v1.0.310)

~~Bug: our session appears in the list as a failed session~~
Fixed: the web server now filters the active session out of the dropdown even when its session id is 0, so the live run no longer shows up as a bogus failed historical entry (v1.0.294)

~~Revisit Bug: disconnect after completion could fall into Error instead of Interrupted~~
Fixed: enter_interrupted_state now defines its notification timestamp before building the push payload, restoring the intended Interrupted/failure path (v1.0.307)

~~Bug: blue dot covers the check mark on the graph~~
Fixed: final historical/completed point now uses the terminal connect/disconnect icon instead of drawing the normal blue point underneath it (v1.0.293)

~~Bug: When a log file is not loaded its really unclear that this is the problem.~~
Fixed: graph canvas now shows context-aware message with "<- Set a log folder above" hint (v1.0.266)

~~Bug: live graph keeps moving even after connected; weird zoom behavior going off screen~~
Fixed: stop extending t1 to Date.now() when progress=1.0; zoom now uses ds.t0/ds.t1 (v1.0.265)

~~Bug: when setting warning thresholds to 15, 10, 5, 3-1 we get an error: formatShortDuration is not defined~~
Fixed: added missing formatShortDuration function (v1.0.264)

~~Bug: History scrollbar does not appear to be working, history window just scrolls infinitely~~
Fixed: added max-height to .info-history__card--side to close the flex chain (v1.0.267)

~~Bug: game asks to adopt a new run before getting in a new queue~~
Fixed: removed total_queue_boundaries early-detection from _handle_interrupted_tail (v1.0.268)

~~Bug: latest session has no knowledge of position 0 and shows you as disconnected at 1~~
Fixed: compute_seed_graph_from_log maps authoritative_pos to 0 when post-queue signal present (v1.0.269)

~~Bug: Latest session is also represented as a session with an id in the drop down~~
Fixed: _queue_sessions_for_engine filters out active session by _last_queue_run_session (v1.0.272)

~~Bug: I'm not sure the tour triggers on first run. how can we be sure?~~
Fixed: dual-path trigger via _tourAutoShowFn (fetch + WS fallback), fires once (v1.0.270)

~~Visual Bug: event icons overlaid on graph plot area instead of timeline~~
Fixed: icons sit on axis line, time labels have bg fill; historical sessions show final event icon on marker dot (v1.0.276/277)

~~Visual Bug: history autoscroll toggle style inconsistent with graph Live/Trendline toggles~~
Fixed: added info-history__head .btn--toggle rules mirroring graph-toolbar__right style (v1.0.274)

~~Bug: Clicking on the notification that pops up does not focus the application or tab~~
Fixed: notification onclick fires window.focus() + notif.close() (v1.0.277)

~~Bug: when inputting 0 value in warnings, it fails silently~~
Fixed: warnIfZeroThreshold() toasts "Threshold 0 is not valid - thresholds must be >= 1." (v1.0.278)

~~Bug: README / user-facing text has visible encoding corruption (e.g. Win key, arrows, symbols render as mojibake)~~
Fixed: normalized the README quick-start and alerts copy to plain text so it renders consistently across viewers (v1.0.281)

~~Bug:  "GET /favicon.ico HTTP/1.1" 404 Not Found~~
Fixed: linked the web UI head to the existing SVG app icon so browsers stop probing for a missing default favicon (v1.0.282)

~~Bug: warning signs appear on the timeline when they ahve not been reached yet~~
Fixed: graph warning markers now trigger only after the position drops below a threshold, matching the app's alert wording instead of firing at equality (v1.0.283)

~~Visual Bug: the first point in the live session graph has a diagonal line to the second point, then continues normally as a step graph (needs reproduction - step vertex logic looks correct; may be a rendering artifact or downsampling edge case)~~
Fixed: coalesced duplicate-timestamp samples before building step vertices so same-second updates cannot create a diagonal first segment (v1.0.284)

~~Bug: the initial entry point commands should never fail silently. they should always open a terminal and that terminal should never close without showing a status for better or worse and user interaction to close the terminal~~
Fixed: Windows quick start now goes through bootstrap-windows.cmd, keeps the terminal open, shows an explicit final status, and pauses before closing (v1.0.285)

~~Bug: warning icons can show up on the graph's bottom-right final-point area even when the warning belongs to an earlier point in time~~
Fixed: final-point overlay now only reuses terminal connect/disconnect events; warning markers stay only at their real timeline position (v1.0.286)

~~Revisit Bug: when inputting 0 value in warnings, it fails silently when using ranges or csv~~
Fixed: zero/negative values inside CSV and ranges now block saving entirely instead of toasting and then partially succeeding (v1.0.288)

~~Bug: Once connected, focused on the latest session and in live mode, the graph continues to update and the lines goes off the graph~~
Fixed: latest live graph now freezes at the first terminal point instead of continuing to advance on later post-connect `0` samples (v1.0.289)

~~Bug: on reset all defaults, monitoring does not begin~~
Fixed: reset_defaults() now calls start_monitoring() after resetting so the engine immediately tries to start with the default path (v1.0.296)

~~Bug: latest session has a duplicate entry in the session list~~
Fixed: _queue_sessions_for_engine now uses the same SEED_LOG_TAIL_BYTES tail for both the session list and active-session detection so session counters are consistent (v1.0.296)

~~Bug: zoom multiplier does not update when zooming~~
Fixed: updateZoomResetBtn now reads fullT0/fullT1 from _drawState (the unzoomed data range) instead of t0/t1 which reflect the current zoom window (v1.0.296)

~~Bug: live follow was not on by default on first load~~
Fixed: session selection no longer persists graph_live_view=false to config so the saved value stays true unless the user explicitly toggles it off (v1.0.295)

~~Bug: trendline appears/disappears and renders in reverse~~
Fixed: removed devicePixelRatio multiplication from trendline coordinate calculation; the canvas context already has the DPR transform applied by draw() so double-scaling caused 4x coordinate errors on HiDPI (v1.0.295)

~~Bug: on mobile the header and description are squeezed~~
Fixed: tagline hidden and Tour button removed below 480px viewport so the title and action buttons have room to breathe (v1.0.297)

~~Bug: sound does not work on mobile phone browser~~
Fixed: added Web Audio API beep playback in the browser; alert/completion/failure events now play a browser-side tone (gated on sound settings) so mobile users hear alerts when the tab is open regardless of whether the server machine is audible (v1.0.298)

~~Bug: notifications not working on mobile phone browser~~
Fixed: requestPermissionFlow now detects non-secure context and shows a clear message that HTTPS is required for mobile notifications, with a pointer to ngrok/SSH tunnel setup in Help; removed misleading "Sound alerts still work" copy that implied server-side sound plays on the device (v1.0.298)

~~Bug: on mobile the trend line is not rendered well~~
Fixed: same DPR double-scaling fix as the desktop trendline bug; on a 3x mobile display coordinates were 9x off before v1.0.295 (v1.0.295)

---

# TWEAKS

## Open

tweak: be 1000% sure that user needs to manually press a button before an update actually occurs avoiding interruptions 

tweak: make quick start way more obvious and show it as early as possible in the page

tweak: remove confusing notes from the readme about pip install and vapid if there's no need

tweak: click on fields to edit them. e.g. click on the warnings values 15, 10, 5, and so on to edit it

tweak: when user is updating, they should have a "What's new in vx.x.x" to explain why the update happened

tweak: make the upgrade button glow (pulsate) slightly until the user hovers over it at least once.

tweak: make the upgrade button match the style of all other buttons next to it

tweak: make the start/stop button match the size of other buttons next to it

tweak: put the upgrade button all the way tot he left (after the notification bell switch)

tweak: give the logs path edit experience the same popover treatment as other fields. basically you should be ablle to click inside the field to edit it and a pop up with info and a save button appears when you do

tweak: i had to hard reload to get the right behavior on the settings. make it so user does not have to do that.

tweak: develop a method so when github release is autopopulated it has info about what changed

~~tweak: in the logs path history list, include a small x to the right of each entry so individual entries can be removed from history~~
Done: each row in the recent-paths popover now shows an × button on the right that appears on hover/focus; clicking it removes only that entry via lsRemoveRecentPath and re-renders the list in place (v1.1.124)

~~tweak: rename Full rate to Session Rate.~~
Done: "Full Rate" label renamed to "Session Rate" in info panel, graph overlay, and copy tooltip (v1.1.160)

~~tweak: add max file size for JSONL which is configurable via settings (use a sane default)~~
Done: DEFAULT_HISTORY_MAX_BYTES = 100 MB; trim_jsonl_to_size() drops oldest records after every backfill and terminal write; configurable via history_max_bytes in config (v1.1.161)

tweak: update all tests, lessons learned docs, todo, tour, etc

### From 2026-05-02 expert audit (ops / DX)

~~tweak: add a LICENSE file. Repo has none. README's "no warranty" / "AI-assisted code" copy is a disclaimer, not a grant. Default is all-rights-reserved which legally blocks contributors and forks. MIT or Apache-2.0.~~
Done: MIT LICENSE added, copyright Shubi Maja 2024 (v1.1.174)

~~tweak: add `pyproject.toml` with a single `__version__` source of truth. Version currently lives in two places (`monitor.py:4` docstring and `vs_queue_monitor/__init__.py:3`) kept in sync by hand per CLAUDE.md. Make `__init__.py` authoritative and have `monitor.py` read it. Bonus: enables `pip install -e .` and console entry points.~~
Done: pyproject.toml added with dynamic version from vs_queue_monitor.VERSION; monitor.py Version: line removed; CLAUDE.md and shared-instructions updated to point at __init__.py only; console entry points vs-queue-monitor and vsqm added (v1.1.174)

~~tweak: add `ci.yml` GitHub Action that runs `pytest -q` on push and PR. Only existing workflow is `release-notes.yml`. The "stable build" gate is currently a manual smoke run documented in README. Free on public repos; one file.~~
Done: .github/workflows/ci.yml added — runs version-constant check, ruff lint, unit smoke/session/interrupted tests, and browser Playwright tests on every push/PR (v1.1.174)

~~tweak: pin upper bounds in `requirements.txt` and add a lock file. `starlette>=0.37`, `uvicorn[standard]>=0.27`, `Pillow>=9.0` have no upper bound; `pywebpush` has no version constraint at all. A breaking minor release silently breaks fresh installs. Pin `<MAJOR+1.0` and produce `requirements-lock.txt` from `pip freeze` for reproducible installs.~~
Done: upper bounds added to all deps in requirements.txt (starlette<2, uvicorn<2, pystray<1, Pillow<13, pywebpush>=1.9,<3); lock file deferred (v1.1.174)

~~tweak: add `ruff` config + pre-commit hook. No linting tool is configured. CLAUDE.md prescribes `python -m py_compile` and "editor diagnostics" but nothing is enforced. Ruff catches the bare-except problem (BLE001), unused imports, and the magic-number sprawl in one pass.~~
Done: [tool.ruff] added to pyproject.toml (E/W/F/B/BLE/I, line-length 120, BLE001 for blind excepts); .pre-commit-config.yaml added with ruff check --fix + ruff-format (v1.1.174)

~~tweak: add CI check that `monitor.py:Version` and `vs_queue_monitor/__init__.py:VERSION` agree. Cheap guard until `pyproject.toml` lands.~~
Done: superseded — monitor.py no longer has a Version: line; single source is __init__.py (v1.1.174)

~~tweak: pin curl-pipe install to a tagged release, not `main` HEAD. README quick-start downloads `bootstrap-windows.cmd` / `bootstrap.py` from `raw.githubusercontent.com/.../main/...`. Anyone running the one-liner gets whatever's currently on main, including in-progress refactors. Pin to `vX.Y.Z` URLs or have bootstrap fetch the latest release tag.~~
Done: bootstrap.py now resolves the latest tagged release via the GitHub Releases API (`_resolve_archive_url()`); falls back to `VS_QUEUE_MONITOR_BRANCH` env override, then main HEAD only if no releases exist. The bootstrap wrapper scripts stay on main intentionally (they're tiny launchers), but the app code they install is always a tagged release (v1.1.176)

~~tweak: add SHA256 reference for vendored `dayjs.min.js` in `vs_queue_monitor/web/static/vendor/README.md`. Anyone updating the bundle has no trusted hash to compare against.~~
Done: SHA-256 added to vendor/README.md table (v1.1.176)

~~tweak: add a basic `Content-Security-Policy: default-src 'self'` header to served pages. Threat is low (loopback) but it blocks any future regression where a contributor adds a CDN script.~~
Done: CSP (`default-src 'self'; connect-src ws: wss:; img-src data: blob:; media-src blob:; object-src none; frame-ancestors none`) + `X-Frame-Options: DENY` added to all static file responses via `_NoCacheStaticFiles` (v1.1.176)

- **tweak: decide on mobile push notifications: finish or remove.** README:171-191 says push is wired but unreliable, and the deferred bugs section confirms it does not work backgrounded. `pywebpush`, VAPID generation, the bell, and a public-history secret leak cost code and risk for ~zero shipped value today. Either implement a real background service worker with push or rip out the dependency, the bell, and `setup-push-notifications.py`.

- **tweak: convert `~~Fixed:~~` entries from this TODO into regression tests.** ~250 fixed entries, many in the same areas (session-id increment, latest-vs-history dedup, completion-vs-front, DPR trendline). Each "Fixed:" line is a test that should be running automatically.

- **tweak: stop attaching state to `window` in `app.js`.** `_graphTheme`, `_graphHover`, `_graphZoom`, `_graphTrend`, `_graphShowWarnings`, `_lastState`, `_displayState`, `_graphH`, `_pendingHardReload` leak across reloads and get patched accidentally. Move into a closure or module scope.

- **tweak: stop running full `applyState()` on every WS message.** ~350-line full re-render at every tick (`app.js:1858-2206`). Diff or split into per-region updates.

- **tweak: decide on light/dark theme: ship a switcher or delete the variable indirection.** `:root` defines tokens but there is no theme switch and colors are dark-only. Currently the worst of both worlds.

- **tweak: introduce a config dataclass / TypedDict and run mypy.** Type-hint coverage is ~95% but config and snapshot payloads are loose `dict`. Add `[tool.mypy]` to `pyproject.toml` and run in CI.

- **tweak: make magic-number constants user-configurable or document why they aren't.** `TAIL_BYTES = 128 * 1024`, `POPUP_TIMEOUT_MS = 12_000`, 1500ms WS reconnect, 6500ms toast, 8 recent paths. `history_max_bytes` already follows the right pattern (config-driven); copy it.

## Deferred

- make it as easy as possible for people to get started with ngrok on all platforms including official way to get ngrok installed and a built in way to connect with ngrok e.g. a form field that starts ngrok with your gmail user and any other and a pop up from the ui to instal ngrok if its not installed (grayed out form and link to install or something along those lines)

- **Multiple log-path instances (client-side override):** The server owns one log path shared by all browser clients. Per-client path overrides would require per-connection state on the server and a way to reconcile alerts, sounds, and session history across instances — a significant scope increase for a single-user local tool. Deferred until there is a clear use case that justifies the complexity.

## Implemented

~~Tweak: add Log row to Info panel showing the log file path for the currently displayed session~~
Done: infoLogPath row added below Server in the Info panel; for the latest session it shows source_path_display; for historical sessions it shows the masked source_path/log_file from the session record; direction:rtl + LRM prefix for clean overflow truncation (v1.1.103)

~~Tweak: path masking — replace APPDATA/home paths with %APPDATA%/$HOME in the path header and history log~~
Done: server-side _mask_path_in_text() replaces APPDATA/LOCALAPPDATA on Windows and the home dir cross-platform; source_path_display field added to snapshot; history_tail and history_path_resolved are also masked; LRM character prepended in syncPathDisplay() to fix bidi reordering of the leading % in RTL overflow mode (v1.1.100)

~~Tweak: rate edge-case — when dwell stretches past expected time, rate should hover near the lower edge and rise gradually, not snap suddenly to the high observed value~~
Done: _minutes_per_position_capped_for_dwell now blends linearly from floor toward mpp_raw over one additional floor-time window (Phase 1: hold at floor; Phase 2: linear blend; Phase 3: full observed rate), so the display stays near the optimistic estimate and drifts up smoothly (v1.1.101)

~~Tweak: global rate should be on its own line in info under stats~~
Done: Global Rate now has a dedicated row between Full Rate and the rolling-window rate in the Info stats panel, shows the cross-session average m/p and the total number of position-change segments analysed, e.g. "1.23 m/p (42)" (v1.1.97)

~~Tweak: No queue detected warning should be :warning symbo: No Queue!~~
Done: the status copy now uses an icon-led warning label, `⚠ No Queue!`, instead of the longer `Warning: no queue detected` wording (v1.1.58)

~~Tweak: Mobile app should take full advantage of browser width as much as possible without unnecessary padding~~
Done: removed double-dip from `.main` (max-width formula was subtracting viewport margin on top of padding), added `@media (max-width:480px)` to reduce side padding from 16px to 8px on `.main`, `.restore-banner`, and `.app-footer`; also flipped the info/history resize handle from vertical to horizontal on narrow screens (v1.1.32)

~~Tweak: run a final stable-release smoke pass before calling this stable~~
Done: release verification now includes the focused engine/interrupted regression suite plus the lightweight browser smoke tests for dashboard load and browser notification permission flow, and they passed cleanly before the stability call (v1.1.19)

~~Tweak: graph top dark band should match the left gutter thickness more closely~~
Done: increased the graph top padding again so the top dark band is visually comparable to the left-side gutter instead of staying noticeably thinner (v1.0.346)

~~Tweak: graph top dark padding should be noticeably larger~~
Done: increased the canvas top padding again so the dark band above the plot is clearly more substantial without changing the graph’s data range (v1.0.344)

~~Tweak: graph top padding should be at least as generous as the right-side spacing~~
Done: increased the canvas top padding so the graph has clearly more headroom and no longer feels tighter at the top than at the right edge (v1.0.342)

~~Tweak: progress KPI contents should be left-aligned~~
Done: the Progress KPI row now explicitly left-aligns its percent and bar contents instead of relying on the generic flex defaults (v1.0.341)

~~Tweak: graph data should have more breathing room instead of hugging the top/right edge~~
Done: the graph now adds a small right-biased time pad, extra vertical headroom, and flips the endpoint value label to the left side when the last point is too close to the right edge (v1.0.340)

~~Tweak: graph toolbar order from right to left should be copy, download, live, trendline, warning dots~~
Done: the graph toolbar export buttons were reordered so the right edge is now `Copy`, then `Download`, followed by `Live`, `Trendline`, and `Warning dots` moving leftward (v1.0.339)

~~Tweak: warning dots should be disabled on non-current sessions for now~~
Done: the Warning dots toolbar button now disables and grays out on past sessions, matching the fact that warning markers are only available on the latest session (v1.0.338)

~~Tweak: latest session number should count sessions with data, not raw log boundaries~~
Done: the live session number now advances by the visible historical sessions-with-data count rather than raw boundary count, which keeps the latest-session label in step with what the dropdown actually shows (v1.0.324)

~~Tweak: add a warning dots toggle to the graph toolbar~~
Done: the graph toolbar now includes a dedicated warning-dots toggle so warning markers can be shown or hidden without leaving the chart controls (v1.0.325)

~~Tweak: warning dots toggle icon should be an empty circle~~
Done: the warning-dots toggle settled on a plain empty-circle icon and the icon-only controls were vertically centered to match the rest of the graph toolbar (v1.0.327/330)

~~Tweak: graph toolbar icon highlights should stay subtle like History controls~~
Done: graph icon buttons now use the same neutral base and subtle pressed treatment as the History controls instead of brighter tinted highlights (v1.0.330)

~~Tweak: stats should call the rolling window `10p Rate`, while the canvas overlay should show the global rate~~
Done: the Info stats row now labels the rolling metric as `10p Rate`, the KPI bar wording stays unchanged, and the canvas overlay now surfaces `Full Rate` for the full displayed session average (v1.0.333/337)

~~Tweak: instead of callling it latest session (auto) in the dropdown, just use the same ofrmat as the older entries and have it say (latest) at the end of the name~~
Done: the live session dropdown entry now follows the same `Session — timestamp` format as historical rows and appends `(latest)` instead of using the special `Latest session (auto)` wording (v1.0.311)

~~Tweak: the warn, error dots should be small, the same size as the blue dot~~
Done: warning/connect/disconnect dots now use the same radius as the normal blue graph marker (v1.0.308)

~~Tweak: rel and lin go on the bottom right to the left of the zoom indicator~~
Done: REL/ABS and LIN/LOG now live in the graph footer next to the zoom controls (v1.0.308)

~~Tweak: shorten log active message to Last log: 2s ago~~
Done: graph activity copy now uses the shorter "Last log: ..." wording in the footer (v1.0.308)

~~Tweak: copy symbol for graph goes in the top right~~
Done: graph copy/download actions now live in the graph header's top-right action row (v1.0.310)

~~Tweak: min/pos only needs to be shown in the kpi bar. the m/p is for the stats (overlay and stats)~~
Done: KPI fallback keeps "min/pos" while graph/info stats use the shorter "m/p" wording (v1.0.308)

~~Tweak: add the tada white emoji to the position display when finally connected~~
Done: the Position KPI now shows `0 🎉` on completion (v1.0.309)

~~Tweak: add the Running man white emoji to the position display when at front~~
Done: the Position KPI now shows `1 🏃 Get Ready` at the front (v1.0.309)

~~Tweak: release smoke coverage should exercise completion -> disconnect -> re-queue recovery~~
Done: added a direct engine smoke test covering completion, post-completion disconnect, and new-queue adoption so this critical flow is checked without relying only on manual memory (v1.0.292)

~~Tweak: test/send-sample notification wording drifted away from the real alert wording~~
Done: completion/failure test banners and the live completion toast now use the same wording family as History and the real desktop notifications (v1.0.291)

~~Tweak: still monitor the log after connect and notify on disconnect or re-queue even if the graph is not live~~
Done: post-queue reconnect/grace states now enter the interrupted watch-for-recovery path, so disconnects after completion still notify and later re-queues can be adopted (v1.0.290)

~~Tweak: Webapp still does not have the same visual and non visualnotification language as the standalone app for desktop notifications. lets be consistent~~
Done: desktop notification titles/bodies now match History panel wording for threshold/completion/failure messages (v1.0.280)

~~Tweak: Default Warnings are 15, 10, 5 3-1~~
Done: DEFAULT_ALERT_THRESHOLDS = "15, 10, 5, 3, 2, 1" (v1.0.275)

~~Tweak: Reset Defaults should be "Reset all defaults" and warn the user that all settings will be reset~~
Done: button renamed, confirm() dialog added explaining what will be reset (v1.0.279)

~~Tweak: add a table of contents to the readme~~
Done: added a short README contents list near the top for faster navigation (v1.0.287)

~~Tweak: don't take responsibility for installing python for the user. just link them the official python website and exit gracefully if there is no python in the main script~~
Done: quick-start/docs wording now points users to the official Python download page rather than implying the app manages Python installation (v1.0.287)

~~Tweak: right most (current live) timestamp should have an opaque background which allows it to always be readable even when overlapping another timestamp~~
Done: graph time labels draw on an opaque background fill, including the rightmost current/live timestamp label (v1.0.287)

~~Tweak: connection-lost message should not be absolutist~~
Done: overlay text now says the page "may" lose the current view if the server stopped; acknowledges auto-reconnect in progress (v1.0.300)

~~Tweak: add download icon button next to copy button for chart PNG~~
Done: added download button (arrow-down icon) next to Copy PNG; triggers canvas.toDataURL and an anchor download with a timestamped filename (v1.0.300)

~~Tweak: use colored dots instead of warning/check/x symbols for session events~~
Done: drawGraphEventMarker replaced with solid colored circles (amber=warning, green=connect, red=disconnect) with dark stroke outline (v1.0.301)

~~Tweak: clarify rate display; add Global Rate to stats; use m/p with tooltip~~
Done: stats mini-panel now shows Avg Rate and Full Rate rows; rate unit changed from "min/pos" to "m/p" with title tooltips explaining the abbreviation; KPI Rate card also gets title tooltip (v1.0.302/337)

# REFACTORS

Architectural debt surfaced by the 2026-05-02 expert audit. These are multi-day rewrites, not one-touch tweaks; they live here so they don't get lost between bugs and features.

## Open

- **refactor: decompose `QueueMonitorEngine` (`vs_queue_monitor/engine.py`).** 2138 LOC, 91 instance attributes initialized in `__init__` (lines 47-169), 85 methods. Mixes Tk `StringVar`/`BoolVar` bindings (legacy from a tkinter UI that's no longer the primary surface), poll state machine flags (`_interrupted_mode`, `_starting`, `_queue_stale_latched`, `_queue_stale_logged_once`, `_last_queue_run_session`, …), file-IO and history backfill threads, config persistence, and push notifier wiring. Split into `QueueState` (pure dataclass), `LogPoller` (threaded), `HistoryStore`, `Notifier`. Drop the Tk var indirection while you're in there.

- **refactor: split `app.js` (4893 LOC) into ES modules.** 213 top-level functions, ~9 leaked `window._*` globals, `applyState()` ~350 lines (`app.js:1858-2206`), `setupChrome()` ~800 lines (`app.js:4099-4900`). Use `<script type="module">` (no bundler needed) and break into ~10 files: graph, settings, history, ws, kpi, chrome, push, sounds, modals, state. Lets each domain be reviewed and tested in isolation.

- **refactor: extract `LogClassifier` from `core.py` regex pile.** `QUEUE_RE`, `POST_QUEUE_PROGRESS_LINE_RES`, `DISCONNECTED_LINE_RES`, `RECONNECTING_LINE_RES`, `QUEUE_RUN_BOUNDARY_RES` are scattered across `core.py:24-121` and feed the 128-line `extract_all_session_records_from_log()` (`core.py:1427-1555`). Most session-boundary regression entries in this TODO trace back here. Build a deterministic classifier with named line types and a state machine, with one fixture test per "Fixed:" entry that originated in this region.

- **refactor: introduce a CSS system in `styles.css` (2199 LOC).** Currently mixes BEM (`.kpi__val`), utility classes (`.hidden`), and ad-hoc selectors. No documented spacing rhythm, duplicated topbar rules. Pick one pattern, document tokens at the top of the file, drop unused indirection, and decide on the theme story.

- **refactor: kill the Tk `StringVar`/`BoolVar` indirection on the engine.** Holdover from the original Tk UI. Every config field currently has a getter, setter, trace_add callback, and persistence round-trip through Tk variables, but the tkinter UI is no longer the primary surface. Replace with plain attributes plus an explicit `on_change` event for the web hooks. Reduces the engine's 91-attribute surface and removes a hidden tkinter dependency.

# FEATURES

Feature: show the user when they are expected to join (ETA) in their local time
- options: 
  - 0. Remaining value because ETR_TIME (ETA_TIME)
  - 1. Remaining becomes ETR / ETA
  - 2. add a new section (bad because warnings will be reduced to retain same size as the other blocks)
  - 3. Add "Est. Join Time: users-local-time" some prominent place like the bar with the session drop down or maybe someplace else

feature: store recent files (*history button) of selected file swso they can be selected again from a history button

feature: disable automatic updates

feature: choose Rate for display and remianing (Global, Full, Point)

~~Feature: Persist queue session history to a local JSONL file so historical data survives restarts and can be analyzed later. Each record should capture: profile path (source_path), server name (parsed from "Connecting to <server>..." log line), start/end epoch, outcome (completed/interrupted/unknown), and position-over-time points at change resolution. File lives alongside app config. Dedup on restart so a session is not written twice. No external dependencies needed.~~
Done: session_history.jsonl written alongside app config on session end (completed/interrupted/abandoned); records source_path, server, start/end epoch, outcome, and position-change-resolution points. Dedup by (log_file, session_id). Merged into the graph session dropdown across restarts and log sources (v1.1.86+)

feature: store recent files (*history button) of selected file swso they can be selected again from a history button

feature: add light and dark theme

Feature: Queue Scheduling

$LaunchAt = "2026-04-10 19:50"   # Change this to the time you want to join queue. YYYY-MM-DD date format and military time.
$Target = Get-Date $LaunchAt

while ((Get-Date) -lt $Target) {
    $Remaining = $Target - (Get-Date)
    Write-Host "Launching at $LaunchAt | Time left: $($Remaining.ToString('hh\:mm\:ss'))"
    Start-Sleep -Seconds 10
    Clear-Host
}

Start-Process "C:\Users\Name\AppData\Roaming\Vintagestory\Vintagestory.exe" -ArgumentList "--connect=tops.vintagestory.at" # Set to your Vintagestory.exe directory

requires you to set the game directory instead of the log directory


Simply paste this into a text document, change to your preferred time and game directory, save, and then rename the text document so that its a .ps1 file. Run the file with Power shell when you leave your computer and you will automatically join the queue at the time you set.

Give yourself some leeway, I am not responsible if you accidently join the game while not at your computer and get afk kicked or die. I recommend disconnecting in a safe location and putting your inventory loot in a chest before doing this.

---
Feature: Join Scheduling
1. have the user get into the queue exactly when they need to be in it.
2. check how big is the queue, then the time it takes to finish it (check global rate) 
3. set it up to boot you into the queue early enough to appear in the chosen server somewhat around the time you need

Feature: Auto-Leave (leave if idle for x mins)

Feature: Auto-Join (try the server until join works or entered queue -- be respectful of the server use things like exponential backoff)

Feature: Auto-rejoin (if disconnected while in queue, try to Auto rejoin the queue)

Feature: Keep-Alive (leave the queue 1 position before you join and rejoin it -- always keep you in the queue)
