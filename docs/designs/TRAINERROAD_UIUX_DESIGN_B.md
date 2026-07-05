# TrainerRoad UI/UX Design B: Inline Annotation Approach

**Design philosophy:** Instead of adding new cards, sections, or pages, this design
*annotates existing surfaces* with workout context. Workout data is a lens applied
on top of weather, commute, and route information — not a destination of its own.
The cyclist's morning decision flow stays unchanged: open app, see recommendation,
ride. Workout awareness is conveyed through **inline badges, tinted borders,
and expandable detail rows** rather than standalone cards.

---

## Design Tokens Reference

> **Superseded 2026-07-05:** `--primary-color`, `--success-color`, `--warning-color`, and
> `--danger-color` below are the pre-rebrand values. The app's brand colors are now the
> Fair Weather palette — see [`docs/designs/FAIR_WEATHER_BRAND_BOOK.md`](FAIR_WEATHER_BRAND_BOOK.md)
> and `plans/v0.6.0/DESIGN_PRINCIPLES.md` §4. `--workout-color` (burnt orange) is unaffected —
> it was chosen to be distinct from the brand palette and remains so under Fair Weather.

```
Spacing:  --space-1: 4px  --space-2: 8px  --space-3: 16px  --space-4: 24px
Type:     --font-size-xs: 0.75rem  --font-size-sm: 0.875rem  --font-size-base: 1rem
Colors (pre-rebrand):
          --primary-color: #667eea  --success-color: #28a745
          --warning-color: #ffc107  --danger-color: #dc3545
New:      --workout-color: #e85d04 (burnt orange — distinct from all existing palette)
          --workout-bg: rgba(232, 93, 4, 0.08)
          --workout-border: rgba(232, 93, 4, 0.3)
Grid:     8px baseline, all vertical spacing multiples of 8
```

---

## 1. Settings Page: TrainerRoad Configuration

### Approach: Add a section inside the existing "Connections" card

TrainerRoad joins Strava and intervals.icu as a third integration under the
existing `<div class="card">` with header "Connections". This avoids a new card
and keeps all external services grouped. The section is **collapsed by default**
behind a single clickable row — progressive disclosure for users who do not use
TrainerRoad.

### ASCII Mockup — Disconnected (collapsed default)

```
Connections
+---------------------------------------------------------------------------+
| [i] Strava                                                                |
|     [v Connected]  token expires Jun 2027                                 |
|     ... (existing Strava UI unchanged) ...                                |
|                                                                           |
|  -----------------------------------------------------------------------  |
|                                                                           |
| [i] intervals.icu                                                         |
|     ... (existing intervals.icu UI unchanged) ...                         |
|                                                                           |
|  -----------------------------------------------------------------------  |
|                                                                           |
| [>] TrainerRoad Calendar                                [Not connected]   |
|     Sync structured workouts from your TrainerRoad plan                   |
+---------------------------------------------------------------------------+
```

The `[>]` is a `bi-chevron-right` that rotates to `bi-chevron-down` on expand.
"Not connected" is a `badge bg-secondary`. The one-line description is
`font-size-sm text-muted`.

### ASCII Mockup — Disconnected (expanded)

```
|  -----------------------------------------------------------------------  |
|                                                                           |
| [v] TrainerRoad Calendar                                [Not connected]   |
|     Sync structured workouts from your TrainerRoad plan                   |
|                                                                           |
|     ICS Feed URL                                                          |
|     +---------------------------------------------------------------+     |
|     | https://feed.trainerroad.com/calendar/abc123.ics              |     |
|     +---------------------------------------------------------------+     |
|     (i) Find this at TrainerRoad > Settings > Calendar > ICS Link         |
|                                                                           |
|     [ Connect ]                                                           |
|                                                                           |
+---------------------------------------------------------------------------+
```

- Input is `type="url"` with `form-control`.
- Helper text uses `form-text` with `bi-info-circle`.
- "Connect" button is `btn btn-primary btn-sm`.

### ASCII Mockup — Connected

```
| [v] TrainerRoad Calendar                  [v Connected]  synced 2h ago    |
|     Sync structured workouts from your TrainerRoad plan                   |
|                                                                           |
|     +------------------------------------------------------------------+  |
|     | Next 7 days                                                      |  |
|     |  Thu 19  Pettit             Endurance    60 min    TSS 52        |  |
|     |  Sat 21  Spanish Needle     VO2Max       75 min    TSS 95        |  |
|     |  Mon 23  Slide Mountain     Threshold    90 min    TSS 110       |  |
|     +------------------------------------------------------------------+  |
|                                                                           |
|     [bi-arrow-repeat Sync Now]     [bi-trash3 Disconnect]                 |
|                                                                           |
+---------------------------------------------------------------------------+
```

Details:
- "Connected" is `badge bg-success`. "synced 2h ago" is `font-size-xs text-muted`.
- Upcoming workouts render in a **borderless compact table** (`table table-sm table-borderless mb-0`).
- Table columns: Date (short, `font-size-sm fw-semibold`), Name, Type (as a
  tinted `badge` — see color mapping below), Duration, TSS.
- "Sync Now" is `btn btn-outline-primary btn-sm`.
- "Disconnect" is `btn btn-outline-danger btn-sm`. Triggers confirm dialog.

### Workout Type Badge Colors

| Type       | Badge class                  | Icon              |
|------------|------------------------------|-------------------|
| Endurance  | `bg-success-subtle text-success` | `bi-heart-pulse`  |
| Tempo      | `bg-info-subtle text-info`       | `bi-speedometer`  |
| Threshold  | `bg-warning-subtle text-dark`    | `bi-lightning`    |
| VO2Max     | `bg-danger-subtle text-danger`   | `bi-fire`         |
| Sprint     | `bg-danger-subtle text-danger`   | `bi-lightning-charge` |
| Anaerobic  | `bg-dark-subtle text-dark`       | `bi-lightning-charge-fill` |

### States

| State        | Visual                                                          |
|--------------|----------------------------------------------------------------|
| Collapsed    | Chevron-right, one-line summary, badge "Not connected"         |
| Expanded/empty | URL input + Connect button                                   |
| Connecting   | Spinner on Connect button, input disabled                      |
| Connected    | Badge "Connected", sync timestamp, upcoming workout table      |
| Syncing      | Spinner on "Sync Now" button, "Syncing..." text                |
| Sync error   | `alert-warning` inline: "Sync failed — last successful: 6h ago" |
| Stale (>24h) | Badge changes to `bg-warning text-dark`: "Stale — sync now"   |
| Feed invalid | `alert-danger` inline after Connect: "Invalid ICS feed URL"   |

### Responsive

- **Desktop (md+):** Workout table shows all 5 columns.
- **Mobile (<md):** Table hides TSS column. Date column narrows to "Thu" only.
  Disconnect button moves below Sync Now (stacked `d-grid`).

### HTML Structure (key elements)

```html
<!-- Inside existing Connections card-body, after intervals.icu <hr> -->
<hr class="my-3">

<div class="d-flex align-items-start gap-2 cursor-pointer"
     data-bs-toggle="collapse" data-bs-target="#trainerroad-section"
     aria-expanded="false" aria-controls="trainerroad-section"
     role="button">
    <i class="bi bi-chevron-right tr-chevron" aria-hidden="true"></i>
    <div class="flex-grow-1">
        <h3 class="h6 fw-bold mb-0">
            <i class="bi bi-calendar-week me-1" aria-hidden="true"></i>TrainerRoad Calendar
        </h3>
        <p class="small text-muted mb-0">Sync structured workouts from your TrainerRoad plan</p>
    </div>
    <div id="tr-status-badge">
        <span class="badge bg-secondary">Not connected</span>
    </div>
</div>

<div class="collapse mt-3" id="trainerroad-section">
    <!-- Dynamic content: connect form OR connected state -->
    <div id="tr-connect-form">...</div>
    <div id="tr-connected-state" style="display:none">...</div>
</div>
```

CSS for chevron rotation:
```css
[aria-expanded="true"] .tr-chevron { transform: rotate(90deg); }
.tr-chevron { transition: transform 0.2s; display: inline-block; }
```

---

## 2. Dashboard: Workout Annotation on Existing Elements

### Approach: No new card. Two injection points.

The workout is NOT its own section. Instead:

**A) Weather banner gets a workout pill** — a small inline badge appended to
the right side of the existing weather banner, showing today's workout name
and type at a glance.

**B) Hero commute card gets a workout fit annotation** — an inline detail row
between the route name and the "Why this route?" reasons, showing how the
commute aligns with today's workout.

This preserves the existing visual hierarchy: weather at top, commute decision
below. The workout information *modifies* the decision context rather than
competing with it.

### 2A. Weather Banner — Workout Pill

#### No workout scheduled

Weather banner is unchanged. No workout pill renders.

#### Workout scheduled

```
+===========================================================================+
||                                                                         ||
||  [sun]  72F     Wind 8mph SW    Humidity 45%    [Excellent]             ||
||                                                                         ||
||                              [calendar-week] Pettit - Endurance  60min  ||
||                                                                         ||
+===========================================================================+
```

The workout pill sits on a second row within the weather banner, right-aligned.
It is a single `<div>` using the weather banner's existing flex layout:

```
+--------------------------------------------------------------------+
|  [bi-calendar-week]  Pettit  ·  Endurance [badge]  ·  60 min      |
+--------------------------------------------------------------------+
```

Styling:
- Container: `d-flex align-items-center gap-2 mt-2` inside the weather banner.
- Background: `rgba(255,255,255,0.15)` with `border-radius: 1rem` and
  `padding: var(--space-1) var(--space-3)` — matches the existing comfort badge.
- Text: `font-size-sm`, white, `opacity: 0.95`.
- Workout type badge: uses the badge color mapping from Section 1 but with
  white text on semi-transparent bg (`rgba(255,255,255,0.2)`).
- The pill is a link to the Settings page TrainerRoad section (anchor:
  `settings.html#trainerroad-section`).

#### ASCII Mockup — Full weather banner with workout

```
+===========================================================================+
||  [sun]  72F                                                             ||
||  Wind 8mph SW  ·  Humidity 45%  ·  UV 6  ·  [Excellent]                ||
||                                                                         ||
||  [calendar-week  Pettit · Endurance · 60 min                     ]      ||
+===========================================================================+
```

On mobile, the workout pill wraps to its own line and takes full width:

```
+=========================================+
||  [sun]  72F                           ||
||  Wind 8mph · Humid 45%               ||
||  [Excellent]                          ||
||                                       ||
||  [cal  Pettit · Endurance · 60m ]     ||
+=========================================+
```

### 2B. Hero Commute Card — Workout Fit Row

#### No workout scheduled

Hero card is unchanged. No workout fit row renders.

#### Workout scheduled — Good fit

```
+---+----------------------------------------------------------------------+
| G |  [check-circle-fill]  River Trail                                    |
| R |  [badge 87]  [Highly Recommended]                                    |
| E |                                                                      |
| E |  [heart-pulse] Workout fit: Pettit (Endurance)        [badge Good]   |
| N |  Duration matches workout target · Suitable for outdoor              |
|   |                                                                      |
| B |  [cloud-sun] Partly cloudy, light tailwind                           |
| O |  [clock] ~28 min                                                     |
| R |                                                                      |
| D |  Why this route?                                                     |
| E |  - Best weather window before noon                                   |
| R |  - Favorable wind on Ridge segment                                   |
+---+----------------------------------------------------------------------+
```

The workout fit row is injected **between the route name/score header and the
weather summary line**. It consists of:

1. A **header line**: workout icon + "Workout fit:" + workout name + type badge
   + fit rating badge.
2. A **detail line**: fit reasons joined by " · " in `font-size-xs text-muted`.

Fit rating badge colors:
- Good (score >= 0.7): `badge bg-success-subtle text-success`
- Moderate (0.4-0.7): `badge bg-warning-subtle text-dark`
- Poor (< 0.4): `badge bg-danger-subtle text-danger`

#### Workout scheduled — Poor fit (indoor recommended)

```
+---+----------------------------------------------------------------------+
| A |  [exclamation-triangle-fill]  River Trail                            |
| M |  [badge 52]  [Consider Alternatives]                                 |
| B |                                                                      |
| E |  [lightning] Workout fit: Spanish Needle (VO2Max)      [badge Poor]  |
| R |  High-intensity workout - indoor trainer recommended                 |
|   |                                                                      |
|   |  +----------------------------------------------------------------+  |
|   |  | [bi-house-door]  Indoor trainer recommended for this workout.  |  |
|   |  |  VO2Max efforts need controlled conditions for target power.   |  |
|   |  +----------------------------------------------------------------+  |
|   |                                                                      |
|   |  [cloud-sun] Partly cloudy, light tailwind                           |
+---+----------------------------------------------------------------------+
```

When `indoor_fallback: true`, an **amber alert strip** appears below the fit row:
- `alert alert-warning py-2 px-3 mb-2 small` (matches the existing transit
  recommendation alert pattern).
- Icon: `bi-house-door`.
- Text explains why indoor is better for this workout type.

#### Workout scheduled — Route extended

```
+---+----------------------------------------------------------------------+
| G |  [check-circle-fill]  River Trail (extended)                         |
| R |  [badge 82]  [Highly Recommended]                                    |
| E |                                                                      |
| E |  [heart-pulse] Workout fit: Pettit (Endurance)        [badge Good]   |
| N |  Route extended +12 min for endurance duration target                 |
|   |                                                                      |
|   |  [cloud-sun] Partly cloudy, light tailwind                           |
|   |  [clock] ~42 min (extended from ~30 min)                             |
+---+----------------------------------------------------------------------+
```

When `is_workout_extended: true`:
- Route name gets "(extended)" suffix in `text-muted`.
- Time estimate shows both extended and original duration.
- Fit reason line explains the extension.

### Rendering Logic (pseudocode)

```javascript
function renderWorkoutFitRow(workoutFit, isExtended) {
    if (!workoutFit) return '';

    const typeIcon = WORKOUT_TYPE_ICONS[workoutFit.workout_type] || 'bi-activity';
    const rating = workoutFit.fit_score >= 0.7 ? 'Good'
                 : workoutFit.fit_score >= 0.4 ? 'Moderate' : 'Poor';
    const ratingClass = rating === 'Good' ? 'bg-success-subtle text-success'
                      : rating === 'Moderate' ? 'bg-warning-subtle text-dark'
                      : 'bg-danger-subtle text-danger';

    let html = `
        <div class="d-flex align-items-center gap-2 mb-1"
             style="border-left: 3px solid var(--workout-color, #e85d04);
                    padding-left: var(--space-2); margin: var(--space-2) 0;">
            <i class="bi ${typeIcon}" style="color: var(--workout-color)"></i>
            <span class="fw-semibold" style="font-size: var(--font-size-sm)">
                Workout fit:
            </span>
            <span style="font-size: var(--font-size-sm)">
                ${esc(workoutFit.workout_name)}
                (${esc(workoutFit.workout_type)})
            </span>
            <span class="badge ${ratingClass} ms-auto">${rating}</span>
        </div>
        <div style="font-size: var(--font-size-xs); color: #6c757d;
                    padding-left: calc(var(--space-2) + 3px);
                    margin-bottom: var(--space-2);">
            ${workoutFit.fit_reasons.map(esc).join(' &middot; ')}
        </div>`;

    if (workoutFit.indoor_fallback) {
        html += `
            <div class="alert alert-warning py-2 px-3 mb-2 d-flex align-items-start gap-2 small">
                <i class="bi bi-house-door mt-1 flex-shrink-0"></i>
                <div>
                    <strong>Indoor trainer recommended for this workout.</strong>
                    ${workoutFit.workout_type} efforts need controlled conditions
                    for consistent target power.
                </div>
            </div>`;
    }

    return html;
}
```

---

## 3. Commute Page (now redirects to Dashboard)

The commute page currently redirects to `/` (index.html). All commute
information lives in the dashboard hero card. Therefore, the workout-aware
commute design from Section 2B **is** the commute page design. No separate
page changes needed.

If the commute page is ever restored as a standalone, the same workout fit
row pattern applies — it injects into each commute direction card identically.

### Additional detail for the "Compare routes" expanded view

When the user clicks "Compare routes" on the hero card, the collapsed
`#commute-detail` section shows both to-work and to-home recommendations.
Each secondary commute card in this expanded view should also get workout
annotation if relevant:

```
+----------------------------------------------------------------------+
|  Compare Routes                                                      |
|                                                                      |
|  To Work                                                             |
|  +----------------------------------------------------------------+  |
|  |  River Trail            [87]                                   |  |
|  |  [heart-pulse] Pettit fit: Good  ·  28 min  ·  6.2 mi         |  |
|  +----------------------------------------------------------------+  |
|  +----------------------------------------------------------------+  |
|  |  Hill Route              [71]                                  |  |
|  |  [heart-pulse] Pettit fit: Moderate  ·  35 min  ·  7.1 mi     |  |
|  +----------------------------------------------------------------+  |
|                                                                      |
|  To Home                                                             |
|  +----------------------------------------------------------------+  |
|  |  Riverside Return        [83]                                  |  |
|  |  [heart-pulse] Pettit fit: Good  ·  32 min  ·  6.8 mi         |  |
|  +----------------------------------------------------------------+  |
+----------------------------------------------------------------------+
```

In the compact secondary card format, the workout fit is a **single line**:
workout icon + workout name + "fit:" + rating badge. No expanded reasons.
This keeps the compare view scannable.

---

## 4. Recommendation: No Dedicated Workout Page

**Decision: Against a dedicated workout/training page.**

### Reasoning

1. **The app's job is commute routing, not training management.** TrainerRoad
   already has a full-featured UI for viewing/editing training plans. Duplicating
   workout calendars, completion tracking, or plan visualization would be a poor
   use of engineering time and would always be inferior to the source tool.

2. **The user's decision flow does not include a "training" stop.** The cyclist
   opens the app to answer one question: "How should I ride to work today?"
   Workout data is an input to that answer, not a destination. Forcing a detour
   through a workout page adds friction to the morning check.

3. **Information density is better served by annotation.** A dedicated page for
   a single day's workout (name, type, duration, TSS) would be 90% whitespace.
   The same information fits in 2 lines on the hero card and a pill on the
   weather banner.

4. **Progressive disclosure already handles complexity.** Power users who want
   to see upcoming workouts can expand the TrainerRoad section in Settings.
   The 7-day table there serves the "what's my training week look like?" use
   case without a separate page.

5. **Nav bar real estate.** Adding a 7th nav item degrades mobile navigation
   (the bottom nav currently has 3 items; more would crowd it or require a
   hamburger menu on mobile).

### When to reconsider

If the app later adds features that go beyond commute routing — multi-day
trip planning, weekly training load tracking, ride logging — then a
Training/Plan page would make sense as part of a broader scope expansion.
For the current single-purpose app, the annotation approach is correct.

---

## 5. Interaction Details

### Morning Decision Flow (with workout awareness)

```
User opens app
    |
    v
Weather banner loads
    +-- Workout pill appears if workout scheduled today
    |   (user sees "Pettit - Endurance - 60min" at a glance)
    |
    v
Hero commute card loads
    +-- Workout fit row appears below route name
    |   "Workout fit: Pettit (Endurance) [Good]"
    |   "Duration matches workout target"
    |
    |   IF indoor_fallback:
    |   +-- Amber alert: "Indoor trainer recommended"
    |   |   User decides to skip cycling commute
    |   |
    |   ELSE IF route extended:
    |   +-- Route shows extended duration
    |   |   "~42 min (extended from ~30 min)"
    |   |
    |   ELSE:
    |   +-- Normal recommendation with fit context
    |
    v
User taps "View route" or decides to ride
```

### Settings Configuration Flow

```
User navigates to Settings
    |
    v
Scrolls to Connections card
    +-- Sees collapsed TrainerRoad row
    |   "TrainerRoad Calendar  [Not connected]"
    |
    v
Clicks to expand
    +-- Sees URL input field
    |   Pastes ICS feed URL from TrainerRoad
    |   Clicks Connect
    |
    v
System validates URL, fetches feed, parses workouts
    +-- Success: badge flips to "Connected", table shows upcoming workouts
    +-- Failure: inline error "Invalid feed" or "Could not fetch"
    |
    v
Automatic sync every 6 hours (background, via APScheduler)
    +-- User can force sync with "Sync Now" button
    +-- Stale indicator (>24h) prompts resync
```

### Data Staleness Handling

The workout pill and fit row both check data freshness:

```javascript
function isWorkoutDataFresh(lastSync) {
    if (!lastSync) return false;
    const hoursSinceSync = (Date.now() - new Date(lastSync)) / 3600000;
    return hoursSinceSync < 24;
}
```

If stale (>24h since last sync):
- Weather banner pill adds a subtle `bi-exclamation-circle` icon and tooltip:
  "Workout data may be outdated — last synced 28h ago".
- Hero card fit row adds a `font-size-xs text-warning` note below reasons:
  "Workout data last synced 28h ago".
- Settings badge changes from "Connected" to "Stale — sync now" (`bg-warning`).

---

## 6. Empty States

### Dashboard — TrainerRoad not configured

No workout pill on weather banner. No workout fit row on hero card.
Everything looks exactly as it does today. Zero visual noise for users
who do not use TrainerRoad.

### Dashboard — TrainerRoad configured but no workout today

Weather banner: no workout pill.
Hero card: no workout fit row.
The absence of workout information IS the information — today is a rest day
or an unscheduled day.

Optionally (low priority): a subtle one-liner below the hero card:
```
[bi-calendar-check text-muted]  No workout scheduled today — ride as you like
```
This is `font-size-xs text-muted` and only shows when TR is connected AND
no workout exists for today. It confirms the system is working, not broken.

### Dashboard — TrainerRoad configured, sync failed

Weather banner: no workout pill (fail silent — do not show stale data).
Hero card: no workout fit row.
Settings page shows sync error state with retry option.

### Settings — Connected but 0 upcoming workouts

```
| [v] TrainerRoad Calendar                  [v Connected]  synced 2h ago    |
|                                                                           |
|     No workouts scheduled in the next 7 days.                             |
|     Check your TrainerRoad plan or sync again.                            |
|                                                                           |
|     [bi-arrow-repeat Sync Now]     [bi-trash3 Disconnect]                 |
```

---

## 7. Accessibility

- All workout badges have `aria-label` attributes:
  `aria-label="Workout type: Endurance"`.
- The collapsible TrainerRoad section uses `aria-expanded`, `aria-controls`.
- Fit rating badges include screen-reader text:
  `<span class="visually-hidden">Workout fit rating:</span> Good`.
- The indoor trainer alert uses `role="alert"` for screen reader announcement.
- Color is never the only indicator — badges include text labels, icons have
  adjacent text, the workout fit row has both the rating word and the color.
- The workout pill in the weather banner is keyboard-focusable and has
  `aria-label="Today's workout: Pettit, Endurance, 60 minutes"`.

---

## 8. API Endpoints Required

The frontend needs these endpoints (some may already exist in the backend):

| Endpoint                        | Method | Purpose                           |
|---------------------------------|--------|-----------------------------------|
| `/api/trainerroad/status`       | GET    | Connection status + last sync     |
| `/api/trainerroad/connect`      | POST   | Set ICS feed URL                  |
| `/api/trainerroad/disconnect`   | POST   | Remove credentials                |
| `/api/trainerroad/sync`         | POST   | Force sync                        |
| `/api/trainerroad/workouts`     | GET    | Upcoming workouts (7-day table)   |
| `/api/commute` (existing)       | GET    | Extended to include `workout_fit` |

The existing `/api/commute` endpoint should be extended to call
`get_workout_aware_commute()` instead of `get_next_commute()` when
TrainerRoad is configured. The response gains two new fields:

```json
{
  "to_work": {
    "status": "success",
    "route": { "name": "River Trail", "..." : "..." },
    "score": 0.87,
    "workout_fit": {
      "workout_name": "Pettit",
      "workout_type": "Endurance",
      "fit_score": 0.8,
      "fit_reasons": ["Duration matches workout target", "Suitable for outdoor completion"],
      "indoor_fallback": false,
      "notes": ["Can extend commute for endurance work"],
      "duration_target": { "min": 60, "max": 90 }
    },
    "is_workout_extended": false
  }
}
```

When TrainerRoad is not configured, `workout_fit` is `null` and
`is_workout_extended` is `false` — backward compatible.

---

## 9. Implementation Priority

| Phase | Scope                                      | Effort |
|-------|--------------------------------------------|--------|
| 1     | Settings: TR section in Connections card    | Small  |
| 2     | Dashboard: workout fit row in hero card     | Small  |
| 3     | Dashboard: workout pill in weather banner   | Small  |
| 4     | Compare view: compact workout fit lines     | Small  |
| 5     | Staleness indicators + empty states         | Small  |

Each phase is independently shippable. Phase 1 enables configuration;
Phase 2 delivers the core value (workout-aware commute decisions);
Phases 3-5 polish the experience.

---

## 10. Files to Modify

| File                          | Changes                                    |
|-------------------------------|--------------------------------------------|
| `static/settings.html`        | Add TR section inside Connections card     |
| `static/index.html`           | Add workout pill container in weather banner; CSS for workout tokens |
| `static/js/dashboard.js`      | `renderWorkoutFitRow()`, extend `renderHeroCard()`, workout pill in `loadWeather()` |
| `static/css/main.css`         | `--workout-color`, `.tr-chevron`, `.workout-pill`, `.workout-fit-row` |
| `static/js/api-client.js`     | Add TR API methods (status/connect/disconnect/sync/workouts) |
| `launch.py`                   | Add `/api/trainerroad/*` endpoints         |
| `app/services/commute_service.py` | Wire `get_workout_aware_commute()` into API response |
