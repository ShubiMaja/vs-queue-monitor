#!/usr/bin/env bash

# monitor.sh
# Version: 1.1.0
# Watches Vintage Story client-main.log for queue position changes
# and alerts on Windows via PowerShell popup + loud beeps.
#
# Git Bash / MSYS2 / Cygwin on Windows.

set -u

VERSION="1.1.0"

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
POPUP_TIMEOUT=15

LAST_POSITION=""
LAST_ALERT_POSITION=""
LAST_ALERT_EPOCH=0
ALERT_REASON=""

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
  --tail-lines N            Number of trailing log lines to inspect per poll (default: ${TAIL_LINES})
  --popup 0|1               Enable popup alerts (default: ${ENABLE_POPUP})
  --sound 0|1               Enable sound alerts (default: ${ENABLE_SOUND})
  --sound-repeats N         Number of fallback beep repetitions (default: ${SOUND_REPEATS})
  --sound-file PATH         Optional WAV file to play for alerts
  --popup-timeout N         Popup timeout in seconds (default: ${POPUP_TIMEOUT})
  --show-every-change 0|1   Print every queue change to terminal (default: ${SHOW_EVERY_CHANGE})
  -h, --help                Show help

Examples:
  $(basename "$0") --file "$APPDATA/VSLInstallations/Unstable/client-main.log"
  $(basename "$0") --file "C:\\Users\\Joe\\AppData\\Roaming\\VSLInstallations\\Unstable\\client-main.log"
  $(basename "$0") --alert-at 8 --step 3 --repeat-sec 20
EOF
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

is_number() {
  [[ "${1:-}" =~ ^[0-9]+$ ]]
}

normalize_path() {
  local p="${1:-}"

  [[ -z "$p" ]] && {
    printf '%s' "$p"
    return
  }

  # Turn backslashes into forward slashes so mixed APPDATA paths work.
  p="${p//\\//}"

  # Convert Windows drive path to Git Bash/Cygwin path if possible.
  if [[ "$p" =~ ^[A-Za-z]:/ ]]; then
    if command -v cygpath >/dev/null 2>&1; then
      cygpath -u "$p"
      return
    fi
  fi

  printf '%s' "$p"
}

win_path() {
  local p="${1:-}"

  [[ -z "$p" ]] && {
    printf '%s' "$p"
    return
  }

  # Already Windows-ish
  if [[ "$p" =~ ^[A-Za-z]:[\\/] ]]; then
    printf '%s' "${p//\//\\}"
    return
  fi

  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$p"
    return
  fi

  printf '%s' "$p"
}

escape_ps_single() {
  printf "%s" "$1" | sed "s/'/''/g"
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
  local ps_title ps_message

  ps_title="$(escape_ps_single "$title")"
  ps_message="$(escape_ps_single "$message")"

  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
    \$wshell = New-Object -ComObject WScript.Shell
    \$null = \$wshell.Popup('$ps_message', $POPUP_TIMEOUT, '$ps_title', 48)
  " >/dev/null 2>&1 &
}

play_sound() {
  [[ "$ENABLE_SOUND" == "1" ]] || return 0

  if [[ -n "$SOUND_FILE" && -f "$SOUND_FILE" ]]; then
    local sound_file_win
    sound_file_win="$(win_path "$SOUND_FILE")"
    sound_file_win="$(escape_ps_single "$sound_file_win")"

    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
      try {
        \$player = New-Object System.Media.SoundPlayer '$sound_file_win'
        \$player.Load()
        \$player.PlaySync()
      } catch {
        for (\$i = 0; \$i -lt $SOUND_REPEATS; \$i++) {
          [console]::Beep(1400, 250)
          Start-Sleep -Milliseconds 100
          [console]::Beep(1000, 250)
          Start-Sleep -Milliseconds 100
        }
      }
    " >/dev/null 2>&1 &
    return 0
  fi

  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
    for (\$i = 0; \$i -lt $SOUND_REPEATS; \$i++) {
      try {
        [console]::Beep(1400, 250)
        Start-Sleep -Milliseconds 100
        [console]::Beep(1000, 250)
        Start-Sleep -Milliseconds 100
      } catch {
        [System.Media.SystemSounds]::Hand.Play()
        Start-Sleep -Milliseconds 250
      }
    }
  " >/dev/null 2>&1 &
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

  is_number "$position" || return 1

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
      LOG_FILE="${2:-}"
      shift 2
      ;;
    -a|--alert-at)
      ALERT_AT="${2:-}"
      shift 2
      ;;
    -s|--step)
      POSITION_STEP="${2:-}"
      shift 2
      ;;
    -r|--repeat-sec)
      REPEAT_ALERT_SECONDS="${2:-}"
      shift 2
      ;;
    -p|--poll-sec)
      POLL_SECONDS="${2:-}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    --popup)
      ENABLE_POPUP="${2:-}"
      shift 2
      ;;
    --sound)
      ENABLE_SOUND="${2:-}"
      shift 2
      ;;
    --sound-repeats)
      SOUND_REPEATS="${2:-}"
      shift 2
      ;;
    --sound-file)
      SOUND_FILE="${2:-}"
      shift 2
      ;;
    --popup-timeout)
      POPUP_TIMEOUT="${2:-}"
      shift 2
      ;;
    --show-every-change)
      SHOW_EVERY_CHANGE="${2:-}"
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

for n in \
  "$ALERT_AT" \
  "$POSITION_STEP" \
  "$REPEAT_ALERT_SECONDS" \
  "$POLL_SECONDS" \
  "$TAIL_LINES" \
  "$SOUND_REPEATS" \
  "$ENABLE_POPUP" \
  "$ENABLE_SOUND" \
  "$SHOW_EVERY_CHANGE" \
  "$POPUP_TIMEOUT"
do
  if ! is_number "$n"; then
    echo "Invalid numeric value: $n" >&2
    exit 1
  fi
done

LOG_FILE="$(normalize_path "$LOG_FILE")"
SOUND_FILE="$(normalize_path "$SOUND_FILE")"

log "monitor.sh v${VERSION}"
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
