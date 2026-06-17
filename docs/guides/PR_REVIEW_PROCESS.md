# Pull Request Review Process

**Version:** 1.0
**Date:** 2026-06-17
**Status:** MANDATORY for all contributors
**Authority:** Project-wide standard

---

## Overview

All code changes to `main` must go through a pull request with at least one approval. Direct pushes to `main` are not permitted once branch protection is enabled.

---

## Required Reviewers

| Change Type | Required Reviewer |
|---|---|
| Backend (`app/`, `src/`, `launch.py`) | Backend-familiar contributor |
| Frontend (`static/`) | Frontend-familiar contributor |
| CI/CD (`.github/workflows/`) | Project maintainer |
| Documentation (`docs/`) | Any contributor |
| Config (`config/`, `requirements*.txt`) | Project maintainer |

For a solo-maintainer project, self-review with the checklist below is acceptable, but a second pair of eyes is always preferred.

---

## Review Checklist

Reviewers should verify each of these before approving:

### Correctness
- [ ] Code does what the PR description claims
- [ ] Acceptance criteria from the linked issue are met
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
- [ ] Test coverage meets the 80% minimum for new code
- [ ] All CI checks pass

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

## Branch Protection Rules

The following rules should be enabled on the `main` branch via GitHub Settings > Branches > Branch protection rules:

| Rule | Setting |
|---|---|
| Require pull request before merging | **Enabled** |
| Required approvals | **1** |
| Dismiss stale reviews on new pushes | **Enabled** |
| Require status checks to pass | **Enabled** |
| Required status checks | `test` (from CI workflow) |
| Require branches to be up to date | **Enabled** |
| Require conversation resolution | **Enabled** |
| Include administrators | **Enabled** |

### How to Enable

1. Go to **Settings > Branches** in the GitHub repository
2. Click **Add branch protection rule**
3. Set **Branch name pattern** to `main`
4. Enable the rules listed above
5. Click **Create** / **Save changes**

---

## PR Workflow

### Author Responsibilities

1. Create a feature branch from `main` (e.g., `feat/123-description`)
2. Make changes and push to the remote branch
3. Open a PR using the PR template — fill in all sections
4. Link the issue with `Fixes #123` in the PR description
5. Ensure CI passes before requesting review
6. Address all review comments before merging
7. Squash-merge or rebase-merge (no merge commits)

### Reviewer Responsibilities

1. Respond to review requests within 1 business day
2. Use the review checklist above
3. Leave actionable, specific comments — suggest code when possible
4. Approve only when all checklist items are satisfied
5. Re-review promptly after the author addresses feedback

### Merge Policy

- **Squash merge** is preferred for single-purpose PRs (keeps `main` history clean)
- **Rebase merge** is acceptable for multi-commit PRs where individual commits are meaningful
- Delete the source branch after merging

---

## Related Documents

- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) — when work is considered complete
- [TEST_COVERAGE_GUIDE.md](TEST_COVERAGE_GUIDE.md) — testing standards

---

**Last Updated:** 2026-06-17
**Owner:** Project Maintainer
