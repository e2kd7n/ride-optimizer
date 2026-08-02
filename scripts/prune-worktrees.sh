#!/bin/bash
# Worktree hygiene: removes git worktrees that are safe to remove and
# reports everything else for manual review. Never touches a worktree
# with uncommitted changes or commits not reflected in a merged/closed PR.
#
# Usage:
#   prune-worktrees.sh <repo-path> [--apply]
#   prune-worktrees.sh --all [--apply]   # every git repo directly under
#                                         # the parent of this script's dir
#
# Default is dry-run (report only). Pass --apply to actually remove
# worktrees and delete their local/remote branches.
#
# "Safe to remove" = branch has a merged or closed PR, AND the worktree
# has no uncommitted changes (besides .claude/settings.local.json, which
# is local-only noise), AND no commits ahead of the default branch that
# aren't already on it. Anything else is reported as needs-review.
#
# A worktree locked by a session whose owning PID is no longer running
# is treated as unlocked (stale lock) for the purposes of this check.

set -uo pipefail

DEV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APPLY=""
TARGETS=()

for arg in "$@"; do
  case "$arg" in
    --apply) APPLY="--apply" ;;
    --all) TARGETS=() ;;
    *) TARGETS+=("$arg") ;;
  esac
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  for d in "$DEV_ROOT"/*/; do
    [ -d "$d/.git" ] && TARGETS+=("${d%/}")
  done
fi

prune_repo() {
  local repo="$1"
  cd "$repo" || return
  [ -d .git ] || return

  local default_branch
  default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$default_branch" ] && default_branch="main"
  git fetch origin --quiet 2>/dev/null || true

  local wt_list
  wt_list=$(git worktree list --porcelain)
  [ -z "$wt_list" ] && return

  local any_extra=0
  echo "=== $repo (default: $default_branch) ==="

  local wt="" branch=""
  while IFS= read -r line; do
    case "$line" in
      worktree\ *) wt="${line#worktree }" ;;
      branch\ *)
        branch="${line#branch }"
        branch="${branch#refs/heads/}"
        ;;
      "")
        if [ -n "$wt" ] && [ "$wt" != "$repo" ] && [ "$branch" != "$default_branch" ]; then
          any_extra=1
          evaluate_worktree "$repo" "$wt" "$branch" "$default_branch"
        fi
        wt=""; branch=""
        ;;
    esac
  done <<< "$wt_list"$'\n'

  [ "$any_extra" = 0 ] && echo "  (no extra worktrees)"
  echo
}

evaluate_worktree() {
  local repo="$1" wt="$2" branch="$3" default_branch="$4"

  local lockfile="$repo/.git/worktrees/$(basename "$wt")/locked"
  if [ -f "$lockfile" ]; then
    local pid
    pid=$(grep -oE 'pid [0-9]+' "$lockfile" | grep -oE '[0-9]+' | head -1)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "  [active-session] $branch — locked, owning pid $pid still running, skipping"
      return
    fi
    echo "  [stale-lock] $branch — locked but owning pid ${pid:-unknown} is dead"
  fi

  local dirty ahead pr_state
  dirty=$(git -C "$wt" status --porcelain 2>/dev/null | grep -v '\.claude/settings\.local\.json')
  ahead=$(git -C "$wt" log "origin/$default_branch..HEAD" --oneline 2>/dev/null)
  pr_state=$(gh pr list --repo "$(git -C "$repo" remote get-url origin 2>/dev/null | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')" \
    --state all --head "$branch" --json state --jq '.[0].state' 2>/dev/null)

  if [ "$pr_state" = "MERGED" ] || [ "$pr_state" = "CLOSED" ]; then
    if [ -z "$dirty" ] && [ -z "$ahead" ]; then
      echo "  [safe-remove] $branch — PR $pr_state, clean, nothing unmerged"
      if [ "$APPLY" = "--apply" ]; then
        remove_worktree "$repo" "$wt" "$branch"
      fi
    else
      echo "  [needs-review] $branch — PR $pr_state, but has uncommitted or unpushed work:"
      [ -n "$dirty" ] && echo "$dirty" | sed 's/^/      /'
      [ -n "$ahead" ] && echo "$ahead" | sed 's/^/      unpushed: /'
    fi
  else
    echo "  [keep] $branch — PR state: ${pr_state:-none/open}"
  fi
}

remove_worktree() {
  local repo="$1" wt="$2" branch="$3"
  cd "$repo" || return

  if ! git worktree remove --force "$wt" 2>/dev/null; then
    if command -v robocopy >/dev/null 2>&1; then
      # Windows: git worktree remove's recursive delete hits MAX_PATH on
      # deep node_modules trees even with core.longpaths set. robocopy's
      # mirror-of-empty trick deletes via the long-path-aware Win32 API.
      echo "    long-path removal failed, falling back to robocopy mirror (Windows)..."
      local empty
      empty=$(mktemp -d)
      robocopy "$empty" "$wt" /MIR /NFL /NDL /NJH /NJS >/dev/null 2>&1
      rm -rf "$empty" 2>/dev/null
      rmdir "$wt" 2>/dev/null
    else
      # macOS/Linux: no MAX_PATH limit, so a plain rm -rf covers whatever
      # else made git's own removal fail.
      echo "    git worktree remove failed, falling back to rm -rf..."
      rm -rf "$wt" 2>/dev/null
    fi
    git worktree prune
  fi

  git branch -D "$branch" 2>/dev/null
  git push origin --delete "$branch" 2>/dev/null
  echo "    removed worktree and branch: $branch"
}

for repo in "${TARGETS[@]}"; do
  prune_repo "$repo"
done

if [ -z "$APPLY" ]; then
  echo "(dry run — pass --apply to actually remove the [safe-remove] worktrees above)"
fi
