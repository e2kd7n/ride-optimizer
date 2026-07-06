/**
 * API Client for Ride Optimizer Smart Static Architecture
 * Handles all API communication with error handling and retry logic
 */

class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.retryAttempts = 3;
        this.retryDelay = 1000; // ms
        this.timeout = 10000; // 10 second timeout
        this._csrfToken = null;
        this._csrfReady = this._fetchCsrfToken();
    }

    async _fetchCsrfToken() {
        try {
            const response = await fetch(`${this.baseURL}/csrf-token`);
            if (response.ok) {
                const data = await response.json();
                this._csrfToken = data.csrf_token;
            }
        } catch (e) {
            // Non-fatal: SameSite=Lax cookies still protect against cross-origin mutations
        }
    }

    /**
     * Map HTTP status codes to user-friendly messages
     */
    getErrorMessage(status, error) {
        const messages = {
            400: 'Invalid request. Please check your input.',
            401: 'Authentication required. Please log in.',
            403: 'Access denied. You do not have permission.',
            404: 'Data not found. The requested resource does not exist.',
            408: 'Request timeout. Please try again.',
            429: 'Too many requests. Please wait a moment.',
            500: 'Server error. Please try again later.',
            502: 'Bad gateway. The server is temporarily unavailable.',
            503: 'Service temporarily unavailable. Please try again later.',
            504: 'Gateway timeout. The server took too long to respond.'
        };

        if (status && messages[status]) {
            return messages[status];
        }

        // Network errors
        if (error && error.name === 'TypeError' && error.message.includes('fetch')) {
            return 'Unable to connect. Please check your internet connection.';
        }

        if (error && error.name === 'AbortError') {
            return 'Request timeout. The server took too long to respond.';
        }

        return 'An unexpected error occurred. Please try again.';
    }

    /**
     * Generic fetch wrapper with error handling and retry logic
     */
    async fetch(endpoint, options = {}) {
        const { timeoutMs, ...fetchOptions } = options;
        const url = `${this.baseURL}${endpoint}`;
        const method = (fetchOptions.method || 'GET').toUpperCase();
        const isMutation = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

        // Ensure CSRF token is ready before any state-changing request
        if (isMutation) {
            await this._csrfReady;
        }

        let lastError;
        let lastStatus;

        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs || this.timeout);

            try {
                const response = await fetch(url, {
                    ...fetchOptions,
                    headers: {
                        'Content-Type': 'application/json',
                        ...(isMutation && this._csrfToken ? { 'X-CSRFToken': this._csrfToken } : {}),
                        ...fetchOptions.headers
                    },
                    signal: controller.signal
                });

                clearTimeout(timeoutId);
                lastStatus = response.status;

                if (!response.ok) {
                    let serverMessage = null;
                    try {
                        const body = await response.json();
                        serverMessage = body.error || body.message || null;
                    } catch (_) {}
                    const errorMessage = serverMessage || this.getErrorMessage(response.status);
                    const error = new Error(errorMessage);
                    error.status = response.status;
                    error.statusText = response.statusText;
                    throw error;
                }

                const data = await response.json();
                
                // Log successful retry if not first attempt
                if (attempt > 0) {
                    console.log(`✓ Request succeeded on attempt ${attempt + 1}`);
                }
                
                return data;
            } catch (error) {
                clearTimeout(timeoutId);
                lastError = error;
                
                // Log error details for debugging
                console.error(`API request failed (attempt ${attempt + 1}/${this.retryAttempts}):`, {
                    endpoint,
                    error: error.message,
                    status: error.status
                });
                
                // Don't retry on client errors (4xx) except 408 (timeout) and 429 (rate limit)
                // Don't retry on server errors (5xx) — these are deterministic failures (misconfiguration, etc.)
                if (error.status && error.status >= 400 && error.status < 500) {
                    if (error.status !== 408 && error.status !== 429) {
                        throw error;
                    }
                }
                if (error.status && error.status >= 500) {
                    throw error;
                }
                
                // If this was the last attempt, throw the error
                if (attempt === this.retryAttempts - 1) {
                    throw error;
                }
                
                // Exponential backoff: 1s, 2s, 4s
                const delay = this.retryDelay * Math.pow(2, attempt);
                console.log(`Retrying in ${delay}ms...`);
                await this.sleep(delay);
            }
        }

        throw lastError;
    }

    /**
     * Sleep utility for retry delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get system status
     */
    async getStatus() {
        return this.fetch('/status');
    }

    /**
     * Get current weather data
     */
    async getWeather() {
        return this.fetch('/weather');
    }

    async getForecast() {
        return this.fetch('/weather/forecast');
    }

    async getHourlyForecast() {
        return this.fetch('/weather/hourly');
    }

    /**
     * Get next commute recommendation
     */
    async getRecommendation() {
        return this.fetch('/recommendation');
    }

    /**
     * Get all routes with optional filters
     */
    async getRoutes(filters = {}) {
        const params = new URLSearchParams();
        
        if (filters.favorite !== undefined) {
            params.append('favorite', filters.favorite);
        }
        if (filters.sport_type) {
            params.append('sport_type', filters.sport_type);
        }
        if (filters.min_distance) {
            params.append('min_distance', filters.min_distance);
        }
        if (filters.max_distance) {
            params.append('max_distance', filters.max_distance);
        }

        const queryString = params.toString();
        const endpoint = queryString ? `/routes?${queryString}` : '/routes';
        
        return this.fetch(endpoint);
    }

    /**
     * Get route details by route ID
     */
    async getRouteDetails(routeId, routeType = null) {
        const params = new URLSearchParams();

        if (routeType) {
            params.append('type', routeType);
        }

        const queryString = params.toString();
        const endpoint = queryString
            ? `/routes/${encodeURIComponent(routeId)}?${queryString}`
            : `/routes/${encodeURIComponent(routeId)}`;

        return this.fetch(endpoint);
    }

    /**
     * Toggle route favorite status
     */
    async toggleFavorite(routeId) {
        return this.fetch(`/routes/${routeId}/favorite`, {
            method: 'POST'
        });
    }

    /**
     * Get Strava OAuth connection status
     */
    async getStravaStatus() {
        return this.fetch('/strava/status');
    }

    /**
     * Get local activity cache stats (count, date range, size, age)
     */
    async getCacheInfo() {
        return this.fetch('/cache-info');
    }

    /**
     * Trigger a background analysis run.
     * @param {Object} options
     * @param {boolean} options.fetchNew  true = pull from Strava first; false = reanalyze cache only
     */
    async triggerAnalysis(options = {}) {
        const body = { fetch_new: options.fetchNew || false };
        if (options.afterDate) body.after_date = options.afterDate;
        if (options.beforeDate) body.before_date = options.beforeDate;
        return this.fetch('/analyze', {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    /**
     * Poll the current analysis job status
     */
    async getAnalysisStatus() {
        return this.fetch('/analyze/status');
    }

    // ── TrainerRoad ────────────────────────────────────────────

    async getTrainerRoadStatus() {
        return this.fetch('/trainerroad/status');
    }

    async connectTrainerRoad(feedUrl) {
        return this.fetch('/trainerroad/connect', {
            method: 'POST',
            body: JSON.stringify({ feed_url: feedUrl }),
        });
    }

    async syncTrainerRoad() {
        return this.fetch('/trainerroad/sync', { method: 'POST' });
    }

    async disconnectTrainerRoad() {
        return this.fetch('/trainerroad/disconnect', { method: 'POST' });
    }

    async getTrainerRoadWorkouts() {
        return this.fetch('/trainerroad/workouts');
    }

    async getTrainerRoadToday() {
        return this.fetch('/trainerroad/today');
    }

    // ── Exploration / Coverage ───────────────────────────────

    async getTileCoverage(bounds = null, zoom = null) {
        // Coverage is computed from scratch (no cache) on the first request
        // after each activity sync and can take 30s+ over a large ride history.
        const timeoutMs = 45000;
        const params = new URLSearchParams();
        if (bounds) {
            params.set('south', bounds.south);
            params.set('west', bounds.west);
            params.set('north', bounds.north);
            params.set('east', bounds.east);
        }
        if (zoom) params.set('zoom', zoom);
        const qs = params.toString();
        return this.fetch(`/exploration/tiles${qs ? '?' + qs : ''}`, { timeoutMs });
    }

    async getRoadCoverage(bounds) {
        const params = new URLSearchParams({
            south: bounds.south, west: bounds.west,
            north: bounds.north, east: bounds.east,
        });
        return this.fetch(`/exploration/roads?${params}`);
    }

    async invalidateCoverageCache() {
        return this.fetch('/exploration/invalidate', { method: 'POST' });
    }

    async getExplorationRoute({ waypoints, surfacePreference = 'any', exclude } = {}) {
        // Route computation involves a live ORS call; allow generous timeout.
        const body = { waypoints, surface_preference: surfacePreference };
        if (exclude) body.exclude = exclude;
        return this.fetch('/exploration/route', {
            method: 'POST',
            timeoutMs: 60000,
            body: JSON.stringify(body),
        });
    }

    /**
     * Forward-geocode a city/state or postal code to coordinates.
     */
    async geocodeLocation(query) {
        const params = new URLSearchParams({ query });
        return this.fetch(`/geocode?${params}`);
    }

    // ── Planner / Long Rides ─────────────────────────────────

    async getLongRideRecommendations(options = {}) {
        const params = new URLSearchParams();
        if (options.forecastDays) params.append('forecast_days', options.forecastDays);
        if (options.minDistance) params.append('min_distance', options.minDistance);
        if (options.maxDistance) params.append('max_distance', options.maxDistance);
        const qs = params.toString();
        return this.fetch(`/planner/recommendations${qs ? '?' + qs : ''}`);
    }

    async getRidesNearLocation(lat, lon, options = {}) {
        const params = new URLSearchParams({ lat, lon });
        if (options.radiusMiles) params.append('radius_miles', options.radiusMiles);
        if (options.limit) params.append('limit', options.limit);
        return this.fetch(`/planner/rides/nearby?${params}`);
    }

    async getLongRideDetails(rideId) {
        return this.fetch(`/planner/rides/${encodeURIComponent(rideId)}`);
    }

    async analyzeLongRide(distance, duration, date = null) {
        const body = { distance, duration };
        if (date) body.date = date;
        return this.fetch('/planner/analyze', {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    // ── Saved Plans ────────────────────────────────────────

    async getPlans() {
        return this.fetch('/plans');
    }

    async savePlan(planData) {
        return this.fetch('/plans', {
            method: 'POST',
            body: JSON.stringify(planData),
        });
    }

    async deletePlan(planId) {
        return this.fetch(`/plans/${planId}`, {
            method: 'DELETE',
        });
    }

    async get(endpoint) {
        return this.fetch(endpoint, { method: 'GET' });
    }

    async post(endpoint, body) {
        return this.fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }
}

// Create global API client instance
window.apiClient = new APIClient();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}

// Made with Bob
