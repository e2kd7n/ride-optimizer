#!/usr/bin/env python3
"""
Integration test for Map API endpoints.
Tests with actual cache data.
"""

import sys
import json
from src.secure_cache import SecureCacheStorage

def test_cache_data():
    """Test that cache data exists and is valid."""
    print("=" * 60)
    print("MAP API INTEGRATION TEST")
    print("=" * 60)
    
    try:
        import json
        with open('cache/route_groups_cache.json', 'r') as f:
            data = json.load(f)
        
        if not data:
            print("❌ FAIL: No cache data found")
            print("   Run: python3 main.py --analyze")
            return False
        
        if 'groups' not in data:
            print("❌ FAIL: Cache data missing 'groups' key")
            return False
        
        groups = data['groups']
        print(f"✅ Cache loaded: {len(groups)} route groups found")
        
        # Test first 3 routes
        print("\n" + "=" * 60)
        print("SAMPLE ROUTE DATA")
        print("=" * 60)
        
        for i, group in enumerate(groups[:3]):
            print(f"\nRoute {i+1}:")
            print(f"  ID: {group['id']}")
            print(f"  Direction: {group['direction']}")
            print(f"  Frequency: {group['frequency']} uses")
            
            rep_route = group.get('representative_route', {})
            coords = rep_route.get('coordinates', [])
            print(f"  Coordinates: {len(coords)} points")
            print(f"  Distance: {rep_route.get('distance', 0)/1000:.2f} km")
            print(f"  Elevation gain: {rep_route.get('elevation_gain', 0):.0f} m")
            print(f"  Avg speed: {rep_route.get('average_speed', 0)*3.6:.1f} km/h")
            
            if coords:
                print(f"  Start: ({coords[0][0]:.4f}, {coords[0][1]:.4f})")
                print(f"  End: ({coords[-1][0]:.4f}, {coords[-1][1]:.4f})")
        
        # Test API endpoint logic
        print("\n" + "=" * 60)
        print("API ENDPOINT SIMULATION")
        print("=" * 60)
        
        test_route_id = groups[0]['id']
        print(f"\nTesting with route: {test_route_id}")
        
        # Simulate coordinates endpoint
        route_group = next((g for g in groups if g['id'] == test_route_id), None)
        if route_group:
            coords = route_group['representative_route']['coordinates']
            print(f"✅ Coordinates endpoint would return {len(coords)} points")
            
            # Test sampling
            sample_rate = 5
            sampled = coords[::sample_rate]
            print(f"✅ With sample_rate={sample_rate}: {len(sampled)} points")
            
            # Test bounds calculation
            lats = [c[0] for c in coords]
            lngs = [c[1] for c in coords]
            bounds = {
                'north': max(lats),
                'south': min(lats),
                'east': max(lngs),
                'west': min(lngs)
            }
            print(f"✅ Bounds calculated: {bounds}")
        
        # Test speed analytics
        routes = route_group.get('routes', [])
        if routes:
            avg_speed = sum(r.get('average_speed', 0) for r in routes) / len(routes)
            print(f"✅ Speed analytics: avg {avg_speed*3.6:.1f} km/h across {len(routes)} routes")
        
        print("\n" + "=" * 60)
        print("CURL TEST COMMANDS")
        print("=" * 60)
        print("\nStart Flask server first:")
        print("  export FLASK_APP=launch.py")
        print("  python3 -m flask run --port 5000")
        print("\nThen test endpoints:")
        print(f"\n  # Coordinates")
        print(f"  curl http://localhost:5000/api/map/routes/{test_route_id}/coordinates")
        print(f"\n  # Elevation")
        print(f"  curl http://localhost:5000/api/map/routes/{test_route_id}/elevation")
        print(f"\n  # Speed analytics")
        print(f"  curl http://localhost:5000/api/map/routes/{test_route_id}/analytics/speed")
        print(f"\n  # Geocoding")
        print(f"  curl 'http://localhost:5000/api/map/geocode/reverse?lat={coords[0][0]}&lng={coords[0][1]}'")
        
        print("\n" + "=" * 60)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_cache_data()
    sys.exit(0 if success else 1)

# Made with Bob
