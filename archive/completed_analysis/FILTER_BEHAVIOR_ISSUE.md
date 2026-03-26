# Filter Behavior Issue - Code Review Needed

## Issue Type
🐛 Bug - Requires Group Code Review by 2 Senior Developer Agents

## Priority
**HIGH** - Core functionality not working as expected

## Problem Description
The route table filters are not working properly despite multiple attempted fixes. When users interact with the direction filter ("All Routes", "To Work", "To Home") and the Plus Routes toggle ("Show"/"Hide"), the filters do not correctly display/hide rows.

### Expected Behavior
1. Direction filter should show only routes matching the selected direction
2. Plus Routes toggle should show/hide routes marked as "plus" routes
3. Both filters should work together with AND logic (show only rows that match BOTH conditions)
4. Filter changes should be immediate and visible

### Actual Behavior
- Filters appear to not work at all - no rows are returned regardless of filter combination
- Clicking different filter options doesn't change the visible rows
- The filter state may be updating but the DOM is not reflecting changes

## Technical Context

### Current Implementation
**File:** `templates/report_template.html`

**Filter Logic (lines 503-535):**
```javascript
function applyFilters() {
    console.log('Applying filters - direction:', currentDirection, 'showPlus:', showPlusRoutes);
    let visibleCount = 0;
    
    allRouteRows.forEach(row => {
        const rowDirection = row.getAttribute('data-direction');
        const isPlus = row.getAttribute('data-is-plus') === 'true';
        
        // Boolean AND: show only if BOTH conditions are met
        const matchesDirection = (currentDirection === 'all' || rowDirection === currentDirection);
        const matchesPlusFilter = (showPlusRoutes || !isPlus);
        
        // Always update both classes independently
        if (matchesDirection) {
            row.classList.remove('direction-hidden');
        } else {
            row.classList.add('direction-hidden');
        }
        
        if (matchesPlusFilter) {
            row.classList.remove('plus-hidden');
        } else {
            row.classList.add('plus-hidden');
        }
        
        // Count visible rows
        if (matchesDirection && matchesPlusFilter) {
            visibleCount++;
        }
    });
    
    console.log('Visible routes after filter:', visibleCount);
}
```

**CSS Classes (lines 88-94):**
```css
.direction-hidden {
    display: none !important;
}

.plus-hidden {
    display: none !important;
}
```

**HTML Structure:**
- Route rows have `data-direction` attribute (values: "home_to_work", "work_to_home")
- Route rows have `data-is-plus` attribute (values: "true", "false")
- Rows are in a table with class `route-table`

### Previous Fix Attempts
1. ✅ Changed filter logic to update CSS classes independently
2. ✅ Fixed route highlighting regex matching
3. ✅ Added multi-select functionality
4. ✅ Fixed JavaScript syntax error (newline escaping)
5. ❌ Filters still not working

### Potential Root Causes to Investigate

1. **JavaScript Syntax Error Blocking Execution**
   - Despite fixing the newline issue in line 1460, there may be another syntax error
   - The error at line 22437 in generated HTML might still exist
   - Check browser console for JavaScript errors

2. **DOM Selection Issues**
   - `allRouteRows` variable might not be selecting the correct elements
   - Selector might be too specific or not matching actual HTML structure
   - Check if `document.querySelectorAll('.route-table tbody tr')` returns expected elements

3. **Timing Issues**
   - Filters might be initialized before DOM is fully loaded
   - Event listeners might not be properly attached
   - Check if `DOMContentLoaded` or similar event is being used

4. **CSS Specificity Problems**
   - Other CSS rules might be overriding the `display: none !important`
   - Check computed styles in browser DevTools
   - Verify no inline styles are conflicting

5. **Data Attribute Issues**
   - `data-direction` or `data-is-plus` attributes might not be set correctly
   - Values might not match expected strings exactly (case sensitivity, whitespace)
   - Check actual HTML output for these attributes

6. **Event Handler Problems**
   - Click handlers on filter buttons might not be firing
   - Event propagation might be stopped somewhere
   - Check if filter state variables are actually updating

## Investigation Tasks for Code Review

### Senior Developer Agent 1 - Frontend/JavaScript Focus
1. **Verify JavaScript Execution**
   - Check if there are any JavaScript syntax errors preventing code execution
   - Verify the `tojson` filter fix resolved the newline issue completely
   - Look for any other potential syntax errors in the template

2. **DOM Analysis**
   - Verify the selector `document.querySelectorAll('.route-table tbody tr')` matches actual HTML
   - Check if `allRouteRows` is populated correctly
   - Inspect actual HTML structure vs. expected structure

3. **Event Flow**
   - Trace the event flow from button click to `applyFilters()` execution
   - Verify event listeners are attached correctly
   - Check if any errors occur during filter execution

4. **Browser Console Testing**
   - Provide JavaScript snippets to test in browser console
   - Check if manual filter application works
   - Verify data attributes are present and correct

### Senior Developer Agent 2 - Template/Integration Focus
1. **Template Generation**
   - Review how route rows are generated in Jinja2 template
   - Verify `data-direction` and `data-is-plus` attributes are set correctly
   - Check for any template logic that might interfere

2. **CSS Analysis**
   - Verify CSS specificity and rule application
   - Check for conflicting styles
   - Test if `display: none !important` is actually being applied

3. **Integration Points**
   - Review how Python data flows into JavaScript
   - Check if there are multiple filter implementations conflicting
   - Verify initialization order

4. **Alternative Approaches**
   - Propose alternative filter implementation strategies
   - Consider using visibility instead of display
   - Evaluate using a JavaScript framework approach

## Debugging Steps to Provide

### For User Testing
```javascript
// Run in browser console to debug
console.log('Route rows:', document.querySelectorAll('.route-table tbody tr').length);
console.log('First row direction:', document.querySelector('.route-table tbody tr')?.getAttribute('data-direction'));
console.log('First row is-plus:', document.querySelector('.route-table tbody tr')?.getAttribute('data-is-plus'));
console.log('Current direction filter:', currentDirection);
console.log('Show plus routes:', showPlusRoutes);

// Test manual filter application
document.querySelectorAll('.route-table tbody tr').forEach(row => {
    console.log('Row:', row.querySelector('td:first-child')?.textContent, 
                'Direction:', row.getAttribute('data-direction'),
                'IsPlus:', row.getAttribute('data-is-plus'),
                'Classes:', row.className);
});
```

## Success Criteria
- [ ] Filters work correctly when clicking direction buttons
- [ ] Plus Routes toggle correctly shows/hides plus routes
- [ ] Both filters work together with AND logic
- [ ] Filter state is visually indicated (button styling)
- [ ] No JavaScript errors in console
- [ ] Filter changes are immediate and smooth

## Related Files
- `templates/report_template.html` - Main template with filter logic
- `src/visualizer.py` - Generates route data
- `src/report_generator.py` - Renders template

## Additional Context
- This is a Strava commute route analyzer application
- The report is a single HTML file with embedded JavaScript
- Uses Jinja2 templating
- No external JavaScript frameworks (vanilla JS)
- Previous fixes have addressed route highlighting and multi-select, which work correctly

## Request for Code Review
**Please assign 2 senior developer agents (both powered by Bob) to:**
1. Independently analyze the code and identify root cause(s)
2. Propose specific solutions with code examples
3. Collaborate to agree on the best approach
4. Provide step-by-step implementation plan

**Review Focus Areas:**
- JavaScript execution and error handling
- DOM manipulation and CSS application
- Template rendering and data flow
- Event handling and state management

---

## Post-Resolution TODO

### v1.0.0 Milestone Completion

Once the filter behavior issue is successfully resolved:

- [ ] Declare v1.0.0 milestone complete
- [ ] Prune GITHUB_ISSUES.md to remove old issues that got us here
- [ ] Archive completed issues in a separate file (e.g., GITHUB_ISSUES_ARCHIVE.md)
- [ ] Update ISSUE_PRIORITIES.md to reflect v1.0.0 completion
- [ ] Create v1.0.0 release notes documenting:
  - All features implemented
  - All bugs fixed
  - Known limitations
  - Upgrade instructions (if any)
- [ ] Tag the repository with v1.0.0
- [ ] Update README.md with v1.0.0 status and features
- [ ] Clean up any temporary debugging files or comments
- [ ] Ensure all documentation is up to date for v1.0.0

**Rationale:** The filter behavior is the last critical issue blocking v1.0.0. Once resolved, we should clean up the issue tracking to start fresh for v1.1.0 development.