# Issues Tracking

This document tracks known issues and bugs in the Ride Optimizer application.

## Active Issues

### Issue #1: Excessive Whitespace Between Sections
**Priority:** P2 (Medium)
**Component:** UI/UX - Report Layout
**Reported:** 2026-03-29
**Status:** Open
**GitHub Issue:** [#127](https://github.com/e2kd7n/ride-optimizer/issues/127)

**Description:**
There is excessive whitespace between the "Alternative Routes" section and the "Long Ride Recommendations" tab content, creating poor visual flow and wasting screen space.

**Expected Behavior:**
Sections should have consistent, reasonable spacing (e.g., 20-30px margin) to maintain visual hierarchy without excessive gaps.

**Current Behavior:**
Large whitespace gap exists between sections, making the interface feel disconnected and requiring unnecessary scrolling.

**Impact:**
- Poor user experience due to excessive scrolling
- Wastes valuable screen real estate
- Makes interface feel disjointed

**Affected Files:**
- `templates/report_template.html` (section spacing/margins)

**Proposed Fix:**
1. Audit all section margins and padding
2. Standardize spacing to 20-30px between major sections
3. Ensure consistent spacing throughout the report

---

### Issue #2: "Unnamed Activity" in Uses Modal
**Priority:** P2 (Medium)
**Component:** Route Comparison / Uses Modal
**Reported:** 2026-03-29
**Status:** Open
**GitHub Issue:** [#128](https://github.com/e2kd7n/ride-optimizer/issues/128)

**Description:**
When clicking the "uses" count in the Route Comparison table to view matched activities, the modal displays "Unnamed Activity" instead of the actual Strava activity names.

**Expected Behavior:**
The modal should display the actual Strava activity names (e.g., "Morning Commute", "Evening Ride", etc.) for each matched activity.

**Current Behavior:**
All activities show as "Unnamed Activity" with date, distance, and duration information.

**Impact:**
- Users cannot identify which specific rides are included in a route group
- Reduces usefulness of the matched activities modal
- Makes it harder to verify route grouping accuracy

**Root Cause:**
The activity data being passed to the modal likely doesn't include the `name` field from Strava, or the template is not accessing it correctly.

**Affected Files:**
- `templates/report_template.html` (modal template around line 1600-1700)
- `src/report_generator.py` (data preparation for modal)

**Steps to Reproduce:**
1. Open generated HTML report
2. Click on any "uses" count number in the Route Comparison table
3. Observe modal shows "Unnamed Activity" for all entries

**Proposed Fix:**
1. Ensure activity names are included in the data passed to the template
2. Update modal template to display `activity.name` field
3. Add fallback to show activity ID if name is unavailable

---

### Issue #3: Report Template Size and Complexity
**Priority:** P3 (Low - Technical Debt)
**Component:** Architecture / Report Generation
**Reported:** 2026-03-29
**Status:** Open
**GitHub Issue:** [#102](https://github.com/e2kd7n/ride-optimizer/issues/102) (Already tracked as "Refactor report template to extract JavaScript into separate files")

**Description:**
The `templates/report_template.html` file has grown to over 3000 lines and contains a mix of HTML structure, inline CSS, and extensive JavaScript. This makes the template difficult to maintain, debug, and extend.

**Expected Behavior:**
- Template should be modular with separated concerns
- JavaScript should be in separate files or modules
- CSS should be in separate stylesheets
- Template should focus primarily on HTML structure and Jinja2 templating

**Current Behavior:**
- Single monolithic 3000+ line HTML file
- Inline JavaScript for multiple features (maps, charts, filtering, pagination)
- Inline CSS styles mixed with Bootstrap classes
- Difficult to locate and modify specific features

**Impact:**
- Increased maintenance burden
- Higher risk of introducing bugs when making changes
- Difficult for new developers to understand codebase
- Slower development velocity for new features
- Code duplication across different sections

**Root Cause:**
Incremental feature additions without refactoring have led to template bloat. Each new feature (route comparison, long rides, next commute, etc.) added more inline JavaScript and CSS.

**Affected Files:**
- `templates/report_template.html` (primary file)
- `src/report_generator.py` (template rendering)

**Proposed Fix:**
1. **Architecture Review:** Have architect examine current structure and propose modular design
2. **Separate JavaScript:** Extract JavaScript into separate files:
   - `report-maps.js` (Leaflet map functionality)
   - `report-charts.js` (Chart.js functionality)
   - `report-filters.js` (filtering and pagination)
   - `report-ui.js` (UI interactions, modals, tabs)
3. **Separate CSS:** Extract custom styles into `report-styles.css`
4. **Template Partials:** Break template into smaller Jinja2 includes:
   - `_route_comparison.html`
   - `_long_rides.html`
   - `_next_commute.html`
   - `_statistics.html`
5. **Build Process:** Consider adding a build step to bundle/minify assets
6. **Documentation:** Document template architecture and component interactions

**Notes:**
- This is a significant refactoring effort
- Should be done incrementally to avoid breaking changes
- Consider using a JavaScript module bundler (webpack, rollup, etc.)
- May want to explore modern frontend frameworks for future versions

---

## Resolved Issues

(None yet)

---

## Issue Template

```markdown
### Issue #N: [Title]
**Priority:** P1/P2/P3  
**Component:** [Component Name]  
**Reported:** YYYY-MM-DD  
**Status:** Open/In Progress/Resolved

**Description:**
[Brief description]

**Expected Behavior:**
[What should happen]

**Current Behavior:**
[What actually happens]

**Impact:**
[How this affects users]

**Root Cause:**
[Technical explanation if known]

**Affected Files:**
- file1.py
- file2.html

**Steps to Reproduce:**
1. Step 1
2. Step 2

**Proposed Fix:**
[Solution approach]