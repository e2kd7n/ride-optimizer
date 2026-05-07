/**
 * Route Detail Page - Advanced Features Integration
 * 
 * Initializes elevation profiles and export functionality for route detail pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a route detail page with elevation data
    const elevationContainer = document.getElementById('elevation-profile');
    if (!elevationContainer) return;
    
    // Get route data from page (passed via data attributes or global variable)
    const routeData = window.routeDetailData || {};
    
    if (!routeData.elevationData || routeData.elevationData.length === 0) {
        // Show message if no elevation data available
        elevationContainer.innerHTML = `
            <div class="elevation-profile-error">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Elevation data not available for this route</p>
                <small>Elevation profiles require GPS data with altitude information</small>
            </div>
        `;
        return;
    }
    
    // Initialize elevation profile
    try {
        const chart = MapAdvancedFeatures.initElevationProfile({
            containerId: 'elevation-profile',
            elevationData: routeData.elevationData,
            routeName: routeData.name || 'Route'
        });
        
        // Update elevation stats
        updateElevationStats(routeData.elevationData);
        
    } catch (error) {
        console.error('Failed to initialize elevation profile:', error);
        elevationContainer.innerHTML = `
            <div class="elevation-profile-error">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Failed to load elevation profile</p>
                <small>${error.message}</small>
            </div>
        `;
    }
    
    // Initialize export functionality
    const exportContainer = document.getElementById('map-export-container');
    if (exportContainer && typeof MapAdvancedFeatures !== 'undefined') {
        MapAdvancedFeatures.createExportButton({
            containerId: 'map-export-container',
            exportOptions: {
                mapContainerId: 'route-map',
                coordinates: routeData.coordinates || [],
                routeName: routeData.name || 'route',
                filename: (routeData.name || 'route').replace(/\s+/g, '-').toLowerCase(),
                routeStats: {
                    name: routeData.name,
                    distance: routeData.distance,
                    duration: routeData.duration,
                    elevation: routeData.elevation
                }
            }
        });
    }
});

/**
 * Update elevation statistics display
 */
function updateElevationStats(elevationData) {
    if (!elevationData || elevationData.length === 0) return;
    
    const elevations = elevationData.map(d => d.elevation);
    let gain = 0, loss = 0;
    
    // Calculate gain/loss
    for (let i = 1; i < elevations.length; i++) {
        const diff = elevations[i] - elevations[i-1];
        if (diff > 0) gain += diff;
        else loss += Math.abs(diff);
    }
    
    const max = Math.max(...elevations);
    const min = Math.min(...elevations);
    
    // Update DOM
    const gainEl = document.getElementById('elevation-gain');
    const lossEl = document.getElementById('elevation-loss');
    const maxEl = document.getElementById('elevation-max');
    const minEl = document.getElementById('elevation-min');
    
    if (gainEl) gainEl.textContent = `${gain.toFixed(0)}m`;
    if (lossEl) lossEl.textContent = `${loss.toFixed(0)}m`;
    if (maxEl) maxEl.textContent = `${max.toFixed(0)}m`;
    if (minEl) minEl.textContent = `${min.toFixed(0)}m`;
}

// Made with Bob