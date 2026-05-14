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
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            return 'Unable to connect. Please check your internet connection.';
        }

        if (error.name === 'AbortError') {
            return 'Request timeout. The server took too long to respond.';
        }

        return 'An unexpected error occurred. Please try again.';
    }

    /**
     * Generic fetch wrapper with error handling and retry logic
     */
    async fetch(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        let lastError;
        let lastStatus;

        for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            try {
                const response = await fetch(url, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    signal: controller.signal
                });

                clearTimeout(timeoutId);
                lastStatus = response.status;

                if (!response.ok) {
                    const errorMessage = this.getErrorMessage(response.status);
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
                if (error.status && error.status >= 400 && error.status < 500) {
                    if (error.status !== 408 && error.status !== 429) {
                        throw error;
                    }
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
}

// Create global API client instance
window.apiClient = new APIClient();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}

// Made with Bob
