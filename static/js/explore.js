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

function setStart(lat, lon) {
    if (startMarker) map.removeLayer(startMarker);
    startMarker = L.marker([lat, lon], {
        title: 'Start',
        alt: 'Route start point',
    }).addTo(map).bindPopup('Start').openPopup();
    document.getElementById('start-display').textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
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

    const bounds = map.getBounds();
    const zoom = map.getZoom();

    try {
        let data;
        if (zoom >= 10) {
            data = await api.getTileCoverage({
                south: bounds.getSouth(),
                west: bounds.getWest(),
                north: bounds.getNorth(),
                east: bounds.getEast(),
            });
        } else {
            data = await api.getTileCoverage();
        }

        if (data.status !== 'success') {
            statusEl.textContent = data.message || 'Failed to load coverage';
            return;
        }

        coverageData = data;
        renderStats(data);
        renderTiles(data.visited);
        fitToCoverage(data);
        statusEl.textContent = `Updated ${new Date(data.computed_at).toLocaleTimeString()}`;
    } catch (e) {
        statusEl.textContent = `Error: ${e.message}`;
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

function renderTiles(visited) {
    tileLayer.clearLayers();
    if (!visited || typeof visited !== 'object') return;

    const zoom = 14;
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
    btn.disabled = true;
    statusEl.textContent = 'Computing exploration route…';

    const startPos = startMarker.getLatLng();
    const distanceKm = parseFloat(document.getElementById('distance-slider').value);

    explorationWorker.onmessage = (e) => {
        btn.disabled = false;
        const result = e.data;

        if (result.status !== 'success') {
            statusEl.textContent = result.message || 'Route generation failed';
            return;
        }

        renderWaypoints(result.waypoints);
        statusEl.textContent = `${result.stats.waypoints || 0} waypoints from ${result.stats.zones} zones (${result.stats.unvisited} unvisited tiles)`;
    };

    explorationWorker.onerror = (err) => {
        btn.disabled = false;
        statusEl.textContent = 'Worker error: ' + err.message;
    };

    explorationWorker.postMessage({
        start: { lat: startPos.lat, lon: startPos.lng },
        end: null,
        distanceKm,
        mode: 'tiles',
        routeType: 'round_trip',
        coverageData,
    });
}

function renderWaypoints(waypoints) {
    waypointMarkers.clearLayers();
    routeLayer.clearLayers();

    if (!waypoints || waypoints.length === 0) return;

    const startPos = startMarker.getLatLng();
    const coords = [[startPos.lat, startPos.lng]];

    waypoints.forEach((wp, i) => {
        coords.push([wp.lat, wp.lon]);
        const marker = L.circleMarker([wp.lat, wp.lon], {
            radius: 6,
            color: '#fd7e14',
            fillColor: '#fd7e14',
            fillOpacity: 0.8,
        }).bindPopup(`Waypoint ${i + 1}`);
        waypointMarkers.addLayer(marker);
    });

    coords.push([startPos.lat, startPos.lng]);

    const line = L.polyline(coords, {
        color: '#0d6efd',
        weight: 3,
        dashArray: '8, 8',
        opacity: 0.7,
    });
    routeLayer.addLayer(line);
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
