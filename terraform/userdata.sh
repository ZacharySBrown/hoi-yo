#!/bin/bash
# hoi-yo EC2 bootstrap script
# Runs as root via cloud-init user data on first boot.

set -euo pipefail

LOG_FILE="/var/log/hoi-yo-setup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================="
echo "hoi-yo bootstrap starting at $(date -u)"
echo "========================================="

REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
export AWS_DEFAULT_REGION="$REGION"

# Helper: read an SSM parameter (decrypted)
ssm_get() {
  aws ssm get-parameter --name "$1" --with-decryption --query 'Parameter.Value' --output text
}

# -------------------------------------------------------------------
# 1. System packages
# -------------------------------------------------------------------
echo "[1/11] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  software-properties-common \
  awscli \
  git \
  nginx \
  xvfb \
  x11-utils \
  xdotool \
  lib32gcc-s1 \
  ca-certificates \
  curl \
  unzip \
  jq

# Python 3.11 from deadsnakes PPA
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3.11-dev

echo "[1/11] System packages installed."

# -------------------------------------------------------------------
# 2. SteamCMD
# -------------------------------------------------------------------
echo "[2/11] Installing SteamCMD..."
mkdir -p /opt/steamcmd
cd /opt/steamcmd
if [ ! -f ./steamcmd.sh ]; then
  curl -sSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar -xz
fi
echo "[2/11] SteamCMD installed at /opt/steamcmd."

# -------------------------------------------------------------------
# 3. Read Steam credentials from SSM
# -------------------------------------------------------------------
echo "[3/11] Reading Steam credentials from SSM..."
STEAM_USER=$(ssm_get "/hoi-yo/steam-user")
STEAM_PASS=$(ssm_get "/hoi-yo/steam-pass")
echo "[3/11] Steam credentials retrieved."

# -------------------------------------------------------------------
# 4. Install HOI4 via SteamCMD
# -------------------------------------------------------------------
echo "[4/11] Installing Hearts of Iron IV (this may take a while)..."
/opt/steamcmd/steamcmd.sh \
  +@sSteamCmdForcePlatformType linux \
  +force_install_dir /opt/hoi4 \
  +login "$STEAM_USER" "$STEAM_PASS" \
  +app_update 394360 validate \
  +quit

# Clear credentials from memory
unset STEAM_PASS
echo "[4/11] HOI4 installed at /opt/hoi4."

# -------------------------------------------------------------------
# 5. Configure HOI4 settings
# -------------------------------------------------------------------
echo "[5/11] Configuring HOI4 settings..."
HOI4_DOCS="/root/Documents/Paradox Interactive/Hearts of Iron IV"
mkdir -p "$HOI4_DOCS"

cat > "$HOI4_DOCS/settings.txt" << 'SETTINGS'
save_as_binary=no
autosave=MONTHLY
autosave_count=10
SETTINGS

# Create save directory
mkdir -p "$HOI4_DOCS/save games"
echo "[5/11] HOI4 configured (plaintext saves, monthly autosave)."

# -------------------------------------------------------------------
# 6. Clone hoi-yo repository
# -------------------------------------------------------------------
echo "[6/11] Cloning hoi-yo repository..."
if [ -d /opt/hoi-yo/.git ]; then
  cd /opt/hoi-yo && git pull
else
  git clone https://github.com/zacharysbrown/hoi-yo.git /opt/hoi-yo
fi
echo "[6/11] hoi-yo source at /opt/hoi-yo."

# -------------------------------------------------------------------
# 7. Python venv + install
# -------------------------------------------------------------------
echo "[7/11] Setting up Python environment..."
python3.11 -m venv /opt/hoi-yo/.venv
source /opt/hoi-yo/.venv/bin/activate
pip install --upgrade pip
pip install /opt/hoi-yo
echo "[7/11] Python environment ready."

# -------------------------------------------------------------------
# 8. Read remaining secrets from SSM
# -------------------------------------------------------------------
echo "[8/11] Reading application secrets from SSM..."
ANTHROPIC_API_KEY=$(ssm_get "/hoi-yo/anthropic-api-key")
DASHBOARD_PASSWORD_HASH=$(ssm_get "/hoi-yo/dashboard-password-hash")
JWT_SECRET=$(ssm_get "/hoi-yo/jwt-secret")
echo "[8/11] Application secrets retrieved."

# -------------------------------------------------------------------
# 9. Write cloud config.toml
# -------------------------------------------------------------------
echo "[9/11] Writing cloud config.toml..."
cat > /opt/hoi-yo/config.toml << TOML
[game]
hoi4_executable = "/opt/hoi4/hoi4"
save_dir = "/root/Documents/Paradox Interactive/Hearts of Iron IV/save games"
mod_dir = "/root/Documents/Paradox Interactive/Hearts of Iron IV/mod/hoi_yo_bots"
config_dir = "/root/Documents/Paradox Interactive/Hearts of Iron IV"
use_xvfb = true
autosave_interval = "MONTHLY"
initial_speed = 4
use_plaintext_saves = true

[personas]
GER = "personas/germany"
SOV = "personas/soviet_union"
USA = "personas/usa"
ENG = "personas/united_kingdom"
JAP = "personas/japan"
ITA = "personas/italy"

[api]
default_model = "claude-haiku-4-5"
war_model = "claude-sonnet-4-6"
crisis_model = "claude-opus-4-6"
cache_ttl_static = "1h"
cache_ttl_board = "5m"
max_output_tokens = 2000

[dashboard]
port = 8080
enable_vnc = true
vnc_port = 6080
popcorn_mode_pause = 5
TOML

echo "[9/11] config.toml written."

# -------------------------------------------------------------------
# 10. Systemd service
# -------------------------------------------------------------------
echo "[10/11] Creating systemd services..."

# Xvfb as its own service so hoi-yo can depend on it
cat > /etc/systemd/system/xvfb.service << XVFB
[Unit]
Description=X Virtual Framebuffer (display :99)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
XVFB

cat > /etc/systemd/system/hoi-yo.service << SERVICE
[Unit]
Description=hoi-yo Hearts of Iron IV AI Agent System
After=network-online.target xvfb.service
Wants=network-online.target
Requires=xvfb.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hoi-yo
Environment=ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
Environment=DASHBOARD_PASSWORD_HASH=${DASHBOARD_PASSWORD_HASH}
Environment=JWT_SECRET=${JWT_SECRET}
Environment=DISPLAY=:99
ExecStart=/opt/hoi-yo/.venv/bin/hoi-yo run
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Auto-shutdown timer
cat > /etc/systemd/system/hoi-yo-autoshutdown.service << AUTOSHUT
[Unit]
Description=hoi-yo auto-shutdown check

[Service]
Type=oneshot
ExecStart=/opt/hoi-yo/.venv/bin/python /opt/hoi-yo/scripts/auto_shutdown.py
AUTOSHUT

cat > /etc/systemd/system/hoi-yo-autoshutdown.timer << TIMER
[Unit]
Description=Run hoi-yo auto-shutdown check every 5 minutes

[Timer]
OnBootSec=10min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable --now xvfb.service
systemctl enable --now hoi-yo.service
systemctl enable --now hoi-yo-autoshutdown.timer

echo "[10/11] systemd services started."

# -------------------------------------------------------------------
# 11. Nginx reverse proxy
# -------------------------------------------------------------------
echo "[11/11] Configuring nginx..."
cat > /etc/nginx/sites-available/hoi-yo << 'NGINX'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/hoi-yo /etc/nginx/sites-enabled/hoi-yo
nginx -t && systemctl restart nginx

echo "[11/11] nginx configured."

# -------------------------------------------------------------------
# Done
# -------------------------------------------------------------------
echo "========================================="
echo "hoi-yo bootstrap COMPLETE at $(date -u)"
echo "Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
echo "========================================="
