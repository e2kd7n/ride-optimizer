#!/usr/bin/env python3
"""
Integration test for dashboard with overview map.

Tests the full dashboard page rendering with map.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_integration():
    """Test dashboard page with overview map."""
    print("=" * 80)
    print("DASHBOARD INTEGRATION TEST")
    print("=" * 80)
    
    try:
        from app import create_app
        
        print("\n1. Creating Flask app...")
        app = create_app()
        
        print("\n2. Testing dashboard route...")
        with app.test_client() as client:
            response = client.get('/')
            
            print(f"   - Status code: {response.status_code}")
            
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                
                # Check for key dashboard elements
                checks = {
                    'Dashboard title': 'Welcome back' in html,
                    'Status banner': 'Data Freshness' in html,
                    'Quick stats': 'Commute Routes' in html,
                    'Overview map section': 'Activity Overview' in html or 'dashboard-overview-map' in html,
                    'Map container': 'map-container' in html,
                    'Recommendations': 'Next Commute' in html,
                    'Mobile responsive meta': 'viewport' in html,
                    'Bootstrap CSS': 'bootstrap' in html.lower()
                }
                
                print("\n3. Verifying page components...")
                all_passed = True
                for component, present in checks.items():
                    status_icon = "✓" if present else "❌"
                    print(f"   {status_icon} {component}: {'Present' if present else 'Missing'}")
                    if not present:
                        all_passed = False
                
                # Check for map HTML if present
                if 'folium' in html.lower() or 'leaflet' in html.lower():
                    print("\n4. Map verification...")
                    print("   ✓ Map HTML detected in response")
                    
                    map_checks = {
                        'Folium/Leaflet': 'folium' in html.lower() or 'leaflet' in html.lower(),
                        'Map tiles': 'tile' in html.lower(),
                        'Interactive elements': 'marker' in html.lower() or 'polyline' in html.lower()
                    }
                    
                    for check, present in map_checks.items():
                        status_icon = "✓" if present else "⚠"
                        print(f"   {status_icon} {check}: {'Present' if present else 'Not detected'}")
                else:
                    print("\n4. Map verification...")
                    print("   ⚠ Map HTML not detected (may not be generated yet)")
                    print("   Note: Run analysis first if map is missing")
                
                # Save response for manual inspection
                output_file = 'test_dashboard_integration_output.html'
                with open(output_file, 'w') as f:
                    f.write(html)
                print(f"\n5. Dashboard HTML saved to: {output_file}")
                print(f"   Open in browser to verify visually")
                print(f"   Test mobile responsiveness by resizing browser window")
                
                if all_passed:
                    print("\n" + "=" * 80)
                    print("✓ INTEGRATION TEST PASSED")
                    print("=" * 80)
                    return True
                else:
                    print("\n" + "=" * 80)
                    print("⚠ SOME CHECKS FAILED - Review output above")
                    print("=" * 80)
                    return False
            else:
                print(f"   ❌ ERROR: Unexpected status code {response.status_code}")
                return False
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_dashboard_integration()
    sys.exit(0 if success else 1)

# Made with Bob
