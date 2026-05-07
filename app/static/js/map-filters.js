/**
 * Map Filters and Route Selection for Folium/Leaflet Maps
 * 
 * Provides interactive filtering and click-to-select functionality for route comparison maps.
 * Works with Folium-generated Leaflet maps embedded in Flask templates.
 */

(function() {
    'use strict';
    
    /**
     * Initialize map filters and route selection for commute comparison page
     */
    function initCommuteMapFilters() {
        const mapContainer = document.getElementById('commute-comparison-map');
        if (!mapContainer) return;
        
        // Wait for Folium map to load
        waitForMap(mapContainer).then((map) => {
            console.log('Commute map loaded, initializing filters');
            
            // Setup route selection
            setupRouteSelection(map);
            
            // Setup filter controls
            setupFilterControls();
        }).catch(err => {
            console.warn('Could not initialize map filters:', err);
        });
    }
    
    /**
     * Wait for Folium/Leaflet map to be fully loaded
     */
    function waitForMap(container, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            function checkMap() {
                // Check for iframe (Folium embeds maps in iframes)
                const iframe = container.querySelector('iframe');
                if (iframe) {
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        const mapDiv = iframeDoc.querySelector('.folium-map');
                        
                        if (mapDiv && window.L) {
                            // Try to get the Leaflet map instance
                            const mapId = mapDiv.id;
                            const map = iframe.contentWindow[mapId];
                            
                            if (map && map._layers) {
                                resolve({ map, iframe, iframeDoc });
                                return;
                            }
                        }
                    } catch (e) {
                        // Cross-origin iframe, can't access
                        console.warn('Cannot access iframe map (cross-origin)');
                    }
                }
                
                // Check if we've exceeded timeout
                if (Date.now() - startTime > timeout) {
                    reject(new Error('Map load timeout'));
                    return;
                }
                
                setTimeout(checkMap, 100);
            }
            
            checkMap();
        });
    }
    
    /**
     * Setup route selection (click route card to highlight on map)
     */
    function setupRouteSelection(mapData) {
        const routeCards = document.querySelectorAll('.route-option-card');
        
        routeCards.forEach(card => {
            card.addEventListener('click', function() {
                const routeId = this.dataset.routeId;
                
                // Remove previous selection
                document.querySelectorAll('.route-option-card').forEach(c => {
                    c.classList.remove('route-selected');
                });
                
                // Add selection to clicked card
                this.classList.add('route-selected');
                
                // Scroll card into view
                this.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest'
                });
                
                // TODO: Highlight route on map (requires map layer access)
                console.log('Selected route:', routeId);
            });
        });
    }
    
    /**
     * Setup filter controls
     */
    function setupFilterControls() {
        // Check if filter panel exists
        const filterPanel = document.getElementById('map-filter-panel');
        if (!filterPanel) {
            // Create filter panel if it doesn't exist
            createFilterPanel();
        }
        
        // Setup filter event listeners
        setupFilterEventListeners();
    }
    
    /**
     * Create filter panel HTML
     */
    function createFilterPanel() {
        const comparisonSection = document.querySelector('.comparison-section');
        if (!comparisonSection) return;
        
        const filterHTML = `
            <div id="map-filter-panel" class="map-filter-panel">
                <button id="filter-toggle-btn" class="filter-toggle-btn d-lg-none" aria-label="Toggle filters">
                    <i class="bi bi-funnel"></i> Filters
                </button>
                
                <div class="filter-controls" id="filter-controls">
                    <div class="filter-header">
                        <h3>Filter Routes</h3>
                        <button id="filter-reset-btn" class="btn-reset">Reset</button>
                    </div>
                    
                    <div class="filter-group">
                        <label for="filter-distance-min">Distance (km)</label>
                        <div class="range-inputs">
                            <input type="number" id="filter-distance-min" min="0" max="50" value="0" step="1">
                            <span>to</span>
                            <input type="number" id="filter-distance-max" min="0" max="50" value="50" step="1">
                        </div>
                    </div>
                    
                    <div class="filter-group">
                        <label for="filter-duration-min">Duration (min)</label>
                        <div class="range-inputs">
                            <input type="number" id="filter-duration-min" min="0" max="180" value="0" step="5">
                            <span>to</span>
                            <input type="number" id="filter-duration-max" min="0" max="180" value="180" step="5">
                        </div>
                    </div>
                    
                    <div class="filter-group">
                        <label>Route Score</label>
                        <div class="checkbox-group">
                            <label class="checkbox-label">
                                <input type="checkbox" class="filter-score-checkbox" value="optimal" checked>
                                <span>Optimal (85%+)</span>
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" class="filter-score-checkbox" value="good" checked>
                                <span>Good (70-84%)</span>
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" class="filter-score-checkbox" value="acceptable" checked>
                                <span>Acceptable (50-69%)</span>
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" class="filter-score-checkbox" value="unfavorable" checked>
                                <span>Unfavorable (<50%)</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="filter-results">
                        <span id="filter-visible-count">All routes visible</span>
                    </div>
                </div>
            </div>
        `;
        
        // Insert before comparison layout
        const comparisonLayout = comparisonSection.querySelector('.comparison-layout');
        if (comparisonLayout) {
            comparisonLayout.insertAdjacentHTML('beforebegin', filterHTML);
        }
    }
    
    /**
     * Setup filter event listeners
     */
    function setupFilterEventListeners() {
        // Mobile filter toggle
        const toggleBtn = document.getElementById('filter-toggle-btn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleFilterPanel);
        }
        
        // Reset button
        const resetBtn = document.getElementById('filter-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetFilters);
        }
        
        // Filter inputs
        const filterInputs = document.querySelectorAll(
            '#filter-distance-min, #filter-distance-max, ' +
            '#filter-duration-min, #filter-duration-max, ' +
            '.filter-score-checkbox'
        );
        
        filterInputs.forEach(input => {
            input.addEventListener('change', debounce(applyFilters, 300));
        });
    }
    
    /**
     * Toggle filter panel (mobile)
     */
    function toggleFilterPanel() {
        const filterControls = document.getElementById('filter-controls');
        if (filterControls) {
            filterControls.classList.toggle('filter-panel-open');
        }
    }
    
    /**
     * Reset all filters
     */
    function resetFilters() {
        document.getElementById('filter-distance-min').value = 0;
        document.getElementById('filter-distance-max').value = 50;
        document.getElementById('filter-duration-min').value = 0;
        document.getElementById('filter-duration-max').value = 180;
        
        document.querySelectorAll('.filter-score-checkbox').forEach(cb => {
            cb.checked = true;
        });
        
        applyFilters();
    }
    
    /**
     * Apply current filters to route cards
     */
    function applyFilters() {
        const distanceMin = parseFloat(document.getElementById('filter-distance-min').value);
        const distanceMax = parseFloat(document.getElementById('filter-distance-max').value);
        const durationMin = parseFloat(document.getElementById('filter-duration-min').value);
        const durationMax = parseFloat(document.getElementById('filter-duration-max').value);
        
        const scoreFilters = Array.from(document.querySelectorAll('.filter-score-checkbox:checked'))
            .map(cb => cb.value);
        
        const routeCards = document.querySelectorAll('.route-option-card');
        let visibleCount = 0;
        
        routeCards.forEach(card => {
            const distance = parseFloat(card.querySelector('.route-option-metric:nth-child(1) span:nth-child(2)')?.textContent) || 0;
            const duration = parseFloat(card.querySelector('.route-option-metric:nth-child(2) span:nth-child(2)')?.textContent) || 0;
            const scoreText = card.querySelector('.route-option-score')?.textContent || '0';
            const score = parseInt(scoreText.replace('%', ''));
            
            // Determine score category
            let scoreCategory = 'unfavorable';
            if (score >= 85) scoreCategory = 'optimal';
            else if (score >= 70) scoreCategory = 'good';
            else if (score >= 50) scoreCategory = 'acceptable';
            
            // Check if route matches filters
            const matchesDistance = distance >= distanceMin && distance <= distanceMax;
            const matchesDuration = duration >= durationMin && duration <= durationMax;
            const matchesScore = scoreFilters.includes(scoreCategory);
            
            const visible = matchesDistance && matchesDuration && matchesScore;
            
            card.style.display = visible ? '' : 'none';
            if (visible) visibleCount++;
        });
        
        // Update visible count
        const countElement = document.getElementById('filter-visible-count');
        if (countElement) {
            countElement.textContent = `${visibleCount} of ${routeCards.length} routes visible`;
        }
        
        // Save filter state
        saveFilterState({
            distanceMin, distanceMax,
            durationMin, durationMax,
            scoreFilters
        });
    }
    
    /**
     * Save filter state to localStorage
     */
    function saveFilterState(filters) {
        try {
            localStorage.setItem('commuteMapFilters', JSON.stringify(filters));
        } catch (e) {
            console.warn('Could not save filter state:', e);
        }
    }
    
    /**
     * Load filter state from localStorage
     */
    function loadFilterState() {
        try {
            const saved = localStorage.getItem('commuteMapFilters');
            if (saved) {
                const filters = JSON.parse(saved);
                
                if (document.getElementById('filter-distance-min')) {
                    document.getElementById('filter-distance-min').value = filters.distanceMin || 0;
                    document.getElementById('filter-distance-max').value = filters.distanceMax || 50;
                    document.getElementById('filter-duration-min').value = filters.durationMin || 0;
                    document.getElementById('filter-duration-max').value = filters.durationMax || 180;
                    
                    document.querySelectorAll('.filter-score-checkbox').forEach(cb => {
                        cb.checked = filters.scoreFilters.includes(cb.value);
                    });
                    
                    applyFilters();
                }
            }
        } catch (e) {
            console.warn('Could not load filter state:', e);
        }
    }
    
    /**
     * Debounce function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initCommuteMapFilters();
            loadFilterState();
        });
    } else {
        initCommuteMapFilters();
        loadFilterState();
    }
    
})();

// Made with Bob
