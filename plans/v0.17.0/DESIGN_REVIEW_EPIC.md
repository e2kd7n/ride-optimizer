# Epic: Design Review — Information Architecture & Workflow Optimization

**Version:** v0.17.0
**Created:** 2026-07-04
**Updated:** 2026-07-04 (post-review)
**Status:** Implementation in progress
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
| **A — Navigation Gaps** | Reports and Explore absent from mobile bottom nav on all pages | P2 | #362 |
| **B — Placement Inversions** | Context cards placed above action/decision cards; map columns wider than content columns | P1–P2 | #357 #358 #363 #365 #366 #367 #371 |
| **C — Hidden Features / No Onboarding** | Interactive features undiscoverable; Explore page uses jargon without definitions | P1–P2 | #360 #361 #370 #372 #374 |
| **D — Information Overload** | Admin controls mixed into analytics; raw JSON rendered; secondary data at primary weight | P1–P2 | #359 #364 #368 #369 |
| **E — Unit & Version Consistency** | Unit preferences not applied globally; stale `v0.14.0` version strings throughout | P2–P3 | #373 #375 #376 |

---

## Prioritized Child Issues

### 🔴 P1 — Must ship in v0.17.0 (blocks usability)

These are ordered by **impact breadth × task criticality**. Fix in this sequence — #362 enables
reliable navigation to test all other fixes on mobile.

| # | Issue | Page | Why P1 | Unblocks |
|---|-------|------|--------|----------|
| 1 | [#362](https://github.com/e2kd7n/ride-optimizer/issues/362) | All pages | Reports and Explore unreachable on mobile — 2 of 6 sections inaccessible | Mobile testing of every other fix |
| 2 | [#358](https://github.com/e2kd7n/ride-optimizer/issues/358) | Dashboard | Mobile stacking puts Route Status above commute decision; map column wider than decision panel | #363, #370 |
| 3 | [#357](https://github.com/e2kd7n/ride-optimizer/issues/357) | Weather | 7-day forecast above same-day commute windows — urgency ordering inverted | #373 |
| 4 | [#359](https://github.com/e2kd7n/ride-optimizer/issues/359) | Route Detail | Raw `JSON.stringify` rendered in primary metrics card | #371 |
| 5 | [#360](https://github.com/e2kd7n/ride-optimizer/issues/360) | Explore | Zero explanation of Squadrats/tiles — primary task uncompletable for new users | #361, #367 |
| 6 | [#361](https://github.com/e2kd7n/ride-optimizer/issues/361) | Explore | Multi-step Generate workflow has no sequencing — Load Coverage must precede Generate | #367 |

### 🟠 P2 — Should ship in v0.17.0 (significant friction)

Ordered by **dependency chain first, then impact breadth**.

| # | Issue | Page(s) | Theme | Depends on |
|---|-------|---------|-------|------------|
| 7 | [#368](https://github.com/e2kd7n/ride-optimizer/issues/368) | Settings | D | — |
| 8 | [#369](https://github.com/e2kd7n/ride-optimizer/issues/369) | Reports | D | #368 (gear admin buttons move to Settings) |
| 9 | [#363](https://github.com/e2kd7n/ride-optimizer/issues/363) | Dashboard | B | #358 (column layout must be correct first) |
| 10 | [#370](https://github.com/e2kd7n/ride-optimizer/issues/370) | Dashboard | C | #358 (collapse structure must be stable first) |
| 11 | [#364](https://github.com/e2kd7n/ride-optimizer/issues/364) | Routes Library | D | — |
| 12 | [#365](https://github.com/e2kd7n/ride-optimizer/issues/365) | Routes Library | B | #364 (filter collapse affects above-fold space) |
| 13 | [#372](https://github.com/e2kd7n/ride-optimizer/issues/372) | Routes Library | C | #364, #365 (layout must be stable first) |
| 14 | [#366](https://github.com/e2kd7n/ride-optimizer/issues/366) | Reports | B | #369 (empty stats hidden before reordering) |
| 15 | [#367](https://github.com/e2kd7n/ride-optimizer/issues/367) | Explore | B | #360, #361 (concept explainer and workflow first) |
| 16 | [#371](https://github.com/e2kd7n/ride-optimizer/issues/371) | Route Detail | B | #359 (weather card must be replaced first) |
| 17 | [#373](https://github.com/e2kd7n/ride-optimizer/issues/373) | Weather | E | #357 (card order must be correct first) |
| 18 | [#374](https://github.com/e2kd7n/ride-optimizer/issues/374) | All pages | C | — |
| 19 | [#375](https://github.com/e2kd7n/ride-optimizer/issues/375) | Settings/Reports/Explore | E | #368 (Settings restructure first for temp slider) |

### 🟡 P3 — Can defer if needed (polish)

| # | Issue | Page(s) | Theme | Notes |
|---|-------|---------|-------|-------|
| 20 | [#376](https://github.com/e2kd7n/ride-optimizer/issues/376) | All pages | E | Bundle: stale `v0.14.0` version strings, missing H1s, a11y minor, touch target tweaks |

---

## Dependency Graph

```
Mobile nav fix (#362) ──────────────────────────────────────────► enables mobile testing of ALL fixes

Dashboard layout (#358) ──► relocate How It Works (#363)
                        └──► collapse affordances (#370)

Settings restructure (#368) ──► move gear admin (#369) ──► reorder Reports cards (#366)
                           └──► unit system (temp slider) (#375)

Explore: concept explainer (#360) ──► workflow steps (#361) ──► merge controls/stats (#367)

Routes: filter collapse (#364) ──► column ratio (#365) ──► compare label + plans entry (#372)

Route Detail: fix JSON dump (#359) ──► demote Uses / surface charts (#371)

Weather: swap card order (#357) ──► comfort legend + time labels (#373)

Reports: hide empty stats (#369) ──► reorder cards (#366)      [#369 also depends on #368]

Unit system (#375) ──► depends on #368 (temp slider lives in Settings)
```

---

## Output Artifacts

- [x] **Consolidated findings** → [`plans/v0.17.0/DESIGN_REVIEW_FINDINGS.md`](./DESIGN_REVIEW_FINDINGS.md)
- [x] **Reviewer findings** → `plans/v0.17.0/findings-information-density.md`, `findings-discoverability.md`, `findings-card-placement.md`
- [x] **Design guidelines updated** → [`plans/v0.6.0/DESIGN_PRINCIPLES.md`](../v0.6.0/DESIGN_PRINCIPLES.md) bumped to v2.1
- [x] **20 implementation issues created** → #357–#376 (all in v0.17.0 milestone)
- [ ] All child implementation issues resolved and closed
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
