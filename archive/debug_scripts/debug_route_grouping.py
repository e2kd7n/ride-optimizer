#!/usr/bin/env python3
"""
Debug tool to visualize route grouping and similarity scores.

Shows which routes are being grouped together and why, with similarity scores.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import folium
from folium import plugins

from src.location_finder import LocationFinder
from src.route_analyzer import RouteAnalyzer
from src.config import Config
from src.data_fetcher import Activity

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_debug_map(route_groups: List, direction: str, output_path: str):
    """Create a map showing all routes in each group with different colors."""
    
    if not route_groups:
        logger.warning(f"No route groups for {direction}")
        return
    
    # Calculate center point
    all_coords = []
    for group in route_groups:
        for route in group.routes:
            all_coords.extend(route.coordinates)
    
    if not all_coords:
        return
    
    center_lat = sum(c[0] for c in all_coords) / len(all_coords)
    center_lon = sum(c[1] for c in all_coords) / len(all_coords)
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    
    # Color palette for groups
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
              'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
              'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 
              'gray', 'black', 'lightgray']
    
    # Add each group with a different color
    for idx, group in enumerate(route_groups):
        color = colors[idx % len(colors)]
        
        # Add all routes in this group
        for route_idx, route in enumerate(group.routes):
            folium.PolyLine(
                route.coordinates,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Group {idx} - Route {route_idx}<br>"
                      f"Activity: {route.activity_id}<br>"
                      f"Uses: {group.frequency}<br>"
                      f"Distance: {route.distance/1000:.2f}km<br>"
                      f"Date: {route.timestamp[:10]}"
            ).add_to(m)
        
        # Add marker for group representative
        if group.representative_route and group.representative_route.coordinates:
            mid_idx = len(group.representative_route.coordinates) // 2
            mid_lat, mid_lon = group.representative_route.coordinates[mid_idx]
            
            folium.Marker(
                [mid_lat, mid_lon],
                popup=f"<b>Group {idx}</b><br>"
                      f"Uses: {group.frequency}<br>"
                      f"Routes: {len(group.routes)}<br>"
                      f"ID: {group.id}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
    
    # Add legend
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 250px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
    <h4>{direction.replace('_', ' ').title()}</h4>
    <p><b>Total Groups:</b> {len(route_groups)}</p>
    <p><b>Total Routes:</b> {sum(len(g.routes) for g in route_groups)}</p>
    <hr>
    <p style="font-size:12px">Each color represents a route group.<br>
    Click routes/markers for details.</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    m.save(output_path)
    logger.info(f"Saved debug map to {output_path}")


def print_grouping_details(route_groups: List, direction: str):
    """Print detailed information about route grouping."""
    
    print(f"\n{'='*80}")
    print(f"{direction.replace('_', ' ').upper()} - GROUPING DETAILS")
    print(f"{'='*80}")
    print(f"Total Groups: {len(route_groups)}")
    print(f"Total Routes: {sum(len(g.routes) for g in route_groups)}")
    print()
    
    # Sort by frequency
    sorted_groups = sorted(route_groups, key=lambda g: g.frequency, reverse=True)
    
    for idx, group in enumerate(sorted_groups[:20]):  # Show top 20
        print(f"\nGroup {idx + 1}: {group.id}")
        print(f"  Uses: {group.frequency}")
        print(f"  Routes in group: {len(group.routes)}")
        print(f"  Activities:")
        
        for route in group.routes:
            print(f"    - Activity {route.activity_id}: "
                  f"{route.distance/1000:.2f}km, "
                  f"{route.timestamp[:10]}")


def main():
    """Main debug function."""
    
    # Load config
    config = Config()
    
    # Get similarity threshold
    threshold = config.get('route_analysis.similarity_threshold', 0.70)
    print(f"\n{'='*80}")
    print(f"ROUTE GROUPING DEBUG TOOL")
    print(f"{'='*80}")
    print(f"Current similarity threshold: {threshold}")
    print(f"(Lower = more strict grouping, Higher = more lenient grouping)")
    print()
    
    # Load cached activities
    print("Loading cached activities...")
    cache_file = Path('cache/activities_cache.json')
    
    if not cache_file.exists():
        print("No cached activities found. Run: python3 main.py --fetch")
        return
    
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)
    
    activities = [Activity(**a) for a in cache_data.get('activities', [])]
    print(f"Found {len(activities)} cached activities")
    
    # Find locations
    print("\nFinding home and work locations...")
    location_finder = LocationFinder(activities, config)
    home, work = location_finder.find_home_work_locations()
    
    if not home or not work:
        print("Could not determine home and work locations")
        return
    
    print(f"Home: ({home.lat:.4f}, {home.lon:.4f})")
    print(f"Work: ({work.lat:.4f}, {work.lon:.4f})")
    
    # Filter commute activities
    print("\nFiltering commute activities...")
    from src.route_analyzer import is_commute_activity
    commute_activities = [a for a in activities if is_commute_activity(a, home, work, config)]
    
    print(f"Found {len(commute_activities)} commute activities")
    
    # Analyze routes
    print("\nAnalyzing and grouping routes...")
    analyzer = RouteAnalyzer(commute_activities, home, work, config)
    route_groups = analyzer.group_similar_routes()
    
    # Separate by direction
    home_to_work = [g for g in route_groups if g.direction == 'home_to_work']
    work_to_home = [g for g in route_groups if g.direction == 'work_to_home']
    
    # Print details
    print_grouping_details(home_to_work, 'home_to_work')
    print_grouping_details(work_to_home, 'work_to_home')
    
    # Create debug maps
    output_dir = Path('output/debug')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print("Creating debug maps...")
    create_debug_map(home_to_work, 'home_to_work', 
                     str(output_dir / 'debug_home_to_work.html'))
    create_debug_map(work_to_home, 'work_to_home', 
                     str(output_dir / 'debug_work_to_home.html'))
    
    print(f"\n{'='*80}")
    print("DEBUG COMPLETE!")
    print(f"{'='*80}")
    print(f"\nDebug maps saved to:")
    print(f"  - {output_dir / 'debug_home_to_work.html'}")
    print(f"  - {output_dir / 'debug_work_to_home.html'}")
    print(f"\nOpen these files in a browser to see which routes are grouped together.")
    print(f"\nTo adjust grouping:")
    print(f"  - LOWER threshold (e.g., 0.60) = stricter grouping = more groups")
    print(f"  - HIGHER threshold (e.g., 0.80) = looser grouping = fewer groups")
    print(f"\nEdit config/config.yaml -> route_analysis.similarity_threshold")
    print()


if __name__ == '__main__':
    main()

# Made with Bob
