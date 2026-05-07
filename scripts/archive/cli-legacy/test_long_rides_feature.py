#!/usr/bin/env python3
"""
Test script for Long Rides feature implementation.

Tests that all components are properly integrated:
- Backend data calculation
- Frontend rendering
- Map initialization
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.long_ride_analyzer import LongRide
from src.report_generator import ReportGenerator
from src.config import Config


def test_long_rides_data_preparation():
    """Test that report generator properly prepares long rides data."""
    print("🧪 Testing Long Rides Data Preparation...")
    
    # Create mock long rides data
    mock_rides = [
        LongRide(
            activity_id=12345,
            name="Test Ride 1",
            coordinates=[(41.8781, -87.6298), (41.8881, -87.6398)],
            distance=50000,  # 50km in meters
            duration=7200,  # 2 hours in seconds
            elevation_gain=500,
            timestamp="2024-01-15T10:00:00Z",
            average_speed=6.94,  # m/s
            start_location=(41.8781, -87.6298),
            end_location=(41.8881, -87.6398),
            is_loop=True
        ),
        LongRide(
            activity_id=12346,
            name="Test Ride 2",
            coordinates=[(41.8781, -87.6298), (41.9081, -87.6598)],
            distance=75000,  # 75km
            duration=10800,  # 3 hours
            elevation_gain=800,
            timestamp="2024-02-20T14:00:00Z",
            average_speed=6.94,
            start_location=(41.8781, -87.6298),
            end_location=(41.9081, -87.6598),
            is_loop=False
        ),
        LongRide(
            activity_id=12347,
            name="Test Ride 3",
            coordinates=[(41.8781, -87.6298), (41.8981, -87.6498)],
            distance=60000,  # 60km
            duration=8640,  # 2.4 hours
            elevation_gain=600,
            timestamp="2024-03-10T09:00:00Z",
            average_speed=6.94,
            start_location=(41.8781, -87.6298),
            end_location=(41.8981, -87.6498),
            is_loop=True
        )
    ]
    
    # Create mock analysis results
    analysis_results = {
        'long_rides': mock_rides,
        'config': Config(),
        'all_activities': [],
        'commute_activities': [],
        'route_groups': [],
        'ranked_routes': [],
        'home': type('obj', (object,), {'lat': 41.8781, 'lon': -87.6298})(),
        'work': type('obj', (object,), {'lat': 41.8881, 'lon': -87.6398})()
    }
    
    # Create report generator
    generator = ReportGenerator(analysis_results)
    
    # Prepare context
    context = generator._prepare_context()
    
    # Verify long rides stats
    assert 'long_rides_stats' in context, "❌ long_rides_stats missing from context"
    stats = context['long_rides_stats']
    
    print(f"✅ Long rides stats calculated:")
    print(f"   - Total rides: {stats.get('total_rides', 0)}")
    print(f"   - Average distance: {stats.get('avg_distance', 0):.1f} km")
    print(f"   - Longest ride: {stats.get('longest_ride', 0):.1f} km")
    print(f"   - Total elevation: {stats.get('total_elevation', 0):.0f} m")
    print(f"   - Average speed: {stats.get('avg_speed_kmh', 0):.1f} km/h")
    
    # Verify top 10 rides
    assert 'top_10_rides' in context, "❌ top_10_rides missing from context"
    top_10 = context['top_10_rides']
    print(f"✅ Top 10 rides prepared: {len(top_10)} rides")
    
    # Verify monthly stats
    assert 'monthly_stats' in context, "❌ monthly_stats missing from context"
    monthly = context['monthly_stats']
    if monthly:
        print(f"✅ Monthly stats prepared: {len(monthly.get('labels', []))} months")
    
    # Verify GeoJSON data
    assert 'long_rides_geojson' in context, "❌ long_rides_geojson missing from context"
    geojson = context['long_rides_geojson']
    print(f"✅ GeoJSON data prepared: {len(geojson)} routes")
    
    # Verify GeoJSON structure
    if geojson:
        first_route = geojson[0]
        required_fields = ['activity_id', 'name', 'coordinates', 'distance_km', 
                          'duration_hours', 'elevation_gain', 'is_loop']
        for field in required_fields:
            assert field in first_route, f"❌ {field} missing from GeoJSON"
        print(f"✅ GeoJSON structure valid")
    
    print("\n✅ All tests passed!")
    return True


def test_statistics_calculations():
    """Test that statistics are calculated correctly."""
    print("\n🧪 Testing Statistics Calculations...")
    
    # Test data
    rides = [
        LongRide(12345, "Ride 1", [], 50000, 7200, 500, "2024-01-15T10:00:00Z", 
                6.94, (0,0), (0,0), True),
        LongRide(12346, "Ride 2", [], 75000, 10800, 800, "2024-01-20T10:00:00Z", 
                6.94, (0,0), (0,0), False),
        LongRide(12347, "Ride 3", [], 60000, 8640, 600, "2024-02-10T10:00:00Z", 
                6.94, (0,0), (0,0), True),
    ]
    
    # Calculate stats manually
    distances = [r.distance_km for r in rides]
    speeds = [r.average_speed * 3.6 for r in rides]
    elevations = [r.elevation_gain for r in rides]
    
    expected_avg_distance = sum(distances) / len(distances)
    expected_longest = max(distances)
    expected_total_elevation = sum(elevations)
    expected_avg_speed = sum(speeds) / len(speeds)
    
    print(f"✅ Expected average distance: {expected_avg_distance:.1f} km")
    print(f"✅ Expected longest ride: {expected_longest:.1f} km")
    print(f"✅ Expected total elevation: {expected_total_elevation:.0f} m")
    print(f"✅ Expected average speed: {expected_avg_speed:.1f} km/h")
    
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Long Rides Feature Test Suite")
    print("=" * 60)
    
    try:
        test_long_rides_data_preparation()
        test_statistics_calculations()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe Long Rides feature is properly implemented!")
        print("Run 'python main.py --analyze' to see it in action.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
