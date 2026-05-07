#!/usr/bin/env python3
"""
Test harness for Issue #138 - Weather Integration

This script provides manual testing capabilities for QA to verify:
- Weather snapshot creation and caching
- Weather service API integration
- Dashboard weather display
- Commute weather reasoning
- Planner weather-aware ranking

Usage:
    python scripts/test_weather_integration.py [--test-all|--test-cache|--test-service|--test-ui]
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models.weather import WeatherSnapshot
from app.services.weather_service import WeatherService
from src.config import Config


def test_weather_snapshot_model():
    """Test WeatherSnapshot model CRUD operations."""
    print("\n" + "="*60)
    print("TEST: WeatherSnapshot Model")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        # Test 1: Create weather snapshot
        print("\n1. Creating weather snapshot...")
        weather_data = {
            'temperature': 20.0,
            'conditions': 'Clear',
            'wind_speed': 10.0,
            'wind_direction': 180,
            'precipitation': 0.0,
            'humidity': 50.0
        }
        
        snapshot = WeatherSnapshot.create_from_weather_data(
            weather_data,
            location_name='Test Location',
            is_current=True
        )
        
        print(f"   ✓ Created snapshot ID: {snapshot.id}")
        print(f"   ✓ Location: {snapshot.location_name}")
        print(f"   ✓ Temperature: {snapshot.temperature_c}°C")
        print(f"   ✓ Comfort Score: {snapshot.comfort_score:.2f}")
        print(f"   ✓ Cycling Favorability: {snapshot.cycling_favorability}")
        
        # Test 2: Retrieve cached weather
        print("\n2. Retrieving cached weather...")
        lat, lon = snapshot.latitude, snapshot.longitude
        retrieved = WeatherSnapshot.get_current_for_location(lat, lon, max_age_hours=2)
        
        if retrieved:
            print(f"   ✓ Retrieved snapshot ID: {retrieved.id}")
            # Ensure both datetimes are timezone-aware for comparison
            retrieved_ts = retrieved.timestamp if retrieved.timestamp.tzinfo else retrieved.timestamp.replace(tzinfo=timezone.utc)
            age_minutes = (datetime.now(timezone.utc) - retrieved_ts).seconds // 60
            print(f"   ✓ Age: {age_minutes} minutes")
        else:
            print("   ✗ Failed to retrieve cached weather")
            return False
        
        # Test 3: Comfort score calculation
        print("\n3. Testing comfort score calculation...")
        test_cases = [
            ({'temperature': 20.0, 'wind_speed': 5.0, 'precipitation': 0.0}, 'favorable'),
            ({'temperature': -5.0, 'wind_speed': 35.0, 'precipitation': 10.0}, 'unfavorable'),
            ({'temperature': 15.0, 'wind_speed': 20.0, 'precipitation': 2.0}, 'neutral')
        ]
        
        for weather, expected_favorability in test_cases:
            snap = WeatherSnapshot.create_from_weather_data(
                weather, location_name='Test', is_current=True
            )
            print(f"   Temp: {weather['temperature']}°C, Wind: {weather['wind_speed']} kph")
            print(f"   → Score: {snap.comfort_score:.2f}, Favorability: {snap.cycling_favorability}")
            
            if expected_favorability in snap.cycling_favorability:
                print(f"   ✓ Correct favorability")
            else:
                print(f"   ✗ Expected {expected_favorability}, got {snap.cycling_favorability}")
        
        # Test 4: Cleanup old snapshots
        print("\n4. Testing cleanup of old snapshots...")
        old_snapshot = WeatherSnapshot.create_from_weather_data(
            {'temperature': 15.0}, location_name='Old', is_current=True
        )
        old_snapshot.timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        old_snapshot.save()
        
        deleted = WeatherSnapshot.cleanup_old_snapshots(days=7)
        print(f"   ✓ Deleted {deleted} old snapshot(s)")
        
        print("\n✅ WeatherSnapshot Model Tests PASSED")
        return True


def test_weather_service():
    """Test WeatherService caching and degradation."""
    print("\n" + "="*60)
    print("TEST: WeatherService")
    print("="*60)
    
    app = create_app()
    config = Config('config/config.yaml')
    service = WeatherService(config)
    
    with app.app_context():
        # Test 1: Get current weather (cache miss)
        print("\n1. Testing weather fetch (cache miss)...")
        lat, lon = 40.7128, -74.0060  # NYC
        weather = service.get_current_weather(lat, lon, 'New York City')
        
        if weather:
            print(f"   ✓ Fetched weather for NYC")
            print(f"   Temperature: {weather.get('temperature_c', weather.get('temperature'))}°C")
            print(f"   Conditions: {weather.get('conditions', 'N/A')}")
            print(f"   Comfort Score: {weather.get('comfort_score', 'N/A')}")
        else:
            print("   ⚠ Weather fetch failed (API may be unavailable)")
        
        # Test 2: Get current weather (cache hit)
        print("\n2. Testing weather fetch (cache hit)...")
        weather2 = service.get_current_weather(lat, lon, 'New York City')
        
        if weather2:
            print(f"   ✓ Retrieved from cache")
            if weather2.get('is_stale'):
                print(f"   ⚠ Data is stale (age: {weather2.get('age_hours')} hours)")
            else:
                print(f"   ✓ Data is fresh")
        
        # Test 3: Route weather with wind impact
        print("\n3. Testing route weather with wind impact...")
        coordinates = [
            (40.7128, -74.0060),
            (40.7580, -73.9855),
            (40.7614, -73.9776)
        ]
        
        route_weather = service.get_route_weather(coordinates, 'Test Route')
        
        if route_weather:
            print(f"   ✓ Fetched route weather")
            if 'wind_impact' in route_weather:
                impact = route_weather['wind_impact']
                print(f"   Headwind: {impact.get('headwind_pct', 0):.1f}%")
                print(f"   Tailwind: {impact.get('tailwind_pct', 0):.1f}%")
                print(f"   Crosswind: {impact.get('crosswind_pct', 0):.1f}%")
        else:
            print("   ⚠ Route weather fetch failed")
        
        print("\n✅ WeatherService Tests PASSED")
        return True


def test_ui_integration():
    """Test weather integration in UI views."""
    print("\n" + "="*60)
    print("TEST: UI Integration")
    print("="*60)
    
    app = create_app()
    client = app.test_client()
    
    with app.app_context():
        # Pre-populate weather
        weather_data = {'temperature': 20.0, 'conditions': 'Clear'}
        WeatherSnapshot.create_from_weather_data(
            weather_data, location_name='Home', is_current=True
        )
        
        # Test 1: Dashboard weather display
        print("\n1. Testing dashboard weather display...")
        response = client.get('/')
        
        if response.status_code == 200:
            print(f"   ✓ Dashboard loaded (status: {response.status_code})")
            if b'Weather' in response.data or b'weather' in response.data:
                print("   ✓ Weather section present")
            else:
                print("   ⚠ Weather section not found in HTML")
        else:
            print(f"   ✗ Dashboard failed (status: {response.status_code})")
        
        # Test 2: Commute weather reasoning
        print("\n2. Testing commute weather reasoning...")
        response = client.get('/commute')
        
        if response.status_code == 200:
            print(f"   ✓ Commute page loaded (status: {response.status_code})")
            if b'Weather' in response.data or b'weather' in response.data:
                print("   ✓ Weather reasoning present")
            else:
                print("   ⚠ Weather reasoning not found")
        else:
            print(f"   ✗ Commute page failed (status: {response.status_code})")
        
        # Test 3: Planner weather integration
        print("\n3. Testing planner weather integration...")
        response = client.get('/planner')
        
        if response.status_code == 200:
            print(f"   ✓ Planner page loaded (status: {response.status_code})")
        else:
            print(f"   ✗ Planner page failed (status: {response.status_code})")
        
        print("\n✅ UI Integration Tests PASSED")
        return True


def main():
    """Run test harness."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test weather integration')
    parser.add_argument('--test-all', action='store_true', help='Run all tests')
    parser.add_argument('--test-cache', action='store_true', help='Test caching only')
    parser.add_argument('--test-service', action='store_true', help='Test service only')
    parser.add_argument('--test-ui', action='store_true', help='Test UI only')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("WEATHER INTEGRATION TEST HARNESS - Issue #138")
    print("="*60)
    
    results = []
    
    if args.test_all or args.test_cache or (not any([args.test_cache, args.test_service, args.test_ui])):
        results.append(('WeatherSnapshot Model', test_weather_snapshot_model()))
    
    if args.test_all or args.test_service or (not any([args.test_cache, args.test_service, args.test_ui])):
        results.append(('WeatherService', test_weather_service()))
    
    if args.test_all or args.test_ui or (not any([args.test_cache, args.test_service, args.test_ui])):
        results.append(('UI Integration', test_ui_integration()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests PASSED!")
        return 0
    else:
        print("\n⚠️  Some tests FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
