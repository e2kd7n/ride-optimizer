#!/bin/bash
#
# Pull the latest image from GHCR and redeploy if changed.
# Runs unattended via systemd timer (daily at 01:30) and accepts manual invocation:
#
#   ./scripts/pi-auto-update.sh          # update only if a newer image exists
#   ./scripts/pi-auto-update.sh --force  # pull and redeploy unconditionally

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

REGISTRY="ghcr.io"
IMAGE_OWNER="e2kd7n"
REMOTE_IMAGE="${REGISTRY}/${IMAGE_OWNER}/ride-optimizer:latest"
LOCAL_IMAGE="ride-optimizer:latest"
FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Ride Optimizer Auto-Update ==="

# Disk check — warn but do not block unattended runs
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "WARNING: Disk at ${DISK_USAGE}% — pull may fail. Consider: podman image prune -a"
fi

# Record current local image ID so we can detect a real change after pull
BEFORE_ID=$(podman inspect "$LOCAL_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")

log "Pulling ${REMOTE_IMAGE}..."
if ! podman pull "$REMOTE_IMAGE"; then
    log "ERROR: Pull failed — network issue or image not yet published. Aborting."
    exit 1
fi

podman tag "$REMOTE_IMAGE" "$LOCAL_IMAGE"
AFTER_ID=$(podman inspect "$LOCAL_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")

# Keep only the local tag; layers are retained
podman rmi "$REMOTE_IMAGE" 2>/dev/null || true

if [ "$BEFORE_ID" = "$AFTER_ID" ] && [ -n "$BEFORE_ID" ] && [ "$FORCE" = false ]; then
    log "Image unchanged (${AFTER_ID:0:12}) — containers not restarted."
    exit 0
fi

log "New image: ${BEFORE_ID:0:12} → ${AFTER_ID:0:12}"

log "Restarting containers..."
podman-compose down 2>&1 | grep -v "no pod with name or ID" || true

# Ensure mounted directories are writable by container user (UID 1000 = rideopt)
mkdir -p logs data cache config
chown 1000:1000 logs data cache 2>/dev/null || true

podman-compose up -d

log "Waiting for app to become healthy..."
for i in $(seq 1 12); do
    sleep 5
    if podman inspect --format='{{.State.Health.Status}}' ride-optimizer 2>/dev/null | grep -q healthy; then
        log "✓ App healthy after $((i * 5))s."
        break
    fi
    if [ "$i" -eq 12 ]; then
        log "ERROR: ride-optimizer did not become healthy after 60s. Last 30 log lines:"
        podman-compose logs --tail=30 >&2
        exit 1
    fi
done

log "✓ Deployment complete."
