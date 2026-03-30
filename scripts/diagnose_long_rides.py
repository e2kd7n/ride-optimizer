#!/usr/bin/env python3
"""
Diagnostic script to check why Long Rides tab is empty.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("Long Rides Diagnostic")
print("=" * 60)

# Check if report was generated
report_dir = Path("output/reports")
if not report_dir.exists():
    report_dir = Path("data")

reports = list(report_dir.glob("commute_analysis_*.html"))
if not reports:
    print("❌ No reports found")
    sys.exit(1)

latest_report = max(reports, key=lambda p: p.stat().st_mtime)
print(f"\n📄 Latest report: {latest_report.name}")

# Check if long rides data exists in the report
with open(latest_report, 'r') as f:
    content = f.read()
    
# Check for data indicators
has_stats = 'long_rides_stats' in content and 'total_rides' in content
has_top10 = 'top_10_rides' in content
has_monthly = 'monthly_stats' in content  
has_geojson = 'long_rides_geojson' in content

print(f"\n🔍 Data Check:")
print(f"  Statistics data: {'✅' if has_stats else '❌'}")
print(f"  Top 10 rides: {'✅' if has_top10 else '❌'}")
print(f"  Monthly stats: {'✅' if has_monthly else '❌'}")
print(f"  GeoJSON data: {'✅' if has_geojson else '❌'}")

# Check for the tab content
if '<div class="tab-pane fade" id="longrides"' in content:
    print(f"\n✅ Long Rides tab exists in HTML")
    
    # Check what's in the tab
    start = content.find('<div class="tab-pane fade" id="longrides"')
    end = content.find('</div><!-- End Tab Content -->', start)
    if end == -1:
        end = start + 5000
    tab_content = content[start:end]
    
    has_input_form = 'rideDateTime' in tab_content
    has_recommendation_container = 'recommendationsContainer' in tab_content
    has_placeholder = 'Set your ride time and starting location' in tab_content
    
    print(f"  Input form: {'✅' if has_input_form else '❌'}")
    print(f"  Recommendations container: {'✅' if has_recommendation_container else '❌'}")
    print(f"  Placeholder message: {'✅' if has_placeholder else '❌'}")
    
    # Count conditional blocks
    stats_blocks = tab_content.count('{% if long_rides_stats %}')
    print(f"  Conditional blocks: {stats_blocks}")
    
else:
    print(f"\n❌ Long Rides tab NOT found in HTML")

print(f"\n📊 Conclusion:")
if not (has_stats or has_top10 or has_monthly or has_geojson):
    print("  ⚠️  NO LONG RIDES DATA - You likely don't have any rides > 15km")
    print("  ⚠️  that aren't classified as commutes in your Strava data.")
    print("\n  The tab shows correctly but has no statistics to display.")
    print("  The interactive recommendation system needs an API to work.")
else:
    print("  ✅ Long rides data exists but may not be rendering")
    print("  Check browser console for JavaScript errors")

print("\n" + "=" * 60)

# Made with Bob
