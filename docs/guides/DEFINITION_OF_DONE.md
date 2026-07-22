# Definition of "Done" - Ride Optimizer Project

**Version:** 2.0
**Date:** 2026-07-22
**Status:** Guidance for a solo-maintainer project
**Authority:** Project-wide standard

---

## Purpose

This document establishes a clear definition of "done" for work items in the Ride Optimizer
project. It was originally created in response to issues #138, #139, and #140 being closed
prematurely with only stub implementations — that principle still holds.

**Key Principle:** Stubs ≠ Done. Placeholder code ≠ Done. Only fully implemented and tested
features are "done."

This is a solo-maintainer project. There is no squad structure, no second reviewer, and no PR
requirement — see `docs/guides/PR_REVIEW_PROCESS.md`. References below to "PR merged" or
"review approval" mean self-review, not sign-off from another person.

---

## Definition of "Done" Checklist

A work item (issue, feature, bug fix) is considered **DONE** when:

### 1. Implementation Complete
- [ ] Actual code implemented (not stubs, not placeholders, not TODOs)
- [ ] Code follows project coding standards and style guide
- [ ] All acceptance criteria from the issue are met
- [ ] Edge cases and error handling implemented
- [ ] No debug code, console.logs, or temporary hacks remain

### 2. Testing Complete
- [ ] Unit tests written for new code where it makes sense
- [ ] All tests pass locally / in CI
- [ ] No existing tests broken by changes
- [ ] Manual testing performed for UI changes

### 3. Committed
- [ ] Change is committed and pushed to `main` (directly, or via a PR if one was opened)
- [ ] Self-review against the checklist in `PR_REVIEW_PROCESS.md` done for anything nontrivial

### 4. Documentation Complete
- [ ] Code comments added for complex logic (the *why*, not the *what*)
- [ ] User-facing documentation updated, if behavior changed
- [ ] CLAUDE.md/AGENTS.md updated, if architecture or conventions changed

### 5. Deployed
- [ ] Change is on `main` (continuous deploy off `main` handles the rest — see
      `WORKFLOW_GUIDELINES.md`)
- [ ] Deployment notes added for anything requiring manual steps on the Pi

---

## What is NOT "Done"

❌ **Stub implementations** — placeholder code that returns mock data
❌ **TODO comments** — code with "TODO: implement this later"
❌ **Partial implementations** — only some acceptance criteria met
❌ **Untested code** — no tests for nontrivial new logic
❌ **Local-only changes** — code not pushed to the repository

---

## Reopening an Issue

Issues should be reopened if:
- A stub implementation is discovered (like #138, #139, #140)
- Tests are failing
- Acceptance criteria are not met
- The change was reverted
- Critical bugs are found in the implementation

---

## Related Documents

- [PR_REVIEW_PROCESS.md](PR_REVIEW_PROCESS.md) - when to open a PR, self-review checklist
- [WORKFLOW_GUIDELINES.md](WORKFLOW_GUIDELINES.md) - actual branching/merge/deploy practice

---

**Last Updated:** 2026-07-22
**Owner:** Project Maintainer
