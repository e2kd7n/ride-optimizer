#!/usr/bin/env python3
"""Debug script to check sport_type extraction from Strava API."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stravalib.client import Client
from src.config import Config

def main():
    """Test sport_type extraction."""
    config = Config()
    
    # Initialize Strava client
    client = Client(access_token=config.get('strava', {}).get('access_token'))
    
    # Fetch a single activity (Melting Mann)
    activity_id = 17891459939
    print(f"Fetching activity {activity_id}...")
    
    activity = client.get_activity(activity_id)
    
    print("\n" + "="*60)
    print("ACTIVITY OBJECT INSPECTION")
    print("="*60)
    
    print(f"\nActivity name: {activity.name}")
    print(f"Activity type: {activity.type}")
    print(f"Activity type (type): {type(activity.type)}")
    print(f"Activity type (str): {str(activity.type)}")
    
    if hasattr(activity, 'sport_type'):
        print(f"\n✓ Has sport_type attribute")
        print(f"  sport_type: {activity.sport_type}")
        print(f"  sport_type (type): {type(activity.sport_type)}")
        print(f"  sport_type (str): {str(activity.sport_type)}")
        print(f"  sport_type (repr): {repr(activity.sport_type)}")
        
        if hasattr(activity.sport_type, 'root'):
            print(f"\n✓ sport_type has 'root' attribute")
            print(f"  sport_type.root: {activity.sport_type.root}")
            print(f"  sport_type.root (type): {type(activity.sport_type.root)}")
            print(f"  sport_type.root (str): {str(activity.sport_type.root)}")
        else:
            print(f"\n✗ sport_type does NOT have 'root' attribute")
            print(f"  Available attributes: {dir(activity.sport_type)}")
    else:
        print(f"\n✗ Does NOT have sport_type attribute")
    
    print("\n" + "="*60)
    print("RECOMMENDED FIX")
    print("="*60)
    
    if hasattr(activity, 'sport_type') and activity.sport_type:
        if hasattr(activity.sport_type, 'root'):
            print(f"Use: str(activity.sport_type.root) = '{str(activity.sport_type.root)}'")
        else:
            print(f"Use: str(activity.sport_type) = '{str(activity.sport_type)}'")

if __name__ == '__main__':
    main()

# Made with Bob
