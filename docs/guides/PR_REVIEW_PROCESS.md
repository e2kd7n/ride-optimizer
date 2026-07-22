# Pull Request Review Process

**Version:** 2.0
**Date:** 2026-07-22
**Status:** Guidance for a solo-maintainer project
**Authority:** Project-wide standard

---

## Overview

This is a solo-maintainer project. There is no second human reviewer, and PRs are not
required before merging to `main` — direct commits/pushes to `main` are fine for routine
work. Branch protection on `main` is intentionally **off** (see
`docs/guides/WORKFLOW_GUIDELINES.md`) — don't re-enable it without asking.

Opening a PR is still useful sometimes: a risky change you want a paper trail on, something
you want CI to run against before merging, or work spanning multiple sessions/worktrees where
a PR makes the diff easier to review later. Use it when it helps, skip it when it doesn't.

Every Claude Code session works in its own git worktree (per project convention) and so is
always on its own branch — that's for avoiding collisions between concurrent sessions, not a
signal that a PR is required. A worktree branch can be merged/pushed straight to `main`
without going through a PR.

---

## Self-Review Checklist

When you do want a self-review pass (PR or not), this checklist still applies:

### Correctness
- [ ] Code does what it claims
- [ ] Acceptance criteria from the linked issue (if any) are met
- [ ] Edge cases and error paths are handled
- [ ] No regressions in existing functionality

### Quality
- [ ] Code is readable and follows project conventions
- [ ] No unnecessary complexity or premature abstractions
- [ ] No leftover debug code, TODOs, or commented-out blocks
- [ ] Functions and variables are clearly named

### Testing
- [ ] New/changed code has corresponding tests
- [ ] Tests are meaningful (not just asserting `True`)
- [ ] All CI checks pass (if a PR was opened) or `pytest` passes locally (if not)

### Security
- [ ] No secrets, credentials, or PII in the diff
- [ ] User input is validated at system boundaries
- [ ] No new OWASP Top 10 vulnerabilities introduced
- [ ] PII sanitizer (`src/pii_sanitizer.py`) is used where needed

### Documentation
- [ ] Public API changes are documented
- [ ] Complex logic has a brief inline comment explaining *why*
- [ ] User-facing behavior changes are reflected in guides

---

## If You Do Open a PR

1. Create a branch from `main` (e.g., `feat/123-description`) — or use the worktree branch
   a session already created.
2. Push, then open a PR using `.github/pull_request_template.md`. Link the issue with
   `Fixes #123` if there is one.
3. CI (`test` job in `.github/workflows/docker-publish.yml`) runs automatically; it does not
   block merging (branch protection is off) but should still be checked.
4. **Merge with a merge commit**, not squash/rebase — this matches actual practice on `main`
   (see `WORKFLOW_GUIDELINES.md`).
5. Delete the source branch after merging.

There is no required-approval step and no second reviewer to wait on.

---

## Related Documents

- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) — when work is considered complete
- [WORKFLOW_GUIDELINES.md](WORKFLOW_GUIDELINES.md) — actual branching/merge practice on this repo

---

**Last Updated:** 2026-07-22
**Owner:** Project Maintainer
