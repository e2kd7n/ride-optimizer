# CLI Legacy Scripts Archive

This directory contains scripts from the old CLI-based version of Ride Optimizer (pre-web platform migration).

## Archived Date
2026-05-07

## Reason for Archiving
These scripts were designed for the original CLI application that used `main.py` and the `src/` module structure. After migrating to the Flask web platform with the `app/` structure, these scripts are no longer compatible with the current architecture.

## Archived Scripts

### Testing Scripts
- `test_analyze_no_hang.py` - Test that analysis doesn't hang
- `test_geocoding.py` - Test geocoding functionality
- `test_long_ride_recommendations.py` - Test long ride analysis
- `test_long_rides_feature.py` - Test long rides feature
- `test_next_commute.py` - Test next commute feature
- `test_route_naming.py` - Test route naming
- `test_sport_type_fix.py` - Test sport type fix
- `test_uses_count.py` - Test uses count feature
- `test_weather_integration.py` - Test weather integration
- `test_workout_aware_commutes.py` - Test workout-aware commutes

### Debugging Scripts
- `check_old_school_routes.py` - Check "Old School" route grouping
- `debug_route_matching.py` - Debug route matching issues
- `debug_sport_type.py` - Debug sport type issues
- `diagnose_long_rides.py` - Diagnose long rides issues
- `find_matched_routes.py` - Find and analyze matched routes

### Performance Scripts
- `profile_analysis.py` - Profile application performance
- `performance_test.py` - Performance testing for Smart Static architecture

### Data Scripts
- `fetch_test_activities.py` - Fetch test activities from Strava

## Migration Notes
- The web platform now has proper test suites in `tests/` directory
- API testing should use the Flask test client
- Performance testing should target the API endpoints (port 8083)
- Feature testing should be done through the web interface or API

## If You Need These Scripts
If you need functionality from these scripts:
1. Check if equivalent tests exist in `tests/` directory
2. For API testing, use `pytest` with the Flask test client
3. For manual testing, use the web interface at http://localhost:8083
4. For integration testing, see `scripts/run_integration_tests.sh`

## Port Changes Reference
- Old CLI used various ports inconsistently
- New web platform uses:
  - API: 8083
  - OAuth callback: 8000