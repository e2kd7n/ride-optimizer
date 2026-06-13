#!/bin/bash
# Backup .env file to private backups repository
# Usage: ./scripts/backup_env.sh

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_REPO_PATH="$HOME/dev/backups"
BACKUP_FILE=".env.backup-$TIMESTAMP"

echo "🔒 Backing up .env file to private backups repository"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in current directory"
    exit 1
fi

# Check if backups repo exists
if [ ! -d "$BACKUP_REPO_PATH" ]; then
    echo "❌ Error: Backups repository not found at $BACKUP_REPO_PATH"
    echo ""
    echo "Clone it first:"
    echo "  cd ~"
    echo "  git clone https://github.com/e2kd7n/backups.git"
    exit 1
fi

# Create ride-optimizer subdirectory if it doesn't exist
mkdir -p "$BACKUP_REPO_PATH/ride-optimizer"

# Copy .env file
cp .env "$BACKUP_REPO_PATH/ride-optimizer/$BACKUP_FILE"
echo "✅ Copied .env to $BACKUP_REPO_PATH/ride-optimizer/$BACKUP_FILE"

# Commit and push
cd "$BACKUP_REPO_PATH"
git add "ride-optimizer/$BACKUP_FILE"
git commit -m "Backup ride-optimizer .env - $TIMESTAMP"
git push

echo ""
echo "✅ Backup complete!"
echo ""
echo "Backup location: $BACKUP_REPO_PATH/ride-optimizer/$BACKUP_FILE"

# Made with Bob