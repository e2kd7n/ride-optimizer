# AGENTS.md

This file provides guidance to agents when working with code in this repository.

Please also refer to CLAUDE.md for direction. In the event of a conflict - explain the conundrum and ask the user how to proceed. 

## ⚠️ CRITICAL ARCHITECTURE RULES ⚠️

> **Updated 2026-07-18.** The architecture below superseded an earlier `static/`-only
> UI (see "The Epic #237 Mistake" historical note below) when pages were migrated to
> Jinja templates under `templates/` (#470). If you find an older doc, plan, or issue
> that says "the web app uses `static/` files, `templates/` is deprecated" — that is
> now backwards. Trust this file and `CLAUDE.md` over anything else.

### Product Vision: WEB APPLICATION (NOT CLI Tool)

**THE PRODUCT IS A WEB APPLICATION. Period.**

- ✅ **Active System:** `launch.py` (CLI entry, port 8083) → `app/factory.py` → `app/api/*_bp.py` + `templates/*.html` (Jinja-rendered pages) + `static/js`, `static/css` + `app/services/`
- ❌ **Deprecated System:** `main.py` (CLI-only data analysis; do not extend for web features)

### Where to Make Changes

#### ✅ FOR WEB APP UI/UX WORK (CORRECT):
```
templates/index.html        # Home page
templates/routes.html       # Routes library
templates/route-detail.html # Route detail
templates/compare.html      # Route comparison
templates/explore.html      # Explore / new-tile routing
templates/reports.html      # Reports
templates/settings.html     # Settings
templates/weather.html      # Weather
templates/partials/         # Shared navbar/bottom-nav/theme-init markup (#470)
static/commute.html         # Commute recommendations (standalone, no shared nav)
static/setup.html           # First-run setup (standalone)
static/css/main.css         # Styles
static/js/*.js              # Client-side logic
app/api/*_bp.py             # API route handlers (9 Blueprints)
app/services/*.py           # Business logic
app/container.py            # ServiceContainer (wave-parallel init)
launch.py                   # CLI entry point only
```

#### ❌ NEVER EDIT THESE FOR UI/UX (WRONG):
```
main.py                     # CLI tool - not for UI work
```

### The Epic #237 Mistake (May 2026) — historical, architecture has since changed

**What Happened:**
- Epic #237 (UI/UX Redesign, 14 issues, 40-60 hours) was implemented in `templates/report_template.html`
- At the time, that was the DEPRECATED CLI system — the web app used `static/` files
- Result: All work was wasted and needs to be redone

**Cost:** 40-60 hours of misdirected development

**Root Cause:** Insufficient deprecation warnings (now fixed)

**Note:** This incident is why earlier revisions of this doc warned "never edit `templates/`."
That warning is now **obsolete** — `templates/` was later adopted (#470) as the real, live
location for page markup, and the pre-#470 `static/dashboard.html` / `static/routes.html` /
`static/planner.html` pages it replaced no longer exist. Don't apply the old warning to
today's `templates/` directory.

### Architecture Decision Tree

**If implementing a UI/UX feature:**
1. Is it a full page? → Edit the matching file in `templates/` (or `static/commute.html` / `static/setup.html` for the two pages that don't use shared nav)
2. Is it client-side behavior/styling? → Edit `static/js/*.js` / `static/css/main.css`
3. Is it for API endpoints? → Edit the relevant `app/api/*_bp.py` Blueprint
4. Is it for business logic? → Edit `app/services/`
5. Is it for CLI data analysis? → Edit `main.py` and `src/*.py`

### Web App Architecture (ACTIVE)

> **Blueprint refactor complete (Epic #413).** All route handlers live in `app/api/` Blueprints.
> **Factory consolidation complete (#460):** `app/factory.py::create_app()` is the only
> app factory — the older `app/__init__.py::create_app()` / `app/config.py` pair was deleted.

```
User Browser
    ↓
launch.py (CLI entry point only)
    ↓
app/factory.py (create_app)
    ↓
app/container.py (ServiceContainer, wave-parallel init; refresh_services(*names)
                   does a granular re-init of just the affected service(s) — #461)
    ↓
Page routes (registered directly in app/factory.py, Jinja-rendered from templates/)
app/api/*_bp.py (9 Blueprints — all JSON API routes)
    weather_bp.py      /api/weather/*
    commute_bp.py      /api/commute, /api/recommendation, /api/workout-options
    routes_bp.py       /api/routes/*
    planner_bp.py      /api/planner/*, /api/exploration/*, /api/geocode
    strava_bp.py       /api/strava/*, /api/setup/*
    integrations_bp.py /api/intervals/*, /api/ors/*, /api/garmin/*, /api/trainerroad/*
    data_bp.py         /api/analyze/*, /api/fetch/*, /api/activities
    stats_bp.py        /api/stats/*
    core_bp.py         /api/status, /api/settings/*, /api/plans/*, /api/user/*
    maps_api.py        /api/maps/* (registered separately, not counted in the 9)
    ↓
app/services/*.py (business logic — unchanged)
    ↓
data/*.json (cached data)
```

### CLI Tool Architecture (data-analysis only, not for UI)
```
User Terminal
    ↓
main.py --analyze
    ↓
Uses: src/*.py (analysis logic)
    ↓
Generates via: legacy/report_generator.py (moved out of src/, #467/#508 —
               PDF/QR export; requires manually-installed weasyprint/qrcode extras)
    ↓
Outputs: output/report.html (static file)
```

**The CLI tool is ONLY for data analysis, NOT for UI/UX work.**


## ⚠️ SECURITY & PRIVACY GUARDRAILS (MANDATORY) ⚠️

### The Coordinate Leak Incident (2026-07-07)

**What happened:** The maintainer's real home/work GPS coordinates were hardcoded in `config/config.yaml` (a tracked file) since commit `3ea7ec8` (#77) and sat in plaintext on the **public** repo for months, alongside full-resolution GPS route traces from a debug script (`archive/debug_scripts/test_route_*_coords.json`) and old cache snapshots with real geocoded addresses. Separately, an audit found the codebase's own privacy tooling (`SecureLogger`/`pii_sanitizer.py`, `SecureCacheStorage`) was applied to only ~8 of 30+ modules that log or cache location/PII data — the rest used plain `logging.getLogger`/raw `json.dump`, silently bypassing the protection that exists.

**Cost:** Full git history rewrite (`git filter-repo`) across every branch/tag, force-push, and a since-invalidated set of commit hashes for anyone with an existing clone or fork.

**Root cause:** Sensitive values were hardcoded directly into a tracked file instead of using the `${VAR}` env-substitution pattern that already existed in the same file for other secrets (`STRAVA_CLIENT_ID`, etc.). Debug output containing real data was committed instead of being written to a gitignored path. Security/privacy helper classes were built once and never enforced as the required pattern for new code.

**Prevention — these rules are not optional:**

1. **Never hardcode a real coordinate, address, name, token, or key into a file that's tracked by git** — not even in a comment, example, or "temporary" debug script. `config/config.yaml` is tracked; secrets and PII-adjacent values (home/work lat/lon, API keys, tokens) go in `.env` (gitignored) and are referenced via `${VAR_NAME}` — the pattern already used for `STRAVA_CLIENT_ID`/`STRAVA_CLIENT_SECRET`. Before committing any change to `config/config.yaml` or any other tracked config file, re-read the diff specifically looking for float literals that could be real coordinates, or any value that looks like a real credential.
2. **Debug/analysis scripts that touch real user data (activities, routes, coordinates) must write output to a gitignored path** (e.g. under `data/` or a scratch dir already covered by `.gitignore`) — never to a path that will be `git add`ed, even under `archive/` or `docs/`. If a debug artifact with real data was already committed by mistake, it needs a history purge, not just a follow-up commit that deletes it — deleting in a new commit leaves the data recoverable from history.
3. **All new logging must use `SecureLogger`, never plain `logging.getLogger`.** Any module that could conceivably touch GPS coordinates, addresses, activity/athlete IDs, tokens, or credentials must do `from src.secure_logger import SecureLogger; logger = SecureLogger(__name__)`. When formatting a Strava ID into a log message, use the `activity_id=<id>`/`athlete_id=<id>` shape (with `=` or `:`) so `pii_sanitizer.sanitize_strava_id`'s regex actually matches it — `f"activity {id}"` (no separator) silently does NOT get sanitized even through `SecureLogger`.
4. **If you add a new cache file that stores GPS coordinates, addresses, or route data, it must get 0o600 permissions** — use `JSONStorage` (sets this automatically) or, if you write via a bare `json.dump()`/`Path.write_text()`, call `secure_chmod()` from `src/json_storage.py` right after the write. This codebase deliberately relies on OS file permissions rather than at-rest encryption for cache files (`src/secure_cache.py`'s `SecureCacheStorage` was removed as unused dead code — see `GHSA-ffw6-3927-gq93`) — don't add a new encrypted-cache scheme without discussing it first, and don't silently skip the permissions call either.
5. **Security scaffolding must be verified as actually enforced, not just present.** If you wire up `CSRFProtect`, an encryption key generator, a validator, etc., write or run a quick check that it actually fires on the code path you think it protects (e.g. does the route actually reject a request without a valid token?) — don't assume presence of the class/decorator/import means the protection is active.
6. **Never log a generated secret/key value itself.** When a key-generation code path logs "generated a new key," log the file path to retrieve it from, never the key material in the log message.
7. **Any server-side fetch of a user-supplied URL needs SSRF hardening** — restrict scheme to `http`/`https`, and reject hostnames that resolve to private/loopback/link-local ranges, checked at fetch time (not just when the URL is first saved, since DNS can rebind between save and use).
8. **Before marking any task complete that touched config files, logging, caching, or URL-fetching code, ask: "would this diff be safe if the repo is public?"** — because this one is.


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
- [ ] **No real secrets/PII in the diff** (see SECURITY & PRIVACY GUARDRAILS) — check any touched config file, debug/test fixture, or log statement
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
- **See "SECURITY & PRIVACY GUARDRAILS" above first** — mandatory rules, not just background info.
- **Credential validation is mandatory**: App exits immediately if `STRAVA_CLIENT_ID` or `STRAVA_CLIENT_SECRET` are missing/invalid in `.env`
- **Encrypted storage**: Tokens stored in `config/credentials.json` are encrypted using Fernet (key auto-generated in `config/.token_encryption_key`). Cache files under `cache/`/`data/` are **not** encrypted — `SecureCacheStorage` was removed as unused dead code (`GHSA-ffw6-3927-gq93`); the deliberate baseline for caches is 0o600 file permissions, not encryption. Don't assume a cache file is protected beyond that.
- **Security audit logging**: All auth events logged to `logs/security_audit.log` (separate from main logs)
- **File permissions**: Cache and credential files automatically set to 0600 (owner read/write only) — on Linux/the Pi; Windows dev checkouts can't enforce the permission bits, so don't treat a passing local permissions check as proof it works in production. Cross-process write locking (`JSONStorage`'s POSIX `fcntl.flock`) does have a Windows equivalent now (`msvcrt.locking`, plus a rename retry for transient antivirus/indexer `PermissionError`s — #504) — that part works cross-platform even though the permission bits don't.

### Cache Behavior (Non-Standard)
- **Cache merging by default**: `--fetch` merges with existing cache, NOT replaces (use `--replace-cache` to clear)
- **Separate test cache**: Tests use `cache/test_activities_cache.json`, production uses `cache/activities_cache.json`
- **SHA256 for cache keys**: All cache keys use SHA256 (MD5 was replaced for security)
- **Cache file permissions**: Every cache writer must end up at 0o600 — automatic via `JSONStorage`, or via an explicit `secure_chmod()` call (`src/json_storage.py`) for bare `json.dump()` writers. No cache encryption layer exists by design (see Security & Authentication above).

### Route Analysis Algorithm
- **Shared comparison math**: `route_analyzer.py` and `long_ride_analyzer.py` both delegate similarity math to `src/route_comparison.py` (#507) — change Fréchet/Hausdorff comparison logic there, not in either caller.
- **Fréchet distance primary**: Uses `similaritymeasures` library for route matching (NOT Hausdorff alone)
- **Dual validation**: Fréchet (300m threshold) + Hausdorff (0.50 threshold) for route similarity
- **Percentile-based outlier tolerance**: Uses 95th percentile in Hausdorff to ignore GPS glitches
- **Parallel processing**: Route grouping supports 1-8 workers via `--parallel` flag (default: 2)
- **Route naming**: Segment-based naming samples 10 points along route (configurable in `config.yaml`)

### Testing Requirements
- **Test markers**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- **Run single test**: `pytest tests/test_module.py::TestClass::test_method -v`
- **Coverage**: `./scripts/run-tests.sh coverage` generates HTML report in `htmlcov/`
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
- **Run tests**: `./scripts/run-tests.sh [all|unit|integration|coverage|quick]`

## Issue Management (Project-Specific)

### Priority System (Release-Aware)
**CRITICAL CHANGE:** Priority is now WITHIN a release. A P1 issue in the next release takes precedence over a P0 issue in a future release.

**Work Order Priority:**
1. **Next Release P0** - Drop everything
2. **Next Release P1** - Current sprint focus
3. **Next Release P2** - Next sprint planning
4. **Next Release P3** - Backlog for this release
5. **Future Release P0** - Plan for future critical work
6. **Future Release P1+** - Long-term planning

**Priority Definitions (Within a Release):**
- **P0-critical**: Blocks release deployment, app down, data loss, security vulnerabilities
- **P1-high**: Must complete before release - core features broken, significant pain points
- **P2-medium**: Should complete for release - enhancements, moderate pain points
- **P3-low**: Can defer to next release if needed - minor improvements, edge cases
- **P4-future**: Explicitly deferred to later releases - new features, major enhancements

### GitHub Labels Cache
**IMPORTANT:** Use `.bob/github_labels.md` for available labels - updated weekly during maintenance.

Common label combinations:
- Bug reports: `P1-high,bug,backend`
- UI/UX enhancements: `P2-medium,enhancement,ux,design,frontend`
- Accessibility: `P1-high,accessibility,a11y,WCAG`
- Performance: `P2-medium,performance,backend`
- Documentation: `P3-low,documentation,help`

**Do NOT query GitHub for labels** - use the cache to avoid failed issue creation.

### Issue Workflow (Release-Aware)
- **Assign to milestone FIRST**: `gh issue edit <num> --milestone "v0.13.0"` - every issue needs a target release
- **Then set priority**: `gh issue create --label "P1-high,bug"` (use labels from `.bob/github_labels.md`)
- **Reference in commits**: `Fixes #123: Description` (auto-closes on merge)
- **Update priorities**: Run `./scripts/update-issue-priorities.sh` to regenerate `ISSUE_PRIORITIES.md`
- **Weekly maintenance**: Review open issues, close completed, update labels, refresh `.bob/github_labels.md`
- **Focus on next release**: Always work on next release issues before future release issues, regardless of P-label

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
- **Implementation plans**: `plans/` directory - ALL plans MUST be organized by version subdirectory

### Plans Directory Structure (MANDATORY)
All implementation plans, epics, and technical planning documents MUST be stored in `/plans/` organized by version:

```
plans/
├── README.md                           # Index of all plans
├── v0.11.0/                           # Current version plans
│   ├── README.md                      # Version overview
│   ├── INTERACTIVE_MAPS_RESTORATION_EPIC.md
│   └── ARCHITECTURE_SIMPLIFICATION_PROPOSAL.md
├── v0.12.0/                           # Future version plans
│   └── README.md
└── current/                           # Symlink to current version (optional)
    → v0.11.0/
```

**Rules:**
- **NEVER** store plans in `docs/plans/` - this location is deprecated
- **ALWAYS** determine the target version from GitHub milestones (`gh api repos/:owner/:repo/milestones`) before creating plans
- **ALWAYS** place plans in the appropriate `/plans/vX.X.X/` subdirectory
- **ALWAYS** update `/plans/README.md` when adding new plans
- Version-agnostic or cross-version plans go in the version where work begins

## Design Principles (Non-Negotiable)

**Full spec:** `plans/v0.6.0/DESIGN_PRINCIPLES.md` (v2.2). **Brand identity:** `docs/designs/FAIR_WEATHER_BRAND_BOOK.md` — logo, color tokens (Day/Night), type, and reference screens for the current "Fair Weather" brand, adopted 2026-07-05. Not yet wired into `static/css/main.css` (still on pre-rebrand tokens) — check the brand book before hand-picking a color or icon for new UI work.

### Mobile-First Approach
- Start with 320px viewport (iPhone SE)
- Touch targets minimum 44x44px
- Stack vertically on mobile, side-by-side on desktop
- **On `lg`+ desktop viewports, map controls/lists go beside the map, not stacked above or below it** (new in v2.2 — see DESIGN_PRINCIPLES.md §3)
- Test on real devices, not just emulators

### Semantic Color System (Fair Weather, v2.2 — see brand book for Night-mode values)
- **Cobalt (`#0B6FA6`)**: Brand, structure, links, informational — NOT `#667eea`/`#764ba2`, which are retired
- **Coral (`#F2662D`)**: Reserved for exactly one CTA/badge per screen — never used structurally
- **Green (`#3E8E63`)**: Optimal routes, favorable conditions, good fit
- **Red (`#C4483A`)**: Unfavorable conditions, warnings, poor fit
- **Amber (`#C98A1D`)**: Neutral conditions, caution
- All colors WCAG AA compliant for accessibility

### Progressive Disclosure
- Show 3 primary metrics by default (duration, distance, score)
- Use "Show More" buttons for additional details
- Collapse secondary information by default
- Avoid information overload on initial view
- **Weather cards show wind and precipitation whenever available, not temperature alone** (new in v2.2 — see DESIGN_PRINCIPLES.md §2)

## Shared Pi Infrastructure

### Pi Health Stats File

A snapshot of the Pi's hardware, OS, containers, services, and performance is written to `/home/admin/pi-stats.txt` by cron jobs installed from the `couponclipper` project (`scripts/pi-diag.sh`). Updated daily at 3am and on every reboot (45s after boot).

Reference this file when:
- Diagnosing memory pressure or CPU spikes affecting this app
- Checking container inventory before deploying a new image
- Identifying optimization opportunities (disk usage, image sizes, running services)
- Verifying what else is running on the Pi that could compete for resources

```bash
cat ~/pi-stats.txt                          # full report
grep -A 30 "CONTAINER RUNTIME" ~/pi-stats.txt
grep -A 10 "QUICK HEALTH CHECK" ~/pi-stats.txt
```