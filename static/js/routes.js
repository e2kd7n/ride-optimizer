/**
 * routes.js - Route management utilities for Ride Optimizer
 * Epic #237 - UI/UX Redesign
 * 
 * Features:
 * - Compact route card component (Issue #247)
 * - Skeleton loading states (Issue #248)
 * - Route filtering and sorting
 * - Route selection and highlighting
 * - Touch target validation (Issue #250)
 */

/**
 * Creates a compact route card (56px height) with all required information
 * @param {Object} routeData - Route data object
 * @param {number} routeData.rank - Route ranking (1-based)
 * @param {string} routeData.id - Route ID
 * @param {string} routeData.name - Route name
 * @param {number} routeData.score - Route score
 * @param {number} routeData.distance - Distance in meters
 * @param {number} routeData.duration - Duration in seconds
 * @param {number} routeData.elevation - Elevation gain in meters (optional)
 * @param {Object} routeData.weather - Weather data (optional)
 * @param {boolean} routeData.isOptimal - Whether this is the optimal route
 * @param {Function} routeData.onClick - Click handler (optional)
 * @returns {HTMLElement} The compact route card element
 */
window.createCompactRouteCard = function(routeData) {
    const card = document.createElement('div');
    card.className = 'route-card-compact';
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('data-route-id', routeData.id);
    card.setAttribute('aria-label', `Route ${routeData.rank}: ${routeData.name}, Score ${routeData.score.toFixed(1)}`);
    
    if (routeData.isOptimal) {
        card.classList.add('optimal');
        card.setAttribute('aria-label', `Optimal route: ${routeData.name}, Score ${routeData.score.toFixed(1)}`);
    }
    
    // Rank
    const rank = document.createElement('div');
    rank.className = 'route-card-compact-rank';
    rank.textContent = routeData.rank;
    card.appendChild(rank);
    
    // Name
    const name = document.createElement('div');
    name.className = 'route-card-compact-name';
    name.textContent = routeData.name;
    name.title = routeData.name; // Full name on hover
    card.appendChild(name);
    
    // Metrics container
    const metrics = document.createElement('div');
    metrics.className = 'route-card-compact-metrics';
    
    // Score
    const scoreMetric = document.createElement('div');
    scoreMetric.className = 'route-card-compact-metric';
    scoreMetric.innerHTML = `
        <span class="route-card-compact-metric-icon">⭐</span>
        <span class="route-card-compact-score">${routeData.score.toFixed(1)}</span>
    `;
    metrics.appendChild(scoreMetric);
    
    // Distance
    const distanceMetric = document.createElement('div');
    distanceMetric.className = 'route-card-compact-metric';
    const distanceKm = (routeData.distance / 1000).toFixed(1);
    distanceMetric.innerHTML = `
        <span class="route-card-compact-metric-icon">📏</span>
        <span>${distanceKm} km</span>
    `;
    metrics.appendChild(distanceMetric);
    
    // Duration
    const durationMetric = document.createElement('div');
    durationMetric.className = 'route-card-compact-metric';
    const durationMin = Math.round(routeData.duration / 60);
    durationMetric.innerHTML = `
        <span class="route-card-compact-metric-icon">⏱️</span>
        <span>${durationMin} min</span>
    `;
    metrics.appendChild(durationMetric);
    
    // Elevation (optional)
    if (routeData.elevation !== undefined && routeData.elevation > 0) {
        const elevationMetric = document.createElement('div');
        elevationMetric.className = 'route-card-compact-metric';
        elevationMetric.innerHTML = `
            <span class="route-card-compact-metric-icon">⛰️</span>
            <span>${Math.round(routeData.elevation)} m</span>
        `;
        metrics.appendChild(elevationMetric);
    }
    
    // Weather (optional)
    if (routeData.weather) {
        const weatherDiv = document.createElement('div');
        weatherDiv.className = `route-card-compact-weather ${routeData.weather.favorability || 'neutral'}`;
        weatherDiv.innerHTML = `
            <span>${routeData.weather.icon || '🌬️'}</span>
            <span>${routeData.weather.label || 'Wind'}</span>
        `;
        weatherDiv.title = routeData.weather.tooltip || '';
        metrics.appendChild(weatherDiv);
    }
    
    card.appendChild(metrics);
    
    // Click handler
    const handleClick = routeData.onClick || function() {
        card.classList.toggle('selected');
        // Announce selection to screen readers
        const isSelected = card.classList.contains('selected');
        card.setAttribute('aria-pressed', isSelected);
        
        if (window.announceToScreenReader) {
            announceToScreenReader(`Route ${isSelected ? 'selected' : 'deselected'}`);
        }
    };
    
    card.addEventListener('click', handleClick);
    card.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
        }
    });
    
    return card;
};

/**
 * Creates a skeleton loader for route cards
 * @param {number} count - Number of skeleton cards to create
 * @returns {HTMLElement} Container with skeleton cards
 */
window.createSkeletonRouteCards = function(count = 5) {
    const container = document.createElement('div');
    container.className = 'skeleton-container';
    container.setAttribute('aria-busy', 'true');
    container.setAttribute('aria-label', 'Loading routes');
    
    for (let i = 0; i < count; i++) {
        const card = document.createElement('div');
        card.className = 'skeleton-route-card';
        
        const rank = document.createElement('div');
        rank.className = 'skeleton skeleton-route-card-rank';
        card.appendChild(rank);
        
        const name = document.createElement('div');
        name.className = 'skeleton skeleton-route-card-name';
        card.appendChild(name);
        
        const metrics = document.createElement('div');
        metrics.className = 'skeleton-route-card-metrics';
        
        for (let j = 0; j < 4; j++) {
            const metric = document.createElement('div');
            metric.className = 'skeleton skeleton-route-card-metric';
            metrics.appendChild(metric);
        }
        
        card.appendChild(metrics);
        container.appendChild(card);
    }
    
    return container;
};

/**
 * Creates a skeleton loader for map
 * @returns {HTMLElement} Skeleton map element
 */
window.createSkeletonMap = function() {
    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton skeleton-map';
    skeleton.setAttribute('aria-busy', 'true');
    skeleton.setAttribute('aria-label', 'Loading map');
    return skeleton;
};

/**
 * Creates a skeleton loader for weather widget
 * @returns {HTMLElement} Skeleton weather element
 */
window.createSkeletonWeather = function() {
    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton-weather';
    skeleton.setAttribute('aria-busy', 'true');
    skeleton.setAttribute('aria-label', 'Loading weather');
    
    const header = document.createElement('div');
    header.className = 'skeleton skeleton-weather-header';
    skeleton.appendChild(header);
    
    const metrics = document.createElement('div');
    metrics.className = 'skeleton-weather-metrics';
    
    for (let i = 0; i < 4; i++) {
        const metric = document.createElement('div');
        metric.className = 'skeleton skeleton-weather-metric';
        metrics.appendChild(metric);
    }
    
    skeleton.appendChild(metrics);
    return skeleton;
};

/**
 * Creates a generic skeleton card
 * @param {Object} options - Configuration options
 * @param {number} options.lines - Number of content lines (default: 3)
 * @param {string} options.headerWidth - Width of header (default: '150px')
 * @returns {HTMLElement} Skeleton card element
 */
window.createSkeletonCard = function(options = {}) {
    const { lines = 3, headerWidth = '150px' } = options;
    
    const card = document.createElement('div');
    card.className = 'skeleton-card';
    card.setAttribute('aria-busy', 'true');
    card.setAttribute('aria-label', 'Loading content');
    
    const header = document.createElement('div');
    header.className = 'skeleton skeleton-card-header';
    header.style.width = headerWidth;
    card.appendChild(header);
    
    const content = document.createElement('div');
    content.className = 'skeleton-card-content';
    
    const widths = ['long', 'medium', 'short'];
    for (let i = 0; i < lines; i++) {
        const line = document.createElement('div');
        line.className = `skeleton skeleton-card-line ${widths[i % widths.length]}`;
        content.appendChild(line);
    }
    
    card.appendChild(content);
    return card;
};

/**
 * Replaces skeleton with real content
 * @param {HTMLElement} container - Container with skeleton
 * @param {HTMLElement} realContent - Real content to show
 */
window.replaceSkeletonWithContent = function(container, realContent) {
    if (!container || !realContent) return;
    
    // Mark container as loaded
    container.classList.add('loaded');
    container.setAttribute('aria-busy', 'false');
    
    // Add real content
    realContent.classList.add('real-content');
    container.appendChild(realContent);
    
    // Remove skeleton after fade-in animation
    setTimeout(() => {
        const skeletons = container.querySelectorAll('.skeleton, .skeleton-route-card, .skeleton-map, .skeleton-weather, .skeleton-card');
        skeletons.forEach(s => s.remove());
    }, 300);
};

/**
 * Validates that all interactive elements meet 44x44px minimum touch target size
 * Useful for development and testing
 * @returns {Object} Validation results with failing elements
 */
window.validateTouchTargets = function() {
    const MIN_SIZE = 44;
    const selectors = [
        'button',
        'a',
        'input[type="checkbox"]',
        'input[type="radio"]',
        '.btn',
        '.nav-link',
        '.btn-close',
        '.route-card-compact'
    ];
    
    const results = {
        passed: [],
        failed: [],
        warnings: []
    };
    
    selectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            const rect = el.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;
            
            // Check if element meets minimum size
            if (width >= MIN_SIZE && height >= MIN_SIZE) {
                results.passed.push({
                    element: el,
                    selector: selector,
                    size: `${Math.round(width)}x${Math.round(height)}px`
                });
            } else if (width < MIN_SIZE || height < MIN_SIZE) {
                // Check if it's an exception (inline text links, etc.)
                const isException = el.closest('p') || el.closest('li') || el.classList.contains('inline-link');
                
                if (isException) {
                    results.warnings.push({
                        element: el,
                        selector: selector,
                        size: `${Math.round(width)}x${Math.round(height)}px`,
                        reason: 'Inline text link (exception)'
                    });
                } else {
                    results.failed.push({
                        element: el,
                        selector: selector,
                        size: `${Math.round(width)}x${Math.round(height)}px`,
                        required: `${MIN_SIZE}x${MIN_SIZE}px`
                    });
                }
            }
        });
    });
    
    // Log results
    console.group('Touch Target Validation');
    console.log(`✅ Passed: ${results.passed.length} elements`);
    console.log(`⚠️  Warnings: ${results.warnings.length} elements (exceptions)`);
    console.log(`❌ Failed: ${results.failed.length} elements`);
    
    if (results.failed.length > 0) {
        console.group('Failed Elements');
        results.failed.forEach(item => {
            console.log(`${item.selector}: ${item.size} (required: ${item.required})`, item.element);
        });
        console.groupEnd();
    }
    
    if (results.warnings.length > 0) {
        console.group('Warnings (Exceptions)');
        results.warnings.forEach(item => {
            console.log(`${item.selector}: ${item.size} - ${item.reason}`, item.element);
        });
        console.groupEnd();
    }
    
    console.groupEnd();
    
    return results;
};

/**
 * Enables visual debugging of touch targets
 * Adds dashed borders around all interactive elements to show 44x44px minimum
 */
window.debugTouchTargets = function(enable = true) {
    if (enable) {
        document.body.classList.add('debug-touch-targets');
        console.log('Touch target debugging enabled. Dashed borders show 44x44px minimum.');
    } else {
        document.body.classList.remove('debug-touch-targets');
        console.log('Touch target debugging disabled.');
    }
};

/**
 * Route filtering utility
 * @param {Array} routes - Array of route objects
 * @param {Object} filters - Filter criteria
 * @returns {Array} Filtered routes
 */
window.filterRoutes = function(routes, filters = {}) {
    return routes.filter(route => {
        // Distance filter
        if (filters.minDistance && route.distance < filters.minDistance * 1000) {
            return false;
        }
        if (filters.maxDistance && route.distance > filters.maxDistance * 1000) {
            return false;
        }
        
        // Duration filter
        if (filters.minDuration && route.duration < filters.minDuration * 60) {
            return false;
        }
        if (filters.maxDuration && route.duration > filters.maxDuration * 60) {
            return false;
        }
        
        // Elevation filter
        if (filters.maxElevation && route.elevation > filters.maxElevation) {
            return false;
        }
        
        // Score filter
        if (filters.minScore && route.score < filters.minScore) {
            return false;
        }
        
        // Favorite filter
        if (filters.favoritesOnly) {
            const favorites = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
            if (!favorites.includes(route.id)) {
                return false;
            }
        }
        
        // Hidden routes filter
        const hiddenRoutes = JSON.parse(localStorage.getItem('hiddenRoutes') || '[]');
        if (hiddenRoutes.includes(route.id)) {
            return false;
        }
        
        return true;
    });
};

/**
 * Route sorting utility
 * @param {Array} routes - Array of route objects
 * @param {string} sortBy - Sort field ('score', 'distance', 'duration', 'elevation')
 * @param {string} direction - Sort direction ('asc' or 'desc')
 * @returns {Array} Sorted routes
 */
window.sortRoutes = function(routes, sortBy = 'score', direction = 'desc') {
    return routes.sort((a, b) => {
        let aVal, bVal;
        
        switch(sortBy) {
            case 'score':
                aVal = a.score;
                bVal = b.score;
                break;
            case 'distance':
                aVal = a.distance;
                bVal = b.distance;
                break;
            case 'duration':
                aVal = a.duration;
                bVal = b.duration;
                break;
            case 'elevation':
                aVal = a.elevation || 0;
                bVal = b.elevation || 0;
                break;
            case 'name':
                aVal = a.name.toLowerCase();
                bVal = b.name.toLowerCase();
                break;
            default:
                return 0;
        }
        
        if (direction === 'asc') {
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        } else {
            return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
        }
    });
};

/**
 * Toggle route favorite status
 * @param {string} routeId - Route ID
 */
window.toggleRouteFavorite = function(routeId) {
    const favorites = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
    const index = favorites.indexOf(routeId);
    
    if (index > -1) {
        // Remove from favorites
        favorites.splice(index, 1);
        if (window.showToast) {
            showToast('Route removed from favorites', 'info', { duration: 2000 });
        }
    } else {
        // Add to favorites
        favorites.push(routeId);
        if (window.showToast) {
            showToast('Route added to favorites', 'success', { duration: 2000 });
        }
    }
    
    localStorage.setItem('favoriteRoutes', JSON.stringify(favorites));
    
    // Announce to screen readers
    if (window.announceToScreenReader) {
        announceToScreenReader(index > -1 ? 'Route unfavorited' : 'Route favorited');
    }
};

/**
 * Check if route is favorited
 * @param {string} routeId - Route ID
 * @returns {boolean} True if favorited
 */
window.isRouteFavorited = function(routeId) {
    const favorites = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
    return favorites.includes(routeId);
};

console.log('✓ routes.js loaded - Route cards, skeleton loaders, and utilities ready');

// Made with Bob
