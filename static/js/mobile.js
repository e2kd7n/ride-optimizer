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
        // The "More" drawer toggle (Issue #362) is handled entirely by
        // Bootstrap collapse via data-bs-toggle; don't steal its active
        // state or aria-current — it highlights only when a drawer page
        // (Explore/Settings) is the current page.
        const isDrawerToggle = item.hasAttribute('data-bs-toggle');

        // Click handler
        item.addEventListener('click', function(e) {
            if (isDrawerToggle) return;
            e.preventDefault();
            handleNavItemActivation(this, navItems);
        });

        // Keyboard navigation handler
        item.addEventListener('keydown', function(e) {
            // Enter or Space to activate
            if (e.key === 'Enter' || e.key === ' ') {
                if (isDrawerToggle) return; // native button click triggers Bootstrap collapse
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
     * Handle navigation item activation.
     * Sets visual/ARIA state, announces to screen readers, then navigates
     * via the item's `data-page` attribute (a PAGE_ROUTES key).
     *
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

        // Announce to screen readers
        const label = item.getAttribute('aria-label');
        if (label && window.announceToScreenReader) {
            announceToScreenReader(`Navigated to ${label}`);
        }

        const pageId = item.dataset.page;
        if (pageId) {
            navigateToTab(pageId);
        }
    }
    
    console.log('✓ Bottom navigation initialized');
}

/**
 * Page routes used by mobile navigation.
 * The app uses separate HTML pages (not Bootstrap tab panes), so
 * navigation is handled via page loads rather than tab switching.
 */
const PAGE_ROUTES = {
    home:     '/',
    routes:   '/routes.html',
    weather:  '/weather.html',
    reports:  '/reports.html',
    explore:  '/explore.html',
    settings: '/settings.html'
};

/**
 * Navigate to a page by its short name (e.g. 'home', 'routes').
 * @param {string} pageId - Key in PAGE_ROUTES
 */
function navigateToTab(pageId) {
    const href = PAGE_ROUTES[pageId];
    if (href) {
        window.location.href = href;
    }
}

/**
 * Pages listed in the "More" overflow drawer, in display order.
 * `id` must be a PAGE_ROUTES key.
 */
const DRAWER_ITEMS = [
    { id: 'explore', icon: 'bi-compass', label: 'Explore' },
    { id: 'settings', icon: 'bi-gear', label: 'Settings' }
];

/**
 * Populate the #bottom-nav-more drawer from DRAWER_ITEMS/PAGE_ROUTES so the
 * markup isn't hand-duplicated across every page (Issue #443).
 */
function renderBottomNavDrawer() {
    const drawer = document.getElementById('bottom-nav-more');
    if (!drawer) {
        return;
    }

    const currentIndex = getCurrentPageIndex();
    const currentPageId = currentIndex >= 0 ? PAGE_ORDER[currentIndex] : null;

    drawer.innerHTML = DRAWER_ITEMS.map(({ id, icon, label }) => {
        const isActive = id === currentPageId;
        return `<a class="bottom-nav-drawer-item${isActive ? ' active' : ''}" href="${PAGE_ROUTES[id]}"${isActive ? ' aria-current="page"' : ''}>
            <i class="bi ${icon}" aria-hidden="true"></i>
            <span>${label}</span>
        </a>`;
    }).join('');
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
 * Ordered page list for swipe navigation.
 */
const PAGE_ORDER = Object.keys(PAGE_ROUTES); // ['home', 'routes', 'weather', 'settings']

/**
 * Detect which page we are currently on based on the URL path.
 * @returns {number} index into PAGE_ORDER, or -1
 */
function getCurrentPageIndex() {
    const path = window.location.pathname;
    return PAGE_ORDER.findIndex(key => {
        const route = PAGE_ROUTES[key];
        // Match either exact path or path ending with the route
        return path === route || path.endsWith(route);
    });
}

/**
 * Navigate to next page (swipe left)
 */
function navigateToNextTab() {
    const currentIndex = getCurrentPageIndex();
    if (currentIndex < 0) return;

    if (currentIndex < PAGE_ORDER.length - 1) {
        showSwipeFeedback('left');
        navigateToTab(PAGE_ORDER[currentIndex + 1]);
    }
}

/**
 * Navigate to previous page (swipe right)
 */
function navigateToPreviousTab() {
    const currentIndex = getCurrentPageIndex();
    if (currentIndex < 0) return;

    if (currentIndex > 0) {
        showSwipeFeedback('right');
        navigateToTab(PAGE_ORDER[currentIndex - 1]);
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
        color: var(--accent, #0B6FA6);
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
    renderBottomNavDrawer();
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
