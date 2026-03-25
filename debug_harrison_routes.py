#!/usr/bin/env python3
"""
Debug script to analyze Harrison St routes and identify "Ride to Work+" patterns.

Examines routes 135, 131, 134, 123, 144, 137, 140, 146, 149, 139 to understand
why they're being treated as separate routes.
"""

import json
from pathlib import Path
from typing import List, Dict
import re

def load_activities():
    """Load cached activities."""
    cache_file = Path('data/cache/activities.json')
    if not cache_file.exists():
        print(f"No cache found at {cache_file}")
        print("Run: python3 main.py --fetch")
        return []
    
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    activities = cache_data.get('activities', [])
    print(f"Loaded {len(activities)} activities from cache")
    return activities


def analyze_route_names(activities: List[Dict]):
    """Analyze activity names for patterns."""
    
    # Patterns to look for
    patterns = {
        'ride_to_work_plus': r'ride to work\+|rtw\+|commute\+',
        'morning_ride': r'morning ride',
        'long_way': r'long way|scenic route',
        'extended': r'extended|extra',
    }
    
    print("\n" + "="*80)
    print("ACTIVITY NAME ANALYSIS")
    print("="*80)
    
    # Group by pattern
    categorized = {pattern: [] for pattern in patterns.keys()}
    categorized['other'] = []
    
    for activity in activities:
        name = activity.get('name', '').lower()
        activity_id = activity.get('id')
        distance_km = activity.get('distance', 0) / 1000
        
        matched = False
        for pattern_name, pattern_regex in patterns.items():
            if re.search(pattern_regex, name, re.IGNORECASE):
                categorized[pattern_name].append({
                    'id': activity_id,
                    'name': activity.get('name'),
                    'distance_km': distance_km,
                    'date': activity.get('start_date', '')[:10]
                })
                matched = True
                break
        
        if not matched and activity.get('commute'):
            categorized['other'].append({
                'id': activity_id,
                'name': activity.get('name'),
                'distance_km': distance_km,
                'date': activity.get('start_date', '')[:10]
            })
    
    # Print results
    for category, items in categorized.items():
        if items:
            print(f"\n{category.upper().replace('_', ' ')} ({len(items)} activities):")
            print("-" * 80)
            for item in sorted(items, key=lambda x: x['distance_km'], reverse=True)[:10]:
                print(f"  {item['id']:12} | {item['distance_km']:6.2f}km | {item['date']} | {item['name']}")


def find_harrison_routes():
    """Find activities that might be the Harrison St routes."""
    activities = load_activities()
    
    if not activities:
        return
    
    print("\n" + "="*80)
    print("SEARCHING FOR HARRISON ST ROUTES")
    print("="*80)
    print("\nLooking for activities with 'harrison' in name or description...")
    
    harrison_activities = []
    for activity in activities:
        name = activity.get('name', '').lower()
        if 'harrison' in name:
            harrison_activities.append({
                'id': activity.get('id'),
                'name': activity.get('name'),
                'distance_km': activity.get('distance', 0) / 1000,
                'date': activity.get('start_date', '')[:10],
                'commute': activity.get('commute', False)
            })
    
    if harrison_activities:
        print(f"\nFound {len(harrison_activities)} activities mentioning Harrison:")
        for act in harrison_activities:
            print(f"  {act['id']:12} | {act['distance_km']:6.2f}km | {act['date']} | {act['name']}")
    else:
        print("\nNo activities found with 'harrison' in name")
    
    # Look for longer commutes (potential "ride to work+" routes)
    print("\n" + "="*80)
    print("LONGER COMMUTE ACTIVITIES (>15km)")
    print("="*80)
    
    long_commutes = []
    for activity in activities:
        if activity.get('commute') and activity.get('distance', 0) / 1000 > 15:
            long_commutes.append({
                'id': activity.get('id'),
                'name': activity.get('name'),
                'distance_km': activity.get('distance', 0) / 1000,
                'date': activity.get('start_date', '')[:10]
            })
    
    if long_commutes:
        print(f"\nFound {len(long_commutes)} long commute activities:")
        for act in sorted(long_commutes, key=lambda x: x['distance_km'], reverse=True)[:20]:
            print(f"  {act['id']:12} | {act['distance_km']:6.2f}km | {act['date']} | {act['name']}")


def suggest_filters():
    """Suggest filtering strategies."""
    print("\n" + "="*80)
    print("SUGGESTED FILTERING STRATEGIES")
    print("="*80)
    
    print("""
1. DISTANCE THRESHOLD
   - Exclude commutes longer than X km (e.g., 15km)
   - Typical commute: 5-12km
   - "Ride to Work+": 15-40km

2. NAME PATTERN MATCHING
   - Exclude activities with keywords:
     * "ride to work+"
     * "rtw+"
     * "long way"
     * "scenic"
     * "extended"
     * "morning ride" (if >15km)

3. ROUTE SIMILARITY WITH DISTANCE FILTER
   - Group routes by similarity
   - Within each group, exclude outliers >2x median distance
   
4. HYBRID APPROACH (RECOMMENDED)
   - Set max commute distance (e.g., 15km)
   - Exclude name patterns
   - Keep similarity grouping for remaining routes
    """)


def main():
    """Main analysis function."""
    activities = load_activities()
    
    if not activities:
        return
    
    print(f"\nLoaded {len(activities)} activities from cache")
    
    # Analyze activity names
    analyze_route_names(activities)
    
    # Find Harrison routes
    find_harrison_routes()
    
    # Suggest filters
    suggest_filters()
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
1. Review the activity names above
2. Identify common patterns in "Ride to Work+" activities
3. Add filtering logic to route_analyzer.py
4. Re-run analysis to see improved grouping
    """)


if __name__ == '__main__':
    main()

# Made with Bob
