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
# shellcheck source=utilities.sh
source "$SCRIPT_DIR/utilities.sh"

REGISTRY="ghcr.io"
IMAGE_OWNER="e2kd7n"
REMOTE_IMAGE="${REGISTRY}/${IMAGE_OWNER}/ride-optimizer:latest"
FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

# On abend, dump the last container logs so the failure is debuggable, then
# prune any dangling (untagged) images left by a partial pull.
_on_exit() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        echo -e "${RED}✗ Auto-update failed (exit $exit_code) — last 30 container log lines:${NC}"
        podman logs --tail=30 ride-optimizer 2>/dev/null || true
        start_spinner "Pruning dangling images left by failed update"
        podman image prune -f 2>/dev/null || true
        stop_spinner ok
    fi
}
trap _on_exit EXIT

section "Ride Optimizer Auto-Update" "🚀"

# ── Pre-flight ───────────────────────────────────────────────────────────────

section "Pre-flight Check" "🔍"

# Disk check — warn but do not block unattended runs
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "  ${YELLOW}⚠️  Disk at ${DISK_USAGE}% — consider running: podman image prune -a${NC}"
else
    echo -e "  ${GREEN}✓${NC}  Disk usage OK (${DISK_USAGE}%)"
fi

# Prune stopped containers and dangling images before starting so stale
# remnants from a previous failed run do not interfere.
start_spinner "Cleaning up stale containers and dangling images"
podman container prune -f 2>/dev/null || true
podman image prune -f 2>/dev/null || true
stop_spinner ok

# ── Pull image ───────────────────────────────────────────────────────────────

section "Pulling Image" "📥"
echo -e "  ${BLUE}Image: ${REMOTE_IMAGE}${NC}"

# Record current image ID so we can detect whether a new layer was actually pulled.
BEFORE_ID=$(podman inspect "$REMOTE_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")

timer_start
start_spinner "Pulling ${REMOTE_IMAGE}"
if ! podman pull "$REMOTE_IMAGE" &>/dev/null; then
    stop_spinner fail
    echo -e "  ${RED}❌ Pull failed — network issue or image not yet published. Aborting.${NC}"
    exit 1
fi
stop_spinner ok
timer_end

AFTER_ID=$(podman inspect "$REMOTE_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")

if [ "$BEFORE_ID" = "$AFTER_ID" ] && [ -n "$BEFORE_ID" ] && [ "$FORCE" = false ]; then
    section "Summary" "🚲"
    echo -e "  ${GREEN}✓${NC}  Image unchanged (${AFTER_ID:0:12}) — containers not restarted."
    exit 0
fi

echo -e "  ${BLUE}New image: ${BEFORE_ID:0:12} → ${AFTER_ID:0:12}${NC}"

# Remove the superseded image layer so it does not accumulate on the Pi.
if [ -n "$BEFORE_ID" ] && [ "$BEFORE_ID" != "$AFTER_ID" ]; then
    podman rmi "$BEFORE_ID" 2>/dev/null || true
fi

# ── Deploy ───────────────────────────────────────────────────────────────────

section "Deploying" "🚀"

step "Stopping containers"
# Suppress expected "not found" noise when nothing was running before this update,
# but let any real error through — that's why this isn't wrapped in a spinner.
podman-compose down 2>&1 | grep -v "no such container\|no such pod\|no pod with name\|no container with name" || true

# Ensure bind-mounted directories exist and are writable by the container user.
# The container runs as rideopt (UID 1000); sudo is used so this works even
# when the directory was previously created by root during an older run.
mkdir -p logs data cache config
if ! podman unshare chown -R 1000:1000 logs data cache config 2>/dev/null; then
    echo -e "  ${YELLOW}⚠️  Could not chown logs/data/cache/config — if the app fails to start, run: podman unshare chown -R 1000:1000 logs data cache config${NC}"
fi

start_spinner "Starting containers"
podman-compose up -d &>/dev/null
stop_spinner ok

wait_for "Waiting for app to become healthy" 180 5 \
    bash -c "[ \"\$(podman inspect --format='{{.State.Health.Status}}' ride-optimizer 2>/dev/null)\" = healthy ]" \
    || { echo -e "  ${RED}❌ ride-optimizer did not become healthy after 180s.${NC}"; exit 1; }

# Remove any images that are now untagged (the superseded build).
start_spinner "Cleaning up superseded images"
podman image prune -f 2>/dev/null || true
stop_spinner ok

# ── Summary ──────────────────────────────────────────────────────────────────

section "Summary" "🚲"
echo -e "  ${GREEN}✓ Deployment complete.${NC}"
