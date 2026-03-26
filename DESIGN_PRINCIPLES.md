# Design Principles & Guidelines

**Version:** 2.0  
**Last Updated:** 2026-03-26  
**Status:** Active

---

## Overview

This document establishes the design principles and guidelines for the Strava Commute Analyzer. All new features and modifications must adhere to these principles to ensure a consistent, accessible, and delightful user experience.

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

**Rationale:** Reduces cognitive load, especially for new users.

---

### 3. Clear Visual Hierarchy
**Principle:** Use size, color, and spacing to guide user attention.

**Guidelines:**
- Optimal route: Largest, most prominent (gradient border, elevated shadow)
- Alternative routes: Standard cards with subtle styling
- Typography scale: H1 (2.5rem) → H2 (2rem) → H3 (1.5rem) → Body (1rem)
- Spacing scale: xs (4px) → sm (8px) → md (16px) → lg (24px) → xl (32px)
- Use whitespace generously to separate content groups

**Rationale:** Users should immediately understand what's most important.

---

### 4. Semantic Color System
**Principle:** Colors must have clear, consistent meanings across the interface.

### Color Palette

**Primary Colors:**
- `#667eea` - Primary (actions, links, brand)
- `#764ba2` - Primary Dark (hover states, gradients)

**Semantic Colors (WCAG AA Compliant):**

**Success (Green) - Optimal, Favorable, Positive:**
- `#28a745` - Success (optimal routes, tailwind, favorable conditions)
- `#d4edda` - Success Light (backgrounds, selected states)
- `#155724` - Success Dark (text on light backgrounds)

**Danger (Red) - Unfavorable, Warning, Negative:**
- `#dc3545` - Danger (headwind, unfavorable conditions)
- `#f8d7da` - Danger Light (backgrounds)
- `#721c24` - Danger Dark (text on light backgrounds)

**Warning (Yellow) - Caution, Neutral:**
- `#ffc107` - Warning (neutral conditions, caution)
- `#fff3cd` - Warning Light (backgrounds, temporary highlights)
- `#856404` - Warning Dark (text on light backgrounds)

**Info (Blue) - Informational:**
- `#007bff` - Info (informational elements)
- `#e7f3ff` - Info Light (backgrounds)

**Neutral (Grey) - Secondary, Muted:**
- `#6c757d` - Neutral (secondary text, muted info)
- `#e2e3e5` - Neutral Light (backgrounds)
- `#383d41` - Neutral Dark (text)
- `#808080` - Grey (dimmed/unselected routes)
- `#f0f0f0` - Light Grey (hover states)
- `#f8f9fa` - Background (page background)

### Color Usage Rules

1. **Route States:**
   - Selected: `#d4edda` (green background) - clearly indicates selection
   - Highlighted: `#fff3cd` (yellow background) - temporary highlight
   - Hover: `#f0f0f0` (light grey) - subtle feedback
   - Dimmed: `#808080` at 40% opacity - unselected routes on map

2. **Wind Conditions:**
   - Favorable (Tailwind): Green (`#d4edda` background, `#28a745` border)
   - Unfavorable (Headwind): Red (`#f8d7da` background, `#dc3545` border)
   - Neutral: Grey (`#e2e3e5` background, `#6c757d` border)

3. **Map Routes:**
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
- Destructive action: Red (`#dc3545`)
- Disabled: 50% opacity, no pointer events

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
    background: #667eea;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.2s;
}

.btn-primary:hover {
    background: #764ba2;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}
```

### Card Styles
```css
.card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
    background-color: #d4edda;
    border-left: 4px solid #28a745;
    font-weight: 600;
}

.route-row.highlighted {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
}

.route-row:hover {
    background-color: #f0f0f0;
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