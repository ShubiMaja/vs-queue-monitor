# BUGS

## Open

## Fixed (closed)

~~Bug: our session appears in the list as a failed session~~
Fixed: the web server now filters the active session out of the dropdown even when its session id is 0, so the live run no longer shows up as a bogus failed historical entry (v1.0.294)

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

---

# TWEAKS

## Open

- Run a manual stable-release smoke pass across first run, path setup, live queue, completion, interrupted/disconnect, history scroll/autoscroll, and Chrome/Edge notifications before calling this stable

## Implemented

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

# FEATURES

Feature: Auto update mechanism that detects a change to main branch and asks you to update by pulling the main branch and restarting the app

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

Feature: Auto-rejoin (if disconnected while in queue, try to Auto Join)
