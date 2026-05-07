# Production Code Bugs Discovered by Unit Tests

**Date**: 2026-05-07  
**Discovered By**: QA Squad unit test development  
**Test File**: `tests/test_routes_api.py`  
**Affected File**: `app/routes/api.py`

## Summary

Unit tests for the API routes have uncovered **critical schema mismatches** between the API code and database models. The API code was written using an outdated schema that doesn't match the current `JobHistory` model.

## Bugs Discovered

### Bug #1: JobHistory Creation Uses Wrong Fields
**Location**: [`app/routes/api.py:164-168`](app/routes/api.py:164)  
**Severity**: 🔴 **CRITICAL** - Breaks `/api/sync` endpoint

```python
# Current (BROKEN) code:
job = JobHistory(
    job_type=f'sync_{source}',
    status='pending',
    description=f'Manual sync: {source} (force={force})'  # ❌ Field doesn't exist
)
```

**Issue**: `JobHistory` model requires `job_id` and `job_name` fields (both NOT NULL), but API code uses non-existent `description` field.

**Model Schema** ([`app/models/jobs.py:23-26`](app/models/jobs.py:23)):
```python
job_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
job_type = db.Column(db.String(50), nullable=False, index=True)
job_name = db.Column(db.String(200), nullable=False)
# No 'description' field exists!
```

**Fix Required**:
```python
job = JobHistory(
    job_id=f'manual_sync_{datetime.now(timezone.utc).timestamp()}',
    job_name=f'Manual Sync: {source}',
    job_type=f'sync_{source}',
    status='pending',
    triggered_by='user'
)
```

### Bug #2: Jobs List Endpoint Accesses Wrong Field
**Location**: [`app/routes/api.py:223`](app/routes/api.py:223)  
**Severity**: 🔴 **CRITICAL** - Breaks `/api/jobs` endpoint

```python
# Current (BROKEN) code:
'description': job.description,  # ❌ Attribute doesn't exist
```

**Fix Required**:
```python
'job_name': job.job_name,  # ✅ Use correct field
```

### Bug #3: Job Status Endpoint Accesses Wrong Field  
**Location**: [`app/routes/api.py:253`](app/routes/api.py:253)  
**Severity**: 🔴 **CRITICAL** - Breaks `/api/jobs/<id>` endpoint

```python
# Current (BROKEN) code:
'description': job.description,  # ❌ Attribute doesn't exist
```

**Fix Required**:
```python
'job_name': job.job_name,  # ✅ Use correct field
```

## Impact Assessment

### Affected Endpoints
1. ❌ `POST /api/sync` - Cannot create jobs (500 error)
2. ❌ `GET /api/jobs` - Cannot list jobs (500 error)  
3. ❌ `GET /api/jobs/<id>` - Cannot get job status (500 error)
4. ❌ `POST /api/jobs/<id>/cancel` - Cannot cancel jobs (500 error)

### User Impact
- **Manual sync feature completely broken**
- **Job monitoring dashboard non-functional**
- **Background job management unusable**

### Root Cause
The API routes were implemented using an old schema design that had a `description` field. When the `JobHistory` model was refactored to use `job_id` and `job_name` fields (likely in Issue #137), the API code was not updated to match.

## Test Evidence

### Failing Tests (11 total)
```
FAILED tests/test_routes_api.py::TestSync::test_sync_all_sources
FAILED tests/test_routes_api.py::TestSync::test_sync_specific_source  
FAILED tests/test_routes_api.py::TestSync::test_sync_no_body
FAILED tests/test_routes_api.py::TestJobs::test_list_all_jobs
FAILED tests/test_routes_api.py::TestJobs::test_list_jobs_filtered
FAILED tests/test_routes_api.py::TestJobs::test_list_jobs_with_limit
FAILED tests/test_routes_api.py::TestJobStatus::test_get_job_status
```

### Error Messages
```
TypeError: 'description' is an invalid keyword argument for JobHistory
AttributeError: 'JobHistory' object has no attribute 'description'
```

## Recommended Actions

### Immediate (P0)
1. ✅ **Fix API code** to use correct `JobHistory` schema
2. ✅ **Update all job creation** to include required fields
3. ✅ **Update all job serialization** to use `job_name` instead of `description`

### Short-term (P1)
4. ✅ **Add database migration** if schema changed
5. ✅ **Update API documentation** to reflect correct fields
6. ✅ **Run full test suite** to verify fixes

### Long-term (P2)
7. ✅ **Add schema validation** to prevent future mismatches
8. ✅ **Implement integration tests** for API + database
9. ✅ **Add pre-commit hooks** to catch schema issues

## Prevention

To prevent similar issues:

1. **Always update API code when models change**
2. **Run unit tests before merging model changes**
3. **Use type hints and validation** (Pydantic/Marshmallow)
4. **Implement database migration tests**
5. **Add CI/CD checks** for schema consistency

## Related Issues

- Issue #137: Scheduled Jobs and Status Tracking (likely introduced the schema change)
- Issue #99: Create Comprehensive Unit Tests (discovered these bugs)
- PR #151: Integration Squad work (may have similar issues)

## Status

- **Discovered**: 2026-05-07
- **Reported**: 2026-05-07  
- **Assigned**: TBD
- **Priority**: P0-critical
- **Estimated Fix Time**: 1-2 hours

---

**Note**: These bugs were discovered through comprehensive unit test development. This demonstrates the value of thorough testing - without these tests, these critical bugs would have made it to production and broken core functionality.