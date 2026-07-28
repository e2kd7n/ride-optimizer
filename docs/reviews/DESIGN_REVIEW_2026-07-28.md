# Design Review — Docs-vs-Built Audit & Issue #519+ Design Instructions
**Date:** 2026-07-28
**Reviewer:** Design (incoming, first pass on this codebase)
**Scope:** `docs/designs/FAIR_WEATHER_BRAND_BOOK.md`, `plans/v0.6.0/DESIGN_PRINCIPLES.md` (v2.3), `docs/guides/GRID_CONTRACT.md` vs. `static/css/main.css` + `templates/*.html` + `static/js/*.js`; open issues #519, #526, #532, #540
**Status:** Findings complete — all remediation work covered by open issues (#546, #547) and comments on #519, #526, #540

---

## Executive Summary

The design system itself is in good shape — Fair Weather's Day/Night token set is fully implemented in `main.css` (contrary to what the Brand Book's own "Rollout" section still claims), and several violations logged in the v0.17.0 review (`plans/v0.17.0/DESIGN_REVIEW_FINDINGS.md`) have since been quietly fixed in code without the source docs being updated to say so. The problem is **document staleness in both directions**: some docs describe bugs that are already fixed, others still show a pre-rebrand pattern library (8px/10px cards, `#667eea` buttons) that the CSS moved past months ago. Left alone, this actively misleads whoever (human or agent) trusts the docs over the code next.

Underneath that, there's one real, unfixed visual-system gap: the app's most decision-critical widgets — the dashboard hero card border and the per-route status icons, i.e. the exact "Today" screen the Brand Book uses as its flagship mockup — don't use the brand's semantic tokens at all. They're hardcoded Bootstrap defaults that never adapt to Night mode, plus a sixth, undocumented accent color (`--workout-color`) with the same problem.

For the open issues: #519 is the substantive design ask and this review provides full instructions below. #540 turns out to be largely already implemented (commits `8db109b`, `7e545c2`, `7a5b2a4`, `0780a06` over the last four days) — the remaining gap is a small, concrete UI-feedback item, not a redesign. #526 and #532 are infrastructure/backend tickets with no meaningful design surface; each gets a short note rather than a full section.

---

## Part 1 — Documentation Drift Findings

*Tracked as [#547](https://github.com/e2kd7n/ride-optimizer/issues/547).*

| ID | Area | Severity | Finding |
|---|---|---|---|
| DOC-1 | Brand Book §Rollout | P2 | States tokens are "not yet wired into `static/*.html` or `static/css/main.css`." False as of this review — `main.css:16-130` fully implements the Day/Night token table, including the dark-mode override block. `CLAUDE.md` already has this right; the Brand Book source doc doesn't. |
| DOC-2 | Card radius: 3-way conflict | P2 | `GRID_CONTRACT.md:266` says `border-radius: 8px`. `DESIGN_PRINCIPLES.md` §10 bullet list (line 307) says `10px`. `DESIGN_PRINCIPLES.md`'s own Common Patterns Library CSS (line 418) and the Brand Book both say `16px` — and that's what's actually shipped (`main.css:322`). Two of three docs are stale against the doc's own third section and against the code. |
| DOC-3 | §10 Buttons bullet list, self-contradiction | P3 | `DESIGN_PRINCIPLES.md` line 298 still lists primary-button color as `#667eea` (the pre-rebrand indigo the Brand Book explicitly retired) and destructive as `#dc3545`. The Common Patterns Library CSS two sections below (line 390, `var(--accent)`) already has the correct, current value. Whoever reads only the bullet list gets stale guidance. |
| DOC-4 | §10 Cards bullet vs. Common Patterns Library | P3 | Bullet list (line 309) gives card shadow as `0 2px 4px rgba(0,0,0,0.1)`; the CSS snippet a few lines later (line 419) gives `0 1px 2px rgba(0,0,0,0.08)` for the resting state. Not the same value — one of the two needs to go. |
| DOC-5 | v2.3 field note on Route Detail, resolved-but-marked-open | P2 | The v2.3 correction (line 464) calls Route Detail's `col-lg-5`/`col-lg-7` split "a known, not-yet-corrected deviation." Current code (`static/js/route-detail.js:474,534`) already ships `col-lg-7` (stats) / `col-lg-5` (map) — compliant with the >=`col-lg-6` rule. The dashboard hero row (`templates/index.html:92,131`, `col-lg-6`/`col-lg-6`) is likewise already fixed from the PLACE-DASH-2 finding. Both field notes need a "Resolved" annotation so nobody re-litigates or re-breaks a fix that already landed. |

**Root cause common to all five:** `DESIGN_PRINCIPLES.md` mixes two kinds of content — living rules (the numbered sections) and dated field notes (blockquotes citing specific review findings) — with no mechanism to mark a field note as resolved once its linked GitHub issue closes. The doc has no "last verified against code" step in its own update process.

---

## Part 2 — Undocumented, Unfixed Violations (not a docs problem — actual code gaps)

*SEM-1 through SEM-4 tracked as [#546](https://github.com/e2kd7n/ride-optimizer/issues/546). ERR-1 tracked as a comment on [#526](https://github.com/e2kd7n/ride-optimizer/issues/526).*

| ID | Area | Severity | Finding |
|---|---|---|---|
| SEM-1 | Hero card border + route status icons | P1 | `static/js/dashboard.js:658` (`hero-border-good/warn/bad`) and `:821-825` (`route-status-icon-great/good/fair/poor/bad`) render via `main.css:2109-2118`, which hardcodes raw Bootstrap hex (`#28a745`, `#ffc107`, `#dc3545`, plus two colors — `#20c997`, `#fd7e14` — that aren't in the palette at all) instead of `var(--success)/var(--warning)/var(--danger)`. These are the single most prominent decision surfaces on the app (literally the Brand Book's own "Today" reference screen) and they don't shift for Night mode at all — every other token in the system does. |
| SEM-2 | Score-bucket inconsistency | P2 | The hero border uses a 3-bucket scale (`good >=70 / warn >=50 / bad`, `dashboard.js:658`). The route-list status icon uses a 5-bucket scale for the same underlying score (`great >=80 / good >=65 / fair >=50 / poor >=35 / bad`, `dashboard.js:821-825`). Same number, two different bucket counts, in two widgets on the same screen. |
| SEM-3 | Workout-type badge reuses "poor fit" red for a neutral category | P2 | `WORKOUT_TYPE_BADGES` (`dashboard.js:27-36`) maps `VO2Max`/`Sprint`/`Anaerobic` to `bg-danger` — the same visual token `renderWorkoutFitRow`'s `ratingClass` (`dashboard.js:252-254`) uses to mean "poor fit." On the same workout-fit card these can both render red for unrelated reasons (a hard workout vs. a bad match), which is exactly the color-dilution failure mode the Brand Book calls out as the thing Fair Weather was designed to prevent. |
| SEM-4 | Undocumented, Night-blind accent color | P2 | `--workout-color: #e85d04` (`main.css:109-111`) is a sixth accent alongside cobalt/coral/success/warning/danger, absent from the Brand Book's token table entirely, and — unlike every other token — has no `:root[data-theme="dark"]` override. It keeps its light-tuned value against the `#122232`/`#0B1620` Night surfaces. |
| ERR-1 | Geolocation error messages are raw browser strings | P3 | `useMyLocation()` (`static/js/explore.js:505-509`) surfaces `err.message` from the Geolocation API directly via toast, undifferentiated by `err.code`. On the current HTTP-only Pi deployment this is the actual failure path for issue #526 — the user sees whatever implementation-defined string Chrome/Firefox picks for an insecure-origin denial, with no explanation or next step. |

---

## Part 3 — Remediation Plan

Ordered by leverage, not severity — the doc fixes are cheap and unblock everything else being trustworthy.

1. **Fix the docs first (DOC-1–5, #547).** Small text edits, no code risk, ~30 min total:
   - Brand Book: update §Rollout to state migration is complete, point at `main.css` as the reference implementation.
   - `DESIGN_PRINCIPLES.md` §10: delete the stale bullet-list color/shadow values (`#667eea`, `#dc3545`, `10px`, the mismatched shadow) and point the bullets at the Common Patterns Library CSS instead of duplicating values that will drift again.
   - `GRID_CONTRACT.md`: change card radius to 16px, or better, delete the duplicate card-anatomy section and cross-reference the Brand Book as sole source of truth for shape (Grid Contract should own spacing/sizing, not color/shape — see the existing `feedback_designer_audit_scope` split).
   - Add a "Resolved as of [date]/[commit]" line to the v0.17.0 field notes for Route Detail and Dashboard now that both are fixed, so the v2.3 correction doesn't keep pointing engineers at a non-bug.
   - Process fix: when a GitHub issue tied to a field note closes, that's the trigger to annotate the doc — add this one line to `docs/guides/PR_REVIEW_PROCESS.md` or wherever design-doc hygiene is checked.

2. **Fix SEM-1/SEM-2 together (#546)** (same files, same root cause): swap the five hardcoded hex values in `main.css:2109-2118` for `var(--success)`/`var(--warning)`/`var(--danger)`, and collapse the hero border's 3-bucket scale and the route-icon's 5-bucket scale onto one shared threshold function (put it once in `dashboard.js`, e.g. `scoreToRating(score)`, and have both call sites use it). This is the highest-value single fix in this review — it's the app's actual flagship screen.

3. **Fix SEM-3 (#546)**: recolor `WORKOUT_TYPE_BADGES` off the semantic success/warning/danger scale entirely — workout *category* isn't a value judgment, so give it a neutral treatment (e.g. `--accent`/`--ink-soft`-based, or the existing `--workout-color` token once SEM-4 gives it a Night value) so it can never collide with the adjacent fit-quality badge.

4. **Fix SEM-4 (#546)**: add a Night-mode value for `--workout-color` in the `:root[data-theme="dark"]` block (check contrast against `#122232`/`#16283A` — likely needs the same brightness-lift treatment the other accents got, e.g. lighten toward `#ff8a4d`-ish, verify with a contrast checker before committing to a value).

5. **ERR-1 (comment on #526)** is low cost, bundled into whichever ticket touches `useMyLocation()` next (naturally #526's verification step) — branch on `err.code` (`PERMISSION_DENIED`/`POSITION_UNAVAILABLE`/`TIMEOUT`) with copy for each, and special-case the insecure-origin case if detectable (`location.protocol !== 'https:' && location.hostname !== 'localhost'`) with an explanation rather than the raw browser string.

None of items 2–5 required new GitHub issues to be *filed* separately from #546 — they're small, contained diffs bundled as one "design-token cleanup" ticket rather than four separate ones.

---

## Part 4 — Design Instructions for Open Issues

### #519 — Recommend routes based on scheduled TrainerRoad outdoor workouts (primary ask)

**Correction to the issue's own premise, established during this review:** the issue states *"`PlannerService` has zero TrainerRoad integration today"* and suggests *"may need a new view/card rather than extending the existing commute flow."* Neither is accurate as of this review:

- `PlannerService.get_workout_rides()` (`app/services/planner_service.py:118-175`) already exists, is already wired end-to-end (`app/api/commute_bp.py:293-323,393-401` → `dashboard.js`'s `renderWorkoutRideOption()`, line 315), and already renders as a card on the dashboard today, gated behind `data.workout_ride` being present.
- The gap the issue is actually describing is real, but it's narrower than "build a new surface": `get_workout_rides()`'s scoring (`planner_service.py:138-161`) is 50% duration match / 30% route variety / 20% proximity to home. `workout_type` is accepted as a parameter and used only for display labeling — it never affects the score. Elevation is fetched and returned in the payload (`elevation_ft`, line 168) but likewise never scored. This *is* the "duration-only filtering, elevation never considered" problem the issue describes — it's just one layer more specific than the issue text suggests.

**Design instructions, given that grounding:**

1. **Do not build a new page.** Extend the existing workout-ride card. A dedicated Planner page is the CLAUDE.md-documented right home for the *long-ride planning* feature generally, but for this specific ask — "what route fits today's scheduled workout" — the existing dashboard surface already does the job and a second, competing entry point for the same decision would violate the app's own "one decision-first screen" thesis.

2. **Decouple the workout-ride card from commute-day gating.** Today, `workout_ride` is only computed inside `commute_bp.py`'s commute-recommendation flow (both call sites at lines 293 and 393 sit inside commute logic), and the issue itself flags the real scenario this breaks: a weekend Endurance ride has no commute to attach to, so the card likely never renders that day. The `workout-strip` element (`templates/index.html:86`, driven by `fetchTodayWorkout()`/`loadWorkoutStrip()`, `dashboard.js:11-13`) already loads independently of the commute recommendation once per dashboard load — move the workout-ride-matching call to hang off *that* fetch instead of the commute fetch, so it renders on any day a TrainerRoad workout is scheduled, commute or not.

3. **Time-urgency ordering (Design Principles §2) applies here directly.** On a day with a scheduled workout but no commute, the workout-ride recommendation *is* that day's time-sensitive actionable content — it must render in the hero position (first in DOM/visual order), not nested as a secondary card below a commute recommendation that doesn't exist that day. On a day with both a commute and a workout, current placement (workout-ride option alongside/below the commute hero) is fine — the commute is still the day's most time-urgent decision.

4. **Reuse the existing `workout-fit-row-reasons` pattern for match explanation.** `renderWorkoutFitRow()` (`dashboard.js:230-285`) already has a small-caption "why" line under the fit badge (`workout-fit-row-reasons`, `main.css:1886-1891`). When elevation/TSS-based scoring lands, surface *why* a route was suggested the same way — e.g. "Sustained 6% grade over 3 mi matches Threshold intervals" or "Flat, low-traffic loop — good fit for Recovery" — rather than a bare score. Don't invent a second explanation pattern.

5. **Fix SEM-3 (#546) before or alongside this work, not after.** This issue is about to add a *second* rating badge (route-profile match quality) onto a card that already has a workout-type badge miscolored as success/danger (see Part 2). Landing more badges on that card first will make the collision worse and harder to unwind later. Sequence: SEM-3 fix → then add the profile-match badge using the shared `scoreToRating()` from item 2 of the Remediation Plan, so category and fit-quality are visually and semantically distinct from day one.

6. **Jargon-free first use (§7) applies to TSS.** If Training Stress Score is surfaced as a label or number anywhere in the new UI (the issue explicitly proposes matching "expected duration/TSS"), it needs the same one-line-definition-on-first-render treatment Squadrats/Squadratinhos already got on Explore (`templates/explore.html:27-28,61-62`) — a tooltip or inline caption, not an assumption the user already knows TrainerRoad vocabulary.

7. **No new nav entry needed.** Keeping this on the dashboard avoids reopening the bottom-nav gap (Reports/Explore already missing from mobile bottom nav, tracked separately as #362) — don't add a seventh nav destination for what's really an enrichment of an existing one.

*Posted as a comment on [#519](https://github.com/e2kd7n/ride-optimizer/issues/519).*

---

### #540 — Relax distance/time adherence for point-to-point routing

This issue is **substantially already implemented** — `8db109b` ("Skip point-to-point distance-target padding when route is efficient", 2026-07-24) landed the efficient-baseline computation, the `ptp_wild_multiplier` split, and `refineRoute()`'s `skipExpansion` path almost exactly per the issue's proposed solution, with `7e545c2`, `7a5b2a4`, `0780a06`, and `b99648b` following up on adjacent behavior through 2026-07-28. Recommend the team reconcile the issue's checklist against what's shipped rather than treating this as greenfield.

**One real, concrete UI gap remains, found by reading the current `plotRoadRoute()` (`static/js/explore.js:1528` on):**

1. **Silent distance mismatch reads as a bug.** When `skipExpansion` is true, the user requested (say) 8 mi and gets back whatever the direct efficient route measures (say 5.2 mi) with *no on-screen explanation* — just a distance number in the badge row (`variantRow()`, line 1664+). Compare this to the existing `is_out_and_back` badge (line 1674-1676, from #452), which handles a structurally similar "the result isn't what you'd naively expect, here's why" case with a small `bg-secondary-subtle` badge and a `title` tooltip. Add the same pattern here: when `skipExpansion` was true for a variant, add a badge like `Direct route` with a tooltip along the lines of "Origin and destination are already {distLabel} apart by road — showing the efficient route instead of padding to your {targetLabel} target." This is a one-badge addition, reusing an established component, not new UI.

2. **Drop the misleading `(+)` suffix in skip-expansion mode.** In `skipExpansion` mode only `longOutcome` is computed (`shortOutcome = { route: null, message: null }`, line ~1572), so `renderVariant()` labels the single result `(+)` (line 1631) — the "long variant of a pair" label, even though there is no pair and nothing was lengthened. Use a distinct label (e.g. no suffix, or "Direct") when `skipExpansion` is true so the UI doesn't imply a short/long comparison that didn't happen.

3. **Recommend adding both as acceptance criteria** to #540 before closing it — the current checklist has three manual-test bullets and no UI-feedback requirement, which is how this gap made it through implementation unflagged.

*Posted as a comment on [#540](https://github.com/e2kd7n/ride-optimizer/issues/540).*

---

### #526 — Add HTTPS/TLS to Pi deployment

No design surface beyond what's noted as ERR-1 in Part 2/Remediation item 5 above (differentiate geolocation error messages by `err.code` rather than passing through the raw browser string). The infrastructure work itself (reverse proxy, cert provisioning) is out of design's lane. Once HTTPS lands, re-verify `useMyLocation()`'s error path is still reachable/testable — the insecure-origin branch of ERR-1 becomes moot but `PERMISSION_DENIED`/`TIMEOUT` still need distinct copy regardless of transport.

*Posted as a comment on [#526](https://github.com/e2kd7n/ride-optimizer/issues/526).*

### #532 — Persist ORS route cache to disk; add TTL to coverage-tile cache

No design surface — purely a backend caching/performance change with no user-visible behavior difference (same data, same UI, just durable across restarts). No action needed from design.

---

## Recommendations / Next Steps — Status

- Part 4's #519 instructions were posted as a comment on [#519](https://github.com/e2kd7n/ride-optimizer/issues/519).
- Part 1 (doc drift, DOC-1–5) filed as [#547](https://github.com/e2kd7n/ride-optimizer/issues/547).
- Part 2 items 2–4 (SEM-1–4, token/badge cleanup) filed as [#546](https://github.com/e2kd7n/ride-optimizer/issues/546).
- Part 2 item 5 (ERR-1) and the #540 UI-feedback gap were added as comments on [#526](https://github.com/e2kd7n/ride-optimizer/issues/526) and [#540](https://github.com/e2kd7n/ride-optimizer/issues/540) respectively, rather than filed as new issues, since both are small additions to work already tracked there.
- #532 has no design surface — nothing filed.

All findings in this review are now covered by an open issue or issue comment.