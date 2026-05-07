/**
 * Map Renderer - Client-side Leaflet.js map rendering for Smart Static architecture
 * 
 * Fetches map data from /api/maps/<page_type> and renders interactive maps
 * using Leaflet.js with layer controls, markers, and route polylines.
 */

class MapRenderer {
    constructor(containerId, pageType, options = {}) {
        this.containerId = containerId;
        this.pageType = pageType;
        this.options = options;
        this.map = null;
        this.layers = {};
        this.layerControl = null;
    }

    /**
     * Initialize and render the map
     */
    async render() {
        try {
            // Fetch map data from API
            const mapData = await this.fetchMapData();
            
            if (mapData.status !== 'success') {
                this.showError(mapData.message || 'Failed to load map data');
                return;
            }

            // Create base map
            this.createBaseMap(mapData.center, mapData.zoom);

            // Add tile layers
            this.addTileLayers();

            // Add routes (if not using layers)
            if (mapData.routes && mapData.routes.length > 0) {
                this.addRoutes(mapData.routes);
            }

            // Add markers (if not using layers)
            if (mapData.markers && mapData.markers.length > 0) {
                this.addMarkers(mapData.markers);
            }

            // Add feature layers (for multi-route maps)
            if (mapData.layers && mapData.layers.length > 0) {
                this.addFeatureLayers(mapData.layers);
            }

            // Add layer control if we have layers
            if (Object.keys(this.layers).length > 1) {
                this.layerControl = L.control.layers(null, this.layers, {
                    collapsed: false
                }).addTo(this.map);
            }

            console.log(`Map rendered successfully for ${this.pageType}`);
        } catch (error) {
            console.error('Error rendering map:', error);
            this.showError('Failed to load map. Please try again later.');
        }
    }

    /**
     * Fetch map data from API
     */
    async fetchMapData() {
        const url = this.buildApiUrl();
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    /**
     * Build API URL with query parameters
     */
    buildApiUrl() {
        let url = `/api/maps/${this.pageType}`;
        
        // Add query parameters if provided
        const params = new URLSearchParams();
        if (this.options.routeId) {
            params.append('route_id', this.options.routeId);
        }
        if (this.options.routeType) {
            params.append('route_type', this.options.routeType);
        }
        
        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }
        
        return url;
    }

    /**
     * Create base Leaflet map
     */
    createBaseMap(center, zoom) {
        this.map = L.map(this.containerId).setView(center, zoom);
        
        // Set max bounds to prevent excessive panning
        const bounds = L.latLngBounds(
            L.latLng(center[0] - 0.5, center[1] - 0.5),
            L.latLng(center[0] + 0.5, center[1] + 0.5)
        );
        this.map.setMaxBounds(bounds);
    }

    /**
     * Add tile layers (base maps)
     */
    addTileLayers() {
        // OpenStreetMap (default)
        const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Satellite imagery
        const satelliteLayer = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: 'Tiles © Esri',
                maxZoom: 19
            }
        );

        // Light theme
        const lightLayer = L.tileLayer(
            'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {
                attribution: '© OpenStreetMap, © CARTO',
                maxZoom: 19
            }
        );

        // Store base layers for layer control
        this.layers['OpenStreetMap'] = osmLayer;
        this.layers['Satellite'] = satelliteLayer;
        this.layers['Light'] = lightLayer;
    }

    /**
     * Add routes to map
     */
    addRoutes(routes) {
        routes.forEach(route => {
            const polyline = L.polyline(route.coordinates, {
                color: route.color || '#007bff',
                weight: route.weight || 4,
                opacity: route.opacity || 0.8
            });

            // Add popup if provided
            if (route.popup_html) {
                polyline.bindPopup(route.popup_html, { maxWidth: 320 });
            }

            // Add tooltip if provided
            if (route.tooltip) {
                polyline.bindTooltip(route.tooltip);
            }

            polyline.addTo(this.map);
        });
    }

    /**
     * Add markers to map
     */
    addMarkers(markers) {
        markers.forEach(marker => {
            const icon = this.createIcon(marker.icon);
            const leafletMarker = L.marker(marker.position, { icon });

            // Add popup if provided
            if (marker.popup_html) {
                leafletMarker.bindPopup(marker.popup_html, { maxWidth: 320 });
            }

            // Add tooltip if provided
            if (marker.tooltip) {
                leafletMarker.bindTooltip(marker.tooltip);
            }

            leafletMarker.addTo(this.map);
        });
    }

    /**
     * Add feature layers (for multi-route maps with layer control)
     */
    addFeatureLayers(layers) {
        layers.forEach(layerData => {
            const featureGroup = L.featureGroup();

            // Add routes to feature group
            if (layerData.routes) {
                layerData.routes.forEach(route => {
                    const polyline = L.polyline(route.coordinates, {
                        color: route.color || '#007bff',
                        weight: route.weight || 4,
                        opacity: route.opacity || 0.8
                    });

                    if (route.popup_html) {
                        polyline.bindPopup(route.popup_html, { maxWidth: 320 });
                    }

                    if (route.tooltip) {
                        polyline.bindTooltip(route.tooltip);
                    }

                    polyline.addTo(featureGroup);
                });
            }

            // Add markers to feature group
            if (layerData.markers) {
                layerData.markers.forEach(marker => {
                    const icon = this.createIcon(marker.icon);
                    const leafletMarker = L.marker(marker.position, { icon });

                    if (marker.popup_html) {
                        leafletMarker.bindPopup(marker.popup_html, { maxWidth: 320 });
                    }

                    if (marker.tooltip) {
                        leafletMarker.bindTooltip(marker.tooltip);
                    }

                    leafletMarker.addTo(featureGroup);
                });
            }

            // Add to map if show is true
            if (layerData.show) {
                featureGroup.addTo(this.map);
            }

            // Store in layers for layer control
            this.layers[layerData.name] = featureGroup;
        });
    }

    /**
     * Create Leaflet icon from icon data
     */
    createIcon(iconData) {
        if (!iconData) {
            return new L.Icon.Default();
        }

        // Use Font Awesome icons via Leaflet.awesome-markers
        // For now, use default colored markers
        const iconColors = {
            'green': '#28a745',
            'blue': '#007bff',
            'red': '#dc3545',
            'yellow': '#ffc107',
            'orange': '#fd7e14',
            'purple': '#6f42c1'
        };

        const color = iconColors[iconData.color] || '#007bff';

        return L.divIcon({
            className: 'custom-marker',
            html: `<div style="background-color: ${color}; width: 25px; height: 25px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>`,
            iconSize: [25, 25],
            iconAnchor: [12, 12]
        });
    }

    /**
     * Show error message in map container
     */
    showError(message) {
        const container = document.getElementById(this.containerId);
        if (container) {
            container.innerHTML = `
                <div class="alert alert-warning" role="alert">
                    <i class="bi bi-exclamation-triangle"></i>
                    ${message}
                </div>
            `;
        }
    }

    /**
     * Destroy map instance
     */
    destroy() {
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
}

/**
 * Convenience function to render a map
 * 
 * @param {string} containerId - ID of the container element
 * @param {string} pageType - Type of map (dashboard, commute, planner, route_detail)
 * @param {object} options - Additional options (routeId, routeType, etc.)
 * @returns {MapRenderer} - MapRenderer instance
 */
async function renderMap(containerId, pageType, options = {}) {
    const renderer = new MapRenderer(containerId, pageType, options);
    await renderer.render();
    return renderer;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MapRenderer, renderMap };
}

// Made with Bob
