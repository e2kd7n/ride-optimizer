# TrainerRoad Integration -- UI/UX Design A

**Date:** 2026-06-18
**Status:** Proposal
**Scope:** Settings configuration, Dashboard workout awareness, Commute workout-fit indicator

---

## Design Principles

1. **Additive, not disruptive.** TrainerRoad is an optional integration. Every touchpoint
   degrades gracefully when no feed is configured or no workout is scheduled.
2. **Consistent with existing patterns.** Reuse the same card/badge/alert vocabulary already
   established by Strava and intervals.icu sections.
3. **8px grid.** All spacing uses `--space-1` through `--space-5`. No magic numbers.
4. **Bootstrap 5.3 + Bootstrap Icons only.** No new icon libraries.

---

## 1. Settings Page -- TrainerRoad Configuration

### Placement

Insert a new `<hr class="my-3">` + TrainerRoad section inside the existing **Connections** card,
between the intervals.icu block and the closing `</div>` of the card-body. This follows the
exact pattern used by the Strava and intervals.icu sections: an `<h3 class="h6">` subheading
inside the shared Connections card, not a separate card.

### Layout

```
Connections card
+---------------------------------------------------------------+
| (i) Connections                                               |
+---------------------------------------------------------------+
| [Strava section -- existing]                                  |
| -----------------------------------------------------------  |
| [intervals.icu section -- existing]                           |
| -----------------------------------------------------------  |
|                                                               |
| (bicycle) TrainerRoad                                         |
|                                                               |
| [connection-status badge]  [sync-status text]                 |
|                                                               |
|  Connect your TrainerRoad calendar to get workout-aware        |
|  commute recommendations. Paste the ICS feed URL from          |
|  TrainerRoad > Settings > Calendar Sync.                       |
|                                                               |
| +--col-md-8-----------+ +--col-md-4--+                        |
| | ICS Feed URL         | |            |                        |
| | [________________________] | [Connect]  |                    |
| | (i) Found in TR >   | |            |                        |
| |     Settings > Cal   | |            |                        |
| +---------------------+ +------------+                        |
|                                                               |
| [feedback area -- hidden until action]                        |
|                                                               |
| When connected:                                               |
| +-----------------------------------------------------+      |
| | (check) Connected  Last sync: 2h ago  14 workouts   |      |
| |                                                      |      |
| | [Sync Now]  [Disconnect]                             |      |
| +-----------------------------------------------------+      |
+---------------------------------------------------------------+
```

### States

#### Empty (no feed configured)

```html
<hr class="my-3">
<h3 class="h6 fw-bold mb-2">
    <i class="bi bi-bicycle me-1"></i>TrainerRoad
</h3>
<div class="mb-3 d-flex align-items-center gap-3 flex-wrap">
    <div id="tr-connection-status">
        <span class="badge bg-secondary">
            <i class="bi bi-x-circle"></i> Not connected
        </span>
    </div>
</div>
<p class="small text-muted mb-3">
    Connect your TrainerRoad calendar to get workout-aware
    commute recommendations. Paste the ICS feed URL from
    TrainerRoad &rarr; Settings &rarr; Calendar Sync.
</p>
<div class="row g-3">
    <div class="col-md-8">
        <label class="form-label fw-bold" for="tr-feed-url">
            ICS Feed URL
        </label>
        <input type="url" class="form-control" id="tr-feed-url"
               placeholder="https://www.trainerroad.com/calendar/ics/..."
               autocomplete="off" spellcheck="false">
        <div class="form-text">
            Find it at TrainerRoad &rarr; Settings &rarr;
            <strong>Calendar Sync</strong> &mdash; copy the ICS link.
        </div>
    </div>
    <div class="col-md-4 d-flex align-items-end">
        <button type="button" class="btn btn-primary w-100"
                id="tr-connect-btn">
            <i class="bi bi-link-45deg"></i> Connect
        </button>
    </div>
</div>
<div id="tr-connect-feedback" class="mt-2" style="display:none">
</div>
```

#### Connected

Replace the input row with a status panel:

```html
<div id="tr-connected-panel">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <span class="badge bg-success">
            <i class="bi bi-check-circle"></i> Connected
        </span>
        <span class="text-muted small">
            <i class="bi bi-clock"></i> Last sync: 2h ago
        </span>
        <span class="badge bg-secondary">
            <i class="bi bi-calendar-week"></i> 14 upcoming workouts
        </span>
    </div>
    <div class="d-flex gap-2 flex-wrap">
        <button type="button" class="btn btn-sm btn-outline-primary"
                id="tr-sync-btn">
            <i class="bi bi-arrow-repeat"></i> Sync Now
        </button>
        <button type="button" class="btn btn-sm btn-outline-danger"
                id="tr-disconnect-btn">
            <i class="bi bi-x-lg"></i> Disconnect
        </button>
    </div>
</div>
```

#### Syncing (spinner on Sync Now)

```html
<button class="btn btn-sm btn-outline-primary" disabled>
    <span class="spinner-border spinner-border-sm me-1"></span>
    Syncing...
</button>
```

Display result as inline feedback below the buttons:

```html
<div class="mt-2 small text-success">
    <i class="bi bi-check-circle"></i>
    Synced 14 workouts (3 new, 11 updated)
</div>
```

#### Error states

- **Invalid URL:** Red form-text below input: `<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Invalid URL. Must start with https://</span>`
- **Feed fetch failed:** `<span class="text-danger small"><i class="bi bi-x-circle"></i> Could not reach TrainerRoad. Check your URL and try again.</span>`
- **Stale data (>24h since last sync):** Replace the "Last sync" badge color with `bg-warning text-dark`: `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> Last sync: 26h ago</span>`

### API Endpoints Needed

| Method | Path | Body | Response |
|--------|------|------|----------|
| `GET` | `/api/trainerroad/status` | -- | `{ connected: bool, last_sync: iso, workout_count: int, feed_url_masked: str }` |
| `POST` | `/api/trainerroad/connect` | `{ feed_url: str }` | `{ success: bool, workouts_synced: int, error?: str }` |
| `POST` | `/api/trainerroad/sync` | -- | `{ success: bool, workouts_synced: int, created: int, updated: int }` |
| `POST` | `/api/trainerroad/disconnect` | -- | `{ success: bool }` |

### Responsive Behavior

- `col-md-8` / `col-md-4` stacks to full-width below `md` breakpoint (same as intervals.icu).
- Badge row wraps naturally with `flex-wrap`.

---

## 2. Dashboard -- Workout Awareness

### Design Decision

Add a **workout strip** between the weather banner and the decision row. This strip is a
narrow, single-line element that appears only when a workout is scheduled for today. It does
not compete with the weather banner or the hero card -- it bridges them.

When no workout is scheduled today, this element does not render at all.

### Placement in DOM

```
<main class="container mt-2 mb-3">
    <!-- Weather Banner -->
    <div class="mb-2">...</div>

    <!-- NEW: Workout Strip (conditional) -->
    <div id="workout-strip" class="mb-2" style="display:none">
    </div>

    <!-- Decision Row: Hero Card + Map -->
    <div class="row mb-2">...</div>
</main>
```

### ASCII Mockup -- Workout Scheduled

```
+------------------------------------------------------------------+
| WEATHER BANNER (existing -- purple gradient)                      |
| 72F  Partly Cloudy  Wind 8mph SW  Precip 10%  [Good]            |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
| (lightning-charge) Pettit  Endurance  1:00   TSS 52              |
|                                                                   |
| "Can extend commute for endurance work"     [fit: Good]          |
+------------------------------------------------------------------+

+----Hero Card (col-lg-5)------+  +----Map + Panels (col-lg-7)----+
| (signpost) Your Commute      |  | Commute Forecast | Route Stat |
| ...                           |  | ...              | ...        |
```

### Workout Strip HTML

```html
<div id="workout-strip" class="mb-2" style="display:none">
    <div class="workout-strip">
        <!-- Filled dynamically by JS -->
    </div>
</div>
```

### Workout Strip CSS

```css
.workout-strip {
    background: white;
    border-radius: 8px;
    padding: var(--space-2) var(--space-3);
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    border: 1px solid rgba(0,0,0,0.07);
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex-wrap: wrap;
}

.workout-strip-icon {
    font-size: var(--font-size-lg);
    color: var(--primary-color);
    flex-shrink: 0;
}

.workout-strip-name {
    font-weight: 700;
    font-size: var(--font-size-base);
}

.workout-strip-meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    font-size: var(--font-size-sm);
    color: #6c757d;
}

.workout-strip-meta .badge {
    font-weight: 500;
}

.workout-strip-note {
    font-size: var(--font-size-sm);
    color: #555;
    flex-grow: 1;
}

.workout-fit-badge {
    font-weight: 600;
    padding: var(--space-1) var(--space-2);
    border-radius: 1rem;
}

.workout-fit-badge.fit-good {
    background-color: rgba(40, 167, 69, 0.12);
    color: #1a7431;
}

.workout-fit-badge.fit-moderate {
    background-color: rgba(255, 193, 7, 0.15);
    color: #7a6000;
}

.workout-fit-badge.fit-poor {
    background-color: rgba(220, 53, 69, 0.12);
    color: #a71d2a;
}
```

### Rendered States

#### Endurance workout (good fit -- commute can substitute)

```
+------------------------------------------------------------------+
| (lightning-charge)  Pettit                                       |
|                                                                   |
| [Endurance]  60 min  TSS 52                                      |
| Can extend commute for endurance work           [Good fit]       |
+------------------------------------------------------------------+
```

HTML:

```html
<div class="workout-strip">
    <i class="bi bi-lightning-charge workout-strip-icon"></i>
    <div>
        <div class="workout-strip-name">Pettit</div>
        <div class="workout-strip-meta">
            <span class="badge bg-info text-dark">Endurance</span>
            <span><i class="bi bi-clock"></i> 60 min</span>
            <span><i class="bi bi-speedometer2"></i> TSS 52</span>
        </div>
    </div>
    <div class="workout-strip-note">
        Can extend commute for endurance work
    </div>
    <span class="workout-fit-badge fit-good">
        <i class="bi bi-check-circle"></i> Good fit
    </span>
</div>
```

#### High-intensity workout (poor fit -- indoor recommended)

```
+------------------------------------------------------------------+
| (lightning-charge)  Spencer +2                                    |
|                                                                   |
| [VO2Max]  75 min  TSS 102  IF 1.05                               |
| (!) Indoor trainer recommended for this workout  [Indoor]        |
+------------------------------------------------------------------+
```

The note area uses `text-warning` color, and the badge becomes:

```html
<span class="workout-fit-badge fit-poor">
    <i class="bi bi-house-door"></i> Indoor
</span>
```

#### Threshold workout (moderate fit)

```
+------------------------------------------------------------------+
| (lightning-charge)  Kaweah                                       |
|                                                                   |
| [Threshold]  60 min  TSS 78                                      |
| High-intensity -- consider indoor trainer       [Moderate fit]   |
+------------------------------------------------------------------+
```

#### No workout today

The `#workout-strip` div stays `display:none`. Nothing renders. No placeholder.

### Workout Type Badge Colors

| Type | Bootstrap class | Rationale |
|------|----------------|-----------|
| Endurance | `bg-info text-dark` | Calm, blue-toned, low stress |
| Tempo | `bg-primary` (custom: `bg-primary-subtle text-primary`) | Mid-effort, branded |
| Threshold | `bg-warning text-dark` | Amber = caution, hard effort |
| VO2Max | `bg-danger` | Red = very hard |
| Sprint | `bg-danger` | Red = explosive |
| Anaerobic | `bg-danger` | Red = maximal |
| Recovery | `bg-success` | Green = easy |

### Responsive Behavior

At `< md` breakpoint:

```css
@media (max-width: 767.98px) {
    .workout-strip {
        padding: var(--space-2);
        gap: var(--space-2);
    }

    .workout-strip-icon {
        font-size: var(--font-size-base);
    }

    .workout-strip-note {
        width: 100%;
        order: 10;
    }
}
```

The note text wraps to its own line on mobile. The badge stays inline with the
workout name row.

### API Endpoint Needed

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/trainerroad/today` | `{ has_workout: bool, workout?: { name, type, duration_minutes, tss, intensity_factor, fit_label, fit_score, indoor_fallback, notes[] } }` |

### Dashboard JS Integration

Add a new `loadWorkoutStrip()` function called from `loadDashboard()`:

```javascript
async function loadWorkoutStrip() {
    const container = document.getElementById('workout-strip');
    if (!container) return;

    try {
        const data = await window.apiClient.fetch('/trainerroad/today');
        if (!data.has_workout) {
            container.style.display = 'none';
            return;
        }

        const w = data.workout;
        const esc = window.escapeHtml;
        const typeBadgeClass = getWorkoutTypeBadgeClass(w.type);
        const fitClass = w.fit_score >= 0.7 ? 'fit-good'
                       : w.fit_score >= 0.4 ? 'fit-moderate'
                       : 'fit-poor';
        const fitLabel = w.indoor_fallback ? 'Indoor'
                       : w.fit_score >= 0.7 ? 'Good fit'
                       : w.fit_score >= 0.4 ? 'Moderate fit'
                       : 'Poor fit';
        const fitIcon = w.indoor_fallback ? 'bi-house-door'
                      : w.fit_score >= 0.7 ? 'bi-check-circle'
                      : w.fit_score >= 0.4 ? 'bi-dash-circle'
                      : 'bi-x-circle';

        const noteText = w.notes && w.notes.length > 0
            ? esc(w.notes[0])
            : '';

        container.innerHTML = `
            <div class="workout-strip">
                <i class="bi bi-lightning-charge workout-strip-icon"></i>
                <div>
                    <div class="workout-strip-name">${esc(w.name)}</div>
                    <div class="workout-strip-meta">
                        <span class="badge ${typeBadgeClass}">${esc(w.type)}</span>
                        <span><i class="bi bi-clock"></i> ${w.duration_minutes} min</span>
                        ${w.tss ? `<span><i class="bi bi-speedometer2"></i> TSS ${w.tss}</span>` : ''}
                        ${w.intensity_factor ? `<span>IF ${w.intensity_factor.toFixed(2)}</span>` : ''}
                    </div>
                </div>
                ${noteText ? `<div class="workout-strip-note">${noteText}</div>` : ''}
                <span class="workout-fit-badge ${fitClass}">
                    <i class="bi ${fitIcon}"></i> ${fitLabel}
                </span>
            </div>`;

        container.style.display = '';
    } catch (error) {
        // Silent failure -- workout info is supplementary
        console.warn('Workout strip unavailable:', error);
        container.style.display = 'none';
    }
}
```

---

## 3. Commute Hero Card -- Workout Fit Indicator

### Design Decision

When a workout is scheduled, the hero card's commute recommendation gains a
**workout-fit alert** inserted between the "Why this route?" reasons list and
the action buttons. This is a Bootstrap `alert` component (same pattern as the
existing transit recommendation banner).

The hero card already has a transit banner for bad weather. The workout-fit alert
sits above it (workout context first, then transit fallback).

### ASCII Mockup -- Good Fit (Endurance, route extended)

```
+---------------------------------------------+
| (signpost) Your Commute                     |
|                                              |
| To Work  Morning                             |
|                                              |
| (check-circle) River Trail Extended          |
| [88] [High confidence]                       |
|                                              |
| Partly cloudy, 72F, light SW wind            |
| ~42 min                                      |
|                                              |
| Why this route?                              |
|  - Best wind conditions today                |
|  - Extended +12 min for Pettit workout       |
|                                              |
| +------------------------------------------+|
| | (bicycle) Workout fit: Good               ||
| |                                           ||
| | Pettit (Endurance, 60 min)                ||
| | Route extended to 42 min to match         ||
| | endurance target. Remaining 18 min at     ||
| | home on trainer.                          ||
| +------------------------------------------+|
|                                              |
| [View route]  [Compare routes v]             |
+---------------------------------------------+
```

### ASCII Mockup -- Poor Fit (VO2Max, indoor fallback)

```
+---------------------------------------------+
| (signpost) Your Commute                     |
|                                              |
| To Work  Morning                             |
|                                              |
| (check-circle) Greenway                      |
| [82] [High confidence]                       |
|                                              |
| +------------------------------------------+|
| | (!) Indoor trainer recommended            ||
| |                                           ||
| | Spencer +2 (VO2Max, 75 min, TSS 102)     ||
| | High-intensity intervals require precise  ||
| | power control. Complete on trainer, use   ||
| | standard commute route.                   ||
| +------------------------------------------+|
|                                              |
| [View route]  [Compare routes v]             |
+---------------------------------------------+
```

### ASCII Mockup -- Moderate Fit (Threshold)

```
| +------------------------------------------+|
| | (dash-circle) Workout fit: Moderate       ||
| |                                           ||
| | Kaweah (Threshold, 60 min)               ||
| | Commute duration close to workout target  ||
| | but intervals need controlled effort.     ||
| | Consider doing structured part on trainer.||
| +------------------------------------------+|
```

### HTML Structure

Injected into the hero card template, between `hero-reasons` and the action buttons:

```html
<!-- Workout fit alert (only when workout_fit is present) -->
<div class="alert alert-workout-fit mt-2 mb-2 py-2 px-3
            d-flex align-items-start gap-2"
     role="status">
    <i class="bi bi-bicycle mt-1 flex-shrink-0
              workout-fit-icon"></i>
    <div class="flex-grow-1 small">
        <strong class="workout-fit-headline">
            Workout fit: Good
        </strong>
        <div class="mt-1">
            Pettit (Endurance, 60 min)
        </div>
        <div class="text-muted mt-1">
            Route extended to 42 min to match endurance target.
            Remaining 18 min at home on trainer.
        </div>
    </div>
</div>
```

### Alert Styling by Fit Level

| Fit | Alert class | Icon | Border color | Background |
|-----|-------------|------|-------------|------------|
| Good (>= 0.7) | `alert-success` | `bi-bicycle` | `--success-color` | Bootstrap success-subtle |
| Moderate (0.4 - 0.69) | `alert-warning` | `bi-dash-circle` | `--warning-color` | Bootstrap warning-subtle |
| Poor / Indoor (< 0.4 or indoor_fallback) | `alert-danger` | `bi-exclamation-triangle` | `--danger-color` | Bootstrap danger-subtle |

CSS overrides for tight spacing:

```css
.alert-workout-fit {
    border-radius: 8px;
    font-size: var(--font-size-sm);
    border-left: 4px solid;
}

.alert-workout-fit.alert-success {
    border-left-color: var(--success-color);
}

.alert-workout-fit.alert-warning {
    border-left-color: var(--warning-color);
}

.alert-workout-fit.alert-danger {
    border-left-color: var(--danger-color);
}
```

### JS Integration in renderHeroCard()

Modify `renderHeroCard()` in `dashboard.js` to accept workout_fit data from the
API response and inject the alert:

```javascript
// Inside renderHeroCard(), after the reasons <ul> and before the action buttons:

const workoutFit = rec.workout_fit;
const workoutAlert = workoutFit ? (() => {
    const fitScore = workoutFit.fit_score || 0;
    const isIndoor = workoutFit.indoor_fallback;

    let alertClass, icon, headline;
    if (isIndoor) {
        alertClass = 'alert-danger';
        icon = 'bi-exclamation-triangle';
        headline = 'Indoor trainer recommended';
    } else if (fitScore >= 0.7) {
        alertClass = 'alert-success';
        icon = 'bi-bicycle';
        headline = 'Workout fit: Good';
    } else if (fitScore >= 0.4) {
        alertClass = 'alert-warning';
        icon = 'bi-dash-circle';
        headline = 'Workout fit: Moderate';
    } else {
        alertClass = 'alert-danger';
        icon = 'bi-x-circle';
        headline = 'Workout fit: Poor';
    }

    const wName = esc(workoutFit.workout_name || 'Workout');
    const wType = esc(workoutFit.workout_type || '');
    const dur = workoutFit.duration_target;
    const durText = dur && dur.min
        ? `, ${dur.min} min`
        : '';
    const notes = (workoutFit.notes || [])
        .map(n => esc(n)).join('. ');
    const reasons = (workoutFit.fit_reasons || [])
        .map(r => esc(r)).join('. ');

    return `
        <div class="alert alert-workout-fit ${alertClass} mt-2 mb-2
                    py-2 px-3 d-flex align-items-start gap-2"
             role="status">
            <i class="bi ${icon} mt-1 flex-shrink-0"></i>
            <div class="flex-grow-1 small">
                <strong>${headline}</strong>
                <div class="mt-1">
                    ${wName}${wType ? ` (${wType}${durText})` : ''}
                </div>
                ${reasons ? `<div class="text-muted mt-1">${reasons}</div>` : ''}
                ${notes ? `<div class="text-muted mt-1">${notes}</div>` : ''}
            </div>
        </div>`;
})() : '';

// Then in the template string, insert ${workoutAlert} before the action buttons div.
```

### API Change: Commute Endpoint

The existing `/api/commute` endpoint should call `get_workout_aware_commute()` instead
of `get_next_commute()` when TrainerRoad is configured. The response gains two new fields:

```json
{
    "status": "success",
    "direction": "to_work",
    "route": { ... },
    "score": 0.88,
    "workout_fit": {
        "workout_name": "Pettit",
        "workout_type": "Endurance",
        "fit_score": 0.8,
        "fit_reasons": [
            "Duration matches workout target",
            "Suitable for outdoor completion"
        ],
        "indoor_fallback": false,
        "notes": ["Can extend commute for endurance work"],
        "duration_target": { "min": 60, "max": 90 }
    },
    "is_workout_extended": true,
    "extension_reason": "Extended to meet Pettit duration"
}
```

When no TrainerRoad feed is configured, `workout_fit` is `null` and
`is_workout_extended` is `false`. The frontend checks `if (rec.workout_fit)`
before rendering the alert -- zero visual change for users without the integration.

---

## 4. Interaction Flow Summary

### First-time setup

1. User navigates to Settings.
2. Scrolls to Connections card, finds TrainerRoad section showing "Not connected".
3. Pastes ICS feed URL, clicks **Connect**.
4. Button shows spinner. On success: input row replaced with connected panel showing
   badge count and sync timestamp. Toast: "TrainerRoad connected! 14 workouts synced."
5. On error: inline red feedback below input. Input stays editable for correction.

### Daily use -- workout day

1. User opens Dashboard.
2. Weather banner loads (existing).
3. Workout strip fades in below weather banner: "Pettit -- Endurance -- 60 min -- Good fit".
4. Hero commute card loads. If the commute was extended for the workout, the reasons list
   includes "Extended +12 min for Pettit workout". The workout-fit alert box appears in
   green: "Workout fit: Good".
5. If a VO2Max day: workout strip shows red "Indoor" badge. Hero card shows red alert:
   "Indoor trainer recommended". Standard (non-extended) commute route is shown.

### Daily use -- rest day / no workout

1. Dashboard loads normally. Workout strip is hidden. Hero card has no workout alert.
   Zero visual difference from pre-integration behavior.

### Stale data

1. If sync is >24 hours old, the workout strip adds a subtle warning:
   `<span class="badge bg-warning text-dark ms-2"><i class="bi bi-exclamation-triangle"></i> Stale</span>`
2. Settings page shows the "Last sync" badge in amber instead of gray.
3. Data is still used -- just flagged. The sync interval (6h) normally prevents this.

---

## 5. Complete File Change List

| File | Change |
|------|--------|
| `static/settings.html` | Add TrainerRoad section inside Connections card |
| `static/index.html` | Add `#workout-strip` div between weather banner and decision row |
| `static/css/main.css` | Add `.workout-strip`, `.workout-fit-badge`, `.alert-workout-fit` styles |
| `static/js/dashboard.js` | Add `loadWorkoutStrip()`, modify `renderHeroCard()` for workout_fit |
| `static/js/api-client.js` | Add TrainerRoad API methods |
| `launch.py` | Add `/api/trainerroad/*` endpoints, modify `/api/commute` to use workout-aware path |
| `app/services/trainerroad_service.py` | Add `get_status()`, `get_today_workout_summary()` methods |
| `app/services/commute_service.py` | Already has `get_workout_aware_commute()` -- no changes needed |

---

## 6. Accessibility

- All icons have `aria-hidden="true"` with adjacent text labels.
- Workout-fit alert uses `role="status"` so screen readers announce it.
- Workout strip uses `role="complementary"` with `aria-label="Today's workout"`.
- Color is never the sole indicator: every colored badge has a text label (Good/Moderate/Poor/Indoor).
- Focus order: workout strip is in natural tab order between weather banner and hero card.
- Disconnect button gets a confirmation dialog (same pattern as "Clear All Local Data").

---

## 7. Mobile Wireframe (< 768px)

```
+-----------------------------+
| Weather Banner (compact)    |
+-----------------------------+

+-----------------------------+
| (lightning) Pettit          |
| [Endurance] 60 min TSS 52  |
| Can extend commute...       |
|                   [Good fit]|
+-----------------------------+

+-----------------------------+
| (signpost) Your Commute     |
| (check) River Trail Ext.    |
| [88] [High confidence]      |
|                              |
| ~42 min  12.3 mi  620 ft    |
|                              |
| +-- Workout fit: Good -----+|
| | Pettit (Endurance, 60min)||
| | Route extended to match  ||
| | endurance target.        ||
| +---------------------------+|
|                              |
| [View route] [Compare v]    |
+-----------------------------+

+-----------------------------+
| Commute Forecast            |
+-----------------------------+
| Route Status                |
+-----------------------------+
| Map                         |
+-----------------------------+
```

All elements stack vertically. The workout strip and workout-fit alert both use
full width. No horizontal scrolling.
