/**
 * Ride Optimizer - Main JavaScript
 * Version: 3.0.0-dev
 */

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const navbarToggle = document.getElementById('navbar-toggle');
    const navbarMenu = document.querySelector('.navbar-menu');
    
    if (navbarToggle && navbarMenu) {
        navbarToggle.addEventListener('click', function() {
            navbarMenu.classList.toggle('active');
        });
    }
    
    // Close flash messages
    const alertCloseButtons = document.querySelectorAll('.alert-close');
    alertCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.remove();
        });
    });
    
    // Auto-close flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
    
    // Handle action buttons with POST method
    const actionButtons = document.querySelectorAll('.action-btn[data-method="POST"]');
    actionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            
            // Show loading state
            const originalContent = this.innerHTML;
            this.innerHTML = '<span class="action-icon">⏳</span><span class="action-label">Loading...</span>';
            this.style.pointerEvents = 'none';
            
            // Make POST request
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                // Show success message
                showFlashMessage('success', data.message || 'Action completed successfully');
                
                // Restore button
                this.innerHTML = originalContent;
                this.style.pointerEvents = 'auto';
                
                // Reload page after short delay
                setTimeout(() => location.reload(), 1000);
            })
            .catch(error => {
                console.error('Error:', error);
                showFlashMessage('danger', 'An error occurred. Please try again.');
                
                // Restore button
                this.innerHTML = originalContent;
                this.style.pointerEvents = 'auto';
            });
        });
    });
});

/**
 * Show a flash message dynamically
 * @param {string} category - Message category (success, warning, danger, info)
 * @param {string} message - Message text
 */
function showFlashMessage(category, message) {
    const flashContainer = document.querySelector('.flash-messages .container');
    if (!flashContainer) {
        // Create flash messages container if it doesn't exist
        const navbar = document.querySelector('.navbar');
        const newContainer = document.createElement('div');
        newContainer.className = 'flash-messages';
        newContainer.innerHTML = '<div class="container"></div>';
        navbar.parentNode.insertBefore(newContainer, navbar.nextSibling);
    }
    
    const container = document.querySelector('.flash-messages .container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${category}`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="alert-close" aria-label="Close">×</button>
    `;
    
    container.appendChild(alert);
    
    // Add close handler
    const closeButton = alert.querySelector('.alert-close');
    closeButton.addEventListener('click', function() {
        alert.remove();
    });
    
    // Auto-close after 5 seconds
    setTimeout(() => {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

/**
 * Format date for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format distance for display
 * @param {number} meters - Distance in meters
 * @returns {string} Formatted distance
 */
function formatDistance(meters) {
    const miles = meters * 0.000621371;
    return `${miles.toFixed(1)} mi`;
}

/**
 * Format elevation for display
 * @param {number} meters - Elevation in meters
 * @returns {string} Formatted elevation
 */
function formatElevation(meters) {
    const feet = meters * 3.28084;
    return `${Math.round(feet)} ft`;
}

/**
 * Debounce function for search inputs
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
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

// Made with Bob
