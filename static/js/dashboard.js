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
    // Fetch workout data first so weather pill and workout strip can render
    await fetchTodayWorkout();

    await Promise.all([
        loadWeather(),
        loadWorkoutStrip(),
        loadRecommendation(),
        loadRouteStatus(),
        loadCommuteWindows(),
        loadHourlyForecast()
    ]);
}

/**
 * Workout type badge class mapping for TrainerRoad integration.
 */
const WORKOUT_TYPE_BADGES = {
    'Endurance':  'bg-info text-dark',
    'Tempo':      'bg-primary',
    'Threshold':  'bg-warning text-dark',
    'VO2Max':     'bg-danger',
    'Sprint':     'bg-danger',
    'Anaerobic':  'bg-danger',
    'Recovery':   'bg-success',
};

/**
 * Shared workout data cache — fetched once per dashboard load,
 * used by both the workout strip and the weather banner pill.
 */
let _todayWorkout = null;
let _trainerRoadStatus = null;

async function fetchTodayWorkout() {
    try {
        _trainerRoadStatus = await window.apiClient.getTrainerRoadStatus();
        if (!_trainerRoadStatus.connected) {
            _todayWorkout = null;
            return;
        }
        const data = await window.apiClient.getTrainerRoadToday();
        _todayWorkout = data.has_workout ? data.workout : null;
    } catch (e) {
        _todayWorkout = null;
        _trainerRoadStatus = null;
    }
}

function isWorkoutDataStale() {
    if (!_trainerRoadStatus || !_trainerRoadStatus.last_sync) return false;
    const hoursSinceSync = (Date.now() - new Date(_trainerRoadStatus.last_sync)) / 3600000;
    return hoursSinceSync > 24;
}

/**
 * Load workout strip between weather banner and hero card.
 * Only renders when TrainerRoad is configured and a workout exists today.
 */
async function loadWorkoutStrip() {
    const container = document.getElementById('workout-strip');
    if (!container) return;

    if (!_todayWorkout) {
        container.style.display = 'none';
        return;
    }

    try {
        const w = _todayWorkout;
        const esc = window.escapeHtml;
        const typeBadgeClass = WORKOUT_TYPE_BADGES[w.type] || 'bg-secondary';

        const fitScore = w.fit_score || 0;
        const fitClass = w.indoor_fallback ? 'fit-poor'
                       : fitScore >= 0.7 ? 'fit-good'
                       : fitScore >= 0.4 ? 'fit-moderate'
                       : 'fit-poor';
        const fitLabel = w.indoor_fallback ? 'Indoor'
                       : fitScore >= 0.7 ? 'Good fit'
                       : fitScore >= 0.4 ? 'Moderate fit'
                       : fitScore > 0 ? 'Poor fit' : '';
        const fitIcon = w.indoor_fallback ? 'bi-house-door'
                      : fitScore >= 0.7 ? 'bi-check-circle'
                      : fitScore >= 0.4 ? 'bi-dash-circle'
                      : 'bi-x-circle';

        const noteText = w.notes && w.notes.length > 0 ? esc(w.notes[0]) : '';
        const stale = isWorkoutDataStale();
        const staleBadge = stale
            ? '<span class="badge bg-warning text-dark ms-2"><i class="bi bi-exclamation-triangle" aria-hidden="true"></i> Stale</span>'
            : '';

        container.innerHTML = `
            <div class="workout-strip">
                <i class="bi bi-lightning-charge workout-strip-icon" aria-hidden="true"></i>
                <div>
                    <div class="workout-strip-name">${esc(w.name)}${staleBadge}</div>
                    <div class="workout-strip-meta">
                        <span class="badge ${typeBadgeClass}">${esc(w.type || 'Workout')}</span>
                        ${w.duration_minutes ? `<span><i class="bi bi-clock" aria-hidden="true"></i> ${w.duration_minutes} min</span>` : ''}
                        ${w.tss ? `<span><i class="bi bi-speedometer2" aria-hidden="true"></i> TSS ${w.tss}</span>` : ''}
                    </div>
                </div>
                ${noteText ? `<div class="workout-strip-note">${noteText}</div>` : ''}
                ${fitLabel ? `<span class="workout-fit-badge ${fitClass}"><i class="bi ${fitIcon}" aria-hidden="true"></i> ${fitLabel}</span>` : ''}
            </div>`;
        container.style.display = '';
    } catch (error) {
        console.warn('Workout strip unavailable:', error);
        container.style.display = 'none';
    }
}

/**
 * Build workout fit row HTML for the hero card (Design B §2B).
 * Inline annotation with burnt-orange left border, not a standalone alert.
 */
function renderWorkoutFitRow(rec) {
    const workoutFit = rec.workout_fit;
    if (!workoutFit) return '';

    const esc = window.escapeHtml;
    const fitScore = workoutFit.fit_score || 0;
    const isIndoor = workoutFit.indoor_fallback;

    const WORKOUT_TYPE_ICONS = {
        'Endurance': 'bi-heart-pulse',
        'Tempo':     'bi-speedometer',
        'Threshold': 'bi-lightning',
        'VO2Max':    'bi-fire',
        'Sprint':    'bi-lightning-charge',
        'Anaerobic': 'bi-lightning-charge-fill',
        'Recovery':  'bi-heart',
    };

    const rating = fitScore >= 0.7 ? 'Good'
                 : fitScore >= 0.4 ? 'Moderate' : 'Poor';
    const ratingClass = rating === 'Good' ? 'bg-success-subtle text-success'
                      : rating === 'Moderate' ? 'bg-warning-subtle text-dark'
                      : 'bg-danger-subtle text-danger';
    const typeIcon = WORKOUT_TYPE_ICONS[workoutFit.workout_type] || 'bi-activity';

    const wName = esc(workoutFit.workout_name || 'Workout');
    const wType = esc(workoutFit.workout_type || '');
    const reasons = (workoutFit.fit_reasons || []).map(r => esc(r)).join(' · ');

    let html = `
        <div class="workout-fit-row" role="status">
            <div class="workout-fit-row-header">
                <i class="bi ${typeIcon}" aria-hidden="true"></i>
                <span class="fw-semibold">Workout fit:</span>
                <span>${wName} (${wType})</span>
                <span class="badge ${ratingClass} ms-auto">${rating}</span>
            </div>
            ${reasons ? `<div class="workout-fit-row-reasons">${reasons}</div>` : ''}`;

    if (isIndoor) {
        const indoorReason = workoutFit.indoor_reason
            ? esc(workoutFit.indoor_reason) + '.'
            : `${wType} efforts need controlled conditions for consistent target power.`;
        html += `
            <div class="alert alert-warning py-2 px-3 mb-2 d-flex align-items-start gap-2 small" role="alert">
                <i class="bi bi-house-door mt-1 flex-shrink-0" aria-hidden="true"></i>
                <div>
                    <strong>Indoor trainer recommended.</strong>
                    ${indoorReason}
                </div>
            </div>`;
    }

    html += '</div>';
    return html;
}

/**
 * Build compact workout fit line for secondary/compare cards (Design B §3).
 */
function renderWorkoutFitCompact(rec) {
    const workoutFit = rec.workout_fit;
    if (!workoutFit) return '';

    const esc = window.escapeHtml;
    const fitScore = workoutFit.fit_score || 0;
    const rating = fitScore >= 0.7 ? 'Good'
                 : fitScore >= 0.4 ? 'Moderate' : 'Poor';
    const ratingClass = rating === 'Good' ? 'bg-success-subtle text-success'
                      : rating === 'Moderate' ? 'bg-warning-subtle text-dark'
                      : 'bg-danger-subtle text-danger';
    const wName = esc(workoutFit.workout_name || 'Workout');

    return `
        <div class="workout-fit-compact">
            <i class="bi bi-heart-pulse" aria-hidden="true"></i>
            <span>${wName} fit:</span>
            <span class="badge ${ratingClass}">${rating}</span>
        </div>`;
}

/**
 * Render the "Workout ride" option card when PlannerService found
 * non-commute routes matching today's workout (#339).
 */
function renderWorkoutRideOption(workoutRide) {
    if (!workoutRide || !workoutRide.rides || workoutRide.rides.length === 0) return '';

    const esc = window.escapeHtml;
    const wName = esc(workoutRide.workout_name || 'Workout');
    const wType = esc(workoutRide.workout_type || '');
    const typeBadgeClass = WORKOUT_TYPE_BADGES[workoutRide.workout_type] || 'bg-secondary';

    const rideCards = workoutRide.rides.map(ride => {
        const scorePct = Math.round(ride.score * 100);
        const scoreClass = scorePct >= 70 ? 'bg-success'
                         : scorePct >= 50 ? 'bg-warning text-dark'
                         : 'bg-danger';
        return `
            <div class="d-flex align-items-center justify-content-between py-1">
                <div>
                    <span class="small fw-semibold">${esc(ride.name)}</span>
                    <div class="d-flex gap-2 small text-muted">
                        <span><i class="bi bi-clock" aria-hidden="true"></i> ${ride.duration_minutes} min</span>
                        <span><i class="bi bi-signpost" aria-hidden="true"></i> ${ride.distance_miles.toFixed(1)} mi</span>
                        <span><i class="bi bi-graph-up" aria-hidden="true"></i> ${ride.elevation_ft} ft</span>
                    </div>
                </div>
                <span class="badge ${scoreClass}">${scorePct}</span>
            </div>`;
    }).join('');

    return `
        <div class="mt-3">
            <div class="small text-muted fw-semibold mb-1">
                <i class="bi bi-bicycle me-1" aria-hidden="true"></i>Workout rides for ${wName}
                <span class="badge ${typeBadgeClass} ms-1">${wType}</span>
            </div>
            <div class="secondary-commute-card border rounded p-2">
                ${rideCards}
            </div>
        </div>`;
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
        container.innerHTML = window.renderErrorState('System status unavailable.', { variant: 'danger', retry: 'loadSystemStatus()' });
    }
}

/**
 * Get weather severity level based on conditions
 * Issue #112 - Weather severity indicators
 *
 * Returns: { level: 'good'|'fair'|'poor'|'miserable', icon: string, color: string, label: string }
 */
function getWeatherSeverity(weather) {
    const temp = weather.temperature || 70;
    const windSpeed = weather.wind_speed || 0;
    const condition = (weather.conditions || '').toLowerCase();
    const precipProb = weather.precipitation_probability || 0;
    
    // Miserable conditions (score 0-25)
    if (condition.includes('thunder') || condition.includes('storm')) {
        return { level: 'miserable', icon: '⛈️', color: 'danger', label: 'Miserable' };
    }
    if (temp >= 95 || temp <= 25) {
        return { level: 'miserable', icon: '🥵', color: 'danger', label: 'Extreme Temp' };
    }
    if (windSpeed >= 25) {
        return { level: 'miserable', icon: '💨', color: 'danger', label: 'Very Windy' };
    }
    if (condition.includes('heavy rain') || precipProb >= 80) {
        return { level: 'miserable', icon: '🌧️', color: 'danger', label: 'Heavy Rain' };
    }
    
    // Poor conditions (score 26-50)
    if (condition.includes('rain') || condition.includes('drizzle') || precipProb >= 50) {
        return { level: 'poor', icon: '🌧️', color: 'warning', label: 'Rainy' };
    }
    if (temp >= 85 || temp <= 35) {
        return { level: 'poor', icon: temp >= 85 ? '🌡️' : '🥶', color: 'warning', label: temp >= 85 ? 'Hot' : 'Cold' };
    }
    if (windSpeed >= 15) {
        return { level: 'poor', icon: '💨', color: 'warning', label: 'Windy' };
    }
    if (condition.includes('snow')) {
        return { level: 'poor', icon: '❄️', color: 'info', label: 'Snowy' };
    }
    
    // Fair conditions (score 51-75)
    if (condition.includes('cloud') || condition.includes('overcast')) {
        return { level: 'fair', icon: '⛅', color: 'secondary', label: 'Cloudy' };
    }
    if (windSpeed >= 8) {
        return { level: 'fair', icon: '🍃', color: 'info', label: 'Breezy' };
    }
    if (temp >= 75 || temp <= 45) {
        return { level: 'fair', icon: '⛅', color: 'secondary', label: 'Fair' };
    }
    
    // Good conditions (score 76-100)
    return { level: 'good', icon: '☀️', color: 'success', label: 'Excellent' };
}

/**
 * Get weather icon based on conditions
 * Issue #116 - Visual weather icons
 */
function getWeatherIcon(conditions, temp) {
    const condition = (conditions || '').toLowerCase();
    
    // Temperature-based icons
    if (temp >= 85) return 'bi-thermometer-sun text-danger';
    if (temp <= 32) return 'bi-thermometer-snow text-primary';
    
    // Condition-based icons
    if (condition.includes('rain') || condition.includes('drizzle')) return 'bi-cloud-rain text-primary';
    if (condition.includes('snow')) return 'bi-cloud-snow text-info';
    if (condition.includes('thunder') || condition.includes('storm')) return 'bi-cloud-lightning text-warning';
    if (condition.includes('cloud') || condition.includes('overcast')) return 'bi-cloud text-secondary';
    if (condition.includes('clear') || condition.includes('sunny')) return 'bi-sun text-warning';
    if (condition.includes('fog') || condition.includes('mist')) return 'bi-cloud-fog text-muted';
    if (condition.includes('wind')) return 'bi-wind text-info';
    
    // Default
    return 'bi-cloud-sun text-primary';
}

/**
 * Get temperature color class
 * Issue #116 - Color-coded temperature ranges
 */
function getTempColorClass(temp) {
    if (temp >= 85) return 'text-danger';  // Hot (red)
    if (temp >= 75) return 'text-warning'; // Warm (orange)
    if (temp >= 60) return 'text-success'; // Comfortable (green)
    if (temp >= 45) return 'text-info';    // Cool (blue)
    return 'text-primary';                  // Cold (dark blue)
}

/**
 * Get wind direction arrow
 * Issue #116 - Wind direction visualization
 */
function getWindArrow(direction) {
    const arrows = {
        'N': '↓', 'NNE': '↓', 'NE': '↙', 'ENE': '↙',
        'E': '←', 'ESE': '←', 'SE': '↖', 'SSE': '↖',
        'S': '↑', 'SSW': '↑', 'SW': '↗', 'WSW': '↗',
        'W': '→', 'WNW': '→', 'NW': '↘', 'NNW': '↘'
    };
    return arrows[direction] || '•';
}

/**
 * Get wind speed color and description
 * Issue #116 - Wind visualization
 */
function getWindInfo(speed) {
    if (speed >= 25) return { color: 'text-danger', desc: 'Very Windy' };
    if (speed >= 15) return { color: 'text-warning', desc: 'Windy' };
    if (speed >= 8) return { color: 'text-info', desc: 'Breezy' };
    return { color: 'text-success', desc: 'Calm' };
}

/**
 * Load and display weather data in banner format
 */
async function loadWeather() {
    const container = document.getElementById('weather-banner');
    
    try {
        const weather = await window.apiClient.getWeather();
        
        if (!weather || !weather.current) {
            container.innerHTML = '<span class="text-white opacity-75 small"><i class="bi bi-cloud-slash me-1"></i>Weather data unavailable</span>';
            return;
        }
        
        const esc = window.escapeHtml;
        const current = weather.current;
        const weatherIcon = getWeatherIcon(current.conditions, current.temperature);
        const windArrow = getWindArrow(current.wind_direction);
        const windInfo = getWindInfo(current.wind_speed);
        const severity = getWeatherSeverity(current); // Issue #112 - Weather severity

        const html = `
            <div class="weather-icon">
                <i class="bi ${weatherIcon}"></i>
            </div>
            <div>
                <div class="weather-temp">${current.temperature}°F</div>
                <small style="opacity: 0.9;">Feels like ${current.feels_like}°F</small>
            </div>
            <div class="weather-details flex-grow-1">
                <div class="weather-detail-item">
                    <span class="badge bg-${severity.color}" style="font-size: 1rem; padding: var(--space-2) var(--space-3);" title="Weather severity: ${severity.label}">
                        ${severity.icon} ${severity.label}
                    </span>
                </div>
                <div class="weather-detail-item">
                    <i class="bi bi-wind"></i>
                    <span>${current.wind_speed} mph ${windArrow} ${esc(current.wind_direction)}</span>
                </div>
                <div class="weather-detail-item">
                    <i class="bi bi-droplet"></i>
                    <span>${current.humidity}%</span>
                </div>
                ${current.precipitation_probability ? `
                    <div class="weather-detail-item">
                        <i class="bi bi-cloud-rain"></i>
                        <span>${current.precipitation_probability}%</span>
                    </div>
                ` : ''}
                <div class="weather-detail-item">
                    <span class="comfort-badge">Score: ${current.comfort_score}/100</span>
                </div>
            </div>
            ${weather.timestamp ? `
                <div class="weather-detail-item timestamp-display" data-timestamp="${weather.timestamp}" title="${formatAbsoluteTime(weather.timestamp)}" style="opacity: 0.8;">
                    <i class="bi bi-clock"></i>
                    <span>${formatRelativeTime(weather.timestamp)}</span>
                </div>
            ` : ''}
        `;
        
        container.innerHTML = html;

        renderWeatherWorkoutPill(container);
    } catch (error) {
        console.error('Failed to load weather:', error);
        container.innerHTML = '<span class="text-white small"><i class="bi bi-cloud-slash me-1"></i>Weather unavailable <button class="btn btn-sm btn-outline-light ms-2 py-0 px-1" onclick="loadWeather()">Retry</button></span>';
    }
}

/**
 * Render workout pill inside the weather banner (Design B §2A).
 * Shows today's workout name, type, and duration at a glance.
 * Links to settings.html#trainerroad-section.
 */
function renderWeatherWorkoutPill(bannerEl) {
    if (!_todayWorkout) return;

    const esc = window.escapeHtml;
    const w = _todayWorkout;
    const typeBadgeClass = WORKOUT_TYPE_BADGES[w.type] || 'bg-secondary';
    const staleClass = isWorkoutDataStale() ? ' workout-pill-stale' : '';
    const staleTitle = isWorkoutDataStale()
        ? ' — workout data may be outdated'
        : '';

    const pill = document.createElement('a');
    pill.href = 'settings.html#trainerroad-section';
    pill.className = `workout-pill${staleClass}`;
    pill.setAttribute('aria-label',
        `Today's workout: ${w.name}, ${w.type || 'Workout'}, ${w.duration_minutes || '?'} minutes${staleTitle}`);
    pill.title = `Today's workout${staleTitle}`;
    pill.innerHTML = `
        <i class="bi bi-calendar-week" aria-hidden="true"></i>
        <span class="fw-semibold">${esc(w.name)}</span>
        <span>&middot;</span>
        <span class="badge ${typeBadgeClass}">${esc(w.type || 'Workout')}</span>
        <span>&middot;</span>
        <span>${w.duration_minutes || '?'} min</span>
        ${isWorkoutDataStale() ? '<i class="bi bi-exclamation-circle ms-1" aria-hidden="true" title="Workout data stale"></i>' : ''}`;

    bannerEl.appendChild(pill);
}

/**
 * Determine which commute direction to show as hero based on time of day (#287).
 * Returns 'to_work', 'to_home', or 'weekend'.
 */
function getContextualDirection() {
    const now = new Date();
    const hour = now.getHours();
    const isWeekend = now.getDay() === 0 || now.getDay() === 6;
    if (isWeekend) return 'weekend';
    if (hour >= 5 && hour < 10) return 'to_work';
    if (hour >= 15 && hour < 19) return 'to_home';
    return 'off_peak';
}

function getHeroHeading(contextDir) {
    const headings = {
        to_work:  { icon: 'bi-sunrise',      label: 'Morning commute',  sub: 'To Work' },
        to_home:  { icon: 'bi-sunset',        label: 'Evening commute',  sub: 'To Home' },
        weekend:  { icon: 'bi-map',           label: 'Weekend ride',     sub: 'Suggestion' },
        off_peak: { icon: 'bi-arrow-right-circle', label: 'Next commute', sub: '' }
    };
    return headings[contextDir] || headings.off_peak;
}

/**
 * Render hero decision card (#286) from a recommendation object.
 */
function renderHeroCard(rec, isHero) {
    if (!rec || rec.status !== 'success') return '';

    const esc = window.escapeHtml;
    const route = rec.route || {};
    const score = typeof rec.score === 'number' && rec.score <= 1
        ? Math.round(rec.score * 100)
        : Math.round(rec.score || 0);
    const scoreClass = getScoreClass(score);
    const scoreIcon = score >= 80 ? 'bi-check-circle-fill text-success'
                    : score >= 60 ? 'bi-hand-thumbs-up-fill text-info'
                    : score >= 40 ? 'bi-exclamation-triangle-fill text-warning'
                    : 'bi-x-circle-fill text-danger';
    const isExtended = rec.is_workout_extended;
    const routeName = esc(route.name || 'Route') + (isExtended ? ' <span class="text-muted fw-normal">(extended)</span>' : '');
    const confidence = esc(rec.confidence || 'Recommended');
    const weatherSummary = rec.weather_summary ? esc(rec.weather_summary) : '';
    const reasons = rec.reasons || [];
    const timeLabel = rec.time_impact && rec.time_impact.label ? esc(rec.time_impact.label) : null;
    const estMins = rec.time_impact && rec.time_impact.estimated_minutes;
    const departureTime = rec.departure_time ? esc(rec.departure_time) : null;

    const borderColor = score >= 70 ? '#28a745' : score >= 50 ? '#ffc107' : '#dc3545';
    const windImpact = rec.wind_impact;
    const windBadge = windImpact
        ? `<span class="badge bg-light text-dark border ms-2" title="Wind impact on this route">
               <i class="bi ${esc(windImpact.icon || 'bi-wind')}"></i> ${esc(windImpact.label)}
           </span>`
        : '';

    const transit = rec.transit_recommendation;
    const transitBanner = transit && transit.suggested ? (() => {
        const isSevere = transit.severity === 'severe';
        const alertClass = isSevere ? 'alert-danger' : 'alert-warning';
        const icon = isSevere ? 'bi-exclamation-triangle-fill' : 'bi-bus-front-fill';
        const url = transit.transit_url || 'https://www.google.com/maps?travelmode=transit';
        return `
            <div class="alert ${alertClass} py-2 px-3 mt-3 mb-0 d-flex align-items-start gap-2" role="alert">
                <i class="bi ${icon} mt-1 flex-shrink-0"></i>
                <div class="flex-grow-1 small">
                    <strong>${isSevere ? 'Conditions unsafe for cycling.' : 'Consider transit today.'}</strong>
                    ${transit.reason ? ` ${esc(transit.reason)}.` : ''}
                    <a href="${esc(url)}" target="_blank" rel="noopener noreferrer" class="d-block mt-1">
                        <i class="bi bi-box-arrow-up-right me-1"></i>Open transit planner
                    </a>
                </div>
            </div>`;
    })() : '';

    if (isHero) {
        return `
            <div class="hero-decision-card" style="border-left: 4px solid ${borderColor}; padding-left: var(--space-3);">
                <div class="hero-card-header">
                    <span class="hero-route-name">
                        <i class="bi ${scoreIcon} me-1"></i>${routeName}
                        <span class="badge ${scoreClass} ms-2">${score}</span>
                        ${windBadge}
                    </span>
                    <span class="hero-confidence badge bg-secondary">${confidence}</span>
                </div>
                ${weatherSummary ? `<div class="hero-weather-summary"><i class="bi bi-cloud-sun me-1"></i>${weatherSummary}</div>` : ''}
                ${estMins ? `<div class="hero-time-estimate"><i class="bi bi-clock me-1"></i>${timeLabel}</div>` : ''}
                ${reasons.length ? `
                    <div class="small fw-semibold text-muted mt-2 mb-1">Why this route?</div>
                    <ul class="hero-reasons">
                        ${reasons.map(r => `<li>${esc(r)}</li>`).join('')}
                    </ul>
                ` : ''}
                ${renderWorkoutFitRow(rec)}
                <div class="hero-meta small text-muted mt-2">
                    <span><i class="bi bi-signpost"></i> ${route.distance ? route.distance.toFixed(1) : '—'} mi</span>
                    <span class="ms-3"><i class="bi bi-graph-up"></i> ${route.elevation || '—'} ft</span>
                    ${departureTime ? `<span class="ms-3"><i class="bi bi-alarm"></i> ${departureTime}</span>` : ''}
                </div>
                ${transitBanner}
                <div class="mt-3 d-flex gap-2 flex-wrap">
                    ${route.id ? `
                    <a href="route-detail.html?id=${encodeURIComponent(route.id)}" class="btn btn-primary btn-sm">
                        <i class="bi bi-map me-1"></i>View route
                    </a>` : ''}
                    <button type="button" class="btn btn-outline-secondary btn-sm"
                            data-bs-toggle="collapse" data-bs-target="#commute-detail"
                            aria-expanded="false" aria-controls="commute-detail">
                        <i class="bi bi-list-ul"></i> Compare routes
                        <i class="bi bi-chevron-down ms-1 commute-chevron"></i>
                    </button>
                </div>
            </div>`;
    }

    // Compact secondary card with optional workout fit annotation (Design B §3)
    return `
        <div class="secondary-commute-card border rounded p-2 mt-3">
            <div class="d-flex align-items-center justify-content-between">
                <span class="small fw-semibold">
                    <i class="bi ${scoreIcon} me-1"></i>${routeName}
                </span>
                <span class="badge ${scoreClass}">${score}</span>
            </div>
            ${weatherSummary ? `<div class="small text-muted mt-1">${weatherSummary}</div>` : ''}
            <div class="d-flex gap-3 mt-1 small text-muted">
                ${estMins ? `<span><i class="bi bi-clock"></i> ${estMins} min</span>` : ''}
                <span><i class="bi bi-signpost"></i> ${route.distance ? route.distance.toFixed(1) : '—'} mi</span>
            </div>
            ${renderWorkoutFitCompact(rec)}
        </div>`;
}

/**
 * Load and display commute recommendation as Hero Decision Card (#286, #287).
 */
async function loadRecommendation() {
    const container = document.getElementById('commute-recommendation');

    try {
        const response = await fetch('/api/commute');
        const data = await response.json();

        if (data.status !== 'success' || (!data.to_work && !data.to_home)) {
            container.innerHTML = window.renderEmptyState('No commute recommendations yet.', 'Run analysis to generate route recommendations.', 'bi-signpost-2');
            return;
        }

        const contextDir = getContextualDirection();
        const heading = getHeroHeading(contextDir);

        let primary, secondary, primaryLabel, secondaryLabel;
        if (contextDir === 'to_home') {
            primary = data.to_home;
            secondary = data.to_work;
            primaryLabel = 'To Home';
            secondaryLabel = 'To Work (later)';
        } else {
            primary = data.to_work;
            secondary = data.to_home;
            primaryLabel = contextDir === 'weekend' ? 'Suggested' : 'To Work';
            secondaryLabel = 'To Home';
        }

        let html = `
            <div class="hero-card-context mb-2 small text-muted fw-semibold">
                <i class="bi ${heading.icon} me-1"></i>${heading.label}
                ${heading.sub ? `<span class="ms-1">· ${heading.sub}</span>` : ''}
            </div>`;

        html += renderHeroCard(primary, true);

        if (secondary && secondary.status === 'success') {
            html += `
                <div class="secondary-label small text-muted mt-3 mb-1">
                    <i class="bi bi-arrow-return-right me-1"></i>${secondaryLabel}
                </div>`;
            html += renderHeroCard(secondary, false);
        }

        if (data.workout_ride) {
            html += renderWorkoutRideOption(data.workout_ride);
        }

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load commute recommendations:', error);
        container.innerHTML = window.renderErrorState('Commute recommendations unavailable.', { retry: 'loadRecommendation()' });
    }
}

/**
 * Load Today's Conditions card with traffic-light indicators (#288).
 * Mobile: collapses to a 1-line summary with an expand chevron.
 */
async function loadConditionsCard() {
    const container = document.getElementById('conditions-card');
    if (!container) return;

    try {
        const weather = await window.apiClient.getWeather();
        if (!weather || !weather.current) {
            container.innerHTML = window.renderEmptyState('Conditions unavailable.', '', 'bi-cloud-slash');
            return;
        }

        const esc = window.escapeHtml;
        const current = weather.current;
        const severity = getWeatherSeverity(current);
        const comfort = current.comfort_score || 0;

        function conditionStatus(score) {
            if (score >= 80) return { icon: 'bi-check-circle-fill', color: '#28a745', label: 'Excellent' };
            if (score >= 65) return { icon: 'bi-hand-thumbs-up-fill', color: '#20c997', label: 'Good' };
            if (score >= 50) return { icon: 'bi-exclamation-triangle-fill', color: '#ffc107', label: 'Fair' };
            if (score >= 35) return { icon: 'bi-hand-thumbs-down-fill', color: '#fd7e14', label: 'Poor' };
            return { icon: 'bi-x-circle-fill', color: '#dc3545', label: 'Bad' };
        }

        function conditionRow(label, score, note) {
            const s = conditionStatus(score);
            return `
                <div class="conditions-row d-flex align-items-center gap-2 py-1">
                    <span class="conditions-label small text-muted" style="min-width:90px">${label}</span>
                    <i class="bi ${s.icon}" style="color:${s.color};font-size:1rem;"></i>
                    <span class="small">${esc(note)}</span>
                </div>`;
        }

        const windSpeed = current.wind_speed;
        const windDir = current.wind_direction || '';
        const windScore = windSpeed <= 5 ? 90
                        : windSpeed <= 10 ? 75
                        : windSpeed <= 18 ? 55
                        : 30;
        const windNote = windSpeed <= 5 ? 'Calm'
                       : windSpeed <= 10 ? `Light ${windDir} wind`
                       : windSpeed <= 18 ? `${windDir} wind (${windSpeed} mph)`
                       : `Strong ${windDir} wind (${windSpeed} mph)`;
        const conditionsText = `${severity.label} — ${(current.conditions || '').toLowerCase()}`;

        const overall = conditionStatus(comfort);
        const html = `
            <div class="conditions-summary-toggle d-flex d-md-none align-items-center gap-2"
                 role="button" tabindex="0" aria-expanded="false" aria-controls="conditions-full-rows">
                <i class="bi ${overall.icon}" style="color:${overall.color}"></i>
                <span class="small fw-semibold">${overall.label} · ${comfort}/100</span>
                <i class="bi bi-chevron-down ms-auto conditions-chevron" aria-hidden="true"></i>
            </div>
            <div class="conditions-full-rows">
                ${conditionRow('Weather', comfort, conditionsText)}
                ${conditionRow('Wind', windScore, windNote)}
                ${conditionRow('Comfort', comfort, `${comfort}/100`)}
                <div class="mt-2">
                    <a href="/weather.html" class="small text-muted">Detailed forecast →</a>
                </div>
            </div>`;

        container.innerHTML = html;

        const toggle = container.querySelector('.conditions-summary-toggle');
        const fullRows = container.querySelector('.conditions-full-rows');
        if (toggle && fullRows) {
            toggle.addEventListener('click', () => {
                const expanded = toggle.getAttribute('aria-expanded') === 'true';
                toggle.setAttribute('aria-expanded', String(!expanded));
                fullRows.classList.toggle('conditions-rows-open', !expanded);
                toggle.querySelector('.conditions-chevron').style.transform = expanded ? '' : 'rotate(180deg)';
            });
            toggle.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle.click(); }
            });
        }

        const mobile = document.getElementById('conditions-card-mobile');
        if (mobile) mobile.innerHTML = html;
    } catch (error) {
        console.error('Failed to load conditions card:', error);
        container.innerHTML = window.renderErrorState('Conditions unavailable.', { small: true, retry: 'loadConditionsCard()' });
    }
}

/**
 * Load Route Status panel with per-route condition summary (#289).
 * Mobile: panel is hidden when fewer than 2 routes (not worth showing).
 */
async function loadRouteStatus() {
    const container = document.getElementById('route-status-panel');
    if (!container) return;

    try {
        const response = await fetch('/api/routes/status');
        const data = await response.json();

        if (data.status !== 'success' || !data.routes || data.routes.length === 0) {
            container.innerHTML = window.renderEmptyState('No route data.', 'Sync Strava to see route conditions.', 'bi-map');
            container.closest('.route-status-col').classList.add('d-none', 'd-md-block');
            return;
        }

        if (data.routes.length < 2) {
            container.closest('.route-status-col').classList.add('d-none', 'd-md-block');
        }

        const esc = window.escapeHtml;
        function routeStatusRow(route) {
            const score = route.condition_score || 75;
            let icon, color;
            if (score >= 80) { icon = 'bi-check-circle-fill'; color = '#28a745'; }
            else if (score >= 65) { icon = 'bi-hand-thumbs-up-fill'; color = '#20c997'; }
            else if (score >= 50) { icon = 'bi-exclamation-triangle-fill'; color = '#ffc107'; }
            else if (score >= 35) { icon = 'bi-hand-thumbs-down-fill'; color = '#fd7e14'; }
            else { icon = 'bi-x-circle-fill'; color = '#dc3545'; }
            const name = esc((route.name || 'Route').slice(0, 22));
            return `
                <div class="route-status-row d-flex align-items-center gap-2 py-1">
                    <span class="small text-truncate" style="min-width:120px;max-width:140px">${name}</span>
                    <i class="bi ${icon}" style="color:${color};font-size:1rem;flex-shrink:0"></i>
                    <span class="small text-muted">${esc(route.condition_note || 'Clear')}</span>
                </div>`;
        }

        const rows = data.routes.map(routeStatusRow).join('');
        const html = `
            ${rows}
            <div class="mt-2">
                <a href="/routes.html" class="small text-muted">All Routes →</a>
            </div>`;
        container.innerHTML = html;
        const mobile = document.getElementById('route-status-panel-mobile');
        if (mobile) mobile.innerHTML = html;
    } catch (error) {
        console.error('Failed to load route status:', error);
        container.innerHTML = window.renderErrorState('Route status unavailable.', { small: true, retry: 'loadRouteStatus()' });
    }
}

/**
 * Load and display route statistics
 */
async function loadRouteStats() {
    const container = document.getElementById('route-stats');
    
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
    } catch (error) {
        console.error('Failed to load route stats:', error);
        container.innerHTML = window.renderErrorState('Failed to load route statistics.', { variant: 'danger', retry: 'loadRouteStats()' });
    }
}

/**
 * Load morning/evening commute window forecast cards (#110, #111, #115).
 */
async function loadCommuteWindows() {
    const container = document.getElementById('commute-windows');
    if (!container) return;

    try {
        const response = await fetch('/api/weather/commute-windows');
        const data = await response.json();

        if (data.status !== 'success') {
            container.innerHTML = window.renderEmptyState('Forecast unavailable.', '', 'bi-cloud-slash');
            return;
        }

        const esc = window.escapeHtml;

        function windowCard(label, icon, window) {
            if (!window || !window.avg_temp_f) return '';
            const precip = window.max_precip_prob || 0;
            const wind = window.avg_wind_mph || 0;
            const precipColor = precip >= 60 ? 'text-danger' : precip >= 30 ? 'text-warning' : 'text-success';
            const windColor = wind >= 15 ? 'text-danger' : wind >= 8 ? 'text-warning' : 'text-success';
            const opt = window.optimal_departure;
            const optText = opt
                ? `<span class="badge bg-primary ms-1" title="Best departure: lowest wind + precip">${esc(opt)}</span>`
                : '';

            // Hourly progression rows (#115 — weather progression)
            const hours = Array.isArray(window.hours) ? window.hours : [];
            const progressionRows = hours.map(h => {
                const isOpt = opt && h.hour === opt;
                const hWind = h.wind_mph || 0;
                const hWindClass = hWind >= 15 ? 'text-danger' : hWind >= 8 ? 'text-warning' : 'text-muted';
                const hPrecip = h.precip_prob || 0;
                const hPrecipPart = hPrecip > 0
                    ? `<span class="${hPrecip >= 60 ? 'text-danger' : hPrecip >= 30 ? 'text-warning' : 'text-muted'}"> · ${hPrecip}%</span>`
                    : '';
                return `<div class="d-flex align-items-center gap-1 ${isOpt ? 'fw-semibold' : ''}" style="font-size:0.7rem;line-height:1.6">
                    <span class="text-muted" style="min-width:36px">${esc(h.hour)}</span>
                    <span>${h.temp_f}°</span>
                    <span class="${hWindClass}">${hWind}mph</span>
                    ${hPrecipPart}
                    ${isOpt ? '<i class="bi bi-arrow-left text-primary" title="Best departure"></i>' : ''}
                </div>`;
            }).join('');

            return `
                <div class="commute-window-card d-flex align-items-start gap-2 py-2">
                    <i class="bi ${icon} text-muted" style="font-size:1.1rem;margin-top:2px;flex-shrink:0"></i>
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center gap-1 mb-1">
                            <span class="small fw-semibold">${label}</span>
                            ${optText}
                        </div>
                        <div class="d-flex flex-wrap gap-2 small text-muted mb-1">
                            <span><i class="bi bi-thermometer-half"></i> ${window.avg_temp_f}°F avg</span>
                            <span class="${windColor}"><i class="bi bi-wind"></i> ${wind} mph ${esc(window.dominant_wind_direction || '')}</span>
                            ${precip > 0 ? `<span class="${precipColor}"><i class="bi bi-cloud-rain"></i> ${precip}%</span>` : ''}
                        </div>
                        ${progressionRows ? `<div class="commute-window-progression">${progressionRows}</div>` : ''}
                    </div>
                </div>`;
        }

        const html = `
            ${windowCard('Morning (7–9 AM)', 'bi-sunrise', data.morning)}
            ${data.morning && data.evening ? '<hr class="my-1">' : ''}
            ${windowCard('Evening (3–6 PM)', 'bi-sunset', data.evening)}
            <div class="mt-1">
                <a href="/weather.html" class="small text-muted">Full forecast →</a>
            </div>`;

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load commute windows:', error);
        container.innerHTML = window.renderErrorState('Forecast unavailable.', { small: true, retry: 'loadCommuteWindows()' });
    }
}

async function loadHourlyForecast() {
    const container = document.getElementById('hourly-forecast');
    if (!container) return;

    try {
        const data = await window.apiClient.getHourlyForecast();

        if (data.status !== 'success' || !data.hours || data.hours.length === 0) {
            container.innerHTML = window.renderEmptyState('Hourly forecast unavailable.', '', 'bi-clock');
            return;
        }

        const esc = window.escapeHtml;

        const hourCells = data.hours.map(h => {
            const tempClass = getTempColorClass(h.temp_f);
            const windInfo = getWindInfo(h.wind_speed_mph);
            const precipColor = h.precipitation_prob >= 60 ? 'text-danger'
                              : h.precipitation_prob >= 30 ? 'text-warning'
                              : 'text-muted';
            const commuteClass = h.is_commute_hour ? 'hourly-commute' : '';

            return `
                <div class="hourly-cell ${commuteClass}">
                    <div class="hourly-time">${esc(h.time)}</div>
                    <div class="hourly-temp ${tempClass}">${h.temp_f}°</div>
                    <div class="hourly-wind ${windInfo.color}">
                        <i class="bi bi-wind" aria-hidden="true"></i> ${h.wind_speed_mph}
                    </div>
                    ${h.precipitation_prob > 0
                        ? `<div class="hourly-precip ${precipColor}"><i class="bi bi-droplet" aria-hidden="true"></i> ${h.precipitation_prob}%</div>`
                        : '<div class="hourly-precip text-muted">-</div>'}
                </div>`;
        }).join('');

        container.innerHTML = `<div class="hourly-strip">${hourCells}</div>`;
    } catch (error) {
        console.error('Failed to load hourly forecast:', error);
        container.innerHTML = window.renderErrorState('Hourly forecast unavailable.', { small: true, retry: 'loadHourlyForecast()' });
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
