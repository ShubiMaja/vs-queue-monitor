# BUGS




## Open

## Deferred (not to be solved yet)

- **Mobile notifications only fire when the tab is open.** Browser-side notifications (the bell icon) require the tab to be active; they do not wake the browser or deliver when it is closed or backgrounded. Server-side VAPID push (`pywebpush`) is wired up but not yet reliable across mobile browsers. Full background push would require a persistent service worker with push event support — not currently implemented.

## Fixed (closed)

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

Tweak: No queue detected warning should be :warning symbo: No Queue!

Questions: should we allow multiple queue monitor location? What would the impact be?

## Implemented

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

# FEATURES

Feature: Persist queue session history to a local JSONL file so historical data survives restarts and can be analyzed later. Each record should capture: profile path (source_path), server name (parsed from "Connecting to <server>..." log line), start/end epoch, outcome (completed/interrupted/unknown), and position-over-time points at change resolution. File lives alongside app config. Dedup on restart so a session is not written twice. No external dependencies needed.

~~Feature: Auto update mechanism that detects a change to main branch and asks you to update by pulling the main branch and restarting the app~~
Done: background thread fetches `origin/main` every hour and sets `update_available` on app state; a green banner appears at the top when a newer commit exists on main; "Update & restart" runs `git pull` then `os.execv` to replace the server process; the browser detects the disconnect and hard-reloads on reconnect (v1.1.33)

Feature: Snapshot every session recorded once the session ends and store it as appdata so we can perform analytics later

feature: store history of selected file swso they can be selected again from a history button

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

additional feature

I suppose it's a player made script that will have them get into the queue exactly when they need to be in it, like, it checks how big is the queue, then the time it takes to finish it (0.54 user a minute usually goes through the queue), and so you can set it up to boot you into the queue two hours earlier and then appear in the TOPS somewhat around the time they need

Feature: Auto-Leave (leave if idle for x mins)

Feature: Auto-Join (try the server until join works or entered queue -- be respectful of the server)

Feature: Auto-rejoin (if disconnected while in queue, try to Auto rejoin the queue)

Feature: Keep-Alive (leave the queue 1 position before you join and rejoin it -- always keep you in the queue)
