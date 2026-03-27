#!/usr/bin/env python3
"""
Debug script for investigating route matching issues.

Helps diagnose why specific routes aren't being grouped together.
"""

import sys
import json
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.route_analyzer import RouteAnalyzer, Route
from src.config import load_config


def load_cached_activities():
    """Load activities from cache."""
    cache_file = Path('data/cache/activities.json')
    if not cache_file.exists():
        print("❌ No cached activities found. Run: python main.py --fetch")
        return None
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
        return data.get('activities', [])


def find_route_by_activity_id(routes, activity_id):
    """Find a route by its activity ID."""
    for route in routes:
        if route.activity_id == activity_id:
            return route
    return None


def analyze_route_pair(analyzer, route1, route2):
    """Analyze why two routes might not be matching."""
    print(f"\n{'='*70}")
    print(f"ROUTE PAIR ANALYSIS")
    print(f"{'='*70}\n")
    
    print(f"Route 1: Activity {route1.activity_id}")
    print(f"  Direction: {route1.direction}")
    print(f"  Distance: {route1.distance:.1f}m")
    print(f"  Duration: {route1.duration}s ({route1.duration/60:.1f} min)")
    print(f"  Coordinates: {len(route1.coordinates)} points")
    print(f"  Start: {route1.coordinates[0]}")
    print(f"  End: {route1.coordinates[-1]}")
    print()
    
    print(f"Route 2: Activity {route2.activity_id}")
    print(f"  Direction: {route2.direction}")
    print(f"  Distance: {route2.distance:.1f}m")
    print(f"  Duration: {route2.duration}s ({route2.duration/60:.1f} min)")
    print(f"  Coordinates: {len(route2.coordinates)} points")
    print(f"  Start: {route2.coordinates[0]}")
    print(f"  End: {route2.coordinates[-1]}")
    print()
    
    # Check if same direction
    if route1.direction != route2.direction:
        print("❌ DIFFERENT DIRECTIONS - Routes cannot match")
        return
    
    # Calculate distance difference
    dist_diff = abs(route1.distance - route2.distance)
    dist_diff_pct = (dist_diff / min(route1.distance, route2.distance)) * 100
    print(f"Distance difference: {dist_diff:.1f}m ({dist_diff_pct:.1f}%)")
    
    # Calculate duration difference
    dur_diff = abs(route1.duration - route2.duration)
    dur_diff_pct = (dur_diff / min(route1.duration, route2.duration)) * 100
    print(f"Duration difference: {dur_diff}s ({dur_diff_pct:.1f}%)")
    print()
    
    # Calculate similarity
    print("Calculating route similarity...")
    similarity = analyzer.calculate_route_similarity(route1, route2)
    threshold = analyzer.similarity_threshold
    
    print(f"\n{'='*70}")
    print(f"SIMILARITY RESULTS")
    print(f"{'='*70}\n")
    print(f"Similarity score: {similarity:.4f}")
    print(f"Threshold: {threshold:.4f}")
    print(f"Match: {'✅ YES' if similarity >= threshold else '❌ NO'}")
    
    if similarity < threshold:
        gap = threshold - similarity
        print(f"\nGap to threshold: {gap:.4f} ({gap/threshold*100:.1f}% below)")
        print("\nPossible reasons for mismatch:")
        if dist_diff_pct > 15:
            print(f"  • Distance difference is high ({dist_diff_pct:.1f}%)")
        if dur_diff_pct > 20:
            print(f"  • Duration difference is high ({dur_diff_pct:.1f}%)")
        print("  • Routes may take different paths")
        print("  • GPS accuracy issues")
        print("  • One route may have detours or stops")
    
    print(f"\n{'='*70}\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Debug route matching issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two specific routes
  python scripts/debug_route_matching.py --routes 78 62
  
  # Show all routes for a direction
  python scripts/debug_route_matching.py --list to_work
        """
    )
    
    parser.add_argument('--routes', nargs=2, type=int, metavar=('ID1', 'ID2'),
                       help='Compare two routes by activity ID')
    parser.add_argument('--list', choices=['to_work', 'to_home', 'both'],
                       help='List all routes for a direction')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    if not args.routes and not args.list:
        parser.print_help()
        return
    
    # Load config
    config = load_config(args.config)
    
    # Load activities
    print("Loading cached activities...")
    activities_data = load_cached_activities()
    if not activities_data:
        return
    
    print(f"Loaded {len(activities_data)} activities")
    
    # Note: This script requires home/work locations which would need to be
    # loaded from a previous analysis or specified manually
    print("\n⚠️  Note: This script requires home and work locations.")
    print("    Run a full analysis first: python main.py --analyze")
    print("    Then check the route groups cache for route information.")
    
    # For now, just show what we can from the cache
    groups_cache = Path('cache/route_groups_cache.json')
    if groups_cache.exists():
        with open(groups_cache, 'r') as f:
            cache_data = json.load(f)
            print(f"\n✅ Found route groups cache with {len(cache_data.get('groups', []))} groups")
            print(f"   Similarity threshold: {cache_data.get('similarity_threshold', 'N/A')}")
            print(f"   Algorithm: {cache_data.get('algorithm', 'N/A')}")
    else:
        print("\n❌ No route groups cache found")
        print("   Run: python main.py --analyze")


if __name__ == '__main__':
    main()

# Made with Bob
