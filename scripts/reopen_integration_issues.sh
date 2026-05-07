#!/bin/bash
# Script to reopen Integration Squad issues #138, #139, #140
# These were closed prematurely with only stub implementations

set -e

echo "=========================================="
echo "Reopening Integration Squad Issues"
echo "=========================================="
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"
echo ""

# Issue #138 - Weather Integration
echo "📋 Reopening Issue #138: Weather Integration"
gh issue reopen 138 --comment "**REOPENING: Stub Implementation Discovered**

This issue was closed prematurely with only a stub implementation. The current code in \`app/services/weather_service.py\` contains placeholder methods that return None or False.

**Current State:**
- ❌ Stub implementation only
- ❌ No actual weather API integration
- ❌ No weather scoring algorithm
- ❌ No unit tests

**Required for Completion:**
- [ ] Replace stub with real WeatherService
- [ ] Integrate with weather API (Open-Meteo)
- [ ] Implement weather scoring algorithm
- [ ] Add comprehensive unit tests (80%+ coverage)
- [ ] Create integration tests
- [ ] Submit PR for code review
- [ ] Merge PR to main branch

**Reference:**
- See [DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md)
- See [CROSS_SQUAD_COORDINATION_URGENT.md](../CROSS_SQUAD_COORDINATION_URGENT.md)

**Priority:** P1-high (blocks QA testing)
**Squad:** Integration Squad
**Estimated Effort:** 1-2 weeks"

echo "✅ Issue #138 reopened"
echo ""

# Issue #139 - TrainerRoad Integration
echo "📋 Reopening Issue #139: TrainerRoad Integration"
gh issue reopen 139 --comment "**REOPENING: Stub Implementation Discovered**

This issue was closed prematurely with only a stub implementation. The current code in \`app/services/trainerroad_service.py\` contains placeholder methods that return \`{'status': 'unavailable'}\`.

**Current State:**
- ❌ Stub implementation only
- ❌ No ICS feed parser
- ❌ No workout normalization
- ❌ No unit tests

**Required for Completion:**
- [ ] Replace stub with real TrainerRoadService
- [ ] Implement ICS feed parser
- [ ] Add workout normalization logic
- [ ] Add comprehensive unit tests (80%+ coverage)
- [ ] Create integration tests
- [ ] Submit PR for code review
- [ ] Merge PR to main branch

**Reference:**
- See [DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md)
- See [CROSS_SQUAD_COORDINATION_URGENT.md](../CROSS_SQUAD_COORDINATION_URGENT.md)

**Priority:** P1-high (blocks QA testing)
**Squad:** Integration Squad
**Estimated Effort:** 1-2 weeks"

echo "✅ Issue #139 reopened"
echo ""

# Issue #140 - Workout-Aware Commute Recommendations
echo "📋 Reopening Issue #140: Workout-Aware Commute Recommendations"
gh issue reopen 140 --comment "**REOPENING: Stub Implementation Discovered**

This issue was closed prematurely without any actual implementation. This feature depends on #139 (TrainerRoad Integration) being completed first.

**Current State:**
- ❌ No implementation exists
- ❌ Depends on #139 (TrainerRoad stub)
- ❌ No workout fit algorithm
- ❌ No unit tests

**Required for Completion:**
- [ ] Complete #139 first (TrainerRoad Integration)
- [ ] Implement workout fit algorithm
- [ ] Integrate with commute recommendations
- [ ] Add comprehensive unit tests (80%+ coverage)
- [ ] Create integration tests
- [ ] Submit PR for code review
- [ ] Merge PR to main branch

**Reference:**
- See [DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md)
- See [CROSS_SQUAD_COORDINATION_URGENT.md](../CROSS_SQUAD_COORDINATION_URGENT.md)

**Priority:** P1-high (blocks QA testing)
**Squad:** Integration Squad
**Estimated Effort:** 1-2 weeks (after #139 complete)
**Blocked By:** #139"

echo "✅ Issue #140 reopened"
echo ""

# Add labels
echo "🏷️  Adding labels to reopened issues..."
gh issue edit 138 --add-label "P1-high,integration,in-progress,blocked"
gh issue edit 139 --add-label "P1-high,integration,in-progress,blocked"
gh issue edit 140 --add-label "P1-high,integration,blocked"

echo "✅ Labels added"
echo ""

echo "=========================================="
echo "✅ All Integration Squad issues reopened"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Integration Squad must provide realistic timeline"
echo "2. Create implementation plan with acceptance criteria"
echo "3. Submit PRs for code review (mandatory)"
echo "4. QA Squad can resume testing after PRs merged"
echo ""
echo "See CROSS_SQUAD_COORDINATION_URGENT.md for full details"

# Made with Bob
