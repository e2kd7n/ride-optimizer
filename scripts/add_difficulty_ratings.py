#!/usr/bin/env python3
"""
Add difficulty ratings to all routes in route_groups.json
Based on weighted scoring algorithm from PRODUCTION_READINESS_ROADMAP.md:
- Distance (30% weight)
- Elevation gain (40% weight)
- Average grade (30% weight)

Difficulty levels:
- Easy: <25 score
- Moderate: 25-50 score
- Hard: 50-75 score
- Very Hard: >75 score
"""

import json
import sys
from pathlib import Path

def calculate_difficulty(distance_m, elevation_m):
    """
    Calculate difficulty rating based on weighted scoring algorithm
    
    Args:
        distance_m: Distance in meters
        elevation_m: Elevation gain in meters
    
    Returns:
        str: 'Easy', 'Moderate', 'Hard', or 'Very Hard'
    """
    distance_km = distance_m / 1000
    
    # Normalize metrics (0-100 scale)
    # Distance: 50km = max (100 score)
    distance_score = min(distance_km / 50 * 100, 100)
    
    # Elevation: 500m = max (100 score)
    elevation_score = min(elevation_m / 500 * 100, 100)
    
    # Average grade: Calculate percentage grade
    # Grade score: Higher grade = higher difficulty
    if distance_km > 0:
        grade_percent = (elevation_m / (distance_km * 1000)) * 100
        grade_score = min(grade_percent * 10, 100)  # 10% grade = 100 score
    else:
        grade_score = 0
    
    # Weighted average (distance: 30%, elevation: 40%, grade: 30%)
    total_score = (distance_score * 0.3 + elevation_score * 0.4 + grade_score * 0.3)
    
    # Determine difficulty level
    if total_score < 25:
        return 'Easy'
    elif total_score < 50:
        return 'Moderate'
    elif total_score < 75:
        return 'Hard'
    else:
        return 'Very Hard'

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
    stats = {'Easy': 0, 'Moderate': 0, 'Hard': 0, 'Very Hard': 0}
    
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
    print(f"   - Easy: {stats['Easy']} ({stats['Easy']/total*100:.1f}%)")
    print(f"   - Moderate: {stats['Moderate']} ({stats['Moderate']/total*100:.1f}%)")
    print(f"   - Hard: {stats['Hard']} ({stats['Hard']/total*100:.1f}%)")
    print(f"   - Very Hard: {stats['Very Hard']} ({stats['Very Hard']/total*100:.1f}%)")
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
