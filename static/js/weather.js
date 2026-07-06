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

function renderTodayGlance(today) {
    const card = document.getElementById('today-glance');
    const content = document.getElementById('today-glance-content');
    if (!card || !content) return;

    content.innerHTML = `
        <div class="window-metric mb-0">
            <i class="bi bi-speedometer2 text-success"></i>
            <span>${today.comfort_score}/100 comfort</span>
        </div>
        <div class="window-metric mb-0">
            <i class="bi bi-thermometer-half"></i>
            <span>${today.temp_max_f}° / ${today.temp_min_f}°F</span>
        </div>
        <div class="window-metric mb-0">
            <i class="bi bi-wind"></i>
            <span>${today.wind_mph} mph ${today.wind_direction || ''}</span>
        </div>
        <div class="window-metric mb-0">
            <i class="bi bi-droplet"></i>
            <span>${today.precip_prob}% precip</span>
        </div>
    `;
    card.classList.remove('d-none');
}

function maybeShowTransitAlert(today) {
    if (today.comfort_score >= TRANSIT_COMFORT_THRESHOLD) {
        renderTodayGlance(today);
        return;
    }

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
        ${windowData.optimal_departure ? `
        <div class="window-metric text-success mt-1">
            <i class="bi bi-clock-history"></i>
            <span>Best departure: <strong>${windowData.optimal_departure}</strong></span>
        </div>
        ` : ''}
    `;
}

/** Format an hour-of-day (0–23) as a locale-friendly 12-hour label, e.g. "7 AM". */
function formatHour12(hour24) {
    const d = new Date(2000, 0, 1, ((hour24 % 24) + 24) % 24, 0, 0);
    return d.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
}

/**
 * Derive a "(7–9 AM)" style range label from a commute window's `hours` array.
 * Each entry's `hour` field is an "HH:MM" string for the start of that hourly
 * bucket, so the window's end is the last bucket's hour + 1 (#373).
 */
function formatWindowRangeLabel(hours) {
    if (!hours || !hours.length) return '';

    const startHour = parseInt(hours[0].hour.split(':')[0], 10);
    const lastHour = parseInt(hours[hours.length - 1].hour.split(':')[0], 10);
    const endHour = lastHour + 1;

    const startLabel = formatHour12(startHour);
    const endLabel = formatHour12(endHour);
    const startMeridiem = startLabel.split(' ')[1];
    const endMeridiem = endLabel.split(' ')[1];

    if (startMeridiem === endMeridiem) {
        return `(${startLabel.split(' ')[0]}–${endLabel})`;
    }
    return `(${startLabel}–${endLabel})`;
}

function updateWindowTimeRange(windowData, labelId) {
    const el = document.getElementById(labelId);
    if (!el) return;
    const label = formatWindowRangeLabel(windowData && windowData.hours);
    el.textContent = label || '';
}

async function loadCommuteWindows() {
    try {
        const res = await fetch('/api/weather/commute-windows');
        const data = await res.json();
        if (!data || data.status !== 'success') throw new Error(data?.message || 'No window data');

        updateWindowTimeRange(data.morning, 'morning-time-range');
        updateWindowTimeRange(data.evening, 'evening-time-range');
        renderWindowMetrics(data.morning, 'morning-content');
        renderWindowMetrics(data.evening, 'evening-content');
    } catch (err) {
        console.error('Failed to load commute windows:', err);
        document.getElementById('morning-content').innerHTML = '';
        document.getElementById('evening-content').innerHTML = '';
        document.getElementById('morning-time-range').textContent = '';
        document.getElementById('evening-time-range').textContent = '';
        document.getElementById('windows-error').classList.remove('d-none');
    }
}

function initComfortLegendPopover() {
    const icon = document.getElementById('comfort-legend-icon');
    if (!icon || typeof bootstrap === 'undefined') return;

    const popover = new bootstrap.Popover(icon, { trigger: 'manual', html: false });

    const hide = () => popover.hide();
    const toggle = (e) => {
        e.preventDefault();
        e.stopPropagation();
        popover.toggle();
    };

    // Manual trigger (rather than the built-in "focus"/"click" triggers) so the
    // same handler reliably opens on both mouse click and touch tap, and closes
    // on outside interaction — Bootstrap's own triggers are inconsistent on iOS Safari.
    icon.addEventListener('click', toggle);
    icon.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') toggle(e);
        if (e.key === 'Escape') hide();
    });
    document.addEventListener('click', (e) => {
        if (e.target !== icon) hide();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadForecast();
    loadCommuteWindows();
    initComfortLegendPopover();
});
