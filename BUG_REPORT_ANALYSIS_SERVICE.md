# P0 Bug: AnalysisService Has Multiple Initialization Errors

## Severity: P0-Critical
**Discovered**: 2026-05-06 during QA Squad unit testing
**Impact**: AnalysisService cannot be instantiated - breaks entire analysis workflow

## Problems

### 1. StravaDataFetcher Initialization (Line 44)

`app/services/analysis_service.py` line 44 attempts to initialize `StravaDataFetcher` incorrectly:

```python
# Current (BROKEN):
self.data_fetcher = StravaDataFetcher(config)
```

But `src/data_fetcher.py` line 124 shows the actual signature:

```python
def __init__(self, client: Client, config, use_test_cache: bool = False):
```

**Missing**: The required `client` parameter (authenticated Strava Client object)

### 2. LocationFinder Initialization (Line 50)

`app/services/analysis_service.py` line 50 attempts to initialize `LocationFinder` incorrectly:

```python
# Current (BROKEN):
self.location_finder = LocationFinder(config)
```

But `src/location_finder.py` line 36 shows the actual signature:

```python
def __init__(self, activities: List[Activity], config):
```

**Missing**: The required `activities` parameter

## Root Cause

Foundation Squad created `AnalysisService` without understanding the dependency requirements of `StravaDataFetcher`. This suggests:

1. **No unit tests were written** for AnalysisService during development
2. **Integration testing was incomplete** - service was never actually instantiated
3. **Code review missed the signature mismatch**

## Impact

- AnalysisService cannot be instantiated
- All routes depending on AnalysisService will fail at runtime
- Dashboard, analysis endpoints, scheduler jobs all broken
- **This should have been caught in Foundation Squad testing**

## Evidence

Test failure:
```
TypeError: StravaDataFetcher.__init__() missing 1 required positional argument: 'config'
```

## Recommended Fix

### Option 1: Pass Client to AnalysisService (Preferred)
```python
class AnalysisService:
    def __init__(self, config: Config, client: Client):
        self.config = config
        self.client = client
        self.data_fetcher = StravaDataFetcher(client, config)
```

### Option 2: Create Client Inside AnalysisService
```python
class AnalysisService:
    def __init__(self, config: Config):
        self.config = config
        # Create authenticated client
        from src.auth import get_authenticated_client
        self.client = get_authenticated_client(config)
        self.data_fetcher = StravaDataFetcher(self.client, config)
```

**Recommendation**: Option 1 (dependency injection) is better for testability

## Related Issues

This is the **4th P0/P1 architectural issue** discovered during QA testing:

1. Missing `icalendar` dependency (P0) - Fixed
2. Missing `WeatherSnapshot` model (P0) - Stubbed temporarily
3. Tight coupling between services (P1) - Documented
4. **AnalysisService initialization bug (P0)** - This issue

## Action Required

1. **Immediate**: Fix AnalysisService initialization
2. **Update all routes** that create AnalysisService instances
3. **Update scheduler jobs** that use AnalysisService
4. **Add unit tests** to prevent regression
5. **Review other services** for similar issues

## Testing Notes

QA Squad will work around this by mocking the initialization in tests, but **production code is broken** and needs immediate fix from Foundation Squad.

---
**Status**: Open - Blocking QA testing
**Assigned**: Foundation Squad
**Priority**: P0-Critical