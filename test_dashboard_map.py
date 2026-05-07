#!/usr/bin/env python3
"""
Test script for dashboard overview map functionality.

Tests:
1. Map generation with route groups and locations
2. Heatmap layer rendering
3. Top routes display
4. Home/work markers
5. Error handling with missing data
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from app.services.analysis_service import AnalysisService

def test_dashboard_map():
    """Test dashboard overview map generation."""
    print("=" * 80)
    print("DASHBOARD OVERVIEW MAP TEST")
    print("=" * 80)
    
    # Initialize config and service
    config = Config('config/config.yaml')
    analysis_service = AnalysisService(config)
    
    # Load cached data
    print("\n1. Loading cached analysis data...")
    analysis_service._load_from_cache()
    
    # Check data availability
    print("\n2. Checking data availability...")
    status = analysis_service.get_analysis_status()
    print(f"   - Has data: {status['has_data']}")
    print(f"   - Route groups: {status['route_groups_count']}")
    print(f"   - Activities: {status['activities_count']}")
    print(f"   - Last analysis: {status['last_analysis']}")
    
    if not status['has_data']:
        print("\n❌ ERROR: No analysis data available")
        print("   Run analysis first: python main.py --force-reanalysis")
        return False
    
    # Generate dashboard map (this will extract locations if needed)
    print("\n3. Generating dashboard overview map...")
    try:
        map_html = analysis_service.generate_dashboard_overview_map()
        
        if map_html:
            print(f"   ✓ Map generated successfully")
            print(f"   - HTML length: {len(map_html)} characters")
            
            # Check for key components
            checks = {
                'Folium map': 'folium-map' in map_html,
                'Heatmap layer': 'HeatMap' in map_html or 'heat' in map_html.lower(),
                'Route polylines': 'PolyLine' in map_html or 'polyline' in map_html.lower(),
                'Home marker': 'Home' in map_html,
                'Work marker': 'Work' in map_html,
                'Layer control': 'LayerControl' in map_html or 'layer' in map_html.lower()
            }
            
            # Check locations after map generation
            print("\n4. Verifying locations were extracted...")
            home, work = analysis_service.get_locations()
            if home and work:
                print(f"   ✓ Home: {home.name} ({home.lat:.4f}, {home.lon:.4f})")
                print(f"   ✓ Work: {work.name} ({work.lat:.4f}, {work.lon:.4f})")
            else:
                print("   ⚠ Locations not available (may still work)")
            
            print("\n5. Verifying map components...")
            all_passed = True
            for component, present in checks.items():
                status_icon = "✓" if present else "❌"
                print(f"   {status_icon} {component}: {'Present' if present else 'Missing'}")
                if not present:
                    all_passed = False
            
            # Save map to file for manual inspection
            output_file = 'test_dashboard_map_output.html'
            with open(output_file, 'w') as f:
                f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Overview Map Test</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
        }}
        h1 {{
            color: #2c3e50;
        }}
        .map-container {{
            width: 100%;
            height: 500px;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            overflow: hidden;
        }}
        @media (max-width: 768px) {{
            .map-container {{
                height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <h1>🗺️ Dashboard Overview Map Test</h1>
    <p>Generated: {status['last_analysis']}</p>
    <p>Route Groups: {status['route_groups_count']} | Activities: {status['activities_count']}</p>
    <div class="map-container">
        {map_html}
    </div>
</body>
</html>
""")
            print(f"\n6. Map saved to: {output_file}")
            print(f"   Open in browser to verify visually")
            
            if all_passed:
                print("\n" + "=" * 80)
                print("✓ ALL TESTS PASSED")
                print("=" * 80)
                return True
            else:
                print("\n" + "=" * 80)
                print("⚠ SOME CHECKS FAILED - Review output above")
                print("=" * 80)
                return False
        else:
            print("   ❌ ERROR: Map generation returned None")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_dashboard_map()
    sys.exit(0 if success else 1)

# Made with Bob
