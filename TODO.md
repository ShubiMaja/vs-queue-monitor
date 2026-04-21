# BUGS

Bug: WHen a log file is not loaded its really unclear that this is the  problem. for example the graph area should say something Queue data will be displayed here when a file is loaded. 

Also maybe if theres no log file there should be some kind of indicator towards the folder pickier, maybe arrow pointing <- Click here to get started or start here (is that redundant?)

Bug: I'm not sure the tour triggers on first run. how can we be sure?

Bug: live graph keeps moving even after connected, when zoomed it there is wierd behavior where live graph goes off the screen

Visual Bug: Instead overlaying visual icons on the graph, instead they should be on hte timeline with time having the ability to show over them (maybe have bold dark outline around the timestamps or pick another elegant way to not clutter the graph)

Bug: game asks to adopt a new run before i got in a new queue
Feature: Add Prequeue feature

Bug: latest session hhas no knowledge of position 0 and shows you as disconnected at 1

Bug: when setting wearning thresholds to 15, 10, 5, 3-1
we get an error: formatShortDuration is not defined

Bug: History scrollbar does not appear to be working, history  window just scrolls infinitely

Visual Bug:  the first point in the live session graph has a diagonal line to the second point, then continues normally as a step graph

Bug: Clicking on the notification that pops up does not focus the application or tab

# FEATURES

Feature: Auto update mechanism that detects a change to main branch and asks you to update by bulling the main branch and restarting the app

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
