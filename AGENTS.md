# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Workflow Orchestration

### Parallel Operation
- **Use subagents/new tasks liberally** to keep main context window clean
- **Offload research, exploration, and parallel analysis** to separate task instances
- **For complex problems, throw more compute at it** via parallel tasks
- **One focused objective per task** for clear execution

### Planning & Verification
- **Enter plan mode for ANY non-trivial task** (3+ steps or architectural decisions)
- **If something goes sideways, STOP and re-plan** immediately - don't keep pushing
- **Never mark a task complete without testing** to prove that it works
- **Ask yourself: "Would a staff engineer approve this?"**

### Continuous Improvement
- **After ANY correction from the user**: document the pattern and lesson learned
- **Write rules for yourself** that prevent the same mistake
- **Ruthlessly iterate on these lessons** until mistake rate drops

## Critical Non-Obvious Patterns

### Security & Authentication
- **Credential validation is mandatory**: App exits immediately if `STRAVA_CLIENT_ID` or `STRAVA_CLIENT_SECRET` are missing/invalid in `.env`
- **Encrypted storage**: Tokens stored in `config/credentials.json` and cache in `cache/` are encrypted using Fernet (keys auto-generated in `config/.token_encryption_key` and `config/.cache_encryption_key`)
- **Security audit logging**: All auth events logged to `logs/security_audit.log` (separate from main logs)
- **File permissions**: Cache and credential files automatically set to 0600 (owner read/write only)

### Cache Behavior (Non-Standard)
- **Cache merging by default**: `--fetch` merges with existing cache, NOT replaces (use `--replace-cache` to clear)
- **Separate test cache**: Tests use `cache/test_activities_cache.json`, production uses `cache/activities_cache.json`
- **SHA256 for cache keys**: All cache keys use SHA256 (MD5 was replaced for security)
- **Encrypted cache storage**: Use `SecureCacheStorage` from `src/secure_cache.py` for PII protection

### Route Analysis Algorithm
- **Fréchet distance primary**: Uses `similaritymeasures` library for route matching (NOT Hausdorff alone)
- **Dual validation**: Fréchet (300m threshold) + Hausdorff (0.50 threshold) for route similarity
- **Percentile-based outlier tolerance**: Uses 95th percentile in Hausdorff to ignore GPS glitches
- **Parallel processing**: Route grouping supports 1-8 workers via `--parallel` flag (default: 2)
- **Route naming**: Segment-based naming samples 10 points along route (configurable in `config.yaml`)

### Testing Requirements
- **Test markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Run single test**: `pytest tests/test_module.py::TestClass::test_method -v`
- **Coverage**: `./scripts/run_tests.sh coverage` generates HTML report in `htmlcov/`
- **Test isolation**: Each test must use separate cache files to avoid conflicts

### Configuration System
- **Environment variable substitution**: Config uses `${VAR_NAME}` syntax, replaced at runtime
- **Dot notation access**: Use `config.get('strava.client_id')` for nested keys
- **Validation on startup**: Config validates all required env vars exist before proceeding

### macOS-Specific
- **Homebrew lib path**: `main.py` adds `/opt/homebrew/lib` to `DYLD_LIBRARY_PATH` for WeasyPrint
- **Python 3.9+**: Project requires Python 3.9+ (specified in `pyrightconfig.json`)

### Data Model Quirks
- **Activity timestamps**: Always ISO format strings, NOT datetime objects in dataclasses
- **Coordinates**: Stored as `List[Tuple[float, float]]` (lat, lng), NOT numpy arrays
- **Sport type handling**: Use `sport_type` field (more specific) over `type` field when available
- **Polyline encoding**: Routes use encoded polyline strings, decode with `polyline.decode()`

### Commands
- **Auth first time**: `python main.py --auth` (opens browser, starts local server on port 8000)
- **Fetch with date range**: When both `--from-date` and `--to-date` specified, `--limit` is ignored (fetches ALL in range)
- **Parallel analysis**: `python main.py --analyze --parallel 4` (1-8 workers)
- **Run tests**: `./scripts/run_tests.sh [all|unit|integration|coverage|quick]`

## Issue Management (Project-Specific)

### Priority System
- **P0-critical**: Drop everything (app down, data loss, security)
- **P1-high**: Current sprint (1-2 weeks) - core features broken
- **P2-medium**: Next sprint (2-4 weeks) - enhancements
- **P3-low**: Backlog - nice-to-haves
- **P4-future**: Long-term planning

### Issue Workflow
- **Create issues via**: `gh issue create --label "P1-high,bug"`
- **Reference in commits**: `Fixes #123: Description` (auto-closes on merge)
- **Update priorities**: Run `./scripts/update-issue-priorities.sh` to regenerate `ISSUE_PRIORITIES.md`
- **Weekly maintenance**: Review open issues, close completed, update labels

### Documentation Organization
- **Technical docs**: `docs/` directory with README index
- **Release notes**: `docs/releases/v*.*/` by version
- **User guides**: `docs/guides/` for setup and features
- **Archive**: `docs/archive/` for completed analysis
- **Plans**: `plans/v*.*/` for version-specific implementation plans

## Design Principles (Non-Negotiable)

### Mobile-First Approach
- Start with 320px viewport (iPhone SE)
- Touch targets minimum 44x44px
- Stack vertically on mobile, side-by-side on desktop
- Test on real devices, not just emulators

### Semantic Color System
- **Green (#28a745)**: Optimal routes, favorable conditions, success
- **Red (#dc3545)**: Unfavorable conditions, warnings, danger
- **Yellow (#ffc107)**: Neutral conditions, caution
- **Blue (#007bff)**: Informational elements
- All colors WCAG AA compliant for accessibility

### Progressive Disclosure
- Show 3 primary metrics by default (duration, distance, score)
- Use "Show More" buttons for additional details
- Collapse secondary information by default
- Avoid information overload on initial view