# Design Principles & Guidelines

**Version:** 2.2
**Last Updated:** 2026-07-05
**Status:** Active

---

## Overview

This document establishes the design principles and guidelines for the Strava Commute Analyzer. All new features and modifications must adhere to these principles to ensure a consistent, accessible, and delightful user experience.

---

## Brand Identity — Fair Weather

**Adopted:** 2026-07-05. Full spec, rationale, and screen mockups: [`docs/designs/FAIR_WEATHER_BRAND_BOOK.md`](../../docs/designs/FAIR_WEATHER_BRAND_BOOK.md).

The app's visual identity is **Fair Weather** — built around the one decision the product actually exists to support: *is today a good day to ride, and which route fits it.* It replaces the previous unstyled Bootstrap defaults (indigo/purple gradient, system font stack, `bi-*` icons with no supporting type or color system).

**Mark:** a circle with eight radiating ticks — reads simultaneously as a wheel hub and a sun, since the product sits at exactly that intersection. Defined once as an SVG using `stroke="currentColor"` so it can be recolored per context (navbar, favicon, PWA icon) from one source. Below 24px, drop the diagonal rays and keep only the circle plus the four cardinal ticks.

**Wordmark:** "Ride" in ink, "Optimizer" in the cobalt accent, set in the display face. Tagline: *"Know before you go."*

**Typography:**
- Display (headlines, decision copy, CTAs): a geometric sans — `"Century Gothic", "Avenir Next", "Futura", -apple-system, sans-serif`.
- Body (everything read at length): the existing system UI stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
- No separate mono face in-product. Numerals that line up in a column (temperature, distance, elevation, match score) use `font-variant-numeric: tabular-nums` on the body/display face instead.

**Color — two grounds, not one inverted into the other.** Day is an overcast-bright sky; Night is a clear one. Accents shift in brightness between modes to stay correct on each ground, not just recolored. This supersedes the Primary Colors and Semantic Colors tables in §4 below, which are updated to these values.

| Role | Day | Night |
|---|---|---|
| Ground | `#F3F6F7` | `#0B1620` |
| Surface (cards) | `#FFFFFF` | `#122232` |
| Surface 2 | `#EDF2F4` | `#16283A` |
| Ink (text) | `#0F2233` | `#EAF0F3` |
| Ink soft (secondary text) | `#5B7686` | `#8FA6B4` |
| Line (borders/dividers) | `#DCE3E6` | `#223243` |
| Accent — cobalt (brand, structure, links, info) | `#0B6FA6` | `#4FB3E8` |
| Accent — coral (reserved for the single most important CTA/badge per screen) | `#F2662D` | `#FF8A57` |
| Good fit / favorable / success | `#3E8E63` | `#57B384` |
| Caution / neutral | `#C98A1D` | `#E0A63E` |
| Poor fit / unfavorable / danger | `#C4483A` | `#E2695C` |

**Rule:** coral is spent in exactly one place per screen — the primary call to action or the day's headline decision badge. Cobalt carries everything structural (nav, links, accent borders, informational data). Diluting coral into badges, borders, and hover states the way the old indigo gradient was overused is the failure mode this palette is designed to avoid.

---

## Core Design Philosophy

### 1. Mobile-First Approach
**Principle:** Design for mobile devices first, then enhance for larger screens.

**Guidelines:**
- Start with 320px viewport (iPhone SE)
- Use responsive breakpoints: mobile (<768px), tablet (768-1024px), desktop (>1024px)
- Touch targets minimum 44x44px (Apple HIG standard)
- Stack content vertically on mobile, side-by-side on desktop
- Test on real devices, not just browser emulators

**Rationale:** Cyclists check routes on-the-go. Mobile experience is critical.

---

### 2. Progressive Disclosure
**Principle:** Show essential information first, reveal details on demand.

**Guidelines:**
- Display 3 primary metrics by default (duration, distance, score)
- Use "Show More" buttons for additional details
- Collapse secondary information by default
- Provide clear visual hierarchy (primary → secondary → tertiary)
- Avoid information overload on initial view
- **Time-urgency ordering:** When a page contains both time-sensitive actionable content and lower-urgency planning/context content, the time-sensitive content must appear first in DOM source order (so mobile stacking is correct without CSS overrides). Example: same-day commute windows before a 7-day forecast; hero decision card before supporting map context.
- **Teaser before collapse:** Any collapsible section containing useful secondary data must include a visible teaser or count in the collapsed state so users know expandable content exists. Never render a bare chevron with no accompanying text.
- **Weather cards show wind and precipitation whenever available:** Any card or hourly cell displaying weather must surface wind speed/direction and precipitation chance alongside temperature, not temperature alone — both affect ride decisions as much as temperature does. In a single-instance card (a hero decision card, a current-conditions summary) show the value even when it's zero, since confirming "0% chance of rain" is itself useful information. In a repeated list (an hourly forecast strip), omit a field for a given cell only when its value is trivial/zero, to avoid clutter across many repeated cells — do not omit it simply because it's unavailable from a lower-priority data source without checking a fallback first.

> **Field note (v0.17.0 Design Review):** Findings PLACE-WEATHER-1 and PLACE-DASH-1 confirmed two P1 ordering violations where planning-horizon content preceded same-day actionable data. Finding ID-WX-1 independently corroborated the Weather page ordering problem. Findings DISC-DASH-1, DISC-DASH-2, and ID-DASH-3 documented three collapse toggles with no teaser content across the Dashboard alone.

**Rationale:** Reduces cognitive load, especially for new users.

---

### 3. Clear Visual Hierarchy
**Principle:** Use size, color, and spacing to guide user attention.

**Guidelines:**
- Optimal route: Largest, most prominent (gradient border, elevated shadow)
- Alternative routes: Standard cards with subtle styling
- Typography scale: H1 (2.5rem) → H2 (2rem) → H3 (1.5rem) → Body (1rem); every page must have exactly one `<h1>` as its first visible heading
- Spacing scale: xs (4px) → sm (8px) → md (16px) → lg (24px) → xl (32px)
- Use whitespace generously to separate content groups
- **Card column ratios:** On two-column layouts, the column containing primary decision data or the route list must receive equal or greater Bootstrap column width than the column containing a map or supporting context (minimum `col-lg-6` for the primary data column). Maps are confirmatory, not primary.
- **Map + controls placed side-by-side on desktop:** On `lg` (≥1024px) and wider viewports, controls or lists that operate on a map (route-generation controls, filters, coverage stats, a route list) must be placed in a column beside the map, not stacked above or below it — stacking wastes the vertical real estate a wide viewport provides and pushes the primary action below the fold. Use `col-lg-4`/`col-lg-8` (compact controls / map) or the column-ratio rule above (data-dense list / map) depending on what the side column contains. Below `lg`, stack per the Mobile-First principle — controls or the list above the map, since there's no width to spare.
- **Secondary metrics demoted:** Metrics that are social signals (popularity/uses), administrative counts (pipeline health), or derived redundancies (near-zero percentages) must not appear in the same visual tier (same CSS class, same card slot, same grid cell) as primary decision metrics (distance, duration, score).

> **Field note (v0.17.0 Design Review):** Findings PLACE-DASH-2, PLACE-ROUTES-2, and PLACE-DETAIL-2 identified three pages where the map column received more Bootstrap columns than the decision/data column. Finding ID-RDTL-2 documented the "Uses" popularity metric sharing equal visual weight with Distance, Duration, and Elevation in the Route Detail primary grid. CP-4 (Information Density) documented this secondary-at-primary-weight pattern recurring across Dashboard, Reports, Route Detail, and Explore.

> **Field note (v2.2 — Fair Weather):** The map + controls side-by-side rule formalizes a recommendation already made ad hoc in #367 (Explore: "two-column layout on desktop: generation controls left `col-lg-4` / map right `col-lg-8`"). It also applies to #365 (Routes Library column ratio) and should be checked against Route Detail's existing `col-lg-5`/`col-lg-7` split (`route-detail.html`), which already follows this pattern and can serve as the reference implementation.

**Rationale:** Users should immediately understand what's most important.

---

### 4. Semantic Color System
**Principle:** Colors must have clear, consistent meanings across the interface.

### Color Palette

**As of v2.2, sourced from the Fair Weather brand (see Brand Identity section above for full Day/Night table).** Primary Colors and Semantic Colors below give the flattened reference for implementers; the Day/Night table above is authoritative when the two disagree.

**Primary Colors:**
- `#0B6FA6` (Day) / `#4FB3E8` (Night) - Cobalt (structure, links, brand, informational)
- `#F2662D` (Day) / `#FF8A57` (Night) - Coral (reserved for the single primary CTA/badge per screen — do not use for structural elements)

**Semantic Colors (WCAG AA Compliant):**

**Success (Green) - Optimal, Favorable, Good fit:**
- `#3E8E63` (Day) / `#57B384` (Night) - Success (optimal routes, tailwind, favorable conditions)
- `rgba(62,142,99,0.13)` - Success Light (backgrounds, selected states; use `rgba(87,179,132,0.16)` on Night surfaces)
- `#1F5C3F` - Success Dark (text on light backgrounds)

**Danger (Red) - Unfavorable, Poor fit:**
- `#C4483A` (Day) / `#E2695C` (Night) - Danger (headwind, unfavorable conditions)
- `rgba(196,72,58,0.12)` - Danger Light (backgrounds)
- `#7A2A21` - Danger Dark (text on light backgrounds)

**Warning (Amber) - Caution, Neutral:**
- `#C98A1D` (Day) / `#E0A63E` (Night) - Warning (neutral conditions, caution — e.g. an exposed climb, rising wind)
- `rgba(201,138,29,0.15)` - Warning Light (backgrounds, temporary highlights)
- `#6E4C0F` - Warning Dark (text on light backgrounds)

**Info (Blue) - Informational:**
- Use the Cobalt primary above. A separate Info color is retired in v2.2 — cobalt already carries this role, and a third blue alongside it diluted the palette.

**Neutral (Grey) - Secondary, Muted:**
- `#5B7686` (Day) / `#8FA6B4` (Night) - Ink soft (secondary text, muted info)
- `#DCE3E6` (Day) / `#223243` (Night) - Line (borders, dividers, hover backgrounds)
- `#808080` - Grey (dimmed/unselected routes on map — unchanged, functional not brand color)
- `#F3F6F7` (Day) / `#0B1620` (Night) - Ground (page background)

### Color Usage Rules

1. **Route States:**
   - Selected: `rgba(62,142,99,0.13)` (success-tinted background) - clearly indicates selection
   - Highlighted: `rgba(201,138,29,0.15)` (warning-tinted background) - temporary highlight
   - Hover: Line color (`#DCE3E6` Day / `#223243` Night) - subtle feedback
   - Dimmed: `#808080` at 40% opacity - unselected routes on map

2. **Wind Conditions:**
   - Favorable (Tailwind): Success-tinted background, success border
   - Unfavorable (Headwind): Danger-tinted background, danger border
   - Neutral: Line-colored background, ink-soft border

3. **Map Routes:** Functional categorical palette for showing multiple simultaneous route overlays — kept constant across Day/Night since it's a data-encoding palette, not a brand one:
   - Route 1 (Primary): `#28a745` (green)
   - Route 2: `#dc3545` (red)
   - Route 3: `#007bff` (blue)
   - Route 4: `#ffc107` (yellow)
   - Unselected: `#808080` at 40% opacity

4. **Accessibility:**
   - All color combinations must meet WCAG AA contrast ratio (4.5:1 for text)
   - Never rely on color alone to convey information
   - Provide text labels, icons, or patterns as alternatives

**Rationale:** Consistent color meanings reduce cognitive load and improve usability.

---

### 5. Touch-Optimized Interactions
**Principle:** All interactions must work seamlessly on touch devices.

**Guidelines:**
- Replace hover states with tap interactions
- Minimum touch target: 44x44px
- Add 8px spacing between touch targets
- Provide visual feedback on tap (scale, color change)
- Use tap-to-show for tooltips (auto-hide after 3s)
- Support common gestures (swipe, pinch-to-zoom)
- Add loading indicators for async actions

**Rationale:** Touch devices don't support hover; interactions must be explicit.

---

### 6. Map Clarity & Readability
**Principle:** Maps must be clean, crisp, and easy to interpret.

**Guidelines:**

**Route Styling:**
- Selected routes: 6px stroke, 100% opacity, z-index 1000
- Highlighted routes: 5px stroke, 90% opacity, z-index 900
- Default routes: 4px stroke, 80% opacity, z-index 500
- Dimmed routes: 3px stroke, 40% opacity, grey color, z-index 100

**Visual Enhancements:**
- Add subtle drop shadow to routes for depth: `drop-shadow(0 2px 4px rgba(0,0,0,0.3))`
- Use smooth transitions (0.3s) for state changes
- Store original colors in `data-originalStroke` attribute
- Maintain color consistency with semantic color system

**Route Direction Indicators:**
- Display directional arrows on polylines to show route direction
- Arrow placement varies by zoom level:
  - **Zoomed out (city view):** Single arrow at midpoint of route
  - **Medium zoom (neighborhood view):** Arrows every 25% of route length
  - **Zoomed in (street view):** Arrows every 10% of route length, animated on hover
- Arrow styling:
  - Size: 12px (zoomed out) → 16px (medium) → 20px (zoomed in)
  - Color: Matches route color with 20% darker shade for contrast
  - Shape: Filled triangle pointing in direction of travel
  - Opacity: 80% (default), 100% (selected/highlighted)
- Direction labels:
  - Show "To Work" or "To Home" label at route start point
  - Label styling: Small badge with route color, white text
  - Only visible at medium/high zoom levels
  - Position: Offset 10px from route start to avoid overlap
- Implementation considerations:
  - Use Leaflet decorator plugin or custom SVG markers
  - Update arrow density dynamically on zoom change
  - Ensure arrows don't clutter map at any zoom level
  - Arrows should be clickable (same behavior as route)

**Interaction:**
- Click route to select (green highlight)
- Ctrl/Cmd+Click for multi-select
- Click again to deselect
- Clear visual feedback for all states
- Hover over route shows animated direction flow (optional enhancement)

**Rationale:** Clear map visualization is essential for route comparison. Direction indicators help users quickly understand route flow, especially when comparing "to work" vs "to home" routes that may overlap.

---

### 7. Discoverable Features
**Principle:** Important features should be obvious, not hidden.

**Guidelines:**
- Add visual hints for hidden features (badges, tooltips, icons)
- Provide first-time user onboarding (welcome modal, tour)
- Use contextual help ("?" icons, inline explanations)
- Show keyboard shortcuts in UI (e.g., "Ctrl+Click to select multiple")
- Add examples in empty states
- Use progressive disclosure for advanced features
- **Workflow sequencing:** Multi-step workflows (where step N is a prerequisite for step N+1) must have visible step numbers, a numbered header, or progressive button enablement. A button that will fail silently without a preceding action must be disabled with a visible explanation of what is needed to enable it.
- **Jargon-free first use:** Domain-specific or subculture terms (e.g. "Squadrats", "Squadratinhos") that are not part of general cycling vocabulary must have an in-page definition — a one-line explainer, tooltip, or help popover — present on first render, not hidden behind an additional interaction.
- **Interactive elements visually distinct:** Elements with `cursor: pointer` or click/tap handlers must be visually distinguishable from static content. Touch devices receive no hover affordance; labels, visible borders, or icons must convey interactivity without hover.
- **Post-action navigation hints:** After a user completes a save/create action that produces an artifact visible on another page, show a toast or inline link directing them to where the result can be found.

> **Field note (v0.17.0 Design Review):** Findings DISC-EXPLORE-1 (P1) and DISC-EXPLORE-2 (P1) documented that the Explore page's primary task (generating a coverage route) is not completable by a new user without guessing due to absent jargon definitions and an unsequenced multi-step workflow. DISC-SETTINGS-1 found the same sequencing gap for the Strava fetch → analyze two-step pipeline. DISC-ROUTES-1 documented the route-compare feature being invisible on mobile due to a label-free checkbox.

**Rationale:** Users shouldn't have to guess how to use features.

---

### 8. Performance & Responsiveness
**Principle:** Interface must feel fast and responsive.

**Guidelines:**
- Use CSS transitions (0.2-0.3s) for smooth state changes
- Show loading indicators for operations >500ms
- Implement optimistic UI updates where possible
- Lazy load images and heavy content
- Cache API responses appropriately
- Minimize layout shifts (CLS)

**Rationale:** Perceived performance is as important as actual performance.

---

### 9. Accessibility First
**Principle:** Design for all users, including those with disabilities.

**Guidelines:**
- Support keyboard navigation (Tab, Enter, Escape, Arrow keys)
- Provide ARIA labels for screen readers
- Ensure WCAG AA contrast ratios (4.5:1 for text, 3:1 for UI)
- Use semantic HTML elements
- Provide text alternatives for visual content
- Support browser zoom up to 200%
- Test with screen readers (VoiceOver, NVDA)

**Rationale:** Accessibility is not optional; it's a fundamental requirement.

---

### 10. Consistent Patterns
**Principle:** Use consistent UI patterns throughout the application.

**Guidelines:**

**Buttons:**
- Primary action: Solid color (`#667eea`)
- Secondary action: Outline style
- Destructive action: Red (`#dc3545`) with `btn-danger` or `btn-outline-danger` styling; must be accompanied by a confirmation dialog (`confirm()` or a Bootstrap confirmation popover) before executing irreversible operations
- Disabled: 50% opacity, no pointer events
- **Unit system applied globally:** Any label, static string, slider range, or stat header that displays a measurement (distance, temperature, speed) must read the user's unit preference from `window.getUnitSystem()` / `window.getDistanceUnit()` on page load. Hard-coded unit strings (e.g. `"Miles"`, `"°F"`, `"km"` in HTML) are not permitted.

> **Field note (v0.17.0 Design Review):** Finding DISC-EXPLORE-5 documented the "Clear Cache" destructive action on Explore using identical button styling to the safe "Load Coverage" action, with no confirmation. Findings DISC-SETTINGS-3, DISC-REPORTS-4, and DISC-EXPLORE-3 documented three separate pages where unit-system preference was not applied to measurement labels, each independently found by the Discoverability reviewer.

**Cards:**
- Border radius: 10px
- Shadow: `0 2px 4px rgba(0,0,0,0.1)`
- Padding: 20px
- Margin bottom: 20px

**Forms:**
- Label above input
- Required fields marked with asterisk
- Validation messages below input
- Error state: Red border + message

**Modals:**
- Centered on screen
- Backdrop: `rgba(0,0,0,0.5)`
- Close button in top-right
- Escape key to close

**Tables:**
- Zebra striping for readability
- Sticky header on scroll
- Hover state on rows
- Responsive: horizontal scroll on mobile

**Rationale:** Consistency reduces learning curve and improves usability.

---

## Implementation Checklist

When implementing new features or modifying existing ones, ensure:

- [ ] Mobile-first responsive design (test on 320px viewport)
- [ ] Touch targets ≥44x44px with 8px spacing
- [ ] Semantic colors used correctly (green=good, red=bad, yellow=caution)
- [ ] WCAG AA contrast ratios met (4.5:1 for text)
- [ ] Progressive disclosure for complex information
- [ ] Clear visual hierarchy (size, color, spacing)
- [ ] Smooth transitions (0.2-0.3s) for state changes
- [ ] Loading indicators for async operations
- [ ] Keyboard navigation support
- [ ] Screen reader compatibility (ARIA labels)
- [ ] Feature discoverability (hints, tooltips, onboarding)
- [ ] Map routes have clear visual states (selected, dimmed, default)
- [ ] Map routes show direction indicators at appropriate zoom levels
- [ ] Direction arrows are visible and don't clutter the map
- [ ] Consistent UI patterns (buttons, cards, forms, modals)
- [ ] Performance optimized (lazy loading, caching)
- [ ] Tested on real devices (iOS, Android)

---

## Design Review Process

Before merging UI/UX changes:

1. **Self-Review:**
   - Check against design principles
   - Test on mobile device
   - Verify color contrast
   - Test keyboard navigation

2. **Peer Review:**
   - Another developer reviews code
   - Designer reviews visual implementation
   - Product owner reviews functionality

3. **User Testing:**
   - Test with 3-5 users
   - Gather feedback on usability
   - Iterate based on findings

4. **Accessibility Audit:**
   - Run automated tools (axe, Lighthouse)
   - Manual screen reader testing
   - Keyboard navigation testing

---

## Common Patterns Library

### Button Styles
```css
.btn-primary {
    background: var(--accent); /* #0B6FA6 Day / #4FB3E8 Night */
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 999px;
    font-weight: 700;
    transition: all 0.2s;
}

.btn-primary:hover {
    filter: brightness(0.92);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(11, 111, 166, 0.3);
}

/* Reserve for exactly one primary CTA/badge per screen — see Brand Identity */
.btn-cta {
    background: var(--accent-warm); /* #F2662D Day / #FF8A57 Night */
    color: white;
    border-radius: 999px;
}
```

### Card Styles
```css
.card {
    background: var(--surface); /* #FFFFFF Day / #122232 Night */
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    padding: 20px;
    margin-bottom: 20px;
    transition: all 0.2s;
}

.card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}
```

### Route State Styles
```css
.route-row.selected {
    background-color: rgba(62,142,99,0.13); /* success-tinted, both modes via var(--success) */
    border-left: 4px solid var(--success);
    font-weight: 600;
}

.route-row.highlighted {
    background-color: rgba(201,138,29,0.15); /* warning-tinted */
    border-left: 4px solid var(--warning);
}

.route-row:hover {
    background-color: var(--line);
    transform: translateX(4px);
}
```

---

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Material Design](https://material.io/design)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.1/)
- [Contrast Checker](https://webaim.org/resources/contrastchecker/)

---

## Version History

- **v2.2** (2026-07-05): Fair Weather brand identity adopted — new Brand Identity section (mark, wordmark, type, tagline); Primary/Semantic Colors in §4 replaced with Day/Night cobalt/coral tokens (full spec: [`docs/designs/FAIR_WEATHER_BRAND_BOOK.md`](../../docs/designs/FAIR_WEATHER_BRAND_BOOK.md)); §2 new guideline that weather cards show wind and precipitation alongside temperature whenever meaningful; §3 new guideline that map controls/lists sit beside the map on desktop (`lg`+), not stacked above or below it, formalizing prior ad hoc recommendations in #365 and #367; Common Patterns Library CSS snippets updated to the new tokens and 999px/16px shape language.
- **v2.1** (2026-07-04): Field notes and extended guidelines added from v0.17.0 Design Review (Epic #352). New sub-guidelines added to §2 (time-urgency ordering, teaser before collapse), §3 (card column ratios, secondary metrics demoted), §7 (workflow sequencing, jargon-free first use, interactive elements visually distinct, post-action navigation hints), §10 (destructive action confirmation, unit system applied globally).
- **v2.0** (2026-03-26): Comprehensive design system with mobile-first approach
- **v1.0** (2024): Initial design guidelines

---

## Questions?

If you're unsure about how to apply these principles to a specific feature, ask:
1. Is this mobile-friendly?
2. Are the colors semantically correct?
3. Is the feature discoverable?
4. Does it meet accessibility standards?
5. Is it consistent with existing patterns?

When in doubt, refer to this document or consult with the design team.