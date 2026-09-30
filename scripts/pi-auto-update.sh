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

# ── Sync config ──────────────────────────────────────────────────────────────
# config/ (and this whole checkout) is bind-mounted, not baked into the image
# (docker-compose.yml) — pulling a new image alone leaves config.yaml frozen at
# whatever it was when this checkout was last updated, so any config-touching
# fix silently never takes effect on the Pi until someone happens to git pull
# by hand (#597). Fast-forward only: never clobber a diverged checkout.
section "Syncing Config" "🔄"

if git fetch origin main --quiet 2>/dev/null; then
    if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
        echo -e "  ${GREEN}✓${NC}  Checkout already up to date"
    elif git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
        # config/ is owned by the rootless-Podman subuid, not this user —
        # open it up long enough for git to write; the chown step below
        # (after podman-compose down) restores the subuid ownership, and
        # this closes the world-write bit back up right after the merge.
        sudo chmod -R o+w config 2>/dev/null || true
        if git merge --ff-only origin/main &>/dev/null; then
            echo -e "  ${GREEN}✓${NC}  Checkout fast-forwarded to $(git rev-parse --short HEAD)"
        else
            echo -e "  ${YELLOW}⚠️  Fast-forward failed — config may be stale. Investigate manually.${NC}"
        fi
        sudo chmod -R o-w config 2>/dev/null || true
    else
        echo -e "  ${YELLOW}⚠️  Local checkout has diverged from origin/main — not auto-updating. Investigate manually.${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  git fetch failed — skipping checkout sync, config may be stale${NC}"
fi

# ── Pull image ───────────────────────────────────────────────────────────────

section "Pulling Image" "📥"
echo -e "  ${BLUE}Image: ${REMOTE_IMAGE}${NC}"

# Retry with backoff: a single transient GHCR/network failure (e.g. the
# "TLS handshake timeout" while authenticating that killed the 2026-09-30
# run) used to abort the whole night's update. Keep podman's output instead
# of discarding it so a failure says *why* in the journal.
PULL_ATTEMPTS=4
PULL_LOG=$(mktemp)
pulled=false
timer_start
for attempt in $(seq 1 "$PULL_ATTEMPTS"); do
    start_spinner "Pulling ${REMOTE_IMAGE} (attempt ${attempt}/${PULL_ATTEMPTS})"
    if podman pull "$REMOTE_IMAGE" >"$PULL_LOG" 2>&1; then
        stop_spinner ok
        pulled=true
        break
    fi
    stop_spinner fail
    echo -e "  ${YELLOW}⚠️  $(tail -n 1 "$PULL_LOG")${NC}"
    if [ "$attempt" -lt "$PULL_ATTEMPTS" ]; then
        delay=$((attempt * 120))
        echo -e "  Retrying in ${delay}s..."
        sleep "$delay"
    fi
done
timer_end
if [ "$pulled" != true ]; then
    echo -e "  ${RED}❌ Pull failed after ${PULL_ATTEMPTS} attempts. Last podman output:${NC}"
    tail -n 15 "$PULL_LOG" | sed 's/^/     /'
    rm -f "$PULL_LOG"
    exit 1
fi
rm -f "$PULL_LOG"

# Compare what's *running* against what's now pulled — not the image ID
# before vs after this run's pull. The old before/after check never
# redeployed once the new image was already on disk (a manual pull, or an
# earlier run whose pull succeeded but whose deploy failed), so the Pi could
# sit on a stale container indefinitely while every run reported "unchanged".
PULLED_ID=$(podman image inspect "$REMOTE_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")
RUNNING_ID=$(podman inspect ride-optimizer --format '{{.Image}}' 2>/dev/null || echo "")

if [ -n "$RUNNING_ID" ] && [ "$RUNNING_ID" = "$PULLED_ID" ] && [ "$FORCE" = false ]; then
    section "Summary" "🚲"
    echo -e "  ${GREEN}✓${NC}  Already running the latest image (${PULLED_ID:0:12}) — containers not restarted."
    exit 0
fi

echo -e "  ${BLUE}Deploying image: ${RUNNING_ID:0:12} → ${PULLED_ID:0:12}${NC}"
# The superseded image is still in use by the running container here; it
# becomes dangling once the new container is up and is pruned below.

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
