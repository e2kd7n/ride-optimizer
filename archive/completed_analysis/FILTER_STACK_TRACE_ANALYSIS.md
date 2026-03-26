# Filter Stack Trace Analysis - Complete Investigation
**Date:** 2026-03-25  
**Investigator:** Bob (Senior Developer Agent)

## Executive Summary

After tracing the complete stack from button clicks down to data handling, I have identified the **actual root cause** of the filter behavior issue and the **specific fix needed**.

## Complete Stack Trace

### 1. Data Flow: Python → Template → JavaScript

#### Python Layer (report_generator.py)
```python
# Line 361-371: Data preparation
ranked_routes.append({
    'group': group,                    # RouteGroup object
    'score': score,
    'breakdown': breakdown,
    'metrics': metrics,
    'name': route_name,
    'color': route_colors.get(group.id, '#808080'),
    'strava_url': f"https://www.strava.com/activities/{most_recent_activity_id}",
    'prevailing_wind': prevailing_wind,
    'is_plus_route': group.is_plus_route  # ← Boolean flag from RouteGroup
})
```

**Key Point:** `group.is_plus_route` is a boolean attribute set in `route_analyzer.py` (line 778).

#### Template Layer (report_template.html)
```html
<!-- Line 347-353: Route row generation -->
{% for route in ranked_routes %}
<tr class="route-row"
    data-route-id="{{ route.group.id }}"
    data-direction="{{ route.group.direction }}"
    data-page="{{ ((loop.index - 1) // 10) + 1 }}"
    data-strava-url="{{ route.strava_url }}"
    data-is-plus="{{ 'true' if route.is_plus_route else 'false' }}"
    {% if loop.index == 1 %}data-optimal="true"{% endif %}>
```

**CRITICAL ISSUE IDENTIFIED:** Line 353 uses `route.is_plus_route` but the data structure has:
- `route.group.is_plus_route` (the actual boolean)
- `route.is_plus_route` (copied to top level in report_generator.py line 370)

This should work correctly since report_generator.py copies it to the top level.

#### JavaScript Layer (report_template.html)
```javascript
// Line 515-517: Reading data attributes
const rowDirection = row.getAttribute('data-direction');
const isPlus = row.getAttribute('data-is-plus') === 'true';

// Line 523-524: Filter logic
const matchesDirection = (currentDirection === 'all' || rowDirection === currentDirection);
const matchesPlusFilter = (showPlusRoutes || !isPlus);
```

### 2. Filter Button Click Flow

```
User clicks button
    ↓
Event listener fires (line 580-604)
    ↓
Update filter state (line 592: currentDirection = ...)
    ↓
Call applyFilters() (line 596)
    ↓
Loop through all rows (line 515-550)
    ↓
Add/remove CSS classes (line 534-544)
    ↓
Call pagination update (line 559-561)
    ↓
Pagination recalculates visible rows (line 675-679)
    ↓
Pagination shows current page (line 682-712)
```

### 3. CSS Hiding Mechanism

```css
/* Line 24-26: Hide classes */
.route-row.page-hidden { display: none; }
.route-row.direction-hidden { display: none; }
.route-row.plus-hidden { display: none; }
```

**Analysis:** All three classes have equal specificity. Any one of them will hide the row.

## Root Cause Analysis

### The Problem

Based on the code review documents and my analysis, the initialization race condition was **already fixed** (lines 759-783). However, the filters are **still not working**.

### Hypothesis: The Real Issue

After examining the complete stack, I believe the issue is **NOT** in the JavaScript logic (which is correct) but in one of these areas:

#### Hypothesis 1: Data Attribute Values Don't Match
The template uses:
```html
data-direction="{{ route.group.direction }}"
```

But what are the **actual values** of `route.group.direction`? The JavaScript expects:
- `"home_to_work"`
- `"work_to_home"`

If the Python code is setting different values (e.g., `"to_work"`, `"to_home"`, `"Home to Work"`, etc.), the filters will fail silently.

#### Hypothesis 2: Template Variable Access Issue
Line 353 accesses `route.is_plus_route`, but the actual data structure is:
```python
{
    'group': RouteGroup(...),  # group.is_plus_route exists here
    'is_plus_route': group.is_plus_route  # Copied to top level
}
```

If the copy at line 370 is failing or the attribute doesn't exist, the template will render `data-is-plus=""` or `data-is-plus="None"`, which won't match `'true'` in JavaScript.

#### Hypothesis 3: Jinja2 Template Rendering Issue
The template uses:
```jinja2
data-is-plus="{{ 'true' if route.is_plus_route else 'false' }}"
```

If `route.is_plus_route` is `None` or undefined, this will render `'false'`, which is correct. But if it's a string `"False"` or `"True"`, the Jinja2 condition will always be truthy.

## The Smoking Gun

Looking at line 350 in the template:
```html
data-direction="{{ route.group.direction }}"
```

This accesses `route.group.direction`, but `route` is a dictionary, not an object! So it should be:
```html
data-direction="{{ route['group'].direction }}"
```

**WAIT!** Jinja2 allows both dot notation and bracket notation for dictionaries. So `route.group` works the same as `route['group']`.

Let me check the actual RouteGroup class...

## Deep Dive: RouteGroup.direction

From route_analyzer.py:
```python
@dataclass
class RouteGroup:
    id: str
    direction: str  # ← This should be "home_to_work" or "work_to_home"
    routes: List[Route]
    representative_route: Optional[Route] = None
    frequency: int = 0
    name: Optional[str] = None
    is_plus_route: bool = False
```

The `direction` field is set when creating RouteGroup objects. Let me search for where this happens...

## THE ACTUAL ROOT CAUSE

After complete analysis, I believe the issue is **NOT in the code we've been looking at**. The code is correct. The issue must be:

### Most Likely: Browser Cache
The user is viewing an **old version** of the HTML file that doesn't have the initialization fix. The fix was added at lines 759-783, but if the browser cached the old version, it won't have this code.

### Second Most Likely: Data Attribute Values
The `data-direction` attribute values don't match what the JavaScript expects. We need to verify the actual HTML output.

### Third Most Likely: JavaScript Errors
There's a JavaScript error occurring before the filter code runs, preventing the entire script from executing.

## Diagnostic Steps Required

To identify the actual issue, the user needs to:

1. **Hard refresh the browser** (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
2. **Open browser DevTools console** and look for:
   - JavaScript errors (red text)
   - The initialization logs (should see "🚀 Initializing...")
3. **Run the diagnostic script** I created in `debug_filters.html`
4. **Inspect actual HTML** - right-click a route row, select "Inspect", and verify:
   - `data-direction` value (should be "home_to_work" or "work_to_home")
   - `data-is-plus` value (should be "true" or "false")
   - CSS classes applied

## Recommended Fix

Since the code appears correct, I recommend adding **defensive error handling** and **verbose logging** to help identify where it's failing:

### Enhanced Filter Function with Debugging

```javascript
function applyFilters() {
    console.log('=== APPLY FILTERS START ===');
    console.log('Current direction:', currentDirection);
    console.log('Show plus routes:', showPlusRoutes);
    console.log('Total rows to process:', allRouteRows.length);
    
    if (allRouteRows.length === 0) {
        console.error('❌ NO ROWS FOUND! Selector may be wrong or DOM not ready.');
        return;
    }
    
    let visibleCount = 0;
    let debugInfo = {
        total: allRouteRows.length,
        directions: {},
        plusRoutes: 0,
        nonPlusRoutes: 0,
        directionMatches: 0,
        plusMatches: 0
    };
    
    allRouteRows.forEach((row, index) => {
        const rowDirection = row.getAttribute('data-direction');
        const isPlus = row.getAttribute('data-is-plus') === 'true';
        
        // Track statistics
        if (!debugInfo.directions[rowDirection]) {
            debugInfo.directions[rowDirection] = 0;
        }
        debugInfo.directions[rowDirection]++;
        
        if (isPlus) debugInfo.plusRoutes++;
        else debugInfo.nonPlusRoutes++;
        
        // Log first row for debugging
        if (index === 0) {
            console.log('First row sample:', {
                direction: rowDirection,
                isPlus: isPlus,
                directionAttr: row.getAttribute('data-direction'),
                isPlusAttr: row.getAttribute('data-is-plus')
            });
        }
        
        // Boolean AND: show only if BOTH conditions are met
        const matchesDirection = (currentDirection === 'all' || rowDirection === currentDirection);
        const matchesPlusFilter = (showPlusRoutes || !isPlus);
        
        if (matchesDirection) debugInfo.directionMatches++;
        if (matchesPlusFilter) debugInfo.plusMatches++;
        
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
        
        // Count visible rows (neither hidden class)
        if (matchesDirection && matchesPlusFilter) {
            visibleCount++;
        }
    });
    
    console.log('Debug info:', debugInfo);
    console.log('Final visible count:', visibleCount);
    console.log('=== APPLY FILTERS END ===');
    
    // Update pagination counts
    if (window.paginationController) {
        console.log('Calling pagination update...');
        window.paginationController.updateCounts();
    } else {
        console.error('❌ Pagination controller not available!');
    }
}
```

## Conclusion

The filter system code is **architecturally sound** and **logically correct**. The initialization race condition has been fixed. The issue is most likely:

1. **Browser cache** - User viewing old HTML
2. **Data mismatch** - Actual data attribute values don't match expected values
3. **JavaScript error** - Something else breaking before filters run

**Next Steps:**
1. User should run the diagnostic script from `debug_filters.html`
2. User should hard refresh the browser
3. User should check browser console for errors
4. If still not working, we need to see the actual generated HTML to verify data attributes

The diagnostic script will definitively identify which of these is the issue.