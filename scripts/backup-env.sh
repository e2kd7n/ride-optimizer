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

# Credential files that must survive server rebuilds
declare -a CRED_FILES=(
    "config/credentials.json"                  # Strava OAuth tokens
    "config/.token_encryption_key"             # Strava token encryption key
    "config/.cache_encryption_key"             # Cache encryption key
    "config/trainerroad_credentials.json"      # TrainerRoad ICS feed URL (encrypted)
    "config/.trainerroad_encryption_key"       # TrainerRoad encryption key
    "config/trainerroad_encryption_key"        # TrainerRoad encryption key (alt path)
    "config/intervals_credentials.json"        # intervals.icu credentials (encrypted)
    "config/.intervals_encryption_key"         # intervals.icu encryption key
    "config/.garmin_tokens/credentials.json"   # Garmin tokens
)

for cred_file in "${CRED_FILES[@]}"; do
    if [ -f "$cred_file" ]; then
        # Flatten path: config/foo.json -> config_foo.json
        flat_name="${cred_file//\//_}"
        cp "$cred_file" "$DEST/${flat_name}.backup-$TIMESTAMP"
        echo "  $cred_file -> ${flat_name}.backup-$TIMESTAMP"
        COPIED=$((COPIED + 1))
    fi
done

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