#!/bin/bash
# Raspberry Pi optimized build script for Podman
# Addresses common ARM architecture and rootless networking issues

set -e

echo "🍓 Raspberry Pi Podman Build Script"
echo "===================================="
echo ""

# Check if running on ARM
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo "⚠️  Warning: Not running on ARM architecture (detected: $ARCH)"
    echo "   This script is optimized for Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Error: podman is not installed"
    echo "   Install with: sudo apt-get install -y podman"
    exit 1
fi

# Check if podman-compose is installed
if ! command -v podman-compose &> /dev/null; then
    echo "⚠️  Warning: podman-compose is not installed"
    echo "   Install with: pipx install podman-compose"
    echo "   Or: pip3 install --user podman-compose"
    read -p "Continue with podman only? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    if [ -f .env.example ]; then
        echo "   Creating .env from .env.example"
        cp .env.example .env
        echo "   ⚠️  Please edit .env with your Strava credentials before running!"
    else
        echo "   ❌ Error: .env.example not found"
        exit 1
    fi
fi

echo ""
echo "📦 Building container image..."
echo "   This may take 15-30 minutes on Raspberry Pi"
echo ""

# Build with network=host to avoid slirp4netns issues
if [ "$USE_COMPOSE" = true ]; then
    echo "Using podman-compose..."
    # Build with host network to avoid slirp4netns issues
    podman-compose build --no-cache || {
        echo ""
        echo "❌ Build failed with podman-compose"
        echo "   Trying alternative build method..."
        podman build --network=host --no-cache -t ride-optimizer:latest .
    }
else
    echo "Using podman directly..."
    podman build --network=host --no-cache -t ride-optimizer:latest .
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env with your Strava credentials (if not done)"
    echo "  2. Run: podman-compose up -d"
    echo "     Or: podman run -d --name ride-optimizer --env-file .env \\"
    echo "         -v ./data:/app/data:Z -v ./cache:/app/cache:Z \\"
    echo "         -v ./logs:/app/logs:Z -v ./config:/app/config:Z \\"
    echo "         --network=host ride-optimizer:latest"
    echo "  3. Access menu: podman exec -it ride-optimizer python scripts/menu.py"
else
    echo ""
    echo "❌ Build failed!"
    echo ""
    echo "Troubleshooting tips:"
    echo "  1. Check available disk space: df -h"
    echo "  2. Check available memory: free -h"
    echo "  3. Increase swap if needed:"
    echo "     sudo dphys-swapfile swapoff"
    echo "     sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048"
    echo "     sudo dphys-swapfile setup"
    echo "     sudo dphys-swapfile swapon"
    echo "  4. Try building as root: sudo podman build --network=host -t ride-optimizer:latest ."
    echo "  5. Check logs: journalctl --user -u podman"
    exit 1
fi

# Made with Bob
