# GitHub Issue Labels Cache

**Last Updated:** 2026-05-10  
**Update Frequency:** Weekly maintenance

## Priority Labels
- `P0-critical` - Critical priority - immediate attention
- `P1-high` - High priority - next sprint
- `P2-medium` - Medium priority - backlog
- `P3-low` - Low priority - nice to have
- `P4-future` - Future consideration

## Type Labels
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `question` - Further information is requested
- `duplicate` - This issue or pull request already exists
- `invalid` - This doesn't seem right
- `wontfix` - This will not be worked on

## Area Labels
- `backend` - Backend changes
- `frontend` - Frontend changes
- `architecture` - Architecture and infrastructure changes
- `infrastructure` - Infrastructure and system resources
- `performance` - Performance improvements
- `testing` - Testing and QA
- `security` - Security vulnerabilities and hardening
- `deployment` - Deployment and DevOps
- `docker` - Docker and containerization
- `ci/cd` - Continuous Integration/Continuous Deployment

## Feature Labels
- `accessibility` - Accessibility improvements
- `a11y` - Accessibility (WCAG compliance)
- `design` - Design and UI
- `ux` - User experience improvements
- `navigation` - Navigation and routing changes
- `mobile` - Mobile-specific features
- `keyboard-navigation` - Keyboard navigation support
- `touch` - Touch interaction
- `gestures` - Gesture support
- `routes` - Route-related features
- `notifications` - Notifications and toasts

## Component Labels
- `component` - Reusable component
- `layout` - Layout and viewport optimization
- `loading` - Loading states

## Quality Labels
- `WCAG` - WCAG compliance
- `quality` - Quality assurance
- `e2e` - End-to-end testing
- `error-recovery` - Error recovery and data loss prevention
- `data-loss-prevention` - Prevents user data loss

## Special Labels
- `epic` - Epic issue tracking multiple related issues
- `blocking-launch` - Cannot launch without fixing this
- `breaking-change` - Breaking changes requiring migration
- `quick-win` - Quick win - high impact, low effort
- `help wanted` - Extra attention is needed
- `good first issue` - Good for newcomers
- `help` - Help and documentation
- `onboarding` - User onboarding
- `raspberry-pi` - Raspberry Pi specific

## Common Label Combinations

### Bug Reports
```bash
gh issue create --label "P1-high,bug,backend"
```

### UI/UX Enhancements
```bash
gh issue create --label "P2-medium,enhancement,ux,design,frontend"
```

### Accessibility Issues
```bash
gh issue create --label "P1-high,accessibility,a11y,WCAG"
```

### Performance Improvements
```bash
gh issue create --label "P2-medium,performance,backend"
```

### Documentation
```bash
gh issue create --label "P3-low,documentation,help"
```

## Maintenance

Update this file weekly by running:
```bash
gh label list --limit 100 > .bob/github_labels_raw.txt
```

Then manually format into this document.