#!/usr/bin/env bash
# start_campaign.sh -- Start a HOI4 campaign in headless mode
#
# Usage:
#   ./start_campaign.sh [DISPLAY_NUM]
#   ./start_campaign.sh :99       # default
#   ./start_campaign.sh :1

set -euo pipefail

DISPLAY_NUM="${1:-:99}"
HOI4_DIR="${HOI4_DIR:-/opt/hoi4}"
HOI4_BIN="$HOI4_DIR/hoi4"
GAME_LOAD_WAIT="${GAME_LOAD_WAIT:-45}"

log() { echo "[start_campaign] $(date '+%H:%M:%S') $*"; }

# -------------------------------------------------------------------
# Validate
# -------------------------------------------------------------------
if [ ! -x "$HOI4_BIN" ]; then
  log "ERROR: HOI4 executable not found at $HOI4_BIN"
  log "Set HOI4_DIR or run install_hoi4.sh first."
  exit 1
fi

for cmd in Xvfb xdotool; do
  if ! command -v "$cmd" &>/dev/null; then
    log "ERROR: $cmd not found. Install it: apt-get install -y xvfb xdotool"
    exit 1
  fi
done

# -------------------------------------------------------------------
# Start Xvfb if not already running on this display
# -------------------------------------------------------------------
if ! pgrep -f "Xvfb $DISPLAY_NUM" >/dev/null 2>&1; then
  log "Starting Xvfb on display $DISPLAY_NUM..."
  Xvfb "$DISPLAY_NUM" -screen 0 1280x1024x24 -nolisten tcp &
  XVFB_PID=$!
  sleep 2

  if ! kill -0 "$XVFB_PID" 2>/dev/null; then
    log "ERROR: Xvfb failed to start."
    exit 1
  fi
  log "Xvfb running (PID $XVFB_PID)."
else
  log "Xvfb already running on display $DISPLAY_NUM."
fi

export DISPLAY="$DISPLAY_NUM"

# -------------------------------------------------------------------
# Launch HOI4
# -------------------------------------------------------------------
log "Launching HOI4 in debug mode..."
"$HOI4_BIN" -debug -nolauncher &
HOI4_PID=$!

if ! kill -0 "$HOI4_PID" 2>/dev/null; then
  log "ERROR: HOI4 failed to start."
  exit 1
fi

log "HOI4 launched (PID $HOI4_PID). Waiting ${GAME_LOAD_WAIT}s for game to load..."
sleep "$GAME_LOAD_WAIT"

# Verify process is still alive after loading
if ! kill -0 "$HOI4_PID" 2>/dev/null; then
  log "ERROR: HOI4 process died during loading."
  exit 1
fi

# -------------------------------------------------------------------
# Send console commands via xdotool
# -------------------------------------------------------------------
log "Sending console commands..."

# Open console (~ key = grave)
xdotool key --delay 100 grave
sleep 1

# Type 'observe' to enter observer mode
xdotool type --delay 50 "observe"
xdotool key Return
sleep 1

# Set game speed to 4
xdotool type --delay 50 "speed 4"
xdotool key Return
sleep 0.5

# Close console
xdotool key grave
sleep 0.5

log "Console commands sent (observe mode, speed 4)."

# -------------------------------------------------------------------
# Report
# -------------------------------------------------------------------
log "============================================"
log "HOI4 campaign running."
log "  PID     : $HOI4_PID"
log "  Display : $DISPLAY_NUM"
log "  Mode    : observer, speed 4"
log ""
log "To attach: export DISPLAY=$DISPLAY_NUM"
log "To stop:   kill $HOI4_PID"
log "============================================"

echo "$HOI4_PID"
