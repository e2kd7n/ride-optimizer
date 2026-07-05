# Epic: Design Review — Information Architecture & Workflow Optimization

**Version:** v0.17.0
**Created:** 2026-07-04
**Updated:** 2026-07-06 (final staff engineering review: re-scoped #362, resolved #374, shipped version-string fix, replaced implementation plan with PR/subagent execution plan)
**Status:** Planned for implementation
**Epic Issue:** [#352](https://github.com/e2kd7n/ride-optimizer/issues/352)
**Consolidated Findings:** [DESIGN_REVIEW_FINDINGS.md](./DESIGN_REVIEW_FINDINGS.md)

---

## Overview

Three parallel design reviewers audited all 7 in-scope pages of the Ride Optimizer web app
against a live instance (2,059 activities, 221 route groups) across three dimensions:
Information Density, Discoverability & Ease of Use, and Card & Object Placement.

50+ raw findings were produced, deduplicated, and consolidated into **20 actionable GitHub
issues** across **5 themes**. Design Principles v2.0 was updated to v2.1 with field-tested
rules derived from the findings.

Nothing in the current design is considered sacred **except alignment to the Bootstrap 5 grid.**

---

## Scope

### Pages Reviewed

| Page | File | Primary Purpose |
|------|------|-----------------|
| Dashboard | `static/index.html` | Weather + commute recommendation |
| Routes Library | `static/routes.html` | Browse & compare saved routes |
| Route Detail | `static/route-detail.html` | Single-route deep-dive |
| Reports | `static/reports.html` | Historical ride analytics |
| Explore | `static/explore.html` | Discover new rides |
| Weather | `static/weather.html` | Full weather breakdown |
| Settings | `static/settings.html` | App configuration |

### Constraint (Sacred)
- **Grid alignment** — All elements must remain on the Bootstrap 5 grid
  (12-column, breakpoints: mobile <768px, tablet 768–1024px, desktop >1024px).

---

## Finding Themes

| Theme | Description | Severity | Issues |
|-------|-------------|----------|--------|
| **A — Navigation Gaps** | Reports and Explore absent from mobile bottom nav on all pages | P1 | #362 |
| **B — Placement Inversions** | Context cards placed above action/decision cards; map columns wider than content columns | P1–P2 | #357 #358 #363 #365 #366 #367 #371 |
| **C — Hidden Features / No Onboarding** | Interactive features undiscoverable; Explore page uses jargon without definitions | P1–P2 | #360 #361 #370 #372 #374 |
| **D — Information Overload** | Admin controls mixed into analytics; raw JSON rendered; secondary data at primary weight | P1–P2 | #359 #364 #368 #369 |
| **E — Unit & Version Consistency** | Unit preferences not applied globally; stale `v0.14.0` version strings throughout | P2–P3 | #373 #375 #376 |

---

## Prioritized Child Issues

### 🔴 P1 — Must ship in v0.17.0 (blocks usability or validation)

These are ordered by **release gating first, then task criticality**. After review, #362 is elevated
from P2 to P1 because mobile navigation reach is a release-level usability concern, not just a test
sequencing concern: two primary sections remain effectively second-class on mobile until it is fixed.

| # | Issue | Page | Why first / why P1-for-sequencing | Unblocks |
|---|-------|------|-----------------------------------|----------|
| 1 | [#362](https://github.com/e2kd7n/ride-optimizer/issues/362) | All pages | Reports and Explore are unreachable from the primary mobile nav; execute first so mobile validation is possible across the full app. **Re-scoped 2026-07-06: ship as a 6-item icon-only bar, not "add 2 items to the existing 4."** | Mobile testing of every other fix |
| 2 | [#358](https://github.com/e2kd7n/ride-optimizer/issues/358) | Dashboard | Mobile stacking puts Route Status above the commute decision and inverts desktop emphasis on the highest-frequency page | #363, #370 |
| 3 | [#357](https://github.com/e2kd7n/ride-optimizer/issues/357) | Weather | 7-day forecast above same-day commute windows inverts time urgency on a core commute workflow page | Recommended before #373 |
| 4 | [#359](https://github.com/e2kd7n/ride-optimizer/issues/359) | Route Detail | Raw `JSON.stringify` rendered in the primary metrics card breaks comprehension of current weather context | #371 |
| 5 | [#360](https://github.com/e2kd7n/ride-optimizer/issues/360) | Explore | No explanation of tiles / Squadrats makes the primary Explore task uncompletable for new users | #361, #367 |
| 6 | [#361](https://github.com/e2kd7n/ride-optimizer/issues/361) | Explore | Multi-step Generate workflow has no visible sequencing; Load Coverage must precede Generate | #367 |

### 🟠 P2 — Should ship in v0.17.0 (significant friction)

Ordered by **hard dependencies first, then page-criticality and breadth**.

| # | Issue | Page(s) | Theme | Depends on |
|---|-------|---------|-------|------------|
| 7 | [#368](https://github.com/e2kd7n/ride-optimizer/issues/368) | Settings | D | — |
| 8 | [#369](https://github.com/e2kd7n/ride-optimizer/issues/369) | Reports | D | #368 (gear admin buttons move to Settings) |
| 9 | [#366](https://github.com/e2kd7n/ride-optimizer/issues/366) | Reports | B | #369 (admin / empty-state cleanup should land before card reorder) |
| 10 | [#363](https://github.com/e2kd7n/ride-optimizer/issues/363) | Dashboard | B | #358 (dashboard layout should stabilize before relocating explainer content) |
| 11 | [#370](https://github.com/e2kd7n/ride-optimizer/issues/370) | Dashboard | C | #358 (collapse affordances should be added after the destination structure is stable) |
| 12 | [#364](https://github.com/e2kd7n/ride-optimizer/issues/364) | Routes Library | D | — |
| 13 | [#365](https://github.com/e2kd7n/ride-optimizer/issues/365) | Routes Library | B | #364 (filter collapse changes above-the-fold space and should land first) |
| 14 | [#372](https://github.com/e2kd7n/ride-optimizer/issues/372) | Routes Library | C | #364, #365 (entry points and labels should target the stabilized layout) |
| 15 | [#367](https://github.com/e2kd7n/ride-optimizer/issues/367) | Explore | B | #360, #361 (concept explainer and workflow guidance should land before control consolidation) |
| 16 | [#371](https://github.com/e2kd7n/ride-optimizer/issues/371) | Route Detail | B | #359 (formatted weather context should replace the JSON dump first) |
| 17 | [#373](https://github.com/e2kd7n/ride-optimizer/issues/373) | Weather | E | Recommended after #357 (visual order first), but can proceed independently if needed |
| 18 | [#375](https://github.com/e2kd7n/ride-optimizer/issues/375) | Settings/Reports/Explore | E | Can run in parallel with #368; only coordinate on the Settings temperature control markup |
| 19 | [#374](https://github.com/e2kd7n/ride-optimizer/issues/374) | All pages | C | **Resolved 2026-07-06** — graceful-degradation `onerror` fallback shipped directly; no longer waiting on tutorial asset creation |

### 🟡 P3 — Can defer if needed (polish)

| # | Issue | Page(s) | Theme | Notes |
|---|-------|---------|-------|-------|
| 20 | [#376](https://github.com/e2kd7n/ride-optimizer/issues/376) | All pages | E | Bundle: missing H1s, a11y minor, touch target tweaks. Stale `v0.14.0` version strings **fixed directly 2026-07-06**, pulled out of this bundle. |

---

## Dependency Graph

```
Mobile nav fix (#362) ──────────────────────────────────────────► enables mobile testing of ALL fixes

Dashboard layout (#358) ──► relocate How It Works (#363)
                        └──► collapse affordances (#370)

Settings restructure (#368) ──► move gear admin (#369) ──► reorder Reports cards (#366)

Explore: concept explainer (#360) ──► workflow steps (#361) ──► merge controls/stats (#367)

Routes: filter collapse (#364) ──► column ratio (#365) ──► compare label + plans entry (#372)

Route Detail: fix JSON dump (#359) ──► demote Uses / surface charts (#371)

Weather: swap card order (#357) ──► recommended sequencing for comfort legend + time labels (#373)

Unit system (#375) ──► can run in parallel with #368, coordinate only where the Settings temp control changes

Help assets (#374) ──► either ship tutorial media or implement graceful degradation per page
```

---

## Staff Engineering Review — Final Call (2026-07-06)

The 2026-07-05 "Staff Engineering Implementation Plan" below this heading has been **superseded**. It
restated the existing dependency graph as four sequential "sub-tasks" without changing any technical
decision — for a single-developer app this adds process overhead (fake per-paragraph status checkboxes,
a strict waterfall) without adding judgment. I re-verified the underlying findings directly against the
live code (not just the reviewer docs) before making this call. They check out: the `JSON.stringify`
dump, the stale `v0.14.0` strings in all 8 templates, the missing bottom-nav entries, and the missing
`onerror` fallback on tutorial images are all real, not hallucinated. The raw findings docs
(`findings-*.md`) remain the source of truth for *what's* wrong. This section replaces the *how and in
what order* it gets fixed.

### Decisions made this pass

1. **#362 (mobile nav) is re-scoped.** "Add Reports and Explore to the existing 4-item bar" was never
   going to work — that's 6 items in a bottom nav, which is unreadable with text labels below ~360px
   viewports. Decision: **6 items, icon-only** (drop text labels, keep all six primary sections —
   Home, Routes, Reports, Explore, Weather, Settings — reachable in one tap). The implementer should
   verify legibility/tap-target size (≥44px) at a 360px viewport before calling this done; if it's
   still too cramped, fall back to dropping Settings from the bar (it's already reachable from the top
   navbar on every page) rather than shipping a nav that doesn't work on small phones.
2. **Version string and "What's New" toast — fixed directly in this session**, not left for the
   implementation phase. This was mechanical (global string replace across 8 templates) with one
   content judgment call: the toast's bullet list was still advertising `v0.14.0`-era features
   ("Hourly forecast", "Saved plans") under a bumped title, which would have made the mismatch worse,
   not better. Replaced the bullets with features that actually shipped since then, per `git log`
   (tile-coverage exploration, road-following routes with GPX export, location search, Garmin/
   TrainerRoad integration). No epic tracking needed for this — it's done.
3. **#374 (help modal tutorial assets) — resolved as "graceful degradation," fixed directly in this
   session.** `static/img/tutorials/` doesn't exist at all, so every "Help" click was showing 4 broken
   images with no fallback. Added an `onerror` handler that swaps to a "Preview coming soon" placeholder
   and hides the now-meaningless "Hover to play" badge. This unblocks the epic without waiting on
   someone to record four tutorial GIFs — if/when those assets show up, they'll just work; if they
   never do, the modal still reads cleanly. No further tracking needed for this issue.
4. **Real dependencies vs. review-order preferences.** The original dependency graph treated "should be
   reviewed in this order for a cleaner diff" the same as "will break if done out of order." Only the
   latter are real blockers: things that touch the *same file*. #368/#369/#366 (Settings + Reports admin
   controls) and #360/#361/#367 (Explore) and #364/#365/#372 (Routes Library) share files and should
   each land as **one PR per page**, not three sequenced issues per page. Cross-page items that touch
   *every* template (nav, and now-resolved version/help-asset fixes) must land before or alongside
   everything else, since every other change will otherwise conflict with them on the same lines.
   Everything else — Dashboard vs. Weather vs. Route Detail vs. Routes Library vs. Explore — touches
   disjoint files and has **no real ordering constraint**. Treating it as a waterfall (Sub-Task 2 → 3 → 4)
   was leaving parallelism on the table for no benefit.

### Execution plan — by PR, not by issue

Twenty GitHub issues is the right granularity for *tracking findings*; it's the wrong granularity for
*implementation* on a single small codebase, where issue-per-finding would mean 20 PRs almost all
touching the same handful of files. Collapse to page-scoped PRs:

| PR | Issues | Files | Can start | Notes |
|----|--------|-------|-----------|-------|
| **A — Nav rework** | #362 | all 8 `static/*.html` (bottom nav block) | Now | Must merge before B–G branch, since it touches shared markup in every file. Do this first, alone. |
| **B — Dashboard** | #358, #363, #370 | `static/index.html` | After A merges | Independent of C–G. |
| **C — Weather** | #357, #373 | `static/weather.html` | After A merges | Independent of B, D–G. |
| **D — Route Detail** | #359, #371 | `static/route-detail.html` | After A merges | Independent of B, C, E–G. |
| **E — Explore** | #360, #361, #367 | `static/explore.html`, `static/js/explore.js` | After A merges | Real intra-PR order: #360 (explainer) → #361 (workflow steps) → #367 (merge controls), same file, same PR. |
| **F — Routes Library** | #364, #365, #372 | `static/routes.html`, `static/js/routes.js` | After A merges | Real intra-PR order: #364 → #365 → #372, same file, same PR. |
| **G — Settings + Reports admin** | #368, #369, #366 | `static/settings.html`, `static/reports.html` | After A merges | Real cross-file dependency: #368 (Settings restructure) before #369 (buttons move *into* Settings) before #366 (Reports reorder). One PR, sequenced commits. |
| **H — Unit system pass** | #375 | `static/settings.html`, `static/reports.html`, `static/explore.html` | After G merges | Touches the same Settings/Reports markup G just changed — sequencing here is real, not preference. |
| **I — P3 cleanup** | #376 (minus version strings, already fixed) | various | Anytime, low risk | Missing H1s, a11y, touch targets. |

### Subagent assignment

This shape — one cross-cutting PR followed by five to six page-disjoint PRs — is close to the ideal
case for parallel subagents in isolated git worktrees:

1. **PR A runs solo, first**, one agent, no parallelism (it's the one thing every other PR would conflict
   with).
2. **Once A merges, spawn agents B, C, D, E, F in parallel**, each in its own worktree, each scoped to
   exactly the files/issues in its row above. Give each agent the relevant `findings-*.md` excerpts
   (not the whole 350-line doc) plus the specific issue numbers — they don't need the other pages'
   context.
3. **G runs as its own agent**, sequentially internally (368→369→366) since it's a real dependency chain
   within one PR.
4. **H runs after G merges** (same agent or a fresh one — either is fine since G's outcome is now just
   "current code," not context the agent needs to have generated itself).
5. **I can run whenever**, lowest priority, single agent, no coordination needed.

This turns a 20-issue waterfall into ~7 PRs, of which 5 run in true parallel — a meaningfully faster and
less error-prone path than the previous sub-task sequencing, without touching any of the underlying
design verdicts from the three reviewers.

## Output Artifacts

- [x] **Consolidated findings** → [`plans/v0.17.0/DESIGN_REVIEW_FINDINGS.md`](./DESIGN_REVIEW_FINDINGS.md)
- [x] **Reviewer findings** → `plans/v0.17.0/findings-information-density.md`, `findings-discoverability.md`, `findings-card-placement.md`
- [x] **Design guidelines updated** → [`plans/v0.6.0/DESIGN_PRINCIPLES.md`](../v0.6.0/DESIGN_PRINCIPLES.md) bumped to v2.1
- [x] **20 implementation issues created** → #357–#376 (all in v0.17.0 milestone)
- [x] **#374 resolved directly** (help modal now degrades gracefully via `onerror` fallback — no longer blocked on tutorial asset creation)
- [x] **Stale `v0.14.0` version strings and "What's New" toast fixed directly** across all 8 templates (part of #376, pulled forward — see `static/index.html`, footers app-wide)
- [ ] Remaining 18 child implementation issues resolved via PR plan (A–I) above and closed
- [ ] Epic #352 closed with summary comment

---

## Definition of Done

- [x] All pages evaluated against all three criteria
- [x] Findings consolidated into a single document
- [x] Design guidelines updated to reflect new decisions
- [x] All actionable findings have a corresponding GitHub issue in v0.17.0
- [ ] All child issues resolved and closed (#357–#376)
- [ ] This epic closed with a summary comment linking the findings document

---

## Evaluation Methodology

The review was conducted against the **live running app** at `http://localhost:8083`, not static
HTML alone. All API endpoints were queried to validate what data actually renders:

- `/api/recommendation` — live composite score and departure time
- `/api/weather` + `/api/weather/forecast` + `/api/weather/commute-windows` — real weather conditions
- `/api/routes?limit=10` + `/api/routes/{id}` — real route geometry and history
- `/api/stats` + `/api/stats/gear` — 2,059 activities, monthly distance, gear breakdown

This means findings are grounded in what real users see with real data, not skeleton states.
