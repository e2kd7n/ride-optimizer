# JSON Serialization Error Fix - Implementation Plan

## Issue Summary

**Error**: `TypeError: Object of type Route is not JSON serializable`

**Location**: Line 653 in `templates/report_template.html`

**Root Cause**: The Jinja2 `tojson` filter attempts to serialize `route['group'].routes`, which contains `Route` dataclass objects that cannot be directly serialized to JSON.

## Error Details

### Stack Trace Analysis
```
File "/Users/erik/dev/ride-optimizer/src/report_generator.py", line 483, in _render_template
    return template.render(**context)
File "<template>", line 653, in top-level template code
File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/jinja2/filters.py", line 1721, in do_tojson
    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)
TypeError: Object of type Route is not JSON serializable
when serializing list item 0
```

### Problematic Code
**File**: `templates/report_template.html:653`
```html
<span class="uses-count" style="cursor: pointer; color: #667eea; text-decoration: underline; font-weight: 600;"
      onclick="showMatchedRoutes('{{ route['group'].id }}', '{{ route['name'] }}', {{ route['group'].routes | tojson | safe }})"
      title="Click to view matched activities">
```

### JavaScript Consumer
**File**: `templates/report_template.html:1157`
```javascript
function showMatchedRoutes(routeId, routeName, routes) {
    // Expects routes array with properties:
    // - start_date (for date display)
    // - distance (in meters)
    // - moving_time (duration in seconds)
    // - id (activity_id for Strava link)
}
```

## Route Dataclass Structure

**File**: `src/route_analyzer.py:38-48`
```python
@dataclass
class Route:
    """Represents a single route."""
    activity_id: int
    direction: str  # "home_to_work" or "work_to_home"
    coordinates: List[Tuple[float, float]]
    distance: float  # meters
    duration: int  # seconds
    elevation_gain: float  # meters
    timestamp: str  # ISO format
    average_speed: float  # m/s
    is_plus_route: bool = False
```

## Solution Implementation

### Step 1: Add Helper Method to ReportGenerator

**File**: `src/report_generator.py`

Add this method after line 115 (after `_generate_qr_code` method):

```python
def _route_to_dict(self, route: Route) -> dict:
    """
    Convert Route dataclass to JSON-serializable dictionary.
    
    Only includes fields needed by JavaScript showMatchedRoutes() function.
    
    Args:
        route: Route dataclass instance
        
    Returns:
        Dictionary with serializable route data
    """
    return {
        'id': route.activity_id,
        'start_date': route.timestamp,
        'distance': route.distance,
        'moving_time': route.duration
    }
```

### Step 2: Modify _prepare_context Method

**File**: `src/report_generator.py:367`

Current code (around line 367):
```python
ranked_routes.append({
    'group': group,
    'score': score,
    'breakdown': breakdown,
    'metrics': metrics,
    'name': route_name,
    'color': route_colors.get(group.id, '#808080'),
    'strava_url': f"https://www.strava.com/activities/{most_recent_activity_id}" if most_recent_activity_id else None,
    'current_weather': current_route_weather,
    'is_plus_route': group.is_plus_route
})
```

**Change to**:
```python
ranked_routes.append({
    'group': group,
    'score': score,
    'breakdown': breakdown,
    'metrics': metrics,
    'name': route_name,
    'color': route_colors.get(group.id, '#808080'),
    'strava_url': f"https://www.strava.com/activities/{most_recent_activity_id}" if most_recent_activity_id else None,
    'current_weather': current_route_weather,
    'is_plus_route': group.is_plus_route,
    'routes_data': [self._route_to_dict(r) for r in group.routes]  # Add this line
})
```

### Step 3: Update Template

**File**: `templates/report_template.html:653`

Current code:
```html
onclick="showMatchedRoutes('{{ route['group'].id }}', '{{ route['name'] }}', {{ route['group'].routes | tojson | safe }})"
```

**Change to**:
```html
onclick="showMatchedRoutes('{{ route['group'].id }}', '{{ route['name'] }}', {{ route['routes_data'] | tojson | safe }})"
```

## Import Requirements

Add this import at the top of `src/report_generator.py` if not already present:

```python
from .route_analyzer import Route
```

## Testing Plan

1. **Run analysis with force-reanalysis**:
   ```bash
   python3 main.py --analyze --force-reanalysis
   ```

2. **Verify report generation completes without errors**

3. **Test interactive functionality**:
   - Open generated HTML report
   - Click on "Uses" count for any route
   - Verify modal displays matched activities correctly
   - Verify Strava links work

4. **Verify data integrity**:
   - Check that activity dates display correctly
   - Check that distances and durations are accurate
   - Check that Strava links point to correct activities

## Benefits

1. **Minimal Changes**: Only 3 files modified
2. **Backward Compatible**: Keeps original `group` object for other template uses
3. **Efficient**: Only serializes necessary fields (reduces payload size)
4. **Maintainable**: Clear separation between dataclass and serialization logic
5. **Type Safe**: Uses existing Route dataclass structure

## Verification Checklist

- [ ] Helper method `_route_to_dict()` added to `ReportGenerator`
- [ ] Import statement for `Route` added to `report_generator.py`
- [ ] `routes_data` field added to ranked_routes dictionary
- [ ] Template updated to use `route['routes_data']` instead of `route['group'].routes`
- [ ] Analysis runs without JSON serialization errors
- [ ] Report generates successfully
- [ ] Modal displays matched activities correctly
- [ ] All Strava links work correctly

## Related Files

- `src/report_generator.py` - Main implementation
- `templates/report_template.html` - Template update
- `src/route_analyzer.py` - Route dataclass definition
- `main.py` - Entry point for analysis

## Notes

- No other `tojson` usage in templates requires changes (verified)
- No other dataclass serialization issues found (verified)
- This fix only affects the matched routes modal functionality
- Original Route objects remain available via `route['group']` for other template uses