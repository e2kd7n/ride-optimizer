#!/bin/bash
# Raspberry Pi optimized build script for Podman
# Addresses common ARM architecture and rootless networking issues
#
# ============================================================================
# LAST-RESORT ONLY — DO NOT USE FOR NORMAL DEPLOYMENTS
# ============================================================================
# CI/CD (GitHub Actions) builds multi-arch images (amd64 + arm64) and pushes
# them to ghcr.io/e2kd7n/ride-optimizer:latest.  Building locally on the Pi:
#   - takes 15–30 minutes and pins one CPU core
#   - produces an arm64-only local image tagged "ride-optimizer:latest"
#   - WILL be silently overwritten by the next pi-auto-update.sh run
#
# Normal deploy workflow:
#   git push  →  CI builds  →  ./scripts/pi-auto-update.sh [--force]
#
# Use this script ONLY when GHCR is unreachable or CI is broken and you need
# an immediate local fix.  Remember to re-pull from GHCR once CI is restored.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
# shellcheck source=utilities.sh
source "$SCRIPT_DIR/utilities.sh"

section "Local Pi Build" "📦"
echo -e "  ${YELLOW}⚠️  This bypasses CI/CD and GHCR.${NC}"
echo -e "  ${YELLOW}   This image will be overwritten by the next auto-update run.${NC}"
echo ""
echo -e "  ${BLUE}Preferred workflow:${NC}"
echo -e "  ${BLUE}  git push  ->  CI builds  ->  ./scripts/pi-auto-update.sh --force${NC}"
echo ""
read -p "  Build locally instead of pulling from GHCR? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "  ${BLUE}Aborted.  Run: ./scripts/pi-auto-update.sh --force${NC}"
    exit 1
fi

# ── Pre-flight ───────────────────────────────────────────────────────────────

section "Pre-flight Check" "🔍"

ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo -e "  ${YELLOW}⚠️  Not running on ARM architecture (detected: $ARCH)${NC}"
    echo -e "  ${YELLOW}   This script is optimized for Raspberry Pi${NC}"
    read -p "  Continue anyway? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
else
    echo -e "  ${GREEN}✓${NC}  ARM architecture ($ARCH)"
fi

if ! command -v podman &> /dev/null; then
    echo -e "  ${RED}❌ podman is not installed${NC}"
    echo -e "  ${YELLOW}   Install with: sudo apt-get install -y podman${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC}  podman installed"

if ! command -v podman-compose &> /dev/null; then
    echo -e "  ${YELLOW}⚠️  podman-compose is not installed${NC}"
    echo -e "  ${YELLOW}   Install with: pipx install podman-compose${NC}"
    echo -e "  ${YELLOW}   Or: pip3 install --user podman-compose${NC}"
    read -p "  Continue with podman only? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
    USE_COMPOSE=false
else
    echo -e "  ${GREEN}✓${NC}  podman-compose installed"
    USE_COMPOSE=true
fi

if [ ! -f .env ]; then
    echo -e "  ${YELLOW}⚠️  .env file not found${NC}"
    if [ -f .env.example ]; then
        echo -e "  ${YELLOW}   Creating .env from .env.example${NC}"
        cp .env.example .env
        echo -e "  ${YELLOW}   ⚠️  Please edit .env with your Strava credentials before running!${NC}"
    else
        echo -e "  ${RED}❌ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "  ${GREEN}✓${NC}  .env present"
fi

# ── Build ────────────────────────────────────────────────────────────────────

section "Building Image" "📦"
echo -e "  ${BLUE}This may take 15-30 minutes on Raspberry Pi${NC}"
timer_start

BUILD_OK=true
if [ "$USE_COMPOSE" = true ]; then
    echo -e "  ${DIM}Using podman-compose...${NC}"
    if ! podman-compose build --no-cache; then
        echo ""
        echo -e "  ${YELLOW}⚠️  Build failed with podman-compose — trying podman directly${NC}"
        podman build --network=host --no-cache -t ride-optimizer:latest . || BUILD_OK=false
    fi
else
    echo -e "  ${DIM}Using podman directly...${NC}"
    podman build --network=host --no-cache -t ride-optimizer:latest . || BUILD_OK=false
fi

timer_end

# ── Summary ──────────────────────────────────────────────────────────────────

if [ "$BUILD_OK" = true ]; then
    section "Summary" "🚲"
    echo -e "  ${GREEN}✓ Build successful!${NC}"
    echo ""
    echo -e "  ${BLUE}Next steps:${NC}"
    echo "    1. Edit .env with your Strava credentials (if not done)"
    echo "    2. Run: podman-compose up -d"
    echo "       Or: podman run -d --name ride-optimizer --env-file .env \\"
    echo "           -v ./data:/app/data:Z -v ./cache:/app/cache:Z \\"
    echo "           -v ./logs:/app/logs:Z -v ./config:/app/config:Z \\"
    echo "           --network=host ride-optimizer:latest"
    echo "    3. Access menu: podman exec -it ride-optimizer python scripts/menu.py"
else
    section "Summary" "🚲"
    echo -e "  ${RED}✗ Build failed!${NC}"
    echo ""
    echo -e "  ${YELLOW}Troubleshooting tips:${NC}"
    echo "    1. Check available disk space: df -h"
    echo "    2. Check available memory: free -h"
    echo "    3. Increase swap if needed:"
    echo "       sudo dphys-swapfile swapoff"
    echo "       sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048"
    echo "       sudo dphys-swapfile setup"
    echo "       sudo dphys-swapfile swapon"
    echo "    4. Try building as root: sudo podman build --network=host -t ride-optimizer:latest ."
    echo "    5. Check logs: journalctl --user -u podman"
    exit 1
fi
