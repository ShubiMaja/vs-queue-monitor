#!/usr/bin/env bash

# vs_queue_alert.sh
# Version: 1.0.0
# Watches a Vintage Story client log for queue position changes and raises
# loud Windows alerts using PowerShell popups + beeps.
#
# Intended for Git Bash / MSYS2 / Cygwin on Windows.
# Native Windows notifications are invoked through powershell.exe.

set -u

VERSION="1.0.0"

# =========================
# Default configuration
# =========================
LOG_FILE="${APPDATA:-}/VintagestoryData/client-main.log"
POLL_SECONDS=2
ALERT_AT=10
POSITION_STEP=5
REPEAT_ALERT_SECONDS=30
ENABLE_POPUP=1
ENABLE_SOUND=1
SOUND_REPEATS=8
SOUND_FILE=""
TAIL_LINES=250
SHOW_EVERY_CHANGE=0

LAST_POSITION=""
LAST_ALERT_POSITION=""
LAST_ALERT_EPOCH=0

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [options]

Options:
  -f, --file PATH           Path to client log file
  -a, --alert-at N          Alert when queue position is <= N (default: ${ALERT_AT})
  -s, --step N              Alert when position improves by N since last alert (default: ${POSITION_STEP})
  -r, --repeat-sec N        Minimum seconds between repeated alerts (default: ${REPEAT_ALERT_SECONDS})
  -p, --poll-sec N          Poll interval in seconds (default: ${POLL_SECONDS})
  --tail-lines N            How many trailing log lines to inspect each poll (default: ${TAIL_LINES})
  --popup 0|1               Enable popup alerts (default: ${ENABLE_POPUP})
  --sound 0|1               Enable sound alerts (default: ${ENABLE_SOUND})
  --sound-repeats N         Number of fallback beep repetitions (default: ${SOUND_REPEATS})
  --sound-file PATH         Optional WAV file to play for alerts
  --show-every-change 0|1   Print every queue change to terminal (default: ${SHOW_EVERY_CHANGE})
  -h, --help                Show help

Examples:
  $(basename "$0") --file "/c/Users/Joe/AppData/Roaming/VintagestoryData/client-main.log" --alert-at 8 --repeat-sec 20
  $(basename "$0") --alert-at 15 --step 3 --sound-file "/c/Users/Joe/Downloads/alarm.wav"
EOF
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

is_number() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

win_path() {
  local p="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$p"
  else
    printf '%s' "$p"
  fi
}

get_latest_position() {
  [[ -f "$LOG_FILE" ]] || return 1

  tail -n "$TAIL_LINES" "$LOG_FILE" 2>/dev/null \
    | grep -aE 'Client is in connect queue at position: [0-9]+' \
    | tail -n 1 \
    | sed -E 's/.*position: ([0-9]+).*/\1/'
}

show_popup() {
  local title="$1"
  local message="$2"

  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
Add-Type -AssemblyName PresentationFramework | Out-Null
[System.Windows.MessageBox]::Show('$message', '$title') | Out-Null
" >/dev/null 2>&1 || true
}

play_sound() {
  if [[ "$ENABLE_SOUND" != "1" ]]; then
    return 0
  fi

  if [[ -n "$SOUND_FILE" && -f "$SOUND_FILE" ]]; then
    local sound_file_win
    sound_file_win="$(win_path "$SOUND_FILE")"
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
try {
  Add-Type -AssemblyName System.Windows.Extensions | Out-Null
  \$player = New-Object System.Media.SoundPlayer '$sound_file_win'
  \$player.Load()
  \$player.PlaySync()
} catch {
  [console]::beep(1200, 400)
  Start-Sleep -Milliseconds 150
  [console]::beep(1200, 400)
}
" >/dev/null 2>&1 || true
    return 0
  fi

  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
for (\$i = 0; \$i -lt ${SOUND_REPEATS}; \$i++) {
  try {
    [console]::beep(1400, 250)
    Start-Sleep -Milliseconds 100
    [console]::beep(1000, 250)
    Start-Sleep -Milliseconds 100
  } catch {
    [System.Media.SystemSounds]::Hand.Play()
    Start-Sleep -Milliseconds 250
  }
}
" >/dev/null 2>&1 || true
}

alert_user() {
  local position="$1"
  local reason="$2"
  local now
  now="$(date +%s)"

  LAST_ALERT_EPOCH="$now"
  LAST_ALERT_POSITION="$position"

  log "ALERT: queue position ${position} (${reason})"
  play_sound

  if [[ "$ENABLE_POPUP" == "1" ]]; then
    show_popup "Vintage Story Queue Alert" "Queue position is now ${position}\n\nReason: ${reason}"
  fi
}

should_alert() {
  local position="$1"
  local now elapsed improvement
  now="$(date +%s)"
  elapsed=$(( now - LAST_ALERT_EPOCH ))

  if ! is_number "$position"; then
    return 1
  fi

  if [[ -z "$LAST_ALERT_POSITION" ]]; then
    if (( position <= ALERT_AT )); then
      ALERT_REASON="position <= ${ALERT_AT}"
      return 0
    fi
    return 1
  fi

  improvement=$(( LAST_ALERT_POSITION - position ))

  if (( position <= ALERT_AT && elapsed >= REPEAT_ALERT_SECONDS )); then
    ALERT_REASON="still at or below ${ALERT_AT} after ${elapsed}s"
    return 0
  fi

  if (( improvement >= POSITION_STEP && elapsed >= REPEAT_ALERT_SECONDS )); then
    ALERT_REASON="improved by ${improvement} since last alert"
    return 0
  fi

  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)
      LOG_FILE="$2"
      shift 2
      ;;
    -a|--alert-at)
      ALERT_AT="$2"
      shift 2
      ;;
    -s|--step)
      POSITION_STEP="$2"
      shift 2
      ;;
    -r|--repeat-sec)
      REPEAT_ALERT_SECONDS="$2"
      shift 2
      ;;
    -p|--poll-sec)
      POLL_SECONDS="$2"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="$2"
      shift 2
      ;;
    --popup)
      ENABLE_POPUP="$2"
      shift 2
      ;;
    --sound)
      ENABLE_SOUND="$2"
      shift 2
      ;;
    --sound-repeats)
      SOUND_REPEATS="$2"
      shift 2
      ;;
    --sound-file)
      SOUND_FILE="$2"
      shift 2
      ;;
    --show-every-change)
      SHOW_EVERY_CHANGE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

for n in "$ALERT_AT" "$POSITION_STEP" "$REPEAT_ALERT_SECONDS" "$POLL_SECONDS" "$TAIL_LINES" "$SOUND_REPEATS" "$ENABLE_POPUP" "$ENABLE_SOUND" "$SHOW_EVERY_CHANGE"; do
  if ! is_number "$n"; then
    echo "Invalid numeric value: $n" >&2
    exit 1
  fi
done

log "vs_queue_alert.sh v${VERSION}"
log "Watching: $LOG_FILE"
log "Alert when <= ${ALERT_AT}, step improvement ${POSITION_STEP}, repeat every ${REPEAT_ALERT_SECONDS}s"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "Log file not found: $LOG_FILE" >&2
  echo "Tip: pass --file with the full path to your client-main.log" >&2
  exit 1
fi

trap 'log "Stopped."; exit 0' INT TERM

while true; do
  position="$(get_latest_position || true)"

  if is_number "$position"; then
    if [[ "$position" != "$LAST_POSITION" ]]; then
      if [[ "$SHOW_EVERY_CHANGE" == "1" || -z "$LAST_POSITION" ]]; then
        log "Queue position: ${position}"
      fi
      LAST_POSITION="$position"
    fi

    if should_alert "$position"; then
      alert_user "$position" "$ALERT_REASON"
    fi
  fi

  sleep "$POLL_SECONDS"
done

