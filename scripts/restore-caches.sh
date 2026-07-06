#!/bin/bash
# Restore ride-optimizer caches from the private backups repository.
# Works on both Mac (~/dev/backups) and Pi (~/dev/backups or ~/backups).
#
# Usage:
#   ./scripts/restore-caches.sh           # restore all files
#   ./scripts/restore-caches.sh --dry-run # show what would be restored

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Locate the backups repo — check the two common locations
BACKUP_REPO_PATH=""
for candidate in "$HOME/dev/backups" "$HOME/backups"; do
    if [[ -d "$candidate/ride-optimizer" ]]; then
        BACKUP_REPO_PATH="$candidate"
        break
    fi
done

if [[ -z "$BACKUP_REPO_PATH" ]]; then
    echo "❌ Backups repo not found. Expected at ~/dev/backups or ~/backups."
    echo "   Clone it first:"
    echo "     git clone https://github.com/e2kd7n/backups.git ~/dev/backups"
    exit 1
fi

SRC="$BACKUP_REPO_PATH/ride-optimizer"
echo "📦 Restoring from: $SRC"
$DRY_RUN && echo "   (dry run — no files will be written)"
echo ""

restored=0
skipped=0

restore_file() {
    local src="$1"
    local dest="$2"
    local mode="${3:-}"

    if [[ ! -f "$src" ]]; then
        echo "  ⚠️  $(basename "$src") (not in backup, skipped)"
        skipped=$((skipped + 1))
        return
    fi

    if $DRY_RUN; then
        echo "  🔍 $dest  ← $src"
        restored=$((restored + 1))
        return
    fi

    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    [[ -n "$mode" ]] && chmod "$mode" "$dest"
    echo "  ✅ $dest"
    restored=$((restored + 1))
}

# ── Activity cache (the main one that keeps disappearing) ──────────────────
restore_file "$SRC/data/cache/activities.json"   "data/cache/activities.json"

# ── Computed caches (expensive to regenerate) ─────────────────────────────
restore_file "$SRC/cache/route_similarity_cache.json"       "cache/route_similarity_cache.json"
restore_file "$SRC/cache/long_ride_similarity_cache.json"   "cache/long_ride_similarity_cache.json"
restore_file "$SRC/cache/geocoding_cache.json"              "cache/geocoding_cache.json"
restore_file "$SRC/cache/route_groups_cache.json"           "cache/route_groups_cache.json"

# ── Saved user data ────────────────────────────────────────────────────────
restore_file "$SRC/data/route_groups.json"    "data/route_groups.json"
restore_file "$SRC/data/long_rides.json"      "data/long_rides.json"
restore_file "$SRC/favorite_routes.json"      "data/favorite_routes.json"

echo ""
if $DRY_RUN; then
    echo "Dry run complete — $restored file(s) would be restored, $skipped skipped."
else
    echo "✅ Restore complete — $restored file(s) restored, $skipped skipped."
fi
