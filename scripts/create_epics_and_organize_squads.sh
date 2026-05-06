#!/bin/bash

# Create Epics and Organize Work Across Squads
# Generated: 2026-05-06

set -e

echo "🎯 Creating Epic Issues and Organizing Squad Work..."
echo ""

# First, apply priority labels to remaining issues
echo "📍 Applying priority labels to remaining issues..."
gh issue edit 54 --add-label "P3-low" && echo "  ✅ #54 - Weather Dashboard (will be epic)"
gh issue edit 47 --add-label "P4-future" && echo "  ✅ #47 - Side-by-Side Route Comparison"
gh issue edit 80 --add-label "P4-future" && echo "  ✅ #80 - Weather Forecast in Commute Tab"
gh issue edit 79 --add-label "P4-future" && echo "  ✅ #79 - How It Works Modal"
echo ""

# Create Web Platform Epic (P1)
echo "📋 Creating Web Platform Epic..."
gh issue create \
  --title "🌐 EPIC: Personal Web Platform Migration (v3.0.0)" \
  --label "P1-high,epic" \
  --body "## Overview
Transform ride-optimizer from CLI tool to web-based platform with interactive dashboard, planning views, and background job scheduling.

## Objectives
- Flask backend with RESTful API endpoints
- SQLite persistence layer for data management
- Interactive dashboard and planning views
- Background job scheduling with status visibility
- Weather and workout integration

## Architecture Phases

### Phase 1: Backend Infrastructure (Foundation Squad)
**Dependencies:** None - can start immediately
**Issues:**
- #129 - Create Flask app factory, route blueprints, and web-platform skeleton
- #130 - Extract shared service layer for analysis, recommendations, planner logic
- #131 - Add SQLite-backed persistence for snapshots, preferences, route summaries
- #137 - Add scheduled jobs, stage-level status visibility, freshness windows

**Deliverable:** Working Flask API with persistence and job scheduling

### Phase 2: Core Views (Frontend Squad)
**Dependencies:** Phase 1 (#129-131) must be complete
**Issues:**
- #132 - Build recommendation-first dashboard with freshness, status, workout-fit summary
- #133 - Implement commute recommendation views with alternatives, weather impact
- #134 - Build long ride planner with ride-intent presets and ranked suggestions
- #135 - Build route library browsing, filtering, and route detail pages

**Deliverable:** Interactive web interface for all core features

### Phase 3: Feature Integration (Integration Squad)
**Dependencies:** Phase 1 complete, can work in parallel with Phase 2
**Issues:**
- #136 - Implement settings and preferences page
- #138 - Integrate weather snapshots into dashboard and recommendations
- #139 - Implement optional TrainerRoad ICS ingestion
- #140 - Implement workout-aware commute recommendations
- #141 - Add repeat-a-past-ride flow and saved plan support

**Deliverable:** Full feature integration with external services

### Phase 4: Polish & Quality (QA Squad)
**Dependencies:** Phases 1-3 substantially complete
**Issues:**
- #142 - Implement responsive layout and shared navigation shell
- #143 - Create integration test suite for all workflows
- #100 - Create comprehensive integration tests
- #99 - Create comprehensive unit tests
- #101 - Update documentation for all features

**Deliverable:** Production-ready platform with full test coverage

## Squad Assignments

### Foundation Squad (Backend Infrastructure)
**Focus:** API, persistence, job scheduling
**P1 Issues:** #129, #130, #131, #137
**P2 Issues:** #89 (Data Persistence Layer)
**Timeline:** Weeks 1-3

### Frontend Squad (Core Views)
**Focus:** Dashboard, commute, planner, route library
**P1 Issues:** #132, #133, #134, #135
**P2 Issues:** #85-88 (Interactive forms, map integration)
**Timeline:** Weeks 3-6 (starts after Foundation completes #129-131)

### Integration Squad (Feature Integration)
**Focus:** Weather, workouts, settings, external services
**P1 Issues:** #136, #138, #139, #140
**P2 Issues:** #141, #82-84 (API endpoints), #127-128 (UI fixes)
**Timeline:** Weeks 3-6 (parallel with Frontend)

### QA Squad (Polish & Quality)
**Focus:** Testing, responsive design, documentation
**P1 Issues:** #99, #100, #101, #142, #143
**P2 Issues:** #90-94 (validation, rate limiting, error states, accessibility)
**Timeline:** Weeks 5-8 (starts when core features are ready)

## Success Criteria
- [ ] All API endpoints functional and documented
- [ ] All core views implemented and responsive
- [ ] Weather and workout integration working
- [ ] 80%+ test coverage
- [ ] Documentation complete
- [ ] Performance benchmarks met

## Related Issues
#129, #130, #131, #132, #133, #134, #135, #136, #137, #138, #139, #140, #141, #142, #143, #99, #100, #101

## Timeline
**Target:** 8 weeks
**Milestone:** v3.0.0
**Release Date:** TBD based on squad progress"

echo "  ✅ Created Web Platform Epic"
echo ""

# Create Weather Dashboard Epic (P3)
echo "📋 Creating Weather Dashboard Epic..."
gh issue create \
  --title "🌤️ EPIC: Weather Dashboard & Forecast Integration" \
  --label "P3-low,epic" \
  --body "## Overview
Comprehensive weather dashboard with 7-day forecasts, commute window analysis, and intelligent recommendations.

## Objectives
- Visual 7-day weather forecast display
- Morning (7-9 AM) and evening (3-6 PM) commute windows
- Weather severity indicators and icons
- Wind-based route recommendations
- Transit recommendations for poor conditions
- Optimal departure time suggestions

## Related Issues
- #54 - Weather Dashboard Implementation (parent)
- #109 - Design 7-day forecast card layout
- #110 - Add morning commute window (7-9 AM) weather display
- #111 - Add evening commute window (3-6 PM) weather display
- #112 - Add weather severity indicators (good/fair/poor/miserable icons)
- #113 - Show optimal route recommendations based on wind
- #114 - Add transit recommendations when conditions are poor
- #115 - Display optimal departure time suggestions
- #116 - Add visual weather icons and color coding
- #108 - Integrate forecast generator into main.py workflow

## Implementation Phases

### Phase 1: Forecast Display
**Issues:** #109, #110, #111, #112, #116
**Deliverable:** Visual 7-day forecast with commute windows

### Phase 2: Intelligent Recommendations
**Issues:** #113, #114, #115
**Deliverable:** Wind-based routing and transit suggestions

### Phase 3: Integration
**Issues:** #108, #54
**Deliverable:** Fully integrated weather dashboard

## Success Criteria
- [ ] 7-day forecast displayed with visual indicators
- [ ] Commute windows show relevant weather data
- [ ] Wind-based route recommendations working
- [ ] Transit alternatives suggested when appropriate
- [ ] Optimal departure times calculated

## Timeline
**Target:** 4 weeks
**Priority:** P3 (after web platform MVP)
**Dependencies:** Web platform Phase 1 complete"

echo "  ✅ Created Weather Dashboard Epic"
echo ""

# Update issue relationships
echo "📎 Linking issues to epics..."

# Link web platform issues to epic (will need to get epic number after creation)
echo "  Note: Link issues #129-143, #99-101 to Web Platform Epic manually"
echo "  Note: Link issues #54, #108-116 to Weather Dashboard Epic manually"
echo ""

# Distribute P1/P2 work across squads
echo "🏷️ Redistributing P1/P2 work across squads..."

# Move some P1 issues to P2 to balance load
echo "  Moving polish/testing issues from P1 to P2..."
gh issue edit 92 --remove-label "P1-high" --add-label "P2-medium" && echo "    ✅ #92 - Loading States → P2"
gh issue edit 93 --remove-label "P1-high" --add-label "P2-medium" && echo "    ✅ #93 - Error States → P2"
gh issue edit 94 --remove-label "P1-high" --add-label "P2-medium" && echo "    ✅ #94 - Accessibility → P2"
gh issue edit 141 --remove-label "P1-high" --add-label "P2-medium" && echo "    ✅ #141 - Repeat-a-past-ride → P2"

echo ""
echo "✅ Epic creation and squad organization complete!"
echo ""
echo "📊 Summary:"
echo "  - Created 2 epic issues (Web Platform, Weather Dashboard)"
echo "  - Organized work into 4 squads:"
echo "    • Foundation Squad: Backend infrastructure (4 P1 issues)"
echo "    • Frontend Squad: Core views (4 P1 issues)"
echo "    • Integration Squad: Feature integration (4 P1 issues)"
echo "    • QA Squad: Polish & quality (5 P1 issues)"
echo "  - Moved 4 issues from P1 to P2 to balance load"
echo "  - Applied priority labels to 4 remaining issues"
echo ""
echo "📋 Next Steps:"
echo "  1. Get epic issue numbers from GitHub"
echo "  2. Link related issues to epics using:"
echo "     gh issue edit <issue_num> --body 'Part of #<epic_num>'"
echo "  3. Create GitHub milestones for each phase"
echo "  4. Assign squad members to their respective issues"
echo "  5. Run: ./scripts/update-issue-priorities.sh > ISSUE_PRIORITIES.md"
echo ""
echo "🎯 Squad Work Distribution:"
echo ""
echo "Foundation Squad (Weeks 1-3):"
echo "  P1: #129, #130, #131, #137"
echo "  P2: #89"
echo ""
echo "Frontend Squad (Weeks 3-6):"
echo "  P1: #132, #133, #134, #135"
echo "  P2: #85, #86, #87, #88"
echo ""
echo "Integration Squad (Weeks 3-6):"
echo "  P1: #136, #138, #139, #140"
echo "  P2: #82, #83, #84, #127, #128, #141"
echo ""
echo "QA Squad (Weeks 5-8):"
echo "  P1: #99, #100, #101, #142, #143"
echo "  P2: #90, #91, #92, #93, #94"

# Made with Bob
