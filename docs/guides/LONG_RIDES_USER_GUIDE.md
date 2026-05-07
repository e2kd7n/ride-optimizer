# Long Rides Feature - User Guide

**Version:** 2.4.0+  
**Last Updated:** 2026-05-07

---

## Overview

The Long Rides feature analyzes your non-commute cycling activities to help you discover, track, and plan recreational rides. It provides comprehensive statistics, visualizations, and recommendations for your longer cycling adventures.

## What is a "Long Ride"?

A long ride is defined as:
- **Distance:** Greater than 15 km (configurable)
- **Type:** Real-world cycling activities (excludes virtual/indoor rides)
- **GPS Data:** Must have valid GPS coordinates
- **Not a Commute:** Automatically excludes identified commute routes

### Virtual Ride Exclusion

The system automatically filters out virtual/indoor rides using multiple detection methods:
- Activity type (e.g., "VirtualRide")
- Activity name keywords (Zwift, Trainer, Indoor, Rouvy,Sufferfest, Peloton)
- Missing GPS data (common in virtual rides)

## Features

### 1. Statistics Dashboard

**Seven Key Metrics:**
- **Total Long Rides:** Count of all qualifying rides
- **Total Distance:** Cumulative distance of all long rides
- **Average Distance:** Mean distance per ride
- **Longest Ride:** Your personal distance record
- **Total Elevation Gain:** Cumulative climbing across all rides
- **Average Speed:** Mean speed across all long rides
- **Total Time:** Cumulative duration of all rides

### 2. Top 10 Longest Rides Table

**Displays:**
- Ride name (linked to Strava activity)
- Distance (km/miles based on your preference)
- Duration (hours:minutes)
- Average speed
- Elevation gain
- Date of the ride
- Route type (Loop or Point-to-Point)

**Features:**
- Direct links to Strava activities
- Sortable columns
- Mobile-responsive design

### 3. Monthly Statistics Chart

**Visualizes:**
- Number of long rides per month
- Total distance per month
- Interactive Chart.js visualization
- Hover tooltips with detailed data

### 4. Interactive Route Map

**Map Features:**
- All long rides displayed as colored routes
- Color coding by distance:
  - **Green:** Shorter long rides (15-30 km)
  - **Yellow:** Medium rides (30-50 km)
  - **Red:** Epic rides (50+ km)
- Route filtering options:
  - Show All Routes
  - Loops Only (start/end within 500m)
  - Point-to-Point Only
- Click routes for detailed information
- Zoom and pan functionality
- Mobile-friendly controls

## How to Access

1. **Generate Report:** Run the analyzer with your Strava data
2. **Open HTML Report:** Open the generated `report.html` file
3. **Navigate to Long Rides Tab:** Click the "Long Rides" tab in the report

## Configuration Options

### Distance Threshold

Customize the minimum distance for long rides in your `config.yaml`:

```yaml
long_rides:
  min_distance_km: 15  # Default: 15 km
```

**Common Settings:**
- **15 km:** Default, good for most cyclists
- **20 km:** For more experienced cyclists
- **25 km:** For serious recreational riders
- **10 km:** For urban cyclists or beginners

### Route Naming

Configure how routes are named in the system:

```yaml
route_naming:
  sample_points: 10  # Points along route for naming
  max_name_length: 50  # Maximum characters in route name
```

## Understanding Route Grouping

### Name-Based Grouping

Routes are primarily grouped by their Strava activity names:
- **Same Name:** Activities with identical names are grouped together
- **Similar Names:** Routes with similar names may be consolidated
- **Generic Names:** Activities named "Morning Ride", "Afternoon Ride", etc. are treated as unique

### Route Similarity Detection

The system uses advanced algorithms to identify similar routes:
- **Fréchet Distance:** Measures route shape similarity
- **Hausdorff Distance:** Measures maximum deviation between routes
- **Threshold:** Routes within 200m similarity are considered the same

### Loop Detection

Routes are classified as loops if:
- Start and end points are within 500 meters
- Helps distinguish between out-and-back vs. circular routes

## Tips for Better Analysis

### 1. Name Your Rides Consistently

**Good Examples:**
- "Lake Loop"
- "Mountain Climb - Bear Creek"
- "Coastal Route to Lighthouse"

**Avoid:**
- Generic names like "Morning Ride"
- Inconsistent naming for the same route
- Very long, descriptive names

### 2. Ensure GPS Accuracy

- Start GPS recording before you begin riding
- Keep your device charged throughout the ride
- Avoid starting/stopping in areas with poor GPS signal

### 3. Regular Data Updates

- Sync your Strava data regularly
- Re-run the analyzer after significant new rides
- Update your configuration as your riding habits change

## Troubleshooting

### No Long Rides Showing

**Possible Causes:**
1. **Distance Filter:** Your rides may be shorter than the 15km threshold
2. **Virtual Rides:** System may be filtering out indoor rides
3. **Missing GPS:** Rides without GPS data are excluded
4. **Commute Classification:** Rides may be classified as commutes

**Solutions:**
1. Lower the `min_distance_km` setting
2. Check activity types and names for virtual ride keywords
3. Verify GPS data exists in Strava
4. Review commute detection settings

### Incorrect Route Grouping

**Possible Causes:**
1. **Inconsistent Naming:** Same route with different names
2. **GPS Drift:** Poor GPS accuracy causing route variations
3. **Route Variations:** Slightly different paths treated as separate routes

**Solutions:**
1. Rename activities in Strava for consistency
2. Adjust similarity thresholds in configuration
3. Manually group routes by using consistent naming

### Map Not Loading

**Possible Causes:**
1. **Internet Connection:** Maps require internet for tiles
2. **Browser Compatibility:** Older browsers may not support features
3. **JavaScript Disabled:** Maps require JavaScript

**Solutions:**
1. Check internet connection
2. Use a modern browser (Chrome, Firefox, Safari, Edge)
3. Enable JavaScript in browser settings

### Performance Issues

**Possible Causes:**
1. **Large Dataset:** Many activities can slow processing
2. **Complex Routes:** Routes with many GPS points
3. **Multiple Maps:** Interactive map with many routes

**Solutions:**
1. Increase distance threshold to reduce dataset size
2. Use date filters to analyze specific time periods
3. Close other browser tabs to free memory

## Advanced Features

### Route Recommendations

The system can provide route recommendations based on:
- **Weather Conditions:** Wind direction and speed
- **Location Preferences:** Routes near clicked map locations
- **Historical Performance:** Your past performance on similar routes

### Weather Integration

When weather data is available:
- **Wind Analysis:** Optimal direction for route completion
- **Precipitation Risk:** Weather-based ride timing
- **Temperature Considerations:** Seasonal route preferences

### Export Options

**Available Formats:**
- **HTML Report:** Interactive web-based report
- **JSON Data:** Raw data for custom analysis
- **GPX Files:** Route data for GPS devices

## Privacy and Data

### Local Processing

- All analysis happens on your local machine
- No data is sent to external servers (except Strava API)
- Your activity data remains private

### Strava Integration

- Uses official Strava API with your permission
- Only accesses activities you've granted permission for
- Respects Strava privacy settings

### Data Storage

- Activity data cached locally for performance
- Cache files stored in `cache/` directory
- Can be deleted safely (will re-download from Strava)

## Getting Help

### Documentation

- **Technical Spec:** `docs/TECHNICAL_SPEC.md`
- **API Documentation:** `docs/api/LONG_RIDES_API.md`
- **Configuration Guide:** `config/config.yaml` comments

### Support

- **GitHub Issues:** Report bugs or request features
- **Configuration Help:** Check example configurations
- **Community:** Share tips and configurations with other users

---

## Version History

### v2.4.0 (March 2026)
- Initial Long Rides feature release
- Statistics dashboard with 7 key metrics
- Top 10 longest rides table
- Monthly statistics chart
- Interactive route map with filtering
- Virtual ride exclusion system

### Future Enhancements
- Pagination for large datasets
- Preview maps in table rows
- Distance and time filters
- Route comparison features
- Performance analytics