# Map API Integration Testing Guide

## Prerequisites

1. **Ensure cache files exist:**
   ```bash
   ls -la cache/route_groups_cache.json
   ```
   If missing, run CLI analysis first:
   ```bash
   python3 main.py --analyze
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify geopy is installed:**
   ```bash
   python3 -c "import geopy; print('geopy OK')"
   ```

## Testing Steps

### 1. Start Flask Development Server

```bash
export FLASK_APP=launch.py
export FLASK_ENV=development
python3 -m flask run --port 5000
```

### 2. Test Endpoints with curl

#### Test Coordinates Endpoint
```bash
# Get route coordinates (replace route_123 with actual route ID from cache)
curl http://localhost:5000/api/map/routes/route_123/coordinates

# With sampling
curl "http://localhost:5000/api/map/routes/route_123/coordinates?sample_rate=5"
```

#### Test Elevation Endpoint
```bash
curl http://localhost:5000/api/map/routes/route_123/elevation

# With custom points
curl "http://localhost:5000/api/map/routes/route_123/elevation?points=50"
```

#### Test Speed Analytics
```bash
curl http://localhost:5000/api/map/routes/route_123/analytics/speed
```

#### Test Reverse Geocoding
```bash
curl "http://localhost:5000/api/map/geocode/reverse?lat=40.7128&lng=-74.0060"
```

#### Test Forward Geocoding
```bash
curl "http://localhost:5000/api/map/geocode/forward?q=Central+Park+New+York"
```

### 3. Get Actual Route IDs from Cache

```bash
python3 -c "
from src.secure_cache import SecureCacheStorage
cache = SecureCacheStorage('cache')
data = cache.load('route_groups_cache.json')
if data and 'groups' in data:
    for g in data['groups'][:5]:
        print(f\"Route ID: {g['id']}, Direction: {g['direction']}, Uses: {g['frequency']}\")
"
```

### 4. Run Automated Tests

```bash
# Run all map API tests
python3 -m pytest tests/test_map_api.py -v

# Run specific test class
python3 -m pytest tests/test_map_api.py::TestRouteCoordinatesEndpoint -v

# Run with coverage
python3 -m pytest tests/test_map_api.py --cov=app/api --cov-report=html
```

### 5. Frontend Integration Test

Create `test_map_api_frontend.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Map API Test</title>
</head>
<body>
    <h1>Map API Integration Test</h1>
    <div id="results"></div>
    
    <script>
        async function testAPI() {
            const results = document.getElementById('results');
            
            // Test coordinates endpoint
            try {
                const response = await fetch('http://localhost:5000/api/map/routes/route_123/coordinates');
                const data = await response.json();
                results.innerHTML += `<h2>Coordinates:</h2><pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (e) {
                results.innerHTML += `<p>Error: ${e.message}</p>`;
            }
            
            // Test geocoding
            try {
                const response = await fetch('http://localhost:5000/api/map/geocode/reverse?lat=40.7128&lng=-74.0060');
                const data = await response.json();
                results.innerHTML += `<h2>Geocoding:</h2><pre>${JSON.stringify(data, null, 2)}</pre>`;
            } catch (e) {
                results.innerHTML += `<p>Error: ${e.message}</p>`;
            }
        }
        
        testAPI();
    </script>
</body>
</html>
```

Open in browser: `open test_map_api_frontend.html`

## Troubleshooting

### Issue: "No route data available"
**Solution:** Run CLI analysis to generate cache:
```bash
python3 main.py --analyze
```

### Issue: "ModuleNotFoundError: No module named 'geopy'"
**Solution:** Install geopy:
```bash
pip install geopy
```

### Issue: "Geocoding service unavailable"
**Solution:** Check internet connection and Nominatim rate limits (1 req/sec)

### Issue: Route ID not found
**Solution:** Use actual route IDs from cache (see step 3 above)

## Expected Response Formats

### Coordinates Response
```json
{
  "status": "success",
  "route_id": "route_123",
  "coordinates": [
    {"lat": 40.7128, "lng": -74.0060},
    {"lat": 40.7138, "lng": -74.0070}
  ],
  "bounds": {
    "north": 40.7138,
    "south": 40.7128,
    "east": -74.0060,
    "west": -74.0070
  },
  "metadata": {
    "total_points": 100,
    "returned_points": 20,
    "sample_rate": 5
  }
}
```

### Elevation Response
```json
{
  "status": "success",
  "route_id": "route_123",
  "elevation_data": [
    {"distance": 0.0, "elevation": 100, "lat": 40.7128, "lng": -74.0060}
  ],
  "statistics": {
    "elevation_gain": 150,
    "total_distance": 10.5
  }
}
```

### Geocoding Response
```json
{
  "status": "success",
  "location": {"lat": 40.7128, "lng": -74.0060},
  "address": {
    "city": "New York",
    "state": "New York"
  },
  "display_name": "123 Main St, New York, NY",
  "cached": false
}
```

## Performance Benchmarks

Expected response times:
- Coordinates: < 200ms
- Elevation: < 500ms
- Geocoding (cached): < 50ms
- Geocoding (uncached): < 1s
- Speed analytics: < 300ms

## Next Steps After Testing

1. Update frontend JavaScript to use new endpoints
2. Replace hardcoded map data with API calls
3. Add error handling in frontend
4. Implement loading states
5. Close related issues (#83, #117, #234)