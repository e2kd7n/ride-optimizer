# Workflow Guidelines — ride-optimizer

Descriptive, not aspirational: this documents how git/GitHub have actually been used on
`ride-optimizer`, derived from the repo's commit graph, merged PRs, and CI config as of
2026-07-09. Where the project's own docs (`docs/guides/PR_REVIEW_PROCESS.md`) prescribe
something different from what actually happens, that's called out explicitly below — treat
this file as the current source of truth for practice, and reconcile the other doc
separately if it should change.

## Branching model: trunk-based, not classic Gitflow

There is no `develop` branch and no long-lived `release/*` branches. Every branch forks
from `main` and merges back into `main`. Despite the "gitflow" shorthand in conversation,
what's actually run is closer to **GitHub Flow**: one integration branch, short-lived
feature/fix branches, continuous deploy off `main`.

```
main ─●─●─●───●───────●─●───────●──▶
       \       \       \         \
        feat/x  fix/y   epic-z    fix/w
         \       \       \         \
          ●───────●───────●─────────●   (merge commit back to main)
```

## Branch naming

Pattern: `<type>/<issue-or-epic-number>-<short-description>`, or for multi-issue epic work,
`<epic-name>-<epic-issue-number>` without a type prefix. Observed examples:

| Branch | Purpose |
|---|---|
| `feat/107-interactive-route-map` | Single-issue feature |
| `fix/264-ux-audit` | Single-issue fix |
| `fix/304-306-ux-and-dead-code` | Fix branch covering multiple issue numbers |
| `docs/192-pr-review-requirements` | Docs-only change |
| `test/208-163-161-162-fixtures-and-coverage` | Test-coverage branch spanning several issues |
| `refactor/launch-py-blueprints` | Structural refactor, no single issue number |
| `design-review-epic-352` | Epic branch, named after the epic issue |
| `explore-enhancements-412` | Epic branch |
| `fair-weather-completion-449` | Epic branch |
| `fix/epic-413-dod-completion` | Follow-up branch closing out an epic's Definition of Done |

Types in use: `feat`, `fix`, `docs`, `test`, `refactor`. Epic-scale work often skips the
type prefix and just uses `<theme>-<epic-issue-number>`.

## PR & merge workflow (actual practice)

1. Branch off `main` using the naming pattern above.
2. Open a PR via `gh pr create`, using `.github/pull_request_template.md`
   (Summary / Changes / Test Plan / Checklist, with `Fixes #<n>` linking the issue).
3. CI (`.github/workflows/docker-publish.yml`) runs the `test` job on every PR against
   `main`. `build-and-push` only runs on push to `main` (not on PRs) since it needs GHCR
   write access.
4. **Merge commits are used, not squash** — confirmed from the commit graph (e.g. `fda97f1
   Merge pull request #456`, `3754342 Merge pull request #455`, both 2-parent merges).
   This **contradicts** `docs/guides/PR_REVIEW_PROCESS.md`, which currently states "Squash
   merge or rebase merge (no merge commits)." A few early PRs (#324, #325) were in fact
   squash-merged, but the pattern since has consistently been merge commits — the doc is
   stale, not the practice.
5. **Branch protection on `main` is intentionally OFF** (`gh api repos/.../branches/main/protection`
   → 404 "Branch not protected"), despite `PR_REVIEW_PROCESS.md` describing 1 required
   approval + required `test` status check as enabled. It was turned on once (PR #323,
   2026-06-17) and has since been left off by choice for this solo-maintainer project — don't
   re-enable it without asking, and don't assume a red CI run blocks merging, since it doesn't.
6. This is a solo-maintainer project. Self-review against the checklist in
   `PR_REVIEW_PROCESS.md` is the norm; there is no second human reviewer in practice.

## Releases & versioning

- No release branches. Versions are tracked as **GitHub milestones** and mirrored in
  `ISSUE_PRIORITIES.md` under "Release Context" (`Current Release` / `Next Release` /
  `Future Releases`), regenerated after epics/issues close.
- Git tags (`v0.1.0`–`v0.10.0`) exist but were bulk-created retroactively on a single day
  (2026-05-06) to backfill early history — they are not a live per-release cut process.
  `v2.x.y-deprecated` tags mark the abandoned CLI-era version line; ignore them for current
  work.
- There's no separate "cut a release branch, stabilize, tag, merge back" step. A milestone
  closing == its issues/epics merged to `main`.

## Deploy is continuous off `main`

Push to `main` → `docker-publish.yml` builds and pushes a multi-arch image to GHCR →
the Raspberry Pi (`pi4`) pulls it, either manually (`podman-compose pull && up -d`) or via
a nightly systemd timer (01:30, pulls only if the image changed). There is no manual
promotion gate between "merged to main" and "deployed" beyond the nightly pull window.
When redeploying the Pi directly, always pull the GHCR image and tag it — never
`podman build` on the Pi itself.

## Issues & epics

- Work is filed as GitHub issues, grouped into epics for multi-issue efforts (e.g. Epic
  #413 Blueprint refactor, Epic #352 Design Review, Epic #412 Explore enhancements).
  Commit and PR titles reference issue/epic numbers inline (`Fix #345: ...`,
  `feat(#413): ...`).
- `ISSUE_PRIORITIES.md` is the live priority queue, ordered P0–P4 *within* the current
  release milestone before any future-release issue is considered. It gets regenerated
  after closing an epic or its children — treat a stale-looking priorities file as a sign
  work needs to be reflected there, not as ground truth on its own.
- `docs/guides/DEFINITION_OF_DONE.md` sets the completion bar (real implementation, tests,
  review, docs, deploy, verification) — written in response to issues #138–140 being closed
  with stub implementations.

## Net takeaway

If asked to "follow gitflow" on this project: create a short-lived branch off `main` named
per the conventions above, open a PR with the template, let CI run, merge with a merge
commit (not squash) once satisfied, and let the existing push-to-main → GHCR → Pi pipeline
handle deployment. Don't invent a `develop` branch or a release-branch step, and don't
re-enable branch protection — neither reflects actual practice here.
