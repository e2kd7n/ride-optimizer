# Discoverability & Ease-of-Use — Design Review Findings
**Reviewer:** Subagent B (Discoverability)
**Date:** 2026-07-04
**Issue:** #354
**Pages reviewed:** 7

---

## Summary

The app is well-structured overall: every page has a working top navbar and skip-link, filter controls are labeled, and skeleton loaders prevent jarring blank states. The primary discoverability gaps are concentrated on the **Explore** page (no onboarding for the tile-coverage concept, distance slider defaults to km regardless of unit setting until JS runs), the **Routes Library** (compare checkbox has only a `title` tooltip — no visible label — making the feature invisible on mobile), and **Settings** (Strava sync vs. Run Analysis are separated only by a thin `<hr>`, not a visual group header, causing new users to conflate the two operations). The bottom navigation bar is missing **Reports** and **Explore** on all pages, effectively hiding those sections from mobile users.

---

## Findings

---

### DASHBOARD

#### Finding ID: DISC-DASH-1
**Severity:** P2
**Observation:** The "Your Commute" hero card contains a hidden collapse panel (`#commute-detail`) that reveals both commute directions and full score breakdowns. The only trigger is a small text link/chevron rendered dynamically by `dashboard.js` (line 710). On first visit a new user sees a single-direction score card and has no visual hint that the second direction and detailed breakdown are hidden behind it.
**Evidence:** `static/index.html` lines 417–419: `<div class="collapse" id="commute-detail">` — no visible expand button in the HTML shell. The trigger is injected by `static/js/dashboard.js` line 710 using `data-bs-toggle="collapse"`. The "How It Works" modal exists (lines 327–352) but doesn't mention commute directions.
**Recommendation:** Render the expand/collapse trigger in the static HTML shell so it is immediately visible even before JS runs. Add a short hint label — e.g., "See both directions ↓" — adjacent to the score, rather than relying solely on a chevron icon.
**Principle violated:** §7 Discoverable Features — no visual hint for hidden content

---

#### Finding ID: DISC-DASH-2
**Severity:** P2
**Observation:** The Route Status panel (`#route-status-panel`) on mobile collapses to a 1-line summary with an expand chevron (`conditions-summary-toggle`, `dashboard.js` line 846). There is no label or badge on the collapsed state indicating how many routes are in the panel or what information is hidden, so users may not know to tap it.
**Evidence:** `static/js/dashboard.js` lines 846–871: the toggle element uses only `aria-expanded="false"` and a `.conditions-chevron` for affordance; no text label accompanies the chevron in the collapsed state.
**Recommendation:** Add a short static label beside the chevron in the collapsed state, e.g., "Show all route conditions (3)" using the route count returned by `/api/routes/status`.
**Principle violated:** §7 Discoverable Features — hidden interactive element lacks label/count badge

---

#### Finding ID: DISC-DASH-3
**Severity:** P3
**Observation:** The "What's New" first-visit toast (`index.html` lines 505–533) is keyed to `rideOptimizer_whatsNew_v0.14.0`, but the footer and `/api/status` both report the current version as `v0.14.0` while the product version is `v0.17.0`. New users will see a stale changelog toast listing features from three releases ago (hourly forecast, saved plans, etc.).
**Evidence:** `index.html` line 507: `var WHATS_NEW_KEY = 'rideOptimizer_whatsNew_v0.14.0'`; `index.html` line 476: `<small>Ride Optimizer v0.14.0`; `/api/status` response: `"last_analysis": "2026-07-04T19:17:27"`; the product is shipping as `v0.17.0` per this epic.
**Recommendation:** Bump the `WHATS_NEW_KEY` version constant and the footer version string to `v0.17.0` before release. Update the toast content to reflect v0.17.0 changes.
**Principle violated:** §7 Discoverable Features — onboarding toast content is stale

---

#### Finding ID: DISC-DASH-4
**Severity:** P3
**Observation:** The dashboard has no failure/empty state for when the commute service is unavailable. If `/api/recommendation` returns an error or the `commute` service is `"unavailable"` per `/api/status`, `dashboard.js` logs to `console.error` (line 789) but there is no visible user-facing fallback message inside `#commute-recommendation`.
**Evidence:** `static/js/dashboard.js` line 789: `console.error('Failed to load commute recommendations:', error)` — no `renderEmptyState` call in the catch path for the commute section. `/api/status` confirms `"commute": "available"` today, but no error UI path exists.
**Recommendation:** In the `catch` block for commute loading, render an informative empty state inside `#commute-recommendation`, e.g., "Commute data unavailable — check your Strava connection in Settings."
**Principle violated:** §7 Discoverable Features — empty/error state is non-existent (silent failure)

---

### ROUTES LIBRARY

#### Finding ID: DISC-ROUTES-1
**Severity:** P2
**Observation:** Each route card has a small unlabeled checkbox (`.compare-checkbox`) to add routes to comparison. On desktop the checkbox has only `title="Compare"` (tooltip on hover). On mobile/touch there is no visible label at all — tooltips do not fire on tap. A new user has no way to discover the compare feature except by accidentally tapping the checkbox.
**Evidence:** `static/js/routes.js` lines 677–680: `<input class="form-check-input compare-checkbox …" title="Compare">` — no adjacent visible `<label>`. The floating "Compare N Routes" button only appears after at least one checkbox is ticked (`routes.js` lines 779–801), so it gives no pre-discovery affordance.
**Recommendation:** Add a small visible "Compare" text label next to the checkbox — e.g., `<label class="form-check-label small text-muted">Compare</label>` — or add a permanent "Compare routes" hint line beneath the filter bar explaining the checkbox affordance.
**Principle violated:** §7 Discoverable Features — feature hidden with no visual hint on touch

---

#### Finding ID: DISC-ROUTES-2
**Severity:** P2
**Observation:** The "Saved Plans" section (`#saved-plans-section`) starts hidden (`style="display: none"`) and is only revealed by JavaScript when saved plans exist. The toggle button (`#toggle-plans-btn`) only appears alongside the section. There is no permanent entry-point or notification badge on the page indicating that saved plans exist, so users who saved a plan via Route Detail will not know to look for it here.
**Evidence:** `static/routes.html` lines 163–176: `<div id="saved-plans-section" class="mb-3" style="display: none;">` — display is set by `routes.js` at line 1115 only when plans are found. The section header has no badge count or link pointing to it from any other page.
**Recommendation:** When plans exist, add a badge count on the bottom nav "Routes" item, or display a persistent collapsed accordion stub (even when empty) that shows "0 saved plans" with an action link to route detail pages.
**Principle violated:** §7 Discoverable Features — hidden section with no entry-point badge/hint

---

#### Finding ID: DISC-ROUTES-3
**Severity:** P3
**Observation:** The map panel's "Color: Recency" and "Color: Distance" options in the `#color-by` select reveal a color legend (`#map-legend`) at the bottom of the map card, but the legend is hidden by default (`style="display: none"`) and only appears after a route is displayed. The `#map-status` text reads "Click a route to display it on the map" but says nothing about the color-coding feature.
**Evidence:** `static/routes.html` lines 237–241: `<select id="color-by" …>` plus lines 260–261: `<div id="map-legend" … style="display: none;">`. `routes.js` lines 63–85: `renderLegend()` only calls `legendEl.style.display = ''` when routes are visible.
**Recommendation:** When a `color-by` option other than "Default" is selected, show the legend immediately (even before routes are plotted) so users know what the colors mean before clicking through routes.
**Principle violated:** §7 Discoverable Features — contextual information withheld until after interaction

---

#### Finding ID: DISC-ROUTES-4
**Severity:** P3
**Observation:** The help modal (injected by `help-modal.js`) is loaded on this page and injects a "Help" button into the navbar. However, the tutorial GIF assets referenced (e.g., `/img/tutorials/route-comparison.gif`) are placeholders — the `help-modal.js` comment (line 8) states "GIF assets live in /img/tutorials/. Place files there when available." If these assets are missing at launch, users clicking "Help" will see broken image placeholders.
**Evidence:** `static/js/help-modal.js` lines 21–22: `gif: '/img/tutorials/route-comparison.gif'`; the comment at lines 8–10 explicitly confirms assets are not yet placed. No `<img onerror>` fallback is defined.
**Recommendation:** Either ship the GIF assets before launch, or add an `onerror` fallback on each tutorial image that shows the text description in place of the broken image, and conditionally hide the "Help" navbar button if no assets are present.
**Principle violated:** §7 Discoverable Features — onboarding/tutorial assets are missing

---

### ROUTE DETAIL

#### Finding ID: DISC-DETAIL-1
**Severity:** P2
**Observation:** When a route has weather data attached, it is rendered inside a `<pre>` tag as raw JSON (`JSON.stringify(route.weather, null, 2)`). A new user seeing a code dump has no idea what the numbers mean and cannot derive a cycling recommendation from it.
**Evidence:** `static/route-detail.html` lines 428–437 and line 528: `<pre class="mb-0 small">${JSON.stringify(route.weather, null, 2)}</pre>` — no human-readable formatting, labels, or icons.
**Recommendation:** Replace the raw `<pre>` dump with a small formatted weather summary using the same icon+metric chips pattern used on the Dashboard weather banner: temperature, wind speed, precipitation probability, comfort score.
**Principle violated:** §7 Discoverable Features — data presented in developer format, not user format

---

#### Finding ID: DISC-DETAIL-2
**Severity:** P2
**Observation:** The "Ride Again" / save-plan button (`#save-plan-btn`) has only a `title="Save this route as a plan to ride again"` tooltip. Users who save a plan have no visible confirmation of where to find it afterward — the success state changes the button to "✓ Saved" but provides no navigation hint to the Routes page where saved plans appear.
**Evidence:** `static/route-detail.html` lines 474–478: save button with `title` attribute. `route-detail.html` lines 603–607: on success, button changes text to "Saved" but there is no link or toast pointing to `/routes.html#saved-plans`.
**Recommendation:** After a successful save, show a toast notification: "Plan saved! View in Routes →" linking to `/routes.html`.
**Principle violated:** §7 Discoverable Features — success action has no follow-through navigation hint

---

#### Finding ID: DISC-DETAIL-3
**Severity:** P3
**Observation:** The `<skip-link>` for Route Detail is placed *after* the `<nav>` element (line 57), which means keyboard users must tab through the entire navbar before reaching the skip link. Skip links must be the very first focusable element in `<body>`.
**Evidence:** `static/route-detail.html` lines 35–58: `<nav>` is at line 35; `<a href="#main-content" class="skip-link">` is at line 57 — placed inside `<main>`, after the nav.
**Recommendation:** Move the skip link to be the very first element inside `<body>`, before the `<nav>`, consistent with how `index.html`, `routes.html`, and `settings.html` handle it (all place the skip-link before the navbar).
**Principle violated:** §10 Consistent Patterns — skip-link placement inconsistent with all other pages

---

#### Finding ID: DISC-DETAIL-4
**Severity:** P3
**Observation:** The Performance Trends chart card (`#performance-metrics-card`) is hidden by default (`style="display: none"`) and only revealed if there are 2+ route history entries. When it does appear, there is no section heading or context explaining what "Performance Trends" means or which time range is charted. The section simply appears between other content with no transition.
**Evidence:** `static/route-detail.html` lines 546–570: `<div class="card mt-3" id="performance-metrics-card" style="display: none;">` — conditionally shown by `renderPerformanceCharts()`. No date-range label or explanatory sub-heading is present.
**Recommendation:** Add a sub-heading or date-range label under "Performance Trends" (e.g., "Based on your last 20 activities on this route") and show an informative placeholder when fewer than 2 data points exist rather than hiding the card entirely.
**Principle violated:** §7 Discoverable Features — feature invisible until data threshold is met, no breadcrumb

---

### REPORTS

#### Finding ID: DISC-REPORTS-1
**Severity:** P2
**Observation:** The bar charts ("Monthly Distance", "Speed Distribution", "Elevation per Ride") are interactive — individual bars are clickable (`cursor: pointer`, `reports.css` line 113) — but there is no tooltip, legend, or label indicating that bars are clickable. The `role="img"` ARIA attribute on the chart containers (`reports.html` lines 323, 336, 349) reinforces the impression that these are static images, not interactive controls.
**Evidence:** `static/reports.html` lines 323–326: `<div class="bar-chart" id="monthly-chart" role="img" aria-label="Monthly distance bar chart">` — `role="img"` signals non-interactive to both screen readers and sighted users. `static/reports.html` CSS line 113: `.bar-chart .bar { cursor: pointer; }`.
**Recommendation:** Change `role="img"` to `role="group"` or `role="list"` on the bar chart containers. Add a `title` or `data-bs-toggle="tooltip"` to each bar element showing its value. Consider adding a subtle "Click bar to filter" hint below the Monthly Distance chart.
**Principle violated:** §7 Discoverable Features — interactive elements not visually distinct; §10 Consistent Patterns — ARIA role mismatches interaction model

---

#### Finding ID: DISC-REPORTS-2
**Severity:** P2
**Observation:** The "Gear" section contains three admin-grade buttons — "Sync Gear", "Backfill Gear IDs", and "Clear Filter" — styled identically as small `btn-outline-secondary`. A new user cannot distinguish between "Sync Gear" (fetches fresh data from Strava) and "Backfill Gear IDs" (patches cached local data). "Backfill Gear IDs" in particular is a developer-facing label that means nothing to end users.
**Evidence:** `static/reports.html` lines 368–379: three buttons with identical styling, no help text, no separation between user-facing and admin-facing actions.
**Recommendation:** Rename "Backfill Gear IDs" to a user-facing label such as "Repair Gear Names". Add a `title` tooltip or help icon `<i class="bi bi-question-circle">` on each button explaining what it does. Consider moving the repair action to a Settings > Data Management context instead.
**Principle violated:** §7 Discoverable Features — developer labels exposed to end users; §10 Consistent Patterns

---

#### Finding ID: DISC-REPORTS-3
**Severity:** P2
**Observation:** The Reports page is absent from the **bottom navigation bar** on all pages. Mobile users on Home, Routes, Weather, or Settings have no one-tap path to Reports. They must either use the hamburger menu (collapsed on mobile) or know the URL.
**Evidence:** `static/index.html` lines 454–471, `static/routes.html` lines 268–285, `static/weather.html` lines 239–256, `static/settings.html` lines 559–576 — none of the bottom navs include a Reports item. The desktop navbar includes Reports on all pages.
**Recommendation:** Replace the least-used bottom nav slot — "Settings" is available from the hamburger menu and is rarely needed during a ride — with "Reports", or expand the bottom nav to 5 items. Alternatively, add a "More" overflow item.
**Principle violated:** §4 Navigation — high-value page unreachable from mobile primary navigation

---

#### Finding ID: DISC-REPORTS-4
**Severity:** P3
**Observation:** The `stat-label` for total distance reads "Miles" hardcoded in the HTML (`reports.html` line 217), ignoring the unit system setting. The API returns `total_distance_mi` in imperial, and the JS renders it directly. A metric user will see miles labeled as "Miles" even after changing their unit preference to metric.
**Evidence:** `static/reports.html` line 217: `<div class="stat-label">Miles</div>` — static string, not dynamically set. `GET /api/settings` confirms `"unit_system": "imperial"` is configurable, but the reports page does not read this setting for its column header.
**Recommendation:** Set the "Miles"/"km" label dynamically in `reports.js` using `window.getDistanceUnit()` on page load, consistent with how `routes.html` lines 325–327 dynamically update the distance filter labels.
**Principle violated:** §10 Consistent Patterns — unit labels inconsistent across pages

---

### EXPLORE

#### Finding ID: DISC-EXPLORE-1
**Severity:** P1
**Observation:** The Explore page shows a map with colored tiles and three stat cards (Tiles Visited, Coverage, Total in View) but provides no explanation of what "Tiles Visited", "Squadrats", or "Squadratinhos" mean. The page label says only "Tile coverage map". A first-time user cannot understand the primary purpose of the page or how coverage percentages relate to cycling goals without external knowledge.
**Evidence:** `static/explore.html` lines 85–103: stat cards with labels "Tiles Visited", "Coverage", "Total in View" — no explainer text. Lines 117–119: `<select id="coverage-type-select" …>` with options "Squadrats" and "Squadratinhos" — cycling sub-culture jargon with no tooltip or definition. The `aria-label` on the select (line 118) mentions "also controls which grid the route generator targets" but this is only for screen readers.
**Recommendation:** Add a one-line explainer above the stat cards: "Tiles are map grid squares. Covering more tiles means you've explored more unique roads. Squadrats = zoom-14 tiles (~1.2km²); Squadratinhos = zoom-17 tiles (~0.15km²)." Add a `<i class="bi bi-question-circle">` help icon next to the Coverage select that triggers a tooltip or small popover with this definition.
**Principle violated:** §7 Discoverable Features — jargon with no contextual help; first-time user cannot complete primary task without external research

---

#### Finding ID: DISC-EXPLORE-2
**Severity:** P1
**Observation:** The route generation workflow requires the user to (1) click "Load Coverage", (2) click the map to set a start point or use location search, and (3) click "Generate Routes" — but none of these steps are numbered, sequenced visually, or explained. When the page first loads, "Generate Routes" is enabled and will silently fail or produce nonsensical results if coverage has not been loaded and a start point has not been set.
**Evidence:** `static/explore.html` lines 123–188: the three controls ("Load Coverage" button, "Start" location input, "Generate Routes" button) are laid out as a flat grid with no step numbering or dependency indication. `static/js/explore.js` line 122: `document.getElementById('generate-route-btn').disabled = true` — the button IS disabled while coverage is loading, but there is no pre-load state explaining why or what the user needs to do first.
**Recommendation:** Add a numbered 3-step workflow header: "Step 1 — Load your coverage · Step 2 — Set a start point · Step 3 — Generate." Disable "Generate Routes" until both coverage is loaded AND a start point is set, and display the blocking reason in `#worker-status` (e.g., "Set a start point to generate a route").
**Principle violated:** §7 Discoverable Features — multi-step workflow with no sequencing or dependency hints; P1 because primary task is not completable by a new user without guessing

---

#### Finding ID: DISC-EXPLORE-3
**Severity:** P2
**Observation:** The distance slider label reads "Distance (km)" on initial HTML render (`explore.html` line 142: `<span id="distance-unit-label">km</span>`), then updates to the user's unit preference when `explore.js` runs. If JS is slow or fails, the unit label is wrong for imperial users. More importantly, the slider value is stored in kilometers internally but presented in the user's unit — this is not documented anywhere on the page.
**Evidence:** `static/explore.html` line 147: `<span class="small fw-bold" id="distance-value">40 km</span>` — default "40 km" is shown in HTML before JS runs. `static/js/explore.js` lines 49–56: unit conversion only happens after DOM ready.
**Recommendation:** Set the default HTML value to match the most common unit (imperial) or use a server-side rendering approach. At minimum, wrap the static "km" default in a `data-default-unit` attribute and ensure the JS corrects it before first user interaction. Document the conversion in a comment.
**Principle violated:** §7 Discoverable Features — unit label default is wrong for majority of users until JS executes

---

#### Finding ID: DISC-EXPLORE-4
**Severity:** P2
**Observation:** The Explore page has no bottom navigation entry on **any** page's bottom nav except its own. Mobile users cannot navigate from Explore to Reports or from Reports to Explore using the bottom nav — they must use the collapsed hamburger menu.
**Evidence:** All bottom nav implementations (confirmed in `index.html`, `routes.html`, `weather.html`, `settings.html`, `reports.html`) — none include an Explore entry. `explore.html` bottom nav (lines 205–222) has Home, Routes, Explore (active), Settings — Reports is missing.
**Recommendation:** See DISC-REPORTS-3. Redesign the bottom nav to include both Reports and Explore, either by expanding to 5 items or replacing a lower-priority item.
**Principle violated:** §4 Navigation — feature page unreachable from mobile bottom nav on most pages (duplicates DISC-REPORTS-3 from Explore's perspective)

---

#### Finding ID: DISC-EXPLORE-5
**Severity:** P3
**Observation:** The "Clear Cache" button (`#clear-cache-btn`) in the controls row is styled identically to "Load Coverage" (`btn-outline-secondary`) with no warning color or confirmation dialog. A user who accidentally clicks it will lose their cached tile data with no undo.
**Evidence:** `static/explore.html` lines 126–128: `<button class="btn btn-sm btn-outline-secondary" id="clear-cache-btn"><i class="bi bi-trash"></i> Clear Cache</button>` — same visual weight as Load Coverage.
**Recommendation:** Style the Clear Cache button as `btn-outline-danger` and add a `confirm()` dialog or a Bootstrap confirmation popover before executing the cache clear. This is consistent with the Danger Zone pattern used in Settings.
**Principle violated:** §10 Consistent Patterns — destructive action lacks warning styling consistent with Danger Zone pattern in Settings

---

### WEATHER

#### Finding ID: DISC-WEATHER-1
**Severity:** P2
**Observation:** The 7-day forecast cards show a "comfort pill" (`favorable` / `neutral` / `unfavorable`) but do not explain what the comfort score measures or what the threshold is for each label. A user trying to decide whether to ride on Thursday vs. Friday sees "100" vs. "80" comfort scores with no legend. The API returns `cycling_favorability` and `comfort_score` but their meaning is not surfaced in the UI.
**Evidence:** `static/weather.html` lines 27–79: `.comfort-pill` CSS with three states. `/api/weather/forecast` response: `"comfort_score": 100, "cycling_favorability": "favorable"` — no on-page legend explaining the 0–100 scale or what drives it (precipitation, wind, temperature).
**Recommendation:** Add a small legend or info tooltip on the "7-Day Forecast" card header explaining: "Comfort score (0–100) combines temperature, precipitation risk, and wind. ≥80 = favorable, 60–79 = neutral, <60 = unfavorable." A `<i class="bi bi-question-circle">` icon next to the card title suffices.
**Principle violated:** §7 Discoverable Features — key metric has no definition or legend

---

#### Finding ID: DISC-WEATHER-2
**Severity:** P2
**Observation:** The commute window cards ("Morning 7–9 AM", "Evening 3–6 PM") are hardcoded time ranges in the HTML. The API response from `/api/weather/commute-windows` returns `optimal_departure` times (e.g., `"07:00"` morning, `"15:00"` evening). If the user commutes at different times, the hardcoded labels are misleading. Additionally, the evening window shows hours starting at 3 PM (15:00) but the label says "3–6 PM" — the API response confirms `hours` only goes to 17:00 (5 PM), not 6 PM.
**Evidence:** `static/weather.html` lines 206–207: `<strong>Morning (7–9 AM)</strong>` and lines 216–217: `<strong>Evening (3–6 PM)</strong>` — static labels. `/api/weather/commute-windows` response: `evening.hours` ends at `"17:00"`, not `"18:00"`.
**Recommendation:** Derive the displayed time range dynamically from the API `hours` array (`first_hour` to `last_hour`), or add a note that users can configure their commute window hours in Settings. Fix the "3–6 PM" label to "3–5 PM" to match the actual API data.
**Principle violated:** §7 Discoverable Features — static label misrepresents actual data range; §10 Consistent Patterns — time ranges not user-configurable despite Settings page existing

---

#### Finding ID: DISC-WEATHER-3
**Severity:** P3
**Observation:** The Weather page is absent from the **Reports** and **Explore** page bottom navigation bars (those pages have Home, Routes, Weather, Settings — Weather IS present). However, from the Reports page bottom nav, Weather is correctly present. This is consistent. No additional finding beyond cross-page nav gaps captured in DISC-REPORTS-3 / DISC-EXPLORE-4.
*(Non-finding — resolved, no action needed.)*

---

#### Finding ID: DISC-WEATHER-4
**Severity:** P3
**Observation:** The transit alert (`#transit-alert`) links to `https://www.google.com/maps` — a generic URL, not a Google Maps transit directions link pre-populated with the user's commute origin/destination. The API has coordinate data for the user's commute routes (confirmed via `/api/routes?type=commute`), so a more helpful link is achievable.
**Evidence:** `static/weather.html` line 164: `<a id="transit-link" href="https://www.google.com/maps" …>Open transit planner</a>` — static URL with no coordinates.
**Recommendation:** Construct the Google Maps transit URL dynamically using the user's work/home coordinates from the commute route data: `https://www.google.com/maps/dir/?api=1&travelmode=transit&origin=LAT,LNG&destination=LAT,LNG`.
**Principle violated:** §7 Discoverable Features — action link is generic, not contextually useful

---

### SETTINGS

#### Finding ID: DISC-SETTINGS-1
**Severity:** P2
**Observation:** "Fetch Activities" (syncs from Strava) and "Run Analysis" (re-processes cached data) are visually separated only by an `<hr>` and their individual section labels. A new user reads "Sync from Strava" followed immediately by "Run Analysis" and has no clear mental model of the two-stage pipeline: first fetch, then analyze. The buttons are different colors (blue vs. green) which helps, but there is no explicit "you need to do these in order" guidance.
**Evidence:** `static/settings.html` lines 216–292: "Sync from Strava" section with Fetch button, then `<hr class="my-3">` at line 260, then "Run Analysis" section at lines 263–291. No numbered steps or workflow diagram exists. Button text "Fetch Activities" and "Run Analysis" do not describe the relationship.
**Recommendation:** Add a brief two-line workflow explainer before the Fetch button: "1. Fetch Activities — downloads new rides from Strava into local cache. 2. Run Analysis — groups your rides into routes. Run both in sequence after connecting Strava." Consider adding step numbers to the section labels.
**Principle violated:** §7 Discoverable Features — two-step workflow with no sequencing guide

---

#### Finding ID: DISC-SETTINGS-2
**Severity:** P2
**Observation:** The TrainerRoad Calendar section is hidden in a Bootstrap collapse (`#trainerroad-section`) and its trigger is a `div` styled with `cursor:pointer` (not a `<button>`). The collapse trigger is visually ambiguous: it looks like a static heading row with a chevron icon. Mobile users may not recognize it as interactive. The "Not connected" badge provides status but the row has no affordance indicating it will expand.
**Evidence:** `static/settings.html` lines 386–401: `<div … data-bs-toggle="collapse" … role="button">` — a non-button element acting as a button, with only a `bi-chevron-right` icon as the expand hint. `aria-expanded="false"` is present but no visible expand label.
**Recommendation:** Replace the `div[role="button"]` trigger with an actual `<button>` or `<summary>` element. Add a visible "Expand" / "▼ Configure" text label alongside the chevron so users on touch devices have a clear tap target and understand the row is collapsible.
**Principle violated:** §5 Touch-Optimized — non-button collapse trigger; §10 Consistent Patterns — collapse pattern inconsistent with Bootstrap accordion standard

---

#### Finding ID: DISC-SETTINGS-3
**Severity:** P2
**Observation:** The Outdoor Workout Preferences temperature slider (`#outdoor-min-temp`) always displays in °F regardless of the unit system setting. A metric user who sets unit system to "Metric (km, °C)" in the same form will find the temperature threshold labeled in °F.
**Evidence:** `static/settings.html` lines 475–479: `min="0" max="80" step="5" value="40"` with `id="outdoor-min-temp-value"` badge hardcoded to `40°F`. The JS `applySettingsToForm` (line 706–708) sets `label.textContent = settings.outdoor_min_temp_f + '°F'` — always °F. No unit conversion is applied.
**Recommendation:** When the unit system is "metric", convert and display the temperature in °C: `Math.round((°F - 32) * 5/9)`. Update `applySettingsToForm` and the slider `input` event handler to respect `window.getUnitSystem()`.
**Principle violated:** §10 Consistent Patterns — unit system setting not applied to temperature inputs on same page

---

#### Finding ID: DISC-SETTINGS-4
**Severity:** P3
**Observation:** The "Custom…" preset in the Strava fetch date range (`#custom-date-fields`) reveals date inputs using `style="display:none"` toggled by JS. However, the custom date inputs use Bootstrap's `style` attribute for toggling (`settings.js` line 929: `document.getElementById('custom-date-fields').style.display = …`) rather than Bootstrap's `collapse` component. This means the reveal has no animation and no `aria-expanded` state update on the parent preset button, so screen readers are not informed when the custom fields appear.
**Evidence:** `static/settings.html` lines 229–238: `<div id="custom-date-fields" class="d-flex … mt-2" style="display:none">`. No `aria-expanded` or `aria-controls` on the "Custom…" button (`data-preset="custom"`). `settings.js` line 929 uses raw `style.display`.
**Recommendation:** Add `aria-expanded="false"` and `aria-controls="custom-date-fields"` to the "Custom…" button. Toggle `aria-expanded` in the JS handler alongside the `display` toggle. Consider using Bootstrap collapse for consistent animation.
**Principle violated:** §10 Consistent Patterns — disclosure pattern inconsistent (raw display toggle vs. Bootstrap collapse used elsewhere)

---

## Cross-Page Patterns

### CP-1: Bottom Navigation Missing Reports and Explore
**Severity:** P2 (affects 5 of 7 pages)
**Pages affected:** Dashboard, Routes Library, Weather, Settings, Reports (missing Explore)
All bottom navigation bars across the app are capped at 4 items: Home, Routes, Weather, Settings. **Reports** and **Explore** — two of the six top-nav items — have no bottom nav representation. On mobile, reaching these pages requires the hamburger menu. This creates a two-tier navigation experience where 4 of 6 app sections are one tap away and 2 require a multi-step interaction.
**Evidence:** Bottom nav implementations confirmed absent: `index.html:454–471`, `routes.html:268–285`, `weather.html:239–256`, `settings.html:559–576`, `reports.html:450–467`.
**Recommendation:** Expand the bottom nav to 5 items (add Reports, dropping the least-used item) or implement a "More" overflow drawer.

### CP-2: Version String Stale Across All Pages
**Severity:** P3 (affects all 7 pages)
**Pages affected:** Dashboard, Routes Library, Route Detail, Explore, Weather, Reports, Settings
All page footers and the "What's New" toast key reference `v0.14.0` despite the product shipping as `v0.17.0` under this epic.
**Evidence:** `index.html:476`, `routes.html:309`, `settings.html:581`, `route-detail.html:99`, `explore.html:196`, `weather.html:235`, `reports.html:439` — all read `Ride Optimizer v0.14.0`.
**Recommendation:** Run a global find-and-replace for `v0.14.0` → `v0.17.0` in all static files before release.

### CP-3: Help Modal Tutorial Assets Not Shipped
**Severity:** P2 (affects 5 pages where help-modal.js is loaded)
**Pages affected:** Dashboard, Routes Library, Route Detail, Settings, Weather
`help-modal.js` is loaded on 5 pages and injects a "Help" navbar button. All 4 tutorial GIF/PNG assets are unreferenced placeholder paths. Users clicking "Help" on any of these pages will see broken images.
**Evidence:** `help-modal.js` lines 21–47: four tutorial definitions pointing to `/img/tutorials/*.gif` and `/img/tutorials/*-preview.png`. File comment line 8: "Place files there when available."
**Recommendation:** Either ship the assets, or remove the Help button injection and `<script src="/js/help-modal.js">` tags until assets are ready.

### CP-4: Interactive Bar Charts Not Discoverable as Clickable
**Severity:** P2 (Reports page; pattern risk on other future chart pages)
Custom `div`-based bar charts use `cursor:pointer` but have no `role`, `tabindex`, tooltip, or label indicating interactivity. This pattern, if extended to other pages, will recur. Covered under DISC-REPORTS-1 but noted as a systemic risk.

---

## Prioritized Recommendation List

| Priority | Finding ID | Page | Severity | Summary |
|----------|-----------|------|----------|---------|
| 1 | DISC-EXPLORE-1 | Explore | P1 | No explanation of tiles/Squadrats concept — primary task uncompletable |
| 2 | DISC-EXPLORE-2 | Explore | P1 | Multi-step route generation has no workflow sequencing |
| 3 | DISC-ROUTES-1 | Routes | P2 | Compare checkbox has no visible label — feature invisible on touch |
| 4 | DISC-REPORTS-3 | Reports | P2 | Reports absent from all bottom navigation bars |
| 5 | DISC-EXPLORE-4 | Explore | P2 | Explore absent from most bottom navigation bars |
| 6 | CP-1 | All pages | P2 | Bottom nav missing Reports + Explore system-wide |
| 7 | DISC-SETTINGS-1 | Settings | P2 | Fetch + Analyze two-step workflow has no sequencing guidance |
| 8 | DISC-SETTINGS-2 | Settings | P2 | TrainerRoad collapse trigger is non-button div, not touch-safe |
| 9 | DISC-SETTINGS-3 | Settings | P2 | Temperature slider always shows °F regardless of unit system |
| 10 | DISC-DETAIL-1 | Route Detail | P2 | Weather data shown as raw JSON dump |
| 11 | DISC-DETAIL-2 | Route Detail | P2 | "Ride Again" save has no post-save navigation hint |
| 12 | DISC-DASH-1 | Dashboard | P2 | Hidden commute direction collapse has no visual hint |
| 13 | DISC-DASH-2 | Dashboard | P2 | Mobile route status collapse has no count badge |
| 14 | DISC-ROUTES-2 | Routes | P2 | Saved Plans section hidden with no badge/entry-point |
| 15 | DISC-WEATHER-1 | Weather | P2 | Comfort score scale has no legend or definition |
| 16 | DISC-WEATHER-2 | Weather | P2 | Hardcoded commute window time labels mismatch API data |
| 17 | CP-3 | 5 pages | P2 | Help modal tutorial GIF assets not shipped |
| 18 | DISC-REPORTS-1 | Reports | P2 | Bar charts use role="img" — interactive affordance invisible |
| 19 | DISC-REPORTS-2 | Reports | P2 | "Backfill Gear IDs" is developer-facing label, unexplained |
| 20 | DISC-EXPLORE-3 | Explore | P2 | Distance slider defaults to km for imperial users until JS runs |
| 21 | DISC-SETTINGS-4 | Settings | P3 | Custom date fields use raw display toggle, no aria-expanded |
| 22 | DISC-EXPLORE-5 | Explore | P3 | "Clear Cache" lacks warning color or confirmation |
| 23 | DISC-DASH-4 | Dashboard | P3 | No error empty state when commute service fails |
| 24 | DISC-DETAIL-3 | Route Detail | P3 | Skip link placed after navbar, inconsistent with all other pages |
| 25 | DISC-DETAIL-4 | Route Detail | P3 | Performance Trends card hidden with no placeholder |
| 26 | DISC-ROUTES-3 | Routes | P3 | Color-by legend hidden until routes are plotted |
| 27 | DISC-ROUTES-4 | Routes | P3 | Help modal tutorial assets are placeholder paths |
| 28 | DISC-REPORTS-4 | Reports | P3 | "Miles" stat label hardcoded, ignores unit system |
| 29 | DISC-WEATHER-4 | Weather | P3 | Transit alert link is generic Google Maps, not pre-populated |
| 30 | DISC-DASH-3 | Dashboard | P3 | "What's New" toast and footer version string shows v0.14.0 |
| 31 | CP-2 | All pages | P3 | Footer version string stale (v0.14.0) on all 7 pages |
