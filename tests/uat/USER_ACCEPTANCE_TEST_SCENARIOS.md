# User Acceptance Test (UAT) Scenarios

## Overview
Three comprehensive user testing scenarios for automated UAT of the Ride Optimizer web platform. Each scenario represents a complete user journey from authentication through task completion.

---

## Scenario 1: Morning Commute Planning - "The Daily Commuter"

### User Persona
**Sarah** - Software engineer who bikes to work daily, checks weather and route conditions every morning before leaving.

### User Story
"As a daily bike commuter, I want to quickly check today's weather and get my optimal commute route recommendation so I can leave on time with the right gear."

### Test Steps

#### 1. Authentication & Dashboard Access
```python
# User opens app on mobile device (iPhone SE, 320px width)
GET /
EXPECT: Redirect to /dashboard
EXPECT: Status 200
EXPECT: Page loads in < 2 seconds
```

#### 2. View Dashboard Weather Summary
```python
# User sees current weather at a glance
GET /dashboard
EXPECT: Weather widget displays:
  - Current temperature (°F)
  - "Feels like" temperature
  - Wind speed and direction
  - Precipitation probability
  - Weather icon (sunny/cloudy/rainy)
EXPECT: All data loaded within 1 second
EXPECT: Mobile-friendly layout (touch targets ≥ 44px)
```

#### 3. Get Next Commute Recommendation
```python
# User taps "Get Recommendation" button
POST /api/recommendation
REQUEST: {
  "time": "now",
  "direction": "to_work"
}
EXPECT: Response within 3 seconds
EXPECT: JSON response contains:
  - route_name (e.g., "Harrison via Damen")
  - distance_miles
  - estimated_duration_minutes
  - weather_score (0-100)
  - traffic_score (0-100)
  - overall_score (0-100)
  - recommendation_reason (human-readable)
```

#### 4. View Route Details
```python
# User taps on recommended route to see details
GET /commute?route_id=<route_id>
EXPECT: Route details page displays:
  - Route map (polyline visualization)
  - Turn-by-turn directions
  - Elevation profile
  - Historical performance (avg speed, uses count)
  - Current conditions (weather, traffic)
EXPECT: Page responsive on mobile
EXPECT: Map interactive (zoom, pan)
```

#### 5. Check Alternative Routes
```python
# User wants to see other options
GET /api/routes?direction=to_work&limit=5
EXPECT: List of 5 alternative routes
EXPECT: Each route shows:
  - route_name
  - distance_miles
  - score (sorted by score descending)
  - weather_suitability
EXPECT: Response time < 2 seconds
```

### Success Criteria
- ✅ Complete workflow in < 30 seconds
- ✅ All API calls return valid data
- ✅ Mobile layout works on 320px viewport
- ✅ Weather data is current (< 1 hour old)
- ✅ Route recommendation matches user's typical commute time
- ✅ No JavaScript errors in console
- ✅ All touch targets meet 44x44px minimum

### Automated Test Implementation
```python
@pytest.mark.uat
@pytest.mark.scenario1
class TestDailyCommuterScenario:
    """UAT Scenario 1: Morning Commute Planning"""
    
    def test_complete_morning_commute_workflow(self, client, mock_weather, mock_routes):
        # Step 1: Access dashboard
        response = client.get('/')
        assert response.status_code == 302  # Redirect to dashboard
        
        # Step 2: View dashboard
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Current Weather' in response.data
        
        # Step 3: Get recommendation
        response = client.post('/api/recommendation', json={
            'time': 'now',
            'direction': 'to_work'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'route_name' in data
        assert 'overall_score' in data
        assert 0 <= data['overall_score'] <= 100
        
        # Step 4: View route details
        route_id = data['route_id']
        response = client.get(f'/commute?route_id={route_id}')
        assert response.status_code == 200
        
        # Step 5: Check alternatives
        response = client.get('/api/routes?direction=to_work&limit=5')
        assert response.status_code == 200
        routes = response.get_json()
        assert len(routes) <= 5
```

---

## Scenario 2: Weekend Long Ride Planning - "The Weekend Warrior"

### User Persona
**Mike** - Recreational cyclist planning a 50-mile weekend ride, wants optimal weather window and scenic route.

### User Story
"As a weekend cyclist, I want to find the best day and time for a long ride with favorable weather and explore new scenic routes."

### Test Steps

#### 1. Access Route Planner
```python
# User opens planner on tablet (768px width)
GET /planner
EXPECT: Status 200
EXPECT: Planner interface displays:
  - Date/time picker
  - Distance slider (10-100 miles)
  - Route type selector (loop/out-and-back)
  - Weather forecast integration
```

#### 2. View 7-Day Weather Forecast
```python
# User checks weather for next week
GET /api/weather/forecast?days=7
EXPECT: Response within 2 seconds
EXPECT: JSON array with 7 daily forecasts:
  - date (ISO format)
  - high_temp_f
  - low_temp_f
  - precipitation_probability
  - wind_speed_mph
  - wind_direction
  - conditions (sunny/cloudy/rainy)
  - cycling_score (0-100)
```

#### 3. Filter Routes by Distance
```python
# User sets distance filter to 45-55 miles
GET /api/routes?min_distance=45&max_distance=55&type=loop
EXPECT: Filtered route list
EXPECT: All routes within distance range
EXPECT: Routes sorted by popularity (uses_count)
EXPECT: Each route shows:
  - route_name
  - distance_miles (45-55)
  - elevation_gain_feet
  - difficulty_rating
  - scenic_rating (if available)
```

#### 4. View Route Library with Map
```python
# User browses route library
GET /routes
EXPECT: Status 200
EXPECT: Interactive map showing all routes
EXPECT: Route cards with:
  - Route polyline on map
  - Distance and elevation
  - Last ridden date
  - Uses count
  - Average speed
EXPECT: Click route card to highlight on map
```

#### 5. Analyze Long Ride Conditions
```python
# User selects Saturday 8am for 50-mile ride
POST /api/long-rides/analyze
REQUEST: {
  "route_id": "<route_id>",
  "start_time": "2026-05-10T08:00:00",
  "estimated_duration_hours": 3.5
}
EXPECT: Response within 5 seconds
EXPECT: JSON response contains:
  - hourly_weather_forecast (array of 4 hours)
  - temperature_range (start/end temps)
  - wind_conditions (avg speed, gusts)
  - precipitation_risk (percentage)
  - overall_suitability_score (0-100)
  - recommendations (array of strings)
```

### Success Criteria
- ✅ Complete workflow in < 2 minutes
- ✅ Weather forecast accurate and up-to-date
- ✅ Route filtering works correctly
- ✅ Map visualization loads and is interactive
- ✅ Long ride analysis provides actionable insights
- ✅ Tablet layout (768px) displays properly
- ✅ All data persists across page navigation

### Automated Test Implementation
```python
@pytest.mark.uat
@pytest.mark.scenario2
class TestWeekendWarriorScenario:
    """UAT Scenario 2: Weekend Long Ride Planning"""
    
    def test_complete_long_ride_planning_workflow(self, client, mock_weather, mock_routes):
        # Step 1: Access planner
        response = client.get('/planner')
        assert response.status_code == 200
        
        # Step 2: Get 7-day forecast
        response = client.get('/api/weather/forecast?days=7')
        assert response.status_code == 200
        forecast = response.get_json()
        assert len(forecast) == 7
        assert all('cycling_score' in day for day in forecast)
        
        # Step 3: Filter routes by distance
        response = client.get('/api/routes?min_distance=45&max_distance=55&type=loop')
        assert response.status_code == 200
        routes = response.get_json()
        assert all(45 <= r['distance_miles'] <= 55 for r in routes)
        
        # Step 4: View route library
        response = client.get('/routes')
        assert response.status_code == 200
        assert b'Route Library' in response.data
        
        # Step 5: Analyze long ride
        route_id = routes[0]['id']
        response = client.post('/api/long-rides/analyze', json={
            'route_id': route_id,
            'start_time': '2026-05-10T08:00:00',
            'estimated_duration_hours': 3.5
        })
        assert response.status_code == 200
        analysis = response.get_json()
        assert 'hourly_weather_forecast' in analysis
        assert 'overall_suitability_score' in analysis
        assert len(analysis['hourly_weather_forecast']) >= 3
```

---

## Scenario 3: Route Library Management - "The Data Enthusiast"

### User Persona
**Alex** - Power user who tracks all rides, analyzes performance trends, and maintains detailed route library.

### User Story
"As a data-driven cyclist, I want to view my complete route history, analyze performance trends, and organize my route library efficiently."

### Test Steps

#### 1. Access Route Library Dashboard
```python
# User opens route library on desktop (1920px width)
GET /routes
EXPECT: Status 200
EXPECT: Route library displays:
  - Total routes count
  - Total distance ridden
  - Most popular routes (top 5)
  - Recently added routes
  - Search/filter controls
```

#### 2. Search Routes by Name
```python
# User searches for "Harrison" routes
GET /api/routes?search=Harrison
EXPECT: Response within 1 second
EXPECT: Filtered results contain "Harrison" in route_name
EXPECT: Results sorted by relevance
EXPECT: Each result shows:
  - route_name (with "Harrison" highlighted)
  - distance_miles
  - uses_count
  - last_ridden_date
  - average_speed_mph
```

#### 3. View Route Performance History
```python
# User clicks on specific route to see all rides
GET /api/routes/<route_id>/history
EXPECT: Response within 2 seconds
EXPECT: JSON array of all activities on this route:
  - activity_id
  - date (ISO format)
  - duration_minutes
  - average_speed_mph
  - weather_conditions
  - notes (if any)
EXPECT: Sorted by date descending (most recent first)
```

#### 4. Compare Similar Routes
```python
# User wants to compare "Harrison via Damen" vs "Harrison via Ashland"
POST /api/routes/compare
REQUEST: {
  "route_ids": ["<route_id_1>", "<route_id_2>"]
}
EXPECT: Response within 3 seconds
EXPECT: JSON comparison data:
  - side_by_side_stats (distance, elevation, avg speed)
  - route_similarity_score (0-100)
  - polyline_overlay (for map visualization)
  - performance_comparison (which is faster/easier)
  - recommendation (which to use when)
```

#### 5. Export Route Data
```python
# User exports route library to JSON
GET /api/routes/export?format=json
EXPECT: Response within 5 seconds
EXPECT: JSON file download
EXPECT: Contains all routes with:
  - Complete route metadata
  - Polyline coordinates
  - Performance statistics
  - Activity history
EXPECT: File size reasonable (< 5MB for 100 routes)
```

#### 6. View Analytics Dashboard
```python
# User checks overall cycling statistics
GET /api/analytics/summary
EXPECT: Response within 2 seconds
EXPECT: JSON summary statistics:
  - total_rides_count
  - total_distance_miles
  - total_time_hours
  - average_speed_mph
  - most_ridden_route
  - favorite_time_of_day
  - monthly_trends (last 12 months)
```

### Success Criteria
- ✅ Complete workflow in < 3 minutes
- ✅ Search returns accurate results instantly
- ✅ Route history loads all activities
- ✅ Route comparison provides meaningful insights
- ✅ Export generates valid JSON file
- ✅ Analytics dashboard shows accurate statistics
- ✅ Desktop layout (1920px) utilizes screen space efficiently
- ✅ All data operations complete without errors

### Automated Test Implementation
```python
@pytest.mark.uat
@pytest.mark.scenario3
class TestDataEnthusiastScenario:
    """UAT Scenario 3: Route Library Management"""
    
    def test_complete_route_library_workflow(self, client, mock_routes, mock_activities):
        # Step 1: Access route library
        response = client.get('/routes')
        assert response.status_code == 200
        assert b'Route Library' in response.data
        
        # Step 2: Search routes
        response = client.get('/api/routes?search=Harrison')
        assert response.status_code == 200
        routes = response.get_json()
        assert all('Harrison' in r['route_name'] for r in routes)
        
        # Step 3: View route history
        route_id = routes[0]['id']
        response = client.get(f'/api/routes/{route_id}/history')
        assert response.status_code == 200
        history = response.get_json()
        assert isinstance(history, list)
        assert all('activity_id' in activity for activity in history)
        
        # Step 4: Compare routes
        route_ids = [routes[0]['id'], routes[1]['id']]
        response = client.post('/api/routes/compare', json={
            'route_ids': route_ids
        })
        assert response.status_code == 200
        comparison = response.get_json()
        assert 'side_by_side_stats' in comparison
        assert 'route_similarity_score' in comparison
        
        # Step 5: Export data
        response = client.get('/api/routes/export?format=json')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        # Step 6: View analytics
        response = client.get('/api/analytics/summary')
        assert response.status_code == 200
        analytics = response.get_json()
        assert 'total_rides_count' in analytics
        assert 'total_distance_miles' in analytics
        assert analytics['total_rides_count'] > 0
```

---

## Running UAT Scenarios

### Command Line Execution
```bash
# Run all UAT scenarios
pytest tests/uat/ -v -m uat

# Run specific scenario
pytest tests/uat/ -v -m scenario1
pytest tests/uat/ -v -m scenario2
pytest tests/uat/ -v -m scenario3

# Run with detailed output
pytest tests/uat/ -v -m uat --tb=short

# Generate HTML report
pytest tests/uat/ -v -m uat --html=reports/uat_report.html
```

### CI/CD Integration
```yaml
# .github/workflows/uat.yml
name: User Acceptance Tests
on: [pull_request]
jobs:
  uat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run UAT Scenarios
        run: |
          pytest tests/uat/ -v -m uat --html=uat_report.html
      - name: Upload UAT Report
        uses: actions/upload-artifact@v2
        with:
          name: uat-report
          path: uat_report.html
```

## Performance Benchmarks

### Response Time Targets
- Dashboard load: < 2 seconds
- API calls: < 3 seconds
- Route analysis: < 5 seconds
- Search results: < 1 second

### Mobile Performance
- First Contentful Paint: < 1.5 seconds
- Time to Interactive: < 3 seconds
- Lighthouse Score: > 90

### Data Accuracy
- Weather data: < 1 hour old
- Route statistics: Real-time
- Activity history: Complete and accurate

## Success Metrics

### Scenario 1 (Daily Commuter)
- 95% of users complete workflow in < 30 seconds
- 0 JavaScript errors
- 100% mobile compatibility

### Scenario 2 (Weekend Warrior)
- 90% of users find suitable route in < 2 minutes
- Weather forecast accuracy > 85%
- Route recommendations relevant

### Scenario 3 (Data Enthusiast)
- All data operations complete successfully
- Export files valid and complete
- Analytics accurate within 1%

## Maintenance

### Update Frequency
- Review scenarios quarterly
- Update test data monthly
- Verify API contracts weekly

### Test Data Management
- Use realistic test data (anonymized real activities)
- Maintain separate test database
- Reset test data before each run

### Monitoring
- Track UAT pass rates over time
- Alert on scenario failures
- Log performance regressions