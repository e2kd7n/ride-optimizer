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

    // Every route/legend color used on this page comes from a fixed palette
    // (routeColors above plus distanceColor/recencyColor's buckets) — map each
    // hex to a CSS class instead of an inline style="" so CSP style-src can
    // drop 'unsafe-inline' (#475).
    const ROUTE_COLOR_CLASS = {
        '#007bff': 'c-blue',
        '#28a745': 'c-green',
        '#dc3545': 'c-red',
        '#ffc107': 'c-yellow',
        '#17a2b8': 'c-teal',
        '#6f42c1': 'c-purple',
        '#fd7e14': 'c-orange',
        '#6c757d': 'c-gray'
    };

    function colorClass(hex) {
        return ROUTE_COLOR_CLASS[hex] || 'c-blue';
    }

    function byId(id) {
        return document.getElementById(id);
    }

    function getFilters() {
        return {
            favorite: byId('filter-favorite')?.value || '',
            commute: byId('filter-commute')?.value || '',
            sport_type: byId('filter-sport-type')?.value || '',
            difficulty: byId('filter-difficulty')?.value || '',
            min_distance: byId('filter-min-distance')?.value || '',
            max_distance: byId('filter-max-distance')?.value || '',
            date_range: byId('filter-date-range')?.value || '',
            sort_by: byId('sort-by')?.value || 'name',
            search: (byId('search-query')?.value || '').trim().toLowerCase()
        };
    }

    function getColorBy() {
        return byId('color-by')?.value || 'default';
    }

    function distanceColor(distanceKm) {
        const mi = distanceKm * 0.621371;
        if (mi < 10) return '#28a745';
        if (mi < 20) return '#ffc107';
        if (mi < 40) return '#fd7e14';
        return '#dc3545';
    }

    function recencyColor(isoDate) {
        if (!isoDate) return '#6c757d';
        const days = (Date.now() - new Date(isoDate).getTime()) / 86400000;
        if (days < 30) return '#007bff';
        if (days < 90) return '#28a745';
        if (days < 180) return '#ffc107';
        if (days < 365) return '#fd7e14';
        return '#6c757d';
    }

    function getColorForRoute(route, index) {
        const mode = getColorBy();
        if (mode === 'distance') return distanceColor(route.distance || 0);
        if (mode === 'recency') return recencyColor(route.last_ridden);
        return getRouteColor(index);
    }

    function renderLegend() {
        const legendEl = byId('map-legend');
        if (!legendEl) return;

        const mode = getColorBy();
        // Show the legend as soon as a non-default color mode is chosen, even before
        // any routes are plotted on the map (Issue #376) — it previews what the colors mean.
        if (mode === 'default') {
            legendEl.style.display = 'none';
            return;
        }

        legendEl.style.display = '';
        const unit = window.getDistanceUnit ? window.getDistanceUnit() : 'mi';

        if (mode === 'distance') {
            legendEl.innerHTML = '<span class="me-2 fw-semibold">Distance:</span>'
                + ['#28a745|<10' + unit, '#ffc107|10–20' + unit, '#fd7e14|20–40' + unit, '#dc3545|>40' + unit]
                    .map(s => { const [c, l] = s.split('|'); return `<span class="me-2"><span class="legend-dot ${colorClass(c)}"></span> ${l}</span>`; }).join('');
        } else {
            legendEl.innerHTML = '<span class="me-2 fw-semibold">Last ridden:</span>'
                + ['#007bff|<30d', '#28a745|1–3mo', '#ffc107|3–6mo', '#fd7e14|6–12mo', '#6c757d|>1yr']
                    .map(s => { const [c, l] = s.split('|'); return `<span class="me-2"><span class="legend-dot ${colorClass(c)}"></span> ${l}</span>`; }).join('');
        }
    }

    function announce(message) {
        const liveRegion = byId('routes-live-region');
        if (liveRegion) {
            liveRegion.textContent = message;
        }
    }

    function recolorDisplayedRoutes() {
        let i = 0;
        state.displayedRoutes.forEach((mapObjects, routeId) => {
            const route = state.filteredRoutes.find(r => r.id === routeId) || state.routes.find(r => r.id === routeId);
            const color = route ? getColorForRoute(route, i) : getRouteColor(i);
            mapObjects.color = color;
            if (mapObjects.polyline) {
                const isSelected = routeId === state.selectedRouteId;
                mapObjects.polyline.setStyle({ color: isSelected ? color : '#999999' });
            }
            if (mapObjects.startMarker) {
                const icon = mapObjects.startMarker.getIcon();
                if (icon.options && icon.options.html) {
                    mapObjects.startMarker.setIcon(L.divIcon({
                        className: 'custom-marker',
                        html: `<div class="marker-dot-sm ${colorClass(color)}"></div>`,
                        iconSize: [12, 12]
                    }));
                }
            }
            if (mapObjects.endMarker) {
                mapObjects.endMarker.setIcon(L.divIcon({
                    className: 'custom-marker',
                    html: `<div class="marker-dot-sm ${colorClass(color)}"></div>`,
                    iconSize: [12, 12]
                }));
            }
            const card = document.querySelector(`[data-route-id="${routeId}"]`);
            if (card) {
                card.style.borderColor = color;
                const nameEl = card.querySelector('.route-name, h5, .card-title');
                if (nameEl) {
                    nameEl.style.color = contrastOnWhite(color) >= 4.5 ? color : '';
                }
            }
            i++;
        });
        if (state.selectedRouteId) selectRoute(state.selectedRouteId);
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
            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
                subdomains: 'abcd',
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

    function contrastOnWhite(hex) {
        const r = parseInt(hex.slice(1, 3), 16) / 255;
        const g = parseInt(hex.slice(3, 5), 16) / 255;
        const b = parseInt(hex.slice(5, 7), 16) / 255;
        const toLinear = c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        const L = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
        return 1.05 / (L + 0.05);
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
            renderLegend();

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
            const color = getColorForRoute(route, colorIndex);

            // Create polyline with default styling
            const polyline = L.polyline(coordinates, {
                color: color,
                weight: 5,
                opacity: 0.9
            }).addTo(state.mapInstance);

            // Bind popup
            polyline.bindPopup(`<strong>${escapeHtml(route.name)}</strong><br>${window.formatDistance(route.distance)}`);
            
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
                    html: `<div class="marker-dot-sm ${colorClass(color)}"></div>`,
                    iconSize: [12, 12]
                })
            }).addTo(state.mapInstance);
            startMarker.bindTooltip('Start', { permanent: false });

            const endMarker = L.marker(end, {
                icon: L.divIcon({
                    className: 'custom-marker',
                    html: `<div class="marker-dot-sm ${colorClass(color)}"></div>`,
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
                defaultWeight: 5,
                defaultOpacity: 0.9
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

            updateMapStatus();
            renderLegend();

            const card = document.querySelector(`[data-route-id="${routeId}"]`);
            if (card) {
                card.style.borderColor = color;
                card.style.borderWidth = '3px';

                const routeNameElement = card.querySelector('.route-name, h5, .card-title');
                if (routeNameElement) {
                    if (contrastOnWhite(color) >= 4.5) {
                        routeNameElement.style.color = color;
                    }
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

    function selectRoute(routeId) {
        state.displayedRoutes.forEach((mapObjects) => {
            if (mapObjects && mapObjects.polyline) {
                mapObjects.polyline.setStyle({
                    weight: mapObjects.defaultWeight || 4,
                    opacity: 0.3,
                    color: '#999999'
                });
                if (mapObjects.startMarker) {
                    mapObjects.startMarker.setZIndexOffset(0);
                    mapObjects.startMarker.setOpacity(0.3);
                }
                if (mapObjects.endMarker) {
                    mapObjects.endMarker.setZIndexOffset(0);
                    mapObjects.endMarker.setOpacity(0.3);
                }
                const tooltip = mapObjects.polyline.getTooltip();
                if (tooltip) {
                    const el = tooltip.getElement();
                    if (el) el.classList.remove('selected-route-tooltip');
                }
            }
        });

        const mapObjects = state.displayedRoutes.get(routeId);
        if (mapObjects && mapObjects.polyline) {
            mapObjects.polyline.bringToFront();
            if (mapObjects.startMarker) {
                mapObjects.startMarker.setZIndexOffset(1000);
                mapObjects.startMarker.setOpacity(1.0);
            }
            if (mapObjects.endMarker) {
                mapObjects.endMarker.setZIndexOffset(1000);
                mapObjects.endMarker.setOpacity(1.0);
            }
            mapObjects.polyline.setStyle({
                weight: 6,
                opacity: 1.0,
                color: mapObjects.color
            });
            const tooltip = mapObjects.polyline.getTooltip();
            if (tooltip) {
                const el = tooltip.getElement();
                if (el) el.classList.add('selected-route-tooltip');
            }
            state.selectedRouteId = routeId;
        }
    }

    async function fitAllRoutes() {
        if (!state.mapInstance) {
            initializeMap();
        }

        const missing = state.filteredRoutes.filter(r => !state.displayedRoutes.has(r.id));

        if (missing.length === 0 && state.displayedRoutes.size === 0) {
            announce('No routes to show on map');
            return;
        }

        const MAX_BULK = 20;
        const toLoad = missing.slice(0, MAX_BULK);
        if (toLoad.length > 0) {
            const statusEl = byId('map-status');
            if (statusEl) statusEl.textContent = `Loading ${toLoad.length} routes…`;

            const colorBase = state.displayedRoutes.size;
            await Promise.all(toLoad.map(async (route, i) => {
                const color = getColorForRoute(route, colorBase + i);
                try {
                    const response = await window.apiClient.getRouteDetails(route.id, route.type);
                    if (!response?.route?.coordinates?.length) return;
                    const coords = response.route.coordinates;

                    const polyline = L.polyline(coords, { color, weight: 5, opacity: 0.8 }).addTo(state.mapInstance);
                    polyline.bindPopup(`<strong>${escapeHtml(route.name)}</strong><br>${window.formatDistance(route.distance)}`);

                    const mkIcon = c => L.divIcon({
                        className: 'custom-marker',
                        html: `<div class="marker-dot-sm ${colorClass(c)}"></div>`,
                        iconSize: [12, 12]
                    });
                    const startMarker = L.marker(coords[0], { icon: mkIcon(color) }).addTo(state.mapInstance);
                    const endMarker   = L.marker(coords[coords.length - 1], { icon: mkIcon(color) }).addTo(state.mapInstance);

                    state.displayedRoutes.set(route.id, { polyline, startMarker, endMarker, color, defaultWeight: 5, defaultOpacity: 0.8 });

                    const card = document.querySelector(`[data-route-id="${route.id}"]`);
                    if (card) {
                        card.style.borderColor = color;
                        card.style.borderWidth = '3px';
                        const nameEl = card.querySelector('.route-name, h5, .card-title');
                        if (nameEl) {
                            if (contrastOnWhite(color) >= 4.5) {
                                nameEl.style.color = color;
                            }
                            nameEl.style.fontWeight = '700';
                        }
                    }
                } catch (e) {
                    console.warn('Fit All: failed to load route', route.name, e);
                }
            }));
            updateMapStatus();
        }

        if (state.displayedRoutes.size === 0) {
            announce('No route coordinates available');
            return;
        }

        const bounds = L.latLngBounds();
        state.displayedRoutes.forEach(mapObjects => {
            if (mapObjects.polyline) bounds.extend(mapObjects.polyline.getBounds());
        });

        if (bounds.isValid()) {
            state.mapInstance.fitBounds(bounds, { padding: [30, 30] });
            announce(`Fitted ${state.displayedRoutes.size} routes in view`);
            renderLegend();
        }
    }

    async function showAllRoutes() {
        clearAllRoutes();
        await fitAllRoutes();
        renderLegend();
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
        renderLegend();
        announce('Cleared all routes from map');
    }

    async function showUsesModal(route) {
        const modalEl = document.getElementById('route-uses-modal');
        if (!modalEl) return;

        const titleEl = document.getElementById('route-uses-modal-title');
        const bodyEl = document.getElementById('route-uses-modal-body');

        if (titleEl) titleEl.textContent = route.name;
        if (bodyEl) {
            bodyEl.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span class="ms-2 text-muted">Loading activities...</span>
                </div>`;
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();

        try {
            const response = await window.apiClient.getRouteDetails(route.id, route.type);
            const detail = response && response.route ? response.route : {};

            const activityIds = detail.activity_ids || [];
            const activityDates = detail.activity_dates || [];
            const activityNames = detail.activity_names || [];
            const count = Math.max(activityIds.length, activityDates.length, activityNames.length);

            if (count === 0) {
                bodyEl.innerHTML = '<p class="text-muted mb-0">No activity details available for this route.</p>';
                return;
            }

            let html = '<ul class="list-group list-group-flush">';
            for (let i = 0; i < count; i++) {
                const actId = activityIds[i] || null;
                const rawDate = activityDates[i] || '';
                const rawName = activityNames[i] || '';

                let dateStr = '';
                if (rawDate) {
                    const d = new Date(rawDate);
                    if (!isNaN(d.getTime())) {
                        dateStr = d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
                    } else {
                        dateStr = escapeHtml(rawDate);
                    }
                }

                const nameStr = rawName ? escapeHtml(rawName) : (dateStr || 'Activity ' + (i + 1));

                html += '<li class="list-group-item d-flex justify-content-between align-items-center"><div>';
                if (actId) {
                    html += `<a href="https://www.strava.com/activities/${escapeHtml(String(actId))}" target="_blank" rel="noopener noreferrer" class="text-decoration-none">`;
                    html += `<i class="bi bi-box-arrow-up-right me-1" aria-hidden="true"></i>${nameStr}</a>`;
                } else {
                    html += nameStr;
                }
                html += '</div>';
                if (dateStr && rawName) {
                    html += `<span class="text-muted small">${dateStr}</span>`;
                }
                html += '</li>';
            }
            html += '</ul>';
            bodyEl.innerHTML = html;
        } catch (err) {
            console.error('Failed to load activity details:', err);
            bodyEl.innerHTML = `<div class="alert alert-warning mb-0">
                <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
                Unable to load activity details. Please try again.
            </div>`;
        }
    }

    function navigateToRouteDetail(routeId, routeType) {
        const params = new URLSearchParams({ id: routeId });
        if (routeType) {
            params.set('type', routeType);
        }
        window.location.href = `/route-detail.html?${params.toString()}`;
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
                    <div class="flex-grow-1 me-2 min-w-0">
                        <h6 class="mb-1 text-truncate" title="${escapeHtml(route.name)}">
                            ${route.is_favorite ? '<i class="bi bi-star-fill text-warning"></i> ' : ''}
                            ${escapeHtml(route.name)}
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
        
        // Full mode for routes page — compact 2-line row
        const column = document.createElement('div');
        column.className = 'col-12';

        const card = document.createElement('div');
        card.className = 'card route-library-card';
        card.setAttribute('data-route-id', route.id);
        card.setAttribute('data-route-type', route.type || '');
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `${route.name} — ${window.formatDistance(route.distance)}`);
        card.style.transition = 'background-color 0.1s ease, border-color 0.15s ease';

        const isSelected = state.selectedForComparison.some(r => r.id === route.id);
        card.addEventListener('mouseenter', () => { card.style.backgroundColor = 'var(--bs-light, #f8f9fa)'; });
        card.addEventListener('mouseleave', () => { card.style.backgroundColor = ''; });

        const rawDifficulty = route.difficulty || 'Easy';
        const difficulty = rawDifficulty.charAt(0).toUpperCase() + rawDifficulty.slice(1).toLowerCase();
        const difficultyColors = {
            'Easy': 'bg-success', 'Moderate': 'bg-primary',
            'Hard': 'bg-warning text-dark', 'Very hard': 'bg-danger'
        };
        const difficultyIcons = {
            'Easy': 'bi-check-circle', 'Moderate': 'bi-dash-circle',
            'Hard': 'bi-exclamation-circle', 'Very hard': 'bi-exclamation-triangle-fill'
        };

        const favIcon   = route.is_favorite  ? '<i class="bi bi-star-fill text-warning me-1" aria-hidden="true"></i>' : '';
        const plusBadge = route.is_plus_route ? '<span class="badge bg-success-subtle text-success-emphasis me-1 badge-plus">PLUS</span>' : '';
        const diffBadge = `<span class="badge ${difficultyColors[difficulty]} flex-shrink-0 fs-07em" title="${difficulty}" aria-label="Difficulty: ${difficulty}"><i class="bi ${difficultyIcons[difficulty]}" aria-hidden="true"></i></span>`;

        // Direction badge for commute routes
        let dirBadge = '';
        if (route.direction === 'home_to_work') {
            dirBadge = '<span class="badge border border-info-subtle text-info-emphasis flex-shrink-0 ms-1 fs-065em" title="Direction: To Work" aria-label="Direction: To Work"><i class="bi bi-sunrise" aria-hidden="true"></i> To Work</span>';
        } else if (route.direction === 'work_to_home') {
            dirBadge = '<span class="badge border border-warning-subtle text-warning-emphasis flex-shrink-0 ms-1 fs-065em" title="Direction: To Home" aria-label="Direction: To Home"><i class="bi bi-sunset" aria-hidden="true"></i> To Home</span>';
        }

        // Terrain label for sub-line (extracted from name)
        const terrainMatch = route.name && route.name.match(/\((rolling|hilly)\)/i);
        const terrainLabel = terrainMatch
            ? `<span title="Terrain">${terrainMatch[1]}</span>`
            : '';

        card.innerHTML = `
            <div class="card-body py-2 px-3">
                <div class="d-flex align-items-center gap-2">
                    <div class="form-check compare-toggle flex-shrink-0">
                        <input class="form-check-input compare-checkbox mt-0" type="checkbox"
                               id="compare-${route.id}" data-route-id="${route.id}"
                               ${isSelected ? 'checked' : ''}
                               title="Compare">
                        <label class="form-check-label small text-muted" for="compare-${route.id}">Compare</label>
                    </div>
                    <span class="fw-semibold text-truncate flex-grow-1 route-name-link" title="${escapeHtml(route.name)}" data-route-link>
                        ${favIcon}${plusBadge}${escapeHtml(route.name)}
                    </span>
                    ${diffBadge}${dirBadge}
                </div>
                <div class="d-flex align-items-center gap-3 mt-1 text-muted route-meta-row">
                    <span title="Distance"><i class="bi bi-arrow-left-right" aria-hidden="true"></i> ${window.formatDistance(route.distance)}</span>
                    <span title="Duration"><i class="bi bi-clock" aria-hidden="true"></i> ${formatDuration(route.duration)}</span>
                    <span title="Elevation gain"><i class="bi bi-arrow-up" aria-hidden="true"></i> ${window.formatElevation(route.elevation_gain || route.elevation || 0)}</span>
                    ${terrainLabel}
                    <span class="uses-link uses-link-style" role="button" tabindex="0" title="View activities" data-route-uses
                          ><i class="bi bi-repeat" aria-hidden="true"></i> ${route.uses || 0}</span>
                    <span class="ms-auto text-primary cursor-pointer" data-route-link title="View details">
                        <i class="bi bi-arrow-right" aria-hidden="true"></i>
                    </span>
                </div>
            </div>
        `;

        card.style.cursor = 'pointer';
        // Moved off inline onclick="event.stopPropagation()" so CSP
        // script-src can drop 'unsafe-inline' — #475.
        card.querySelector('.compare-toggle').addEventListener('click', (e) => e.stopPropagation());
        function handleCardActivation(e) {
            if (e.target.closest('.compare-toggle') || e.target.closest('[data-route-link]') || e.target.closest('[data-route-uses]')) {
                return;
            }
            toggleRouteOnMap(route);
        }
        card.addEventListener('click', handleCardActivation);
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleCardActivation(e);
            }
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

        const usesLink = card.querySelector('[data-route-uses]');
        if (usesLink) {
            function handleUsesClick(e) {
                e.stopPropagation();
                e.preventDefault();
                showUsesModal(route);
            }
            usesLink.addEventListener('click', handleUsesClick);
            usesLink.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    handleUsesClick(e);
                }
            });
        }

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

    function syncCompareCheckboxes() {
        document.querySelectorAll('.compare-checkbox').forEach(cb => {
            cb.checked = state.selectedForComparison.some(r => String(r.id) === String(cb.dataset.routeId));
        });
    }

    function toggleRouteComparison(route) {
        const index = state.selectedForComparison.findIndex(r => r.id === route.id);

        if (index > -1) {
            state.selectedForComparison.splice(index, 1);
        } else {
            if (state.selectedForComparison.length >= 3) {
                if (window.showToast) {
                    window.showToast('You can compare up to 3 routes at a time. Please deselect one first.', 'warning');
                }
                syncCompareCheckboxes();
                return;
            }
            state.selectedForComparison.push(route);
        }

        syncCompareCheckboxes();
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
            compareBtn.style.cssText = 'bottom: 5rem; right: 1.5rem; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
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

        if (filters.commute === 'commute') {
            filtered = filtered.filter(route => route.type === 'commute');
        } else if (filters.commute === 'non-commute') {
            filtered = filtered.filter(route => route.type !== 'commute');
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
            const minKm = window.getUnitSystem() === 'imperial'
                ? window.milesToKm(Number(filters.min_distance))
                : Number(filters.min_distance);
            filtered = filtered.filter(route => Number(route.distance || 0) >= minKm);
        }

        if (filters.max_distance) {
            const maxKm = window.getUnitSystem() === 'imperial'
                ? window.milesToKm(Number(filters.max_distance))
                : Number(filters.max_distance);
            filtered = filtered.filter(route => Number(route.distance || 0) <= maxKm);
        }

        if (filters.date_range) {
            const cutoff = new Date(Date.now() - Number(filters.date_range) * 86400000);
            filtered = filtered.filter(route => {
                if (!route.last_ridden) return false;
                return new Date(route.last_ridden) >= cutoff;
            });
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
            case 'recent':
                filtered.sort((a, b) => (b.last_ridden || '').localeCompare(a.last_ridden || ''));
                break;
        }

        return filtered;
    }

    function renderSummary(count) {
        const summary = byId('results-summary');
        if (!summary) return;

        summary.className = count > 0 ? 'text-muted small mb-2' : 'text-warning small mb-2';
        summary.innerHTML = count > 0
            ? `<i class="bi bi-info-circle" aria-hidden="true"></i> Showing ${count} route${count === 1 ? '' : 's'}`
            : '<i class="bi bi-exclamation-triangle" aria-hidden="true"></i> No routes match the current filters';
    }

    function displayRoutesTimestamp(timestamp) {
        const summary = byId('results-summary');
        if (!summary || !timestamp) return;

        let timestampEl = summary.querySelector('.timestamp-display');
        if (!timestampEl) {
            timestampEl = document.createElement('small');
            timestampEl.className = 'timestamp-display ms-2';
            summary.appendChild(timestampEl);
        }

        timestampEl.setAttribute('data-timestamp', timestamp);
        timestampEl.setAttribute('title', window.formatAbsoluteTime(timestamp));
        timestampEl.innerHTML = `<i class="bi bi-clock"></i> Synced ${window.formatRelativeTime(timestamp)}`;
    }

    function renderRoutes(routes) {
        const container = byId('routes-container');
        if (!container) return;

        container.innerHTML = '';

        if (!routes.length) {
            renderSummary(0);
            announce('No routes found');
            const hasFilters = state.routes.length > 0;
            container.innerHTML = hasFilters
                ? window.renderEmptyState('No routes match your filters.', 'Try widening the distance range or clearing filters.', 'bi-funnel')
                : window.renderEmptyState('No rides synced yet.', 'Connect Strava and run analysis to populate your route library.', 'bi-bicycle');
            return;
        }

        const row = document.createElement('div');
        row.className = 'row g-1';

        routes.forEach(route => {
            row.appendChild(createRouteCard(route));
        });

        container.appendChild(row);
        renderSummary(routes.length);
        announce(`Showing ${routes.length} routes`);
    }

    function showSkeletonLoaders() {
        const container = byId('routes-container');
        if (!container) return;
        container.innerHTML = `
            <div class="row g-3">
                ${Array.from({length: 4}, () => `
                <div class="col-12">
                    <div class="skeleton-route-card" aria-busy="true" aria-label="Loading route">
                        <div class="skeleton skeleton-route-card-rank"></div>
                        <div class="skeleton skeleton-route-card-name"></div>
                        <div class="skeleton-route-card-metrics">
                            <div class="skeleton skeleton-route-card-metric"></div>
                            <div class="skeleton skeleton-route-card-metric"></div>
                            <div class="skeleton skeleton-route-card-metric"></div>
                        </div>
                    </div>
                </div>`).join('')}
            </div>
        `;
    }

    function showErrorState(message) {
        const container = byId('routes-container');
        if (!container) return;
        const safeMessage = document.createElement('span');
        safeMessage.textContent = message || 'Failed to load routes. Please try again.';
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-exclamation-triangle fs-4 me-2"></i>
                    <strong>Unable to Load Routes</strong>
                </div>
                <p class="mb-2" id="routes-error-message"></p>
                <button class="btn btn-primary btn-sm" id="routes-retry-btn">
                    <i class="bi bi-arrow-clockwise"></i> Retry
                </button>
            </div>
        `;
        byId('routes-error-message').appendChild(safeMessage);
        byId('routes-retry-btn').addEventListener('click', loadRoutes);
    }

    async function loadRoutes() {
        showSkeletonLoaders();

        try {
            const response = await window.apiClient.getRoutes();
            state.routes = Array.isArray(response.routes) ? response.routes : [];
            state.filteredRoutes = applyClientFilters(state.routes, getFilters());
            state.lastUpdated = response.timestamp;
            renderRoutes(state.filteredRoutes);

            if (response.timestamp) {
                displayRoutesTimestamp(response.timestamp);
            }
        } catch (error) {
            console.error('Failed to load routes:', error);
            showErrorState(error.message);
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
        updateMoreFiltersBadge();
        announce(`Applied ${preset} distance filter`);
    }

    // Count how many of the "More Filters" collapsible controls are set to a
    // non-default value, so the toggle button can show "More Filters (N)" (Issue #364).
    function countActiveFilters() {
        const f = getFilters();
        let count = 0;
        if (f.favorite) count++;
        if (f.commute) count++;
        if (f.sport_type) count++;
        if (f.difficulty) count++;
        if (f.min_distance) count++;
        if (f.max_distance) count++;
        if (f.date_range) count++;
        return count;
    }

    function updateMoreFiltersBadge() {
        const countEl = byId('more-filters-count');
        if (!countEl) return;
        const n = countActiveFilters();
        countEl.textContent = n > 0 ? ` (${n})` : '';
    }

    function applyFilters() {
        state.filteredRoutes = applyClientFilters(state.routes, getFilters());
        renderRoutes(state.filteredRoutes);
        updateMoreFiltersBadge();
    }

    function bindEvents() {
        // Auto-apply: dropdowns fire immediately on change
        ['filter-favorite', 'filter-commute', 'filter-sport-type', 'filter-difficulty', 'filter-date-range', 'sort-by'].forEach(id => {
            const el = byId(id);
            if (el) el.addEventListener('change', applyFilters);
        });

        // Auto-apply: text/number inputs debounced 300 ms
        let debounceTimer;
        const debouncedApply = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(applyFilters, 300);
        };
        ['search-query', 'filter-min-distance', 'filter-max-distance'].forEach(id => {
            const el = byId(id);
            if (el) el.addEventListener('input', debouncedApply);
        });

        // Preset buttons
        document.querySelectorAll('.preset-filter').forEach(button => {
            button.addEventListener('click', () => {
                const preset = button.getAttribute('data-preset');
                if (preset) applyPreset(preset);
            });
        });

        // Show All button
        const showAllBtn = byId('show-all-btn');
        if (showAllBtn) {
            showAllBtn.addEventListener('click', () => {
                showAllRoutes();
            });
        }

        // Color-by selector: re-color existing routes on the map
        const colorBySelect = byId('color-by');
        if (colorBySelect) {
            colorBySelect.addEventListener('change', () => {
                recolorDisplayedRoutes();
                renderLegend();
            });
        }

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

    async function loadSavedPlans() {
        const section = byId('saved-plans-section');
        const list = byId('saved-plans-list');
        const titleEl = byId('saved-plans-title');
        const toggleBtn = byId('toggle-plans-btn');
        const card = byId('saved-plans-card');
        if (!section || !list) return;

        try {
            const response = await window.apiClient.getPlans();
            const plans = Array.isArray(response.plans) ? response.plans : [];

            if (titleEl) titleEl.textContent = `Saved Plans (${plans.length})`;

            if (!plans.length) {
                // Persistent stub entry point: always visible, muted, disabled toggle
                // when there is nothing to expand yet (Issue #372b).
                if (card) card.classList.remove('saved-plans-active');
                if (toggleBtn) {
                    toggleBtn.disabled = true;
                    toggleBtn.setAttribute('aria-disabled', 'true');
                }
                list.innerHTML = '';
                return;
            }

            if (card) card.classList.add('saved-plans-active');
            if (toggleBtn) {
                toggleBtn.disabled = false;
                toggleBtn.removeAttribute('aria-disabled');
            }

            list.innerHTML = plans.map(plan => {
                const date = plan.created_at
                    ? new Date(plan.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    : '';
                const dist = plan.distance ? window.formatDistance(plan.distance) : '';
                const safeName = escapeHtml(plan.route_name || plan.route_id);
                const safeId = escapeHtml(plan.id);
                return `<div class="d-flex align-items-center justify-content-between py-1 border-bottom" data-plan-id="${safeId}">
                    <div class="d-flex align-items-center gap-2 flex-grow-1 overflow-hidden">
                        <a href="/route-detail.html?id=${encodeURIComponent(plan.route_id)}${plan.route_type ? '&type=' + encodeURIComponent(plan.route_type) : ''}"
                           class="text-decoration-none text-truncate fw-medium">${safeName}</a>
                        ${dist ? `<span class="text-muted small">${dist}</span>` : ''}
                        ${plan.note ? `<span class="text-muted small fst-italic text-truncate">${escapeHtml(plan.note)}</span>` : ''}
                    </div>
                    <div class="d-flex align-items-center gap-2 flex-shrink-0">
                        <span class="text-muted small">${date}</span>
                        <button class="btn btn-sm btn-outline-danger py-0 px-1 delete-plan-btn" data-plan-id="${safeId}" title="Remove plan">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                </div>`;
            }).join('');

            list.querySelectorAll('.delete-plan-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    const planId = btn.dataset.planId;
                    btn.disabled = true;
                    try {
                        await window.apiClient.deletePlan(planId);
                        loadSavedPlans();
                    } catch (err) {
                        btn.disabled = false;
                    }
                });
            });
        } catch (err) {
            console.error('Failed to load saved plans:', err);
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
            loadSavedPlans();
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

/**
 * Unit-aware filter labels/presets (moved from inline <script> in
 * routes.html so CSP script-src can drop 'unsafe-inline' — #475).
 */
document.addEventListener('DOMContentLoaded', function() {
    const unitSystem = window.getUnitSystem ? window.getUnitSystem() : 'imperial';
    const distanceUnit = window.getDistanceUnit ? window.getDistanceUnit() : 'mi';

    const minLabel = document.getElementById('filter-min-distance-label');
    const maxLabel = document.getElementById('filter-max-distance-label');
    if (minLabel) minLabel.textContent = `Min (${distanceUnit})`;
    if (maxLabel) maxLabel.textContent = `Max (${distanceUnit})`;

    const presetButtons = document.querySelectorAll('.preset-filter');
    presetButtons.forEach(btn => {
        const preset = btn.getAttribute('data-preset');
        const icon = btn.querySelector('i');
        const iconHtml = icon ? icon.outerHTML + ' ' : '';
        if (preset === 'short') {
            btn.innerHTML = `${iconHtml}Short (<${unitSystem === 'imperial' ? '10mi' : '16km'})`;
        } else if (preset === 'medium') {
            btn.innerHTML = `${iconHtml}Medium (${unitSystem === 'imperial' ? '10–20mi' : '16–32km'})`;
        } else if (preset === 'long') {
            btn.innerHTML = `${iconHtml}Long (>${unitSystem === 'imperial' ? '20mi' : '32km'})`;
        }
    });
});
