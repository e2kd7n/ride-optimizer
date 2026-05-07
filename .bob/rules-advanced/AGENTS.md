# Advanced Mode Rules (Non-Obvious Only)

## Workflow Orchestration
- **Use subagents/new tasks liberally** to keep main context window clean
- **Offload research, exploration, and parallel analysis** to separate task instances
- **For complex problems, throw more compute at it** via parallel tasks
- **Enter plan mode for ANY non-trivial task** (3+ steps or architectural decisions)
- **Never mark a task complete without testing** to prove that it works

## Custom Utilities That Replace Standard Approaches
- **SecureCacheStorage** (`src/secure_cache.py`): MUST use for all cache operations - provides encryption, HMAC integrity, and secure file permissions (0600)
- **SecureTokenStorage** (`src/auth_secure.py`): MUST use for OAuth tokens - auto-generates encryption keys in `config/.token_encryption_key`
- **Config.get()** with dot notation: Use `config.get('strava.client_id')` NOT `config['strava']['client_id']` - supports env var substitution

## Non-Standard Patterns
- **Activity dataclass timestamps**: Store as ISO strings, NOT datetime objects - conversion happens at serialization boundary
- **Route coordinates**: Always `List[Tuple[float, float]]` (lat, lng) - never numpy arrays or other formats
- **Cache key generation**: Use SHA256 via `hashlib.sha256(data.encode()).hexdigest()` - MD5 was removed for security
- **Polyline handling**: Routes stored as encoded strings, decode with `polyline.decode()` from polyline library

## Hidden Dependencies
- **Fréchet distance**: Requires `similaritymeasures` library - falls back to Hausdorff-only if missing (logs warning)
- **WeasyPrint on macOS**: `main.py` adds `/opt/homebrew/lib` to `DYLD_LIBRARY_PATH` before imports - required for PDF generation
- **Security logging**: Separate logger `security_audit` writes to `logs/security_audit.log` - does NOT propagate to console

## Required Patterns Not Enforced by Linters
- **Test cache isolation**: Tests MUST use `cache/test_activities_cache.json`, production uses `cache/activities_cache.json`
- **File permissions**: After writing credentials/cache, MUST call `os.chmod(path, 0o600)` - not automatic
- **Config validation**: MUST call `validate_strava_credentials()` before any API operations - app exits if invalid
- **Sport type priority**: Use `activity.sport_type` (specific) over `activity.type` (generic) when available

## Testing Gotchas
- **Test markers required**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.slow` on ALL tests
- **Mock cache paths**: Tests must mock cache paths to avoid polluting production cache
- **Datetime in tests**: Use `datetime.now(timezone.utc).isoformat()` for timestamps - matches production format
- **Run single test**: `pytest tests/test_module.py::TestClass::test_method -v` (double colon syntax)

## Design Principles (Must Follow)
- **Mobile-first**: Start with 320px viewport, touch targets 44x44px minimum
- **Semantic colors**: Green (optimal/success), Red (danger/unfavorable), Yellow (caution), Blue (info)
- **Progressive disclosure**: Show 3 primary metrics, hide details behind "Show More"
- **WCAG AA compliance**: All color combinations must meet accessibility standards

## MCP & Browser Access
- Advanced mode has access to MCP tools and browser capabilities
- Use for external API research, documentation lookup, or web-based debugging