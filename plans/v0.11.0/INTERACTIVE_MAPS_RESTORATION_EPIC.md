# EPIC: Restore Interactive Maps to Web App

**Epic Number:** EPIC-001  
**Priority:** P0-critical  
**Target Version:** v0.11.0 or v0.12.0  
**Status:** Planning  
**Created:** 2026-05-07  

---

## Executive Summary

The web app (v0.10.0) has **NO maps at all** despite having comprehensive Folium-based map generation code in [`src/visualizer.py`](../../src/visualizer.py) (1316 lines). The old CLI version (v0.5.0) had full interactive maps with route comparison, weather overlays, heatmaps, and filtering. This epic restores all map functionality to the web app.

---

## Background

### What Existed Before (v0.5.0 CLI)

The original CLI version had comprehensive interactive maps powered by Folium:

1. **Full Interactive Route Comparison Maps**
   - Multiple basemap layers (OpenStreetMap, Satellite, CartoDB Positron)
   - Color-coded route polylines with opacity control
   - Click-to-zoom functionality with route bounds
   - Route filtering by direction (to work, from work)
   - Plus route filtering (routes with extra distance)
   - Interactive route selection with fade effects

2. **Location Markers**
   - Home marker (green house icon) with activity count
   - Work marker (blue building icon) with activity count
   - Custom Font Awesome icons

3. **Weather Display Overlays**
   - Current conditions display (temperature, wind, precipitation)
   - Wind direction with cardinal directions and degrees
   - Unit system support (metric/imperial)
   - Real-time weather updates
   - Positioned overlay on map

4. **Heatmap Layers**
   - Frequency-based heatmaps showing most-used paths
   - Gradient visualization of route popularity
   - Toggle-able overlay layer

5. **Route Statistics Popups**
   - Distance, duration, elevation gain
   - Frequency of use
   - Average speed
   - Plus route indicator
   - Human-readable route names

6. **Long Ride Recommendations**
   - Click map to find nearby long rides
   - Preview maps in recommendation cards
   - Distance and difficulty color coding
   - Interactive route discovery

### What's Missing Now (v0.10.0 Web App)

**Complete absence of maps across all pages:**

1. **Route Detail Page** ([`static/route-detail.html:169`](../../static/route-detail.html#L169))
   - Explicit "Coming Soon" placeholder message
   - No route visualization
   - No elevation profile
   - No detailed statistics display

2. **Commute Page** ([`app/templates/commute/index.html`](../../app/templates/commute/index.html))
   - No recommended route visualization
   - No alternative route comparison
   - No weather overlay for route conditions
   - Text-only recommendations

3. **Planner Page** ([`app/templates/planner/index.html`](../../app/templates/planner/index.html))
   - No long ride route display
   - No map-based route selection
   - No visual distance/difficulty indicators
   - No interactive route discovery

4. **Dashboard** (assumed missing based on pattern)
   - No overview map of all routes
   - No heatmap of frequently used paths
   - No quick route selection interface

---

## Technical Assets Available

### Existing Code ([`src/visualizer.py`](../../src/visualizer.py))

The `RouteVisualizer` class (1316 lines) provides:

- `create_base_map()` - Multi-layer basemap with zoom control
- `add_route_layer()` - Route polylines with popups and tooltips
- `add_location_markers()` - Home/work markers with icons
- `add_weather_display()` - Current conditions overlay
- `add_heatmap_layer()` - Frequency-based heatmaps
- `add_interactive_controls()` - JavaScript for filtering and interaction
- `create_long_ride_map()` - Long ride visualization
- `save_map()` - Export to HTML

### Data Already Available

- Route coordinates (polylines)
- Home/work locations with activity counts
- Route statistics (distance, duration, elevation, frequency)
- Weather data (temperature, wind, precipitation)
- Route grouping and similarity data
- Long ride recommendations with coordinates

### Dependencies Already Installed

- `folium` - Interactive map generation
- `folium.plugins` - Heatmap and advanced features
- `geopy` - Distance calculations
- Font Awesome icons via CDN

---

## Implementation Strategy

### Phase 1: Quick Win with Folium (Recommended for v0.11.0)

**Approach:** Server-side map generation, embed in templates

**Advantages:**
- Leverage existing [`RouteVisualizer`](../../src/visualizer.py) class (1316 lines of tested code)
- Minimal JavaScript required
- Works like CLI version (proven approach)
- Fast implementation (1-2 weeks)

**Implementation:**
1. Create map generation endpoints/functions
2. Embed Folium HTML in Jinja2 templates
3. Add lazy loading for performance
4. Reuse existing map generation logic

**Disadvantages:**
- Large HTML payload (mitigate with lazy loading)
- Less dynamic than client-side rendering
- Full page reload for filter changes

### Phase 2: Future Enhancement with Client-Side Leaflet.js (v0.12.0+)

**Approach:** Client-side rendering with API endpoints

**Advantages:**
- Real-time filtering without page reload
- Smaller initial payload
- More interactive user experience
- Better mobile performance

**Implementation:**
1. Create route data API endpoints
2. Build JavaScript map components
3. Implement client-side filtering
4. Add real-time updates

**Disadvantages:**
- More JavaScript code to write
- Requires API endpoint development
- More complex state management

---

## Stories Breakdown

### Story 1: Route Detail Page Maps (P0-critical)
**Estimate:** 3 days  
**Dependencies:** None

**Acceptance Criteria:**
- [ ] Single route polyline displayed on map
- [ ] Start/end markers with labels
- [ ] Route statistics popup (distance, duration, elevation)
- [ ] Multiple basemap layers (OSM, Satellite, CartoDB)
- [ ] Replace "Coming Soon" placeholder at [`static/route-detail.html:169`](../../static/route-detail.html#L169)
- [ ] Mobile-responsive map display (320px viewport)
- [ ] Map loads in <2 seconds

**Technical Notes:**
- Use `RouteVisualizer.create_base_map()` and `add_route_layer()`
- Embed Folium HTML in route detail template
- Pass route data from backend to template

---

### Story 2: Commute Page Maps (P0-critical)
**Estimate:** 5 days  
**Dependencies:** Story 1

**Acceptance Criteria:**
- [ ] Recommended route highlighted (optimal color)
- [ ] Alternative routes in different colors
- [ ] Weather overlay showing current conditions
- [ ] Home/work location markers
- [ ] Interactive route comparison (click to zoom)
- [ ] Route filtering by direction
- [ ] Route statistics popups for all routes
- [ ] Mobile-responsive with touch targets ≥44x44px

**Technical Notes:**
- Use `RouteVisualizer.add_weather_display()`
- Use `RouteVisualizer.add_location_markers()`
- Add JavaScript for route interaction
- Color-code routes by score/optimality

---

### Story 3: Planner Page Maps (P1-high)
**Estimate:** 5 days  
**Dependencies:** Story 1, Story 2

**Acceptance Criteria:**
- [ ] All long ride routes displayed on map
- [ ] Color-coded by distance/difficulty
- [ ] Filter by day/weather conditions
- [ ] Click route to see ride details
- [ ] Preview maps in recommendation cards
- [ ] Route discovery (click map to find nearby rides)
- [ ] Distance circles for visual reference
- [ ] Mobile-responsive with progressive disclosure

**Technical Notes:**
- Use `RouteVisualizer.create_long_ride_map()`
- Implement client-side filtering for performance
- Add route clustering for dense areas
- Show distance/elevation in tooltips

---

### Story 4: Dashboard Overview Map (P1-high)
**Estimate:** 4 days  
**Dependencies:** Story 2

**Acceptance Criteria:**
- [ ] All routes displayed at once
- [ ] Heatmap of frequently used paths
- [ ] Home/work markers
- [ ] Quick route selection (click to navigate)
- [ ] Route statistics summary
- [ ] Filter by direction, frequency, date range
- [ ] Toggle heatmap layer on/off
- [ ] Performance optimized for 50+ routes

**Technical Notes:**
- Use `RouteVisualizer.add_heatmap_layer()`
- Implement route clustering for performance
- Add layer control for heatmap toggle
- Cache map generation for performance

---

### Story 5: Interactive Features (P2-medium)
**Estimate:** 3 days  
**Dependencies:** Stories 1-4

**Acceptance Criteria:**
- [ ] Route filtering (direction, distance, weather)
- [ ] Route interaction (click to zoom, hover for stats)
- [ ] Route comparison side-by-side
- [ ] Fade unselected routes on click
- [ ] Keyboard navigation support
- [ ] Screen reader compatibility
- [ ] Touch gesture support (pinch zoom, pan)

**Technical Notes:**
- Add JavaScript event handlers
- Implement ARIA labels for accessibility
- Use CSS transitions for smooth interactions
- Test on real mobile devices

---

### Story 6: Weather Integration (P2-medium)
**Estimate:** 3 days  
**Dependencies:** Story 2

**Acceptance Criteria:**
- [ ] Current conditions overlay
- [ ] Wind direction arrows on map
- [ ] Temperature zones (color-coded)
- [ ] Precipitation forecast overlay
- [ ] Weather icons and visual indicators
- [ ] Unit system support (metric/imperial)
- [ ] Real-time weather updates

**Technical Notes:**
- Reuse existing weather fetcher
- Add wind arrow SVG overlays
- Implement temperature gradient layer
- Cache weather data for performance

---

### Story 7: Advanced Features (P3-low)
**Estimate:** 5 days  
**Dependencies:** Stories 1-6

**Acceptance Criteria:**
- [ ] Long ride discovery (click map to find nearby rides)
- [ ] Elevation profiles with interactive charts
- [ ] Route analytics (usage heatmaps, speed zones)
- [ ] Route comparison with elevation overlay
- [ ] Export map as image/PDF
- [ ] Share map link with filters applied
- [ ] Custom route drawing tool

**Technical Notes:**
- Use Chart.js for elevation profiles
- Implement URL parameter encoding for sharing
- Add canvas export for image generation
- Consider Leaflet.draw for custom routes

---

## Technical Requirements

### Code Reuse
- **Primary:** [`src/visualizer.py`](../../src/visualizer.py) - `RouteVisualizer` class (1316 lines)
- **Supporting:** [`src/route_analyzer.py`](../../src/route_analyzer.py) - Route data structures
- **Supporting:** [`src/location_finder.py`](../../src/location_finder.py) - Location data
- **Supporting:** [`src/route_namer.py`](../../src/route_namer.py) - Human-readable names

### Data Requirements
- Route coordinates (already available)
- Home/work locations (already available)
- Route statistics (already available)
- Weather data (already available via weather fetcher)
- Route grouping data (already available)

### Dependencies
- `folium` - Already installed
- `folium.plugins` - Already installed
- `geopy` - Already installed
- Font Awesome - Via CDN (already used)
- Leaflet.js - Included with Folium

### Performance Targets
- Map load time: <2 seconds
- Route rendering: <500ms for 50 routes
- Filter updates: <100ms
- Mobile performance: 60fps scrolling/panning
- Memory usage: <50MB additional

---

## Success Criteria

### Functional Requirements
- [ ] Maps visible on all major pages (route detail, commute, planner, dashboard)
- [ ] Interactive route selection and filtering working
- [ ] Weather overlays functional and accurate
- [ ] Heatmap layer toggleable and performant
- [ ] All existing map features from v0.5.0 restored

### Performance Requirements
- [ ] Map load time <2 seconds on 3G connection
- [ ] Smooth 60fps panning/zooming on mobile
- [ ] Filter updates <100ms response time
- [ ] Memory usage <50MB additional overhead

### Quality Requirements
- [ ] Mobile-responsive (320px viewport minimum)
- [ ] Touch targets ≥44x44px with 8px spacing
- [ ] WCAG AA accessibility compliance
- [ ] Keyboard navigation support
- [ ] Screen reader compatibility
- [ ] Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

### User Experience Requirements
- [ ] Intuitive map controls
- [ ] Clear visual hierarchy
- [ ] Consistent color coding across pages
- [ ] Helpful tooltips and popups
- [ ] Progressive disclosure of details
- [ ] No "Coming Soon" placeholders

---

## Dependencies

**None** - All code and data already exists:
- [`src/visualizer.py`](../../src/visualizer.py) has all map generation logic
- Route data available in route analyzer
- Weather data available via weather fetcher
- Location data available in location finder
- Folium library already installed

---

## Risks & Mitigation

### Risk 1: Large HTML Payload with Folium
**Impact:** High  
**Probability:** High  
**Mitigation:**
- Implement lazy loading for maps
- Generate maps on-demand, not on page load
- Cache generated maps server-side
- Consider pagination for route lists
- Use map clustering for dense areas

### Risk 2: Mobile Performance
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Test on real devices (iPhone SE, Android mid-range)
- Implement progressive enhancement
- Reduce route complexity for mobile
- Use simpler basemap on mobile
- Add loading indicators

### Risk 3: Browser Compatibility
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Test on Chrome, Firefox, Safari, Edge
- Use Folium's built-in compatibility layer
- Provide fallback for older browsers
- Document minimum browser versions

### Risk 4: Weather API Rate Limits
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Cache weather data aggressively
- Use existing weather fetcher with rate limiting
- Degrade gracefully if weather unavailable
- Show cached data with timestamp

---

## Timeline Estimate

### Phase 1: Folium Implementation (v0.11.0)
- **Week 1:** Story 1 (Route Detail) + Story 2 start
- **Week 2:** Story 2 (Commute) + Story 3 start
- **Week 3:** Story 3 (Planner) + Story 4 (Dashboard)
- **Week 4:** Story 5 (Interactive Features) + QA
- **Total:** 4 weeks

### Phase 2: Client-Side Enhancement (v0.12.0+)
- **Week 5-6:** API endpoints + Leaflet.js integration
- **Week 7:** Story 6 (Weather Integration)
- **Week 8:** Story 7 (Advanced Features) + QA
- **Total:** 4 weeks

**Overall Timeline:** 8 weeks (2 months)

---

## Related Issues

- #169 - "Coming Soon" placeholder on route detail page
- #211 - UAT/QA Test Findings - Production Readiness Gaps
- #144 - EPIC: Personal Web Platform Migration (v3.0.0)
- #145 - EPIC: Weather Dashboard & Forecast Integration

---

## Notes

- This epic restores functionality that already existed in v0.5.0
- All necessary code is in [`src/visualizer.py`](../../src/visualizer.py) (1316 lines)
- Phase 1 (Folium) is recommended for v0.11.0 as quick win
- Phase 2 (Leaflet.js) can be deferred to v0.12.0+ for enhancement
- Mobile-first design is mandatory (320px viewport)
- WCAG AA accessibility compliance required
- Test on real devices, not just emulators

---

**Created:** 2026-05-07  
**Last Updated:** 2026-05-07  
**Epic Owner:** TBD  
**Status:** Planning