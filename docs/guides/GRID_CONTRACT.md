# Grid Contract

**Scope:** All pages in the PWA (`index.html`, `routes.html`, `commute.html`, `settings.html`)  
**Authority:** This document supersedes the spacing scale in `UIUX_REDESIGN_STRATEGY.md` Appendix B, which incorrectly lists 12px as a valid token value.  
**Last Updated:** 2026-05-21

---

## The one rule

Every spacing, sizing, and layout value must land on a **multiple of 8px**. Sub-pixel details (border widths, icon nudges, focus ring offsets) may use **4px**. Nothing else.

If you find yourself writing `6px`, `10px`, `12px`, `20px`, `2px`, or `3px` for spacing — stop. Those values are off-grid.

---

## Spacing tokens

These tokens are defined in `main.css` `:root` and are the only values to use for padding, margin, and gap. Do not write raw `px` or `rem` values for spacing.

```css
--space-1: 4px;   /* sub-grid: border widths, focus offsets, icon nudges */
--space-2: 8px;   /* tight: icon-to-label gaps, inline chip padding    */
--space-3: 16px;  /* standard: card padding, form field spacing         */
--space-4: 24px;  /* comfortable: section padding, card-to-card gaps    */
--space-5: 32px;  /* loose: major section separation                    */
```

### When to use each token

| Token | Value | Use for |
|---|---|---|
| `--space-1` | 4px | Focus ring offset, nav active border, icon margin nudge |
| `--space-2` | 8px | Gap between inline elements, tight card padding, bottom-nav icon margin |
| `--space-3` | 16px | Card body padding, toast padding, standard gap between cards |
| `--space-4` | 24px | Section padding (info bar, filters section), gap between major sections |
| `--space-5` | 32px | Page-level section separation |

### What 12px means

There is no 12px token. `0.75rem` resolves to 12px — it appears throughout the codebase and is off-grid in every case. When you see it, replace it with either `--space-2` (8px) or `--space-3` (16px) depending on whether the intent is tight or standard spacing.

---

## Component sizing

UI component dimensions (heights, fixed widths, icon sizes) must be multiples of 8px. Content dimensions (text, images) follow their natural size.

### Fixed heights

```css
--nav-height:         56px;   /* top navbar and bottom nav bar  */
--info-bar-height:    72px;   /* home page compact info bar     */
--route-card-height:  56px;   /* compact route card row         */
--quick-actions-height: 48px; /* quick action button strip      */
--bottom-nav-height:  56px;   /* mobile bottom navigation       */
```

Add these to `:root` in `main.css`. Reference them as tokens — never hardcode the same pixel value twice.

### Map heights

```css
--map-height-standard: 400px;  /* routes page, inline maps              */
--map-height-large:    600px;  /* commute page dedicated map view        */
```

All three pages currently hardcode map heights independently (400px / 500px / 600px). Use these tokens instead. The `commute.html` inline `style="height: 500px"` on the iframe must become a CSS class using `--map-height-large`.

### Arbitrary-width elements

When you need a fixed width for a UI element (skeleton loader, badge, indicator), use the nearest 8px multiple:

| You want | Use instead |
|---|---|
| 60px | 56px or 64px |
| 100px | 96px or 104px |
| 150px | 144px or 152px |

---

## Layout system: Bootstrap 12-column grid

Do not use raw flexbox with hardcoded widths for page-level layout. Use Bootstrap's `col-*` classes. The one exception is tight inline component layout (e.g., a flex row of a label + value inside a card), where `display: flex` and `gap: var(--space-2)` is appropriate.

### Column layout per page

| Page | Layout | Columns |
|---|---|---|
| Home (`index.html`) | Three-region at `lg` | `col-lg-5` hero + `col-lg-7` (2×`col-6` panels above, map below) |
| Routes (`routes.html`) | Two-region at `lg` | `col-lg-5` list + `col-lg-7` map |
| Commute (`commute.html`) | Two-region at `md` | `col-md-5` cards + `col-md-7` map |
| Settings (`settings.html`) | Two-region at `md` | `col-md-6` + `col-md-6` |

The `commute.html` sidebar currently uses `flex: 0 0 400px`, which bypasses the grid. Replace with `col-md-5` / `col-md-7`.

### The single container pattern

Every page's `<main>` element uses exactly one `.container`. The home page currently wraps a `.container` inside `.container-fluid` — remove the outer `container-fluid` to match every other page.

```html
<!-- Correct — used by routes.html, commute.html, settings.html -->
<main id="main-content" class="container mt-4">

<!-- Wrong — current index.html -->
<main class="container-fluid mt-4">
    <div class="container"> ... </div>
</main>
```

---

## Breakpoints

Bootstrap defines these. Our custom CSS must use the same values — never 1px off.

```
Mobile    < 768px    (max-width: 767.98px)
Tablet    ≥ 768px    (md — two-column layouts unlock)
Desktop   ≥ 992px    (lg — three-column layouts unlock)
Wide      ≥ 1200px   (xl — max container width 1140px)
```

### The primary breakpoint is `md`

All two-column layouts in this app break at `md` (768px). Do not use `sm` (576px) for page-level layout breakpoints. The `settings.html` About section uses `col-sm-3` / `col-sm-9` — change to `col-md-3` / `col-md-9`.

### Writing custom media queries

```css
/* Correct */
@media (max-width: 767.98px) { ... }   /* mobile — matches Bootstrap's md boundary exactly */
@media (min-width: 768px) { ... }      /* tablet and above */
@media (min-width: 992px) { ... }      /* desktop and above */

/* Wrong — off by one pixel from Bootstrap */
@media (max-width: 767px) { ... }
@media (max-width: 768px) { ... }
```

---

## Desktop scope (≥ 992px / `lg`)

At desktop widths the app shows three distinct regions on the home page and two on every other page. No page requires vertical scrolling to access primary content at 1024×768.

### Home page layout at 1024×768

```
┌─────────────────────────────────────────────────────────┐
│ Navbar                                          56px    │
├─────────────────────────────────────────────────────────┤
│ Compact info bar (weather · commute · stats)    72px    │
├──────────────────────┬──────────────────────────────────┤
│                      │ Conditions   │ Route Status      │
│  Hero decision card  ├──────────────┴───────────────    │
│   col-lg-5           │  Map iframe          col-lg-7    │
│                      │  --map-height-large (600px)      │
│                      │                                  │
└──────────────────────┴──────────────────────────────────┘
```

The hero card and map column each take 5/12 and 7/12 of the row. The conditions and route status panels live inside the map column as a `row mb-2` above the map iframe, each taking `col-6`. Do not give the side panels their own `col-lg-2` — that column is too narrow (~160px at 960px viewport) for two stacked cards.

### Routes page layout at desktop

```
┌─────────────────────────────────────────────────────────┐
│ Navbar                                          56px    │
├─────────────────────────────────────────────────────────┤
│ Filters section                                 ~80px   │
├──────────────────────┬──────────────────────────────────┤
│  Route list          │  Map                            │
│  col-lg-5            │  col-lg-7                       │
│  max-height: 600px   │  height: var(--map-height-standard) │
│  overflow-y: auto    │                                  │
└──────────────────────┴──────────────────────────────────┘
```

### Commute page layout at desktop

```
┌─────────────────────────────────────────────────────────┐
│ Navbar                                          56px    │
├──────────────────────┬──────────────────────────────────┤
│  Route cards         │  Map                            │
│  col-md-5            │  col-md-7                       │
│  display: flex       │  height: var(--map-height-large) │
│  flex-direction: col │                                  │
│  gap: var(--space-3) │                                  │
└──────────────────────┴──────────────────────────────────┘
```

---

## Mobile scope (< 768px)

On mobile every page collapses to a single column. The top navbar is replaced by the fixed bottom nav bar. Content cards stack vertically with `var(--space-3)` (16px) between them.

### Mobile layout rules

- All `col-md-*` columns collapse to full width below 768px — no additional overrides needed for most content
- Map sections stack **below** their associated content lists (route list above map, commute cards above map)
- The bottom nav bar is 56px tall and fixed. Add `padding-bottom: var(--nav-height)` (56px) to `<body>` and `padding-bottom: 72px` to `main` / `.container-fluid` on mobile to prevent content clipping

```css
@media (max-width: 767.98px) {
    body { padding-bottom: var(--bottom-nav-height); }   /* 56px */
    main, .container-fluid { padding-bottom: 72px; }     /* 56px nav + 16px buffer */
}
```

### Mobile map heights

On mobile, maps shrink to avoid dominating the viewport:

```css
@media (max-width: 767.98px) {
    .map-container,
    .map-iframe {
        height: var(--map-height-standard);   /* 400px */
    }
}
```

The commute page map drops from `--map-height-large` (600px) to `--map-height-standard` (400px) on mobile. This is already partially implemented but uses inconsistent `!important` overrides — replace with the token-based media query above.

### Touch targets

Every interactive element must meet the 44×44px minimum touch target:

```css
/* Already defined in main.css under Issue #250 */
.btn, button { min-height: 44px; min-width: 44px; }
input, select, textarea { min-height: 44px; }

/* On mobile, increase to 48px */
@media (max-width: 767.98px) {
    .btn, button { min-height: 48px; }
    input, select, textarea { min-height: 48px; }
}
```

### Bottom navigation

The mobile bottom nav uses `--bottom-nav-height: 56px` and is shown via:

```css
.bottom-nav { display: none; }

@media (max-width: 767.98px) {
    .bottom-nav { display: flex !important; }
}
```

The `!important` is required to override Bootstrap's `.d-md-none` utility. This is the one deliberate use of `!important` in the stylesheet — do not add others.

---

## Card anatomy

Every card in the app shares these spatial properties:

```css
.card {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card-body {
    padding: var(--space-3);   /* 16px all sides */
}

.card-title {
    margin-bottom: var(--space-3);   /* 16px below title before content */
}
```

For dense cards (conditions panel, route status panel) where the `card-body` is overridden with `.p-3`, the intent is Bootstrap's `1rem` (16px) — that is on-grid. Do not use `.p-2` (8px) unless the card is intentionally tight (e.g., the compact route card row).

---

## Spacing reference card

Use this when deciding between tokens:

```
4px  --space-1   Focus ring offset, active nav border-bottom, icon-to-text nudge
8px  --space-2   Gap between icon and label, inline chip padding, tight list item gap
16px --space-3   Card body padding, toast padding, standard form field gap, card margin-bottom
24px --space-4   Info bar padding, filters section padding, gap between card rows
32px --space-5   Page section separation (h1 margin-bottom on non-compact pages)
```

---

## Common violations and their fixes

| Wrong | Right | Token |
|---|---|---|
| `padding: 1rem 1.25rem` | `padding: var(--space-3)` | 16px all sides |
| `gap: 0.75rem` | `gap: var(--space-2)` | 8px |
| `gap: 12px` | `gap: var(--space-2)` | 8px |
| `padding: 12px 16px` | `padding: var(--space-2) var(--space-3)` | 8px / 16px |
| `bottom: 20px` | `bottom: var(--space-3)` | 16px |
| `margin-bottom: 2px` | `margin-bottom: var(--space-1)` | 4px |
| `outline-offset: 3px` | `outline-offset: var(--space-1)` | 4px |
| `border-bottom: 3px` | `border-bottom: 4px` | 4px (sub-grid) |
| `width: 60px` | `width: 64px` | nearest 8px multiple |
| `width: 100px` | `width: 96px` | nearest 8px multiple |
| `height: 20px` | `height: 16px` or `24px` | nearest 8px multiple |

---

## How to verify compliance

Before submitting a PR that touches `main.css` or any page `<style>` block:

1. Search for raw spacing values: `grep -E '(padding|margin|gap|top|right|bottom|left):\s*(0\.75|1\.25|0\.375|6px|12px|20px|2px|3px)' static/css/main.css` — should return zero results.

2. Check component heights and widths: any explicit `width` or `height` on a UI component (not a content image) that is not a multiple of 8 is a violation.

3. Check for `container-fluid` on `<main>` — should never appear. `<main>` always uses `container`.

4. Check for custom `flex: 0 0 <Npx>` on page-level layout elements — replace with Bootstrap column classes.

5. Check media query values — all custom `@media` breakpoints must use `767.98px`, `768px`, `991.98px`, or `992px` (Bootstrap's exact boundaries). No `767px`, `769px`, etc.

---

## Related documents

- [UIUX_REDESIGN_STRATEGY.md](../UIUX_REDESIGN_STRATEGY.md) — design principles and page vision (note: Appendix B token names are superseded by this document)
- [DASHBOARD_REDESIGN_VISION.md](../DASHBOARD_REDESIGN_VISION.md) — home page layout rationale
- GitHub Issue #297 — full audit of current violations with per-component fix code
