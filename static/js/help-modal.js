/**
 * help-modal.js - Tutorial GIF help modal (Issue #254)
 *
 * Injects a Bootstrap help modal into the page. Tutorials lazy-load on
 * IntersectionObserver and animate (play) on hover by swapping between a
 * static preview image and the full animated GIF.
 *
 * GIF assets live in /img/tutorials/. Place files there when available.
 * Each tutorial entry specifies a `gif` (animated) and `preview` (static
 * first-frame PNG or JPEG) so users without hover get a clean thumbnail.
 */

(function () {
    'use strict';

    const TUTORIALS = [
        {
            id: 'route-comparison',
            title: 'Compare Routes',
            description: 'Select two or more routes to compare distance, elevation, and ride time side by side.',
            gif: '/img/tutorials/route-comparison.gif',
            preview: '/img/tutorials/route-comparison-preview.png',
            alt: 'Animated tutorial showing how to compare two routes in Ride Optimizer',
        },
        {
            id: 'favorites',
            title: 'Save Favorites',
            description: 'Star any route to pin it to your Favorites list for quick access.',
            gif: '/img/tutorials/favorites.gif',
            preview: '/img/tutorials/favorites-preview.png',
            alt: 'Animated tutorial showing how to save a route as a favorite',
        },
        {
            id: 'filters',
            title: 'Filter Routes',
            description: 'Use the filter panel to narrow routes by distance, elevation, or direction.',
            gif: '/img/tutorials/filters.gif',
            preview: '/img/tutorials/filters-preview.png',
            alt: 'Animated tutorial showing how to filter routes by distance and elevation',
        },
        {
            id: 'multi-select',
            title: 'Multi-Select',
            description: 'Hold Shift and click to select multiple routes, then bulk-export or compare them.',
            gif: '/img/tutorials/multi-select.gif',
            preview: '/img/tutorials/multi-select-preview.png',
            alt: 'Animated tutorial showing how to select multiple routes at once',
        },
    ];

    // ------------------------------------------------------------------
    // Build modal HTML
    // ------------------------------------------------------------------

    /**
     * Build the modal markup.
     * @param {boolean} textOnly - when true (no tutorial assets exist at all),
     *   render titles + text descriptions with no image containers at all.
     */
    function buildModalHTML(textOnly) {
        const cards = TUTORIALS.map((t) => `
            <div class="col-md-6">
                <div class="card h-100 tutorial-card" data-tutorial-id="${t.id}">
                    ${textOnly ? '' : `<div class="tutorial-img-wrapper position-relative overflow-hidden tutorial-img-wrapper-fixed">
                        <img
                            class="tutorial-img w-100 h-100 tutorial-img-cover"
                            src="${t.preview}"
                            data-gif="${t.gif}"
                            data-preview="${t.preview}"
                            alt="${t.alt}"
                            loading="lazy"
                            decoding="async"
                        />
                        <div class="tutorial-img-fallback position-absolute top-0 start-0 w-100 h-100 align-items-center justify-content-center flex-column text-muted hidden-until-shown" aria-hidden="true">
                            <i class="bi bi-image tutorial-img-fallback-icon"></i>
                            <span class="small mt-1">Preview coming soon</span>
                        </div>
                        <span class="tutorial-hover-badge position-absolute bottom-0 end-0 m-2 badge bg-secondary"
                              aria-hidden="true">Hover to play</span>
                    </div>`}
                    <div class="card-body pb-2">
                        <h6 class="card-title mb-1">${t.title}</h6>
                        <p class="card-text small text-muted mb-0">${t.description}</p>
                    </div>
                </div>
            </div>
        `).join('');

        const intro = textOnly
            ? 'Quick guides to the main features.'
            : 'Hover over a tutorial to see it in action.';

        return `
<div class="modal fade" id="helpModal" tabindex="-1"
     aria-labelledby="helpModalLabel" aria-modal="true" role="dialog">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="helpModalLabel">
                    <i class="bi bi-question-circle me-2" aria-hidden="true"></i>How To Use Ride Optimizer
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"
                        aria-label="Close help modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted mb-3">${intro}</p>
                <div class="row g-3">
                    ${cards}
                </div>
            </div>
            <div class="modal-footer">
                <a href="https://github.com/e2kd7n/ride-optimizer/wiki"
                   target="_blank" rel="noopener noreferrer"
                   class="btn btn-outline-secondary btn-sm">
                    <i class="bi bi-book me-1" aria-hidden="true"></i>Full User Guide
                </a>
                <button type="button" class="btn btn-secondary btn-sm"
                        data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>`;
    }

    // ------------------------------------------------------------------
    // Lazy loading via IntersectionObserver
    // ------------------------------------------------------------------

    function observeImages() {
        if (!('IntersectionObserver' in window)) {
            // Fallback: set src directly
            document.querySelectorAll('.tutorial-img[data-preview]').forEach((img) => {
                if (!img.src || img.src.endsWith('undefined')) {
                    img.src = img.dataset.preview;
                }
            });
            return;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.preview) {
                            img.src = img.dataset.preview;
                        }
                        observer.unobserve(img);
                    }
                });
            },
            { rootMargin: '200px' }
        );

        document.querySelectorAll('.tutorial-img').forEach((img) => observer.observe(img));
    }

    // ------------------------------------------------------------------
    // Fallback when a preview/GIF asset 404s (moved off inline onerror=""
    // so CSP script-src can drop 'unsafe-inline' — #475)
    // ------------------------------------------------------------------

    function attachImageErrorFallback() {
        document.querySelectorAll('.tutorial-img').forEach((img) => {
            img.addEventListener('error', () => {
                img.style.display = 'none';
                if (img.nextElementSibling) {
                    img.nextElementSibling.style.display = 'flex';
                }
                const badge = img.parentElement.querySelector('.tutorial-hover-badge');
                if (badge) badge.style.display = 'none';
            });
        });
    }

    // ------------------------------------------------------------------
    // Hover-play: swap preview ↔ animated GIF
    // ------------------------------------------------------------------

    function attachHoverPlay() {
        document.querySelectorAll('.tutorial-img').forEach((img) => {
            const wrapper = img.closest('.tutorial-img-wrapper');
            if (!wrapper) return;

            wrapper.addEventListener('mouseenter', () => {
                if (img.dataset.gif) {
                    img.src = img.dataset.gif;
                    img.setAttribute('aria-label', img.alt + ' (playing)');
                }
            });

            wrapper.addEventListener('mouseleave', () => {
                if (img.dataset.preview) {
                    img.src = img.dataset.preview;
                    img.setAttribute('aria-label', img.alt);
                }
            });

            // Keyboard: Enter/Space toggles play state for accessibility
            wrapper.setAttribute('tabindex', '0');
            wrapper.setAttribute('role', 'button');
            wrapper.setAttribute('aria-label', 'Play tutorial: ' + img.closest('.tutorial-card').querySelector('.card-title').textContent);

            let playing = false;
            wrapper.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (playing) {
                        img.src = img.dataset.preview;
                    } else {
                        img.src = img.dataset.gif;
                    }
                    playing = !playing;
                }
            });
        });
    }

    // ------------------------------------------------------------------
    // Asset probing (Issue #374): the tutorial GIF/PNG assets may not be
    // deployed. Probe the preview images up front; if ALL are missing,
    // rebuild the modal in text-only mode (titles + descriptions, no image
    // containers). If only some are missing, the per-image onerror fallback
    // above handles each one individually.
    // ------------------------------------------------------------------

    function probeTutorialAssets() {
        return Promise.all(
            TUTORIALS.map(
                (t) =>
                    new Promise((resolve) => {
                        const img = new Image();
                        img.onload = () => resolve(true);
                        img.onerror = () => resolve(false);
                        img.src = t.preview;
                    })
            )
        );
    }

    // ------------------------------------------------------------------
    // Inject modal + help button, wire up events
    // ------------------------------------------------------------------

    function injectModal(textOnly) {
        const existing = document.getElementById('helpModal');
        if (existing) existing.remove();
        const wrapper = document.createElement('div');
        wrapper.innerHTML = buildModalHTML(textOnly);
        document.body.appendChild(wrapper.firstElementChild);

        const modalEl = document.getElementById('helpModal');
        if (modalEl && !textOnly) {
            // Bind immediately: the <img> starts loading as soon as it's in
            // the DOM (independent of when the modal itself becomes visible).
            attachImageErrorFallback();
            // Start lazy loading once modal opens (saves bandwidth until user needs it)
            modalEl.addEventListener('shown.bs.modal', () => {
                observeImages();
                attachHoverPlay();
            }, { once: true });
        }
        return modalEl;
    }

    function init() {
        // Inject modal into body (image mode by default)
        injectModal(false);

        // Probe tutorial assets; if none exist, switch to text-only mode.
        // Rebuilding is safe: Bootstrap binds the trigger button lazily via
        // data-bs-target, so a replaced #helpModal keeps working. If the
        // modal is open right now, leave it — the per-image onerror
        // fallback is already showing text descriptions.
        probeTutorialAssets().then((results) => {
            const anyAvailable = results.some(Boolean);
            if (!anyAvailable) {
                const openModal = document.querySelector('#helpModal.show');
                if (!openModal) {
                    injectModal(true);
                }
            }
        });

        // Inject Help button into navbar if present
        const navList = document.querySelector('.navbar-nav');
        if (navList) {
            const li = document.createElement('li');
            li.className = 'nav-item';
            li.innerHTML = `
                <button type="button"
                        class="btn btn-link nav-link"
                        data-bs-toggle="modal"
                        data-bs-target="#helpModal"
                        aria-label="Open help and tutorials">
                    <i class="bi bi-question-circle" aria-hidden="true"></i>
                    <span class="ms-1 d-none d-lg-inline">Help</span>
                </button>`;
            navList.appendChild(li);
        }
    }

    // Run after DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
