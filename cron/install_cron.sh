#!/bin/bash
# Install Ride Optimizer cron jobs for Smart Static architecture

set -e

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_PATH="$(which python3)"

echo "=========================================="
echo "Ride Optimizer Cron Installation"
echo "=========================================="
echo "Project root: $PROJECT_ROOT"
echo "Python path: $PYTHON_PATH"
echo ""

# Make cron scripts executable
echo "Making cron scripts executable..."
chmod +x "$PROJECT_ROOT/cron/daily_analysis.py"
chmod +x "$PROJECT_ROOT/cron/weather_refresh.py"
chmod +x "$PROJECT_ROOT/cron/cache_cleanup.py"
chmod +x "$PROJECT_ROOT/cron/system_health.py"

# Create crontab file from template
echo "Creating crontab configuration..."
CRONTAB_FILE="$PROJECT_ROOT/cron/crontab.generated"
sed -e "s|PROJECT_PATH|$PROJECT_ROOT|g" \
    -e "s|PYTHON_PATH|$PYTHON_PATH|g" \
    "$PROJECT_ROOT/cron/crontab.template" > "$CRONTAB_FILE"

echo ""
echo "Generated crontab configuration:"
echo "=========================================="
cat "$CRONTAB_FILE"
echo "=========================================="
echo ""

# Ask user to confirm installation
read -p "Install these cron jobs? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Backup existing crontab
echo "Backing up existing crontab..."
crontab -l > "$PROJECT_ROOT/cron/crontab.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

# Install new crontab (append to existing)
echo "Installing cron jobs..."
(crontab -l 2>/dev/null || true; echo ""; cat "$CRONTAB_FILE") | crontab -

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Installed cron jobs:"
crontab -l | grep -A 20 "Ride Optimizer"
echo ""
echo "To remove these jobs later, run:"
echo "  crontab -e"
echo "  # Delete the Ride Optimizer section"
echo ""
echo "To view cron logs:"
echo "  tail -f $PROJECT_ROOT/logs/cron.log"
echo ""

# Made with Bob
