# Issue #159: Fix Improper Config Mocking

**Date:** 2026-05-07  
**Issue:** https://github.com/e2kd7n/ride-optimizer/issues/159  
**Status:** ✅ RESOLVED

---

## Problem

Tests were creating mock object directories in the project root due to improper mocking of the `Config` class. Found and removed 18 directories with names like:
- `<MagicMock name='Config().get()' id='4815575024'>`
- `<Mock name='AnalysisService().config.get()' id='4821362272'>`

### Root Cause

When `Config` is patched at the class level without properly configuring the mock's `get()` method, the mock object's string representation gets used as a directory path in code like:

```python
# src/route_namer.py line 57
os.makedirs(self.cache_dir, exist_ok=True)
```

Where `self.cache_dir` ends up being a mock object instead of the string `"cache"`.

---

## Files Fixed

### 1. tests/test_routes_dashboard.py

**Lines 208-240:** Fixed `TestGetServices.test_get_services_creates_services`
- Added proper `config.get.side_effect` configuration
- Returns actual string values instead of mock objects

**Lines 242-260:** Fixed `TestGetServices.test_get_services_caches_in_g`
- Added missing service mocks (@patch decorators)
- Added proper `config.get.side_effect` configuration
- Prevents authentication errors from real service instantiation

### 2. tests/test_routes_route_library.py

**Lines 148-177:** Fixed `TestGetServices.test_get_services_creates_new`
- Added proper `config.get.side_effect` configuration
- Returns actual string values for cache_dir, data_dir, etc.

**Lines 179-206:** Fixed `TestGetServices.test_get_services_handles_initialization_error`
- Added proper `config.get.side_effect` configuration
- Ensures error handling tests don't create mock directories

---

## Solution Pattern

### ✅ CORRECT: Properly Configure config.get()

```python
@patch('app.routes.dashboard.Config')
def test_something(self, mock_config_cls, app):
    # Create mock config instance
    mock_config = Mock()
    
    # CRITICAL: Configure get() to return actual values
    mock_config.get.side_effect = lambda key, default=None: {
        'cache_dir': 'cache',
        'data_dir': 'data',
        'route_naming.sampling_density': 10,
        'route_naming.geocoder_timeout': 10
    }.get(key, default)
    
    # Return configured mock from class constructor
    mock_config_cls.return_value = mock_config
    
    # Now test code will get real strings, not mock objects
```

### ❌ INCORRECT: Unconfigured Mock

```python
@patch('app.routes.dashboard.Config')
def test_something(self, mock_config, app):
    # BAD: config.get() returns a Mock object
    # When code does: cache_dir = config.get('cache_dir')
    # Result: cache_dir = <Mock name='config.get()' id='123'>
    # Then: os.makedirs(cache_dir) creates directory named "<Mock...>"
```

---

## Verification

### Test Results

```bash
# Dashboard tests - ALL PASS
pytest tests/test_routes_dashboard.py::TestGetServices -v
# Result: 2 passed in 1.73s

# Route library tests - ALL PASS  
pytest tests/test_routes_route_library.py::TestGetServices -v
# Result: 3 passed in 1.89s
```

### No Mock Directories Created

```bash
ls -la | grep -E "^d.*<M"
# Result: (empty - no mock directories)
```

---

## Prevention

### 1. .gitignore Protection

Already added to `.gitignore` (lines 21-23):
```gitignore
# Mock object directories (test artifacts)
<Mock*
<Magic*
```

### 2. Test Documentation

Added proper mocking pattern to test documentation showing:
- How to configure `config.get()` with `side_effect`
- Why it's critical to return actual values
- Common pitfalls to avoid

### 3. Existing Good Examples

These test files already use the correct pattern:
- `tests/test_planner_service.py` (lines 22-29)
- `tests/test_route_library_service.py` (lines 23-30)

Both use fixtures with properly configured `config.get.side_effect`.

---

## Acceptance Criteria

- [x] All tests in affected files properly mock `config.get()` return values
- [x] Run full test suite and verify no new mock directories are created
- [x] Document proper mocking patterns in test documentation
- [ ] Add test to verify `RouteNamer` initialization doesn't create unexpected directories (future enhancement)

---

## Impact

### Before Fix
- 18 mock object directories polluting project root
- Tests passing but creating filesystem artifacts
- Potential for test interference and confusion

### After Fix
- Zero mock directories created
- All tests passing cleanly
- Proper mocking pattern documented
- `.gitignore` protection in place

---

## Lessons Learned

1. **Always configure mock return values**: When mocking classes with methods that return values used as strings/paths, configure the mock to return actual values
2. **Test side effects matter**: Even if tests pass, check for filesystem side effects
3. **Good fixtures prevent issues**: Using fixtures with proper configuration (like in test_planner_service.py) prevents these problems
4. **Mock at the right level**: When patching a class, configure the instance methods, not just the class

---

**Fixed By:** QA Squad Lead (Bob)  
**Date:** 2026-05-07  
**Commits:** [To be added after commit]  
**Status:** ✅ RESOLVED - All tests passing, no mock directories created