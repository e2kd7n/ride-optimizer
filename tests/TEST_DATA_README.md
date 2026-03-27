# Test Data System

## Overview

This project now uses **separate cache files** for test and production data to prevent accidental overwrites.

## Cache Files

- **Production Cache**: `data/cache/activities.json` - Your real Strava data
- **Test Cache**: `data/cache/activities_test.json` - Synthetic test data

## Setup Test Data

To create test data for running tests:

```bash
python3 tests/setup_test_data.py
```

This creates `data/cache/activities_test.json` with 12 synthetic activities representing different route variants.

## Using Test Cache in Code

When creating a `StravaDataFetcher` instance for tests:

```python
from src.data_fetcher import StravaDataFetcher

# For tests - uses test cache
fetcher = StravaDataFetcher(client, config, use_test_cache=True)

# For production - uses production cache (default)
fetcher = StravaDataFetcher(client, config)
```

## Protection Against Data Loss

The test cache system prevents:
- Test data from overwriting your real Strava activities
- Accidental loss of cached production data
- Confusion between test and production environments

## Recovering Production Data

If production data was lost, you can recover it by:

1. **Re-fetch from Strava** (recommended):
   ```bash
   python3 main.py --fetch
   ```

2. **Restore from backup** (if available):
   - Time Machine (macOS)
   - System backups
   - Git history (if tracked)

## Best Practices

1. Always use `use_test_cache=True` in test files
2. Never manually edit `data/cache/activities.json`
3. Keep test data in `activities_test.json`
4. Run `setup_test_data.py` to refresh test data
5. Add `data/cache/activities_test.json` to `.gitignore` if not already there

## Migration Notes

**March 27, 2026**: Implemented separate test cache system to prevent production data loss. Previous incident: ~2,408 real activities were overwritten by 12 test activities on March 26, 2026 at 19:20.