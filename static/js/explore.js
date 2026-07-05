/**
 * explore.js — Tile coverage map and exploration route generation
 *
 * Two-phase compute:
 *   Phase 1  Worker runs flood-fill + TSP client-side.  Each result is a
 *            dashed "straight-line preview" badge with a "Plot road route" button.
 *   Phase 2  User clicks the button → POST /api/exploration/route → iterative
 *            distance refinement → solid polyline + surface breakdown badge.
 */

const api = new APIClient('/api');
let map = null;
let tileLayer = null;
let tileLayerSecondary = null;
let routeLayer = null;
let waypointMarkers = null;
let startMarker = null;
let coverageData = null;
let coverageDataSecondary = null;
let explorationWorker = null;

// Phase-1 candidate lists per direction, for iterative refinement.
// { NE: [zoneList, ...], SE: [...], ... }
let _phase1Candidates = {};

const ZOOM_LABELS = { 14: 'Squadrats', 17: 'Squadratinhos' };

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initWorker();
    document.getElementById('load-coverage-btn').addEventListener('click', loadCoverage);
    document.getElementById('coverage-type-select').addEventListener('change', loadCoverage);
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
    tileLayerSecondary = L.layerGroup().addTo(map);
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

function getCoverageMode() {
    return document.getElementById('coverage-type-select').value; // '14' | '17' | 'both'
}

async function loadCoverage() {
    const statusEl = document.getElementById('coverage-status');
    statusEl.textContent = 'Loading coverage…';
    const slowHintTimer = setTimeout(() => {
        statusEl.textContent = 'Still loading — first coverage load over your full ride history can take up to a minute…';
    }, 5000);

    const bounds = map.getBounds();
    const mapZoom = map.getZoom();
    const mode = getCoverageMode();
    const zooms = mode === 'both' ? [14, 17] : [parseInt(mode, 10)];

    const fetchOne = (tileZoom) => mapZoom >= 10
        ? api.getTileCoverage({
            south: bounds.getSouth(),
            west: bounds.getWest(),
            north: bounds.getNorth(),
            east: bounds.getEast(),
        }, tileZoom)
        : api.getTileCoverage(null, tileZoom);

    try {
        const results = await Promise.all(zooms.map(fetchOne));
        const failed = results.find(d => d.status !== 'success');
        if (failed) {
            statusEl.textContent = failed.message || 'Failed to load coverage';
            return;
        }

        coverageData = results[0];
        coverageDataSecondary = results[1] || null;

        renderStats(coverageData, coverageDataSecondary);
        renderTiles(coverageData, coverageDataSecondary);
        fitToCoverage(coverageData);
        statusEl.textContent = `Updated ${new Date(coverageData.computed_at).toLocaleTimeString()}`;
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

function renderStats(primary, secondary) {
    const labelEls = document.querySelectorAll('#coverage-stats .stat-label');
    if (secondary) {
        document.getElementById('stat-tiles-visited').textContent =
            `${primary.visited_count.toLocaleString()} / ${secondary.visited_count.toLocaleString()}`;
        document.getElementById('stat-coverage-pct').textContent =
            `${primary.coverage_pct}% / ${secondary.coverage_pct}%`;
        document.getElementById('stat-total-tiles').textContent =
            `${primary.total_in_bounds.toLocaleString()} / ${secondary.total_in_bounds.toLocaleString()}`;
        labelEls.forEach(el => {
            if (!el.dataset.baseLabel) el.dataset.baseLabel = el.textContent;
            el.textContent = `${el.dataset.baseLabel} (Sq / Sqi)`;
        });
    } else {
        document.getElementById('stat-tiles-visited').textContent = primary.visited_count.toLocaleString();
        document.getElementById('stat-coverage-pct').textContent = primary.coverage_pct + '%';
        document.getElementById('stat-total-tiles').textContent = primary.total_in_bounds.toLocaleString();
        labelEls.forEach(el => {
            if (el.dataset.baseLabel) el.textContent = el.dataset.baseLabel;
        });
    }
}

function renderTiles(primary, secondary) {
    tileLayer.clearLayers();
    tileLayerSecondary.clearLayers();

    // In single-grid mode, keep the original green-fill styling. In "both"
    // mode, distinguish the coarser squadrat grid (blue outline) from the
    // finer squadratinho grid (green fill) drawn on top of it.
    const primaryStyle = secondary
        ? { color: '#0d6efd', weight: 1, fillOpacity: 0.08 }
        : { color: '#28a745', weight: 0.5, fillOpacity: 0.35 };
    const secondaryStyle = { color: '#28a745', weight: 0.5, fillOpacity: 0.35 };

    drawTileGrid(tileLayer, primary.visited, primary.zoom, primaryStyle);
    if (secondary) {
        drawTileGrid(tileLayerSecondary, secondary.visited, secondary.zoom, secondaryStyle);
    }
}

function drawTileGrid(layerGroup, visited, zoom, style) {
    if (!visited || typeof visited !== 'object') return;
    const n = Math.pow(2, zoom || 14);

    for (const key of Object.keys(visited)) {
        const [x, y] = key.split(',').map(Number);
        const west = x / n * 360 - 180;
        const east = (x + 1) / n * 360 - 180;
        const northRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
        const southRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n)));
        const north = northRad * 180 / Math.PI;
        const south = southRad * 180 / Math.PI;

        const rect = L.rectangle([[south, west], [north, east]], {
            ...style,
            interactive: false,
        });
        layerGroup.addLayer(rect);
    }
}

// ── Route generation ────────────────────────────────────────────

const ROUTE_COLORS = ['#0d6efd', '#fd7e14', '#6f42c1', '#20c997'];
const DIRECTION_LABELS = { NE: 'Northeast', SE: 'Southeast', SW: 'Southwest', NW: 'Northwest' };

// Per-direction Phase-1 polyline references, keyed by direction ('NE', etc.)
const _phase1Polylines = {};
// Per-direction Phase-2 polyline references
const _phase2Polylines = {};

/**
 * Draw small arrowhead triangles at the midpoint of each segment in `coords`.
 * Each arrow is a filled L.polygon added to routeLayer.
 * `coords` is an array of [lat, lng] pairs.
 */
function addArrows(coords, color) {
    const ARROW_SIZE_DEG = 0.0004; // ~40m half-length at mid-latitudes
    for (let i = 0; i < coords.length - 1; i++) {
        const [lat1, lng1] = coords[i];
        const [lat2, lng2] = coords[i + 1];
        // Skip degenerate segments
        if (lat1 === lat2 && lng1 === lng2) continue;

        // Midpoint
        const midLat = (lat1 + lat2) / 2;
        const midLng = (lng1 + lng2) / 2;

        // Direction vector (screen space approx — correct enough at any reasonable zoom)
        const dLat = lat2 - lat1;
        const dLng = (lng2 - lng1) * Math.cos(midLat * Math.PI / 180);
        const len = Math.sqrt(dLat * dLat + dLng * dLng);
        if (len === 0) continue;
        const uLat = dLat / len;
        const uLng = dLng / len / Math.cos(midLat * Math.PI / 180);

        // Arrow tip (forward), two base corners (perpendicular)
        const tip  = [midLat + uLat * ARROW_SIZE_DEG,       midLng + uLng * ARROW_SIZE_DEG];
        const base1 = [midLat - uLat * ARROW_SIZE_DEG * 0.6 - uLng * ARROW_SIZE_DEG * 0.5,
                        midLng - uLng * ARROW_SIZE_DEG * 0.6 + uLat * ARROW_SIZE_DEG * 0.5];
        const base2 = [midLat - uLat * ARROW_SIZE_DEG * 0.6 + uLng * ARROW_SIZE_DEG * 0.5,
                        midLng - uLng * ARROW_SIZE_DEG * 0.6 - uLat * ARROW_SIZE_DEG * 0.5];

        routeLayer.addLayer(L.polygon([tip, base1, base2], {
            color,
            fillColor: color,
            fillOpacity: 0.9,
            weight: 0,
            interactive: false,
        }));
    }
}

async function generateRoute() {
    if (!explorationWorker) {
        if (typeof showToast === 'function') showToast('Web Workers not supported', 'error');
        return;
    }
    if (!startMarker) {
        if (typeof showToast === 'function') showToast('Click the map to set a start point', 'warning');
        return;
    }
    const mode = getCoverageMode();
    if (!coverageData || (mode === 'both' && !coverageDataSecondary)) {
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
    _phase1Candidates = {};
    Object.keys(_phase1Polylines).forEach(k => delete _phase1Polylines[k]);
    Object.keys(_phase2Polylines).forEach(k => delete _phase2Polylines[k]);

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
            // Phase 1 result: render dashed preview and add badge with "Plot road route" button.
            renderRoute(msg.route, routeCount);
            addRouteListItem(msg.route, routeCount, distanceKm);
            // Store Phase-1 candidate data for iterative refinement.
            if (msg.candidates) {
                _phase1Candidates[msg.route.direction] = msg.candidates;
            }
            routeCount++;
            statusEl.textContent = `Found ${routeCount} route${routeCount > 1 ? 's' : ''} so far…`;
            return;
        }

        if (msg.type === 'done') {
            stopWorking();
            statusEl.textContent = routeCount > 0
                ? `${routeCount} route${routeCount > 1 ? 's' : ''} generated — click "Plot road route" to get real road directions`
                : 'No reachable unvisited tiles found — try increasing distance or moving the start point';
            if (routeCount > 0) {
                map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
            }
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
        coverageDataSecondary: mode === 'both' ? coverageDataSecondary : null,
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
    }).bindPopup(`${DIRECTION_LABELS[route.direction]} — ${distanceLabel}, ${newTilesLabel(route.stats)}`);
    routeLayer.addLayer(line);
    addArrows(coords, color);
    _phase1Polylines[route.direction] = line;
}

function newTilesLabel(stats) {
    if (stats.breakdown && stats.breakdown.length > 0) {
        return stats.breakdown.map(b => `${b.count} new ${b.label}`).join(' + ');
    }
    return `${stats.unvisited} new tiles`;
}

function addRouteListItem(route, index, targetDistanceKm) {
    const color = ROUTE_COLORS[index % ROUTE_COLORS.length];
    const distanceLabel = window.formatDistance ? window.formatDistance(route.stats.distanceKm, 1) : `${route.stats.distanceKm.toFixed(1)} km`;
    const dir = route.direction;

    const badge = document.createElement('div');
    badge.className = 'route-badge flex-column align-items-start';
    badge.dataset.direction = dir;
    badge.style.gap = '4px';
    badge.innerHTML = `
        <div class="d-flex align-items-center gap-2 w-100">
            <span class="swatch" style="background:${color}"></span>
            <span class="route-label">${DIRECTION_LABELS[dir]} · ${distanceLabel} · ${newTilesLabel(route.stats)}</span>
            <button class="btn btn-xs btn-outline-primary ms-auto plot-road-btn" data-direction="${dir}"
                    aria-label="Plot road route for ${DIRECTION_LABELS[dir]}">
                <i class="bi bi-map" aria-hidden="true"></i> Plot road route
            </button>
        </div>
        <div class="route-phase2-info text-muted small d-none" data-direction="${dir}"></div>
    `;
    document.getElementById('route-list').appendChild(badge);

    badge.querySelector('.plot-road-btn').addEventListener('click', () => {
        plotRoadRoute(dir, route, targetDistanceKm, color, badge);
    });
}

// ── Phase 2: Road routing ────────────────────────────────────────

async function plotRoadRoute(direction, route, targetDistanceKm, color, badgeEl) {
    const plotBtn = badgeEl.querySelector('.plot-road-btn');
    const infoEl = badgeEl.querySelector('.route-phase2-info');

    plotBtn.disabled = true;
    plotBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Routing…';
    infoEl.textContent = 'Calling road routing service…';
    infoEl.classList.remove('d-none');

    const startPos = startMarker.getLatLng();
    const surfacePref = document.getElementById('surface-preference-select').value;

    // Build waypoints list: start → route waypoints → start (round trip).
    const baseWaypoints = [
        [startPos.lat, startPos.lng],
        ...route.waypoints.map(wp => [wp.lat, wp.lon]),
        [startPos.lat, startPos.lng],
    ];

    // Iterative refinement: adjust waypoints up to 3 iterations to get within 10% of target.
    const TOLERANCE = 0.10;
    const MAX_ITERATIONS = 3;
    let waypoints = baseWaypoints;
    let result = null;
    let candidateList = (_phase1Candidates[direction] || []).slice(); // remaining candidates

    for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
        try {
            result = await api.getExplorationRoute({ waypoints, surfacePreference: surfacePref });
        } catch (err) {
            // Network/API error — fall back gracefully.
            result = null;
            break;
        }

        if (!result || result.status !== 'success') break;

        const ratio = result.distance_km / targetDistanceKm;
        if (Math.abs(ratio - 1) <= TOLERANCE) break; // within 10% — done

        if (ratio > 1 + TOLERANCE && waypoints.length > 3) {
            // Too long: drop the last non-start/end waypoint (lowest-priority).
            waypoints = [waypoints[0], ...waypoints.slice(1, -2), waypoints[waypoints.length - 1]];
        } else if (ratio < 1 - TOLERANCE && candidateList.length > 0) {
            // Too short: pull in the next candidate zone.
            const next = candidateList.shift();
            waypoints = [
                waypoints[0],
                ...waypoints.slice(1, -1),
                [next.centroid.lat, next.centroid.lon],
                waypoints[waypoints.length - 1],
            ];
        } else {
            break; // Nothing more to adjust.
        }
    }

    if (!result || result.status !== 'success') {
        const errMsg = (result && result.message) || 'Road routing unavailable';
        if (typeof showToast === 'function') showToast(errMsg, 'warning');
        infoEl.textContent = errMsg;
        plotBtn.disabled = false;
        plotBtn.innerHTML = '<i class="bi bi-map" aria-hidden="true"></i> Plot road route';
        return;
    }

    // Replace dashed preview with solid road-following polyline.
    if (_phase1Polylines[direction]) {
        routeLayer.removeLayer(_phase1Polylines[direction]);
        delete _phase1Polylines[direction];
    }
    if (_phase2Polylines[direction]) {
        routeLayer.removeLayer(_phase2Polylines[direction]);
    }

    const latlngs = result.coordinates.map(([lat, lon]) => [lat, lon]);
    const solidLine = L.polyline(latlngs, { color, weight: 4, opacity: 0.9 });
    const distLabel = window.formatDistance ? window.formatDistance(result.distance_km, 1) : `${result.distance_km} km`;
    solidLine.bindPopup(`${DIRECTION_LABELS[direction]} (road) — ${distLabel}, ${result.duration_min} min`);
    routeLayer.addLayer(solidLine);
    addArrows(latlngs, color);
    _phase2Polylines[direction] = solidLine;

    // Update badge: replace straight-line stats with real stats + surface + GPX button.
    const sb = result.surface_breakdown || {};
    const surfaceText = (sb.paved_pct != null)
        ? `${sb.paved_pct}% paved · ${sb.unpaved_pct}% unpaved · ${sb.unknown_pct}% unknown`
        : '';

    const labelEl = badgeEl.querySelector('.route-label');
    if (labelEl) {
        labelEl.textContent = `${DIRECTION_LABELS[direction]} · ${distLabel} · ${result.duration_min} min`;
    }

    infoEl.innerHTML = `
        ${surfaceText ? `<span>${surfaceText}</span> · ` : ''}
        <button class="btn btn-xs btn-outline-secondary export-gpx-btn"
                aria-label="Export GPX for ${DIRECTION_LABELS[direction]}">
            <i class="bi bi-download" aria-hidden="true"></i> Export GPX
        </button>
    `;

    infoEl.querySelector('.export-gpx-btn').addEventListener('click', () => {
        downloadGpx(result.coordinates, direction);
    });

    plotBtn.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i> Re-plot';
    plotBtn.disabled = false;
}

// ── GPX export ───────────────────────────────────────────────────

function buildGpx(coordinates) {
    const trkpts = coordinates.map(([lat, lon]) =>
        `    <trkpt lat="${lat}" lon="${lon}"/>`
    ).join('\n');

    return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Ride Optimizer"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata><time>${new Date().toISOString()}</time></metadata>
  <trk>
    <name>Exploration Route</name>
    <trkseg>
${trkpts}
    </trkseg>
  </trk>
</gpx>`;
}

function downloadGpx(coordinates, direction) {
    const gpx = buildGpx(coordinates);
    const blob = new Blob([gpx], { type: 'application/gpx+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `exploration-${direction.toLowerCase()}-${Date.now()}.gpx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
