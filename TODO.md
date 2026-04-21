# BUGS

## Open

Bug: I'm not sure the tour triggers on first run. how can we be sure?

Visual Bug: Instead overlaying visual icons on the graph, they should be on the timeline with time having the ability to show over them (maybe have bold dark outline around the timestamps or pick another elegant way to not clutter the graph)

Bug: I'm not sure the tour triggers on first run. how can we be sure?

Visual Bug: Instead overlaying visual icons on the graph, they should be on the timeline with time having the ability to show over them (maybe have bold dark outline around the timestamps or pick another elegant way to not clutter the graph)

Feature: Add Prequeue feature

Visual Bug: the first point in the live session graph has a diagonal line to the second point, then continues normally as a step graph (needs reproduction — step vertex logic looks correct; may be a rendering artifact or downsampling edge case)

Bug: Clicking on the notification that pops up does not focus the application or tab

## Fixed (closed)

~~Bug: When a log file is not loaded its really unclear that this is the problem.~~
Fixed: graph canvas now shows context-aware message with "← Set a log folder above" hint (v1.0.266)

~~Bug: live graph keeps moving even after connected; weird zoom behavior going off screen~~
Fixed: stop extending t1 to Date.now() when progress=1.0; zoom now uses ds.t0/ds.t1 (v1.0.265)

~~Bug: when setting warning thresholds to 15, 10, 5, 3-1 we get an error: formatShortDuration is not defined~~
Fixed: added missing formatShortDuration function (v1.0.264)

~~Bug: History scrollbar does not appear to be working, history window just scrolls infinitely~~
Fixed: added max-height to .info-history__card--side to close the flex chain (v1.0.267)

~~Bug: game asks to adopt a new run before getting in a new queue~~
Fixed: removed total_queue_boundaries early-detection from _handle_interrupted_tail — boundary patterns fire during normal post-queue gameplay (v1.0.268)

~~Bug: latest session has no knowledge of position 0 and shows you as disconnected at 1~~
Fixed: compute_seed_graph_from_log now maps authoritative_pos → 0 when post-queue signal is already present in log tail (v1.0.269)

~~Bug: Latest session is also represented as a session with an id in the drop down — shown as ✕ Failed even though it's the ongoing session~~
Fixed: _queue_sessions_for_engine now filters out the active session by engine._last_queue_run_session (v1.0.272)

---

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

Give yourself some leeway, I'm not responsible if you accidently join the game while not at your computer and get afk kicked or die. I recommend disconnecting in a safe location and putting your inventory loot in a chest before doing this.

---
Feature: Join Scheduling

additional feature

I suppose it's a player made script that will have them get into the queue exactly when they need to be in it, like, it checks how big is the queue, then the time it takes to finish it (0.54 user a minute usually goes through the queue), and so you can set it up to boot you into the queue two hours earlier and then appear in the TOPS somewhat around the time they need

Feature: Auto-Leave (leave if idle for x mins)

Feature: Auto-Join (try the server until join works or entered queue -- be respectful of the server)

Feature: Auto-rejoin (if disconnected while in queue, try to Auto Join)
