/**
 * accessibility.js - Accessibility utilities for Ride Optimizer
 * Epic #237 - UI/UX Redesign
 * 
 * Features:
 * - ARIA live region management (Issue #243)
 * - Focus management and skip links (Issue #241)
 * - Keyboard navigation enhancements
 * - Screen reader announcements
 * - WCAG 2.1 AA compliance utilities
 */

// ARIA live region for screen reader announcements
let ariaLiveRegion = null;

/**
 * Create ARIA live region if it doesn't exist
 * @returns {HTMLElement} ARIA live region element
 */
function createLiveRegion() {
    if (!ariaLiveRegion) {
        ariaLiveRegion = document.createElement('div');
        ariaLiveRegion.id = 'aria-live-region';
        ariaLiveRegion.className = 'visually-hidden';
        ariaLiveRegion.setAttribute('aria-live', 'polite');
        ariaLiveRegion.setAttribute('aria-atomic', 'true');
        document.body.appendChild(ariaLiveRegion);
    }
    return ariaLiveRegion;
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 * @param {string} priority - 'polite' or 'assertive'
 */
window.announceToScreenReader = function(message, priority = 'polite') {
    const liveRegion = createLiveRegion();
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.textContent = message;
    
    // Clear after announcement
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
};

/**
 * Initialize skip links functionality
 */
function initializeSkipLinks() {
    const skipLinks = document.querySelectorAll('.skip-link');
    
    skipLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const target = document.getElementById(targetId);
            
            if (target) {
                // Make target focusable if it isn't already
                if (!target.hasAttribute('tabindex')) {
                    target.setAttribute('tabindex', '-1');
                }
                
                // Focus the target
                target.focus();
                
                // Announce to screen readers
                announceToScreenReader(`Skipped to ${target.getAttribute('aria-label') || targetId}`);
                
                // Scroll into view
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

/**
 * Make card-style interactive elements keyboard accessible
 */
function enhanceFocusIndicators() {
    // Ensure all interactive elements are keyboard accessible
    const interactiveElements = document.querySelectorAll(
        '.route-card-compact, .route-library-card, .next-commute-card, .activity-item'
    );

    interactiveElements.forEach(element => {
        if (!element.hasAttribute('tabindex')) {
            element.setAttribute('tabindex', '0');
        }

        if (!element.hasAttribute('role')) {
            element.setAttribute('role', 'button');
        }

        // Add keyboard event handlers if click handler exists
        if (element.onclick) {
            element.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        }
    });
}

/**
 * Add ARIA labels to elements missing them
 */
function addMissingAriaLabels() {
    // Buttons without aria-label
    const buttons = document.querySelectorAll('button:not([aria-label])');
    buttons.forEach(button => {
        const text = button.textContent.trim();
        const icon = button.querySelector('[aria-hidden="true"]');
        
        if (text && !icon) {
            button.setAttribute('aria-label', text);
        } else if (icon && !text) {
            // Button with only icon needs aria-label
            console.warn('Button with only icon missing aria-label:', button);
        }
    });
    
    // Links without accessible text
    const links = document.querySelectorAll('a:not([aria-label])');
    links.forEach(link => {
        const text = link.textContent.trim();
        const icon = link.querySelector('[aria-hidden="true"]');
        
        if (!text && icon) {
            console.warn('Link with only icon missing aria-label:', link);
        }
    });
    
    // Form inputs without labels
    const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
    inputs.forEach(input => {
        const label = document.querySelector(`label[for="${input.id}"]`);
        if (!label && input.type !== 'hidden') {
            console.warn('Input missing label:', input);
        }
    });
}

/**
 * Make tables more accessible
 */
function enhanceTableAccessibility() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Add role if missing
        if (!table.hasAttribute('role')) {
            table.setAttribute('role', 'table');
        }
        
        // Add caption if missing
        if (!table.querySelector('caption') && !table.hasAttribute('aria-label')) {
            console.warn('Table missing caption or aria-label:', table);
        }
        
        // Ensure headers have scope
        const headers = table.querySelectorAll('th');
        headers.forEach(header => {
            if (!header.hasAttribute('scope')) {
                // Determine scope based on position
                const row = header.parentElement;
                const thead = row.closest('thead');
                header.setAttribute('scope', thead ? 'col' : 'row');
            }
        });
    });
}

/**
 * Initialize all accessibility features
 */
function initializeAccessibility() {
    // Create ARIA live region
    createLiveRegion();
    
    // Initialize skip links
    initializeSkipLinks();
    
    // Enhance focus indicators
    enhanceFocusIndicators();
    
    // Add missing ARIA labels
    addMissingAriaLabels();
    
    // Enhance table accessibility
    enhanceTableAccessibility();
    
    // Handle Escape key globally for closing modals/dialogs
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            // Close any open modals
            const modals = document.querySelectorAll('.modal.show, .modal-backdrop');
            modals.forEach(modal => {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
            });
            
            // Close any open dropdowns
            const dropdowns = document.querySelectorAll('.dropdown-menu.show');
            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    });
    
    // Announce page load completion
    window.addEventListener('load', function() {
        setTimeout(() => {
            announceToScreenReader('Page loaded successfully');
        }, 1000);
    });
    
    console.log('✓ Accessibility features initialized');
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAccessibility);
} else {
    initializeAccessibility();
}

console.log('✓ accessibility.js loaded - ARIA, focus management, and keyboard navigation ready');
