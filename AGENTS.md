# AGENTS.md

This file provides guidance to agents when working with code in this repository.
## ⚠️ CRITICAL ARCHITECTURE RULES ⚠️

### Product Vision: WEB APPLICATION (NOT CLI Tool)

**THE PRODUCT IS A WEB APPLICATION. Period.**

- ✅ **Active System:** `launch.py` (port 8083) + `static/` files + `app/services/`
- ❌ **Deprecated System:** `main.py` + `templates/` (archived to `archive/deprecated_cli_system/`)

### Where to Make Changes

#### ✅ FOR WEB APP UI/UX WORK (CORRECT):
```
static/dashboard.html       # Home page
static/routes.html          # Routes library
static/commute.html         # Commute recommendations
static/planner.html         # Long ride planner
static/css/main.css         # Styles
static/js/*.js              # Client-side logic
launch.py                   # API endpoints
app/services/*.py           # Business logic
```

#### ❌ NEVER EDIT THESE FOR UI/UX (WRONG):
```
archive/deprecated_cli_system/templates/*  # DEPRECATED - archived
main.py                                     # CLI tool - not for UI work
```

### The Epic #237 Mistake (May 2026)

**What Happened:**
- Epic #237 (UI/UX Redesign, 14 issues, 40-60 hours) was implemented in `templates/report_template.html`
- This is the DEPRECATED CLI system
- The web app uses `static/` files
- Result: All work was wasted and needs to be redone

**Cost:** 40-60 hours of misdirected development

**Root Cause:** Insufficient deprecation warnings (now fixed)

**Prevention:**
1. Templates archived to `archive/deprecated_cli_system/`
2. Strong warnings added to `main.py`
3. This section added to AGENTS.md
4. Issue #257 created to port Epic #237 to correct system

### Architecture Decision Tree

**If implementing a UI/UX feature:**
1. Is it for the web app? → Edit `static/` files
2. Is it for API endpoints? → Edit `launch.py`
3. Is it for business logic? → Edit `app/services/`
4. Is it for CLI data analysis? → Edit `main.py` (but NOT templates)

**If you see "templates/" in an issue:**
- STOP and ask for clarification
- The issue may be misdirected
- Templates are deprecated for UI work

### Web App Architecture (ACTIVE)
```
User Browser
    ↓
launch.py (Flask API on port 8083)
    ↓
Serves: static/*.html (client-side rendering)
    ↓
Calls: /api/weather, /api/recommendation, /api/routes, /api/status
    ↓
Uses: app/services/*.py (business logic)
    ↓
Reads: data/*.json (cached data)
```

### CLI Tool Architecture (DEPRECATED FOR UI)
```
User Terminal
    ↓
main.py --analyze
    ↓
Uses: src/*.py (analysis logic)
    ↓
Generates: archive/deprecated_cli_system/templates/report_template.html
    ↓
Outputs: output/report.html (static file)
```

**The CLI tool is ONLY for data analysis, NOT for UI/UX work.**


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

### Post-Completion Checklist (MANDATORY)
After marking any task complete:
- [ ] All tests passing
- [ ] Code reviewed (if applicable)
- [ ] **GitHub issues closed with detailed comments**
- [ ] **ISSUE_PRIORITIES.md updated**
- [ ] **Epic child issues verified closed (if applicable)**
- [ ] Documentation updated
- [ ] Changes committed with proper message format

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

### GitHub Labels Cache
**IMPORTANT:** Use `.bob/github_labels.md` for available labels - updated weekly during maintenance.

Common label combinations:
- Bug reports: `P1-high,bug,backend`
- UI/UX enhancements: `P2-medium,enhancement,ux,design,frontend`
- Accessibility: `P1-high,accessibility,a11y,WCAG`
- Performance: `P2-medium,performance,backend`
- Documentation: `P3-low,documentation,help`

**Do NOT query GitHub for labels** - use the cache to avoid failed issue creation.

### Issue Workflow
- **Create issues via**: `gh issue create --label "P1-high,bug"` (use labels from `.bob/github_labels.md`)
- **Reference in commits**: `Fixes #123: Description` (auto-closes on merge)
- **Update priorities**: Run `./scripts/update-issue-priorities.sh` to regenerate `ISSUE_PRIORITIES.md`
- **Weekly maintenance**: Review open issues, close completed, update labels, refresh `.bob/github_labels.md`

### Issue Closure Protocol (CRITICAL)
After completing and testing any work:
1. **Immediately close related issues** - don't wait for weekly maintenance
2. **Use detailed closure comments** with commit reference and acceptance criteria checklist
3. **For epics**: Verify ALL child issues are closed before closing parent
4. **Update ISSUE_PRIORITIES.md** by running `./scripts/update-issue-priorities.sh`
5. **Verify closure** by checking issue no longer appears in priorities file

**Closure Comment Template:**
```
Completed in commit [hash] - [title]

✅ [Acceptance criterion 1]
✅ [Acceptance criterion 2]
✅ [Acceptance criterion 3]

Files modified: [list]
Tests added: [list]
```

**Example Commands:**
```bash
# Close single issue with comment
gh issue close 123 --comment "Completed in commit abc123 - Fixed authentication bug

✅ Users can now log in successfully
✅ Session tokens persist correctly
✅ Added integration tests

Files modified: src/auth.py, tests/test_auth.py"

# Close multiple related issues
gh issue close 228 229 230 --comment "Completed as part of Epic #235"

# Verify closure
./scripts/update-issue-priorities.sh
```

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