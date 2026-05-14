/**
 * routes.js - Route library page interactions
 */

(function() {
    const state = {
        routes: [],
        filteredRoutes: [],
        selectedForComparison: [],
        mapInstance: null,
        displayedRoutes: new Map(), // Map of routeId -> {polyline, markers}
        selectedRouteId: null, // Track currently selected route for z-index management
        routeColors: ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14']
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function getFilters() {
        return {
            favorite: byId('filter-favorite')?.value || '',
            sport_type: byId('filter-sport-type')?.value || '',
            difficulty: byId('filter-difficulty')?.value || '',
            min_distance: byId('filter-min-distance')?.value || '',
            max_distance: byId('filter-max-distance')?.value || '',
            sort_by: byId('sort-by')?.value || 'name',
            search: (byId('search-query')?.value || '').trim().toLowerCase()
        };
    }

    function announce(message) {
        const liveRegion = byId('routes-live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
        }
    }

    function initializeMap() {
        if (state.mapInstance) {
            return; // Already initialized
        }

        const mapElement = byId('routes-map');
        if (!mapElement) {
            console.warn('Map container not found');
            return;
        }

        // Check if the map container has already been initialized by another script
        if (mapElement._leaflet_id) {
            console.log('Map container already initialized, skipping...');
            return;
        }

        try {
            state.mapInstance = L.map('routes-map').setView([41.8781, -87.6298], 11); // Default to Chicago
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(state.mapInstance);

            // Fix map size after initialization
            setTimeout(() => {
                if (state.mapInstance) {
                    state.mapInstance.invalidateSize();
                }
            }, 100);

            updateMapStatus();
            console.log('✓ Map initialized successfully');
        } catch (error) {
            console.error('Failed to initialize map:', error);
        }
    }

    function updateMapStatus() {
        const statusElement = byId('map-status');
        if (!statusElement) return;

        const count = state.displayedRoutes.size;
        if (count === 0) {
            statusElement.textContent = 'Click on routes below to display them on the map';
            statusElement.className = 'mt-2 text-muted small';
        } else {
            statusElement.textContent = `Showing ${count} route${count > 1 ? 's' : ''} on map`;
            statusElement.className = 'mt-2 text-primary small';
        }
    }

    function getRouteColor(index) {
        return state.routeColors[index % state.routeColors.length];
    }

    async function toggleRouteOnMap(route) {
        console.log('toggleRouteOnMap called for:', route.name, route.id);
        
        if (!state.mapInstance) {
            console.log('Map not initialized, initializing now...');
            initializeMap();
        }

        const routeId = route.id;

        // If route is already displayed, remove it
        if (state.displayedRoutes.has(routeId)) {
            console.log('Route already on map, removing...');
            const mapObjects = state.displayedRoutes.get(routeId);
            if (mapObjects.polyline) {
                state.mapInstance.removeLayer(mapObjects.polyline);
            }
            if (mapObjects.startMarker) {
                state.mapInstance.removeLayer(mapObjects.startMarker);
            }
            if (mapObjects.endMarker) {
                state.mapInstance.removeLayer(mapObjects.endMarker);
            }
            state.displayedRoutes.delete(routeId);
            
            // Clear selection if this was the selected route
            if (state.selectedRouteId === routeId) {
                state.selectedRouteId = null;
            }
            
            updateMapStatus();
            
            // Reset card styling (Issue #121)
            const card = document.querySelector(`[data-route-id="${routeId}"]`);
            if (card) {
                card.style.borderColor = '';
                card.style.borderWidth = '';
                
                // Reset route name color
                const routeNameElement = card.querySelector('.route-name, h5, .card-title');
                if (routeNameElement) {
                    routeNameElement.style.color = '';
                    routeNameElement.style.fontWeight = '';
                }
            }
            return;
        }

        // Fetch route details to get coordinates
        try {
            const response = await window.apiClient.getRouteDetails(routeId, route.type);
            if (!response || !response.route || !response.route.coordinates || !response.route.coordinates.length) {
                console.warn('No coordinates available for route:', routeId);
                announce(`Unable to display ${route.name} - no coordinates available`);
                return;
            }

            const coordinates = response.route.coordinates;
            const colorIndex = state.displayedRoutes.size;
            const color = getRouteColor(colorIndex);

            // Create polyline with default styling
            const polyline = L.polyline(coordinates, {
                color: color,
                weight: 4,
                opacity: 0.8
            }).addTo(state.mapInstance);

            // Bind popup
            polyline.bindPopup(`<strong>${route.name}</strong><br>${window.formatDistance(route.distance)}`);
            
            // Bind tooltip with custom class for z-index control
            polyline.bindTooltip(route.name, {
                permanent: false,
                direction: 'top',
                className: 'route-tooltip',
                opacity: 0.9
            });

            // Add start and end markers
            const start = coordinates[0];
            const end = coordinates[coordinates.length - 1];

            const startMarker = L.marker(start, {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
                    iconSize: [12, 12]
                })
            }).addTo(state.mapInstance);
            startMarker.bindTooltip('Start', { permanent: false });

            const endMarker = L.marker(end, {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
                    iconSize: [12, 12]
                })
            }).addTo(state.mapInstance);
            endMarker.bindTooltip('End', { permanent: false });

            // Store map objects
            state.displayedRoutes.set(routeId, {
                polyline: polyline,
                startMarker: startMarker,
                endMarker: endMarker,
                color: color,
                defaultWeight: 4,
                defaultOpacity: 0.8
            });

            // Select this route (bring to front with enhanced styling)
            selectRoute(routeId);

            // Zoom to show the entire selected route with smooth animation (Issue #117)
            const bounds = polyline.getBounds();
            state.mapInstance.fitBounds(bounds, {
                padding: [50, 50],
                animate: true,
                duration: 0.5
            });
    /**
     * Select a route on the map (bring to front with enhanced styling)
     * Issue #74: Ensure selected polylines and tooltips appear on top
     * Issue #122: Grey out unselected routes
     */
    function selectRoute(routeId) {
        // Grey out ALL routes first
        state.displayedRoutes.forEach((mapObjects, id) => {
            if (mapObjects && mapObjects.polyline) {
                // Grey out unselected routes
                mapObjects.polyline.setStyle({
                    weight: mapObjects.defaultWeight || 4,
                    opacity: 0.3, // Greyed out
                    color: '#999999' // Grey color
                });
                
                // Grey out markers
                if (mapObjects.startMarker) {
                    mapObjects.startMarker.setOpacity(0.3);
                }
                if (mapObjects.endMarker) {
                    mapObjects.endMarker.setOpacity(0.3);
                }
                
                // Remove selected class from tooltip
                const tooltip = mapObjects.polyline.getTooltip();
                if (tooltip) {
                    const tooltipElement = tooltip.getElement();
                    if (tooltipElement) {
                        tooltipElement.classList.remove('selected-route-tooltip');
                    }
                }
            }
        });

        // Highlight the selected route
        const mapObjects = state.displayedRoutes.get(routeId);
        if (mapObjects && mapObjects.polyline) {
            // Bring polyline to front (z-index)
            mapObjects.polyline.bringToFront();
            
            // Bring markers to front
            if (mapObjects.startMarker) {
                mapObjects.startMarker.bringToFront();
                mapObjects.startMarker.setOpacity(1.0);
            }
            if (mapObjects.endMarker) {
                mapObjects.endMarker.bringToFront();
                mapObjects.endMarker.setOpacity(1.0);
            }
            
            // Enhance visual styling with original color
            mapObjects.polyline.setStyle({
                weight: 6, // Thicker line
                opacity: 1.0, // Full opacity
                color: mapObjects.color // Restore original color
            });
            
            // Add selected class to tooltip for higher z-index
            const tooltip = mapObjects.polyline.getTooltip();
            if (tooltip) {
                const tooltipElement = tooltip.getElement();
                if (tooltipElement) {
                    tooltipElement.classList.add('selected-route-tooltip');
                }
            }
            
            state.selectedRouteId = routeId;
            console.log(`✓ Route ${routeId} selected and brought to front, others greyed out`);
        }
    }

            
            updateMapStatus();

            // Update card styling to show it's on the map
            // Issue #121: Color code route names to match map lines
            const card = document.querySelector(`[data-route-id="${routeId}"]`);
            if (card) {
                card.style.borderColor = color;
                card.style.borderWidth = '3px';
                
                // Color the route name to match the map line
                const routeNameElement = card.querySelector('.route-name, h5, .card-title');
                if (routeNameElement) {
                    routeNameElement.style.color = color;
                    routeNameElement.style.fontWeight = '700';
                }
            }

        } catch (error) {
            console.error('Failed to load route coordinates:', error);
            const errorMessage = error.message || 'Unable to load route details';
            announce(`Error displaying ${route.name}: ${errorMessage}`);
            
            // Show temporary error notification
            if (window.showToast) {
                window.showToast(`Failed to display route: ${errorMessage}`, 'error');
            }
        }
    }

    function fitAllRoutes() {
        if (!state.mapInstance || state.displayedRoutes.size === 0) {
            return;
        }

        const bounds = L.latLngBounds();
        state.displayedRoutes.forEach(mapObjects => {
            if (mapObjects.polyline) {
                bounds.extend(mapObjects.polyline.getBounds());
            }
        });

        if (bounds.isValid()) {
            state.mapInstance.fitBounds(bounds, { padding: [30, 30] });
        }
    }

    function clearAllRoutes() {
        if (!state.mapInstance) {
            return;
        }

        state.displayedRoutes.forEach((mapObjects, routeId) => {
            if (mapObjects.polyline) {
                state.mapInstance.removeLayer(mapObjects.polyline);
            }
            if (mapObjects.startMarker) {
                state.mapInstance.removeLayer(mapObjects.startMarker);
            }
            if (mapObjects.endMarker) {
                state.mapInstance.removeLayer(mapObjects.endMarker);
            }

            // Reset card styling (Issue #121)
            const card = document.querySelector(`[data-route-id="${routeId}"]`);
            if (card) {
                card.style.borderColor = '';
                card.style.borderWidth = '';
                
                // Reset route name color
                const routeNameElement = card.querySelector('.route-name, h5, .card-title');
                if (routeNameElement) {
                    routeNameElement.style.color = '';
                    routeNameElement.style.fontWeight = '';
                }
            }
        });

        state.displayedRoutes.clear();
        updateMapStatus();
        announce('Cleared all routes from map');
    }

    function navigateToRouteDetail(routeId, routeType) {
        const params = new URLSearchParams({ id: routeId });
        if (routeType) {
            params.set('type', routeType);
        }
        window.location.href = `/route-detail.html?${params.toString()}`;
    }

    function formatDuration(durationMinutes) {
        const totalMinutes = Math.round(Number(durationMinutes || 0));
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }

        return `${totalMinutes} min`;
    }

    function createRouteCard(route, mode = 'full') {
        // Simple mode for dashboard list view
        if (mode === 'simple') {
            const row = document.createElement('div');
            row.className = 'route-row p-3 mb-2 border rounded';
            row.style.cursor = 'pointer';
            row.setAttribute('data-route-id', route.id);
            
            row.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 me-2" style="min-width: 0;">
                        <h6 class="mb-1 text-truncate" title="${route.name}">
                            ${route.is_favorite ? '<i class="bi bi-star-fill text-warning"></i> ' : ''}
                            ${route.name}
                        </h6>
                        <small class="text-muted">
                            ${window.formatDistance(route.distance)} • ${window.formatElevation(route.elevation_gain || route.elevation || 0)} • ${route.uses || 0} uses
                        </small>
                    </div>
                    <span class="badge bg-secondary flex-shrink-0">${route.sport_type || 'commute'}</span>
                </div>
            `;
            
            return row;
        }
        
        // Full mode for routes page
        const column = document.createElement('div');
        column.className = 'col-12 col-md-6 col-xl-4';

        const card = document.createElement('div');
        card.className = 'card h-100 shadow-sm route-library-card';
        card.setAttribute('data-route-id', route.id);
        card.setAttribute('data-route-type', route.type || '');
        card.style.transition = 'transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease';
        card.style.minHeight = '100%';

        const isSelected = state.selectedForComparison.some(r => r.id === route.id);
        card.addEventListener('focus', () => {
            card.classList.add('border-primary');
        });
        card.addEventListener('blur', () => {
            card.classList.remove('border-primary');
        });
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-2px)';
            card.style.boxShadow = '0 0.5rem 1rem rgba(0,0,0,0.12)';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '';
        });

        const badge = route.is_favorite
            ? '<span class="badge bg-warning text-dark"><i class="bi bi-star-fill"></i> Favorite</span>'
            : '';

        const plusBadge = route.is_plus_route
            ? '<span class="badge bg-success-subtle text-success-emphasis">PLUS</span>'
            : '';

        // Difficulty badge with semantic colors (4 levels)
        // Normalize difficulty to title case for consistency
        const rawDifficulty = route.difficulty || 'Easy';
        const difficulty = rawDifficulty.charAt(0).toUpperCase() + rawDifficulty.slice(1).toLowerCase();
        const difficultyColors = {
            'Easy': 'bg-success',
            'Moderate': 'bg-primary',
            'Hard': 'bg-warning text-dark',
            'Very hard': 'bg-danger'
        };
        const difficultyIcons = {
            'Easy': 'bi-check-circle',
            'Moderate': 'bi-dash-circle',
            'Hard': 'bi-exclamation-circle',
            'Very hard': 'bi-exclamation-triangle-fill'
        };
        const difficultyBadge = `<span class="badge ${difficultyColors[difficulty]}" aria-label="Difficulty: ${difficulty}">
            <i class="bi ${difficultyIcons[difficulty]}" aria-hidden="true"></i> ${difficulty}
        </span>`;

        card.innerHTML = `
            <div class="card-body d-flex flex-column">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
                    <div class="form-check">
                        <input class="form-check-input compare-checkbox" type="checkbox"
                               id="compare-${route.id}"
                               data-route-id="${route.id}"
                               ${isSelected ? 'checked' : ''}
                               onclick="event.stopPropagation()">
                        <label class="form-check-label small text-muted" for="compare-${route.id}">
                            Compare
                        </label>
                    </div>
                    <div class="d-flex flex-column align-items-end gap-1">
                        ${badge}
                        ${plusBadge}
                        ${difficultyBadge}
                    </div>
                </div>
                <div class="mb-3" style="cursor: pointer;" data-route-link>
                    <h3 class="h5 mb-1 text-truncate" title="${route.name}">${route.name}</h3>
                    <p class="text-muted mb-0 text-capitalize">${route.type || 'route'}</p>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="small text-muted">Distance</div>
                            <div class="fw-semibold">${window.formatDistance(route.distance)}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="small text-muted">Duration</div>
                            <div class="fw-semibold">${formatDuration(route.duration)}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="small text-muted">Elevation</div>
                            <div class="fw-semibold">${window.formatElevation(route.elevation_gain || route.elevation || 0)}</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="border rounded p-2 h-100">
                            <div class="small text-muted">Uses</div>
                            <div class="fw-semibold">${route.uses || 0}</div>
                        </div>
                    </div>
                </div>

                <div class="mt-auto d-flex justify-content-between align-items-center" data-route-link>
                    <span class="text-muted small">${route.sport_type || 'Ride'}</span>
                    <span class="text-primary fw-semibold">View details <i class="bi bi-arrow-right" aria-hidden="true"></i></span>
                </div>
            </div>
        `;

        // Add click handler for the card itself to toggle map display
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
            console.log('Card clicked:', route.name);
            // Don't trigger if clicking on checkbox or detail links
            if (e.target.closest('.compare-checkbox') || e.target.closest('[data-route-link]')) {
                console.log('Click was on checkbox or link, ignoring');
                return;
            }
            console.log('Calling toggleRouteOnMap');
            toggleRouteOnMap(route);
        });

        // Add click handler for route details (but not on checkbox)
        const linkElements = card.querySelectorAll('[data-route-link]');
        linkElements.forEach(el => {
            el.style.cursor = 'pointer';
            el.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click
                navigateToRouteDetail(route.id, route.type);
            });
        });

        // Add checkbox handler
        const checkbox = card.querySelector('.compare-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                e.stopPropagation();
                toggleRouteComparison(route);
            });
        }

        column.appendChild(card);
        return column;
    }

    function toggleRouteComparison(route) {
        const index = state.selectedForComparison.findIndex(r => r.id === route.id);
        
        if (index > -1) {
            // Remove from comparison
            state.selectedForComparison.splice(index, 1);
        } else {
            // Add to comparison (max 3 routes)
            if (state.selectedForComparison.length >= 3) {
                alert('You can compare up to 3 routes at a time. Please deselect one first.');
                // Uncheck the checkbox
                const checkbox = document.querySelector(`#compare-${route.id}`);
                if (checkbox) checkbox.checked = false;
                return;
            }
            state.selectedForComparison.push(route);
        }
        
        updateCompareButton();
    }

    function updateCompareButton() {
        let compareBtn = byId('compare-routes-btn');
        const count = state.selectedForComparison.length;
        
        if (!compareBtn && count > 0) {
            // Create floating compare button
            compareBtn = document.createElement('button');
            compareBtn.id = 'compare-routes-btn';
            compareBtn.className = 'btn btn-primary btn-lg position-fixed';
            compareBtn.style.cssText = 'bottom: 2rem; right: 2rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
            document.body.appendChild(compareBtn);
            
            compareBtn.addEventListener('click', () => {
                const ids = state.selectedForComparison.map(r => r.id).join(',');
                window.location.href = `/compare.html?ids=${ids}`;
            });
        }
        
        if (compareBtn) {
            if (count > 0) {
                compareBtn.innerHTML = `<i class="bi bi-arrow-left-right"></i> Compare ${count} Route${count > 1 ? 's' : ''}`;
                compareBtn.style.display = 'block';
            } else {
                compareBtn.style.display = 'none';
            }
        }
    }

    function applyClientFilters(routes, filters) {
        let filtered = [...routes];

        if (filters.favorite === 'true') {
            filtered = filtered.filter(route => route.is_favorite);
        } else if (filters.favorite === 'false') {
            filtered = filtered.filter(route => !route.is_favorite);
        }

        if (filters.sport_type) {
            filtered = filtered.filter(route => (route.sport_type || '') === filters.sport_type);
        }

        if (filters.difficulty) {
            const filterDiff = filters.difficulty.toLowerCase();
            filtered = filtered.filter(route => {
                const routeDiff = (route.difficulty || 'Easy').toLowerCase();
                return routeDiff === filterDiff;
            });
        }

        if (filters.min_distance) {
            filtered = filtered.filter(route => Number(route.distance || 0) >= Number(filters.min_distance));
        }

        if (filters.max_distance) {
            filtered = filtered.filter(route => Number(route.distance || 0) <= Number(filters.max_distance));
        }

        if (filters.search) {
            filtered = filtered.filter(route =>
                (route.name || '').toLowerCase().includes(filters.search)
            );
        }

        switch (filters.sort_by) {
            case 'name':
                filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                break;
            case 'name-desc':
                filtered.sort((a, b) => (b.name || '').localeCompare(a.name || ''));
                break;
            case 'distance':
                filtered.sort((a, b) => Number(a.distance || 0) - Number(b.distance || 0));
                break;
            case 'distance-desc':
                filtered.sort((a, b) => Number(b.distance || 0) - Number(a.distance || 0));
                break;
            case 'elevation':
                filtered.sort((a, b) => Number(a.elevation_gain || a.elevation || 0) - Number(b.elevation_gain || b.elevation || 0));
                break;
            case 'elevation-desc':
                filtered.sort((a, b) => Number(b.elevation_gain || b.elevation || 0) - Number(a.elevation_gain || a.elevation || 0));
                break;
            case 'uses':
                filtered.sort((a, b) => Number(b.uses || 0) - Number(a.uses || 0));
                break;
        }

        return filtered;
    }

    function renderSummary(count) {
        const summary = byId('results-summary');
        if (!summary) return;

        summary.className = count > 0 ? 'alert alert-info' : 'alert alert-warning';
        summary.innerHTML = count > 0
            ? `<i class="bi bi-info-circle"></i> Showing ${count} route${count === 1 ? '' : 's'}`
            : '<i class="bi bi-exclamation-triangle"></i> No routes match the current filters';

    function displayRoutesTimestamp(timestamp) {
        const summary = byId('results-summary');
        if (!summary || !timestamp) return;
        
        // Check if timestamp element already exists
        let timestampEl = summary.querySelector('.timestamp-display');
        if (!timestampEl) {
            timestampEl = document.createElement('small');
            timestampEl.className = 'timestamp-display ms-2';
            summary.appendChild(timestampEl);
        }
        
        // Update timestamp content
        timestampEl.setAttribute('data-timestamp', timestamp);
        timestampEl.setAttribute('title', window.formatAbsoluteTime(timestamp));
        timestampEl.innerHTML = `<i class="bi bi-clock"></i> Synced ${window.formatRelativeTime(timestamp)}`;
    }
    }

    function renderRoutes(routes) {
        const container = byId('routes-container');
        if (!container) return;

        container.innerHTML = '';

        if (!routes.length) {
            renderSummary(0);
            announce('No routes found');
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i> No routes found.
                </div>
            `;
            return;
        }

        const row = document.createElement('div');
        row.className = 'row g-3';

        routes.forEach(route => {
            row.appendChild(createRouteCard(route));
        });

        container.appendChild(row);
        renderSummary(routes.length);
        announce(`Showing ${routes.length} routes`);
    }

    async function loadRoutes() {
        const container = byId('routes-container');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading routes...</span>
                    </div>
                    <p class="mt-3 text-muted">Loading routes...</p>
                </div>
            `;
        }

        try {
            const response = await window.apiClient.getRoutes();
            state.routes = Array.isArray(response.routes) ? response.routes : [];
            state.filteredRoutes = applyClientFilters(state.routes, getFilters());
            state.lastUpdated = response.timestamp; // Store timestamp for display
            renderRoutes(state.filteredRoutes);
            
            // Display timestamp if available
            if (response.timestamp) {
                displayRoutesTimestamp(response.timestamp);
            }
        } catch (error) {
            console.error('Failed to load routes:', error);
            if (container) {
                const errorMessage = error.message || 'Failed to load routes. Please try again.';
                container.innerHTML = `
                    <div class="alert alert-warning" role="alert">
                        <div class="d-flex align-items-center mb-2">
                            <i class="bi bi-exclamation-triangle fs-4 me-2"></i>
                            <strong>Unable to Load Routes</strong>
                        </div>
                        <p class="mb-2">${errorMessage}</p>
                        <button class="btn btn-primary btn-sm" onclick="window.location.reload()">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </div>
                `;
            }
            renderSummary(0);
            announce('Failed to load routes');
        }
    }

    function applyPreset(preset) {
        const minDistanceInput = byId('filter-min-distance');
        const maxDistanceInput = byId('filter-max-distance');
        
        // Clear active state from all preset buttons
        document.querySelectorAll('.preset-filter').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Set the clicked button as active
        const activeButton = document.querySelector(`[data-preset="${preset}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        // Apply preset filters (convert km to miles: 1 km ≈ 0.621371 mi)
        switch (preset) {
            case 'short':
                if (minDistanceInput) minDistanceInput.value = '';
                if (maxDistanceInput) maxDistanceInput.value = '10';
                break;
            case 'medium':
                if (minDistanceInput) minDistanceInput.value = '10';
                if (maxDistanceInput) maxDistanceInput.value = '20';
                break;
            case 'long':
                if (minDistanceInput) minDistanceInput.value = '20';
                if (maxDistanceInput) maxDistanceInput.value = '';
                break;
            case 'all':
                if (minDistanceInput) minDistanceInput.value = '';
                if (maxDistanceInput) maxDistanceInput.value = '';
                break;
        }
        
        // Apply filters immediately
        state.filteredRoutes = applyClientFilters(state.routes, getFilters());
        renderRoutes(state.filteredRoutes);
        announce(`Applied ${preset} distance filter`);
    }

    function bindEvents() {
        const applyButton = byId('apply-filters');
        if (applyButton) {
            applyButton.addEventListener('click', () => {
                state.filteredRoutes = applyClientFilters(state.routes, getFilters());
                renderRoutes(state.filteredRoutes);
            });
        }

        const searchInput = byId('search-query');
        if (searchInput) {
            searchInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    state.filteredRoutes = applyClientFilters(state.routes, getFilters());
                    renderRoutes(state.filteredRoutes);
                }
            });
        }
        
        // Bind preset filter buttons
        document.querySelectorAll('.preset-filter').forEach(button => {
            button.addEventListener('click', () => {
                const preset = button.getAttribute('data-preset');
                if (preset) {
                    applyPreset(preset);
                }
            });
        });

        // Bind map control buttons
        const fitAllBtn = byId('fit-all-btn');
        if (fitAllBtn) {
            fitAllBtn.addEventListener('click', () => {
                fitAllRoutes();
                announce('Fitted all routes in view');
            });
        }

        const clearMapBtn = byId('clear-map-btn');
        if (clearMapBtn) {
            clearMapBtn.addEventListener('click', () => {
                clearAllRoutes();
            });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        // Only initialize if we're on the routes page (has routes-container)
        const routesContainer = byId('routes-container');
        if (routesContainer) {
            console.log('✓ Routes page detected, initializing...');
            initializeMap();
            bindEvents();
            loadRoutes();
        } else {
            console.log('ℹ Not on routes page, skipping routes.js initialization');
        }
    });
    
    // Expose functions for use by dashboard
    window.RouteRenderer = {
        createRouteCard: createRouteCard,
        formatDuration: formatDuration
    };
})();

// Made with Bob
