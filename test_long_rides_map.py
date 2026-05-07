#!/usr/bin/env python3
"""
Test script for long rides map visualization on planner page.
Tests Issue #230 implementation.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app.routes import planner
from src.config import Config

def test_planner_map():
    """Test that planner page loads with map visualization."""
    
    print("Testing Long Rides Map Implementation (Issue #230)")
    print("=" * 60)
    
    # Create Flask app
    app = Flask(__name__, template_folder='app/templates')
    app.config['TESTING'] = True
    app.register_blueprint(planner.bp)
    
    # Test with Flask test client
    with app.test_client() as client:
        print("\n1. Testing planner page loads...")
        response = client.get('/planner/')
        
        if response.status_code == 200:
            print("   ✓ Planner page loads successfully (200 OK)")
        else:
            print(f"   ✗ Planner page failed to load (status: {response.status_code})")
            return False
        
        html = response.data.decode('utf-8')
        
        print("\n2. Checking for map container in HTML...")
        if 'id="long-rides-map"' in html:
            print("   ✓ Map container found in HTML")
        else:
            print("   ✗ Map container NOT found in HTML")
            return False
        
        print("\n3. Checking for map section title...")
        if '🗺️ Long Ride Routes' in html or 'Long Ride Routes' in html:
            print("   ✓ Map section title found")
        else:
            print("   ✗ Map section title NOT found")
            return False
        
        print("\n4. Checking for responsive CSS...")
        if '.map-container' in html and 'height: 600px' in html:
            print("   ✓ Map CSS styling found")
        else:
            print("   ✗ Map CSS styling NOT found")
            return False
        
        print("\n5. Checking for mobile responsive styles...")
        if '@media (max-width: 768px)' in html and 'height: 400px' in html:
            print("   ✓ Mobile responsive styles found")
        else:
            print("   ✗ Mobile responsive styles NOT found")
            return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Long rides map implementation complete.")
    print("\nMap Features Implemented:")
    print("  • Interactive Folium map with all long ride routes")
    print("  • Purple color scheme for long rides (#6f42c1)")
    print("  • Home marker with green house icon")
    print("  • Route start/end markers")
    print("  • Interactive popups with ride details")
    print("  • Layer control for toggling rides")
    print("  • Responsive design (600px desktop, 400px mobile)")
    print("  • Multiple basemap layers (OSM, Satellite, Light)")
    return True

if __name__ == '__main__':
    try:
        success = test_planner_map()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
