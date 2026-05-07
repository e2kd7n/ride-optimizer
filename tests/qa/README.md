# Frontend Squad QA Test Harnesses

This directory contains comprehensive QA test harnesses for all Frontend Squad deliverables (Issues #132-135, #142).

## Overview

Each test harness is a standalone Python script that can be run independently to verify functionality. All tests use Flask's test client to simulate HTTP requests without requiring a running server.

## Test Harnesses

### 1. Dashboard (Issue #132)
**File**: `test_dashboard_qa.py`

Tests the recommendation-first dashboard including:
- Route accessibility (GET /)
- Content sections (quick stats, recommendations, data freshness)
- Health endpoint (GET /health)
- Response time performance
- Error handling with invalid parameters

**Usage**:
```bash
# Run all tests
python tests/qa/test_dashboard_qa.py

# Verbose output
python tests/qa/test_dashboard_qa.py --verbose

# Check performance
python tests/qa/test_dashboard_qa.py --check-performance
```

**Expected Results**:
- All routes return 200 status
- Dashboard contains quick stats, commute recommendation, long ride suggestion
- Health endpoint returns `{"status": "healthy"}`
- Response time < 2 seconds
- Graceful handling of invalid parameters

---

### 2. Commute Views (Issue #133)
**File**: `test_commute_qa.py`

Tests commute recommendation views including:
- Route accessibility (GET /commute/)
- Content sections (primary recommendation, alternatives, weather, departure windows)
- Departure time parameter handling
- Response time performance
- Error handling

**Usage**:
```bash
# Run all tests
python tests/qa/test_commute_qa.py

# Verbose output
python tests/qa/test_commute_qa.py --verbose
```

**Expected Results**:
- Commute index accessible at /commute/
- Page contains primary recommendation, weather impact, score breakdown, alternatives
- Departure time parameter accepted (e.g., ?departure_time=08:00)
- Response time < 3 seconds (includes weather API calls)
- Graceful handling of invalid departure times

---

### 3. Long Ride Planner (Issue #134)
**File**: `test_planner_qa.py`

Tests long ride planner including:
- Route accessibility (GET /planner/)
- Content sections (7-day forecast, filters, daily recommendations, weather)
- Filter parameter handling (distance, duration)
- Forecast days parameter (3, 5, 7, 14 days)
- Response time performance
- Error handling

**Usage**:
```bash
# Run all tests
python tests/qa/test_planner_qa.py

# Verbose output
python tests/qa/test_planner_qa.py --verbose
```

**Expected Results**:
- Planner index accessible at /planner/
- Page contains 7-day forecast, filter controls, daily recommendations, weather
- Filter parameters work: min_distance, max_distance, min_duration, max_duration
- Forecast days parameter works: 3, 5, 7, 14
- Response time < 5 seconds (includes weather API + analysis)
- Graceful handling of invalid filter values

---

### 4. Route Library (Issue #135)
**File**: `test_route_library_qa.py`

Tests route library browsing and detail views including:
- Route accessibility (GET /routes/)
- Content sections (route list, filters, pagination, stats)
- Search functionality (GET /routes/api/search)
- Favorite toggle (POST /routes/api/<route_id>/favorite)
- Route detail page (GET /routes/<route_id>)
- Pagination
- Error handling

**Usage**:
```bash
# Run all tests
python tests/qa/test_route_library_qa.py

# Verbose output
python tests/qa/test_route_library_qa.py --verbose
```

**Expected Results**:
- Route library accessible at /routes/
- Page contains route list, filters, pagination controls
- Search API returns JSON results
- Favorite toggle API works
- Route detail pages accessible
- Pagination works (20 items per page)
- Graceful handling of invalid route IDs

---

### 5. Responsive Layout (Issue #142)
**File**: `test_responsive_qa.py`

Tests responsive layout and mobile-first design including:
- Bootstrap 5 integration
- Mobile navigation (hamburger menu)
- Touch-friendly targets (44px minimum)
- Responsive breakpoints
- Accessibility features
- Loading states

**Usage**:
```bash
# Run all tests
python tests/qa/test_responsive_qa.py

# Verbose output
python tests/qa/test_responsive_qa.py --verbose
```

**Expected Results**:
- Bootstrap 5 CSS and JS loaded
- Mobile navigation present
- All interactive elements ≥ 44px
- Responsive classes applied correctly
- ARIA labels present
- Focus-visible styles applied

---

## Running All Tests

To run all QA test harnesses sequentially:

```bash
# Run all tests
./tests/qa/run_all_qa_tests.sh

# Or manually:
python tests/qa/test_dashboard_qa.py
python tests/qa/test_commute_qa.py
python tests/qa/test_planner_qa.py
python tests/qa/test_route_library_qa.py
python tests/qa/test_responsive_qa.py
```

## Test Output Format

Each test harness produces a summary report:

```
============================================================
Dashboard QA Test Suite (Issue #132)
============================================================

[INFO] Testing dashboard accessibility...
✓ Dashboard accessible

[INFO] Testing dashboard content...
  ✓ Quick Stats present
  ✓ Commute Recommendation present
  ✓ Long Ride Suggestion present
  ✓ Data Freshness present

...

============================================================
Test Summary
============================================================
✓ Dashboard Accessibility      PASS   Route accessible
✓ Dashboard Content            PASS   All sections present
✓ Health Endpoint              PASS   Endpoint healthy
✓ Response Time                PASS   0.234s
✓ Error Handling               PASS   Graceful degradation

------------------------------------------------------------
Total: 5 | Passed: 5 | Failed: 0 | Errors: 0 | Warnings: 0
------------------------------------------------------------
```

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed or errored

## Prerequisites

Before running QA tests:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Strava credentials
   ```

3. **Ensure data is available**:
   ```bash
   # Fetch activities from Strava
   python main.py --fetch --limit 100
   
   # Run analysis
   python main.py --analyze
   ```

## Integration with CI/CD

These test harnesses can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run QA Tests
  run: |
    python tests/qa/test_dashboard_qa.py
    python tests/qa/test_commute_qa.py
    python tests/qa/test_planner_qa.py
    python tests/qa/test_route_library_qa.py
    python tests/qa/test_responsive_qa.py
```

## Manual Testing Checklist

In addition to automated tests, QA should manually verify:

### Dashboard (Issue #132)
- [ ] Quick stats display correct values
- [ ] Commute recommendation shows next commute
- [ ] Long ride suggestion shows upcoming ride
- [ ] Data freshness indicator accurate
- [ ] Links to detail pages work

### Commute Views (Issue #133)
- [ ] Primary recommendation displays correctly
- [ ] Alternative routes show up to 3 options
- [ ] Weather impact grid shows all conditions
- [ ] Score breakdown explains recommendation
- [ ] Departure windows show optimal times
- [ ] Direction toggle works (to_work/from_work)

### Long Ride Planner (Issue #134)
- [ ] 7-day forecast displays correctly
- [ ] Filter controls work (distance, duration)
- [ ] Daily recommendations show top 5 rides
- [ ] Weather scoring visible for each ride
- [ ] Expandable alternatives work
- [ ] Best day highlighted

### Route Library (Issue #135)
- [ ] Route list displays with pagination
- [ ] Search filters routes correctly
- [ ] Favorite toggle persists
- [ ] Route detail page shows all info
- [ ] Statistics accurate
- [ ] Filters update counts correctly

### Responsive Layout (Issue #142)
- [ ] Mobile navigation works on small screens
- [ ] Touch targets are finger-friendly
- [ ] Content stacks vertically on mobile
- [ ] Tables scroll horizontally on mobile
- [ ] Font sizes readable on all devices
- [ ] No horizontal scrolling on mobile

## Troubleshooting

### Tests Fail with "No module named 'app'"
**Solution**: Run from project root directory:
```bash
cd /Users/erik/dev/ride-optimizer
python tests/qa/test_dashboard_qa.py
```

### Tests Fail with "Config file not found"
**Solution**: Ensure config file exists:
```bash
ls config/config.yaml
```

### Tests Fail with "No activities found"
**Solution**: Fetch and analyze data first:
```bash
python main.py --fetch --limit 100
python main.py --analyze
```

### Response Time Tests Fail
**Solution**: This is a warning, not a failure. Check:
- Network latency to weather API
- System load
- Database query performance

## Support

For issues with QA test harnesses:
1. Check this README for troubleshooting steps
2. Review test output for specific error messages
3. Comment on the relevant GitHub issue (#132-135, #142)
4. Contact Frontend Squad Lead

## Test Coverage

These QA harnesses cover:
- ✅ Route accessibility (all endpoints)
- ✅ Content rendering (all sections)
- ✅ Parameter handling (query params, POST data)
- ✅ Error handling (invalid inputs)
- ✅ Performance (response times)
- ✅ Service integration (all services)
- ✅ API endpoints (JSON responses)

Not covered (requires manual testing):
- ❌ Visual appearance (CSS, layout)
- ❌ JavaScript interactions (AJAX, dynamic updates)
- ❌ Browser compatibility
- ❌ Mobile device testing
- ❌ Accessibility (screen readers, keyboard nav)
- ❌ Map visualization

## Next Steps

After QA approval:
1. Merge PR #150 to main
2. Deploy to staging environment
3. Run integration tests with Weather Squad (#136) and Workout Squad (#137)
4. Perform end-to-end testing (Issue #143)
5. Deploy to production

---

**Created by**: Frontend Squad Lead (Bob)
**Last Updated**: 2026-05-07
**Related Issues**: #132, #133, #134, #135, #142
**Pull Request**: #150