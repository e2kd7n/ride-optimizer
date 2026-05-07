# Plan Mode Rules (Non-Obvious Only)

## Workflow Orchestration for Planning
- **Use subagents/new tasks liberally** for parallel research and analysis
- **Break plans into sprintly phases** of work with clear milestones
- **For complex problems, throw more compute at it** via parallel planning tasks
- **Write detailed specs upfront** to reduce ambiguity during implementation
- **Plans should enable autonomous execution** - minimize context switching for user

## Hidden Architectural Constraints
- **Encryption is mandatory**: All cache and credential storage MUST use Fernet encryption - no plaintext allowed
- **Security-first design**: File permissions (0600), HMAC integrity checks, and audit logging are non-negotiable
- **Stateless route analysis**: Route grouping algorithm assumes no state between runs - cache invalidation is critical

## Non-Standard Patterns That Must Be Preserved
- **Cache merging architecture**: System designed for incremental updates, NOT full replacements
- **Dual similarity metrics**: Fréchet (primary) + Hausdorff (validation) - removing either breaks accuracy
- **Percentile-based outliers**: 95th percentile tolerance in Hausdorff is intentional for GPS noise
- **Separate test/prod caches**: Test isolation requires different cache files, not just different directories

## Performance Bottlenecks Discovered
- **Route grouping is O(n²)**: Parallel processing (1-8 workers) added to mitigate - don't remove
- **Geocoding rate limits**: 1 req/sec to Nominatim - background processing required for large datasets
- **Fréchet calculation**: Expensive for long routes - caching layer in `cache/route_similarity_cache.json` is critical

## Undocumented Architectural Decisions
- **ISO timestamps in dataclasses**: Deliberate choice to avoid datetime serialization issues
- **Tuple coordinates**: `List[Tuple[float, float]]` chosen over numpy for JSON serialization
- **Encoded polylines**: Storage optimization - routes stored compressed, decoded on demand
- **Security audit log isolation**: Separate logger prevents sensitive auth events from appearing in console

## Integration Points
- **Strava API**: OAuth 2.0 with CSRF protection (state parameter) - don't simplify
- **Nominatim**: Geocoding with User-Agent requirement and rate limiting
- **Open-Meteo**: Weather API for wind analysis (no auth required)
- **WeasyPrint**: PDF generation requires Homebrew lib path on macOS

## Testing Architecture
- **Pytest markers**: Three-tier system (unit/integration/slow) enables selective test runs
- **Mock isolation**: Tests must mock external APIs and use separate cache files
- **Coverage target**: Aim for >80% coverage (tracked in `htmlcov/`)

## Design System Constraints
- **Mobile-first is mandatory**: All UI starts at 320px viewport, scales up
- **Semantic color meanings**: Green=optimal/success, Red=danger/unfavorable, Yellow=caution, Blue=info
- **Progressive disclosure pattern**: Show 3 primary metrics, hide details behind "Show More"
- **Touch targets**: Minimum 44x44px for all interactive elements
- **WCAG AA compliance**: All color combinations must pass accessibility standards

## Issue Management Architecture
- **Priority-driven development**: P0 (drop everything) → P1 (current sprint) → P2 (next sprint) → P3 (backlog) → P4 (future)
- **ISSUE_PRIORITIES.md**: Auto-generated from GitHub labels via `./scripts/update-issue-priorities.sh`
- **Weekly maintenance required**: Review open issues, close completed, update labels every Monday
- **Commit-issue linking**: Use `Fixes #123` in commits to auto-close issues on merge

## Documentation Architecture (Non-Standard)
- **Version-specific organization**: `docs/releases/v*.*/` contains per-version release notes and time tracking
- **Plans are implementation specs**: `plans/v*.*/` has detailed implementation plans, not just ideas
- **Dual archive structure**: `docs/archive/` for completed analysis, `archive/` for old code/scripts
- **Guides vs specs separation**: `docs/guides/` for user-facing, `docs/` root for technical specs