/**
 * mobile.js - Mobile-specific utilities for Ride Optimizer
 * Epic #237 - UI/UX Redesign
 * 
 * Features:
 * - Bottom navigation bar (Issue #242)
 * - Swipe gesture support (Issue #251)
 * - Touch feedback enhancements
 * - Mobile-optimized interactions
 * - Responsive behavior adjustments
 */

// Mobile detection
const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
const isTouchDevice = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);

/**
 * Initialize bottom navigation for mobile
 */
function initializeBottomNav() {
    const bottomNav = document.getElementById('bottom-nav');
    if (!bottomNav) {
        console.warn('Bottom navigation element not found');
        return;
    }
    
    // CSS handles visibility via media queries - we just set up event listeners
    // Handle nav item clicks and keyboard navigation
    const navItems = bottomNav.querySelectorAll('.bottom-nav-item');
    navItems.forEach((item, index) => {
        // Click handler
        item.addEventListener('click', function(e) {
            e.preventDefault();
            handleNavItemActivation(this, navItems);
        });
        
        // Keyboard navigation handler
        item.addEventListener('keydown', function(e) {
            // Enter or Space to activate
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleNavItemActivation(this, navItems);
            }
            
            // Arrow key navigation
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                e.preventDefault();
                const currentIndex = Array.from(navItems).indexOf(this);
                let nextIndex;
                
                if (e.key === 'ArrowLeft') {
                    nextIndex = currentIndex > 0 ? currentIndex - 1 : navItems.length - 1;
                } else {
                    nextIndex = currentIndex < navItems.length - 1 ? currentIndex + 1 : 0;
                }
                
                navItems[nextIndex].focus();
            }
            
            // Home/End keys
            if (e.key === 'Home') {
                e.preventDefault();
                navItems[0].focus();
            }
            if (e.key === 'End') {
                e.preventDefault();
                navItems[navItems.length - 1].focus();
            }
        });
    });
    
    /**
     * Handle navigation item activation
     * @param {HTMLElement} item - The navigation item to activate
     * @param {NodeList} allItems - All navigation items
     */
    function handleNavItemActivation(item, allItems) {
        // Remove active class and aria-current from all items
        allItems.forEach(i => {
            i.classList.remove('active');
            i.removeAttribute('aria-current');
        });
        
        // Add active class to clicked item
        item.classList.add('active');
        item.setAttribute('aria-current', 'page');
        
        // Navigate to target
        const target = item.getAttribute('data-target');
        if (target) {
            navigateToTab(target);
        }
        
        // Announce to screen readers
        const label = item.getAttribute('aria-label');
        if (label && window.announceToScreenReader) {
            announceToScreenReader(`Navigated to ${label}`);
        }
    }
    
    console.log('✓ Bottom navigation initialized');
}

/**
 * Navigate to a specific tab
 * @param {string} tabId - ID of tab to navigate to
 */
function navigateToTab(tabId) {
    // Manual tab switching (works on both mobile and desktop)
    // Hide all tab panes
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => {
        pane.classList.remove('show', 'active');
        pane.setAttribute('aria-hidden', 'true');
    });
    
    // Deactivate all desktop tabs (if they exist)
    const desktopTabs = document.querySelectorAll('.nav-tabs .nav-link');
    desktopTabs.forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });
    
    // Show target pane
    const targetPane = document.getElementById(tabId);
    if (targetPane) {
        targetPane.classList.add('show', 'active');
        targetPane.setAttribute('aria-hidden', 'false');
        
        // Activate corresponding desktop tab (if it exists)
        const correspondingTab = document.getElementById(`${tabId}-tab`);
        if (correspondingTab) {
            correspondingTab.classList.add('active');
            correspondingTab.setAttribute('aria-selected', 'true');
        }
    }
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Update page title
    const pageTitle = tabId.charAt(0).toUpperCase() + tabId.slice(1);
    document.title = `${pageTitle} - Ride Optimizer`;
}

/**
 * Initialize swipe gesture support
 */
function initializeSwipeGestures() {
    if (!isTouchDevice) {
        return;
    }
    
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    
    const minSwipeDistance = 50; // Minimum distance for swipe
    const maxVerticalDistance = 100; // Maximum vertical movement for horizontal swipe
    
    // Swipeable container (main content area)
    const swipeContainer = document.querySelector('.container-fluid') || document.body;
    
    swipeContainer.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });
    
    swipeContainer.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Check if it's a horizontal swipe (not vertical scroll)
        if (Math.abs(deltaY) > maxVerticalDistance) {
            return;
        }
        
        // Swipe left (next tab)
        if (deltaX < -minSwipeDistance) {
            navigateToNextTab();
        }
        
        // Swipe right (previous tab)
        if (deltaX > minSwipeDistance) {
            navigateToPreviousTab();
        }
    }
    
    console.log('✓ Swipe gestures initialized');
}

/**
 * Navigate to next tab
 */
function navigateToNextTab() {
    const tabs = ['home', 'routes', 'settings'];
    const activeTab = document.querySelector('.bottom-nav-item.active');
    
    if (!activeTab) return;
    
    const currentTarget = activeTab.getAttribute('data-target');
    const currentIndex = tabs.indexOf(currentTarget);
    
    if (currentIndex < tabs.length - 1) {
        const nextTab = tabs[currentIndex + 1];
        const nextNavItem = document.querySelector(`.bottom-nav-item[data-target="${nextTab}"]`);
        
        if (nextNavItem) {
            nextNavItem.click();
            
            // Visual feedback
            showSwipeFeedback('left');
        }
    }
}

/**
 * Navigate to previous tab
 */
function navigateToPreviousTab() {
    const tabs = ['home', 'routes', 'settings'];
    const activeTab = document.querySelector('.bottom-nav-item.active');
    
    if (!activeTab) return;
    
    const currentTarget = activeTab.getAttribute('data-target');
    const currentIndex = tabs.indexOf(currentTarget);
    
    if (currentIndex > 0) {
        const prevTab = tabs[currentIndex - 1];
        const prevNavItem = document.querySelector(`.bottom-nav-item[data-target="${prevTab}"]`);
        
        if (prevNavItem) {
            prevNavItem.click();
            
            // Visual feedback
            showSwipeFeedback('right');
        }
    }
}

/**
 * Show visual feedback for swipe gesture
 * @param {string} direction - 'left' or 'right'
 */
function showSwipeFeedback(direction) {
    const feedback = document.createElement('div');
    feedback.className = 'swipe-feedback';
    feedback.textContent = direction === 'left' ? '→' : '←';
    feedback.style.cssText = `
        position: fixed;
        top: 50%;
        ${direction === 'left' ? 'right: 20px' : 'left: 20px'};
        transform: translateY(-50%);
        font-size: 48px;
        color: var(--epic-primary, #667eea);
        opacity: 0;
        animation: swipeFeedbackAnim 0.3s ease-out;
        pointer-events: none;
        z-index: 9999;
    `;
    
    document.body.appendChild(feedback);
    
    setTimeout(() => {
        feedback.remove();
    }, 300);
}

/**
 * Initialize touch feedback for interactive elements
 */
function initializeTouchFeedback() {
    if (!isTouchDevice) {
        return;
    }
    
    // Add tap feedback to buttons and interactive elements
    const interactiveElements = document.querySelectorAll(
        '.btn, .route-card-compact, .nav-link, .bottom-nav-item, .route-row'
    );
    
    interactiveElements.forEach(element => {
        element.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
            this.style.transition = 'transform 0.1s ease';
        }, { passive: true });
        
        element.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        }, { passive: true });
        
        element.addEventListener('touchcancel', function() {
            this.style.transform = 'scale(1)';
        }, { passive: true });
    });
    
    console.log('✓ Touch feedback initialized');
}

/**
 * Optimize tooltips for touch devices
 */
function optimizeTooltipsForTouch() {
    if (!isTouchDevice) {
        return;
    }
    
    const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    
    tooltipElements.forEach(element => {
        // Change trigger to click for touch devices
        const tooltip = bootstrap.Tooltip.getInstance(element);
        if (tooltip) {
            tooltip.dispose();
        }
        
        new bootstrap.Tooltip(element, {
            trigger: 'click',
            delay: { show: 0, hide: 2000 }
        });
        
        // Auto-hide after 3 seconds
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const tooltipInstance = bootstrap.Tooltip.getInstance(this);
            if (tooltipInstance) {
                setTimeout(() => {
                    tooltipInstance.hide();
                }, 3000);
            }
        });
    });
    
    console.log('✓ Tooltips optimized for touch');
}

/**
 * Handle responsive behavior on window resize
 */
function handleResponsiveResize() {
    let resizeTimeout;
    
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        
        resizeTimeout = setTimeout(function() {
            const width = window.innerWidth;
            
            // Show/hide bottom nav based on screen size
            const bottomNav = document.getElementById('bottom-nav');
            if (bottomNav) {
                if (width < 768) {
                    bottomNav.style.display = 'flex';
                } else {
                    bottomNav.style.display = 'none';
                }
            }
            
            // Adjust touch target sizes
            if (width < 768) {
                document.body.classList.add('mobile-view');
            } else {
                document.body.classList.remove('mobile-view');
            }
            
            // Invalidate map sizes if they exist
            if (window.recommendationsMap) {
                window.recommendationsMap.invalidateSize();
            }
            if (window.nextCommuteMap) {
                window.nextCommuteMap.invalidateSize();
            }
        }, 250);
    });
}

/**
 * Prevent iOS zoom on input focus
 */
function preventIOSZoom() {
    if (!/(iPhone|iPad|iPod)/i.test(navigator.userAgent)) {
        return;
    }
    
    // Ensure all inputs have font-size >= 16px to prevent zoom
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        const fontSize = window.getComputedStyle(input).fontSize;
        const fontSizeValue = parseFloat(fontSize);
        
        if (fontSizeValue < 16) {
            input.style.fontSize = '16px';
        }
    });
    
    console.log('✓ iOS zoom prevention applied');
}

/**
 * Add loading indicator for async actions on mobile
 */
function enhanceAsyncActions() {
    const asyncButtons = document.querySelectorAll('[data-async-action]');
    
    asyncButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.classList.contains('loading')) {
                this.classList.add('loading');
                this.setAttribute('disabled', 'disabled');
                
                // Add spinner
                const originalContent = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>' + originalContent;
                
                // Store original content for restoration
                this.dataset.originalContent = originalContent;
                
                // Auto-remove after 5 seconds (fallback)
                setTimeout(() => {
                    this.classList.remove('loading');
                    this.removeAttribute('disabled');
                    this.innerHTML = this.dataset.originalContent;
                }, 5000);
            }
        });
    });
}

/**
 * Handle pull-to-refresh gesture (optional enhancement)
 */
function initializePullToRefresh() {
    if (!isTouchDevice) {
        return;
    }
    
    let touchStartY = 0;
    let isPulling = false;
    
    document.addEventListener('touchstart', function(e) {
        if (window.scrollY === 0) {
            touchStartY = e.touches[0].clientY;
        }
    }, { passive: true });
    
    document.addEventListener('touchmove', function(e) {
        if (window.scrollY === 0) {
            const touchY = e.touches[0].clientY;
            const pullDistance = touchY - touchStartY;
            
            if (pullDistance > 100 && !isPulling) {
                isPulling = true;
                // Show refresh indicator
                if (window.showToast) {
                    window.showToast('Release to refresh', 'info', { duration: 1000 });
                }
            }
        }
    }, { passive: true });
    
    document.addEventListener('touchend', function() {
        if (isPulling) {
            isPulling = false;
            // Trigger refresh
            if (window.location.reload) {
                window.location.reload();
            }
        }
        touchStartY = 0;
    }, { passive: true });
}

/**
 * Initialize all mobile features
 */
function initializeMobileFeatures() {
    // Check if we're on a mobile device
    if (window.innerWidth < 768 || isMobileDevice) {
        document.body.classList.add('mobile-device');
    }
    
    if (isTouchDevice) {
        document.body.classList.add('touch-device');
    }
    
    // Initialize features
    initializeBottomNav();
    initializeSwipeGestures();
    initializeTouchFeedback();
    optimizeTooltipsForTouch();
    handleResponsiveResize();
    preventIOSZoom();
    enhanceAsyncActions();
    
    // Optional: Pull-to-refresh (can be disabled if not desired)
    // initializePullToRefresh();
    
    console.log('✓ Mobile features initialized');
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMobileFeatures);
} else {
    initializeMobileFeatures();
}

// Export for use in other modules
window.mobileUtils = {
    isMobileDevice,
    isTouchDevice,
    navigateToTab,
    navigateToNextTab,
    navigateToPreviousTab,
    showSwipeFeedback
};

console.log('✓ mobile.js loaded - Bottom nav, swipe gestures, and touch enhancements ready');

// Made with Bob
