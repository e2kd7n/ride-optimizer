# Scripts & Utilities

This directory contains utility scripts, test scripts, and automation tools.

## Shell Scripts

### Testing & Development
- **run_tests.sh** - Run pytest test suite with various options
- **run_with_weasyprint.sh** - Run application with WeasyPrint for PDF generation

### GitHub Integration
- **create_issues.sh** - Create GitHub issues from templates
- **create_uiux_epic_issues_temp.sh** - Create UI/UX epic issues (temporary)
- **sync_todos_to_issues.sh** - Sync TODO items to GitHub issues

### Maintenance
- **rewrite_git_history.sh** - Git history rewriting utility (use with caution)

## Python Scripts

### Testing & Validation
- **test_geocoding.py** - Test geocoding functionality
- **test_imports.py** - Verify all imports work correctly
- **test_long_ride_recommendations.py** - Test long ride analysis
- **test_route_naming.py** - Test route naming functionality
- **verify_dependencies.py** - Check all dependencies are installed

### Data & Analysis
- **fetch_test_activities.py** - Fetch test activities from Strava
- **find_matched_routes.py** - Find and analyze matched routes
- **profile_analysis.py** - Profile application performance

## Usage

Most scripts can be run directly:

```bash
# Run tests
./scripts/run_tests.sh all

# Test geocoding
python scripts/test_geocoding.py

# Verify dependencies
python scripts/verify_dependencies.py
```

## Notes

- Shell scripts are executable (chmod +x)
- Python scripts should be run from project root
- Some scripts require Strava API credentials
- Test scripts may use test cache files

---

*Last Updated: 2026-03-27*