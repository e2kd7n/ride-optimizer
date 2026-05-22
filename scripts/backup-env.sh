#!/bin/bash
# Backup .env and all *.backup files to private backups repository
# Usage: ./scripts/backup-env.sh

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Load .env if present so BACKUP_REPO_PATH can be overridden there
if [ -f ".env" ]; then
    set -a
    # shellcheck source=.env
    source .env
    set +a
fi

if [ -z "$BACKUP_REPO_PATH" ]; then
    echo "Error: BACKUP_REPO_PATH is not set. Add it to your .env file."
    exit 1
fi

DEST="$BACKUP_REPO_PATH/ride-optimizer"

echo "Backing up to ride-optimizer in backup repo"
echo ""

if [ ! -d "$BACKUP_REPO_PATH" ]; then
    echo "Error: Backup repository not found at the path set in BACKUP_REPO_PATH."
    exit 1
fi

mkdir -p "$DEST"

COPIED=0

# .env
if [ -f ".env" ]; then
    cp .env "$DEST/.env.backup-$TIMESTAMP"
    echo "  .env -> .env.backup-$TIMESTAMP"
    COPIED=$((COPIED + 1))
fi

# all *.backup files in the repo tree
while IFS= read -r -d '' file; do
    filename=$(basename "$file")
    cp "$file" "$DEST/${filename}-$TIMESTAMP"
    echo "  $file -> ${filename}-$TIMESTAMP"
    COPIED=$((COPIED + 1))
done < <(find . -name "*.backup" -not -path "./.git/*" -not -path "./venv/*" -print0)

if [ "$COPIED" -eq 0 ]; then
    echo "Nothing to back up."
    exit 0
fi

echo ""

cd "$BACKUP_REPO_PATH"
git add "ride-optimizer/"
git commit -m "Backup ride-optimizer - $TIMESTAMP"
git push

echo ""
echo "Done. $COPIED file(s) backed up."