# Information Density — Design Review Findings
**Reviewer:** Subagent A (Information Density)
**Date:** 2026-07-04
**Issue:** #353
**Pages reviewed:** 7

---

## Summary

Most pages carry an appropriate overall volume of information, but the distribution within pages is uneven: primary decision metrics are frequently buried among secondary data, §2 Progressive Disclosure is inconsistently applied across all pages, and two pages (Reports and Settings) pack genuinely unrelated concerns into shared cards. The Dashboard — the app's highest-traffic page — is the strongest performer, though its secondary weather detail competes with the primary commute decision. The most critical gap is the Route Detail page, which renders a weather block as a raw JSON `<pre>` dump inside the primary metrics card, directly breaking the user's ability to scan key facts.

---

## Findings

---

### DASHBOARD (`static/index.html`)

#### Finding ID: ID-DASH-1
**Severity:** P2
**Observation:** The hourly forecast strip (`#hourly-forecast`) is rendered immediately below the weather banner and above the hero commute card, giving weather data two consecutive full-width sections before the user reaches the primary action (commute recommendation). The three most-important facts for the dashboard's purpose — "Should I ride to work?", composite score, and departure time — live below the fold on most desktop screens after the weather banner + hourly strip occupy ~200 px.
**Evidence:** `index.html` lines 365–387: `#weather-banner` (full-width gradient block) is immediately followed by `.weather-hourly-strip` containing 6 hourly skeleton cards at `height:80px` each. The hero card (`col-lg-5`, line 396) only starts after this combined block. The `/api/recommendation` response shows the three critical values (`composite: 76.6`, `departure_time: "7:00 AM"`, `recommendation: "Recommended"`) that are rendered inside this subordinate card.
**Recommendation:** Collapse the hourly strip to a single-line scrollable row (max 56 px tall) by default, with a "Show full forecast →" toggle that expands it. This recovers ~100 px so the hero commute card is above the fold on 768 px+ screens without scrolling.
**Principle violated:** §2 Progressive Disclosure — secondary detail (hourly strip) precedes primary decision output.

#### Finding ID: ID-DASH-2
**Severity:** P2
**Observation:** The Route Status panel (`#route-status-panel`) is placed in the same column as the map (`col-lg-7`, lines 425–450), but it contains information unrelated to the map view: it summarises how many route groups exist and when data was last analysed. This data belongs logically with the commute recommendation, not with the map.
**Evidence:** `index.html` lines 426–439 place `#route-status-panel` (h6: "Route Status") directly above the commute map iframe. The `/api/status` response confirms the data rendered here (`route_groups_count: 221`, `last_analysis`, `is_stale`) describes the data-pipeline health, not the visible map content.
**Recommendation:** Move the Route Status panel below the hero commute card in the left column (`col-lg-5`) as a collapsed `<details>` or small muted metadata row. The map column should contain only map-related controls/legend.
**Principle violated:** §2 Progressive Disclosure — data-pipeline metadata mixed with primary route/map content; §3 Visual Hierarchy — card grouping does not reflect information relationship.

#### Finding ID: ID-DASH-3
**Severity:** P3
**Observation:** The `#commute-detail` collapse (`index.html` line 417) is hidden by default and shows "both directions" data, but there is no visible count or teaser to indicate it has content worth expanding. Users have no affordance to know that clicking "Compare directions" surfaces additional data.
**Evidence:** `index.html` lines 416–419: `<div class="collapse" id="commute-detail">` with inner `#commute-cards` rendered empty until the toggle is activated. The `/api/recommendation` response contains a full `breakdown` object (time, distance, safety, weather sub-scores) that only becomes visible after interaction.
**Recommendation:** Add a single-line summary teaser (e.g. "↕ Compare both directions — to-home score: 76") as static text above the collapse toggle so users know the secondary content exists.
**Principle violated:** §2 Progressive Disclosure — secondary content is discoverable but has no teaser to invite interaction.

---

### ROUTES LIBRARY (`static/routes.html`)

#### Finding ID: ID-ROUTES-1
**Severity:** P2
**Observation:** The filter bar (`routes.html` lines 67–161) presents 9 filter/sort controls in a single card with two flex rows. On a 1280 px desktop, this entire block is visible, but on 992–1200 px breakpoints the controls wrap into 3+ lines, consuming up to 40 % of the viewport before any routes are shown. There is no "collapsed" or "Advanced filters" mode.
**Evidence:** `routes.html` lines 89–159: Row 2 contains 8 labelled controls (Favorites, Commute, Type, Difficulty, Min distance, Max distance, Ridden, Sort). All are unconditionally visible. The four preset buttons in Row 1 (All, Short, Medium, Long) already provide quick filtering; the 8 advanced controls in Row 2 duplicate or refine the same dimension.
**Recommendation:** Keep Row 1 (presets + search + sort) always visible. Move Row 2 controls (Favorites, Commute, Type, Difficulty, Min/Max distance, Ridden) into a collapsible "Advanced Filters" panel, defaulting to collapsed. Show a badge indicating how many advanced filters are active.
**Principle violated:** §2 Progressive Disclosure — all filter controls shown simultaneously regardless of user intent.

#### Finding ID: ID-ROUTES-2
**Severity:** P3
**Observation:** The `#results-summary` alert (`routes.html` line 179: `alert alert-info`) uses the full Bootstrap alert styling (blue background, icon, padding) to convey a simple count ("221 routes, showing 1–20"). This styling signals importance/urgency disproportionate to the information's role as a passive status line.
**Evidence:** `routes.html` line 179: `<div id="results-summary" class="alert alert-info">`. The API returns 221 routes (`/api/routes?limit=10` → `total_count: 10` for the paged view). A count summary is secondary metadata, not an alert.
**Recommendation:** Replace the `alert alert-info` with a simple muted small-text line (`<p class="text-muted small mb-2">`) consistent with the table-footer style used in Reports.
**Principle violated:** §3 Visual Hierarchy — alert styling elevates secondary metadata to the same visual weight as actionable system alerts.

#### Finding ID: ID-ROUTES-3
**Severity:** P3
**Observation:** The `#saved-plans-section` card (`routes.html` lines 163–176) is hidden by default (`display: none`) and has no teaser or count indicator. When plans do exist, users navigating directly to the Routes page cannot tell that saved plans are surfaced here.
**Evidence:** `routes.html` line 164: `style="display: none;"`. No adjacent element announces the section's existence when it becomes visible. The Routes page is the natural place to discover saved plans, but they are invisible on first load.
**Recommendation:** Show a persistent but minimal header row (e.g. "0 saved plans") that changes to a highlighted link ("3 saved plans — view →") when plans exist. The collapse can still hide the plan cards themselves.
**Principle violated:** §2 Progressive Disclosure — content existence is not surfaced; secondary content hidden without any affordance.

---

### ROUTE DETAIL (`static/route-detail.html`)

#### Finding ID: ID-RDTL-1
**Severity:** P1-high
**Observation:** When `route.weather` is populated, its data is rendered as a raw `JSON.stringify` block inside a `<pre>` tag directly within the primary metrics card (`route-detail.html` line 528). This dumps unformatted JSON into the middle of the key metrics grid, destroying scannability of the primary card.
**Evidence:** `route-detail.html` lines 528: `<pre class="mb-0 small mt-1">${route.weather ? JSON.stringify(route.weather, null, 2) : ''}</pre>`. The weather object appears inline after the distance/duration/elevation/uses metric grid. Additionally, `weatherMarkup` is declared at line 430 and produces a full standalone card (`card mt-4`) but is never inserted into the DOM — only the inline `<pre>` version at line 528 is rendered. The `/api/routes/17654454601` response shows `weather: null` today, but any route with weather data would trigger this.
**Recommendation:** Remove the inline `<pre>` at line 528 entirely. The standalone `weatherMarkup` card (lines 430–436) is the correct pattern — restore its insertion into the rendered output, and render weather fields as labelled key-value rows matching the style of the distance/duration/elevation metrics.
**Principle violated:** §3 Visual Hierarchy — raw debug output mixed into the primary metrics card collapses the visual hierarchy; §2 Progressive Disclosure — raw JSON is neither primary nor secondary content, it is unprocessed data.

#### Finding ID: ID-RDTL-2
**Severity:** P2
**Observation:** The page's three primary facts (distance, duration, elevation) are placed in a 2×2 grid (`col-6` pairs) inside the left column card (`route-detail.html` lines 490–527), but "Uses" — a secondary social/popularity metric — occupies the fourth equal slot alongside them, giving it the same visual weight as the core route metrics. Per §2, the three primary metrics are distance, duration, and score; "Uses" is secondary.
**Evidence:** `route-detail.html` lines 518–526: `<div class="col-6">` block for "Uses" (value: `route.uses || 0`) uses identical markup to Distance, Duration, and Elevation. The `/api/routes/17654454601` response confirms `uses: 89` — a useful but non-primary metric.
**Recommendation:** Demote "Uses" out of the primary 2×2 grid. Place it as a muted chip or badge in the route title row (alongside the existing `.detail-chip` elements at line 464), where it reads as supplemental metadata rather than a primary stat.
**Principle violated:** §2 Progressive Disclosure — secondary metric (uses/popularity) presented at same hierarchy level as primary route metrics.

#### Finding ID: ID-RDTL-3
**Severity:** P2
**Observation:** The Performance Trends card (`#performance-metrics-card`, lines 546–570) renders 4 Chart.js line charts (speed, duration, heart rate, power) in a 2×2 grid and is hidden when fewer than 2 route records exist. For the most-used route ("Gravel for Breakfast", 89 uses), the `routes` array is empty (`"routes": []`), so the charts never appear even though ride history (89 activity dates) is available. The available data — activity_dates, activity_names — is only shown in the "All rides on this route" table below.
**Evidence:** `route-detail.html` line 187: `if (!Array.isArray(route.routes) || route.routes.length < 2) { return; }`. The `/api/routes/17654454601` response shows `"routes": []` and `"activity_ids": [...]` with 89 entries. The performance trend section is permanently hidden for this route despite rich history being available.
**Recommendation:** When `route.routes` is empty but `route.activity_ids` is populated, show a simplified "Activity History" chart using the activity_dates array (ride count per month) instead of hiding the entire section. This surfaces the historical engagement data that exists in the API response.
**Principle violated:** §2 Progressive Disclosure — meaningful secondary data (ride history trend) is silently suppressed rather than shown in an appropriate reduced form.

---

### REPORTS (`static/reports.html`)

#### Finding ID: ID-RPT-1
**Severity:** P2
**Observation:** The "Extra stats" row (`#extra-stats-row`, lines 237–256) shows Avg HR, Kilojoules, and Kudos as three equal headline cards immediately below the four primary stats. The API confirms all three return `0` or `null` for this dataset (`avg_heartrate: null`, `total_kilojoules: 0`, `total_kudos: 0`). Empty/zero secondary metrics displayed at primary hierarchy weight create visual clutter without informational value.
**Evidence:** `reports.html` lines 238–256: three `col-4` stat-cards with `.stat-value` (same CSS class as primary stats) for HR (`—`), KJ (`—`), and Kudos (`—`). The `/api/stats` response shows `avg_heartrate: null`, `total_kilojoules: 0`, `total_kudos: 0` across all periods.
**Recommendation:** Conditionally hide the extra-stats row (or individual cards within it) when all values are null/zero. When at least one value is populated, show the row but use a smaller `.stat-value` size (e.g. `font-size: var(--font-size-base)`) to distinguish secondary from primary stats.
**Principle violated:** §2 Progressive Disclosure — secondary metrics permanently displayed at primary weight regardless of data availability.

#### Finding ID: ID-RPT-2
**Severity:** P2
**Observation:** The "Gear" card (`reports.html` lines 361–386) in the right column contains three admin/maintenance buttons ("Sync Gear", "Backfill Gear IDs", "Clear Filter") alongside the gear breakdown data. These are operational controls unrelated to reading analytics; they belong in Settings, not in the analytics page.
**Evidence:** `reports.html` lines 367–379: `#refresh-gear-btn` (Sync Gear), `#backfill-gear-btn` (Backfill Gear IDs), `#clear-gear-filter-btn` (Clear Filter) are rendered inside the analytics Gear card header. The `/api/stats/gear` response shows `gear_cache_available: false` and `gear: []` — the sync buttons appear even when no gear data exists, making them the most prominent content in the card.
**Recommendation:** Move "Sync Gear" and "Backfill Gear IDs" to the Settings > Connections > Strava section, where data-management actions already live. Keep only "Clear Filter" (which is contextual to the gear filter interaction) in the Reports Gear card, and only show it when a filter is active.
**Principle violated:** §2 Progressive Disclosure — data-management actions mixed into an analytics view; §3 Visual Hierarchy — operational controls compete with data for attention in a read-only context.

#### Finding ID: ID-RPT-3
**Severity:** P2
**Observation:** The left column contains 5 stacked card sections: Personal Records, By Activity Type, Monthly Distance, Speed Distribution, and Elevation per Ride. At 64 px chart height (`.bar-chart { height: 64px }`), the three distribution charts (Monthly, Speed, Elevation) are too small to extract value from — they read as decorative bars rather than functional charts — while the column itself is very long (5 sequential cards require significant scrolling). The three primary summary stats (rides, distance, hours) are visible above, making the chart cards redundant for the primary task.
**Evidence:** `reports.html` lines 317–354: `.bar-chart` height is defined as `64px`. Three bar charts render at this height. The API provides full distribution arrays (e.g., `elevation_distribution` has 44 buckets, `by_month` has 24 months) that cannot be meaningfully compared at 64 px.
**Recommendation:** Collapse all three distribution charts (Monthly Distance, Speed Distribution, Elevation per Ride) into a single tabbed card (using Bootstrap nav-tabs) with the chart height increased to 120 px. This reduces the left column from 5 cards to 3, eliminates excessive scrolling, and gives each chart enough height to be useful.
**Principle violated:** §2 Progressive Disclosure — three separate chart cards where one tabbed card would suffice; §3 Visual Hierarchy — 64 px chart height fails minimum legibility threshold.

#### Finding ID: ID-RPT-4
**Severity:** P3
**Observation:** The "Fastest Speed" personal record shows `57 mph` from a `WeightTraining` activity ("12lb finger-hole kettlebells, 12oz arm curls"). The PR derivation does not filter by cycling activity type, so non-cycling activities that report anomalous GPS-derived speeds pollute the Records card.
**Evidence:** `/api/stats` response: `records.fastest_speed = { speed_mph: 57.0, name: "12lb finger-hole kettlebells...", date: "2022-03-27" }`. The `by_type` breakdown confirms `WeightTraining` entries with `avg_speed_mph: 57.0`. The Personal Records card (`reports.html` lines 263–302) displays this without filtering or disclaimers.
**Recommendation:** Filter PR calculations to cycling-type activities only (Ride, GravelRide, EBikeRide, VirtualRide, MountainBikeRide) on the server side, or add a `(cycling only)` label to the PR card header to set user expectations.
**Principle violated:** §3 Visual Hierarchy — misleading data displayed with the same authority as correct records, eroding trust in the information.

---

### EXPLORE (`static/explore.html`)

#### Finding ID: ID-EXP-1
**Severity:** P2
**Observation:** The three coverage stat cards (`#coverage-stats`, `explore.html` lines 85–104) show "Tiles Visited", "Coverage %", and "Total in View" at equal visual weight. The API response (`/api/exploration/tiles`) shows `coverage_pct: 0.0` (i.e., effectively 0 % of the 14,303,328 tiles in the bounds are visited). Presenting `coverage_pct: 0.0 %` as a headline metric alongside "Tiles Visited" is redundant (both confirm very low coverage) and the "Total in View" count (14,303,328) without context reads as noise.
**Evidence:** `/api/exploration/tiles` response: `coverage_pct: 0.0`, `total_in_bounds: 14303328`, `visited` object contains ~hundreds of tile keys. The bounds span from ~28°N to 64°N, ~122°W to ~3°E — an extremely large geographic area that explains the near-zero coverage percentage.
**Recommendation:** Replace the three equal-weight cards with: (1) a primary "Tiles Visited" count as the headline stat, (2) a muted sub-label showing "of [N] in region" (replacing the separate "Total in View" card), and (3) remove or move "Coverage %" to a tooltip on the count, as 0.0 % is not meaningful at this geographic scale. This reduces 3 cards to 1 with inline context.
**Principle violated:** §2 Progressive Disclosure — three cards for two data points, one of which is a derived redundancy; §3 Visual Hierarchy — near-zero percentage displayed at same weight as the meaningful tile count.

#### Finding ID: ID-EXP-2
**Severity:** P2
**Observation:** The Controls card (`explore.html` lines 113–132) and the Route Generation card (lines 134–189) are two separate cards stacked below the map, but the Controls card's only non-obvious control ("Coverage" granularity select) directly determines which grid is targeted by the route generator. The conceptual relationship is tight but the cards are visually separated, requiring users to connect them mentally.
**Evidence:** `explore.html` lines 118–119: The `#coverage-type-select` aria-label explicitly states "also controls which grid the route generator targets". Lines 134–189: the Route Generation card does not cross-reference or display the current coverage type. The two cards currently have equal `.card` styling with no visual link.
**Recommendation:** Merge the Controls card and the Route Generation card into a single card with two labelled sections separated by a `<hr>` or section divider: "Coverage Display" (granularity select + Load Coverage + Clear Cache buttons) and "Generate Route" (the existing form). This surfaces the dependency and reduces the card count from 3 below the map to 2.
**Principle violated:** §3 Visual Hierarchy — related controls separated into sibling cards, obscuring their dependency.

#### Finding ID: ID-EXP-3
**Severity:** P3
**Observation:** The `#load-coverage-btn` ("Load Coverage") is a required precondition before the map shows any data, but it is styled identically to the secondary "Clear Cache" button. New users have no visual cue that loading coverage is the required first action.
**Evidence:** `explore.html` lines 122–128: `<button class="btn btn-sm btn-primary" id="load-coverage-btn">` and `<button class="btn btn-sm btn-outline-secondary" id="clear-cache-btn">` — the primary action has the correct `btn-primary` style, but the "Generate Routes" button below also uses `btn-primary`, creating two equal-weight primary actions on the page.
**Recommendation:** Visually demote "Generate Routes" to `btn-outline-primary` until coverage has been loaded (enable it via JS once `load-coverage-btn` has been clicked). This creates a clear sequential affordance.
**Principle violated:** §3 Visual Hierarchy — two equal-weight primary actions with a required sequence order present an ambiguous starting point.

---

### WEATHER (`static/weather.html`)

#### Finding ID: ID-WX-1
**Severity:** P2
**Observation:** The 7-day forecast card (`weather.html` lines 172–194) is the first and dominant content block, but the page's most actionable output — "Today's Commute Windows" — comes second. For a user checking the Weather page before a morning commute, the highest-value information (should I ride now? what time is optimal?) is below the fold behind the 7-day grid.
**Evidence:** `weather.html` lines 172–194: `card mb-3` for "7-Day Forecast" (grid of 7 forecast cards at ~144 px skeleton height each). Lines 197–230: `card mb-3` for "Today's Commute Windows". The `/api/weather/commute-windows` response provides `morning.optimal_departure: "07:00"` and `morning.max_precip_prob: 7` — directly actionable data. The `/api/weather/forecast` shows `today comfort_score: 60` and `precip_prob: 83` — which means the transit alert should be the first thing visible, yet the 7-day forecast precedes it.
**Recommendation:** Reorder sections: (1) transit alert (already conditional on today's conditions — correct), (2) Today's Commute Windows, (3) 7-Day Forecast. This puts the most time-sensitive, actionable data first and the planning-horizon data second.
**Principle violated:** §2 Progressive Disclosure — 7-day planning data (lower urgency) precedes same-day actionable data (higher urgency).

#### Finding ID: ID-WX-2
**Severity:** P3
**Observation:** The commute window cards (`#morning-window`, `#evening-window`) display hard-coded time labels in the HTML ("Morning (7–9 AM)" and "Evening (3–6 PM)") but the API `/api/weather/hourly` response contains a `commute_hours` object (`morning: [7, 8]`, `evening: [16, 17, 18]`) that should drive these labels dynamically. The evening label shows "3–6 PM" but the API window starts at 15:00 (3 PM) / 16:00 (4 PM) — a one-hour discrepancy depending on the user's configured commute hours.
**Evidence:** `weather.html` line 207: `<strong>Morning (7–9 AM)</strong>` (hard-coded). Line 219: `<strong>Evening (3–6 PM)</strong>` (hard-coded). `/api/weather/hourly` response: `commute_hours.evening: [16, 17, 18]` → 4 PM–6 PM, not 3–6 PM as shown. `/api/weather/commute-windows` confirms `evening.hours[0].hour: "15:00"` is included (3 PM), suggesting the window does start at 3 PM in the commute-windows data even though hourly marks it as 16+.
**Recommendation:** Drive the window time labels from the API response data rather than hard-coding them. Read `commute_hours` from `/api/weather/hourly` and format the morning/evening labels as `Morning (${first}–${last+1} AM)` dynamically, so they match user configuration and API data.
**Principle violated:** §3 Visual Hierarchy — hard-coded labels that can mismatch the underlying data erode information accuracy; secondary concern per §2 is that the mismatch is invisible to users.

#### Finding ID: ID-WX-3
**Severity:** P3
**Observation:** The Weather page has no H1 page heading visible above the 7-day forecast card. The `<h2>` at line 154 (`Weather Forecast`) is the first heading — skipping H1 entirely — which violates the §3 visual hierarchy scale (`H1: 2.5rem`).
**Evidence:** `weather.html` line 154: `<h2 class="mb-0">…Weather Forecast</h2>`. There is no `<h1>` on this page. Compare with Settings (`settings.html` line 56: `<h1 class="mb-0 fs-4">`).
**Recommendation:** Change line 154's `<h2>` to an `<h1>` and apply `fs-4` to keep the visual size consistent. This fixes both the DOM heading order and the visual hierarchy alignment.
**Principle violated:** §3 Visual Hierarchy — H2 used as page title, skipping H1 level entirely.

---

### SETTINGS (`static/settings.html`)

#### Finding ID: ID-SET-1
**Severity:** P2
**Observation:** The "Connections" card (`settings.html` lines 190–451) is a single monolithic card containing four distinct integrations: Strava (with full sync/analysis workflow), intervals.icu, Garmin Connect, and TrainerRoad. This creates a card with ~260 lines of HTML that requires extensive scrolling and conflates connection status, credential forms, operational actions (Fetch, Run Analysis), and progress indicators.
**Evidence:** `settings.html` lines 192–451: all four integrations plus Strava Sync and Run Analysis subsections are inside one `<div class="card">`. The card body contains at least 5 `<hr>` separators, 4 connection-status `<div>`s, 2 progress panels, and credential inputs for 3 services. The Strava section alone (lines 200–291) includes connection status, cache info, fetch controls, progress bar, and analysis trigger.
**Recommendation:** Split into individual cards per integration: "Strava" (connection + sync + analysis), "intervals.icu", "Garmin Connect", "TrainerRoad". Each card should be collapsible, defaulting to collapsed for disconnected integrations. This brings each connection into a focused, bounded unit and eliminates the need for 5 `<hr>` separators.
**Principle violated:** §2 Progressive Disclosure — 4 unrelated integrations in one card with all states always visible; §3 Visual Hierarchy — card boundary no longer groups a coherent information unit.

#### Finding ID: ID-SET-2
**Severity:** P2
**Observation:** The "Outdoor Workout Preferences" card (`settings.html` lines 455–505) is only meaningful when TrainerRoad is connected (per its own description text: "When a TrainerRoad workout is scheduled…"), yet it appears as a full-width standalone card between Connections and About, always visible regardless of TrainerRoad connection state. Users without TrainerRoad configured see a preferences card with no applicable context.
**Evidence:** `settings.html` lines 454–505: `Outdoor Workout Preferences` card with `col-12` full-width. Line 464: `<p class="small text-muted mb-3">When a TrainerRoad workout is scheduled…`. The `/api/settings` response shows `outdoor_min_temp_f: 40`, `outdoor_allow_rain: false` are stored — the API persists these even when TrainerRoad is not configured.
**Recommendation:** Nest the Outdoor Workout Preferences section inside the TrainerRoad connection card (once that card is separated per ID-SET-1). Show it only when TrainerRoad is connected, or at minimum label it with "Requires TrainerRoad connection" when TrainerRoad is not connected.
**Principle violated:** §2 Progressive Disclosure — configuration options for a conditional feature shown unconditionally, creating irrelevant content for most users.

#### Finding ID: ID-SET-3
**Severity:** P3
**Observation:** The "About" card (`settings.html` lines 508–540) contains a `<p class="lead">` description, a `<dl>` with version/data-source info, and two external links. It is a full-width card with `bg-primary text-white` header identical to the functional cards above it, giving "About" the same visual prominence as action-bearing settings. The About section also shows version `0.14.0` while the project is at v0.17.0.
**Evidence:** `settings.html` lines 509–540: About card uses `card-header bg-primary text-white` (same as User Preferences, Data Management, Connections, Outdoor Preferences cards). Line 521: `<dd class="col-md-9">0.14.0</dd>` — stale version number.
**Recommendation:** Style the About card with a `bg-light` or `bg-transparent border-0` header to visually differentiate informational content from actionable settings sections. Update the version string to `0.17.0`.
**Principle violated:** §3 Visual Hierarchy — informational/about content styled identically to action-bearing settings cards; stale version data degrades information accuracy.

#### Finding ID: ID-SET-4
**Severity:** P3
**Observation:** The "Display Options" group inside User Preferences (`settings.html` lines 107–126) contains three checkboxes: "Show detailed weather information", "Show elevation data", and "Auto-save preferences". "Auto-save preferences" is an application behaviour control, not a display toggle — it governs how the form saves, not what information is shown. Mixing it with display-visibility toggles creates a false grouping.
**Evidence:** `settings.html` lines 107–126: all three checkboxes share the same `<label class="form-label fw-bold d-block mb-2">Display Options</label>`. The `auto_save` setting in the `/api/settings` response (`auto_save: true`) controls whether settings are persisted automatically — clearly a save-behaviour concern, not a display option.
**Recommendation:** Move "Auto-save preferences" to a separate "Save Behavior" line below the Display Options group, or place it adjacent to the "Save Settings" / "Reset to Defaults" buttons at the bottom of the form where it is contextually obvious.
**Principle violated:** §3 Visual Hierarchy — unrelated control grouped under an incorrect label, degrading the clarity of the information grouping.

---

## Cross-Page Patterns

### CP-1: Stale Version Number Across All Pages
Every page footer reads `Ride Optimizer v0.14.0 - Smart Static Architecture`. The app is at v0.17.0. All 7 files share this stale string. While minor individually, it degrades the credibility of information displayed on every page and contradicts the "What's New" toast in `index.html` which references v0.14.0.
**Affected files:** `static/index.html` (line 478), `static/routes.html` (line 310), `static/route-detail.html` (line 101), `static/reports.html` (line 440), `static/weather.html` (line 235), `static/explore.html` (line 196), `static/settings.html` (line 582, and About card line 521).

### CP-2: Inconsistent `show_secondary_metrics` Setting Enforcement
The `/api/settings` response includes `show_secondary_metrics: true` as a persisted preference, but no page visibly respects this toggle. The Reports extra-stats row, the Route Detail "Uses" metric, and the Weather hourly strip all remain visible regardless of this setting. The setting exists in the API but has no effect on the UI.
**Affected pages:** Dashboard, Route Detail, Reports, Weather.

### CP-3: No Page-Level H1 Headings on 3 of 7 Pages
Weather (`weather.html` line 154) uses `<h2>` as the first heading. Route Detail (`route-detail.html` line 461) uses `<h1>` correctly only after JS renders. Explore (`explore.html`) has no visible page heading at all — the first heading is the `<h6>` "Generate Exploration Route" label inside a card. This is inconsistent with the §3 hierarchy and with pages that do use H1 (Settings, Reports).

### CP-4: Primary/Secondary Metric Boundary Inconsistently Applied
Across multiple pages, metrics that §2 designates as secondary (social signals, operational metadata, administrative counts) are displayed at the same visual weight as primary metrics (distance, duration, score). This pattern appears in: Dashboard (route-group count in Route Status), Reports (Kudos and KJ as headline stats), Route Detail (Uses in primary grid), and Explore (Coverage % near zero presented as a headline card).

---

## Prioritized Recommendation List

| Priority | Finding ID | Severity | Page | Short Description |
|----------|------------|----------|------|-------------------|
| 1 | ID-RDTL-1 | P1-high | Route Detail | Raw JSON `<pre>` dump in primary metrics card |
| 2 | ID-DASH-1 | P2 | Dashboard | Hourly strip pushes hero commute card below fold |
| 3 | ID-DASH-2 | P2 | Dashboard | Route Status panel mixed into map column |
| 4 | ID-RPT-2 | P2 | Reports | Admin sync buttons inside analytics Gear card |
| 5 | ID-RPT-3 | P2 | Reports | Five stacked cards with 64 px charts in left column |
| 6 | ID-WX-1 | P2 | Weather | 7-day forecast precedes same-day commute windows |
| 7 | ID-ROUTES-1 | P2 | Routes Library | 9 filter controls unconditionally visible, no collapse |
| 8 | ID-SET-1 | P2 | Settings | Monolithic Connections card with 4 integrations |
| 9 | ID-SET-2 | P2 | Settings | Outdoor Workout Preferences shown without TrainerRoad |
| 10 | ID-RPT-1 | P2 | Reports | Empty/null secondary stats at primary visual weight |
| 11 | ID-RDTL-2 | P2 | Route Detail | "Uses" in primary metrics grid at same weight as distance/duration/elevation |
| 12 | ID-RDTL-3 | P2 | Route Detail | Performance charts hidden despite 89-ride history available |
| 13 | ID-EXP-1 | P2 | Explore | 0.0 % coverage displayed as headline stat |
| 14 | ID-EXP-2 | P2 | Explore | Controls and Route Generation in separate cards despite tight dependency |
| 15 | ID-ROUTES-2 | P3 | Routes Library | Results count rendered as Bootstrap alert |
| 16 | ID-ROUTES-3 | P3 | Routes Library | Saved Plans section hidden with no affordance |
| 17 | ID-RPT-4 | P3 | Reports | Fastest Speed PR from WeightTraining activity |
| 18 | ID-WX-2 | P3 | Weather | Hard-coded commute window time labels mismatch API data |
| 19 | ID-WX-3 | P3 | Weather | Page uses H2 as page title, no H1 |
| 20 | ID-EXP-3 | P3 | Explore | Two equal-weight primary buttons with required sequence |
| 21 | ID-SET-3 | P3 | Settings | About card styled identically to action cards; stale version |
| 22 | ID-SET-4 | P3 | Settings | "Auto-save" mixed into Display Options group |
| 23 | ID-DASH-3 | P3 | Dashboard | Commute detail collapse has no teaser content |
| 24 | CP-1 | P3 | All pages | Stale v0.14.0 version string in all footers |
| 25 | CP-2 | P2 | 4 pages | `show_secondary_metrics` setting has no UI effect |
| 26 | CP-3 | P2 | 3 pages | Missing H1 page headings on Weather, Explore, Route Detail |
| 27 | CP-4 | P2 | 4 pages | Secondary metrics at same visual weight as primary metrics |
