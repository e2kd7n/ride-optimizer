/**
 * compare.js - Side-by-side route comparison page
 */

        (function() {
            function byId(id) {
                return document.getElementById(id);
            }

            function announce(message) {
                const liveRegion = byId('comparison-live-region');
                if (liveRegion) {
                    liveRegion.textContent = message;
                }
            }

            function getRouteIds() {
                const params = new URLSearchParams(window.location.search);
                const ids = params.get('ids');
                return ids ? ids.split(',') : [];
            }

            function getDifficultyBadge(difficulty) {
                const colors = {
                    'Easy': 'success',
                    'Moderate': 'warning',
                    'Hard': 'danger',
                    'Very hard': 'danger'
                };
                return `<span class="badge bg-${colors[difficulty] || 'secondary'}">${escapeHtml(difficulty || 'N/A')}</span>`;
            }

            function renderMap(containerId, coordinates) {
                const mapElement = byId(containerId);
                if (!mapElement || !Array.isArray(coordinates) || !coordinates.length) {
                    return;
                }

                const map = L.map(containerId);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19
                }).addTo(map);

                const polyline = L.polyline(coordinates, {
                    color: '#007bff',
                    weight: 4,
                    opacity: 0.8
                }).addTo(map);

                // Zoom to show entire route with smooth animation (Issue #117)
                map.fitBounds(polyline.getBounds(), {
                    padding: [30, 30],
                    animate: true,
                    duration: 0.5
                });
            }

            function findBestValue(routes, key, preferLower = true) {
                const values = routes.map(r => Number(r[key] || 0));
                return preferLower ? Math.min(...values) : Math.max(...values);
            }

            function renderComparison(routes) {
                if (!routes || routes.length === 0) {
                    byId('comparison-content').innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i> No routes selected for comparison.
                        </div>
                    `;
                    return;
                }

                // Find best values for highlighting
                const bestDistance = findBestValue(routes, 'distance', true);
                const bestDuration = findBestValue(routes, 'duration', true);
                const bestElevation = findBestValue(routes.map(r => ({...r, elevation_gain: r.elevation_gain ?? r.elevation})), 'elevation_gain', true);
                const bestSpeed = findBestValue(routes, 'average_speed', false);

                const content = `
                    <div class="row g-4">
                        ${routes.map((route, index) => `
                            <div class="col-12 col-md-${routes.length === 2 ? '6' : '4'}">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h3 class="h5 mb-3">${escapeHtml(route.name)}</h3>
                                        <div id="map-${index}" class="route-map-small"></div>
                                        
                                        <div class="row g-2 mb-3">
                                            <div class="col-6">
                                                <div class="text-center p-2 border rounded">
                                                    <div class="small text-muted">Distance</div>
                                                    <div class="metric-highlight">${window.formatDistance(route.distance)}</div>
                                                    ${Number(route.distance) === bestDistance ? '<div class="winner-badge mt-1">Shortest</div>' : ''}
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="text-center p-2 border rounded">
                                                    <div class="small text-muted">Duration</div>
                                                    <div class="metric-highlight">${formatDuration(route.duration)}</div>
                                                    ${Number(route.duration) === bestDuration ? '<div class="winner-badge mt-1">Fastest</div>' : ''}
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="text-center p-2 border rounded">
                                                    <div class="small text-muted">Elevation</div>
                                                    <div class="metric-highlight">${window.formatElevation(route.elevation_gain || route.elevation)}</div>
                                                    ${Number(route.elevation_gain || route.elevation) === bestElevation ? '<div class="winner-badge mt-1">Flattest</div>' : ''}
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="text-center p-2 border rounded">
                                                    <div class="small text-muted">Avg Speed</div>
                                                    <div class="metric-highlight">${window.formatSpeed(route.average_speed || 0)}</div>
                                                    ${Number(route.average_speed) === bestSpeed ? '<div class="winner-badge mt-1">Fastest</div>' : ''}
                                                </div>
                                            </div>
                                        </div>

                                        <div class="mb-2">
                                            <strong>Difficulty:</strong> ${getDifficultyBadge(route.difficulty)}
                                        </div>
                                        <div class="mb-2">
                                            <strong>Type:</strong> ${route.sport_type || route.type || 'Ride'}
                                        </div>
                                        <div class="mb-2">
                                            <strong>Uses:</strong> ${route.uses || route.frequency || 0} times
                                        </div>
                                        
                                        <a href="/route-detail.html?id=${route.id}" class="btn btn-outline-primary btn-sm w-100 mt-3">
                                            <i class="bi bi-eye"></i> View Details
                                        </a>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <div class="card mt-4">
                        <div class="card-body">
                            <h3 class="h5 mb-3">Detailed Comparison</h3>
                            <div class="table-responsive comparison-table">
                                <table class="table table-bordered table-hover mb-0">
                                    <thead>
                                        <tr>
                                            <th>Metric</th>
                                            ${routes.map(r => `<th>${escapeHtml(r.name)}</th>`).join('')}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Distance</td>
                                            ${routes.map(r => `<td>${window.formatDistance(r.distance)}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Duration</td>
                                            ${routes.map(r => `<td>${formatDuration(r.duration)}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Elevation Gain</td>
                                            ${routes.map(r => `<td>${window.formatElevation(r.elevation_gain || r.elevation)}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Average Speed</td>
                                            ${routes.map(r => `<td>${window.formatSpeed(r.average_speed || 0)}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Difficulty</td>
                                            ${routes.map(r => `<td>${getDifficultyBadge(r.difficulty)}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Sport Type</td>
                                            ${routes.map(r => `<td>${r.sport_type || r.type || 'Ride'}</td>`).join('')}
                                        </tr>
                                        <tr>
                                            <td>Times Used</td>
                                            ${routes.map(r => `<td>${r.uses || r.frequency || 0}</td>`).join('')}
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;

                byId('comparison-content').innerHTML = content;

                // innerHTML assignment above is synchronous, so map containers already exist
                routes.forEach((route, index) => {
                    if (route.coordinates) {
                        renderMap(`map-${index}`, route.coordinates);
                    }
                });

                announce(`Comparing ${routes.length} routes`);
            }

            async function loadComparison() {
                const routeIds = getRouteIds();
                
                if (routeIds.length === 0) {
                    byId('comparison-content').innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i> No routes selected for comparison.
                            <a href="/routes.html" class="alert-link">Go back to routes</a>
                        </div>
                    `;
                    return;
                }

                try {
                    // Fetch full route details (includes coordinates for maps)
                    const detailResponses = await Promise.all(
                        routeIds.map(id => window.apiClient.getRouteDetails(id).catch(() => null))
                    );
                    const selectedRoutes = detailResponses
                        .filter(r => r && r.route)
                        .map(r => r.route);

                    if (selectedRoutes.length === 0) {
                        throw new Error('Selected routes not found');
                    }

                    renderComparison(selectedRoutes);
                } catch (error) {
                    console.error('Failed to load comparison:', error);
                    byId('comparison-content').innerHTML = `
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-triangle"></i> Failed to load route comparison.
                        </div>
                    `;
                    announce('Failed to load comparison');
                }
            }

            document.addEventListener('DOMContentLoaded', loadComparison);
        })();
