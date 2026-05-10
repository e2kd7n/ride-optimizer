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
 */

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
    
    // Build toast content
    let toastContent = `<strong>${icons[type] || icons.info}</strong> ${message}`;
    
    // Add undo button if undo action provided
    if (undoAction) {
        const undoId = 'undo-' + Date.now();
        toastContent += `
            <button type="button" class="btn btn-sm btn-outline-light ms-2"
                    id="${undoId}"
                    aria-label="Undo last action"
                    style="border-color: currentColor;">
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
            <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()" aria-label="Dismiss error message"></button>
        `;
        
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
 * Show success message to user
 * @param {string} message - Success message to display
 * @param {string} containerId - ID of container to show message in (optional)
 */
window.showSuccess = function(message, containerId = null) {
    if (containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message show';
        successDiv.setAttribute('role', 'status');
        successDiv.setAttribute('aria-live', 'polite');
        successDiv.innerHTML = `
            <strong>Success:</strong> ${message}
            <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()" aria-label="Dismiss success message"></button>
        `;
        
        container.insertBefore(successDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            successDiv.classList.remove('show');
            setTimeout(() => successDiv.remove(), 300);
        }, 5000);
    } else {
        showToast(message, 'success');
    }
};

/**
 * Show loading overlay on an element
 * @param {string} elementId - ID of element to show loading on
 * @param {string} message - Loading message (optional)
 */
window.showLoading = function(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Make element position relative if not already
    const position = window.getComputedStyle(element).position;
    if (position === 'static') {
        element.style.position = 'relative';
    }
    
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = `${elementId}-loading`;
    overlay.setAttribute('role', 'status');
    overlay.setAttribute('aria-live', 'polite');
    overlay.innerHTML = `
        <div class="loading-message">
            <div class="loading-spinner mb-2"></div>
            <div>${message}</div>
        </div>
    `;
    
    element.appendChild(overlay);
};

/**
 * Hide loading overlay
 * @param {string} elementId - ID of element to hide loading from
 */
window.hideLoading = function(elementId) {
    const overlay = document.getElementById(`${elementId}-loading`);
    if (overlay) {
        overlay.remove();
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

/**
 * Validate form input
 * @param {HTMLElement} input - Input element to validate
 * @param {Object} rules - Validation rules
 * @returns {boolean} - True if valid
 */
window.validateInput = function(input, rules = {}) {
    if (!input) return false;
    
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required validation
    if (rules.required && !value) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    // Min length validation
    if (rules.minLength && value.length < rules.minLength) {
        isValid = false;
        errorMessage = `Minimum ${rules.minLength} characters required`;
    }
    
    // Max length validation
    if (rules.maxLength && value.length > rules.maxLength) {
        isValid = false;
        errorMessage = `Maximum ${rules.maxLength} characters allowed`;
    }
    
    // Number validation
    if (rules.type === 'number' && value) {
        const num = parseFloat(value);
        if (isNaN(num)) {
            isValid = false;
            errorMessage = 'Please enter a valid number';
        } else {
            if (rules.min !== undefined && num < rules.min) {
                isValid = false;
                errorMessage = `Minimum value is ${rules.min}`;
            }
            if (rules.max !== undefined && num > rules.max) {
                isValid = false;
                errorMessage = `Maximum value is ${rules.max}`;
            }
        }
    }
    
    // Update input state
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'none';
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        
        // Show or create error feedback
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentNode.insertBefore(feedback, input.nextSibling);
        }
        feedback.textContent = errorMessage;
        feedback.style.display = 'block';
    }
    
    return isValid;
};

// Auto-save functionality (Issue #244)
let hasUnsavedChanges = false;
let autoSaveTimer = null;

/**
 * Mark that there are unsaved changes
 */
window.markUnsavedChanges = function() {
    hasUnsavedChanges = true;
    
    // Show indicator
    const indicator = document.getElementById('unsaved-indicator');
    if (indicator) {
        indicator.style.display = 'inline';
    }
};

/**
 * Clear unsaved changes flag
 */
window.clearUnsavedChanges = function() {
    hasUnsavedChanges = false;
    
    // Hide indicator
    const indicator = document.getElementById('unsaved-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
};

/**
 * Auto-save with debouncing (500ms)
 * @param {Function} saveFunction - Function to call for saving
 */
window.setupAutoSave = function(saveFunction) {
    // Clear existing timer
    if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
    }
    
    // Set new timer
    autoSaveTimer = setTimeout(() => {
        if (hasUnsavedChanges) {
            saveFunction();
            clearUnsavedChanges();
            showToast('Changes saved automatically', 'success', { duration: 2000 });
        }
    }, 500);
};

/**
 * Warn user about unsaved changes before leaving
 */
window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Undo/Redo functionality (Issue #249)
let undoStack = [];
let redoStack = [];

/**
 * Add action to undo stack
 * @param {Function} undoAction - Function to call to undo
 * @param {Function} redoAction - Function to call to redo
 */
window.addToUndoStack = function(undoAction, redoAction) {
    undoStack.push({ undo: undoAction, redo: redoAction });
    redoStack = []; // Clear redo stack when new action is added
    
    // Limit stack size to 50 actions
    if (undoStack.length > 50) {
        undoStack.shift();
    }
};

/**
 * Perform undo action
 */
window.performUndo = function() {
    if (undoStack.length === 0) {
        showToast('Nothing to undo', 'info', { duration: 2000 });
        return;
    }
    
    const action = undoStack.pop();
    action.undo();
    redoStack.push(action);
    showToast('Action undone', 'info', { duration: 2000 });
};

/**
 * Perform redo action
 */
window.performRedo = function() {
    if (redoStack.length === 0) {
        showToast('Nothing to redo', 'info', { duration: 2000 });
        return;
    }
    
    const action = redoStack.pop();
    action.redo();
    undoStack.push(action);
    showToast('Action redone', 'info', { duration: 2000 });
};

// Keyboard shortcuts for undo/redo
document.addEventListener('keydown', function(e) {
    // Ctrl+Z or Cmd+Z for undo
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        performUndo();
    }
    
    // Ctrl+Shift+Z or Cmd+Shift+Z for redo
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        performRedo();
    }
    
    // Ctrl+Y or Cmd+Y for redo (alternative)
    if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        performRedo();
    }
});

// Example undo-able actions
window.hideRouteWithUndo = function(routeId) {
    // Get current hidden routes
    const hiddenRoutes = JSON.parse(localStorage.getItem('hiddenRoutes') || '[]');
    
    // Add to hidden
    hiddenRoutes.push(routeId);
    localStorage.setItem('hiddenRoutes', JSON.stringify(hiddenRoutes));
    
    // Show toast with undo
    showToast('Route hidden', 'warning', {
        undoAction: function() {
            // Undo: remove from hidden
            const routes = JSON.parse(localStorage.getItem('hiddenRoutes') || '[]');
            const index = routes.indexOf(routeId);
            if (index > -1) {
                routes.splice(index, 1);
                localStorage.setItem('hiddenRoutes', JSON.stringify(routes));
                showToast('Route restored', 'success', { duration: 2000 });
            }
        },
        duration: 5000
    });
};

window.unfavoriteRouteWithUndo = function(routeId) {
    // Get current favorites
    const favorites = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
    const index = favorites.indexOf(routeId);
    
    if (index > -1) {
        // Remove from favorites
        favorites.splice(index, 1);
        localStorage.setItem('favoriteRoutes', JSON.stringify(favorites));
        
        // Show toast with undo
        showToast('Route unfavorited', 'warning', {
            undoAction: function() {
                // Undo: add back to favorites
                const faves = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
                faves.push(routeId);
                localStorage.setItem('favoriteRoutes', JSON.stringify(faves));
                showToast('Route re-favorited', 'success', { duration: 2000 });
            },
            duration: 5000
        });
    }
};

console.log('✓ common.js loaded - Toast, auto-save, and undo utilities ready');

// Made with Bob
