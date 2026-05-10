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
        ariaLiveRegion.className = 'sr-only';
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
 * Manage focus trap for modals and dialogs
 * @param {HTMLElement} container - Container element to trap focus within
 * @returns {Function} Function to release the focus trap
 */
window.trapFocus = function(container) {
    if (!container) return () => {};
    
    const focusableElements = container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), ' +
        'input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];
    
    // Store the element that had focus before trap
    const previouslyFocused = document.activeElement;
    
    // Focus first element
    if (firstFocusable) {
        firstFocusable.focus();
    }
    
    // Handle Tab key
    function handleTab(e) {
        if (e.key !== 'Tab') return;
        
        if (e.shiftKey) {
            // Shift + Tab
            if (document.activeElement === firstFocusable) {
                e.preventDefault();
                lastFocusable.focus();
            }
        } else {
            // Tab
            if (document.activeElement === lastFocusable) {
                e.preventDefault();
                firstFocusable.focus();
            }
        }
    }
    
    container.addEventListener('keydown', handleTab);
    
    // Return function to release trap
    return function releaseTrap() {
        container.removeEventListener('keydown', handleTab);
        if (previouslyFocused) {
            previouslyFocused.focus();
        }
    };
};

/**
 * Enhance focus indicators for keyboard navigation
 */
function enhanceFocusIndicators() {
    // Add class to body when user is using keyboard
    let isUsingKeyboard = false;
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            isUsingKeyboard = true;
            document.body.classList.add('keyboard-nav');
        }
    });
    
    document.addEventListener('mousedown', function() {
        isUsingKeyboard = false;
        document.body.classList.remove('keyboard-nav');
    });
    
    // Ensure all interactive elements are keyboard accessible
    const interactiveElements = document.querySelectorAll(
        '.route-card-compact, .next-commute-card, .activity-item'
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
 * Manage focus when navigating between tabs
 * @param {string} tabId - ID of the tab to focus
 */
window.focusTab = function(tabId) {
    const tab = document.getElementById(tabId);
    if (tab) {
        tab.focus();
        announceToScreenReader(`Switched to ${tab.textContent.trim()} tab`);
    }
};

/**
 * Announce route count changes to screen readers
 * @param {number} count - Number of routes
 * @param {string} context - Context (e.g., "filtered", "total")
 */
window.announceRouteCount = function(count, context = 'total') {
    const message = `${count} ${count === 1 ? 'route' : 'routes'} ${context}`;
    announceToScreenReader(message);
};

/**
 * Announce loading state changes
 * @param {boolean} isLoading - Whether content is loading
 * @param {string} content - What is being loaded
 */
window.announceLoadingState = function(isLoading, content = 'content') {
    if (isLoading) {
        announceToScreenReader(`Loading ${content}`, 'polite');
    } else {
        announceToScreenReader(`${content} loaded`, 'polite');
    }
};

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
 * Validate color contrast for WCAG AA compliance
 * @param {string} foreground - Foreground color (hex)
 * @param {string} background - Background color (hex)
 * @returns {Object} Contrast ratio and pass/fail status
 */
window.checkColorContrast = function(foreground, background) {
    // Convert hex to RGB
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
    
    // Calculate relative luminance
    function getLuminance(rgb) {
        const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(val => {
            val = val / 255;
            return val <= 0.03928 ? val / 12.92 : Math.pow((val + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    
    const fg = hexToRgb(foreground);
    const bg = hexToRgb(background);
    
    if (!fg || !bg) {
        return { ratio: 0, passAA: false, passAAA: false };
    }
    
    const l1 = getLuminance(fg);
    const l2 = getLuminance(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    
    return {
        ratio: ratio.toFixed(2),
        passAA: ratio >= 4.5,      // WCAG AA for normal text
        passAAA: ratio >= 7.0,     // WCAG AAA for normal text
        passAALarge: ratio >= 3.0  // WCAG AA for large text (18pt+)
    };
};

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

/**
 * Reduced motion detection and handling
 */
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function handleReducedMotion(e) {
    if (e.matches) {
        document.body.classList.add('reduced-motion');
        console.log('✓ Reduced motion mode enabled');
    } else {
        document.body.classList.remove('reduced-motion');
    }
}

// Check on load
handleReducedMotion(prefersReducedMotion);

// Listen for changes
prefersReducedMotion.addEventListener('change', handleReducedMotion);

console.log('✓ accessibility.js loaded - ARIA, focus management, and keyboard navigation ready');

// Made with Bob
