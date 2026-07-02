/**
 * explore.js — Tile coverage map and exploration route generation
 */

const api = new APIClient('/api');
let map = null;
let tileLayer = null;
let routeLayer = null;
let waypointMarkers = null;
let startMarker = null;
let coverageData = null;
let explorationWorker = null;

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initWorker();
    document.getElementById('load-coverage-btn').addEventListener('click', loadCoverage);
    document.getElementById('clear-cache-btn').addEventListener('click', clearCache);
    document.getElementById('generate-route-btn').addEventListener('click', generateRoute);
    document.getElementById('location-search-btn').addEventListener('click', searchLocation);
    document.getElementById('location-search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchLocation();
        }
    });
    initDistanceSlider();
    loadCoverage();
});

// ── Distance unit display ──────────────────────────────────────

function initDistanceSlider() {
    const unit = window.getDistanceUnit ? window.getDistanceUnit() : 'km';
    document.getElementById('distance-unit-label').textContent = unit;
    updateDistanceDisplay(document.getElementById('distance-slider').value);
}

window.updateDistanceDisplay = function(kmValue) {
    document.getElementById('distance-value').textContent =
        window.formatDistance ? window.formatDistance(parseFloat(kmValue), 1) : `${kmValue} km`;
};

// ── Map setup ───────────────────────────────────────────────────

function initMap() {
    map = L.map('explore-map').setView([39.83, -98.58], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18,
    }).addTo(map);
    tileLayer = L.layerGroup().addTo(map);
    routeLayer = L.layerGroup().addTo(map);
    waypointMarkers = L.layerGroup().addTo(map);

    map.on('click', (e) => {
        setStart(e.latlng.lat, e.latlng.lng);
    });
}

function setStart(lat, lon, label = null) {
    if (startMarker) map.removeLayer(startMarker);
    startMarker = L.marker([lat, lon], {
        title: 'Start',
        alt: 'Route start point',
    }).addTo(map).bindPopup('Start').openPopup();
    document.getElementById('start-display').textContent = label || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

// ── Location search (geocoding) ──────────────────────────────────

async function searchLocation() {
    const input = document.getElementById('location-search-input');
    const btn = document.getElementById('location-search-btn');
    const query = input.value.trim();
    if (!query) return;

    btn.disabled = true;
    const statusEl = document.getElementById('start-display');
    const previousText = statusEl.textContent;
    statusEl.textContent = 'Searching…';

    try {
        const result = await api.geocodeLocation(query);
        if (result.status !== 'success') {
            statusEl.textContent = previousText;
            if (typeof showToast === 'function') showToast(result.message || 'Location not found', 'warning');
            return;
        }

        setStart(result.lat, result.lon, result.display_name);
        map.setView([result.lat, result.lon], 12);
    } catch (e) {
        statusEl.textContent = previousText;
        if (typeof showToast === 'function') showToast(e.message || 'Location search failed', 'error');
    } finally {
        btn.disabled = false;
    }
}

// ── Web Worker ──────────────────────────────────────────────────

function initWorker() {
    if (typeof Worker === 'undefined') {
        document.getElementById('worker-status').textContent = 'Web Workers not supported — route generation unavailable';
        document.getElementById('generate-route-btn').disabled = true;
        return;
    }
    explorationWorker = new Worker('/js/exploration-worker.js');
}

// ── Coverage loading ────────────────────────────────────────────

async function loadCoverage() {
    const statusEl = document.getElementById('coverage-status');
    statusEl.textContent = 'Loading coverage…';
    const slowHintTimer = setTimeout(() => {
        statusEl.textContent = 'Still loading — first coverage load over your full ride history can take up to a minute…';
    }, 5000);

    const bounds = map.getBounds();
    const mapZoom = map.getZoom();
    const tileZoom = parseInt(document.getElementById('coverage-type-select').value, 10);

    try {
        let data;
        if (mapZoom >= 10) {
            data = await api.getTileCoverage({
                south: bounds.getSouth(),
                west: bounds.getWest(),
                north: bounds.getNorth(),
                east: bounds.getEast(),
            }, tileZoom);
        } else {
            data = await api.getTileCoverage(null, tileZoom);
        }

        if (data.status !== 'success') {
            statusEl.textContent = data.message || 'Failed to load coverage';
            return;
        }

        coverageData = data;
        renderStats(data);
        renderTiles(data.visited, data.zoom);
        fitToCoverage(data);
        statusEl.textContent = `Updated ${new Date(data.computed_at).toLocaleTimeString()}`;
    } catch (e) {
        statusEl.textContent = `Error: ${e.message}`;
    } finally {
        clearTimeout(slowHintTimer);
    }
}

function fitToCoverage(data) {
    if (!data.bounds || map.getZoom() >= 10) return;
    const [south, west, north, east] = data.bounds;
    map.fitBounds([[south, west], [north, east]], { padding: [20, 20], maxZoom: 13 });
}

function renderStats(data) {
    document.getElementById('stat-tiles-visited').textContent = data.visited_count.toLocaleString();
    document.getElementById('stat-coverage-pct').textContent = data.coverage_pct + '%';
    document.getElementById('stat-total-tiles').textContent = data.total_in_bounds.toLocaleString();
}

function renderTiles(visited, zoom = 14) {
    tileLayer.clearLayers();
    if (!visited || typeof visited !== 'object') return;

    const n = Math.pow(2, zoom);

    for (const key of Object.keys(visited)) {
        const [x, y] = key.split(',').map(Number);
        const west = x / n * 360 - 180;
        const east = (x + 1) / n * 360 - 180;
        const northRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
        const southRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n)));
        const north = northRad * 180 / Math.PI;
        const south = southRad * 180 / Math.PI;

        const rect = L.rectangle([[south, west], [north, east]], {
            color: '#28a745',
            weight: 0.5,
            fillOpacity: 0.35,
            interactive: false,
        });
        tileLayer.addLayer(rect);
    }
}

// ── Route generation ────────────────────────────────────────────

const ROUTE_COLORS = ['#0d6efd', '#fd7e14', '#6f42c1', '#20c997'];
const DIRECTION_LABELS = { NE: 'Northeast', SE: 'Southeast', SW: 'Southwest', NW: 'Northwest' };

async function generateRoute() {
    if (!explorationWorker) {
        if (typeof showToast === 'function') showToast('Web Workers not supported', 'error');
        return;
    }
    if (!startMarker) {
        if (typeof showToast === 'function') showToast('Click the map to set a start point', 'warning');
        return;
    }
    if (!coverageData) {
        if (typeof showToast === 'function') showToast('Load coverage data first', 'warning');
        return;
    }

    const btn = document.getElementById('generate-route-btn');
    const statusEl = document.getElementById('worker-status');
    const spinnerEl = document.getElementById('worker-spinner');
    btn.disabled = true;
    spinnerEl.classList.remove('d-none');
    statusEl.textContent = 'Computing exploration routes…';

    waypointMarkers.clearLayers();
    routeLayer.clearLayers();
    document.getElementById('route-list').innerHTML = '';

    const startPos = startMarker.getLatLng();
    const distanceKm = parseFloat(document.getElementById('distance-slider').value);
    const optimizeFor = document.getElementById('optimize-for-select').value;

    let routeCount = 0;

    const slowHintTimer = setTimeout(() => {
        statusEl.textContent += ' — still working, larger search areas can take longer…';
    }, 8000);

    const stopWorking = () => {
        btn.disabled = false;
        spinnerEl.classList.add('d-none');
        clearTimeout(slowHintTimer);
    };

    explorationWorker.onmessage = (e) => {
        const msg = e.data;

        if (msg.type === 'progress') {
            statusEl.textContent = msg.message;
            return;
        }

        if (msg.type === 'route') {
            renderRoute(msg.route, routeCount);
            addRouteListItem(msg.route, routeCount);
            routeCount++;
            statusEl.textContent = `Found ${routeCount} route${routeCount > 1 ? 's' : ''} so far…`;
            return;
        }

        if (msg.type === 'done') {
            stopWorking();
            statusEl.textContent = routeCount > 0
                ? `${routeCount} route${routeCount > 1 ? 's' : ''} generated`
                : 'No reachable unvisited tiles found — try increasing distance or moving the start point';
            return;
        }

        if (msg.type === 'error') {
            stopWorking();
            statusEl.textContent = msg.message || 'Route generation failed';
        }
    };

    explorationWorker.onerror = (err) => {
        stopWorking();
        statusEl.textContent = 'Worker error: ' + err.message;
    };

    explorationWorker.postMessage({
        start: { lat: startPos.lat, lon: startPos.lng },
        end: null,
        distanceKm,
        mode: 'tiles',
        routeType: 'round_trip',
        coverageData,
        optimizeFor,
    });
}

function renderRoute(route, index) {
    const color = ROUTE_COLORS[index % ROUTE_COLORS.length];
    const startPos = startMarker.getLatLng();
    const coords = [[startPos.lat, startPos.lng]];

    route.waypoints.forEach((wp, i) => {
        coords.push([wp.lat, wp.lon]);
        const marker = L.circleMarker([wp.lat, wp.lon], {
            radius: 6,
            color,
            fillColor: color,
            fillOpacity: 0.8,
        }).bindPopup(`${DIRECTION_LABELS[route.direction]} · Waypoint ${i + 1}`);
        waypointMarkers.addLayer(marker);
    });

    coords.push([startPos.lat, startPos.lng]);

    const distanceLabel = window.formatDistance ? window.formatDistance(route.stats.distanceKm, 1) : `${route.stats.distanceKm.toFixed(1)} km`;
    const line = L.polyline(coords, {
        color,
        weight: 3,
        dashArray: '8, 8',
        opacity: 0.8,
    }).bindPopup(`${DIRECTION_LABELS[route.direction]} — ${distanceLabel}, ${route.stats.unvisited} new tiles`);
    routeLayer.addLayer(line);
}

function addRouteListItem(route, index) {
    const color = ROUTE_COLORS[index % ROUTE_COLORS.length];
    const distanceLabel = window.formatDistance ? window.formatDistance(route.stats.distanceKm, 1) : `${route.stats.distanceKm.toFixed(1)} km`;

    const badge = document.createElement('span');
    badge.className = 'route-badge';
    badge.innerHTML = `
        <span class="swatch" style="background:${color}"></span>
        <span>${DIRECTION_LABELS[route.direction]} · ${distanceLabel} · ${route.stats.unvisited} new tiles</span>
    `;
    document.getElementById('route-list').appendChild(badge);
}

// ── Cache management ────────────────────────────────────────────

async function clearCache() {
    try {
        await api.invalidateCoverageCache();
        if (typeof showToast === 'function') showToast('Coverage cache cleared', 'info');
        loadCoverage();
    } catch (e) {
        if (typeof showToast === 'function') showToast('Failed to clear cache', 'error');
    }
}
