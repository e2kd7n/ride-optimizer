# Design Review — Consolidated Findings
**Version:** v0.17.0
**Date:** 2026-07-04
**Epic:** #352
**Reviewers:** Information Density (#353), Discoverability (#354), Card Placement (#355)
**Status:** Findings complete — implementation issues created

---

## Executive Summary

The v0.17.0 design review covered all 7 in-scope pages across three evaluation dimensions (information density, discoverability, and card/object placement). Overall, the app has a sound structural foundation — Bootstrap 5 grid, working navigation, skeleton loaders — but suffers from three systemic problems that span every page: (1) card ordering consistently places lower-urgency context before higher-urgency action content, (2) progressive disclosure is unevenly applied so secondary and tertiary data compete with primary decision metrics, and (3) two pages (Explore and Route Detail) have P1 findings that prevent new users from completing the primary task. In total, 50+ raw findings were produced across the three reviewers; after deduplication and merging of closely related items, **20 unique actionable GitHub issues** were created against the v0.17.0 milestone. Design Principles §2, §3, and §7 were updated with field notes from these findings.

---

## Finding Themes

### Theme A — Navigation Gaps (mobile reach)
The bottom navigation bar (4 items: Home / Routes / Weather / Settings) excludes **Reports** and **Explore** on most pages, creating a two-tier mobile UX where two of the six main sections require a hamburger-menu detour. Affects 5+ pages.

Findings: DISC-REPORTS-3, DISC-EXPLORE-4, CP-1 (DISC), CP-3 (PLACE-cross)

---

### Theme B — Placement Inversions (action-before-context rule violated)
On three pages, lower-urgency context cards are placed *above* higher-urgency action/decision cards, both in desktop layout and mobile stacking order. The most critical instance is the Weather page where a 7-day forecast precedes same-day commute windows.

Findings: PLACE-WEATHER-1, PLACE-DASH-1, PLACE-DASH-2, PLACE-DASH-3, PLACE-REPORTS-1, PLACE-REPORTS-2, PLACE-EXPLORE-1, PLACE-EXPLORE-2, ID-DASH-1, ID-DASH-2, ID-WX-1

---

### Theme C — Hidden Features / No Onboarding (discoverability failures)
Multiple interactive features are invisible to first-time users: the route-compare checkbox has no label on mobile; the Explore page uses cycling-subculture jargon without definitions; the multi-step Explore workflow has no sequencing guidance; the commute collapse has no affordance. Two Explore findings were rated P1 because the primary task is not completable without guessing.

Findings: DISC-EXPLORE-1, DISC-EXPLORE-2, DISC-ROUTES-1, DISC-ROUTES-2, DISC-DETAIL-1 (DISC), DISC-DETAIL-2, DISC-SETTINGS-1, DISC-DASH-1, DISC-DASH-2

---

### Theme D — Information Overload / Misweighted Metrics
Secondary and administrative data is displayed at the same visual weight as primary decision metrics across four pages. Specific problems: raw JSON weather dump in Route Detail (P1), admin sync buttons inside the Reports Gear card, 9 unconditionally visible filter controls on Routes Library, empty secondary stats displayed as headline numbers on Reports, monolithic Connections card in Settings.

Findings: ID-RDTL-1, ID-RDTL-2, ID-RPT-1, ID-RPT-2, ID-RPT-3, ID-ROUTES-1, ID-SET-1, ID-SET-2, ID-EXP-1, ID-EXP-2, DISC-REPORTS-1, DISC-REPORTS-2, CP-4 (ID)

---

### Theme E — Unit System & Version Consistency
Unit system preferences are not consistently applied across all pages: Reports hardcodes "Miles", the temperature slider always shows °F regardless of metric setting, the Explore distance slider defaults to km for all users before JS executes. All seven page footers and the "What's New" toast key reference the stale version `v0.14.0` while the product ships as `v0.17.0`.

Findings: DISC-SETTINGS-3, DISC-REPORTS-4, DISC-EXPLORE-3, DISC-DASH-3, CP-2 (DISC), CP-1 (ID), ID-SET-3, ID-WX-2, ID-WX-3

---

## Full Finding Inventory

| Finding ID | Page | Severity | Title | GitHub Issue # |
|---|---|---|---|---|
| PLACE-WEATHER-1 / ID-WX-1 | Weather | P1 | 7-day forecast placed before same-day commute windows | #357 |
| PLACE-DASH-1 / ID-DASH-2 | Dashboard | P1 | Route Status renders before commute recommendation on mobile; map column ratio inverted | #358 |
| ID-RDTL-1 / DISC-DETAIL-1 | Route Detail | P1 | Weather data rendered as raw JSON `<pre>` in primary metrics card | #359 |
| DISC-EXPLORE-1 | Explore | P1 | No explanation of tile/Squadrats concept — primary task uncompletable | #360 |
| DISC-EXPLORE-2 / ID-EXP-3 | Explore | P1 | Multi-step route generation has no workflow sequencing or button dependency logic | #361 |
| DISC-REPORTS-3 / DISC-EXPLORE-4 / CP-1 | All pages | P2 | Reports and Explore absent from mobile bottom navigation bar | #362 |
| PLACE-DASH-3 | Dashboard | P2 | "How It Works" button above weather and commute content | #363 |
| ID-ROUTES-1 / PLACE-ROUTES-1 | Routes Library | P2 | Advanced filter controls unconditionally visible; no collapse on mobile | #364 |
| PLACE-ROUTES-2 | Routes Library | P2 | Route list column narrower than map column — ratio inverted | #365 |
| PLACE-REPORTS-1 / PLACE-REPORTS-2 / ID-RPT-3 | Reports | P2 | Reports right-column ordering: Gear above Activities; chart cards need consolidation | #366 |
| PLACE-EXPLORE-1 / PLACE-EXPLORE-2 / ID-EXP-2 | Explore | P2 | Coverage stats above map; route generation controls below map; controls/generation cards should merge | #367 |
| ID-SET-1 / ID-SET-2 / PLACE-SETTINGS-1 / PLACE-SETTINGS-2 / DISC-SETTINGS-1 | Settings | P2 | Monolithic Connections card; Outdoor Prefs separated from TrainerRoad; Save button below About | #368 |
| ID-RPT-1 / ID-RPT-2 / DISC-REPORTS-2 | Reports | P2 | Empty secondary stats at primary weight; admin sync buttons in Gear card; developer label "Backfill Gear IDs" | #369 |
| DISC-DASH-1 / DISC-DASH-2 / ID-DASH-3 | Dashboard | P2 | Hidden commute detail collapse and route status collapse have no affordance labels or count badges | #370 |
| ID-RDTL-2 / ID-RDTL-3 / PLACE-DETAIL-1 / PLACE-DETAIL-2 | Route Detail | P2 | "Uses" in primary grid; performance charts hidden and buried below history tables; mobile map fills viewport | #371 |
| DISC-ROUTES-1 / DISC-ROUTES-2 | Routes Library | P2 | Compare checkbox invisible on touch; Saved Plans section has no entry-point badge | #372 |
| DISC-WEATHER-1 / DISC-WEATHER-2 / ID-WX-2 | Weather | P2 | Comfort score has no legend; commute window time labels hardcoded and mismatched to API | #373 |
| CP-3 (DISC) | 5 pages | P2 | Help modal tutorial GIF assets are missing/unshipped | #374 |
| DISC-SETTINGS-3 / DISC-REPORTS-4 / DISC-EXPLORE-3 | Settings/Reports/Explore | P2 | Unit system setting not applied to temperature slider, Reports distance label, and Explore distance slider | #375 |
| DISC-DASH-3 / DISC-DASH-4 / CP-2 (DISC) / CP-1 (ID) / ID-SET-3 / ID-WX-3 / ID-RPT-4 / PLACE-SETTINGS-3 / PLACE-WEATHER-2 / DISC-DETAIL-3 / DISC-DETAIL-4 / DISC-EXPLORE-5 / DISC-SETTINGS-2 / DISC-SETTINGS-4 / DISC-ROUTES-3 / DISC-REPORTS-1 / ID-ROUTES-2 / ID-ROUTES-3 / ID-SET-4 | All/Various | P3 | P3 polish bundle: stale versions, missing H1s, a11y minor issues, UX polish | #376 |

---

## Findings Not Actionable / Deferred

| Finding ID | Reason |
|---|---|
| PLACE-ROUTES-3 | Subagent C explicitly confirmed no issue — Saved Plans placement is correct |
| DISC-WEATHER-3 | Subagent B self-resolved as non-finding |
| ID-CP-2 (`show_secondary_metrics` has no UI effect) | Deferred: requires API contract change and new toggle logic across 4 pages — scope for v0.18.0 |
| ID-CP-3 (Missing H1 on 3 pages) | Folded into P3 bundle issue #375 rather than standalone |

---

## Design Principles Updated

The following additions and modifications were made to [`plans/v0.6.0/DESIGN_PRINCIPLES.md`](../v0.6.0/DESIGN_PRINCIPLES.md):

| Principle | Change |
|---|---|
| §2 Progressive Disclosure | Extended with new guideline: "Time-urgency ordering" — most time-sensitive content must precede planning/context content in DOM source order. Added field note citing PLACE-WEATHER-1, PLACE-DASH-1, ID-WX-1. |
| §3 Visual Hierarchy | Extended with new guideline: "Card column ratios" — data/decision columns must be ≥ map/context columns (min col-lg-6). Added field note citing PLACE-DASH-2, PLACE-ROUTES-2, PLACE-DETAIL-2. |
| §7 Discoverable Features | Extended with new guideline: "Workflow sequencing" — multi-step workflows must have visible step numbers or progressive button enablement. Added field note citing DISC-EXPLORE-2, DISC-SETTINGS-1. Also extended with: "Jargon-free first use" — domain-specific terms require in-page definitions. Citing DISC-EXPLORE-1. |
| §10 Consistent Patterns | Extended with new guideline: "Destructive action styling" — destructive actions must use `btn-outline-danger` or `btn-danger` with a confirmation step. Added field note citing DISC-EXPLORE-5. Extended with: "Unit system applied globally" — all labels, sliders, and static strings displaying measurements must read the user unit preference on page load. Citing DISC-SETTINGS-3, DISC-REPORTS-4, DISC-EXPLORE-3. |

> **Addendum (2026-07-05, post-epic):** `DESIGN_PRINCIPLES.md` was bumped again to **v2.2** outside this review, adopting the "Fair Weather" brand identity (full spec: [`docs/designs/FAIR_WEATHER_BRAND_BOOK.md`](../../docs/designs/FAIR_WEATHER_BRAND_BOOK.md)). This replaced the Primary/Semantic Colors tables in §4, and added two new guidelines directly relevant to this epic's open issues: §2 now requires weather cards to show wind and precipitation whenever available, and §3 now formalizes "map + controls beside each other on desktop," which generalizes the column-ratio recommendations already made in #365 and #367 below.

---

## Implementation Issues Created

| Issue # | Title | Priority |
|---|---|---|
| #357 | [Design Review] Weather: swap 7-day forecast and same-day commute windows order | P1 |
| #358 | [Design Review] Dashboard: fix mobile column stacking and widen decision panel | P1 |
| #359 | [Design Review] Route Detail: replace raw JSON weather `<pre>` dump with formatted card | P1 |
| #360 | [Design Review] Explore: add tile/Squadrats concept explainer and coverage legend | P1 |
| #361 | [Design Review] Explore: add numbered workflow steps and progressive button enablement | P1 |
| #362 | [Design Review] Navigation: add Reports and Explore to mobile bottom nav | P2 |
| #363 | [Design Review] Dashboard: relocate "How It Works" button out of above-the-fold content | P2 |
| #364 | [Design Review] Routes Library: collapse advanced filters behind "More Filters" toggle | P2 |
| #365 | [Design Review] Routes Library: invert column ratio to give route list more space than map | P2 |
| #366 | [Design Review] Reports: reorder cards — Activities before Gear; consolidate chart cards | P2 |
| #367 | [Design Review] Explore: move coverage stats below map; merge controls into route generation card | P2 |
| #368 | [Design Review] Settings: split Connections card; nest Outdoor Prefs in TrainerRoad; move Save above About | P2 |
| #369 | [Design Review] Reports: hide empty secondary stats; move admin gear buttons to Settings | P2 |
| #370 | [Design Review] Dashboard: add affordance labels/count badges to collapse toggles | P2 |
| #371 | [Design Review] Route Detail: demote Uses metric; surface performance charts above history tables | P2 |
| #372 | [Design Review] Routes Library: label compare checkbox; add entry-point for Saved Plans | P2 |
| #373 | [Design Review] Weather: add comfort score legend; fix hardcoded commute window time labels | P2 |
| #374 | [Design Review] Ship or gracefully degrade help modal tutorial assets | P2 |
| #375 | [Design Review] Apply unit system preference to temperature slider, Reports distance label, and Explore distance slider | P2 |
| #376 | [Design Review] P3 polish bundle: stale versions, missing H1s, a11y minor, UX polish items | P3 |
