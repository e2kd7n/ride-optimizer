/**
 * Commute View - Client-side logic for commute recommendations
 * 
 * Handles:
 * - Loading commute data from /api/commute
 * - Rendering route cards with metrics
 * - Loading interactive map from /api/commute/map
 * - Card/map interaction (click to highlight and zoom)
 */

(function() {
    'use strict';
    
    let commuteData = null;
    let activeCard = null;
    
    /**
     * Initialize the commute view
     */
    function init() {
        console.log('Initializing commute view...');
        loadCommuteData();
        setupMessageListener();
    }
    
    /**
     * Setup listener for messages from map iframe
     */
    function setupMessageListener() {
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'routeClicked') {
                // Update card selection when polyline is clicked in map
                const direction = event.data.direction;
                const card = document.querySelector(`.commute-card.${direction}`);
                if (card) {
                    handleCardClick(card, direction);
                }
            }
        });
    }
    
    /**
     * Load commute data from API
     */
    async function loadCommuteData() {
        const cardsContainer = document.getElementById('commute-cards');
        
        try {
            const response = await fetch('/api/commute');
            const data = await response.json();
            
            if (data.status === 'success') {
                commuteData = data;
                renderCommuteCards(data);
                loadCommuteMap();
            } else {
                showError(cardsContainer, data.message || 'Failed to load commute data');
            }
        } catch (error) {
            console.error('Error loading commute data:', error);
            showError(cardsContainer, 'Unable to load commute recommendations');
        }
    }
    
    /**
     * Render commute route cards
     */
    function renderCommuteCards(data) {
        const cardsContainer = document.getElementById('commute-cards');
        cardsContainer.innerHTML = '';
        
        // Render To Work card
        if (data.to_work && data.to_work.status === 'success') {
            const toWorkCard = createCommuteCard(data.to_work, 'to-work', '🚴 To Work');
            cardsContainer.appendChild(toWorkCard);
        }
        
        // Render To Home card
        if (data.to_home && data.to_home.status === 'success') {
            const toHomeCard = createCommuteCard(data.to_home, 'to-home', '🏠 To Home');
            cardsContainer.appendChild(toHomeCard);
        }
        
        // If no routes available
        if (cardsContainer.children.length === 0) {
            showError(cardsContainer, 'No commute routes available');
        }
    }
    
    /**
     * Create a commute card element
     */
    function createCommuteCard(recommendation, direction, label) {
        const card = document.createElement('div');
        card.className = `commute-card ${direction}`;
        card.setAttribute('data-direction', direction);
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-label', `${label} route recommendation`);
        
        const route = recommendation.route;
        const score = recommendation.score;
        const scorePercent = typeof score === 'number' ? (score <= 1 ? score * 100 : score) : 0;
        const scoreClass = scorePercent >= 70 ? '' : scorePercent >= 50 ? 'medium' : 'low';
        
        // Format metrics
        const distanceKm = (route.distance / 1000).toFixed(1);
        const distanceMi = (distanceKm * 0.621371).toFixed(1);
        const durationMin = Math.round(route.duration / 60);
        const elevationM = Math.round(route.elevation);
        const elevationFt = Math.round(elevationM * 3.28084);
        
        // Get unit system preference
        const unitSystem = window.getUnitSystem ? window.getUnitSystem() : 'imperial';
        const distance = unitSystem === 'metric' ? `${distanceKm} km` : `${distanceMi} mi`;
        const elevation = unitSystem === 'metric' ? `${elevationM} m` : `${elevationFt} ft`;
        
        // Weather data
        const weather = recommendation.weather || {};
        const temp = weather.temperature ? `${Math.round(weather.temperature)}°F` : 'N/A';
        const wind = weather.wind_speed ? `${Math.round(weather.wind_speed)} mph` : 'N/A';
        const precip = weather.precipitation !== undefined ? `${Math.round(weather.precipitation)}%` : 'N/A';
        
        // Time window
        const timeWindow = recommendation.time_window || 'Today';
        const isToday = recommendation.is_today !== false;
        
        card.innerHTML = `
            <div class="commute-card-header">
                <div class="commute-direction">${label}</div>
                <div class="commute-score ${scoreClass}">${Math.round(scorePercent)}</div>
            </div>
            <div class="commute-route-name">${escapeHtml(route.name)}</div>
            <div class="commute-time-window">
                <i class="bi bi-clock"></i> ${escapeHtml(timeWindow)}
                ${isToday ? '<span class="badge bg-success ms-2">Today</span>' : '<span class="badge bg-info ms-2">Tomorrow</span>'}
            </div>
            <div class="commute-metrics">
                <div class="commute-metric">
                    <i class="bi bi-clock-fill"></i>
                    <span>${durationMin} min</span>
                </div>
                <div class="commute-metric">
                    <i class="bi bi-signpost-fill"></i>
                    <span>${distance}</span>
                </div>
                <div class="commute-metric">
                    <i class="bi bi-thermometer-half"></i>
                    <span>${temp}</span>
                </div>
                <div class="commute-metric">
                    <i class="bi bi-wind"></i>
                    <span>${wind}</span>
                </div>
                <div class="commute-metric">
                    <i class="bi bi-droplet-fill"></i>
                    <span>${precip}</span>
                </div>
                <div class="commute-metric">
                    <i class="bi bi-graph-up"></i>
                    <span>${elevation}</span>
                </div>
            </div>
        `;
        
        // Add click handler
        card.addEventListener('click', () => handleCardClick(card, direction));
        card.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleCardClick(card, direction);
            }
        });
        
        return card;
    }
    
    /**
     * Handle card click - highlight card and zoom map
     */
    function handleCardClick(card, direction) {
        // Remove active class from all cards
        document.querySelectorAll('.commute-card').forEach(c => {
            c.classList.remove('active');
        });
        
        // Add active class to clicked card
        card.classList.add('active');
        activeCard = direction;
        
        // Highlight the selected route's polyline in the map
        highlightRouteOnMap(direction);
        
        // Scroll to card on mobile
        if (window.innerWidth < 768) {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
    
    /**
     * Highlight a route on the map by manipulating polylines via iframe
     */
    function highlightRouteOnMap(direction) {
        const mapIframe = document.getElementById('commute-map-container');
        if (!mapIframe || !mapIframe.contentWindow) {
            console.warn('Map iframe not accessible');
            return;
        }
        
        try {
            // Send message to iframe to highlight the route
            // The iframe will need to listen for this message and update polyline styles
            const message = {
                type: 'highlightRoute',
                direction: direction
            };
            mapIframe.contentWindow.postMessage(message, '*');
        } catch (error) {
            console.error('Failed to communicate with map iframe:', error);
        }
    }
    
    /**
     * Load commute map
     */
    async function loadCommuteMap() {
        const mapContainer = document.getElementById('commute-map-container');
        
        try {
            const response = await fetch('/api/commute/map');
            
            if (response.ok) {
                const mapHtml = await response.text();
                
                // Create a blob URL for the map HTML
                const blob = new Blob([mapHtml], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                
                mapContainer.src = url;
                
                // Clean up blob URL after load
                mapContainer.onload = () => {
                    URL.revokeObjectURL(url);
                };
            } else {
                showMapError(mapContainer, 'Failed to load map');
            }
        } catch (error) {
            console.error('Error loading commute map:', error);
            showMapError(mapContainer, 'Unable to load map');
        }
    }
    
    /**
     * Show error message in cards container
     */
    function showError(container, message) {
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Commute Unavailable</strong>
                </div>
                <p class="mb-2 small">${escapeHtml(message)}</p>
                <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Retry
                </button>
            </div>
        `;
    }
    
    /**
     * Show error message in map container
     */
    function showMapError(container, message) {
        const errorHtml = `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                        font-family: Arial, sans-serif;
                        background: #f8f9fa;
                    }
                    .error-message {
                        text-align: center;
                        padding: 2rem;
                    }
                    .error-icon {
                        font-size: 3rem;
                        color: #ffc107;
                        margin-bottom: 1rem;
                    }
                </style>
            </head>
            <body>
                <div class="error-message">
                    <div class="error-icon">⚠️</div>
                    <h3>Map Unavailable</h3>
                    <p>${escapeHtml(message)}</p>
                </div>
            </body>
            </html>
        `;
        
        const blob = new Blob([errorHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        container.src = url;
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

// Made with Bob
