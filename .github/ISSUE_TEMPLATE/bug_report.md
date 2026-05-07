---
name: Bug Report
about: Report a bug or issue
title: '[BUG] '
labels: 'bug'
assignees: ''
---

## Description
<!-- Clear description of the bug -->

## Current Behavior
<!-- What happens now -->

## Expected Behavior
<!-- What should happen -->

## Steps to Reproduce
1. 
2. 
3. 

## Environment
- **OS:** 
- **Browser:** 
- **Version:** 

## Error Messages
<!-- Include any error messages, stack traces, or logs -->
```
Paste error messages here
```

## Screenshots
<!-- If applicable, add screenshots to help explain the problem -->

## Acceptance Criteria for Fix
<!-- All criteria must be met before closing this issue -->

### Implementation
- [ ] **Root cause identified** and documented
- [ ] **Actual fix implemented** (NOT workarounds)
- [ ] Fix addresses root cause, not just symptoms
- [ ] Edge cases considered and handled
- [ ] No new bugs introduced

### Testing
- [ ] **Regression test added** to prevent recurrence
- [ ] Unit tests updated/added (80%+ coverage)
- [ ] Manual testing confirms fix works
- [ ] All existing tests still pass
- [ ] Bug cannot be reproduced after fix

### Code Review
- [ ] **Pull Request (PR) created** with fix
- [ ] PR links to this issue (Fixes #XXX)
- [ ] **At least one reviewer approval** obtained
- [ ] All review comments addressed
- [ ] CI/CD pipeline passes

### Documentation
- [ ] Code comments explain fix (if complex)
- [ ] Known issues documentation updated
- [ ] User-facing docs updated (if behavior changed)
- [ ] CHANGELOG entry added

### Verification
- [ ] **PR merged to main branch**
- [ ] **QA verification** that bug is fixed
- [ ] No regressions in related functionality
- [ ] Fix deployed to staging/production

## Priority
<!-- Select one based on impact -->
- [ ] P0 - Critical (Application unusable, data loss)
- [ ] P1 - High (Core feature broken, major pain point)
- [ ] P2 - Medium (Feature degraded, workaround exists)
- [ ] P3 - Low (Minor issue, cosmetic)

## Impact
<!-- Who is affected and how severely? -->
- **Users Affected:** 
- **Frequency:** 
- **Severity:** 

## Possible Solution
<!-- If you have ideas on how to fix this -->

## Related Issues
<!-- Link to related issues or PRs -->
- Related to: #
- Duplicate of: #
- Blocks: #

## Additional Context
<!-- Any other relevant information -->

---

## Definition of "Done" Reminder

**This bug is NOT fixed until:**
1. ✅ Root cause identified and fixed (not workaround)
2. ✅ Regression test added
3. ✅ PR reviewed and merged
4. ✅ QA verification complete
5. ✅ Bug cannot be reproduced

**See:** [DEFINITION_OF_DONE.md](../../DEFINITION_OF_DONE.md) for complete checklist.