/**
 * Route-highlighting logic injected into the commute map iframe (blob:
 * document rendered from Folium's HTML). Moved out of an inline <script>
 * built server-side in commute_service.py so CSP script-src doesn't need
 * 'unsafe-inline' for it (#475) — Folium's own map-init script still embeds
 * per-request coordinate data inline and can't be externalized the same way.
 */
(function() {
    // Listen for messages from parent window to highlight routes
    window.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'highlightRoute') {
            highlightRoute(event.data.direction);
        }
    });

    function highlightRoute(direction) {
        // Find all polylines with direction class
        const allPolylines = document.querySelectorAll('path.leaflet-interactive');

        allPolylines.forEach(function(polyline) {
            const classes = polyline.getAttribute('class') || '';

            // Check if this polyline matches the selected direction
            if (classes.includes('direction-' + direction)) {
                // Highlight: full opacity, thicker stroke
                polyline.style.opacity = '1.0';
                polyline.style.strokeOpacity = '1.0';
                polyline.style.strokeWidth = '8';
                polyline.style.zIndex = '1000';
            } else if (classes.includes('direction-')) {
                // Subdue: reduced opacity, thinner stroke
                polyline.style.opacity = '0.3';
                polyline.style.strokeOpacity = '0.3';
                polyline.style.strokeWidth = '5';
                polyline.style.zIndex = '1';
            }
        });
    }

    // Also add click handlers to polylines for direct interaction
    document.addEventListener('DOMContentLoaded', function() {
        const allPolylines = document.querySelectorAll('path.leaflet-interactive');

        allPolylines.forEach(function(polyline) {
            polyline.style.cursor = 'pointer';

            polyline.addEventListener('click', function() {
                const classes = this.getAttribute('class') || '';

                // Extract direction from class
                const directionMatch = classes.match(/direction-(\w+)/);
                if (directionMatch) {
                    highlightRoute(directionMatch[1]);

                    // Notify parent window
                    if (window.parent !== window) {
                        window.parent.postMessage({
                            type: 'routeClicked',
                            direction: directionMatch[1]
                        }, '*');
                    }
                }
            });
        });
    });
})();
