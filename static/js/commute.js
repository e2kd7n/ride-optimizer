/**
 * Commute page logic
 * Displays current conditions and route recommendations
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadCommutePage();
    
    // Refresh every 10 minutes
    setInterval(loadCommutePage, 10 * 60 * 1000);
});

/**
 * Load all commute page data
 */
async function loadCommutePage() {
    await Promise.all([
        loadCurrentConditions(),
        loadRecommendation()
    ]);
}

/**
 * Load and display current weather conditions
 */
async function loadCurrentConditions() {
    const container = document.getElementById('current-conditions');
    
    try {
        const weather = await window.apiClient.getWeather();
        
        if (!weather || !weather.current) {
            container.innerHTML = '<p class="text-muted">Weather data unavailable</p>';
            return;
        }
        
        const current = weather.current;
        const comfortClass = getComfortClass(current.comfort_score);
        const comfortText = getComfortText(current.comfort_score);
        
        const html = `
            <div class="row">
                <div class="col-md-4">
                    <div class="text-center mb-3">
                        <i class="bi bi-thermometer-half weather-icon"></i>
                        <div class="temperature-display">${current.temperature}°F</div>
                        <small class="text-muted">Feels like ${current.feels_like}°F</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="mb-3">
                        <h6>Comfort Score</h6>
                        <div class="progress" style="height: 30px;">
                            <div class="progress-bar ${comfortClass}" role="progressbar" 
                                 style="width: ${current.comfort_score}%;" 
                                 aria-valuenow="${current.comfort_score}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                                ${current.comfort_score}/100
                            </div>
                        </div>
                        <small class="text-muted">${comfortText}</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="mb-2">
                        <i class="bi bi-wind"></i> <strong>Wind:</strong> ${current.wind_speed} mph ${current.wind_direction}
                    </div>
                    <div class="mb-2">
                        <i class="bi bi-droplet"></i> <strong>Humidity:</strong> ${current.humidity}%
                    </div>
                    ${current.precipitation_probability ? `
                        <div class="mb-2">
                            <i class="bi bi-cloud-rain"></i> <strong>Rain:</strong> ${current.precipitation_probability}%
                        </div>
                    ` : ''}
                    <div class="mb-2">
                        <i class="bi bi-info-circle"></i> <strong>Conditions:</strong> ${current.description}
                    </div>
                </div>
            </div>
            ${weather.forecast && weather.forecast.length > 0 ? renderForecast(weather.forecast) : ''}
        `;
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load conditions:', error);
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <i class="bi bi-exclamation-triangle"></i>
                Unable to load current conditions. Please try again later.
            </div>
        `;
    }
}

/**
 * Render forecast section
 */
function renderForecast(forecast) {
    const next3Hours = forecast.slice(0, 3);
    
    return `
        <div class="mt-4">
            <h6>Next 3 Hours</h6>
            <div class="row">
                ${next3Hours.map(hour => `
                    <div class="col-4">
                        <div class="text-center p-2 border rounded">
                            <small class="text-muted">${formatHour(hour.time)}</small>
                            <div class="fs-5">${hour.temperature}°F</div>
                            <small>${hour.description}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Load and display route recommendation
 */
async function loadRecommendation() {
    const recContainer = document.getElementById('recommendation');
    const altContainer = document.getElementById('alternatives');
    
    try {
        const data = await window.apiClient.getRecommendation();
        
        if (!data || !data.recommended_route) {
            recContainer.innerHTML = '<p class="text-muted">No recommendation available at this time</p>';
            altContainer.innerHTML = '<p class="text-muted">No alternative routes available</p>';
            return;
        }
        
        // Render recommended route
        const route = data.recommended_route;
        const scoreClass = getScoreClass(data.score);
        const scoreText = getScoreText(data.score);
        
        const recHtml = `
            <div class="row">
                <div class="col-md-8">
                    <h4 class="mb-3">${escapeHtml(route.name)}</h4>
                    <div class="mb-3">
                        <span class="badge ${scoreClass} fs-5">${data.score}/100</span>
                        <span class="ms-2 fs-6">${scoreText}</span>
                    </div>
                    <p class="text-muted">${data.recommendation}</p>
                    
                    ${data.factors && data.factors.length > 0 ? `
                        <div class="mt-3">
                            <h6>Key Factors:</h6>
                            <ul>
                                ${data.factors.map(f => `<li>${f}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title">Route Details</h6>
                            <div class="mb-2">
                                <i class="bi bi-arrow-left-right"></i> 
                                <strong>Distance:</strong> ${route.distance} mi
                            </div>
                            <div class="mb-2">
                                <i class="bi bi-graph-up"></i> 
                                <strong>Elevation:</strong> ${route.elevation_gain} ft
                            </div>
                            ${route.sport_type ? `
                                <div class="mb-2">
                                    <i class="bi bi-bicycle"></i> 
                                    <strong>Type:</strong> ${route.sport_type}
                                </div>
                            ` : ''}
                            ${route.uses ? `
                                <div class="mb-2">
                                    <i class="bi bi-clock-history"></i> 
                                    <strong>Times Used:</strong> ${route.uses}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="d-grid gap-2 mt-3">
                        <a href="/routes.html?id=${route.id}" class="btn btn-primary">
                            <i class="bi bi-eye"></i> View Full Details
                        </a>
                    </div>
                </div>
            </div>
        `;
        
        recContainer.innerHTML = recHtml;
        
        // Render alternative routes
        if (data.alternatives && data.alternatives.length > 0) {
            const altHtml = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Route</th>
                                <th>Score</th>
                                <th>Distance</th>
                                <th>Elevation</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.alternatives.map(alt => `
                                <tr>
                                    <td>${escapeHtml(alt.route.name)}</td>
                                    <td>
                                        <span class="badge ${getScoreClass(alt.score)}">${alt.score}/100</span>
                                    </td>
                                    <td>${alt.route.distance} mi</td>
                                    <td>${alt.route.elevation_gain} ft</td>
                                    <td>
                                        <a href="/routes.html?id=${alt.route.id}" class="btn btn-sm btn-outline-primary">
                                            View
                                        </a>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            altContainer.innerHTML = altHtml;
        } else {
            altContainer.innerHTML = '<p class="text-muted">No alternative routes available</p>';
        }
        
    } catch (error) {
        console.error('Failed to load recommendation:', error);
        recContainer.innerHTML = `
            <div class="alert alert-info" role="alert">
                <i class="bi bi-info-circle"></i>
                Unable to generate recommendation. Please check back later.
            </div>
        `;
        altContainer.innerHTML = '';
    }
}

/**
 * Get comfort score class
 */
function getComfortClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-info';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}

/**
 * Get comfort score text
 */
function getComfortText(score) {
    if (score >= 80) return 'Excellent riding conditions';
    if (score >= 60) return 'Good riding conditions';
    if (score >= 40) return 'Fair riding conditions';
    return 'Challenging riding conditions';
}

/**
 * Get recommendation score class
 */
function getScoreClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-primary';
    if (score >= 40) return 'bg-warning';
    return 'bg-danger';
}

/**
 * Get recommendation score text
 */
function getScoreText(score) {
    if (score >= 80) return 'Highly Recommended';
    if (score >= 60) return 'Recommended';
    if (score >= 40) return 'Acceptable';
    return 'Not Recommended';
}

/**
 * Format hour from ISO timestamp
 */
function formatHour(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Made with Bob
