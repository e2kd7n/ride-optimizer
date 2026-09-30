/**
 * common.js - Common utilities for Ride Optimizer
 * Epic #237 - UI/UX Redesign
 *
 * Features:
 * - Toast notification system (Issue #245)
 * - Auto-save functionality (Issue #244)
 * - Undo/redo support (Issue #249)
 * - Debounce utility
 * - Error/success message handling
 * - XSS protection via HTML escaping
 */

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} unsafe - Unsafe string that may contain HTML
 * @returns {string} - HTML-escaped safe string
 */
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
        unsafe = String(unsafe);
    }
    return unsafe
        .replace(/&/g, "&")
        .replace(/</g, "<")
        .replace(/>/g, ">")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Make escapeHtml available globally
window.escapeHtml = escapeHtml;

// Toast notification system
let toastQueue = [];
let toastContainer = null;

/**
 * Initialize toast container
 * @returns {HTMLElement} Toast container element
 */
function initToastContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.setAttribute('aria-atomic', 'false');
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {Object} options - Configuration options
 * @param {Function} options.undoAction - Optional undo callback
 * @param {number} options.duration - Auto-dismiss duration in ms (default: 5000, 0 = no auto-dismiss)
 * @param {boolean} options.dismissible - Show close button (default: true)
 * @returns {HTMLElement} Toast element
 */
window.showToast = function(message, type = 'info', options = {}) {
    const {
        undoAction = null,
        duration = 5000,
        dismissible = true
    } = typeof options === 'function' ? { undoAction: options } : options;
    
    const container = initToastContainer();
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-item alert alert-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Icon mapping
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };
    
    // Build toast content with XSS protection
    const safeMessage = escapeHtml(message);
    let toastContent = `<strong>${icons[type] || icons.info}</strong> ${safeMessage}`;
    
    // Add undo button if undo action provided
    if (undoAction) {
        const undoId = 'undo-' + Date.now();
        toastContent += `
            <button type="button" class="btn btn-sm btn-outline-light ms-2 border-currentcolor"
                    id="${undoId}"
                    aria-label="Undo last action">
                ↶ Undo
            </button>
        `;
        
        // Store undo action
        setTimeout(() => {
            const undoBtn = document.getElementById(undoId);
            if (undoBtn) {
                undoBtn.addEventListener('click', function() {
                    if (typeof undoAction === 'function') {
                        undoAction();
                        toast.remove();
                        toastQueue = toastQueue.filter(t => t !== toast);
                    }
                });
            }
        }, 0);
    }
    
    // Add close button if dismissible
    if (dismissible) {
        toastContent += `
            <button type="button" class="btn-close float-end" aria-label="Dismiss notification"></button>
        `;
    }
    
    toast.innerHTML = toastContent;
    toast.tabIndex = 0; // Make keyboard accessible
    
    // Handle Escape key to dismiss
    toast.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            toast.remove();
            toastQueue = toastQueue.filter(t => t !== toast);
        }
    });
    
    // Handle close button click
    const closeBtn = toast.querySelector('.btn-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            toast.remove();
            toastQueue = toastQueue.filter(t => t !== toast);
        });
    }
    
    // Add to queue and container
    toastQueue.push(toast);
    container.appendChild(toast);
    
    // Trigger slide-in animation
    requestAnimationFrame(() => {
        toast.classList.add('toast-show');
    });
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.remove('toast-show');
                setTimeout(() => {
                    toast.remove();
                    toastQueue = toastQueue.filter(t => t !== toast);
                }, 300); // Wait for slide-out animation
            }
        }, duration);
    }
    
    return toast;
};

/**
 * Show error message to user
 * @param {string} message - Error message to display
 * @param {string} containerId - ID of container to show error in (optional)
 */
window.showError = function(message, containerId = null) {
    if (containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Remove existing error messages
        const existingErrors = container.querySelectorAll('.error-message');
        existingErrors.forEach(el => el.remove());
        
        // Create and show new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message show';
        errorDiv.setAttribute('role', 'alert');
        errorDiv.setAttribute('aria-live', 'polite');
        errorDiv.innerHTML = `
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close float-end" aria-label="Dismiss error message"></button>
        `;
        errorDiv.querySelector('.btn-close').addEventListener('click', () => errorDiv.remove());

        container.insertBefore(errorDiv, container.firstChild);
        
        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            errorDiv.classList.remove('show');
            setTimeout(() => errorDiv.remove(), 300);
        }, 10000);
    } else {
        showToast(message, 'error');
    }
};

/**
 * Debounce function to limit rate of function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
window.debounce = function(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Fair Weather Day/Night theme
/**
 * Get the currently active Fair Weather theme.
 * The `data-theme` attribute is set as early as possible (inline in <head>,
 * before this script loads) to avoid a flash of the wrong theme.
 * @returns {string} 'day' or 'night'
 */
window.getFairWeatherTheme = function() {
    return document.documentElement.getAttribute('data-theme') === 'night' ? 'night' : 'day';
};

/**
 * Set and persist the Fair Weather theme.
 * @param {string} theme - 'day' or 'night'
 */
window.setFairWeatherTheme = function(theme) {
    const resolved = theme === 'night' ? 'night' : 'day';
    document.documentElement.setAttribute('data-theme', resolved);
    try {
        localStorage.setItem('fairWeatherTheme', resolved);
    } catch (_) {
        // localStorage unavailable (private browsing, etc.) — theme still applies for this load
    }
};

// Unit conversion utilities
/**
 * Get user's preferred unit system from settings
 * @returns {string} 'metric' or 'imperial'
 */
window.getUnitSystem = function() {
    const settings = JSON.parse(localStorage.getItem('rideOptimizerSettings') || '{}');
    return settings.unitSystem || 'imperial'; // Default to imperial
};

/**
 * Convert kilometers to miles
 * @param {number} km - Distance in kilometers
 * @returns {number} Distance in miles
 */
window.kmToMiles = function(km) {
    return km * 0.621371;
};

/**
 * Convert miles to kilometers
 * @param {number} miles - Distance in miles
 * @returns {number} Distance in kilometers
 */
window.milesToKm = function(miles) {
    return miles / 0.621371;
};

/**
 * Convert meters to feet
 * @param {number} meters - Elevation in meters
 * @returns {number} Elevation in feet
 */
window.metersToFeet = function(meters) {
    return meters * 3.28084;
};

/**
 * Format distance based on user's unit preference
 * @param {number} distanceKm - Distance in kilometers
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted distance with unit
 */
window.formatDistance = function(distanceKm, decimals = 1) {
    const unitSystem = getUnitSystem();
    if (unitSystem === 'imperial') {
        const miles = kmToMiles(distanceKm);
        return `${miles.toFixed(decimals)} mi`;
    }
    return `${Number(distanceKm).toFixed(decimals)} km`;
};

/**
 * Format elevation based on user's unit preference
 * @param {number} elevationMeters - Elevation in meters
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted elevation with unit
 */
window.formatElevation = function(elevationMeters, decimals = 0) {
    const unitSystem = getUnitSystem();
    if (unitSystem === 'imperial') {
        const feet = metersToFeet(elevationMeters);
        return `${feet.toFixed(decimals)} ft`;
    }
    return `${Number(elevationMeters).toFixed(decimals)} m`;
};

/**
 * Format temperature based on user's unit preference
 * @param {number} tempCelsius - Temperature in Celsius
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted temperature with unit
 */
window.formatTemperature = function(tempCelsius, decimals = 1) {
    const unitSystem = getUnitSystem();
    if (unitSystem === 'imperial') {
        const fahrenheit = (tempCelsius * 9/5) + 32;
        return `${fahrenheit.toFixed(decimals)}°F`;
    }
    return `${Number(tempCelsius).toFixed(decimals)}°C`;
};

/**
 * Format speed based on user's unit preference
 * @param {number} speedKmh - Speed in km/h
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted speed with unit
 */
window.formatSpeed = function(speedKmh, decimals = 1) {
    const unitSystem = getUnitSystem();
    if (unitSystem === 'imperial') {
        const mph = kmToMiles(speedKmh);
        return `${mph.toFixed(decimals)} mph`;
    }
    return `${Number(speedKmh).toFixed(decimals)} km/h`;
};

/**
 * Get distance unit label
 * @returns {string} 'mi' or 'km'
 */
window.getDistanceUnit = function() {
    return getUnitSystem() === 'imperial' ? 'mi' : 'km';
};

/**
 * Get weather severity level based on conditions
 * Issue #112 - Weather severity indicators
 *
 * Returns: { level: 'good'|'fair'|'poor'|'miserable'|'unknown', icon: string, color: string, label: string }
 */
window.getWeatherSeverity = function(weather) {
    if (!weather) return { level: 'unknown', icon: '❓', color: 'secondary', label: 'Unknown' };

    const temp = weather.temperature || 70;
    const windSpeed = weather.wind_speed || 0;
    const condition = (weather.conditions || '').toLowerCase();
    const precipProb = weather.precipitation_probability || weather.precipitation || 0;

    // Miserable conditions
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

    // Poor conditions
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

    // Fair conditions
    if (condition.includes('cloud') || condition.includes('overcast')) {
        return { level: 'fair', icon: '⛅', color: 'secondary', label: 'Cloudy' };
    }
    if (windSpeed >= 8) {
        return { level: 'fair', icon: '🍃', color: 'info', label: 'Breezy' };
    }
    if (temp >= 75 || temp <= 45) {
        return { level: 'fair', icon: '⛅', color: 'secondary', label: 'Fair' };
    }

    // Good conditions
    return { level: 'good', icon: '☀️', color: 'success', label: 'Excellent' };
};

/**
 * Format a duration in minutes as "Xh Ym" (or "Xm" under an hour)
 * @param {number} durationMinutes - Duration in minutes
 * @returns {string} Formatted duration
 */
window.formatDuration = function(durationMinutes) {
    const totalMinutes = Math.round(Number(durationMinutes || 0));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return hours > 0 ? `${hours}h ${minutes}m` : `${totalMinutes} min`;
};

/**
 * Format timestamp as relative time (e.g., "5 minutes ago")
 * @param {string|Date} timestamp - ISO 8601 timestamp or Date object
 * @returns {string} Formatted relative time
 */
window.formatRelativeTime = function(timestamp) {
    if (!timestamp) return 'Unknown';
    
    try {
        const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        // Less than 1 minute
        if (diffSec < 60) {
            return 'Just now';
        }
        
        // Less than 60 minutes
        if (diffMin < 60) {
            return diffMin === 1 ? '1 minute ago' : `${diffMin} minutes ago`;
        }
        
        // Less than 24 hours
        if (diffHour < 24) {
            return diffHour === 1 ? '1 hour ago' : `${diffHour} hours ago`;
        }
        
        // Less than 7 days
        if (diffDay < 7) {
            return diffDay === 1 ? '1 day ago' : `${diffDay} days ago`;
        }
        
        // 7 days or more - show formatted date
        const options = { month: 'short', day: 'numeric', year: 'numeric' };
        return date.toLocaleDateString('en-US', options);
        
    } catch (error) {
        console.error('Error formatting relative time:', error);
        return 'Unknown';
    }
};

/**
 * Format timestamp as absolute time (e.g., "May 14, 2026 3:45 PM")
 * @param {string|Date} timestamp - ISO 8601 timestamp or Date object
 * @returns {string} Formatted absolute time
 */
window.formatAbsoluteTime = function(timestamp) {
    if (!timestamp) return 'Unknown';
    
    try {
        const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
        const options = {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };
        return date.toLocaleDateString('en-US', options);
        
    } catch (error) {
        console.error('Error formatting absolute time:', error);
        return 'Unknown';
    }
};

/**
 * Update all timestamp displays on the page
 * Call this periodically to keep relative times fresh
 */
window.updateAllTimestamps = function() {
    const timestamps = document.querySelectorAll('.timestamp-display[data-timestamp]');
    timestamps.forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        const prefix = element.textContent.split(' ')[0]; // Extract prefix (e.g., "Updated")
        element.textContent = `${prefix} ${formatRelativeTime(timestamp)}`;
        element.setAttribute('title', formatAbsoluteTime(timestamp));
    });
};

// Auto-update timestamps every minute
setInterval(updateAllTimestamps, 60000);

/**
 * Render a consistent error state with optional retry (#93).
 * @param {string} message - User-facing error description
 * @param {object} opts
 * @param {string} [opts.icon='bi-exclamation-triangle'] - Bootstrap icon class
 * @param {string} [opts.variant='warning'] - Bootstrap alert variant
 * @param {function} [opts.retry] - Callback invoked by the retry button (omit for no button)
 * @param {boolean} [opts.small=false] - Compact sizing for sidebar widgets
 * @returns {string} HTML string
 */
window.renderErrorState = function(message, { icon = 'bi-exclamation-triangle', variant = 'warning', retry = null, small = false } = {}) {
    const sizeClass = small ? 'py-2 small' : '';
    const retryBtn = retry
        ? `<div class="mt-2"><button type="button" class="btn btn-${variant} btn-sm error-state-retry-btn"><i class="bi bi-arrow-clockwise me-1"></i>Retry</button></div>`
        : '';
    return `
        <div class="alert alert-${variant} ${sizeClass}" role="alert">
            <div class="d-flex align-items-start gap-2">
                <i class="bi ${icon} flex-shrink-0 mt-1" aria-hidden="true"></i>
                <div>
                    <div>${message}</div>
                    ${retryBtn}
                </div>
            </div>
        </div>`;
};

/**
 * Render an error state into a container and bind its retry button.
 * Split from renderErrorState() because that function only returns a
 * string — the retry button has no inline onclick="" (#475: CSP script-src
 * can't allow 'unsafe-inline'), so the callback must be bound after the
 * markup is actually in the DOM.
 * @param {HTMLElement} container
 * @param {string} message
 * @param {object} [opts] - Same options as renderErrorState().
 */
window.renderErrorStateInto = function(container, message, opts = {}) {
    container.innerHTML = window.renderErrorState(message, opts);
    if (opts.retry) {
        const btn = container.querySelector('.error-state-retry-btn');
        if (btn) btn.addEventListener('click', opts.retry);
    }
};

/**
 * Render a consistent empty state with icon and optional suggestion (#93).
 * @param {string} message - Primary empty state message
 * @param {string} [suggestion=''] - Actionable suggestion for the user
 * @param {string} [icon='bi-inbox'] - Bootstrap icon class
 * @returns {string} HTML string
 */
window.renderEmptyState = function(message, suggestion = '', icon = 'bi-inbox') {
    return `
        <div class="text-center py-3 text-muted" role="status">
            <i class="bi ${icon} fs-2 mb-2 d-block opacity-50" aria-hidden="true"></i>
            <div class="small">${message}</div>
            ${suggestion ? `<div class="small mt-1 opacity-75">${suggestion}</div>` : ''}
        </div>`;
};

/**
 * Poll a status endpoint until it reports completion, capping both
 * consecutive-failure count and total duration so a persistently-failing
 * endpoint can't poll forever with a stuck "Running…" button (#468).
 *
 * @param {object} opts
 * @param {function} opts.fetchStatus - async () => job/status object
 * @param {function} opts.onStatus - (job) => 'done'|'error'|'running'.
 *   Inspects the job, updates the caller's UI as a side effect, and
 *   returns the phase so pollJob knows whether to keep polling.
 * @param {function} [opts.onGiveUp] - (reason: 'timeout'|'error') => void.
 *   Called once, in place of onStatus, when polling gives up without ever
 *   seeing 'done'/'error' — the caller's chance to reset its UI to idle.
 * @param {number} [opts.intervalMs=3000] - delay between polls
 * @param {number} [opts.maxConsecutiveFailures=5] - fetchStatus rejections
 *   in a row before giving up
 * @param {number} [opts.maxDurationMs=600000] - hard cap on total poll time
 *   (10 min default) before giving up even if fetchStatus keeps succeeding
 *   with a non-terminal status
 * @returns {function} stop - cancel polling early (e.g. on page navigation)
 */
window.pollJob = function({
    fetchStatus,
    onStatus,
    onGiveUp = null,
    intervalMs = 3000,
    maxConsecutiveFailures = 5,
    maxDurationMs = 600000,
}) {
    const startTime = Date.now();
    let consecutiveFailures = 0;
    let stopped = false;
    let timer = null;

    function stop() {
        stopped = true;
        if (timer) clearTimeout(timer);
    }

    async function tick() {
        if (stopped) return;

        if (Date.now() - startTime > maxDurationMs) {
            stop();
            if (onGiveUp) onGiveUp('timeout');
            return;
        }

        try {
            const job = await fetchStatus();
            consecutiveFailures = 0;
            const phase = onStatus(job);
            if (phase === 'done' || phase === 'error') {
                stop();
                return;
            }
        } catch (e) {
            consecutiveFailures++;
            if (consecutiveFailures >= maxConsecutiveFailures) {
                stop();
                if (onGiveUp) onGiveUp('error');
                return;
            }
        }

        if (!stopped) {
            timer = setTimeout(tick, intervalMs);
        }
    }

    tick();
    return stop;
};

console.log('✓ common.js loaded - Toast, auto-save, undo, unit conversion, and timestamp utilities ready');
