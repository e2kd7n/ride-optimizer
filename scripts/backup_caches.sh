#!/bin/bash
# Backup analysis caches to private backups repository
# Usage: ./scripts/backup_caches.sh
#
# Backs up:
#   cache/route_groups_cache.json        — commute route grouping (incremental analysis)
#   cache/route_similarity_cache.json    — commute pair similarity scores
#   cache/long_ride_similarity_cache.json — long ride pair similarity scores
#   cache/geocoding_cache.json           — reverse-geocoded route names
#   data/cache/activities.json           — full Strava activity cache
#   data/route_groups.json               — web app route groups
#   data/long_rides.json                 — web app long rides

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_REPO_PATH="$HOME/dev/backups"
DEST="$BACKUP_REPO_PATH/ride-optimizer"

echo "💾 Backing up ride-optimizer caches — $TIMESTAMP"
echo "=================================================="
echo ""

# Check if backups repo exists
if [ ! -d "$BACKUP_REPO_PATH" ]; then
    echo "❌ Error: Backups repository not found at $BACKUP_REPO_PATH"
    echo ""
    echo "Clone it first:"
    echo "  git clone https://github.com/e2kd7n/backups.git ~/dev/backups"
    exit 1
fi

mkdir -p "$DEST/cache" "$DEST/data/cache"

backed_up=0

backup_file() {
    local src="$1"
    local dest="$2"
    if [ -f "$src" ]; then
        cp "$src" "$dest"
        echo "  ✅ $src"
        backed_up=$((backed_up + 1))
    else
        echo "  ⚠️  $src (not found, skipped)"
    fi
}

# cache/ files
backup_file "cache/route_groups_cache.json"        "$DEST/cache/route_groups_cache.json"
backup_file "cache/route_similarity_cache.json"    "$DEST/cache/route_similarity_cache.json"
backup_file "cache/long_ride_similarity_cache.json" "$DEST/cache/long_ride_similarity_cache.json"
backup_file "cache/geocoding_cache.json"           "$DEST/cache/geocoding_cache.json"

# data/ files
backup_file "data/cache/activities.json"           "$DEST/data/cache/activities.json"
backup_file "data/route_groups.json"               "$DEST/data/route_groups.json"
backup_file "data/long_rides.json"                 "$DEST/data/long_rides.json"

echo ""
echo "$backed_up file(s) staged for commit"

# Only commit if something actually changed
cd "$BACKUP_REPO_PATH"
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ No changes — caches already up to date in backup repo"
else
    git add "ride-optimizer/cache/" "ride-optimizer/data/"
    git commit -m "Backup ride-optimizer caches — $TIMESTAMP"
    git push
    echo ""
    echo "✅ Cache backup complete!"
fi

# Made with Bob
