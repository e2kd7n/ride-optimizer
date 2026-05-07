/**
 * Routes page logic with client-side filtering, sorting, and pagination
 */

// State management
let allRoutes = [];
let filteredRoutes = [];
let currentPage = 1;
const routesPerPage = 12;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadRoutes();
    setupEventListeners();
});

/**
 * Setup event listeners for filters and controls
 */
function setupEventListeners() {
    // Apply filters button
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    
    // Enter key in search box
    document.getElementById('search-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
    
    // Sort change
    document.getElementById('sort-by').addEventListener('change', applyFilters);
}

/**
 * Load all routes from API
 */
async function loadRoutes() {
    try {
        const data = await window.apiClient.getRoutes();
        allRoutes = data.routes || [];
        filteredRoutes = [...allRoutes];
        
        applyFilters();
    } catch (error) {
        console.error('Failed to load routes:', error);
        showError('Failed to load routes. Please try again later.');
    }
}

/**
 * Apply filters and sorting to routes
 */
function applyFilters() {
    // Get filter values
    const favoriteFilter = document.getElementById('filter-favorite').value;
    const sportTypeFilter = document.getElementById('filter-sport-type').value;
    const minDistance = parseFloat(document.getElementById('filter-min-distance').value) || 0;
    const maxDistance = parseFloat(document.getElementById('filter-max-distance').value) || Infinity;
    const searchQuery = document.getElementById('search-query').value.toLowerCase().trim();
    const sortBy = document.getElementById('sort-by').value;
    
    // Filter routes
    filteredRoutes = allRoutes.filter(route => {
        // Favorite filter
        if (favoriteFilter === 'true' && !route.is_favorite) return false;
        if (favoriteFilter === 'false' && route.is_favorite) return false;
        
        // Sport type filter
        if (sportTypeFilter && route.sport_type !== sportTypeFilter) return false;
        
        // Distance filters
        const distance = route.distance || 0;
        if (distance < minDistance || distance > maxDistance) return false;
        
        // Search query
        if (searchQuery) {
            const name = (route.name || '').toLowerCase();
            const description = (route.description || '').toLowerCase();
            if (!name.includes(searchQuery) && !description.includes(searchQuery)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Sort routes
    sortRoutes(sortBy);
    
    // Reset to first page
    currentPage = 1;
    
    // Update display
    updateResultsSummary();
    renderRoutes();
    renderPagination();
}

/**
 * Sort routes based on selected criteria
 */
function sortRoutes(sortBy) {
    switch (sortBy) {
        case 'name':
            filteredRoutes.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            break;
        case 'name-desc':
            filteredRoutes.sort((a, b) => (b.name || '').localeCompare(a.name || ''));
            break;
        case 'distance':
            filteredRoutes.sort((a, b) => (a.distance || 0) - (b.distance || 0));
            break;
        case 'distance-desc':
            filteredRoutes.sort((a, b) => (b.distance || 0) - (a.distance || 0));
            break;
        case 'elevation':
            filteredRoutes.sort((a, b) => (a.elevation_gain || 0) - (b.elevation_gain || 0));
            break;
        case 'elevation-desc':
            filteredRoutes.sort((a, b) => (b.elevation_gain || 0) - (a.elevation_gain || 0));
            break;
        case 'uses':
            filteredRoutes.sort((a, b) => (b.uses || 0) - (a.uses || 0));
            break;
        default:
            // Default to name ascending
            filteredRoutes.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    }
}

/**
 * Update results summary
 */
function updateResultsSummary() {
    const summary = document.getElementById('results-summary');
    const total = filteredRoutes.length;
    const showing = Math.min(routesPerPage, total - (currentPage - 1) * routesPerPage);
    
    if (total === 0) {
        summary.className = 'alert alert-warning';
        summary.innerHTML = '<i class="bi bi-exclamation-triangle"></i> No routes match your filters.';
    } else if (total === allRoutes.length) {
        summary.className = 'alert alert-info';
        summary.innerHTML = `<i class="bi bi-info-circle"></i> Showing ${total} route${total !== 1 ? 's' : ''}`;
    } else {
        summary.className = 'alert alert-success';
        summary.innerHTML = `<i class="bi bi-check-circle"></i> Found ${total} route${total !== 1 ? 's' : ''} matching your filters`;
    }
}

/**
 * Render routes for current page
 */
function renderRoutes() {
    const container = document.getElementById('routes-container');
    
    if (filteredRoutes.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox fs-1 text-muted"></i>
                <p class="mt-3 text-muted">No routes found. Try adjusting your filters.</p>
            </div>
        `;
        return;
    }
    
    // Calculate pagination
    const startIdx = (currentPage - 1) * routesPerPage;
    const endIdx = Math.min(startIdx + routesPerPage, filteredRoutes.length);
    const pageRoutes = filteredRoutes.slice(startIdx, endIdx);
    
    // Render route cards
    const html = `
        <div class="row">
            ${pageRoutes.map(route => renderRouteCard(route)).join('')}
        </div>
    `;
    
    container.innerHTML = html;
    
    // Add favorite toggle listeners
    pageRoutes.forEach(route => {
        const btn = document.getElementById(`favorite-${route.id}`);
        if (btn) {
            btn.addEventListener('click', () => toggleFavorite(route.id));
        }
    });
}

/**
 * Render a single route card
 */
function renderRouteCard(route) {
    const favoriteIcon = route.is_favorite ? 'bi-star-fill text-warning' : 'bi-star';
    const sportBadge = getSportBadge(route.sport_type);
    
    return `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="route-card fade-in">
                <div class="route-card-header">
                    <h5 class="route-card-title text-truncate">${escapeHtml(route.name)}</h5>
                    <button id="favorite-${route.id}" class="btn btn-link p-0" title="Toggle favorite">
                        <i class="bi ${favoriteIcon} fs-5"></i>
                    </button>
                </div>
                
                <div class="route-card-stats">
                    <div class="route-stat">
                        <span class="route-stat-label">Distance</span>
                        <span class="route-stat-value">${route.distance.toFixed(1)} mi</span>
                    </div>
                    <div class="route-stat">
                        <span class="route-stat-label">Elevation</span>
                        <span class="route-stat-value">${route.elevation_gain} ft</span>
                    </div>
                    ${route.uses ? `
                        <div class="route-stat">
                            <span class="route-stat-label">Uses</span>
                            <span class="route-stat-value">${route.uses}</span>
                        </div>
                    ` : ''}
                </div>
                
                <div class="mb-3">
                    ${sportBadge}
                    ${route.is_favorite ? '<span class="badge bg-warning text-dark ms-1"><i class="bi bi-star-fill"></i> Favorite</span>' : ''}
                </div>
                
                ${route.description ? `
                    <p class="text-muted small mb-3">${escapeHtml(route.description).substring(0, 100)}${route.description.length > 100 ? '...' : ''}</p>
                ` : ''}
                
                <div class="d-grid gap-2">
                    <a href="/route-detail.html?id=${route.id}" class="btn btn-primary btn-sm">
                        <i class="bi bi-eye"></i> View Details
                    </a>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get sport type badge HTML
 */
function getSportBadge(sportType) {
    const badges = {
        'Ride': '<span class="badge bg-primary">Ride</span>',
        'VirtualRide': '<span class="badge bg-info">Virtual</span>',
        'EBikeRide': '<span class="badge bg-success">E-Bike</span>',
        'GravelRide': '<span class="badge bg-secondary">Gravel</span>'
    };
    return badges[sportType] || '<span class="badge bg-secondary">Ride</span>';
}

/**
 * Render pagination controls
 */
function renderPagination() {
    const container = document.getElementById('pagination-container');
    const totalPages = Math.ceil(filteredRoutes.length / routesPerPage);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<nav aria-label="Route pagination"><ul class="pagination justify-content-center">';
    
    // Previous button
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i> Previous
            </a>
        </li>
    `;
    
    // Page numbers (show max 5 pages)
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
            </li>
        `;
    }
    
    // Next button
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;">
                Next <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
    
    html += '</ul></nav>';
    container.innerHTML = html;
}

/**
 * Change page
 */
function changePage(page) {
    const totalPages = Math.ceil(filteredRoutes.length / routesPerPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    renderRoutes();
    renderPagination();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Toggle favorite status for a route
 */
async function toggleFavorite(routeId) {
    try {
        await window.apiClient.toggleFavorite(routeId);
        
        // Update local state
        const route = allRoutes.find(r => r.id === routeId);
        if (route) {
            route.is_favorite = !route.is_favorite;
        }
        
        // Re-render
        applyFilters();
        
        // Show toast notification
        showToast(route.is_favorite ? 'Added to favorites' : 'Removed from favorites');
    } catch (error) {
        console.error('Failed to toggle favorite:', error);
        showToast('Failed to update favorite status', 'error');
    }
}

/**
 * Show error message
 */
function showError(message) {
    const container = document.getElementById('routes-container');
    container.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <i class="bi bi-exclamation-triangle"></i> ${message}
        </div>
    `;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make changePage available globally for pagination
window.changePage = changePage;

// Made with Bob
