# New GitHub Issues - 2026-03-25

These issues should be added to the GitHub repository after the filter behavior issue is resolved and v1.0.0 is declared complete.

---

## Issue #55: Fix Prev/Next Button Screen Movement

**Labels:** `bug`, `ui/ux`, `priority: P2`

**Title:** Prevent screen from scrolling when clicking prev/next buttons

**Description:**

When users click the prev/next navigation buttons in the report, the screen unexpectedly scrolls down, disrupting the user experience and making navigation confusing.

### Current Problem:

- Clicking prev/next buttons causes unwanted page scroll
- User loses their position on the page
- Disrupts flow when navigating between routes or sections
- Likely caused by default button behavior or event propagation

### Expected Behavior:

- Clicking prev/next buttons should navigate without scrolling
- Page position should remain stable
- Only the content should change, not the viewport position

### Technical Investigation:

1. Check if buttons are using `<a>` tags with `href="#"` (causes scroll to top)
2. Verify event handlers call `preventDefault()` to stop default behavior
3. Check for any scroll-related JavaScript triggered by button clicks
4. Ensure buttons use `type="button"` if they're `<button>` elements

### Proposed Solution:

```javascript
// Ensure event handlers prevent default behavior
button.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    // Navigation logic here
});
```

### Files to Check:

- `templates/report_template.html` - Button HTML structure
- `src/report_generator.py` - Button generation code
- Any JavaScript handling button clicks

### Acceptance Criteria:

- [ ] Prev/next buttons do not cause page scroll
- [ ] User viewport position remains stable when clicking buttons
- [ ] Navigation functionality still works correctly
- [ ] Tested on multiple browsers (Chrome, Firefox, Safari)
- [ ] Works on both desktop and mobile viewports

---

## Issue #56: Tighten Table Spacing for Route Names and Stats

**Labels:** `enhancement`, `ui/ux`, `priority: P2`

**Title:** Reduce dead space in route comparison table

**Description:**

The route comparison table has excessive vertical spacing between text and row separators, making the table unnecessarily tall and harder to scan. Tightening the spacing will improve readability and allow more routes to be visible without scrolling.

### Current Problem:

- Too much padding/margin between text and row borders
- Table takes up more vertical space than necessary
- Harder to compare routes at a glance
- Excessive scrolling required for tables with many routes

### Proposed Solution:

Reduce cell padding and line height in the route comparison table while maintaining readability.

### CSS Changes Needed:

```css
/* Tighten table cell spacing */
.route-comparison-table td,
.route-comparison-table th {
    padding: 6px 12px;  /* Reduce from current padding */
    line-height: 1.3;   /* Tighter line height */
}

/* Reduce spacing in multi-line cells */
.route-comparison-table .route-name {
    margin-bottom: 2px;  /* Minimal spacing */
}

/* Compact stat displays */
.route-comparison-table .stat-value {
    margin: 0;
    padding: 0;
}
```

### Design Considerations:

- Maintain minimum touch target size for mobile (44x44px)
- Ensure text remains readable
- Keep adequate spacing for visual hierarchy
- Test with long route names and various screen sizes

### Files to Modify:

- `templates/report_template.html` - Table CSS styles
- `src/report_generator.py` - If table structure needs adjustment

### Acceptance Criteria:

- [ ] Table vertical spacing reduced by ~30-40%
- [ ] Text remains readable and not cramped
- [ ] Touch targets adequate for mobile use
- [ ] Tested with tables containing 3, 5, and 10+ routes
- [ ] Visual hierarchy maintained (headers, data, separators)
- [ ] Consistent spacing throughout all table sections

---

## Issue #57: Investigate Missing Tab Behavior Fix

**Labels:** `bug`, `investigation`, `priority: P2`

**Title:** Check status of tab switching functionality issue

**Description:**

A TODO was written yesterday about fixing tab behavior, but it's unclear if an issue was created or if the task was lost. Need to investigate the current state of tab functionality and create/update issues accordingly.

### Investigation Tasks:

1. **Search for existing issues:**
   - Check GITHUB_ISSUES.md for tab-related issues
   - Search ISSUE_PRIORITIES.md for tab mentions
   - Look for issue #22 (Bootstrap tab switching)

2. **Test current tab behavior:**
   - Open generated report in browser
   - Test all tab switches (Commute Routes, Long Rides, Weather, etc.)
   - Document any issues found

3. **Check recent commits:**
   - Review git history for tab-related fixes
   - Check if issue was resolved but not documented

4. **Review TODO files:**
   - Search for tab-related TODOs
   - Check if TODO was in a file that was deleted/modified

### Known Tab Issues:

From ISSUE_PRIORITIES.md:
- Issue #22 exists: "Debug and fix Bootstrap tab switching functionality" (P3-low priority)

### Possible Problems:

- Tabs not switching when clicked
- Content not loading in inactive tabs
- JavaScript errors in console
- Bootstrap version conflicts
- Event handlers not properly attached

### Next Steps:

Based on investigation results:
1. If issue #22 covers the problem → Update issue with current status
2. If new tab issues found → Create new issue with details
3. If tabs work correctly → Close issue #22 and document resolution
4. If TODO was about different tab behavior → Create specific issue

### Acceptance Criteria:

- [ ] Current tab functionality documented
- [ ] Issue #22 status verified
- [ ] Any new tab issues identified and documented
- [ ] Clear action plan established (fix, close, or update)

---

## Issue #58: Fix Analyzer Output Word Wrapping for Terminal

**Labels:** `bug`, `cli`, `priority: P2`

**Title:** Ensure analyzer output displays cleanly in terminal regardless of window size

**Description:**

The analyzer output currently has clunky word wrapping that doesn't adapt well to different terminal window sizes. Output should be formatted to display cleanly regardless of terminal width.

### Current Problem:

- Text wraps awkwardly in narrow terminals
- Long lines break in the middle of words
- Tables and formatted output become unreadable
- No adaptation to terminal width
- Poor user experience when running from command line

### Expected Behavior:

- Output should detect terminal width
- Text should wrap intelligently at word boundaries
- Tables should adapt or provide horizontal scroll
- Important information should remain readable
- Consistent formatting across different terminal sizes

### Technical Approach:

```python
import shutil
import textwrap

# Get terminal width
terminal_width = shutil.get_terminal_size().columns

# Wrap text intelligently
def format_output(text, width=None):
    if width is None:
        width = min(shutil.get_terminal_size().columns - 2, 100)
    return textwrap.fill(text, width=width, break_long_words=False)

# For tables, use libraries like tabulate with max_width
from tabulate import tabulate
table = tabulate(data, headers=headers, tablefmt='grid', 
                 maxcolwidths=[None, 30, 20, 15])
```

### Files to Modify:

- `src/long_ride_analyzer.py` - Long ride output formatting
- `src/route_analyzer.py` - Route analysis output
- `main.py` - Main output formatting
- Any other files that print to terminal

### Specific Issues to Address:

1. **Long route names:** Truncate or wrap intelligently
2. **Statistics tables:** Use adaptive column widths
3. **Recommendation text:** Wrap at word boundaries
4. **Progress indicators:** Ensure they don't break layout
5. **Error messages:** Format for readability

### Testing Requirements:

Test output in terminals of various widths:
- Narrow: 80 columns
- Standard: 120 columns
- Wide: 200+ columns
- Very narrow: 40 columns (mobile/split screen)

### Acceptance Criteria:

- [ ] Output detects terminal width automatically
- [ ] Text wraps at word boundaries, not mid-word
- [ ] Tables remain readable or provide clear overflow indication
- [ ] No horizontal scrolling required for standard output
- [ ] Tested in terminals: 40, 80, 120, 200 columns wide
- [ ] Works in common terminals (bash, zsh, PowerShell, Windows Terminal)
- [ ] Long route names handled gracefully (truncate with ellipsis)
- [ ] Maintains readability and visual hierarchy

---

## Issue #59: Schedule End-of-Day Critical Code Review

**Labels:** `code-review`, `quality`, `priority: P1`

**Title:** Comprehensive code review from skeptical senior developer perspective

**Description:**

Schedule a thorough end-of-day code review examining the entire project from the perspective of a highly skeptical and experienced senior developer who assumes poor code quality and is extremely critical of performance issues.

### Review Persona:

**"The Skeptical Senior"**
- Assumes everyone else is incompetent until proven otherwise
- Extremely thorough and detail-oriented
- Highly critical of poor performing code
- Zero tolerance for code smells and anti-patterns
- Focuses on scalability, maintainability, and performance
- Questions every design decision
- Demands evidence and benchmarks

### Review Scope:

#### 1. **Performance Analysis**
- [ ] Identify all O(n²) or worse algorithms
- [ ] Find unnecessary loops and iterations
- [ ] Locate redundant API calls
- [ ] Check for inefficient data structures
- [ ] Identify memory leaks or excessive memory usage
- [ ] Find blocking I/O operations
- [ ] Check caching effectiveness

#### 2. **Code Quality**
- [ ] Identify code duplication (DRY violations)
- [ ] Find overly complex functions (cyclomatic complexity)
- [ ] Locate god objects and classes
- [ ] Check for proper error handling
- [ ] Verify input validation
- [ ] Review logging practices
- [ ] Check for hardcoded values

#### 3. **Architecture & Design**
- [ ] Evaluate separation of concerns
- [ ] Check for tight coupling
- [ ] Review dependency management
- [ ] Assess testability
- [ ] Verify SOLID principles adherence
- [ ] Check for proper abstraction layers
- [ ] Review API design

#### 4. **Security**
- [ ] Check for injection vulnerabilities
- [ ] Verify secure credential handling
- [ ] Review authentication/authorization
- [ ] Check for exposed secrets
- [ ] Verify input sanitization
- [ ] Review file handling security

#### 5. **Scalability**
- [ ] Identify bottlenecks for large datasets
- [ ] Check for N+1 query problems
- [ ] Review caching strategy
- [ ] Assess concurrent request handling
- [ ] Check for resource exhaustion risks

#### 6. **Maintainability**
- [ ] Review code documentation
- [ ] Check naming conventions
- [ ] Assess code organization
- [ ] Review test coverage
- [ ] Check for technical debt

### Deliverables:

1. **Critical Issues Report**
   - High-priority performance problems
   - Security vulnerabilities
   - Architectural flaws

2. **Performance Improvement Recommendations**
   - Specific optimizations with expected impact
   - Benchmarks showing current vs. potential performance
   - Priority ranking of improvements

3. **Code Quality Issues**
   - List of code smells with locations
   - Refactoring recommendations
   - Complexity metrics

4. **Action Plan**
   - Immediate fixes (P0)
   - Short-term improvements (P1)
   - Long-term refactoring (P2-P3)

### Review Process:

1. **Automated Analysis:**
   ```bash
   # Run linters and static analysis
   pylint src/
   flake8 src/
   mypy src/
   bandit -r src/
   radon cc src/ -a -nb
   ```

2. **Manual Code Review:**
   - Read through each module critically
   - Question every design decision
   - Look for hidden complexity
   - Test edge cases mentally

3. **Performance Profiling:**
   ```bash
   # Profile the application
   python -m cProfile -o profile.stats main.py
   python -m pstats profile.stats
   ```

4. **Documentation Review:**
   - Check if code matches documentation
   - Verify examples work
   - Look for outdated information

### Success Criteria:

- [ ] Complete review of all source files
- [ ] Documented list of critical issues
- [ ] Performance benchmarks for key operations
- [ ] Prioritized improvement recommendations
- [ ] Specific code examples for each issue
- [ ] Estimated effort for each recommendation
- [ ] Review completed by end of day

### Expected Outcome:

A brutally honest assessment that:
- Identifies real problems, not nitpicks
- Provides actionable recommendations
- Includes performance data and benchmarks
- Prioritizes issues by impact
- Helps improve code quality significantly

---

## Git Hygiene: Close Issue #24

**Issue #24:** Grey out unselected routes on map when route is clicked

**Status:** ✅ RESOLVED - Already Implemented

**Evidence:**

The functionality described in issue #24 has been fully implemented in `src/visualizer.py`. When routes are selected:
- Unselected routes are greyed out with opacity 0.15 (lines 801-804, 954-957)
- Selected routes are highlighted with opacity 1.0 and thicker stroke width
- The implementation uses CSS classes to manage visibility

**Code Reference:**
```javascript
// Unselected route - subdue with low opacity and gray color
line.style.display = '';
line.style.opacity = '0.15';
line.style.strokeWidth = '2';
line.style.stroke = '#808080';
```

**Action Required:**
- Close issue #24 on GitHub
- Mark as resolved in ISSUE_PRIORITIES.md
- Document resolution date: 2026-03-25

---

## Summary

**New Issues to Create:** 5 (Issues #55-59)
**Issues to Close:** 1 (Issue #24)
**Priority Distribution:**
- P1 (High): 1 issue (#59 - Code Review)
- P2 (Medium): 4 issues (#55-58)

**Next Steps:**
1. Wait for filter behavior issue resolution
2. Declare v1.0.0 milestone complete
3. Create these issues on GitHub
4. Close issue #24
5. Prune GITHUB_ISSUES.md of completed issues