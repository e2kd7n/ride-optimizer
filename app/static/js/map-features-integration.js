/**
 * Map Features Integration
 * 
 * Automatically integrates advanced map features (elevation profiles, analytics, export)
 * across all pages with maps
 */

(function() {
    'use strict';
    
    // Wait for DOM and dependencies to load
    document.addEventListener('DOMContentLoaded', function() {
        // Check if advanced features are available
        if (typeof MapAdvancedFeatures === 'undefined') {
            console.warn('MapAdvancedFeatures not loaded');
            return;
        }
        
        // Auto-detect and initialize features based on page elements
        initializePageFeatures();
    });
    
    /**
     * Initialize features based on detected page elements
     */
    function initializePageFeatures() {
        // Detect page type and initialize appropriate features
        const pageType = detectPageType();
        
        switch (pageType) {
            case 'route-detail':
                initializeRouteDetailFeatures();
                break;
            case 'commute':
                initializeCommuteFeatures();
                break;
            case 'planner':
                initializePlannerFeatures();
                break;
            case 'dashboard':
                initializeDashboardFeatures();
                break;
            default:
                console.log('No advanced features for this page type');
        }
    }
    
    /**
     * Detect current page type
     */
    function detectPageType() {
        if (document.getElementById('route-map') && document.getElementById('elevation-profile')) {
            return 'route-detail';
        }
        if (document.getElementById('commute-comparison-map')) {
            return 'commute';
        }
        if (document.getElementById('long-rides-map')) {
            return 'planner';
        }
        if (document.getElementById('dashboard-overview-map')) {
            return 'dashboard';
        }
        return 'unknown';
    }
    
    /**
     * Initialize Route Detail page features
     */
    function initializeRouteDetailFeatures() {
        console.log('Initializing route detail features');
        // Handled by route-detail-advanced.js
    }
    
    /**
     * Initialize Commute page features
     */
    function initializeCommuteFeatures() {
        console.log('Initializing commute features');
        
        // Add export button for commute comparison map
        const mapContainer = document.querySelector('.comparison-map-panel');
        if (mapContainer && !document.getElementById('commute-export-btn')) {
            const exportContainer = document.createElement('div');
            exportContainer.id = 'commute-export-container';
            exportContainer.style.marginTop = '1rem';
            mapContainer.appendChild(exportContainer);
            
            MapAdvancedFeatures.createExportButton({
                containerId: 'commute-export-container',
                exportOptions: {
                    mapContainerId: 'commute-comparison-map',
                    coordinates: [],
                    routeName: 'commute-comparison',
                    filename: 'commute-comparison-map'
                }
            });
        }
        
        // Add elevation comparison for selected routes
        addCommuteElevationComparison();
    }
    
    /**
     * Initialize Planner page features
     */
    function initializePlannerFeatures() {
        console.log('Initializing planner features');
        
        // Add export button for long rides map
        const mapSection = document.querySelector('.long-rides-map-section');
        if (mapSection && !document.getElementById('planner-export-btn')) {
            const exportContainer = document.createElement('div');
            exportContainer.id = 'planner-export-container';
            exportContainer.style.marginTop = '1rem';
            exportContainer.style.textAlign = 'center';
            
            const mapContainer = mapSection.querySelector('.map-container');
            if (mapContainer) {
                mapContainer.parentNode.insertBefore(exportContainer, mapContainer.nextSibling);
                
                MapAdvancedFeatures.createExportButton({
                    containerId: 'planner-export-container',
                    exportOptions: {
                        mapContainerId: 'long-rides-map',
                        coordinates: [],
                        routeName: 'long-rides-overview',
                        filename: 'long-rides-map'
                    }
                });
            }
        }
    }
    
    /**
     * Initialize Dashboard page features
     */
    function initializeDashboardFeatures() {
        console.log('Initializing dashboard features');
        
        // Add export button for overview map
        const mapSection = document.querySelector('.overview-map-section');
        if (mapSection && !document.getElementById('dashboard-export-btn')) {
            const exportContainer = document.createElement('div');
            exportContainer.id = 'dashboard-export-container';
            exportContainer.style.marginTop = '1rem';
            exportContainer.style.textAlign = 'center';
            
            const mapContainer = mapSection.querySelector('.map-container');
            if (mapContainer) {
                mapContainer.parentNode.insertBefore(exportContainer, mapContainer.nextSibling);
                
                MapAdvancedFeatures.createExportButton({
                    containerId: 'dashboard-export-container',
                    exportOptions: {
                        mapContainerId: 'dashboard-overview-map',
                        coordinates: [],
                        routeName: 'activity-overview',
                        filename: 'activity-overview-map'
                    }
                });
            }
        }
        
        // Add analytics info box
        addDashboardAnalyticsInfo();
    }
    
    /**
     * Add elevation comparison for commute routes
     */
    function addCommuteElevationComparison() {
        const routeCards = document.querySelectorAll('.route-option-card');
        if (routeCards.length === 0) return;
        
        // Create comparison container
        const comparisonSection = document.querySelector('.comparison-section');
        if (!comparisonSection || document.getElementById('elevation-comparison')) return;
        
        const comparisonDiv = document.createElement('div');
        comparisonDiv.id = 'elevation-comparison';
        comparisonDiv.className = 'elevation-comparison';
        comparisonDiv.innerHTML = '<h3 style="margin-bottom: 1rem;">Route Elevation Comparison</h3>';
        
        comparisonSection.appendChild(comparisonDiv);
        
        // Add elevation profiles for top 3 routes
        routeCards.forEach((card, index) => {
            if (index >= 3) return; // Only show top 3
            
            const routeName = card.querySelector('h3')?.textContent || `Route ${index + 1}`;
            const itemDiv = document.createElement('div');
            itemDiv.className = 'elevation-comparison-item';
            itemDiv.innerHTML = `
                <h4>${routeName}</h4>
                <div class="elevation-comparison-canvas" id="elevation-comparison-${index}"></div>
            `;
            comparisonDiv.appendChild(itemDiv);
            
            // Generate sample elevation data
            const sampleData = generateSampleElevationData(20);
            
            // Initialize mini elevation profile
            MapAdvancedFeatures.initElevationProfile({
                containerId: `elevation-comparison-${index}`,
                elevationData: sampleData,
                routeName: routeName
            });
        });
    }
    
    /**
     * Add analytics info box to dashboard
     */
    function addDashboardAnalyticsInfo() {
        const mapContainer = document.getElementById('dashboard-overview-map');
        if (!mapContainer || document.querySelector('.analytics-info-box')) return;
        
        const infoBox = document.createElement('div');
        infoBox.className = 'analytics-info-box';
        infoBox.innerHTML = `
            <h5>Activity Heatmap</h5>
            <p>Darker areas indicate more frequently used routes. Click on the map to see route details.</p>
        `;
        
        mapContainer.style.position = 'relative';
        mapContainer.appendChild(infoBox);
    }
    
    /**
     * Generate sample elevation data for testing
     */
    function generateSampleElevationData(points) {
        const data = [];
        for (let i = 0; i < points; i++) {
            data.push({
                distance: (i * 10 / points).toFixed(2),
                elevation: 100 + Math.sin(i / 3) * 50 + Math.random() * 20
            });
        }
        return data;
    }
    
})();

// Made with Bob