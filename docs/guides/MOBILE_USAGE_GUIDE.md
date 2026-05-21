# Mobile Design Guide

**Scope:** PWA mobile experience — `index.html`, `routes.html`, `commute.html`, `settings.html`  
**Applies to:** All work on `static/`, `static/css/main.css`, and page `<style>` blocks  
**Last Updated:** 2026-05-21

> This guide replaced a legacy document that covered the old CLI-generated HTML report. That context no longer applies. This document covers the current web app.

---

## Overview

The app targets two primary device contexts:

| Context | Viewport | Interaction model | Primary use case |
|---|---|---|---|
| Mobile | < 768px | Touch, portrait | Check conditions on the go, pre-ride |
| Desktop/tablet | ≥ 768px | Mouse or touch, landscape | Plan at desk, compare routes |

The breakpoint between them is Bootstrap's `md` tier: **768px**. Everything below 768px is the mobile experience. See [GRID_CONTRACT.md](GRID_CONTRACT.md) for the full layout and spacing spec.

---

## Mobile layout

### Single column

Below 768px all Bootstrap `col-md-*` columns collapse to full width. No additional overrides are needed for most content — Bootstrap handles it. The exceptions are documented below.

### Page-by-page mobile layout

**Home (`index.html`)**
```
┌─────────────────────────────┐
│ Top navbar (collapsible)    │  56px
├─────────────────────────────┤
│ Weather banner              │  auto
├─────────────────────────────┤
│ Hero decision card          │  auto
├─────────────────────────────┤
│ Conditions  │  Route Status │  col-6 / col-6
├─────────────────────────────┤
│ Map iframe                  │  400px (--map-height-standard)
├─────────────────────────────┤
│ Route Statistics            │  auto
├─────────────────────────────┤
│ [bottom nav — fixed]        │  56px
└─────────────────────────────┘
```

**Routes (`routes.html`)**
```
┌─────────────────────────────┐
│ Top navbar                  │  56px
├─────────────────────────────┤
│ Filters section             │  auto
├─────────────────────────────┤
│ Map                         │  400px (--map-height-standard)
├─────────────────────────────┤
│ Route cards (scrollable)    │  auto
├─────────────────────────────┤
│ [bottom nav — fixed]        │  56px
└─────────────────────────────┘
```

**Commute (`commute.html`)**
```
┌─────────────────────────────┐
│ Top navbar                  │  56px
├─────────────────────────────┤
│ Commute cards (stacked)     │  auto, order: 1
├─────────────────────────────┤
│ Map                         │  400px (--map-height-standard)
├─────────────────────────────┤  order: 2
│ [bottom nav — fixed]        │  56px
└─────────────────────────────┘
```

On commute, the cards come before the map on mobile. Use `order-1` / `order-2` Bootstrap utility classes rather than CSS `order` overrides.

**Settings (`settings.html`)**
```
┌─────────────────────────────┐
│ Top navbar                  │  56px
├─────────────────────────────┤
│ User Preferences card       │  full width (col-md-6 → full)
├─────────────────────────────┤
│ Data Management card        │  full width
├─────────────────────────────┤
│ Strava Analysis card        │  full width
├─────────────────────────────┤
│ About card                  │  full width
├─────────────────────────────┤
│ Save / Reset buttons        │  full width
├─────────────────────────────┤
│ [bottom nav — fixed]        │  56px
└─────────────────────────────┘
```

---

## Bottom navigation

The bottom nav replaces the top navbar as the primary navigation on mobile. It is fixed to the bottom of the viewport.

```
┌──────────┬──────────┬──────────┬──────────┐
│  🏠       │  🗺️       │  ⚙️       │          │  56px fixed
│  Home    │  Routes  │  Settings│          │
└──────────┴──────────┴──────────┴──────────┘
```

### Implementation rules

- Height: `--bottom-nav-height: 56px` — use the token, never hardcode
- Shown via `display: flex !important` inside `@media (max-width: 767.98px)` — the `!important` is intentional to override Bootstrap's `.d-md-none`
- The top navbar is hidden on mobile via Bootstrap's `.d-none.d-md-block` classes — do not CSS-hide it separately
- Each nav item: `min-height: 56px`, `padding: var(--space-1) var(--space-2)` (4px 8px), icon + label stacked vertically
- Icon margin below: `var(--space-1)` (4px), label font-size: 11px

### Body padding to prevent content clip

The fixed bottom nav overlaps content without this:

```css
@media (max-width: 767.98px) {
    body { padding-bottom: var(--bottom-nav-height); }   /* 56px */
    main, .container-fluid { padding-bottom: 72px; }     /* 56px + 16px buffer */
}
```

---

## Touch targets

Every interactive element must meet the minimum touch target:

| Element | Desktop min | Mobile min |
|---|---|---|
| Button, link | 44×44px | 48×48px |
| Form input, select | 44px height | 48px height |
| Checkbox, radio | 20×20px with 12px margin | 20×20px with 12px margin |
| Table row | 44px height | 48px height |
| Bottom nav item | — | 56px height (full bar height) |

On mobile, increase all touch targets:

```css
@media (max-width: 767.98px) {
    .btn, button { min-height: 48px; padding: 12px 20px; }
    input, select, textarea { min-height: 48px; font-size: 16px; }  /* 16px prevents iOS zoom */
    .table td, .table th { padding: 14px 12px; }
}
```

The `font-size: 16px` on inputs is required — iOS Safari zooms in on any input with a font size below 16px, breaking the layout.

---

## Map behavior on mobile

Maps shrink from their desktop height to the standard height on mobile:

```css
@media (max-width: 767.98px) {
    .map-container,
    .map-iframe,
    #routes-map,
    #commute-map-container {
        height: var(--map-height-standard);   /* 400px */
        min-height: unset;
    }
}
```

Do not use `!important` to override map heights. If a map is inheriting an inline `style="height: Xpx"` that the media query cannot override, replace the inline style with a CSS class.

---

## Filter layout on mobile

The routes page filter section uses `col-md-3 col-sm-6`, which gives 2-column filter inputs at 576px+ and 4-column at 768px+. On mobile (below 576px) all filter inputs are full-width stacked. The preset buttons use `flex-wrap: wrap` with `flex: 1 1 calc(50% - 0.5rem)` to give a 2-up layout on small screens — do not override this.

---

## Typography on mobile

Do not scale body text down below `14px` on mobile. The current `body { line-height: 1.45 }` is appropriate. Font size reductions should only apply to secondary/meta text (timestamps, labels), not body copy or card content.

---

## Swipe gestures

`static/js/mobile.js` handles swipe detection. The visual indicators (`.swipe-indicator`, `.refresh-indicator`) are defined in `main.css`. On mobile:

- Left/right swipe: navigates between pages in the app's navigation order
- Pull-down: triggers a data refresh
- The swipe indicators use `var(--space-3)` (16px) positioning from the screen edge, not 20px

---

## Responsive breakpoint cheatsheet

```css
/* Single breakpoint tier for this app */
@media (max-width: 767.98px) { /* mobile */ }
@media (min-width: 768px)    { /* tablet + desktop */ }
@media (min-width: 992px)    { /* desktop only — three-column layouts */ }
```

Never use `@media (max-width: 767px)` — it is 0.02px off from Bootstrap's boundary and can cause the bottom nav to flicker at exactly 768px.

---

## What not to do

- Do not create separate mobile-only HTML pages. All pages must work responsively.
- Do not use `display: none` on desktop elements to "create" a mobile layout. Collapse them with Bootstrap column classes instead.
- Do not hardcode the bottom nav height (56px) anywhere except the token definition in `:root`. Reference `var(--bottom-nav-height)` everywhere else.
- Do not override Bootstrap breakpoints. If `col-md-*` doesn't collapse at the right point, check whether the element is actually inside a `.row`.
- Do not set `font-size` below 16px on any `<input>`, `<select>`, or `<textarea>` — iOS Safari will zoom.

---

## Related documents

- [GRID_CONTRACT.md](GRID_CONTRACT.md) — spacing tokens, column layout specs, breakpoint rules
- [UIUX_REDESIGN_STRATEGY.md](../UIUX_REDESIGN_STRATEGY.md) — design principles and page vision
- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) — mobile checklist items for PR review
