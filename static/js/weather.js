/**
 * weather.js — 7-day forecast page (#109, #114)
 */

const TRANSIT_COMFORT_THRESHOLD = 40; // below this → suggest transit

function weatherIcon(precipProb, windMph) {
    if (precipProb >= 70) return 'bi-cloud-rain-heavy text-primary';
    if (precipProb >= 40) return 'bi-cloud-rain text-info';
    if (precipProb >= 20) return 'bi-cloud-drizzle text-secondary';
    if (windMph >= 25)    return 'bi-wind text-secondary';
    if (precipProb >= 5)  return 'bi-cloud-sun text-warning';
    return 'bi-sun text-warning';
}

function dayLabel(dateStr, index) {
    if (index === 0) return 'Today';
    const d = new Date(dateStr + 'T12:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'short' });
}

function favorabilityLabel(fav) {
    const map = { favorable: 'Good', neutral: 'Fair', unfavorable: 'Poor' };
    return map[fav] || fav;
}

function renderForecast(days) {
    const grid = document.getElementById('forecast-grid');
    grid.innerHTML = '';

    days.forEach((day, i) => {
        const isToday = i === 0;
        const icon = weatherIcon(day.precip_prob, day.wind_mph);
        const label = dayLabel(day.date, i);

        const card = document.createElement('div');
        card.className = 'forecast-card' + (isToday ? ' today' : '');
        card.innerHTML = `
            <div class="forecast-day">${label}</div>
            <i class="bi ${icon} forecast-icon"></i>
            <div class="forecast-temps">
                <span class="hi">${day.temp_max_f}°</span>
                <span class="lo"> / ${day.temp_min_f}°</span>
            </div>
            <div class="forecast-detail">
                <i class="bi bi-droplet"></i> ${day.precip_prob}%
                &nbsp;
                <i class="bi bi-wind"></i> ${day.wind_mph} mph
            </div>
            <span class="comfort-pill ${day.cycling_favorability}">
                ${favorabilityLabel(day.cycling_favorability)}
            </span>
        `;
        grid.appendChild(card);
    });
}

function maybeShowTransitAlert(today) {
    if (today.comfort_score >= TRANSIT_COMFORT_THRESHOLD) return;

    const alert = document.getElementById('transit-alert');
    const reason = document.getElementById('transit-reason');

    const parts = [];
    if (today.precip_prob >= 50) parts.push(`${today.precip_prob}% chance of rain`);
    if (today.wind_mph >= 20) parts.push(`${today.wind_mph} mph winds`);
    if (parts.length === 0) parts.push('conditions are unfavorable for cycling');

    reason.textContent = `Today's forecast shows ${parts.join(' and ')}.`;
    alert.classList.remove('d-none');
}

async function loadForecast() {
    try {
        const data = await window.apiClient.getForecast();
        if (!data || data.status !== 'success' || !data.forecast?.length) {
            throw new Error(data?.message || 'No forecast data');
        }

        renderForecast(data.forecast);
        maybeShowTransitAlert(data.forecast[0]);

        const updated = document.getElementById('forecast-updated');
        if (data.timestamp) {
            const d = new Date(data.timestamp);
            updated.textContent = `Updated ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        }
    } catch (err) {
        console.error('Failed to load forecast:', err);
        document.getElementById('forecast-grid').innerHTML = '';
        document.getElementById('forecast-error').classList.remove('d-none');
        document.getElementById('forecast-error-msg').textContent =
            err.message || 'Unable to load forecast';
    }
}

function renderWindowMetrics(windowData, contentId) {
    const el = document.getElementById(contentId);
    if (!windowData || !windowData.avg_temp_f) {
        el.innerHTML = '<div class="text-muted small">No data for this window</div>';
        return;
    }

    const precipColor = windowData.max_precip_prob >= 50 ? 'text-primary' : 'text-muted';
    const windColor   = windowData.avg_wind_mph >= 20   ? 'text-warning' : 'text-muted';

    el.innerHTML = `
        <div class="window-metric">
            <i class="bi bi-thermometer-half"></i>
            <span>${windowData.avg_temp_f}°F avg</span>
        </div>
        <div class="window-metric ${precipColor}">
            <i class="bi bi-droplet"></i>
            <span>${windowData.max_precip_prob}% precip</span>
        </div>
        <div class="window-metric ${windColor}">
            <i class="bi bi-wind"></i>
            <span>${windowData.avg_wind_mph} mph ${windowData.dominant_wind_direction || ''}</span>
        </div>
        <div class="window-metric text-success mt-1">
            <i class="bi bi-clock-history"></i>
            <span>Best departure: <strong>${windowData.optimal_departure}</strong></span>
        </div>
    `;
}

async function loadCommuteWindows() {
    try {
        const res = await fetch('/api/weather/commute-windows');
        const data = await res.json();
        if (!data || data.status !== 'success') throw new Error(data?.message || 'No window data');

        renderWindowMetrics(data.morning, 'morning-content');
        renderWindowMetrics(data.evening, 'evening-content');
    } catch (err) {
        console.error('Failed to load commute windows:', err);
        document.getElementById('morning-content').innerHTML = '';
        document.getElementById('evening-content').innerHTML = '';
        document.getElementById('windows-error').classList.remove('d-none');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadForecast();
    loadCommuteWindows();
});
