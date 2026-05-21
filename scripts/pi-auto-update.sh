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

# On abend, dump the last container logs so the failure is debuggable, then
# prune any dangling (untagged) images left by a partial pull.
_on_exit() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        log "ERROR: script exited with code $exit_code — dumping last 30 container log lines:"
        podman logs --tail=30 ride-optimizer 2>/dev/null || true
        log "Pruning dangling images left by failed update..."
        podman image prune -f 2>/dev/null || true
    fi
}
trap _on_exit EXIT

log "=== Ride Optimizer Auto-Update ==="

# Disk check — warn but do not block unattended runs
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "WARNING: Disk at ${DISK_USAGE}% — consider running: podman image prune -a"
fi

# Prune stopped containers and dangling images before starting so stale
# remnants from a previous failed run do not interfere.
log "Cleaning up stale containers and dangling images..."
podman container prune -f 2>/dev/null || true
podman image prune -f 2>/dev/null || true

# Record current local image ID so we can detect a real change after pull
BEFORE_ID=$(podman inspect "$LOCAL_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")

log "Pulling ${REMOTE_IMAGE}..."
if ! podman pull "$REMOTE_IMAGE"; then
    log "ERROR: Pull failed — network issue or image not yet published. Aborting."
    exit 1
fi

# Tag under the local alias used by docker-compose.yml, then drop the GHCR tag
# so podman-compose does not attempt a second pull.
podman tag "$REMOTE_IMAGE" "$LOCAL_IMAGE"
AFTER_ID=$(podman inspect "$LOCAL_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")
podman rmi "$REMOTE_IMAGE" 2>/dev/null || true

if [ "$BEFORE_ID" = "$AFTER_ID" ] && [ -n "$BEFORE_ID" ] && [ "$FORCE" = false ]; then
    log "Image unchanged (${AFTER_ID:0:12}) — containers not restarted."
    exit 0
fi

log "New image: ${BEFORE_ID:0:12} → ${AFTER_ID:0:12}"

# Remove the old image that was previously tagged as LOCAL_IMAGE (now superseded)
# so it does not accumulate as an untagged layer on the Pi.
if [ -n "$BEFORE_ID" ] && [ "$BEFORE_ID" != "$AFTER_ID" ]; then
    podman rmi "$BEFORE_ID" 2>/dev/null || true
fi

log "Restarting containers..."
# Suppress expected "not found" noise when nothing was running before this update.
podman-compose down 2>&1 | grep -v "no such container\|no such pod\|no pod with name\|no container with name" || true

# Ensure bind-mounted directories exist and are writable by the container user.
# The container runs as rideopt (UID 1000); sudo is used so this works even
# when the directory was previously created by root during an older run.
mkdir -p logs data cache config
podman unshare chown -R 1000:1000 logs data cache config 2>/dev/null || \
    log "WARNING: could not chown logs/data/cache/config — if the app fails to start, run: podman unshare chown -R 1000:1000 logs data cache config"

podman-compose up -d

log "Waiting for app to become healthy..."
for i in $(seq 1 36); do
    sleep 5
    if podman inspect --format='{{.State.Health.Status}}' ride-optimizer 2>/dev/null | grep -q healthy; then
        log "✓ App healthy after $((i * 5))s."
        break
    fi
    if [ "$i" -eq 36 ]; then
        log "ERROR: ride-optimizer did not become healthy after 180s."
        exit 1
    fi
done

# Remove any images that are now untagged (the superseded build).
log "Cleaning up superseded images..."
podman image prune -f 2>/dev/null || true

log "✓ Deployment complete."
