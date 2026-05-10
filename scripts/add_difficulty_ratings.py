#!/usr/bin/env python3
"""
Add difficulty ratings to all routes in route_groups.json
Based on distance and elevation gain:
- Easy: <20mi (<32km) AND <500ft (<152m) elevation
- Moderate: 20-40mi (32-64km) OR 500-1500ft (152-457m) elevation
- Hard: >40mi (>64km) OR >1500ft (>457m) elevation
"""

import json
import sys
from pathlib import Path

def meters_to_miles(meters):
    """Convert meters to miles"""
    return meters / 1609.34

def meters_to_feet(meters):
    """Convert meters to feet"""
    return meters * 3.28084

def calculate_difficulty(distance_m, elevation_m):
    """
    Calculate difficulty rating based on distance and elevation
    
    Args:
        distance_m: Distance in meters
        elevation_m: Elevation gain in meters
    
    Returns:
        str: 'easy', 'moderate', or 'hard'
    """
    distance_mi = meters_to_miles(distance_m)
    elevation_ft = meters_to_feet(elevation_m)
    
    # Hard: >40mi OR >1500ft elevation
    if distance_mi > 40 or elevation_ft > 1500:
        return 'hard'
    
    # Easy: <20mi AND <500ft elevation
    if distance_mi < 20 and elevation_ft < 500:
        return 'easy'
    
    # Everything else is moderate
    return 'moderate'

def add_difficulty_ratings(input_file, output_file=None):
    """
    Add difficulty ratings to all routes in the JSON file
    
    Args:
        input_file: Path to route_groups.json
        output_file: Optional output path (defaults to input_file)
    """
    if output_file is None:
        output_file = input_file
    
    # Load the data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Process each route group
    stats = {'easy': 0, 'moderate': 0, 'hard': 0}
    
    for route_group in data['route_groups']:
        # Get distance and elevation from representative route
        rep_route = route_group.get('representative_route', {})
        distance = rep_route.get('distance', 0)
        elevation = rep_route.get('elevation_gain', 0)
        
        # Calculate difficulty
        difficulty = calculate_difficulty(distance, elevation)
        route_group['difficulty'] = difficulty
        stats[difficulty] += 1
        
        # Also add to representative route
        rep_route['difficulty'] = difficulty
        
        # Add to all individual routes in the group
        for route in route_group.get('routes', []):
            route_distance = route.get('distance', distance)
            route_elevation = route.get('elevation_gain', elevation)
            route['difficulty'] = calculate_difficulty(route_distance, route_elevation)
    
    # Save the updated data
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Print statistics
    total = sum(stats.values())
    print(f"✅ Added difficulty ratings to {total} routes:")
    print(f"   - Easy: {stats['easy']} ({stats['easy']/total*100:.1f}%)")
    print(f"   - Moderate: {stats['moderate']} ({stats['moderate']/total*100:.1f}%)")
    print(f"   - Hard: {stats['hard']} ({stats['hard']/total*100:.1f}%)")
    print(f"\n📝 Updated file: {output_file}")

if __name__ == '__main__':
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    route_file = project_root / 'data' / 'route_groups.json'
    
    if not route_file.exists():
        print(f"❌ Error: {route_file} not found", file=sys.stderr)
        sys.exit(1)
    
    print(f"🚴 Adding difficulty ratings to routes...")
    add_difficulty_ratings(route_file)
    print("✅ Done!")

# Made with Bob
