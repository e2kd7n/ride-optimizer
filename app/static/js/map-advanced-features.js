/**
 * Advanced Map Features Module
 * 
 * Provides elevation profiles, route analytics overlays, and map export functionality
 * for the Ride Optimizer application.
 * 
 * Features:
 * - Elevation profile visualization with Chart.js
 * - Interactive elevation profiles (hover, click)
 * - Route analytics overlays (speed heatmap, effort zones)
 * - Map export (PNG, GPX, GeoJSON, PDF)
 * 
 * Dependencies:
 * - Chart.js 4.x
 * - Leaflet (via Folium)
 * - html2canvas (for PNG export)
 * - jsPDF (for PDF export)
 */

(function(window) {
    'use strict';
    
    // Module namespace
    const MapAdvancedFeatures = {
        charts: {},
        exportHandlers: {},
        analyticsLayers: {}
    };
    
    /**
     * Initialize elevation profile for a route
     * @param {Object} options - Configuration options
     * @param {string} options.containerId - ID of container element
     * @param {Array} options.elevationData - Array of {distance, elevation} objects
     * @param {Object} options.mapInstance - Leaflet map instance (optional)
     * @param {string} options.routeName - Route name for display
     */
    MapAdvancedFeatures.initElevationProfile = function(options) {
        const {
            containerId,
            elevationData,
            mapInstance,
            routeName = 'Route'
        } = options;
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Elevation profile container ${containerId} not found`);
            return null;
        }
        
        // Create canvas element
        const canvas = document.createElement('canvas');
        canvas.id = `${containerId}-canvas`;
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        container.appendChild(canvas);
        
        // Prepare data
        const distances = elevationData.map(d => d.distance);
        const elevations = elevationData.map(d => d.elevation);
        
        // Calculate elevation gain/loss
        let gain = 0, loss = 0;
        for (let i = 1; i < elevations.length; i++) {
            const diff = elevations[i] - elevations[i-1];
            if (diff > 0) gain += diff;
            else loss += Math.abs(diff);
        }
        
        // Create Chart.js chart
        const ctx = canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: distances,
                datasets: [{
                    label: 'Elevation (m)',
                    data: elevations,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#e74c3c',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: `${routeName} - Elevation Profile`,
                        font: { size: 16, weight: 'bold' }
                    },
                    subtitle: {
                        display: true,
                        text: `Gain: ${gain.toFixed(0)}m | Loss: ${loss.toFixed(0)}m`,
                        font: { size: 12 },
                        color: '#7f8c8d'
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                return `Distance: ${context[0].label} km`;
                            },
                            label: function(context) {
                                return `Elevation: ${context.parsed.y.toFixed(0)}m`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Elevation (m)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                onHover: function(event, activeElements) {
                    if (activeElements.length > 0 && mapInstance) {
                        const index = activeElements[0].index;
                        MapAdvancedFeatures.highlightMapPosition(mapInstance, elevationData[index]);
                    }
                }
            }
        });
        
        // Store chart instance
        MapAdvancedFeatures.charts[containerId] = chart;
        
        // Add click handler for map interaction
        if (mapInstance) {
            canvas.addEventListener('click', function(event) {
                const points = chart.getElementsAtEventForMode(event, 'nearest', { intersect: false }, true);
                if (points.length > 0) {
                    const index = points[0].index;
                    MapAdvancedFeatures.panMapToPosition(mapInstance, elevationData[index]);
                }
            });
        }
        
        return chart;
    };
    
    /**
     * Highlight position on map based on elevation profile hover
     * @param {Object} mapInstance - Leaflet map instance
     * @param {Object} dataPoint - Data point with lat/lng
     */
    MapAdvancedFeatures.highlightMapPosition = function(mapInstance, dataPoint) {
        if (!dataPoint.lat || !dataPoint.lng) return;
        
        // Remove existing highlight marker
        if (mapInstance._highlightMarker) {
            mapInstance.removeLayer(mapInstance._highlightMarker);
        }
        
        // Add new highlight marker
        mapInstance._highlightMarker = L.circleMarker([dataPoint.lat, dataPoint.lng], {
            radius: 8,
            fillColor: '#e74c3c',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).addTo(mapInstance);
    };
    
    /**
     * Pan map to specific position
     * @param {Object} mapInstance - Leaflet map instance
     * @param {Object} dataPoint - Data point with lat/lng
     */
    MapAdvancedFeatures.panMapToPosition = function(mapInstance, dataPoint) {
        if (!dataPoint.lat || !dataPoint.lng) return;
        mapInstance.panTo([dataPoint.lat, dataPoint.lng], { animate: true, duration: 0.5 });
    };
    
    /**
     * Add route analytics overlay to map
     * @param {Object} options - Configuration options
     * @param {Object} options.mapInstance - Leaflet map instance
     * @param {Array} options.routeData - Route data with speed/effort info
     * @param {string} options.overlayType - 'speed' or 'effort'
     */
    MapAdvancedFeatures.addAnalyticsOverlay = function(options) {
        const {
            mapInstance,
            routeData,
            overlayType = 'speed'
        } = options;
        
        if (!mapInstance || !routeData) {
            console.warn('Map instance or route data missing for analytics overlay');
            return;
        }
        
        // Remove existing analytics layer
        if (mapInstance._analyticsLayer) {
            mapInstance.removeLayer(mapInstance._analyticsLayer);
        }
        
        // Create polyline segments with color coding
        const segments = [];
        for (let i = 0; i < routeData.length - 1; i++) {
            const point1 = routeData[i];
            const point2 = routeData[i + 1];
            
            let color, weight;
            if (overlayType === 'speed') {
                // Speed heatmap: green (fast) to red (slow)
                color = MapAdvancedFeatures.getSpeedColor(point1.speed);
                weight = 5;
            } else {
                // Effort zones: green (easy) to red (hard)
                color = MapAdvancedFeatures.getEffortColor(point1.effort);
                weight = 6;
            }
            
            const segment = L.polyline(
                [[point1.lat, point1.lng], [point2.lat, point2.lng]],
                {
                    color: color,
                    weight: weight,
                    opacity: 0.8
                }
            );
            
            segments.push(segment);
        }
        
        // Create layer group
        const analyticsLayer = L.layerGroup(segments);
        mapInstance._analyticsLayer = analyticsLayer;
        analyticsLayer.addTo(mapInstance);
        
        // Store reference
        MapAdvancedFeatures.analyticsLayers[mapInstance._leaflet_id] = analyticsLayer;
        
        return analyticsLayer;
    };
    
    /**
     * Get color for speed value
     * @param {number} speed - Speed in km/h
     * @returns {string} Hex color
     */
    MapAdvancedFeatures.getSpeedColor = function(speed) {
        // Speed ranges: <15 (red), 15-20 (yellow), 20-25 (light green), >25 (green)
        if (speed < 15) return '#e74c3c';
        if (speed < 20) return '#f39c12';
        if (speed < 25) return '#f1c40f';
        return '#27ae60';
    };
    
    /**
     * Get color for effort level
     * @param {number} effort - Effort level (0-1)
     * @returns {string} Hex color
     */
    MapAdvancedFeatures.getEffortColor = function(effort) {
        // Effort zones: 0-0.3 (green), 0.3-0.6 (yellow), 0.6-0.8 (orange), >0.8 (red)
        if (effort < 0.3) return '#27ae60';
        if (effort < 0.6) return '#f1c40f';
        if (effort < 0.8) return '#e67e22';
        return '#e74c3c';
    };
    
    /**
     * Toggle analytics overlay visibility
     * @param {Object} mapInstance - Leaflet map instance
     * @param {boolean} visible - Show or hide overlay
     */
    MapAdvancedFeatures.toggleAnalyticsOverlay = function(mapInstance, visible) {
        const layer = MapAdvancedFeatures.analyticsLayers[mapInstance._leaflet_id];
        if (!layer) return;
        
        if (visible) {
            layer.addTo(mapInstance);
        } else {
            mapInstance.removeLayer(layer);
        }
    };
    
    /**
     * Export map as PNG image
     * @param {Object} options - Export options
     * @param {string} options.mapContainerId - ID of map container
     * @param {string} options.filename - Output filename
     */
    MapAdvancedFeatures.exportMapAsPNG = async function(options) {
        const {
            mapContainerId,
            filename = 'route-map.png'
        } = options;
        
        const container = document.getElementById(mapContainerId);
        if (!container) {
            console.error('Map container not found');
            return;
        }
        
        try {
            // Use html2canvas to capture map
            const canvas = await html2canvas(container, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff'
            });
            
            // Convert to blob and download
            canvas.toBlob(function(blob) {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                link.click();
                URL.revokeObjectURL(url);
            });
            
            return true;
        } catch (error) {
            console.error('PNG export failed:', error);
            return false;
        }
    };
    
    /**
     * Export route as GPX file
     * @param {Object} options - Export options
     * @param {Array} options.coordinates - Array of {lat, lng, elevation} objects
     * @param {string} options.routeName - Route name
     * @param {string} options.filename - Output filename
     */
    MapAdvancedFeatures.exportRouteAsGPX = function(options) {
        const {
            coordinates,
            routeName = 'Route',
            filename = 'route.gpx'
        } = options;
        
        if (!coordinates || coordinates.length === 0) {
            console.error('No coordinates provided for GPX export');
            return false;
        }
        
        // Build GPX XML
        let gpx = '<?xml version="1.0" encoding="UTF-8"?>\n';
        gpx += '<gpx version="1.1" creator="Ride Optimizer" xmlns="http://www.topografix.com/GPX/1/1">\n';
        gpx += `  <metadata>\n`;
        gpx += `    <name>${escapeXml(routeName)}</name>\n`;
        gpx += `    <time>${new Date().toISOString()}</time>\n`;
        gpx += `  </metadata>\n`;
        gpx += `  <trk>\n`;
        gpx += `    <name>${escapeXml(routeName)}</name>\n`;
        gpx += `    <trkseg>\n`;
        
        coordinates.forEach(coord => {
            gpx += `      <trkpt lat="${coord.lat}" lon="${coord.lng}">\n`;
            if (coord.elevation !== undefined) {
                gpx += `        <ele>${coord.elevation}</ele>\n`;
            }
            gpx += `      </trkpt>\n`;
        });
        
        gpx += `    </trkseg>\n`;
        gpx += `  </trk>\n`;
        gpx += `</gpx>`;
        
        // Download file
        const blob = new Blob([gpx], { type: 'application/gpx+xml' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
        
        return true;
    };
    
    /**
     * Export route as GeoJSON file
     * @param {Object} options - Export options
     * @param {Array} options.coordinates - Array of {lat, lng} objects
     * @param {Object} options.properties - Additional properties
     * @param {string} options.filename - Output filename
     */
    MapAdvancedFeatures.exportRouteAsGeoJSON = function(options) {
        const {
            coordinates,
            properties = {},
            filename = 'route.geojson'
        } = options;
        
        if (!coordinates || coordinates.length === 0) {
            console.error('No coordinates provided for GeoJSON export');
            return false;
        }
        
        // Build GeoJSON
        const geojson = {
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: coordinates.map(c => [c.lng, c.lat])
            },
            properties: {
                ...properties,
                exported: new Date().toISOString(),
                source: 'Ride Optimizer'
            }
        };
        
        // Download file
        const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
        
        return true;
    };
    
    /**
     * Export map as PDF
     * @param {Object} options - Export options
     * @param {string} options.mapContainerId - ID of map container
     * @param {Object} options.routeStats - Route statistics to include
     * @param {string} options.filename - Output filename
     */
    MapAdvancedFeatures.exportMapAsPDF = async function(options) {
        const {
            mapContainerId,
            routeStats = {},
            filename = 'route-map.pdf'
        } = options;
        
        const container = document.getElementById(mapContainerId);
        if (!container) {
            console.error('Map container not found');
            return false;
        }
        
        try {
            // Capture map as image
            const canvas = await html2canvas(container, {
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff'
            });
            
            // Create PDF
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a4'
            });
            
            // Add title
            pdf.setFontSize(18);
            pdf.text(routeStats.name || 'Route Map', 15, 15);
            
            // Add map image
            const imgData = canvas.toDataURL('image/png');
            const imgWidth = 270;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;
            pdf.addImage(imgData, 'PNG', 15, 25, imgWidth, Math.min(imgHeight, 150));
            
            // Add route statistics
            let yPos = 25 + Math.min(imgHeight, 150) + 10;
            pdf.setFontSize(12);
            pdf.text('Route Statistics:', 15, yPos);
            yPos += 7;
            
            pdf.setFontSize(10);
            if (routeStats.distance) {
                pdf.text(`Distance: ${routeStats.distance} km`, 20, yPos);
                yPos += 5;
            }
            if (routeStats.duration) {
                pdf.text(`Duration: ${routeStats.duration} min`, 20, yPos);
                yPos += 5;
            }
            if (routeStats.elevation) {
                pdf.text(`Elevation Gain: ${routeStats.elevation} m`, 20, yPos);
                yPos += 5;
            }
            
            // Add footer
            pdf.setFontSize(8);
            pdf.text(`Generated by Ride Optimizer on ${new Date().toLocaleDateString()}`, 15, 200);
            
            // Save PDF
            pdf.save(filename);
            
            return true;
        } catch (error) {
            console.error('PDF export failed:', error);
            return false;
        }
    };
    
    /**
     * Create export button UI
     * @param {Object} options - Button options
     * @param {string} options.containerId - Container element ID
     * @param {Object} options.exportOptions - Export configuration
     */
    MapAdvancedFeatures.createExportButton = function(options) {
        const {
            containerId,
            exportOptions = {}
        } = options;
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Export button container ${containerId} not found`);
            return;
        }
        
        // Create button group
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'map-export-buttons';
        buttonGroup.innerHTML = `
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-sm btn-outline-primary dropdown-toggle" 
                        data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-download"></i> Export Map
                </button>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="#" data-export-type="png">
                        <i class="bi bi-image"></i> PNG Image
                    </a></li>
                    <li><a class="dropdown-item" href="#" data-export-type="gpx">
                        <i class="bi bi-geo-alt"></i> GPX File
                    </a></li>
                    <li><a class="dropdown-item" href="#" data-export-type="geojson">
                        <i class="bi bi-code-square"></i> GeoJSON
                    </a></li>
                    <li><a class="dropdown-item" href="#" data-export-type="pdf">
                        <i class="bi bi-file-pdf"></i> PDF Document
                    </a></li>
                </ul>
            </div>
        `;
        
        container.appendChild(buttonGroup);
        
        // Add event listeners
        buttonGroup.querySelectorAll('[data-export-type]').forEach(item => {
            item.addEventListener('click', async function(e) {
                e.preventDefault();
                const exportType = this.dataset.exportType;
                
                // Show loading state
                const btn = buttonGroup.querySelector('.dropdown-toggle');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Exporting...';
                btn.disabled = true;
                
                try {
                    let success = false;
                    switch (exportType) {
                        case 'png':
                            success = await MapAdvancedFeatures.exportMapAsPNG(exportOptions);
                            break;
                        case 'gpx':
                            success = MapAdvancedFeatures.exportRouteAsGPX(exportOptions);
                            break;
                        case 'geojson':
                            success = MapAdvancedFeatures.exportRouteAsGeoJSON(exportOptions);
                            break;
                        case 'pdf':
                            success = await MapAdvancedFeatures.exportMapAsPDF(exportOptions);
                            break;
                    }
                    
                    if (success) {
                        showNotification('success', `Map exported as ${exportType.toUpperCase()}`);
                    } else {
                        showNotification('error', 'Export failed. Please try again.');
                    }
                } catch (error) {
                    console.error('Export error:', error);
                    showNotification('error', 'Export failed. Please try again.');
                } finally {
                    // Restore button
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            });
        });
    };
    
    /**
     * Helper: Escape XML special characters
     */
    function escapeXml(unsafe) {
        return unsafe
            .replace(/&/g, '&' + 'amp;')
            .replace(/</g, '&' + 'lt;')
            .replace(/>/g, '&' + 'gt;')
            .replace(/"/g, '&' + 'quot;')
            .replace(/'/g, '&' + 'apos;');
    }
    
    /**
     * Helper: Show notification
     */
    function showNotification(type, message) {
        // Use existing flash message system if available
        if (typeof showFlashMessage === 'function') {
            showFlashMessage(type === 'error' ? 'danger' : type, message);
        } else {
            alert(message);
        }
    }
    
    // Export module to global scope
    window.MapAdvancedFeatures = MapAdvancedFeatures;
    
})(window);

// Made with Bob