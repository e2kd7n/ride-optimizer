# Filter Behavior - Systematic Evaluation & Solution Plan

## Problem Statement
Filters are not working despite:
- ✅ Initialization race condition fixed
- ✅ Code logic appears correct
- ✅ Browser cache ruled out as issue

## Data Flow Verification

### ✅ Step 1: Direction Values (VERIFIED)
**Source:** `src/route_analyzer.py` lines 600, 606
```python
htw_groups = self._group_routes_by_similarity(home_to_work, 'home_to_work')
wth_groups = self._group_routes_by_similarity(work_to_home, 'work_to_home')
```

**Expected Values:**
- `'home_to_work'`
- `'work_to_home'`

**JavaScript Expects:**
- `'home_to_work'`
- `'work_to_home'`

**Status:** ✅ VALUES MATCH

### ✅ Step 2: is_plus_route Flag (VERIFIED)
**Source:** `src/route_analyzer.py` line 778
```python
group.is_plus_route = True
```

**Type:** Boolean (`True` or `False`)

**Template Rendering:** `templates/report_template.html` line 353
```jinja2
data-is-plus="{{ 'true' if route.is_plus_route else 'false' }}"
```

**JavaScript Expects:** String `'true'` or `'false'`

**Status:** ✅ CONVERSION CORRECT

## Hypothesis Testing Plan

### Hypothesis 1: Template Variable Access Issue ⚠️ HIGH PROBABILITY

**Issue:** Line 350 in template accesses `route.group.direction`

```html
data-direction="{{ route.group.direction }}"
```

But `route` is a dictionary from `report_generator.py` line 361-371:
```python
ranked_routes.append({
    'group': group,  # ← This is the RouteGroup object
    'score': score,
    'breakdown': breakdown,
    'metrics': metrics,
    'name': route_name,
    'color': route_colors.get(group.id, '#808080'),
    'strava_url': f"https://www.strava.com/activities/{most_recent_activity_id}",
    'prevailing_wind': prevailing_wind,
    'is_plus_route': group.is_plus_route
})
```

**In Jinja2:** `route.group` accesses the dictionary key `'group'`, which returns the RouteGroup object. Then `.direction` accesses the object's attribute.

**This should work!** Jinja2 handles both dict keys and object attributes.

**Test:** Check if `route.group` is actually accessible in template.

### Hypothesis 2: Filter Button Selectors Wrong ⚠️ MEDIUM PROBABILITY

**JavaScript Line 500:**
```javascript
const directionButtons = document.querySelectorAll('.direction-filter .btn-group button[data-direction]');
```

**This selector requires:**
1. Parent element with class `direction-filter`
2. Child element with class `btn-group`
3. Button elements with `data-direction` attribute

**Test:** Verify HTML structure matches this selector pattern.

### Hypothesis 3: Event Listeners Not Attaching 🔴 HIGH PROBABILITY

**Potential Issue:** The event listeners are set up inside an IIFE that runs immediately, but the buttons might not exist in the DOM yet.

**JavaScript Lines 579-605:**
```javascript
directionButtons.forEach(button => {
    button.addEventListener('click', function(e) {
        // ...
    });
});
```

**If `directionButtons` is empty (length 0), no event listeners are attached!**

**Test:** Add logging to check if `directionButtons.length > 0`

### Hypothesis 4: CSS Classes Not Being Applied 🔴 MEDIUM PROBABILITY

**Potential Issue:** The classList operations might be failing silently.

**JavaScript Lines 534-544:**
```javascript
if (matchesDirection) {
    row.classList.remove('direction-hidden');
} else {
    row.classList.add('direction-hidden');
}
```

**Test:** Add logging before/after classList operations to verify they execute.

## Evaluation Steps

### Step 1: Add Comprehensive Logging
Add logging at critical points to trace execution:

```javascript
// After line 498 - Check if rows found
const allRouteRows = document.querySelectorAll('.route-row');
console.log('🔍 Filter Init: Found', allRouteRows.length, 'route rows');

// After line 500 - Check if buttons found
const directionButtons = document.querySelectorAll('.direction-filter .btn-group button[data-direction]');
console.log('🔍 Filter Init: Found', directionButtons.length, 'direction buttons');

// After line 501-502 - Check if plus buttons found
const showPlusBtn = document.getElementById('show-plus-routes');
const hidePlusBtn = document.getElementById('hide-plus-routes');
console.log('🔍 Filter Init: Show Plus button:', !!showPlusBtn, 'Hide Plus button:', !!hidePlusBtn);

// Inside event listener (line 580) - Check if firing
console.log('🔍 Direction button clicked!', e.currentTarget.getAttribute('data-direction'));
```

### Step 2: Verify HTML Structure
Check the actual generated HTML for:

1. **Filter buttons structure:**
```html
<div class="direction-filter">
    <div class="btn-group">
        <button data-direction="all">All Routes</button>
        <button data-direction="home_to_work">To Work</button>
        <button data-direction="work_to_home">To Home</button>
    </div>
</div>
```

2. **Plus route buttons:**
```html
<button id="show-plus-routes">Show</button>
<button id="hide-plus-routes">Hide</button>
```

3. **Route rows:**
```html
<tr class="route-row" 
    data-direction="home_to_work" 
    data-is-plus="false">
```

### Step 3: Test Manual Filter Application
In browser console:
```javascript
// Check if systems loaded
console.log('Filter system:', typeof window.routeFilters);
console.log('Pagination system:', typeof window.paginationController);

// Manually trigger filter
if (window.routeFilters) {
    window.routeFilters.applyFilters();
}

// Check visible rows
const visible = document.querySelectorAll('.route-row:not(.direction-hidden):not(.plus-hidden):not(.page-hidden)');
console.log('Visible rows:', visible.length);
```

## Most Likely Root Causes (Ranked)

### 1. 🔴 Event Listeners Not Attaching (85% probability)
**Symptom:** Clicking buttons does nothing
**Cause:** `directionButtons` selector returns empty NodeList
**Fix:** Verify HTML structure or fix selector

### 2. 🔴 Buttons Don't Exist in HTML (10% probability)
**Symptom:** Selector can't find buttons
**Cause:** Template not rendering filter buttons
**Fix:** Check template rendering logic

### 3. ⚠️ JavaScript Error Before Filter Code (3% probability)
**Symptom:** Filter code never runs
**Cause:** Earlier error breaks script execution
**Fix:** Check console for errors

### 4. ⚠️ Data Attributes Not Set (2% probability)
**Symptom:** Filters run but don't match anything
**Cause:** Template not setting data attributes
**Fix:** Verify template rendering

## Solution Implementation Plan

### Phase 1: Diagnostic Enhancement (15 min)
1. Add comprehensive logging to filter initialization
2. Add logging to event handlers
3. Add logging to applyFilters function
4. Regenerate report and check console output

### Phase 2: HTML Structure Verification (10 min)
1. Inspect generated HTML
2. Verify filter button structure
3. Verify route row data attributes
4. Document any mismatches

### Phase 3: Fix Implementation (30 min)
Based on findings:

**If buttons not found:**
- Fix HTML template structure
- Update JavaScript selector

**If event listeners not attaching:**
- Wrap in DOMContentLoaded
- Use event delegation
- Add defensive checks

**If data attributes wrong:**
- Fix template rendering
- Update Python data preparation

### Phase 4: Testing & Validation (15 min)
1. Test all filter combinations
2. Verify pagination updates
3. Test edge cases
4. Document solution

## Next Actions

1. **Implement diagnostic logging** in `templates/report_template.html`
2. **Regenerate report** with new logging
3. **Check browser console** for diagnostic output
4. **Identify specific failure point**
5. **Implement targeted fix**

## Success Criteria

- [ ] Console shows "Found X route rows" (X > 0)
- [ ] Console shows "Found 3 direction buttons"
- [ ] Console shows "Show Plus button: true, Hide Plus button: true"
- [ ] Clicking button logs "Direction button clicked!"
- [ ] Clicking button changes visible rows
- [ ] Filters work correctly for all combinations