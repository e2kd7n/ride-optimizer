/**
 * Dashboard page logic
 * Loads and displays system status, weather, recommendations, and routes
 */

// Initialize dashboard on page load
// NOTE: Initialization is handled by inline script in index.html
// document.addEventListener('DOMContentLoaded', async () => {
//     await loadDashboard();
//
//     // Refresh data every 5 minutes
//     setInterval(loadDashboard, 5 * 60 * 1000);
// });

/**
 * Load all dashboard data
 */
async function loadDashboard() {
    await Promise.all([
        loadSystemStatus(),
        loadWeather(),
        loadRecommendation(),
        loadRouteStats()
    ]);
}

/**
 * Load and display system status
 */
async function loadSystemStatus() {
    const container = document.getElementById('system-status');
    
    try {
        const status = await window.apiClient.getStatus();
        
        const html = `
            <div class="row">
                <div class="col-md-3">
                    <div class="text-center">
                        <i class="bi bi-hdd fs-3 ${status.storage_ok ? 'text-success' : 'text-danger'}"></i>
                        <div class="mt-2">
                            <strong>Storage</strong><br>
                            <small class="text-muted">${status.storage_used_mb}MB / ${status.storage_total_mb}MB</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <i class="bi bi-clock-history fs-3 text-info"></i>
                        <div class="mt-2">
                            <strong>Uptime</strong><br>
                            <small class="text-muted">${formatUptime(status.uptime_seconds)}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <i class="bi bi-calendar-check fs-3 text-primary"></i>
                        <div class="mt-2">
                            <strong>Last Update</strong><br>
                            <small class="text-muted">${formatTimestamp(status.last_update)}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="text-center">
                        <i class="bi bi-check-circle fs-3 text-success"></i>
                        <div class="mt-2">
                            <strong>Status</strong><br>
                            <small class="text-muted">Operational</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load system status:', error);
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load system status. Please try again later.
            </div>
        `;
    }
}

/**
 * Load and display weather data
 */
async function loadWeather() {
    const container = document.getElementById('weather-data');
    
    try {
        const weather = await window.apiClient.getWeather();
        
        if (!weather || !weather.current) {
            container.innerHTML = '<p class="text-muted">No weather data available</p>';
            return;
        }
        
        const current = weather.current;
        const comfortClass = getComfortClass(current.comfort_score);
        
        const html = `
            <div class="row">
                <div class="col-md-6">
                    <div class="d-flex align-items-center mb-3">
                        <i class="bi bi-thermometer-half fs-1 me-3"></i>
                        <div>
                            <h3 class="mb-0">${current.temperature}°F</h3>
                            <small class="text-muted">Feels like ${current.feels_like}°F</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-2">
                        <strong>Comfort Score:</strong>
                        <span class="badge ${comfortClass} ms-2">${current.comfort_score}/100</span>
                    </div>
                    <div class="mb-2">
                        <i class="bi bi-wind"></i> Wind: ${current.wind_speed} mph ${current.wind_direction}
                    </div>
                    <div class="mb-2">
                        <i class="bi bi-droplet"></i> Humidity: ${current.humidity}%
                    </div>
                    ${current.precipitation_probability ? `
                        <div class="mb-2">
                            <i class="bi bi-cloud-rain"></i> Rain: ${current.precipitation_probability}%
                        </div>
                    ` : ''}
                </div>
            </div>
            <div class="mt-3">
                <small class="text-muted">
                    <i class="bi bi-info-circle"></i> ${current.description}
                </small>
            </div>
        `;
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load weather:', error);
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Weather data unavailable. Check back later.
            </div>
        `;
    }
}

/**
 * Load and display commute recommendation
 */
async function loadRecommendation() {
    const container = document.getElementById('commute-recommendation');
    
    try {
        const rec = await window.apiClient.getRecommendation();
        
        if (!rec || !rec.recommended_route) {
            container.innerHTML = '<p class="text-muted">No recommendation available</p>';
            return;
        }
        
        const route = rec.recommended_route;
        const scoreClass = getScoreClass(rec.score);
        
        const html = `
            <div class="mb-3">
                <h5 class="mb-2">${route.name}</h5>
                <div class="mb-2">
                    <span class="badge ${scoreClass} fs-6">${rec.score}/100</span>
                    <span class="ms-2 text-muted">${rec.recommendation}</span>
                </div>
            </div>
            <div class="row">
                <div class="col-6">
                    <small class="text-muted">Distance</small><br>
                    <strong>${route.distance} mi</strong>
                </div>
                <div class="col-6">
                    <small class="text-muted">Elevation</small><br>
                    <strong>${route.elevation_gain} ft</strong>
                </div>
            </div>
            ${rec.factors && rec.factors.length > 0 ? `
                <div class="mt-3">
                    <small class="text-muted">Factors:</small>
                    <ul class="small mb-0">
                        ${rec.factors.map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            <div class="mt-3">
                <a href="/commute.html" class="btn btn-primary btn-sm">
                    <i class="bi bi-arrow-right"></i> View Details
                </a>
            </div>
        `;
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load recommendation:', error);
        container.innerHTML = `
            <div class="alert alert-info" role="alert">
                <i class="bi bi-info-circle"></i>
                No commute recommendation available.
            </div>
        `;
    }
}

/**
 * Load and display route statistics
 */
async function loadRouteStats() {
    const container = document.getElementById('route-stats');
    const recentContainer = document.getElementById('recent-routes');
    
    try {
        const data = await window.apiClient.getRoutes();
        const routes = data.routes || [];
        
        // Calculate statistics
        const totalRoutes = routes.length;
        const favoriteRoutes = routes.filter(r => r.is_favorite).length;
        const totalDistance = routes.reduce((sum, r) => sum + (r.distance || 0), 0);
        const avgDistance = totalRoutes > 0 ? (totalDistance / totalRoutes).toFixed(1) : 0;
        
        // Stats HTML
        const statsHtml = `
            <div class="row text-center">
                <div class="col-md-3">
                    <div class="stat-card">
                        <i class="bi bi-map fs-2 text-primary"></i>
                        <h3 class="mt-2">${totalRoutes}</h3>
                        <small class="text-muted">Total Routes</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <i class="bi bi-star-fill fs-2 text-warning"></i>
                        <h3 class="mt-2">${favoriteRoutes}</h3>
                        <small class="text-muted">Favorites</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <i class="bi bi-speedometer2 fs-2 text-success"></i>
                        <h3 class="mt-2">${totalDistance.toFixed(0)}</h3>
                        <small class="text-muted">Total Miles</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <i class="bi bi-graph-up fs-2 text-info"></i>
                        <h3 class="mt-2">${avgDistance}</h3>
                        <small class="text-muted">Avg Distance</small>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = statsHtml;
        
        // Recent routes (top 5)
        const recentRoutes = routes.slice(0, 5);
        
        if (recentRoutes.length === 0) {
            recentContainer.innerHTML = '<p class="text-muted">No routes available</p>';
            return;
        }
        
        const routesHtml = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Route</th>
                            <th>Distance</th>
                            <th>Elevation</th>
                            <th>Type</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${recentRoutes.map(route => `
                            <tr>
                                <td>
                                    ${route.is_favorite ? '<i class="bi bi-star-fill text-warning"></i> ' : ''}
                                    ${route.name}
                                </td>
                                <td>${route.distance} mi</td>
                                <td>${route.elevation_gain} ft</td>
                                <td><span class="badge bg-secondary">${route.sport_type || 'Ride'}</span></td>
                                <td>
                                    <a href="/routes.html?id=${route.id}" class="btn btn-sm btn-outline-primary">
                                        View
                                    </a>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div class="text-center mt-3">
                <a href="/routes.html" class="btn btn-primary">
                    View All Routes <i class="bi bi-arrow-right"></i>
                </a>
            </div>
        `;
        
        recentContainer.innerHTML = routesHtml;
    } catch (error) {
        console.error('Failed to load route stats:', error);
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                Failed to load route statistics.
            </div>
        `;
        recentContainer.innerHTML = '';
    }
}

/**
 * Utility: Format uptime seconds to human readable
 */
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

/**
 * Utility: Format ISO timestamp to relative time
 */
function formatTimestamp(isoString) {
    if (!isoString) return 'Never';
    
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

/**
 * Utility: Get Bootstrap class for comfort score
 */
function getComfortClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-info';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}

/**
 * Utility: Get Bootstrap class for recommendation score
 */
function getScoreClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-primary';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}

// Made with Bob
