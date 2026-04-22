# BUGS

## Open

## Fixed (closed)

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

- Run a manual stable-release smoke pass across first run, path setup, live queue, completion, interrupted/disconnect, history scroll/autoscroll, and Chrome/Edge notifications before calling this stable

## Implemented

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
Done: stats mini-panel now shows Avg Rate and Global Rate rows; rate unit changed from "min/pos" to "m/p" with title tooltips explaining the abbreviation; KPI Rate card also gets title tooltip (v1.0.302)

# FEATURES


Feature: Auto update mechanism that detects a change to main branch and asks you to update by pulling the main branch and restarting the app

Feature: Snapshot every session recorded once the session ends and store it as appdata so we can perform analytics later


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
