# Advanced Map Features Documentation

**Issue #234 - Phase 4 of Interactive Maps Restoration Epic**

This document describes the advanced map features added to the Ride Optimizer application, including elevation profiles, route analytics overlays, and map export functionality.

## Overview

The advanced map features enhance the interactive maps across all pages with:

1. **Elevation Profiles** - Visual representation of route elevation changes
2. **Route Analytics Overlays** - Speed heatmaps and effort zone visualization
3. **Map Export** - Export maps and routes in multiple formats (PNG, GPX, GeoJSON, PDF)

## Features

### 1. Elevation Profiles

Elevation profiles provide a visual representation of elevation changes along a route.

#### Features:
- **Interactive Chart**: Hover over the chart to see elevation at specific points
- **Map Integration**: Click on the chart to pan the map to that location
- **Statistics**: Displays elevation gain, loss, max, and min values
- **Responsive Design**: Adapts to mobile and desktop screens

#### Implementation:
- Uses Chart.js 4.x for visualization
- Located in `app/static/js/map-advanced-features.js`
- Styling in `app/static/css/map-advanced-features.css`

#### Usage:
```javascript
MapAdvancedFeatures.initElevationProfile({
    containerId: 'elevation-profile',
    elevationData: [
        { distance: 0, elevation: 100, lat: 40.7128, lng: -74.0060 },
        { distance: 1, elevation: 120, lat: 40.7138, lng: -74.0070 },
        // ... more points
    ],
    routeName: 'My Route',
    mapInstance: leafletMapObject // optional
});
```

#### Pages with Elevation Profiles:
- **Route Detail Page**: Full elevation profile with statistics
- **Commute Page**: Comparison of elevation profiles for multiple routes
- **Planner Page**: Elevation profiles for long ride recommendations

### 2. Route Analytics Overlays

Analytics overlays provide visual insights into route characteristics.

#### Types of Overlays:

##### Speed Heatmap
- **Green**: Fast segments (>25 km/h)
- **Yellow**: Moderate segments (20-25 km/h)
- **Orange**: Slow segments (15-20 km/h)
- **Red**: Very slow segments (<15 km/h)

##### Effort Zones
- **Green**: Easy segments (effort < 0.3)
- **Yellow**: Moderate segments (effort 0.3-0.6)
- **Orange**: Hard segments (effort 0.6-0.8)
- **Red**: Very hard segments (effort > 0.8)

#### Usage:
```javascript
MapAdvancedFeatures.addAnalyticsOverlay({
    mapInstance: leafletMapObject,
    routeData: [
        { lat: 40.7128, lng: -74.0060, speed: 22, effort: 0.4 },
        // ... more points
    ],
    overlayType: 'speed' // or 'effort'
});
```

#### Toggle Visibility:
```javascript
MapAdvancedFeatures.toggleAnalyticsOverlay(mapInstance, true); // show
MapAdvancedFeatures.toggleAnalyticsOverlay(mapInstance, false); // hide
```

### 3. Map Export Functionality

Export maps and routes in multiple formats for offline use or sharing.

#### Supported Formats:

##### PNG Image
- Screenshot of current map view
- Includes all visible layers and overlays
- Uses html2canvas library

##### GPX File
- Standard GPS exchange format
- Compatible with Garmin, Wahoo, and other GPS devices
- Includes elevation data if available

##### GeoJSON
- Geographic data format
- Compatible with GIS applications
- Includes route properties and metadata

##### PDF Document
- Printable map with route statistics
- Includes map image and key metrics
- Uses jsPDF library

#### Usage:
```javascript
// PNG Export
await MapAdvancedFeatures.exportMapAsPNG({
    mapContainerId: 'route-map',
    filename: 'my-route-map.png'
});

// GPX Export
MapAdvancedFeatures.exportRouteAsGPX({
    coordinates: [
        { lat: 40.7128, lng: -74.0060, elevation: 10 },
        // ... more points
    ],
    routeName: 'My Route',
    filename: 'my-route.gpx'
});

// GeoJSON Export
MapAdvancedFeatures.exportRouteAsGeoJSON({
    coordinates: [
        { lat: 40.7128, lng: -74.0060 },
        // ... more points
    ],
    properties: {
        name: 'My Route',
        distance: 10.5,
        elevation: 150
    },
    filename: 'my-route.geojson'
});

// PDF Export
await MapAdvancedFeatures.exportMapAsPDF({
    mapContainerId: 'route-map',
    routeStats: {
        name: 'My Route',
        distance: '10.5 km',
        duration: '45 min',
        elevation: '150 m'
    },
    filename: 'my-route-map.pdf'
});
```

#### Export Button Integration:
```javascript
MapAdvancedFeatures.createExportButton({
    containerId: 'export-button-container',
    exportOptions: {
        mapContainerId: 'route-map',
        coordinates: routeCoordinates,
        routeName: 'My Route',
        filename: 'my-route',
        routeStats: { /* ... */ }
    }
});
```

## Architecture

### File Structure

```
app/
├── static/
│   ├── css/
│   │   └── map-advanced-features.css      # Styles for all features
│   └── js/
│       ├── map-advanced-features.js       # Core functionality
│       ├── map-features-integration.js    # Auto-integration across pages
│       └── route-detail-advanced.js       # Route detail specific logic
├── templates/
│   ├── base.html                          # Loads CDN dependencies
│   ├── routes/
│   │   └── detail.html                    # Elevation profile integration
│   ├── commute/
│   │   └── index.html                     # Commute comparison
│   ├── planner/
│   │   └── index.html                     # Long ride planning
│   └── dashboard/
│       └── index.html                     # Activity overview
└── tests/
    └── test_map_advanced_features.py      # Comprehensive tests
```

### Dependencies

#### CDN Libraries (loaded in base.html):
- **Chart.js 4.4.0**: Elevation profile visualization
- **html2canvas 1.4.1**: PNG export functionality
- **jsPDF 2.5.1**: PDF export functionality

#### Internal Dependencies:
- **Leaflet**: Map rendering (via Folium)
- **Bootstrap 5**: UI components and styling

### Integration Pattern

The `map-features-integration.js` script automatically detects page type and initializes appropriate features:

1. **Page Detection**: Identifies page based on DOM elements
2. **Feature Initialization**: Loads relevant features for that page
3. **Dynamic Enhancement**: Adds export buttons and analytics overlays
4. **Graceful Degradation**: Works even if some features are unavailable

## Mobile Optimization

All features are optimized for mobile devices:

- **Responsive Charts**: Elevation profiles adapt to screen size
- **Touch-Friendly Controls**: Minimum 44x44px touch targets
- **Reduced Height**: Smaller chart heights on mobile (250px vs 300px)
- **Simplified UI**: Progressive disclosure of advanced features

### Media Queries:
```css
@media (max-width: 768px) {
    .elevation-profile-canvas {
        height: 250px;
    }
}

@media (max-width: 320px) {
    .elevation-profile-canvas {
        height: 200px;
    }
}
```

## Accessibility

Features follow WCAG AA guidelines:

- **Keyboard Navigation**: All controls accessible via keyboard
- **ARIA Labels**: Proper labeling for screen readers
- **Color Contrast**: All color combinations meet AA standards
- **Focus Indicators**: Clear focus states for interactive elements

## Performance Considerations

### Optimization Strategies:

1. **Lazy Loading**: Features only initialize when needed
2. **Debouncing**: Chart interactions debounced to prevent lag
3. **Canvas Rendering**: Efficient rendering for large datasets
4. **Memory Management**: Charts destroyed when no longer needed

### Best Practices:

- Limit elevation data points to 100-200 for smooth performance
- Use sample data for preview, full data for export
- Cache generated charts to avoid re-rendering
- Clean up event listeners when components unmount

## Testing

Comprehensive test suite in `tests/test_map_advanced_features.py`:

- **Unit Tests**: Individual feature functionality
- **Integration Tests**: Cross-page feature integration
- **Accessibility Tests**: WCAG compliance
- **Responsive Tests**: Mobile and desktop layouts
- **Error Handling**: Graceful degradation

### Running Tests:
```bash
# Run all advanced features tests
pytest tests/test_map_advanced_features.py -v

# Run specific test class
pytest tests/test_map_advanced_features.py::TestElevationProfiles -v

# Run with coverage
pytest tests/test_map_advanced_features.py --cov=app/static/js --cov-report=html
```

## Troubleshooting

### Common Issues:

#### Elevation Profile Not Displaying
- **Check**: Elevation data is properly formatted
- **Check**: Chart.js is loaded (check browser console)
- **Check**: Container element exists in DOM

#### Export Fails
- **Check**: html2canvas and jsPDF are loaded
- **Check**: Browser allows file downloads
- **Check**: Map container is visible (not display:none)

#### Analytics Overlay Not Showing
- **Check**: Route data includes speed/effort values
- **Check**: Leaflet map instance is accessible
- **Check**: Layer control is not hiding the overlay

### Debug Mode:
```javascript
// Enable debug logging
window.MapAdvancedFeatures.debug = true;
```

## Future Enhancements

Potential improvements for future versions:

1. **3D Elevation Profiles**: Three-dimensional route visualization
2. **Animated Playback**: Replay route with synchronized map/chart
3. **Comparison Mode**: Side-by-side elevation profile comparison
4. **Custom Overlays**: User-defined analytics layers
5. **Real-time Updates**: Live elevation data during rides
6. **Social Sharing**: Direct share to social media platforms

## Related Documentation

- [Interactive Maps Restoration Epic](../plans/v0.11.0/INTERACTIVE_MAPS_RESTORATION_EPIC.md)
- [Map Filters Documentation](./MAP_FILTERS.md)
- [Weather Overlays Documentation](./WEATHER_OVERLAYS.md)

## Support

For issues or questions:
- Create an issue on GitHub
- Check existing issues for similar problems
- Review test suite for usage examples

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-07  
**Author**: Bob (AI Assistant)  
**Issue**: #234 - Advanced Map Features