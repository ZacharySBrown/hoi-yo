#!/usr/bin/env bash
# install_hoi4.sh -- Install Hearts of Iron IV via SteamCMD
#
# Usage:
#   ./install_hoi4.sh <steam_user> <steam_pass>
#   STEAM_USER=xxx STEAM_PASS=xxx ./install_hoi4.sh
#
# Environment variables override arguments.

set -euo pipefail

STEAM_USER="${STEAM_USER:-${1:-}}"
STEAM_PASS="${STEAM_PASS:-${2:-}}"
STEAMCMD_DIR="${STEAMCMD_DIR:-/opt/steamcmd}"
HOI4_DIR="${HOI4_DIR:-/opt/hoi4}"
HOI4_APP_ID="394360"

log() { echo "[install_hoi4] $(date '+%H:%M:%S') $*"; }

if [ -z "$STEAM_USER" ] || [ -z "$STEAM_PASS" ]; then
  echo "Error: Steam credentials required."
  echo "Usage: $0 <steam_user> <steam_pass>"
  echo "   or: STEAM_USER=xxx STEAM_PASS=xxx $0"
  exit 1
fi

# -------------------------------------------------------------------
# Install SteamCMD if not present
# -------------------------------------------------------------------
if [ ! -x "$STEAMCMD_DIR/steamcmd.sh" ]; then
  log "Installing SteamCMD to $STEAMCMD_DIR..."
  mkdir -p "$STEAMCMD_DIR"

  # SteamCMD needs lib32gcc on Debian/Ubuntu
  if command -v apt-get &>/dev/null; then
    apt-get update -y
    apt-get install -y lib32gcc-s1 ca-certificates curl
  fi

  cd "$STEAMCMD_DIR"
  curl -sSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar -xz
  log "SteamCMD installed."
else
  log "SteamCMD already installed at $STEAMCMD_DIR."
fi

# -------------------------------------------------------------------
# Download / update HOI4
# -------------------------------------------------------------------
log "Downloading Hearts of Iron IV (app $HOI4_APP_ID) to $HOI4_DIR..."
log "This may take 10-20 minutes on first install."

"$STEAMCMD_DIR/steamcmd.sh" \
  +@sSteamCmdForcePlatformType linux \
  +force_install_dir "$HOI4_DIR" \
  +login "$STEAM_USER" "$STEAM_PASS" \
  +app_update "$HOI4_APP_ID" validate \
  +quit

log "HOI4 downloaded to $HOI4_DIR."

# -------------------------------------------------------------------
# Configure HOI4 settings
# -------------------------------------------------------------------
HOI4_DOCS="/root/Documents/Paradox Interactive/Hearts of Iron IV"
mkdir -p "$HOI4_DOCS"
mkdir -p "$HOI4_DOCS/save games"

log "Writing settings.txt (plaintext saves, monthly autosave)..."
cat > "$HOI4_DOCS/settings.txt" << 'EOF'
save_as_binary=no
autosave=MONTHLY
autosave_count=10
EOF

# -------------------------------------------------------------------
# Done
# -------------------------------------------------------------------
log "============================================"
log "Hearts of Iron IV installation complete."
log "  Install path : $HOI4_DIR"
log "  Config path  : $HOI4_DOCS"
log "  Executable   : $HOI4_DIR/hoi4"
log "============================================"
