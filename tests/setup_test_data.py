#!/usr/bin/env python3
"""
Setup test data for integration tests.

This script creates synthetic test activities in a separate test cache
to avoid overwriting production data.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

def create_test_activities():
    """Create synthetic test activities for testing."""
    
    # Create test activities with varied routes
    activities = []
    base_date = datetime(2024, 1, 1, 8, 0, 0)
    
    # Route 1: Home to Work (main commute)
    for i in range(6):
        activities.append({
            'id': i + 1,
            'name': f'Morning Commute {i + 1}',
            'type': 'Ride',
            'start_date': (base_date + timedelta(days=i)).isoformat() + '+00:00',
            'distance': 5000.0 + (i * 50),
            'moving_time': 1200 + (i * 10),
            'elapsed_time': 1300 + (i * 10),
            'total_elevation_gain': 50.0 + (i * 2),
            'start_latlng': [38.5, -120.2],
            'end_latlng': [38.52, -120.25],
            'polyline': '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
            'average_speed': 4.17,
            'max_speed': 7.5
        })
    
    # Route 2: Alternative route (slightly different)
    for i in range(4):
        activities.append({
            'id': i + 7,
            'name': f'Evening Commute {i + 1}',
            'type': 'Ride',
            'start_date': (base_date + timedelta(days=i, hours=10)).isoformat() + '+00:00',
            'distance': 5200.0 + (i * 50),
            'moving_time': 1250 + (i * 10),
            'elapsed_time': 1350 + (i * 10),
            'total_elevation_gain': 55.0 + (i * 2),
            'start_latlng': [38.52, -120.25],
            'end_latlng': [38.5, -120.2],
            'polyline': 'bq~iF~rs|U_vmLnoqC_nqNwxq`@',
            'average_speed': 4.08,
            'max_speed': 7.2
        })
    
    # Route 3: Weekend long ride
    activities.append({
        'id': 11,
        'name': 'Weekend Long Ride',
        'type': 'Ride',
        'start_date': (base_date + timedelta(days=5)).isoformat() + '+00:00',
        'distance': 25000.0,
        'moving_time': 5400,
        'elapsed_time': 6000,
        'total_elevation_gain': 300.0,
        'start_latlng': [38.5, -120.2],
        'end_latlng': [38.5, -120.2],
        'polyline': '_p~iF~ps|U_ulLnnqC_mqNvxq`@_ulLnnqC_mqNvxq`@',
        'average_speed': 4.63,
        'max_speed': 9.0
    })
    
    # Route 4: Another commute variant
    activities.append({
        'id': 12,
        'name': 'Scenic Commute',
        'type': 'Ride',
        'start_date': (base_date + timedelta(days=6)).isoformat() + '+00:00',
        'distance': 6000.0,
        'moving_time': 1400,
        'elapsed_time': 1500,
        'total_elevation_gain': 80.0,
        'start_latlng': [38.5, -120.2],
        'end_latlng': [38.52, -120.25],
        'polyline': 'cq~iF~qs|U_wmLnpqC_oqNxxq`@',
        'average_speed': 4.29,
        'max_speed': 7.8
    })
    
    return activities

def save_test_cache():
    """Save test activities to test cache file."""
    
    # Create cache directory if it doesn't exist
    cache_dir = Path('data/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test cache file
    test_cache_path = cache_dir / 'activities_test.json'
    
    activities = create_test_activities()
    
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'count': len(activities),
        'activities': activities
    }
    
    with open(test_cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"✅ Created test cache with {len(activities)} activities")
    print(f"📁 Location: {test_cache_path}")
    print(f"⚠️  Production cache (data/cache/activities.json) is protected")

if __name__ == '__main__':
    save_test_cache()

# Made with Bob
