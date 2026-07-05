# Card & Object Placement — Design Review Findings
**Reviewer:** Subagent C (Card & Object Placement)
**Date:** 2026-07-04
**Issue:** #355
**Pages reviewed:** 7

---

## Summary

The app's card ordering is generally sound for desktop workflows but has three systemic problems: (1) Route Status sits above the commute recommendation on mobile (DOM source order), burying the primary decision below context; (2) the Weather page sequences a 7-day forecast before today's granular commute windows, inverting the time-urgency hierarchy; (3) the Reports right column leads with Gear (an administrative object) before the high-value Activity list that most users want to scan first. Several pages also place map context either too early (Explore coverage stats above everything) or too late (Route Detail performance charts below the fold without an anchor link), creating unnecessary scroll before the primary task is reachable.

---

## Findings

### DASHBOARD (static/index.html)

#### Finding ID: PLACE-DASH-1
**Severity:** P1
**Observation:** On mobile (single-column stack), `Route Status` (`#route-status-panel`) renders *before* the commute recommendation (`#commute-recommendation`) because it lives inside `col-lg-7` which is the *second* `col-lg-*` in the DOM row (lines 425–449). Bootstrap stacks columns in DOM source order. A cyclist opening the app on their phone at 6:55 AM therefore sees a list of route names before they see "Recommended / Not Recommended" — the only thing they actually need to act on.
**Evidence:** `static/index.html` lines 394–450. The row structure is:
```
col-lg-5  → Hero Decision Card (#commute-recommendation)   [DOM position 1]
col-lg-7  → Route Status (#route-status-panel) + map       [DOM position 2]
```
On desktop this is fine (side by side). On mobile the stack order is: Commute card → Route Status → Map — but `col-lg-7` contains Route Status *above* the map inside that column, so on mobile the full stacking is: Hero Card → Route Status → Map. The Route Status panel (`#route-status-panel`) provides supporting context ("which routes are available today"), not the decision itself. The decision (`#commute-recommendation`) correctly appears first, but the `col-lg-7` wrapper means the Route Status is squeezed between the commute card and the map rather than deferred below.
**Recommendation:** Move `#route-status-panel` (the small card, lines 426–438) *below* the map within `col-lg-7`, not above it. On mobile this makes the stack: Hero Decision → Map → Route Status, keeping the spatial context (map) between decision and supporting detail. Alternatively, use `order-lg-1` / `order-lg-2` utilities to flip the right-column internal order on mobile.
**Principle violated:** §1 Mobile-First, §2 Progressive Disclosure

---

#### Finding ID: PLACE-DASH-2
**Severity:** P2
**Observation:** The `col-lg-5` / `col-lg-7` split allocates 42% of desktop width to the commute decision and 58% to map + route status. The commute card is the primary decision surface (API confirms it returns a scored recommendation: `"score": 82, "recommendation": "Recommended"`). The supporting map only visualises the recommended route. The current ratio makes the supporting panel larger than the decision panel, which inverts visual hierarchy — the bigger object draws the eye first.
**Evidence:** `static/index.html` line 396 (`col-lg-5`) and line 425 (`col-lg-7`). The API at `/api/recommendation` returns a composite score, route name, weather breakdown, and departure time — all content that benefits from more horizontal display space (multiple factor rows). The map is purely confirmatory.
**Recommendation:** Swap to `col-lg-6` / `col-lg-6` or `col-lg-7` (decision) / `col-lg-5` (map+status) to give the primary decision panel equal or greater visual weight than the supporting map.
**Principle violated:** §3 Visual Hierarchy

---

#### Finding ID: PLACE-DASH-3
**Severity:** P2
**Observation:** The "How It Works" button (`data-bs-target="#howItWorksModal"`) is placed at the very top of `<main>` (lines 356–362), above the weather banner and above the commute recommendation. This is the first interactive element a returning user encounters on every visit, even though it is never needed for the daily go/no-go decision. It occupies prime above-the-fold real estate, pushing time-sensitive content (weather, commute) slightly further down.
**Evidence:** `static/index.html` lines 356–362 — the `d-flex justify-content-end mb-1` wrapper precedes the `#weather-banner` div at line 365.
**Recommendation:** Relocate the "How It Works" button to the page footer or to a persistent help icon in the navbar. It is a first-time-user affordance and should not compete with daily operational content.
**Principle violated:** §2 Progressive Disclosure, §3 Visual Hierarchy

---

### ROUTES LIBRARY (static/routes.html)

#### Finding ID: PLACE-ROUTES-1
**Severity:** P2
**Observation:** The filter card (lines 67–161) contains two rows: quick preset buttons + search (row 1) and seven dropdown/input controls (row 2). On mobile, all seven dropdowns stack vertically inside the filter card before a single route is visible. The user must scroll past the entire filter panel to reach the route list. For the 221 routes in the dataset, the most common task is "show me everything, sorted by Most Used" — a read-only browse rather than a filter operation.
**Evidence:** `static/routes.html` lines 67–161 (filter card) vs. lines 184–264 (route list + map). The route list container `#routes-container` (line 187) does not appear in the DOM until after the full filter card. On mobile (320 px viewport) the second row of filters alone renders 7 controls stacked vertically, pushing the route list ~350 px below the fold.
**Recommendation:** Collapse the second filter row (dropdowns) behind a "More Filters" toggle by default on mobile, so users land immediately on the route list with only search + preset buttons visible. This follows the pattern already used for the Saved Plans section (lines 164–176).
**Principle violated:** §1 Mobile-First, §2 Progressive Disclosure

---

#### Finding ID: PLACE-ROUTES-2
**Severity:** P2
**Observation:** The `col-lg-5` (route list) / `col-lg-7` (map) split gives more than half the desktop width to the map, while the route cards — which contain the decision-driving data (name, distance, elevation, uses) — are cramped into 42%. For the primary task of comparing and choosing a route from 221 options, the list panel is the decision surface; the map is confirmatory. The ratio is inverted.
**Evidence:** `static/routes.html` lines 186 (`col-lg-5` route list) and 230 (`col-lg-7` map). The route list is additionally constrained by `#routes-container .row > [class*="col-"] { flex: 0 0 100%; max-width: 100%; }` (lines 18–22), forcing all route cards to full-width within the already-narrow column.
**Recommendation:** Swap to `col-lg-7` (route list) / `col-lg-5` (map) to give the decision surface more room. The map still renders at a generous width and remains sticky.
**Principle violated:** §3 Visual Hierarchy

---

#### Finding ID: PLACE-ROUTES-3
**Severity:** P3
**Observation:** On mobile, the map (`col-lg-7`) stacks *below* the route list (`col-lg-5`) because of DOM order (list first, map second — lines 186 and 230). This is actually the correct priority order for mobile. However, the `Saved Plans` section (lines 164–176) is hidden by default (`style="display: none"`). When plans exist and become visible, they appear between the filter card and the results summary, which is the right location. No ordering issue here — call this a confirmation that the current Saved Plans placement is correct.
**Evidence:** `static/routes.html` lines 163–176. The `#saved-plans-section` is `display: none` until populated by JS — its DOM position between filters and route list is correct.
**Recommendation:** No change needed for Saved Plans placement. Low-priority note only.
**Principle violated:** N/A (documentation only)

---

### ROUTE DETAIL (static/route-detail.html)

#### Finding ID: PLACE-DETAIL-1
**Severity:** P2
**Observation:** The Performance Trends charts (`#performance-metrics-card`, lines 546–570) are rendered as a full-width card *below* both the stats/map row and the route history tables. They require significant scrolling to reach, yet for a returning cyclist looking at a route they've ridden 89 times (e.g. "Gravel for Breakfast" — 89 uses per API), these trend charts are high-value: they show whether speed and duration are improving. The current depth ordering buries actionable performance intelligence below administrative history lists.
**Evidence:** `static/route-detail.html` lines 440–456 (`longRideUsesMarkup` and `routeHistoryMarkup` render *inside* `col-lg-5`), with `#performance-metrics-card` at lines 546–570 rendered after the entire two-column stats+map row closes at line 543. The route API returns `activity_dates` with 57 entries for route `17654454601` — ample data for meaningful charts. The charts are hidden by default (`style="display: none"`) until JS activates them.
**Recommendation:** Move Performance Trends up into the `col-lg-5` left column, immediately below the key stats card and above the uses/history tables. The history tables (which list individual rides) are lower-value than the aggregate trend lines and should be at the bottom. Also add a `#performance` anchor to enable in-page navigation from the stat cards.
**Principle violated:** §2 Progressive Disclosure, §3 Visual Hierarchy

---

#### Finding ID: PLACE-DETAIL-2
**Severity:** P2
**Observation:** On mobile, the `col-lg-5` stats card stacks above the `col-lg-7` map — which is the correct order (know your route stats, then see the map). However, the sticky map behavior (`position: sticky; top: var(--space-3)`) at line 535 only works on large screens. On mobile the map simply flows inline. The route map height is `var(--map-height-standard)` with a responsive override to `320px` on `<= 991.98px` (line 17–19 in `<style>`). At 320px mobile width, a 320px map occupies the full viewport height, meaning the user has no visible content above or below it — no route name, no stats, no scroll cue. The map effectively becomes a full-screen dead end.
**Evidence:** `static/route-detail.html` line 538: `style="height: var(--map-height-standard); border-radius: 8px;"`. At `max-width: 991.98px` the map is reduced to `320px` (CSS lines 17–19). On a 320px-wide mobile device with ~56px navbar, the map fills the remaining viewport.
**Recommendation:** Add a `max-height: 50vh` cap on the map for mobile (`max-width: 767px`), or reduce the `991.98px` breakpoint override to `240px` for small phones, so the stats card remains partially visible above the map and the user understands they can scroll.
**Principle violated:** §1 Mobile-First

---

### REPORTS (static/reports.html)

#### Finding ID: PLACE-REPORTS-1
**Severity:** P2
**Observation:** In the two-column layout (`col-lg-5` left / `col-lg-7` right), the **right column** leads with `Gear` (lines 361–386) before the `Activity list` (lines 388–432). On the `col-lg-7` right side, Gear occupies the top ~150px and pushes the activity table entirely off-screen on desktop. Yet for a cyclist opening Reports, the most common task is scanning their recent activities. Gear is an administrative grouping used to filter the activity list — it is a secondary control, not primary content.
**Evidence:** `static/reports.html` lines 358–434. The right column `col-lg-7` DOM order: `div.card` (Gear, lines 362–386) → `div.card` (Activities, lines 388–432). The gear card header alone contains four action buttons: "Sync Gear", "Backfill Gear IDs", "Clear Filter" (lines 368–378), making it visually heavy relative to its usage frequency.
**Recommendation:** Swap the order within `col-lg-7`: place the Activity list card first, and move the Gear card below it. On mobile this makes the stack: Stats → PRs + Charts (left column) → Activities → Gear. Gear filtering is a power-user feature that warrants secondary placement.
**Principle violated:** §2 Progressive Disclosure, §3 Visual Hierarchy

---

#### Finding ID: PLACE-REPORTS-2
**Severity:** P2
**Observation:** The left column (`col-lg-5`) stacks five cards: Personal Records → Activity Type Breakdown → Monthly Distance → Speed Distribution → Elevation per Ride (lines 262–354). Monthly Distance is the third card, requiring a scroll on desktop. Yet the headline stat cards (Rides / Miles / Hours / Feet) already give totals — Monthly Distance is the first *trend* view, which is typically the most compelling and decision-relevant chart. Users looking for "am I riding more this year?" need the Monthly Distance chart immediately after the headline numbers, not after the PR and type breakdown cards.
**Evidence:** `static/reports.html` lines 262–303 (Personal Records, card 1 in left col), lines 305–315 (Activity Type Breakdown, card 2), lines 317–328 (Monthly Distance, card 3). The 7 months of API data from `/api/stats` (`by_month` array from April 2024) makes this chart data-rich and immediately useful.
**Recommendation:** Reorder the left column: Monthly Distance first (rename to "Your Trend"), then Personal Records, then Activity Type Breakdown. Speed and Elevation distributions remain at the bottom as analytical deep-dives.
**Principle violated:** §2 Progressive Disclosure

---

### EXPLORE (static/explore.html)

#### Finding ID: PLACE-EXPLORE-1
**Severity:** P2
**Observation:** The page opens with three coverage stat chips (`#coverage-stats`, lines 85–104) before the map. These chips show "Tiles Visited / Coverage / Total in View" — numbers that are meaningless without the map context. A user arriving at Explore for the first time sees three abstract numbers (e.g. "0.0% Coverage" from the API), then a large map, then controls. The numbers only become interpretable once the user has seen the map. Presenting them first creates cognitive friction.
**Evidence:** `static/explore.html` lines 85–104 (`#coverage-stats` row) precedes lines 107–111 (map card). The `/api/exploration/tiles` endpoint returns `coverage_pct: 0.0` with `total_in_bounds: 14,303,328` — numbers that require geospatial context to interpret.
**Recommendation:** Move the coverage stat chips *below* the map, or integrate them as an overlay/legend inside the map card header. The map should be the first thing the user sees on Explore — it is the page's primary visual object.
**Principle violated:** §2 Progressive Disclosure, §3 Visual Hierarchy

---

#### Finding ID: PLACE-EXPLORE-2
**Severity:** P2
**Observation:** The Route Generation controls (lines 134–189) are positioned *below* the map and controls card, making the primary action (Generate Routes) the last element on the page. The cognitive flow is: numbers → map → coverage type selector → generate button. A user who arrives wanting to plan a new exploration ride must scroll past the full map to reach the generation inputs. The map at 500px height (line 12–14) on desktop, combined with the controls card, puts the Generate button approximately 800px below the fold.
**Evidence:** `static/explore.html` lines 107–111 (map, 500px), lines 113–132 (controls card), lines 134–189 (route generation card). On mobile the map reduces to 350px (line 17–19) but the generation card still appears last.
**Recommendation:** Reorder to: Route Generation controls (task-first) → Map → Coverage Stats + Coverage Type selector. The user sets their intent (distance, start point, optimization) before the map renders their result. Alternatively, split the page into a two-column layout on desktop: generation controls left (`col-lg-4`) / map right (`col-lg-8`), with coverage stats below.
**Principle violated:** §1 Mobile-First, §2 Progressive Disclosure

---

### WEATHER (static/weather.html)

#### Finding ID: PLACE-WEATHER-1
**Severity:** P1
**Observation:** The 7-day forecast card (lines 172–194) appears *before* Today's Commute Windows (lines 196–230) in the DOM. The 7-day forecast answers "which day this week is good for a long ride?" — a planning question. Today's Commute Windows answer "should I ride to work this morning and what time?" — an immediate, time-sensitive action question. For a cyclist consulting the weather page at 6:30 AM, the commute windows are the most urgent content. The ordering buries them behind a week-view grid.
**Evidence:** `static/weather.html` lines 172–194 (7-day forecast) then lines 196–230 (commute windows). The `/api/weather/commute-windows` response shows morning optimal departure at `07:00` with `precip_prob: 6%` and evening at `15:00` with `precip_prob: 29%` — high-urgency, time-specific data. The `/api/weather/forecast` 7-day data shows the *same* day as one of seven equal-weight cards.
**Recommendation:** Reorder to: Transit Alert (conditional, already first — correct) → Today's Commute Windows → 7-Day Forecast. The commute windows are today's actionable recommendation; the forecast is planning context. This matches the same priority pattern as the Dashboard (immediate recommendation before supporting data).
**Principle violated:** §2 Progressive Disclosure, §3 Visual Hierarchy

---

#### Finding ID: PLACE-WEATHER-2
**Severity:** P3
**Observation:** The Transit Alert (`#transit-alert`, lines 157–170) is conditionally shown when today is unfavorable. This is positioned correctly at the top. However, when it is *not* shown, there is no "all clear" equivalent — the page opens with the `d-flex` header containing only the h2 title and immediately jumps to the 7-day forecast card. There is no at-a-glance "today is good" positive confirmation that mirrors the urgency of the transit alert. The absence of a positive-state card for today creates an asymmetric information hierarchy.
**Evidence:** `static/weather.html` lines 153–156 (title div) followed immediately by `#transit-alert` (hidden when not needed) then the forecast card. There is no "today looks great to ride" positive card.
**Recommendation:** Add a small "Today at a Glance" card (reusing the current-conditions data from `/api/weather`) that shows comfort score, temp, and wind regardless of favorable/unfavorable status. Position it immediately below the title, collapsing the transit alert into it when unfavorable.
**Principle violated:** §3 Visual Hierarchy

---

### SETTINGS (static/settings.html)

#### Finding ID: PLACE-SETTINGS-1
**Severity:** P2
**Observation:** The `Connections` section (lines 189–452) — which contains Strava sync, Run Analysis, intervals.icu, Garmin Connect, and TrainerRoad — is a full-width card below the User Preferences / Data Management pair. Within the Connections card, the section order is: Strava connection status → cache info → Sync from Strava → Run Analysis → intervals.icu → Garmin Connect → TrainerRoad. This groups data *sources* (Strava, Garmin) with data *actions* (Run Analysis) and buries TrainerRoad — the only connection that *changes daily behavior* (outdoor workout recommendations) — at the very bottom behind a collapsed chevron.
**Evidence:** `static/settings.html` lines 189–452. TrainerRoad section starts at line 386 and is behind `data-bs-toggle="collapse"`. The `Outdoor Workout Preferences` card (lines 454–505) which *depends on* TrainerRoad being connected, appears after Connections as a separate full-width card. A user who wants to configure outdoor workout thresholds must scroll past all of Connections (250+ lines of DOM) to find it, even though the two are functionally linked.
**Recommendation:** Move `Outdoor Workout Preferences` directly inside the Connections card, nested beneath the TrainerRoad section (currently lines 403–447), so the threshold controls appear immediately when TrainerRoad is expanded. Alternatively, if kept as a separate card, place it *before* Connections (after User Preferences) since it is a behavior preference, not a connection setting.
**Principle violated:** §2 Progressive Disclosure

---

#### Finding ID: PLACE-SETTINGS-2
**Severity:** P2
**Observation:** The `About` section (lines 507–540) — which contains the version number, data sources, and GitHub links — is placed *before* the Save Settings / Reset buttons row (lines 542–555). The About card is purely informational and has no interaction except two external links. A user who has just changed settings must scroll past About to reach the Save button. This inverts the action-first principle: the most frequent action (saving settings) should never be buried below inert content.
**Evidence:** `static/settings.html` DOM order: row with User Prefs + Data Mgmt (line 67) → Connections (line 190) → Outdoor Prefs (line 455) → About (line 508) → Save/Reset buttons (line 542). The Save button is the last meaningful interactive element on the page.
**Recommendation:** Move the `Save Settings` / `Reset to Defaults` button row immediately after the `Outdoor Workout Preferences` section (before About). Move the `About` card to the very bottom of the page. The form action should never be separated from the form fields by non-form content.
**Principle violated:** §2 Progressive Disclosure

---

#### Finding ID: PLACE-SETTINGS-3
**Severity:** P3
**Observation:** `User Preferences` (col-md-6, lines 67–130) and `Data Management` (col-md-6, lines 132–186) are side by side. `Data Management` contains a "Danger Zone" with destructive actions (`Clear Favorites`, `Clear All Local Data`). Placing destructive actions in the same visual weight column as daily-use preferences (unit system, display options) creates accidental proximity — the Danger Zone is a `col-md-6` peer of the Unit System selector.
**Evidence:** `static/settings.html` lines 132–186. The Danger Zone heading is at line 168 (`text-danger`) but the buttons (`Clear Favorites`, `Clear All Local Data`) are at lines 172–178, visually equidistant from the Unit System selector in the left column.
**Recommendation:** Move destructive actions to the bottom of the Data Management card behind a collapsed `<details>` element or an explicit "Show Danger Zone" toggle. This is a polish item — the current approach is not critically harmful but increases misclick risk.
**Principle violated:** §3 Visual Hierarchy

---

## Cross-Page Patterns

**Pattern 1: Map oversized relative to decision content (P2, recurring)**
Three pages (`index.html` via `col-lg-7`, `routes.html` via `col-lg-7`, `route-detail.html` via `col-lg-7`) give the map column more Bootstrap columns than the decision/data column. In each case the map is supporting context, not the primary task. A consistent audit and re-balancing toward `col-lg-6`/`col-lg-6` or `col-lg-7`/`col-lg-5` (data-heavier) would correct the visual weight across the app.

**Pattern 2: Administrative / supporting cards before primary-task cards (P2, recurring)**
On Reports (Gear before Activities), Explore (Coverage stats before Map), and Weather (7-day forecast before Commute Windows), secondary or aggregate content precedes the primary interactive or time-sensitive content. The app consistently places "context" cards above "action" cards. Inverting this order — action/decision first, context below — would unify the UX pattern across pages.

**Pattern 3: Mobile stacking not validated for all right-column subordinate content (P1/P2)**
`index.html` (Route Status within `col-lg-7`) and `route-detail.html` (320px map fills viewport) show that inner-column ordering on mobile has not been systematically reviewed. When a `col-lg-*` column contains multiple stacked cards, the top card within that column gets the second-best mobile position (after `col-lg-5`). This means whatever is placed first inside `col-lg-7` becomes the third most prominent element on mobile — and in both Dashboard and Route Detail, the element placed there is supporting context, not primary content.

**Pattern 4: "How It Works" / onboarding content above operational content (P2)**
The Dashboard "How It Works" button appears above weather and commute data. This is a first-time-user affordance living permanently in prime real estate. No other page repeats this pattern, making it inconsistent as well as spatially wasteful.

---

## Prioritized Recommendation List

| Priority | Finding ID | Page | Severity | Summary |
|----------|------------|------|----------|---------|
| 1 | PLACE-WEATHER-1 | Weather | P1 | Commute windows below 7-day forecast — swap order |
| 2 | PLACE-DASH-1 | Dashboard | P1 | Route Status renders before commute decision on mobile |
| 3 | PLACE-DASH-2 | Dashboard | P2 | col-lg-5 (decision) narrower than col-lg-7 (map) — invert ratio |
| 4 | PLACE-DASH-3 | Dashboard | P2 | "How It Works" button above weather banner — relocate |
| 5 | PLACE-REPORTS-1 | Reports | P2 | Gear card above Activity list in col-lg-7 — swap order |
| 6 | PLACE-REPORTS-2 | Reports | P2 | Monthly Distance chart is 3rd card in left column — move to 1st |
| 7 | PLACE-EXPLORE-1 | Explore | P2 | Coverage stats above map — move below or integrate as overlay |
| 8 | PLACE-EXPLORE-2 | Explore | P2 | Route generation controls at bottom — move above map |
| 9 | PLACE-ROUTES-1 | Routes Library | P2 | Full filter panel visible on mobile before any routes show |
| 10 | PLACE-ROUTES-2 | Routes Library | P2 | col-lg-5 (route list) narrower than col-lg-7 (map) — invert ratio |
| 11 | PLACE-DETAIL-1 | Route Detail | P2 | Performance charts below history tables — move charts up |
| 12 | PLACE-DETAIL-2 | Route Detail | P2 | 320px map fills mobile viewport with no scroll cue |
| 13 | PLACE-SETTINGS-1 | Settings | P2 | Outdoor Workout Preferences separated from TrainerRoad section |
| 14 | PLACE-SETTINGS-2 | Settings | P2 | Save button buried below About card |
| 15 | PLACE-WEATHER-2 | Weather | P3 | No positive "today looks good" state card when transit alert is hidden |
| 16 | PLACE-ROUTES-3 | Routes Library | P3 | Saved Plans placement confirmed correct (no action needed) |
| 17 | PLACE-SETTINGS-3 | Settings | P3 | Danger Zone buttons at same visual level as daily-use preferences |
