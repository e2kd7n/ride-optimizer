#!/usr/bin/env python3
"""Test script to verify sport_type field is correctly extracted from Strava activities."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import DataFetcher
from src.config import Config

def main():
    """Test sport_type extraction."""
    print("Testing sport_type field extraction...")
    print("-" * 60)
    
    # Load config
    config = Config()
    
    # Initialize data fetcher
    fetcher = DataFetcher(config)
    
    # Fetch activities
    print("Fetching activities from Strava...")
    activities = fetcher.fetch_activities(limit=50)
    
    print(f"\nFound {len(activities)} activities")
    print("\nChecking sport_type field for each activity:")
    print("-" * 60)
    
    gravel_count = 0
    road_count = 0
    other_count = 0
    
    for activity in activities:
        # Check if activity has sport_type
        sport_type = getattr(activity, 'sport_type', None)
        activity_type = getattr(activity, 'type', None)
        
        # Get activity name
        name = getattr(activity, 'name', 'Unnamed')
        distance_km = getattr(activity, 'distance', 0) / 1000
        
        # Only show rides over 30km
        if distance_km < 30:
            continue
            
        print(f"\nActivity: {name}")
        print(f"  Distance: {distance_km:.1f} km")
        print(f"  sport_type: {sport_type}")
        print(f"  type: {activity_type}")
        
        # Count by type
        if sport_type == 'GravelRide':
            gravel_count += 1
            print(f"  ✓ Correctly identified as GRAVEL")
        elif sport_type == 'Ride':
            road_count += 1
            print(f"  ✓ Correctly identified as ROAD")
        else:
            other_count += 1
            print(f"  ? Other type: {sport_type}")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Road rides: {road_count}")
    print(f"  Gravel rides: {gravel_count}")
    print(f"  Other: {other_count}")
    print("=" * 60)
    
    if gravel_count > 0:
        print("\n✓ SUCCESS: Found gravel rides with sport_type='GravelRide'")
        print("  The fix is working correctly!")
    else:
        print("\n⚠ WARNING: No gravel rides found in recent activities")
        print("  Cannot verify fix without gravel ride data")

if __name__ == '__main__':
    main()

# Made with Bob
