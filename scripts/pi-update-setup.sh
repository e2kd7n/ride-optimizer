#!/bin/bash
#
# Install the systemd service + timer for nightly auto-updates from GHCR.
# Run once on the Pi:
#
#   ./scripts/pi-update-setup.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="$(whoami)"
SERVICE="ride-optimizer-update"

echo "Installing ${SERVICE} systemd units..."
echo "  App dir : ${APP_DIR}"
echo "  Run as  : ${APP_USER}"
echo ""

sudo tee /etc/systemd/system/${SERVICE}.service > /dev/null << EOF
[Unit]
Description=Ride Optimizer — Pull latest image from GHCR and redeploy
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/scripts/pi-auto-update.sh
User=${APP_USER}
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ride-optimizer-update
EOF

sudo tee /etc/systemd/system/${SERVICE}.timer > /dev/null << 'EOF'
[Unit]
Description=Ride Optimizer — Daily auto-update at 01:30

[Timer]
OnCalendar=*-*-* 01:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ${SERVICE}.timer

echo ""
echo "✓ Timer installed and enabled. Schedule:"
systemctl list-timers ${SERVICE}.timer --no-pager
echo ""
echo "Manual trigger (two options):"
echo "  sudo systemctl start ${SERVICE}.service"
echo "  ./scripts/pi-auto-update.sh --force"