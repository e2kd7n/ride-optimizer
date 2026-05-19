#!/bin/bash
# Cleanup script for Raspberry Pi
# Removes containers, images, and build cache to free up storage.
# Volumes (data, config) are never touched. Cache and logs prompt before removal.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'

disk_percent() { df / | awk 'NR==2 {print $5}' | tr -d '%'; }
disk_kb()      { df / | awk 'NR==2 {print $3}'; }
show_disk()    { df -h / | awk 'NR==2 {printf "  Used: %s / %s (%s)\n", $3, $2, $5}'; }

echo "🧹 Starting Ride Optimizer Pi cleanup..."
echo ""

DISK_BEFORE_KB=$(disk_kb)
DISK_BEFORE_PCT=$(disk_percent)

echo -e "${YELLOW}Before cleanup:${NC}"
show_disk
echo ""

if [ "$DISK_BEFORE_PCT" -lt 60 ]; then
    echo -e "${GREEN}✓ Disk usage is healthy (${DISK_BEFORE_PCT}%)${NC}"
    echo -e "${BLUE}No cleanup needed at this time.${NC}"
    podman system df 2>/dev/null || true
    exit 0
elif [ "$DISK_BEFORE_PCT" -lt 70 ]; then
    echo -e "${YELLOW}⚠️  Disk usage is moderate (${DISK_BEFORE_PCT}%)${NC}"
else
    echo -e "${RED}❌ Disk usage is high (${DISK_BEFORE_PCT}%)${NC}"
fi
echo ""

# Stop and remove the app container
echo -e "${YELLOW}🛑 Stopping ride-optimizer...${NC}"
podman-compose -f docker-compose.yml down 2>/dev/null || true
podman rm -f ride-optimizer 2>/dev/null || true
echo -e "${GREEN}✓ Container stopped and removed${NC}"

# Prune unused images — guarded against in-progress pulls
echo -e "${YELLOW}🗑️  Pruning unused images...${NC}"
if pgrep -f "podman pull" > /dev/null 2>&1; then
    echo -e "${BLUE}ℹ️  Pull in progress — only removing images older than 2h${NC}"
    podman image prune -af --filter "until=2h" 2>/dev/null || true
else
    podman image prune -af 2>/dev/null || true
fi
echo -e "${GREEN}✓ Pruned unused images${NC}"

# Clean dangling resources
echo -e "${YELLOW}🧹 Cleaning dangling resources...${NC}"
podman system prune -f 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned dangling resources${NC}"

# Remove image tar files if present
echo -e "${YELLOW}🗑️  Checking for image tar files...${NC}"
if [ -d "./pi-images" ]; then
    TAR_COUNT=$(ls -1 ./pi-images/*.tar ./pi-images/*.tar.gz 2>/dev/null | wc -l)
    if [ "$TAR_COUNT" -gt 0 ]; then
        rm -f ./pi-images/*.tar ./pi-images/*.tar.gz 2>/dev/null || true
        echo -e "${GREEN}✓ Removed ${TAR_COUNT} tar file(s) from ./pi-images/${NC}"
    else
        echo -e "${BLUE}ℹ️  No tar files found${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  No pi-images directory found${NC}"
fi

# Clean build cache — guarded against in-progress builds
echo -e "${YELLOW}🧹 Cleaning build cache...${NC}"
if pgrep -f "podman build" > /dev/null 2>&1; then
    echo -e "${BLUE}ℹ️  Build in progress — skipping builder cache cleanup${NC}"
else
    podman builder prune -af 2>/dev/null || true
    echo -e "${GREEN}✓ Build cache cleaned${NC}"
fi

# NOTE: data/ and config/ volumes are intentionally never removed.
# To wipe them, do so manually after confirming a current backup exists.

# Optional: clear cache directory
echo ""
echo -e "${YELLOW}⚠️  Remove ./cache/? (safe to delete — rebuilt on next run)${NC}"
read -p "Remove cache? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ./cache/* 2>/dev/null || true
    echo -e "${GREEN}✓ Cache cleared${NC}"
else
    echo -e "${BLUE}ℹ️  Keeping cache${NC}"
fi

# Optional: rotate logs
echo ""
echo -e "${YELLOW}⚠️  Clear ./logs/? (application logs — not system journals)${NC}"
read -p "Clear logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ./logs/* 2>/dev/null || true
    echo -e "${GREEN}✓ Logs cleared${NC}"
else
    echo -e "${BLUE}ℹ️  Keeping logs${NC}"
fi

# Summary
DISK_AFTER_KB=$(disk_kb)
DISK_AFTER_PCT=$(disk_percent)
FREED_KB=$(( DISK_BEFORE_KB - DISK_AFTER_KB ))
FREED_MB=$(( FREED_KB / 1024 ))
PCT_FREED=$(( DISK_BEFORE_PCT - DISK_AFTER_PCT ))

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo ""
echo -e "${YELLOW}After cleanup:${NC}"
show_disk
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "   Freed: ~${FREED_MB} MB (${PCT_FREED}% reduction)"
echo -e "   Volumes preserved: data/, config/"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$DISK_AFTER_PCT" -lt 60 ]; then
    echo -e "${GREEN}✓ Disk usage is now healthy (${DISK_AFTER_PCT}%)${NC}"
elif [ "$DISK_AFTER_PCT" -lt 70 ]; then
    echo -e "${YELLOW}⚠️  Disk usage is moderate (${DISK_AFTER_PCT}%) — consider expanding storage${NC}"
else
    echo -e "${RED}⚠️  Disk usage is still high (${DISK_AFTER_PCT}%)${NC}"
    echo -e "${YELLOW}Additional steps to try:${NC}"
    echo -e "   sudo journalctl --vacuum-size=100M"
    echo -e "   sudo apt-get clean && sudo apt-get autoremove -y"
    echo -e "   du -sh /var/log/* | sort -rh | head -10"
fi

echo ""
echo -e "${GREEN}💡 To redeploy:${NC}"
echo -e "   ./scripts/pi-auto-update.sh --force"
