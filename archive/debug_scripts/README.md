# Debug & Analysis Scripts Archive

This directory contains historical debug and analysis scripts used during development. These scripts were created for specific investigations and are no longer needed for regular operation.

## Contents

### Route Analysis Scripts
- **analyze_route_resolution.py** - Analyzed GPS point resolution and sampling rates
  - Used to understand GPS data quality
  - Findings documented in algorithm change decisions

- **compare_similarity_algorithms.py** - Compared Hausdorff vs Fréchet distance
  - Led to adoption of Fréchet distance as primary algorithm
  - Results documented in SIMILARITY_ALGORITHM_CHANGE.md

- **debug_route_grouping.py** - Debugged route grouping logic
  - Investigated similarity threshold issues
  - Helped identify over-clustering problems

### Route-Specific Debug Scripts
- **debug_harrison_routes.py** - Debugged specific user's routes
  - One-off investigation for route matching issues
  - Findings applied to general algorithm improvements

- **debug_plus_routes.py** - Debugged plus route detection
  - Investigated why certain routes weren't marked as plus routes
  - Led to improvements in plus route logic

### Test Data Management
- **add_test_routes.py** - Added test routes to dataset
  - Used during development for testing
  - Test routes later removed (see issue #52)

- **update_test_routes.py** - Updated test route data
  - Maintained test dataset during development
  - No longer needed after test routes removed

### Activity Debugging
- **debug_activities.py** - Debugged activity fetching and parsing
  - Investigated Strava API data issues
  - Helped establish robust error handling

### GitHub Issue Management Scripts (Archived 2026-05-06)
- **create_issues.sh** - One-time issue creation script
  - Created initial GitHub issues from TODO lists
  - Superseded by intelligent issue management
  
- **create_p2_issues.sh** - One-time P2 priority issue creation
  - Created batch of P2 priority issues
  - No longer needed after initial setup
  
- **create_uiux_epic_issues_temp.sh** - Temporary UI/UX epic creation
  - Created UI/UX improvement epic and related issues
  - Temporary script for one-time use
  
- **create_v2.5.0_issue_updates.sh** - One-time v2.5.0 issue updates
  - Updated issues for v2.5.0 release
  - Version-specific, no longer needed
  
- **cleanup-issue-titles.sh** - One-time issue title cleanup
  - Cleaned up inconsistent issue titles
  - Completed, no longer needed
  
- **close-duplicate-issues.sh** - One-time duplicate issue closure
  - Closed duplicate GitHub issues
  - Completed, no longer needed

## Why Archived?

These scripts served their purpose during development:
- ✅ Investigations completed
- ✅ Findings incorporated into main codebase
- ✅ Issues resolved
- ✅ Algorithms finalized

They are kept for:
- Historical reference
- Understanding past debugging approaches
- Potential future similar investigations

## Active Test/Debug Scripts

The following scripts remain in the root directory as they're still useful:

- `test_imports.py` - Validates Python syntax
- `test_geocoding.py` - Tests geocoding functionality
- `test_route_naming.py` - Tests route naming logic
- `test_long_ride_recommendations.py` - Tests long ride features
- `fetch_test_activities.py` - Fetches test data from Strava
- `profile_analysis.py` - Performance profiling
- `verify_dependencies.py` - Dependency validation

---

**Last Updated:** 2026-05-06
**Archived By:** Bob (AI Assistant)