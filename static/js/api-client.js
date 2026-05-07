/**
 * API Client for Ride Optimizer Smart Static Architecture
 * Handles all API communication with error handling and retry logic
 */

class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.retryAttempts = 3;
        this.retryDelay = 1000; // ms
    }

    /**
     * Generic fetch wrapper with error handling and retry logic
     */
    async fetch(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        let lastError;

        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                return data;
            } catch (error) {
                lastError = error;
                console.warn(`API request failed (attempt ${attempt + 1}/${this.retryAttempts}):`, error);
                
                if (attempt < this.retryAttempts - 1) {
                    await this.sleep(this.retryDelay * (attempt + 1));
                }
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
     * Toggle route favorite status
     */
    async toggleFavorite(routeId) {
        return this.fetch(`/routes/${routeId}/favorite`, {
            method: 'POST'
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
