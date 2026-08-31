#!/bin/bash
# Worktree hygiene: removes git worktrees that are safe to remove and
# reports everything else for manual review. Never touches a worktree
# with uncommitted changes or commits not reflected in a merged/closed PR.
# Also detects orphaned directories under .claude/worktrees/ that AREN'T
# registered git worktrees at all — leftovers from a removal that hit the
# Windows MAX_PATH limit partway, or a worktree-creation that never fully
# registered — which the git-worktree-list scan above can't see.
#
# Usage:
#   prune-worktrees.sh <repo-path> [--apply]
#   prune-worktrees.sh --all [--apply]   # every git repo directly under
#                                         # the parent of this script's dir
#
# Default is dry-run (report only). Pass --apply to actually remove
# worktrees and delete their local/remote branches. Orphaned directories
# get their own separate confirmation prompt (see below) since deleting
# them is unrecoverable — there's no branch/commit to fall back on.
#
# "Safe to remove" = branch has a merged or closed PR, AND the worktree
# has no uncommitted changes (besides .claude/settings.local.json, which
# is local-only noise), AND no commits ahead of the default branch that
# aren't already on it. Anything else is reported as needs-review.
#
# A worktree locked by a session whose owning PID is no longer running
# is treated as unlocked (stale lock) for the purposes of this check.
#
# Orphaned (non-worktree) directories have no git pointer at all, so
# there's no branch/PR signal to check — only their content's own
# modification time. One that hasn't changed in $STALE_ORPHAN_DAYS days is
# offered for removal; anything more recent is always left alone (could be
# a worktree mid-creation, or in-progress content dropped there by hand).

set -uo pipefail

DEV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# An orphaned directory younger than this is always left alone, no matter
# what --apply says — it might be a worktree still mid-creation.
STALE_ORPHAN_DAYS=7

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

ORPHAN_DIRS=()
ORPHAN_AGE_DAYS=()

# `pwd` in Git Bash returns MSYS-style paths (/c/Users/...), but git.exe
# always reports its own `git worktree list` paths Windows-style
# (C:/Users/...) since it's a native Windows binary. Without normalizing,
# string comparisons against git's output (skipping the repo root, matching
# orphan dirs against the registered list) silently never match on Windows.
# `pwd -W` is the Git-Bash builtin that returns the Windows-style form;
# elsewhere (macOS/Linux) git and pwd already agree, so plain pwd is used.
portable_pwd() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) pwd -W ;;
    *) pwd ;;
  esac
}

# Age in whole days since the newest file under a directory was modified
# (falls back to the directory's own mtime if it has no files, e.g. empty).
# Handles both GNU stat (Linux/Git-Bash) and BSD stat (macOS).
dir_age_days() {
  local d="$1" newest now
  newest=$(find "$d" -type f -exec stat -c '%Y' {} \; 2>/dev/null | sort -n | tail -1)
  if [ -z "$newest" ]; then
    newest=$(stat -c '%Y' "$d" 2>/dev/null || stat -f '%m' "$d" 2>/dev/null || echo "")
  fi
  [ -z "$newest" ] && { echo 0; return; }
  now=$(date +%s)
  echo $(( (now - newest) / 86400 ))
}

# Shared delete: tries a normal recursive remove first, falls back to a
# robocopy mirror-of-empty (Windows, dodges MAX_PATH) or plain rm -rf
# (macOS/Linux, no MAX_PATH issue so nothing else should make this fail).
force_remove_dir() {
  local target="$1"
  if rm -rf "$target" 2>/dev/null && [ ! -d "$target" ]; then
    return 0
  fi
  if command -v robocopy >/dev/null 2>&1; then
    echo "    plain removal failed, falling back to robocopy mirror (Windows)..."
    local empty
    empty=$(mktemp -d)
    robocopy "$empty" "$target" /MIR /NFL /NDL /NJH /NJS >/dev/null 2>&1
    rm -rf "$empty" 2>/dev/null
    rmdir "$target" 2>/dev/null
  else
    echo "    plain removal failed, retrying rm -rf..."
    rm -rf "$target" 2>/dev/null
  fi
}

# Find directories under <repo>/.claude/worktrees/ that aren't in git's own
# worktree list — i.e. plain content left behind by a removal that didn't
# fully complete, or a worktree that never finished registering.
scan_orphan_dirs() {
  local repo="$1" registered="$2"
  local wt_base="$repo/.claude/worktrees"
  [ -d "$wt_base" ] || return

  local d
  for d in "$wt_base"/*/; do
    d="${d%/}"
    [ -d "$d" ] || continue
    grep -Fxq "$d" <<< "$registered" && continue

    local age
    age=$(dir_age_days "$d")
    local size
    size=$(du -sh "$d" 2>/dev/null | cut -f1)
    if [ "$age" -ge "$STALE_ORPHAN_DAYS" ]; then
      echo "  [orphan] ${d#"$repo"/} — not a registered git worktree, ${size:-?}, untouched ${age}d — candidate for removal"
      ORPHAN_DIRS+=("$d")
      ORPHAN_AGE_DAYS+=("$age")
    else
      echo "  [orphan-recent] ${d#"$repo"/} — not a registered git worktree, ${size:-?}, modified ${age}d ago (too recent, left alone)"
    fi
  done
}

prune_repo() {
  local repo="$1"
  cd "$repo" || return
  [ -d .git ] || return
  # Re-derive repo in the same path representation git worktree list uses
  # (see portable_pwd above) so later string comparisons actually match.
  repo="$(portable_pwd)"

  local default_branch
  default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$default_branch" ] && default_branch="main"
  git fetch origin --quiet 2>/dev/null || true

  local wt_list
  wt_list=$(git worktree list --porcelain)
  [ -z "$wt_list" ] && return

  local registered_paths
  registered_paths=$(grep '^worktree ' <<< "$wt_list" | sed 's/^worktree //')

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

  scan_orphan_dirs "$repo" "$registered_paths"
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

  # git worktree remove's recursive delete hits Windows's MAX_PATH limit on
  # deep node_modules trees even with core.longpaths set; force_remove_dir
  # falls back to a robocopy mirror-of-empty trick there.
  if ! git worktree remove --force "$wt" 2>/dev/null; then
    force_remove_dir "$wt"
    git worktree prune
  fi

  git branch -D "$branch" 2>/dev/null
  git push origin --delete "$branch" 2>/dev/null
  echo "    removed worktree and branch: $branch"
}

for repo in "${TARGETS[@]}"; do
  prune_repo "$repo"
done

if [ ${#ORPHAN_DIRS[@]} -gt 0 ]; then
  if [ "$APPLY" = "--apply" ]; then
    echo "About to permanently delete ${#ORPHAN_DIRS[@]} orphaned director(s) — these aren't git worktrees, so this is NOT recoverable via git:"
    for i in "${!ORPHAN_DIRS[@]}"; do
      echo "  - ${ORPHAN_DIRS[$i]} (untouched ${ORPHAN_AGE_DAYS[$i]}d)"
    done
    read -p "Delete these now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      for d in "${ORPHAN_DIRS[@]}"; do
        force_remove_dir "$d"
        echo "    removed orphaned directory: $d"
      done
    else
      echo "Aborted — no orphaned directories removed."
    fi
  else
    echo "(${#ORPHAN_DIRS[@]} orphaned director(s) above are stale enough to remove — pass --apply to remove them)"
  fi
fi

if [ -z "$APPLY" ]; then
  echo "(dry run — pass --apply to actually remove the [safe-remove] worktrees and stale [orphan] directories above)"
fi
