# Squad Progress Monitoring Guide

**Created:** 2026-05-06
**Purpose:** Track progress of all 4 squads working on Personal Web Platform v3.0.0 MVP

---

## 🎯 Quick Status Dashboard

### Current Sprint Status
```bash
# View all P1 issues across all squads
gh issue list --label "P1-high" --search "is:open" --json number,title,assignees,labels,milestone

# View by epic
gh issue list --search "is:open" --json number,title,labels | jq '.[] | select(.labels[].name | contains("epic"))'
```

### Squad Health Check
| Squad | Status | Blocking Issues | Progress |
|-------|--------|----------------|----------|
| Foundation | 🟢 Active | None | Issue #76 ✅ |
| Frontend | 🔴 Blocked | #129, #130, #131 | 0/4 P1 |
| Integration | 🔴 Blocked | #129, #130, #131 | 0/3 P1 |
| QA | 🟡 Monitoring | All squads | 0/5 P1 |

---

## 📊 Monitoring Commands

### 1. Foundation Squad Progress (Weeks 1-3)

**Check P1 Issues:**
```bash
# View Foundation Squad P1 issues
gh issue view 129  # Flask app factory
gh issue view 130  # Service layer
gh issue view 131  # SQLite persistence
gh issue view 137  # Scheduled jobs

# List all Foundation issues
gh issue list --search "is:open" --json number,title,state | \
  jq '.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)'
```

**Check Completion Status:**
```bash
# Count closed Foundation issues
gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)] | length'
```

**Critical Blocker:**
```bash
# Check if #76 (P0) is complete
gh issue view 76 --json state,title
```

---

### 2. Frontend Squad Progress (Weeks 3-6)

**Check Dependencies:**
```bash
# Are Foundation blockers complete?
gh issue list --search "is:open" --json number,state | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131)] | length'
# Output: 0 = Ready to start, >0 = Still blocked
```

**Check P1 Issues:**
```bash
# View Frontend Squad P1 issues
gh issue view 132  # Dashboard
gh issue view 133  # Commute views
gh issue view 134  # Long ride planner
gh issue view 135  # Route library

# List all Frontend P1 issues
gh issue list --search "is:open" --json number,title,state | \
  jq '.[] | select(.number == 132 or .number == 133 or .number == 134 or .number == 135)'
```

**Progress Percentage:**
```bash
# Calculate Frontend P1 completion
TOTAL=4
CLOSED=$(gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 132 or .number == 133 or .number == 134 or .number == 135)] | length')
echo "Frontend Progress: $((CLOSED * 100 / TOTAL))%"
```

---

### 3. Integration Squad Progress (Weeks 3-6)

**Check Dependencies:**
```bash
# Same as Frontend - check Foundation blockers
gh issue list --search "is:open" --json number,state | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131)] | length'
```

**Check P1 Issues:**
```bash
# View Integration Squad P1 issues
gh issue view 138  # Weather integration
gh issue view 139  # TrainerRoad integration
gh issue view 140  # Workout-aware commutes

# List all Integration P1 issues
gh issue list --search "is:open" --json number,title,state | \
  jq '.[] | select(.number == 138 or .number == 139 or .number == 140)'
```

**Progress Percentage:**
```bash
# Calculate Integration P1 completion
TOTAL=3
CLOSED=$(gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 138 or .number == 139 or .number == 140)] | length')
echo "Integration Progress: $((CLOSED * 100 / TOTAL))%"
```

---

### 4. QA Squad Progress (Weeks 5-8)

**Check Dependencies:**
```bash
# Check if core features are substantially complete
# Foundation (4 issues)
FOUNDATION_DONE=$(gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)] | length')

# Frontend (4 issues)
FRONTEND_DONE=$(gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 132 or .number == 133 or .number == 134 or .number == 135)] | length')

# Integration (3 issues)
INTEGRATION_DONE=$(gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 138 or .number == 139 or .number == 140)] | length')

echo "Foundation: $FOUNDATION_DONE/4"
echo "Frontend: $FRONTEND_DONE/4"
echo "Integration: $INTEGRATION_DONE/3"
echo "Total Core: $((FOUNDATION_DONE + FRONTEND_DONE + INTEGRATION_DONE))/11"
```

**Check P1 Issues:**
```bash
# View QA Squad P1 issues
gh issue view 99   # Unit tests
gh issue view 100  # Integration tests
gh issue view 101  # Documentation
gh issue view 142  # Responsive design
gh issue view 143  # Integration test suite

# List all QA P1 issues
gh issue list --search "is:open" --json number,title,state | \
  jq '.[] | select(.number == 99 or .number == 100 or .number == 101 or .number == 142 or .number == 143)'
```

**Test Coverage Check:**
```bash
# Run tests and check coverage
pytest --cov=src --cov-report=term-missing

# Quick coverage summary
pytest --cov=src --cov-report=term | grep "TOTAL"
```

---

## 📈 Overall Project Progress

### All P1 Issues Across All Squads
```bash
# List all P1 issues (16 total)
gh issue list --label "P1-high" --search "is:open" --json number,title,state

# Count completed P1 issues
gh issue list --label "P1-high" --search "is:closed" --json number | jq 'length'

# Calculate overall P1 completion percentage
TOTAL_P1=16
CLOSED_P1=$(gh issue list --label "P1-high" --search "is:closed" --json number | jq 'length')
echo "Overall P1 Progress: $((CLOSED_P1 * 100 / TOTAL_P1))%"
```

### Epic Progress
```bash
# Epic #144 - Web Platform Migration
gh issue view 144 --json title,body,state

# Epic #145 - Weather Dashboard (Post-MVP)
gh issue view 145 --json title,body,state

# Epic #146 - Beta Release Program
gh issue view 146 --json title,body,state
```

### Milestone Progress
```bash
# View all milestones
gh api repos/:owner/:repo/milestones --jq '.[] | {title, open_issues, closed_issues}'

# Calculate milestone completion
gh api repos/:owner/:repo/milestones --jq '.[] | "\(.title): \(.closed_issues)/\((.open_issues + .closed_issues)) (\((.closed_issues * 100 / (.open_issues + .closed_issues)))%)"'
```

---

## 🔔 Daily Standup Checklist

### Morning Check (Start of Day)
```bash
# 1. Check what changed overnight
gh issue list --search "is:open updated:>=$(date -v-1d +%Y-%m-%d)" --json number,title,updatedAt

# 2. Check for new comments
gh issue list --search "is:open commented:>=$(date -v-1d +%Y-%m-%d)" --json number,title

# 3. Check for newly closed issues
gh issue list --search "is:closed closed:>=$(date -v-1d +%Y-%m-%d)" --json number,title,closedAt
```

### Squad Status Questions
For each squad, answer:
1. **What was completed yesterday?**
2. **What's being worked on today?**
3. **Any blockers or dependencies?**
4. **Need help from another squad?**

### Foundation Squad Daily Check
```bash
# What's in progress?
gh issue list --search "is:open label:foundation" --json number,title,labels

# Any PRs ready for review?
gh pr list --search "is:open label:foundation" --json number,title,isDraft
```

### Frontend Squad Daily Check
```bash
# Still blocked?
gh issue list --search "is:open" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131)] | length'

# If unblocked, what's in progress?
gh issue list --search "is:open label:frontend" --json number,title,labels
```

### Integration Squad Daily Check
```bash
# Still blocked?
gh issue list --search "is:open" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131)] | length'

# If unblocked, what's in progress?
gh issue list --search "is:open label:integration" --json number,title,labels
```

### QA Squad Daily Check
```bash
# Check test coverage trend
pytest --cov=src --cov-report=term | grep "TOTAL" | tee -a coverage_history.txt

# Check for failing tests
pytest --tb=short | grep -E "FAILED|ERROR"
```

---

## 📅 Weekly Progress Report

### Week-End Summary Script
```bash
#!/bin/bash
# Save as: scripts/weekly_progress.sh

echo "=== Weekly Progress Report ==="
echo "Week ending: $(date +%Y-%m-%d)"
echo ""

echo "## Foundation Squad (Weeks 1-3)"
FOUNDATION_CLOSED=$(gh issue list --search "is:closed closed:>=$(date -v-7d +%Y-%m-%d)" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)] | length')
echo "Issues closed this week: $FOUNDATION_CLOSED"
echo ""

echo "## Frontend Squad (Weeks 3-6)"
FRONTEND_CLOSED=$(gh issue list --search "is:closed closed:>=$(date -v-7d +%Y-%m-%d)" --json number | \
  jq '[.[] | select(.number == 132 or .number == 133 or .number == 134 or .number == 135)] | length')
echo "Issues closed this week: $FRONTEND_CLOSED"
echo ""

echo "## Integration Squad (Weeks 3-6)"
INTEGRATION_CLOSED=$(gh issue list --search "is:closed closed:>=$(date -v-7d +%Y-%m-%d)" --json number | \
  jq '[.[] | select(.number == 138 or .number == 139 or .number == 140)] | length')
echo "Issues closed this week: $INTEGRATION_CLOSED"
echo ""

echo "## QA Squad (Weeks 5-8)"
QA_CLOSED=$(gh issue list --search "is:closed closed:>=$(date -v-7d +%Y-%m-%d)" --json number | \
  jq '[.[] | select(.number == 99 or .number == 100 or .number == 101 or .number == 142 or .number == 143)] | length')
echo "Issues closed this week: $QA_CLOSED"
echo ""

echo "## Overall Progress"
TOTAL_CLOSED=$(gh issue list --label "P1-high" --search "is:closed" --json number | jq 'length')
echo "Total P1 issues completed: $TOTAL_CLOSED/16 ($((TOTAL_CLOSED * 100 / 16))%)"
```

---

## 🚨 Blocker Detection

### Identify Blocked Issues
```bash
# Issues blocked by Foundation Squad
gh issue list --search "is:open" --json number,title,body | \
  jq '.[] | select(.body | contains("blocked") or contains("depends on #129") or contains("depends on #130") or contains("depends on #131"))'

# Issues with "blocked" label
gh issue list --label "blocked" --json number,title,state
```

### Critical Path Monitoring
```bash
# Check if critical path is on schedule
# Foundation must complete by Week 3
# Frontend/Integration must complete by Week 6
# QA must complete by Week 8

# Calculate weeks elapsed since project start (adjust start date)
START_DATE="2026-05-06"
WEEKS_ELAPSED=$(( ($(date +%s) - $(date -j -f "%Y-%m-%d" "$START_DATE" +%s)) / 604800 ))
echo "Weeks elapsed: $WEEKS_ELAPSED"

# Check Foundation progress (should be done by Week 3)
if [ $WEEKS_ELAPSED -ge 3 ]; then
  FOUNDATION_OPEN=$(gh issue list --search "is:open" --json number | \
    jq '[.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)] | length')
  if [ $FOUNDATION_OPEN -gt 0 ]; then
    echo "⚠️  WARNING: Foundation Squad behind schedule ($FOUNDATION_OPEN issues still open)"
  fi
fi
```

---

## 📊 Visualization & Dashboards

### GitHub Projects Board
```bash
# View project board (if configured)
gh project list
gh project view <project-number>
```

### Issue Burndown
```bash
# Track P1 issues over time
echo "$(date +%Y-%m-%d),$(gh issue list --label "P1-high" --search "is:open" --json number | jq 'length')" >> burndown.csv

# View burndown chart (requires gnuplot or similar)
gnuplot -e "set terminal dumb; set datafile separator ','; plot 'burndown.csv' using 2 with lines"
```

### Test Coverage Trend
```bash
# Track coverage over time
pytest --cov=src --cov-report=term | grep "TOTAL" | \
  awk '{print strftime("%Y-%m-%d"), $NF}' >> coverage_trend.csv
```

---

## 🎯 Success Metrics

### Milestone 1: Foundation Complete (Week 3)
- [ ] Flask API operational (#129 closed)
- [ ] SQLite persistence working (#131 closed)
- [ ] Background jobs functional (#137 closed)
- [ ] Service layer extracted (#130 closed)

**Check:**
```bash
gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 129 or .number == 130 or .number == 131 or .number == 137)] | length'
# Should output: 4
```

### Milestone 2: Core Views Complete (Week 6)
- [ ] Dashboard implemented (#132 closed)
- [ ] Commute recommendations working (#133 closed)
- [ ] Long ride planner functional (#134 closed)
- [ ] Route library browsable (#135 closed)

**Check:**
```bash
gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 132 or .number == 133 or .number == 134 or .number == 135)] | length'
# Should output: 4
```

### Milestone 3: Feature Integration Complete (Week 6)
- [ ] Weather integration complete (#138 closed)
- [ ] TrainerRoad import functional (#139 closed)
- [ ] Workout-aware recommendations (#140 closed)

**Check:**
```bash
gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 138 or .number == 139 or .number == 140)] | length'
# Should output: 3
```

### Milestone 4: Production Ready (Week 8)
- [ ] 80%+ test coverage
- [ ] All integration tests passing (#100, #143 closed)
- [ ] Responsive design complete (#142 closed)
- [ ] Documentation finished (#101 closed)
- [ ] Accessibility compliant (#94 closed)

**Check:**
```bash
# Test coverage
pytest --cov=src --cov-report=term | grep "TOTAL" | awk '{print $NF}'
# Should output: >=80%

# QA issues
gh issue list --search "is:closed" --json number | \
  jq '[.[] | select(.number == 99 or .number == 100 or .number == 101 or .number == 142 or .number == 143)] | length'
# Should output: 5
```

---

## 🔗 Quick Links

- **Squad Organization:** [`SQUAD_ORGANIZATION.md`](SQUAD_ORGANIZATION.md)
- **Issue Priorities:** [`ISSUE_PRIORITIES.md`](ISSUE_PRIORITIES.md)
- **Release Roadmap:** [`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md)
- **Management Report:** [`INTELLIGENT_ISSUE_MANAGEMENT_REPORT.md`](INTELLIGENT_ISSUE_MANAGEMENT_REPORT.md)

---

## 📝 Notes

- Run daily standup checks every morning
- Update burndown chart weekly
- Review critical path weekly
- Escalate blockers immediately
- Celebrate completed milestones! 🎉

---

*Last updated: 2026-05-06*
*Next review: Daily*