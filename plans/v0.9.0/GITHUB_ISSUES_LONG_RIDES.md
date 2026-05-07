# GitHub Issues for Long Rides Feature (v2.4.0)

**Epic:** #57 - Long Rides Analysis & Recommendations  
**Created:** 2026-03-29  
**Based on:** [`LONG_RIDES_IMPLEMENTATION_PLAN.md`](LONG_RIDES_IMPLEMENTATION_PLAN.md) + [`LONG_RIDES_PEER_REVIEW.md`](LONG_RIDES_PEER_REVIEW.md)

---

## Issue Creation Commands

Run these commands to create all issues:

```bash
# Make script executable
chmod +x plans/v2.4.0/create_long_rides_issues.sh

# Create all issues
./plans/v2.4.0/create_long_rides_issues.sh
```

---

## Epic Issue (Already Exists)

### #57 - 🎯 EPIC: Long Rides Analysis & Recommendations
**Status:** Open  
**Priority:** P1-high  
**Labels:** epic, P1-high, feature

**Description:**
Implement complete long rides feature with statistics, visualization, and interactive recommendations.

**Child Issues:** #6, #7, #8, #9, and new issues below

---

## Phase 1: Navigation Redesign (Week 1, Days 1-2)

### Issue #75 - Simplify Navigation from 4 Tabs to 2 Tabs
**Priority:** P1-high  
**Labels:** P1-high, ui/ux, enhancement  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Simplify the main navigation by reducing from 4 tabs to 2 tabs for better mobile UX and cleaner interface.

**Current State:**
- 📊 Commute Routes
- 📈 How It Works
- 🌤️ Commute Forecast
- 🚵 Long Rides

**Target State:**
- 🚴 Commute Routes (with integrated forecast + modal)
- 🚵 Long Rides

**Tasks:**
- [ ] Remove "How It Works" tab
- [ ] Remove "Commute Forecast" tab
- [ ] Update tab navigation HTML
- [ ] Test tab switching functionality
- [ ] Update CSS for 2-tab layout
- [ ] Test on mobile devices

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Only 2 tabs visible in navigation
- Tab switching works correctly
- Mobile layout is clean and functional
- No broken links or references

---

### Issue #76 - Add "How It Works" Modal
**Priority:** P1-high  
**Labels:** P1-high, ui/ux, enhancement  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours

**Description:**
Convert "How It Works" tab content into a modal dialog accessible via info icon (ℹ️) in the header.

**Tasks:**
- [ ] Create modal HTML structure
- [ ] Add info icon (ℹ️) to header
- [ ] Wire up click handler to open modal
- [ ] Style modal content
- [ ] Add close button and ESC key handler
- [ ] Test on mobile (touch interactions)
- [ ] Ensure accessibility (keyboard navigation, ARIA labels)

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Info icon visible in header
- Modal opens on click
- Modal content is readable and well-formatted
- Modal closes properly (X button, ESC key, click outside)
- Works on mobile devices
- Keyboard accessible

---

### Issue #77 - Integrate Weather Forecast into Commute Tab
**Priority:** P1-high  
**Labels:** P1-high, ui/ux, enhancement  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours

**Description:**
Move weather forecast content from separate tab into collapsible widget in the Commute Routes tab.

**Tasks:**
- [ ] Create collapsible forecast section
- [ ] Move forecast data to commute tab
- [ ] Style forecast cards (3-day view)
- [ ] Add expand/collapse functionality
- [ ] Add morning/evening commute recommendations
- [ ] Test responsiveness on mobile
- [ ] Ensure collapsed by default to save space

**Files to Modify:**
- `templates/report_template.html`
- `src/report_generator.py` (if data structure changes)

**Acceptance Criteria:**
- Forecast widget appears in commute tab
- Collapsible/expandable functionality works
- Shows 3-day forecast with wind conditions
- Mobile-friendly layout
- Collapsed by default

---

## Phase 2: Statistics Display (Week 1, Days 3-5)

### Issue #6 - Add Top 10 Longest Rides Table with Strava Links
**Priority:** P1-high  
**Labels:** P1-high, feature, long-rides  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours  
**Epic:** #57

**Description:**
Display a table showing the top 10 longest rides with key metrics and direct links to Strava activities.

**Tasks:**
- [ ] Create table component in long rides tab
- [ ] Sort rides by distance (descending)
- [ ] Display columns: Rank, Name, Distance, Duration, Elevation, Avg Speed, Date
- [ ] Add Strava link button for each ride
- [ ] Style table consistently with route comparison table
- [ ] Make table responsive/scrollable on mobile
- [ ] Add hover effects for better UX

**Files to Modify:**
- `templates/report_template.html`
- `src/report_generator.py`

**Acceptance Criteria:**
- Table shows top 10 rides sorted by distance
- All columns display correct data
- Strava links work and open in new tab
- Table is responsive on mobile
- Consistent styling with existing tables

---

### Issue #7 - Add Monthly Ride Statistics Breakdown
**Priority:** P1-high  
**Labels:** P1-high, feature, long-rides, visualization  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours  
**Epic:** #57

**Description:**
Create a chart visualization showing monthly ride statistics (count and distance) using Chart.js.

**Tasks:**
- [ ] Group rides by month
- [ ] Calculate rides per month and distance per month
- [ ] Create bar chart with Chart.js
- [ ] Implement dual-axis (count + distance)
- [ ] Add year selector if multi-year data exists
- [ ] Style chart container
- [ ] Make chart responsive for mobile
- [ ] Add tooltips with detailed information

**Files to Modify:**
- `templates/report_template.html`
- `src/report_generator.py`

**Acceptance Criteria:**
- Chart displays monthly statistics
- Both ride count and distance visible
- Chart is responsive and readable on mobile
- Tooltips show detailed information
- Year selector works if applicable

---

### Issue #8 - Add Average Speed and Elevation Gain Metrics
**Priority:** P1-high  
**Labels:** P1-high, feature, long-rides  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours  
**Epic:** #57

**Description:**
Create summary statistics cards showing key metrics: total rides, average distance, longest ride, total elevation, and average speed.

**Tasks:**
- [ ] Create statistics card component
- [ ] Calculate total rides
- [ ] Calculate average distance
- [ ] Calculate longest ride
- [ ] Calculate total elevation gain
- [ ] Calculate average speed
- [ ] Calculate total distance
- [ ] Style cards with icons
- [ ] Make responsive for mobile (2x2 grid on mobile, 4x1 on desktop)

**Files to Modify:**
- `templates/report_template.html`
- `src/report_generator.py`

**Acceptance Criteria:**
- All 4-6 statistics cards display correctly
- Calculations are accurate
- Cards are visually appealing with icons
- Responsive layout works on all screen sizes
- Units are displayed correctly (km, m, km/h)

---

## Phase 3: Interactive Map (Week 2, Days 1-2)

### Issue #9 - Add Interactive Map Showing All Long Ride Routes
**Priority:** P1-high  
**Labels:** P1-high, feature, long-rides, visualization  
**Milestone:** v2.4.0  
**Estimated Effort:** 8 hours  
**Epic:** #57

**Description:**
Create an interactive Leaflet map displaying all long ride routes with color coding, filtering, and detailed popups.

**Tasks:**
- [ ] Initialize Leaflet map in long rides tab
- [ ] Add all long ride routes as polylines
- [ ] Implement color coding by distance (gradient)
- [ ] Add route markers at start/end points
- [ ] Implement route highlighting on hover
- [ ] Add popup with ride details (name, distance, duration, elevation)
- [ ] Fit map bounds to show all routes
- [ ] Add filter buttons (loops, point-to-point, show all)
- [ ] Implement layer control
- [ ] Add legend for color coding
- [ ] Optimize for mobile (touch interactions)
- [ ] Add click-to-zoom functionality

**Files to Modify:**
- `templates/report_template.html`
- `src/visualizer.py`
- `src/report_generator.py`

**Acceptance Criteria:**
- Map displays all long ride routes
- Color coding by distance works
- Hover effects highlight routes
- Popups show correct information
- Filter buttons work correctly
- Mobile touch interactions work smoothly
- Map performance is acceptable (< 1s render time)

---

## Phase 4: Backend API Layer (Week 2, Days 3-5)

### Issue #78 - Create Flask API Server for Long Rides
**Priority:** P1-high  
**Labels:** P1-high, backend, api, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 6 hours

**Description:**
Set up Flask API server with core endpoints for long rides recommendations, geocoding, and weather data.

**Tasks:**
- [ ] Create `src/api/` directory structure
- [ ] Set up Flask application in `long_rides_api.py`
- [ ] Add CORS support (flask-cors)
- [ ] Implement error handling middleware
- [ ] Add request logging
- [ ] Create initialization function to pass data from main app
- [ ] Modify `main.py` to start API server
- [ ] Add configuration options to `config.yaml`
- [ ] Document API server lifecycle

**Files to Create:**
- `src/api/__init__.py`
- `src/api/long_rides_api.py`

**Files to Modify:**
- `main.py`
- `config/config.yaml`

**Acceptance Criteria:**
- Flask server starts successfully
- CORS is configured properly
- Error handling works
- Logging captures requests
- Server integrates with main application
- Configuration options work

---

### Issue #79 - Implement Recommendations API Endpoint
**Priority:** P1-high  
**Labels:** P1-high, backend, api, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Create `/api/long-rides/recommendations` endpoint to return ride recommendations based on location and filters.

**Endpoint:** `GET /api/long-rides/recommendations`

**Query Parameters:**
- `lat` (required): Starting latitude
- `lon` (required): Starting longitude
- `ride_type` (optional): "roundtrip" or "point-to-point"
- `min_distance` (optional): Minimum distance in km
- `max_distance` (optional): Maximum distance in km
- `min_duration` (optional): Minimum duration in hours
- `max_duration` (optional): Maximum duration in hours

**Tasks:**
- [ ] Implement endpoint handler
- [ ] Parse and validate query parameters
- [ ] Call `LongRideAnalyzer.get_ride_recommendations()`
- [ ] Filter results by ride type
- [ ] Filter results by distance range
- [ ] Filter results by duration range
- [ ] Format response JSON
- [ ] Add error handling
- [ ] Limit results to top 10
- [ ] Add response caching

**Files to Modify:**
- `src/api/long_rides_api.py`

**Acceptance Criteria:**
- Endpoint returns valid JSON
- All filters work correctly
- Error responses are helpful
- Response time < 2 seconds
- Caching works

---

### Issue #80 - Implement Geocoding API Endpoint
**Priority:** P1-high  
**Labels:** P1-high, backend, api, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours

**Description:**
Create `/api/long-rides/geocode` endpoint to convert location text to coordinates.

**Endpoint:** `POST /api/long-rides/geocode`

**Request Body:**
```json
{
  "location": "Chicago, IL"
}
```

**Tasks:**
- [ ] Implement endpoint handler
- [ ] Integrate with geocoding service (Nominatim)
- [ ] Parse location string
- [ ] Return lat/lon coordinates
- [ ] Return display name
- [ ] Add error handling for invalid locations
- [ ] Add rate limiting
- [ ] Add response caching

**Files to Modify:**
- `src/api/long_rides_api.py`

**Acceptance Criteria:**
- Endpoint converts locations to coordinates
- Error handling for invalid locations
- Rate limiting works
- Caching prevents redundant API calls
- Response time < 500ms

---

### Issue #81 - Implement Weather API Endpoint
**Priority:** P1-high  
**Labels:** P1-high, backend, api, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours

**Description:**
Create `/api/long-rides/weather` endpoint to fetch current weather and wind conditions.

**Endpoint:** `GET /api/long-rides/weather`

**Query Parameters:**
- `lat` (required): Latitude
- `lon` (required): Longitude

**Tasks:**
- [ ] Implement endpoint handler
- [ ] Integrate with `WeatherFetcher`
- [ ] Fetch current conditions
- [ ] Format wind data (speed, direction)
- [ ] Add error handling
- [ ] Add response caching (1 hour TTL)

**Files to Modify:**
- `src/api/long_rides_api.py`

**Acceptance Criteria:**
- Endpoint returns current weather
- Wind data is accurate
- Error handling works
- Caching reduces API calls
- Response time < 1 second

---

## Phase 5: Interactive Recommendations (Week 3)

### Issue #82 - Create Interactive Recommendation Input Form
**Priority:** P1-high  
**Labels:** P1-high, frontend, ui/ux, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Build interactive form for users to input ride preferences and get personalized recommendations.

**Tasks:**
- [ ] Add location input field (text)
- [ ] Add geocode search button
- [ ] Add ride type selector (roundtrip/point-to-point)
- [ ] Add distance range slider (15-100+ km)
- [ ] Add duration range slider (1-6+ hours)
- [ ] Implement form validation
- [ ] Add loading states
- [ ] Add "Get Recommendations" button
- [ ] Style form consistently
- [ ] Make mobile-friendly

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- All form inputs work correctly
- Validation provides helpful feedback
- Loading states are clear
- Mobile layout is usable
- Form is accessible (keyboard navigation, ARIA labels)

---

### Issue #83 - Implement Frontend API Integration
**Priority:** P1-high  
**Labels:** P1-high, frontend, api, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Create JavaScript API client to connect frontend form to backend API endpoints.

**Tasks:**
- [ ] Create API client class/functions
- [ ] Implement `geocodeLocation()` function
- [ ] Implement `getWeather()` function
- [ ] Implement `getRecommendations()` function
- [ ] Handle API responses
- [ ] Handle API errors with user-friendly messages
- [ ] Add loading indicators
- [ ] Add retry logic for failed requests
- [ ] Add request timeout handling

**Files to Modify:**
- `templates/report_template.html` (JavaScript section)

**Acceptance Criteria:**
- All API calls work correctly
- Error messages are user-friendly
- Loading indicators show during requests
- Timeout handling works
- Retry logic functions properly

---

### Issue #84 - Create Recommendation Results Display Component
**Priority:** P1-high  
**Labels:** P1-high, frontend, ui/ux, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Build component to display ride recommendations with wind scores, metrics, and actions.

**Tasks:**
- [ ] Create recommendation card component
- [ ] Display wind score with progress bar
- [ ] Show route metrics (distance, duration, elevation)
- [ ] Display weather summary
- [ ] Add "View on Map" button
- [ ] Add "View on Strava" link
- [ ] Implement card hover effects
- [ ] Make cards responsive for mobile
- [ ] Add empty state (no results)
- [ ] Add loading skeleton

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Cards display all information correctly
- Wind score visualization is clear
- Buttons/links work properly
- Mobile layout is clean
- Empty state is helpful
- Loading skeleton improves perceived performance

---

### Issue #85 - Integrate Map with Recommendation System
**Priority:** P1-high  
**Labels:** P1-high, frontend, feature  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Connect interactive map with recommendation system for location selection and route visualization.

**Tasks:**
- [ ] Add click-to-select location on map
- [ ] Update form with clicked coordinates
- [ ] Display recommended routes on map
- [ ] Highlight selected route
- [ ] Implement route hover effects
- [ ] Add zoom-to-route functionality
- [ ] Show wind direction indicators
- [ ] Optimize map performance
- [ ] Test touch interactions on mobile

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Map click updates location input
- Recommended routes display on map
- Route highlighting works
- Zoom functionality works
- Mobile touch interactions are smooth
- Performance is acceptable

---

## Phase 6: Backend Improvements (Week 4)

### Issue #86 - Add Data Persistence Layer for API
**Priority:** P1-high  
**Labels:** P1-high, backend, infrastructure  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours  
**Review Feedback:** Senior Developer A - High Priority

**Description:**
Implement persistence layer so API server can reload data after restart without re-running full analysis.

**Tasks:**
- [ ] Create `LongRidesDataStore` class
- [ ] Implement save method (serialize to JSON)
- [ ] Implement load method (deserialize from JSON)
- [ ] Add cache file path to configuration
- [ ] Integrate with API initialization
- [ ] Add cache invalidation logic
- [ ] Handle corrupted cache files gracefully
- [ ] Add cache statistics/metadata

**Files to Create:**
- `src/cache/long_rides_store.py`

**Files to Modify:**
- `src/api/long_rides_api.py`
- `main.py`
- `config/config.yaml`

**Acceptance Criteria:**
- Data persists between API restarts
- Load time is fast (< 1 second)
- Corrupted cache handled gracefully
- Cache invalidation works
- Configuration options work

---

### Issue #87 - Implement Input Validation with Marshmallow
**Priority:** P1-high  
**Labels:** P1-high, backend, security  
**Milestone:** v2.4.0  
**Estimated Effort:** 3 hours  
**Review Feedback:** Senior Developer A - High Priority

**Description:**
Add comprehensive input validation for all API endpoints using Marshmallow schemas.

**Tasks:**
- [ ] Add marshmallow to requirements.txt
- [ ] Create validation schemas for each endpoint
- [ ] Implement RecommendationsQuerySchema
- [ ] Implement GeocodeRequestSchema
- [ ] Implement WeatherQuerySchema
- [ ] Add validation to endpoint handlers
- [ ] Return helpful error messages
- [ ] Add unit tests for validation

**Files to Modify:**
- `requirements.txt`
- `src/api/long_rides_api.py`

**Files to Create:**
- `tests/test_api_validation.py`

**Acceptance Criteria:**
- All endpoints validate input
- Invalid input returns 400 with helpful message
- Valid input passes through
- Edge cases handled (negative values, out of range, etc.)
- Unit tests pass

---

### Issue #88 - Add Rate Limiting to API Endpoints
**Priority:** P1-high  
**Labels:** P1-high, backend, security  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours  
**Review Feedback:** Senior Developer A - High Priority

**Description:**
Implement rate limiting using flask-limiter to prevent API abuse.

**Tasks:**
- [ ] Add flask-limiter to requirements.txt
- [ ] Configure limiter with default limits
- [ ] Add stricter limits to expensive endpoints
- [ ] Configure rate limit storage (memory or Redis)
- [ ] Add rate limit headers to responses
- [ ] Add rate limit exceeded error handling
- [ ] Document rate limits in API docs

**Files to Modify:**
- `requirements.txt`
- `src/api/long_rides_api.py`
- `config/config.yaml`

**Acceptance Criteria:**
- Rate limiting works correctly
- Expensive endpoints have stricter limits
- Rate limit headers are present
- Error messages are clear
- Configuration options work

---

## Phase 7: Frontend Polish (Week 5)

### Issue #89 - Add Loading States with Skeleton Loaders
**Priority:** P1-high  
**Labels:** P1-high, frontend, ui/ux  
**Milestone:** v2.4.0  
**Estimated Effort:** 3 hours  
**Review Feedback:** Senior Developer B - High Priority

**Description:**
Implement skeleton loaders for better perceived performance during data loading.

**Tasks:**
- [ ] Create skeleton loader CSS
- [ ] Add skeleton for recommendation cards
- [ ] Add skeleton for statistics cards
- [ ] Add skeleton for table rows
- [ ] Add skeleton for map loading
- [ ] Implement smooth transitions
- [ ] Test on slow connections
- [ ] Ensure accessibility

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Skeleton loaders display during loading
- Smooth transition to real content
- Improves perceived performance
- Accessible (screen reader friendly)
- Works on all screen sizes

---

### Issue #90 - Implement Comprehensive Error States
**Priority:** P1-high  
**Labels:** P1-high, frontend, ui/ux  
**Milestone:** v2.4.0  
**Estimated Effort:** 3 hours  
**Review Feedback:** Senior Developer B - High Priority

**Description:**
Add visual error states for empty results, API errors, and no data scenarios.

**Tasks:**
- [ ] Create empty state component (no rides found)
- [ ] Create error state component (API error)
- [ ] Create no results state (filters too restrictive)
- [ ] Add retry buttons where appropriate
- [ ] Add helpful messages and suggestions
- [ ] Style error states consistently
- [ ] Test all error scenarios
- [ ] Ensure accessibility

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- All error scenarios have visual states
- Messages are helpful and actionable
- Retry functionality works
- Styling is consistent
- Accessible to all users

---

### Issue #91 - Implement Accessibility Improvements
**Priority:** P1-high  
**Labels:** P1-high, frontend, accessibility, a11y  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours  
**Review Feedback:** Senior Developer B - High Priority

**Description:**
Ensure long rides feature meets WCAG 2.1 AA accessibility standards.

**Tasks:**
- [ ] Add ARIA labels to all interactive elements
- [ ] Add ARIA roles where appropriate
- [ ] Implement keyboard navigation for all features
- [ ] Add focus indicators
- [ ] Test with screen reader
- [ ] Ensure color contrast meets standards
- [ ] Add skip links where needed
- [ ] Test keyboard-only navigation
- [ ] Add alt text for icons
- [ ] Ensure form labels are properly associated

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- All interactive elements keyboard accessible
- Screen reader can navigate all content
- Color contrast meets WCAG AA
- Focus indicators are visible
- ARIA labels are meaningful
- Passes automated accessibility tests

---

### Issue #92 - Optimize Mobile Map Performance
**Priority:** P2-medium  
**Labels:** P2-medium, frontend, performance  
**Milestone:** v2.4.0  
**Estimated Effort:** 3 hours  
**Review Feedback:** Senior Developer B - Medium Priority

**Description:**
Implement route clustering and lazy loading for better mobile map performance.

**Tasks:**
- [ ] Add Leaflet.markercluster library
- [ ] Implement clustering for mobile devices
- [ ] Add lazy loading for route polylines
- [ ] Optimize polyline simplification
- [ ] Test on various mobile devices
- [ ] Measure and optimize render time
- [ ] Add loading indicators for map

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Map loads quickly on mobile (< 2 seconds)
- Clustering works smoothly
- No performance issues with 100+ routes
- Touch interactions remain smooth
- Desktop experience unchanged

---

### Issue #93 - Add Form Validation Feedback
**Priority:** P2-medium  
**Labels:** P2-medium, frontend, ui/ux  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours  
**Review Feedback:** Senior Developer B - Medium Priority

**Description:**
Implement inline validation feedback for form inputs with helpful error messages.

**Tasks:**
- [ ] Add validation on blur for each input
- [ ] Show inline error messages
- [ ] Add success indicators for valid input
- [ ] Implement real-time validation
- [ ] Add helpful hints below inputs
- [ ] Style validation states consistently
- [ ] Test all validation scenarios
- [ ] Ensure accessibility

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Validation feedback is immediate
- Error messages are helpful
- Success states are clear
- Doesn't interfere with user input
- Accessible to screen readers

---

### Issue #94 - Optimize Chart Responsiveness
**Priority:** P2-medium  
**Labels:** P2-medium, frontend, visualization  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours  
**Review Feedback:** Senior Developer B - Medium Priority

**Description:**
Improve Chart.js configuration for better mobile responsiveness and readability.

**Tasks:**
- [ ] Configure responsive options
- [ ] Adjust font sizes for mobile
- [ ] Hide legend on mobile if needed
- [ ] Optimize tooltip display
- [ ] Add resize handler
- [ ] Test on various screen sizes
- [ ] Ensure touch interactions work

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Charts are readable on all screen sizes
- Font sizes appropriate for device
- Touch interactions work smoothly
- Resize handling works correctly
- Performance is acceptable

---

### Issue #95 - Add Animation Performance Optimizations
**Priority:** P2-medium  
**Labels:** P2-medium, frontend, performance  
**Milestone:** v2.4.0  
**Estimated Effort:** 2 hours  
**Review Feedback:** Senior Developer B - Medium Priority

**Description:**
Optimize CSS animations for smooth 60fps performance and respect user motion preferences.

**Tasks:**
- [ ] Use transform and opacity for animations
- [ ] Add will-change hints where appropriate
- [ ] Implement prefers-reduced-motion media query
- [ ] Test animation performance
- [ ] Optimize hover effects
- [ ] Remove janky animations
- [ ] Test on low-end devices

**Files to Modify:**
- `templates/report_template.html`

**Acceptance Criteria:**
- Animations run at 60fps
- No layout thrashing
- Reduced motion preference respected
- Smooth on low-end devices
- No performance regressions

---

## Testing & Documentation

### Issue #96 - Create Unit Tests for API Endpoints
**Priority:** P1-high  
**Labels:** P1-high, testing, backend  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Write comprehensive unit tests for all API endpoints.

**Tasks:**
- [ ] Set up test fixtures
- [ ] Test recommendations endpoint
- [ ] Test geocoding endpoint
- [ ] Test weather endpoint
- [ ] Test error handling
- [ ] Test validation
- [ ] Test rate limiting
- [ ] Achieve 80%+ coverage

**Files to Create:**
- `tests/test_long_ride_api.py`

**Acceptance Criteria:**
- All endpoints have tests
- Edge cases covered
- Error scenarios tested
- 80%+ code coverage
- Tests pass consistently

---

### Issue #97 - Create Integration Tests for Full Flow
**Priority:** P1-high  
**Labels:** P1-high, testing, integration  
**Milestone:** v2.4.0  
**Estimated Effort:** 4 hours

**Description:**
Write integration tests covering complete user workflows.

**Tasks:**
- [ ] Test full recommendation flow
- [ ] Test geocoding → weather → recommendations
- [ ] Test error recovery
- [ ] Test caching behavior
- [ ] Test concurrent requests
- [ ] Test data persistence

**Files to Create:**
- `tests/test_long_ride_integration.py`

**Acceptance Criteria:**
- Complete workflows tested
- Error scenarios covered
- Performance benchmarks included
- Tests pass consistently
- Documentation included

---

### Issue #98 - Update Documentation for Long Rides Feature
**Priority:** P1-high  
**Labels:** P1-high, documentation  
**Milestone:** v2.4.0  
**Estimated Effort:** 3 hours

**Description:**
Update README and create user guide for long rides feature.

**Tasks:**
- [ ] Update README.md with feature description
- [ ] Document API endpoints
- [ ] Create user guide
- [ ] Add configuration documentation
- [ ] Document troubleshooting steps
- [ ] Add screenshots/examples
- [ ] Update TECHNICAL_SPEC.md

**Files to Modify:**
- `README.md`
- `TECHNICAL_SPEC.md`

**Files to Create:**
- `docs/LONG_RIDES_USER_GUIDE.md`
- `docs/LONG_RIDES_API.md`

**Acceptance Criteria:**
- README updated with feature info
- API documentation complete
- User guide is clear and helpful
- Configuration options documented
- Examples included

---

## Summary

### Total Issues: 24 new issues (plus 4 existing: #6, #7, #8, #9)

### By Priority:
- **P1-high:** 20 issues
- **P2-medium:** 4 issues

### By Phase:
- **Phase 1 (Navigation):** 3 issues (#75, #76, #77)
- **Phase 2 (Statistics):** 3 issues (#6, #7, #8)
- **Phase 3 (Map):** 1 issue (#9)
- **Phase 4 (Backend API):** 4 issues (#78, #79, #80, #81)
- **Phase 5 (Interactive):** 4 issues (#82, #83, #84, #85)
- **Phase 6 (Backend Improvements):** 3 issues (#86, #87, #88)
- **Phase 7 (Frontend Polish):** 6 issues (#89, #90, #91, #92, #93, #94, #95)
- **Testing & Docs:** 3 issues (#96, #97, #98)

### Estimated Total Effort: 80-90 hours (5 weeks at 16-18 hours/week)

---

## Issue Creation Script

Save this as `plans/v2.4.0/create_long_rides_issues.sh`:

```bash
#!/bin/bash

# This script creates GitHub issues for the Long Rides feature
# Run from project root: ./plans/v2.4.0/create_long_rides_issues.sh

echo "Creating Long Rides feature issues..."
echo "Note: Issues #6, #7, #8, #9 already exist"
echo ""

# You'll need to manually create these issues on GitHub
# or use the GitHub CLI (gh) if installed

echo "To create issues manually:"
echo "1. Go to https://github.com/YOUR_USERNAME/ride-optimizer/issues/new"
echo "2. Copy the title and description from GITHUB_ISSUES_LONG_RIDES.md"
echo "3. Add appropriate labels and milestone"
echo ""

echo "To create issues with GitHub CLI:"
echo "gh issue create --title 'TITLE' --body 'DESCRIPTION' --label 'LABELS' --milestone 'v2.4.0'"
echo ""

echo "See GITHUB_ISSUES_LONG_RIDES.md for complete issue details"
```

---

**Created:** 2026-03-29  
**Based on:** Implementation Plan + Peer Review Feedback  
**Ready for:** Issue Creation