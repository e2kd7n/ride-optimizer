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
let newTilesLayer = null;   // green highlight for tiles a route will claim
let routeLayer = null;
let waypointMarkers = null;
let startMarker = null;
let endMarker = null;
let coverageData = null;
let coverageDataSecondary = null;
let explorationWorker = null;

// #491: rider-drawn target area — [south, west, north, east] | null.
let selectedAreaBounds = null;
let isDrawingArea = false;
let drawAreaRect = null;
let _drawStartLatLng = null;
let _skipNextMapClick = false;

// Phase-1 candidate lists per direction, for iterative refinement.
// { NE: [zoneList, ...], SE: [...], ... }
let _phase1Candidates = {};

// #453: current wind, fetched once per session and reused across route
// generations rather than re-fetched per click.
let _sessionWind = undefined; // undefined = not yet fetched, null = unavailable

/**
 * Fetch current wind conditions once per session for the worker's
 * headwind-out/tailwind-back tie-break (#453). Failure is silent — the
 * worker falls back to its current (non-wind-aware) behavior when wind is
 * unavailable, matching the acceptance criteria.
 */
async function getSessionWind() {
    if (_sessionWind !== undefined) return _sessionWind;
    try {
        const res = await api.getWeather();
        const current = res && res.current;
        if (current && current.wind_direction_deg != null && current.wind_speed_kph != null) {
            _sessionWind = { windDirectionDeg: current.wind_direction_deg, windSpeedKph: current.wind_speed_kph };
        } else {
            _sessionWind = null;
        }
    } catch {
        _sessionWind = null;
    }
    return _sessionWind;
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initWorker();
    document.getElementById('coverage-type-select').addEventListener('change', () => {
        if (startMarker) loadCoverage();
    });
    document.getElementById('clear-cache-btn').addEventListener('click', clearCache);
    document.getElementById('generate-route-btn').addEventListener('click', generateRoute);
    document.getElementById('workout-combo-btn').addEventListener('click', generateWorkoutCombo);
    document.getElementById('location-search-btn').addEventListener('click', searchLocation);
    document.getElementById('location-search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); searchLocation(); }
    });
    document.getElementById('use-my-location-btn').addEventListener('click', useMyLocation);
    document.getElementById('route-type-select').addEventListener('change', onRouteTypeChange);
    document.getElementById('end-search-btn').addEventListener('click', searchEndLocation);
    document.getElementById('end-search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); searchEndLocation(); }
    });
    initDistanceSlider();
    initDurationSlider();
    document.getElementById('target-type-select').addEventListener('change', onTargetTypeChange);
    document.getElementById('draw-area-btn').addEventListener('click', toggleDrawArea);
    document.getElementById('clear-area-btn').addEventListener('click', clearArea);
    initTooltips();
    updateWorkflowState();
});

// ── Bootstrap tooltips (#360 help icon) ────────────────────────

function initTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
        new bootstrap.Tooltip(el);
    });
}

// ── Distance unit display ──────────────────────────────────────

function initDistanceSlider() {
    const unit = window.getDistanceUnit ? window.getDistanceUnit() : 'km';
    document.getElementById('distance-unit-label').textContent = unit;
    const slider = document.getElementById('distance-slider');
    updateDistanceDisplay(slider.value);
    // Bound here instead of an inline oninput="" attribute so CSP
    // script-src can drop 'unsafe-inline' — #475.
    slider.addEventListener('input', () => updateDistanceDisplay(slider.value));
}

function updateDistanceDisplay(kmValue) {
    document.getElementById('distance-value').textContent =
        window.formatDistance ? window.formatDistance(parseFloat(kmValue), 1) : `${kmValue} km`;
}

// ── Duration-based target (#490) ────────────────────────────────
//
// Duration is converted to a distance budget using the rider's own
// historical average speed (GET /api/stats → summary.avg_speed_mph),
// falling back to a configured default (exploration.default_speed_kmh in
// config.yaml, surfaced as default_speed_mph) when there's no ride history
// to average. The worker pipeline is unaware of duration — it only ever
// receives a computed distanceKm, same as the distance-slider path.

let _avgSpeedKmhPromise = null;

async function getAvgSpeedKmh() {
    if (!_avgSpeedKmhPromise) {
        _avgSpeedKmhPromise = (async () => {
            const FALLBACK_KMH = 18;
            try {
                const stats = await api.getStats();
                const summaryMph = stats.data && stats.data.summary && stats.data.summary.avg_speed_mph;
                const defaultMph = (stats.data && stats.data.default_speed_mph) || stats.default_speed_mph;
                const mph = (summaryMph && summaryMph > 0) ? summaryMph : defaultMph;
                return (mph && mph > 0) ? mph * 1.60934 : FALLBACK_KMH;
            } catch (e) {
                return FALLBACK_KMH;
            }
        })();
    }
    return _avgSpeedKmhPromise;
}

function onTargetTypeChange() {
    const isDuration = document.getElementById('target-type-select').value === 'duration';
    document.getElementById('distance-target-group').classList.toggle('d-none', isDuration);
    document.getElementById('duration-target-group').classList.toggle('d-none', !isDuration);
    if (isDuration) updateDurationHint();
}

function initDurationSlider() {
    const slider = document.getElementById('duration-slider');
    document.getElementById('duration-value').textContent = slider.value;
    slider.addEventListener('input', () => {
        document.getElementById('duration-value').textContent = slider.value;
        updateDurationHint();
    });
}

async function updateDurationHint() {
    const hintEl = document.getElementById('duration-speed-hint');
    hintEl.textContent = 'Estimating distance from your average speed…';
    const minutes = parseFloat(document.getElementById('duration-slider').value);
    const speedKmh = await getAvgSpeedKmh();
    const distanceKm = (minutes / 60) * speedKmh;
    const distanceLabel = window.formatDistance ? window.formatDistance(distanceKm, 1) : `${distanceKm.toFixed(1)} km`;
    const speedLabel = window.formatSpeed ? window.formatSpeed(speedKmh, 1) : `${speedKmh.toFixed(1)} km/h`;
    hintEl.textContent = `≈ ${distanceLabel} at your average ${speedLabel}`;
}

/** Resolve the current distance-slider or duration-slider control into a distanceKm target for the worker. */
async function resolveTargetDistanceKm() {
    if (document.getElementById('target-type-select').value === 'duration') {
        const minutes = parseFloat(document.getElementById('duration-slider').value);
        const speedKmh = await getAvgSpeedKmh();
        return (minutes / 60) * speedKmh;
    }
    return parseFloat(document.getElementById('distance-slider').value);
}

// ── Map setup ───────────────────────────────────────────────────

function initMap() {
    map = L.map('explore-map').setView([39.83, -98.58], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18,
    }).addTo(map);
    newTilesLayer = L.layerGroup().addTo(map);  // below routes
    // FeatureGroup, not LayerGroup — routeLayer.getBounds() (used to fit the
    // map after routes are generated) only exists on FeatureGroup in Leaflet
    // 1.9.4; LayerGroup lacks it despite otherwise sharing the same API.
    routeLayer = L.featureGroup().addTo(map);
    waypointMarkers = L.layerGroup().addTo(map);

    // #491: click-and-drag to draw a target-area rectangle. Only active
    // while "Draw area" is toggled on; otherwise these are no-ops and the
    // map behaves as before (pan/click-to-set-start).
    map.on('mousedown', (e) => {
        if (!isDrawingArea) return;
        _drawStartLatLng = e.latlng;
        if (drawAreaRect) { map.removeLayer(drawAreaRect); drawAreaRect = null; }
        drawAreaRect = L.rectangle(L.latLngBounds(e.latlng, e.latlng), {
            color: '#0d6efd', weight: 2, fillOpacity: 0.08, dashArray: '4,4',
        }).addTo(map);
    });
    map.on('mousemove', (e) => {
        if (!isDrawingArea || !_drawStartLatLng || !drawAreaRect) return;
        drawAreaRect.setBounds(L.latLngBounds(_drawStartLatLng, e.latlng));
    });
    map.on('mouseup', (e) => {
        if (!isDrawingArea || !_drawStartLatLng) return;
        const drawnBounds = L.latLngBounds(_drawStartLatLng, e.latlng);
        _drawStartLatLng = null;
        _skipNextMapClick = true; // the browser fires 'click' right after this mouseup

        if (!drawnBounds.isValid() || drawnBounds.getNorthEast().equals(drawnBounds.getSouthWest())) {
            // Degenerate rectangle (no drag distance) — treat as a cancel.
            if (drawAreaRect) { map.removeLayer(drawAreaRect); drawAreaRect = null; }
        } else {
            selectedAreaBounds = [
                drawnBounds.getSouth(), drawnBounds.getWest(),
                drawnBounds.getNorth(), drawnBounds.getEast(),
            ];
            document.getElementById('clear-area-btn').classList.remove('d-none');
            document.getElementById('area-status').textContent = 'Area selected — routes stay within it';
        }
        setDrawAreaMode(false);
    });

    map.on('click', (e) => {
        if (_skipNextMapClick) { _skipNextMapClick = false; return; }
        if (isDrawingArea) return;
        clearHighlight();
        const routeType = document.getElementById('route-type-select').value;
        // In point-to-point mode: first click sets end if unset, else update start.
        if (routeType === 'point_to_point' && !endMarker) {
            setEnd(e.latlng.lat, e.latlng.lng);
        } else {
            setStart(e.latlng.lat, e.latlng.lng);
        }
    });
}

/** Enter or exit rectangle-draw mode (#491), disabling map panning while active
 *  so a click-drag draws a box instead of moving the map. */
function setDrawAreaMode(active) {
    isDrawingArea = active;
    document.getElementById('draw-area-btn').classList.toggle('active', active);
    map.dragging[active ? 'disable' : 'enable']();
    map.getContainer().style.cursor = active ? 'crosshair' : '';
    if (active) {
        document.getElementById('area-status').textContent = 'Click and drag on the map to draw an area…';
    }
}

function toggleDrawArea() {
    setDrawAreaMode(!isDrawingArea);
}

function clearArea() {
    if (drawAreaRect) { map.removeLayer(drawAreaRect); drawAreaRect = null; }
    selectedAreaBounds = null;
    document.getElementById('clear-area-btn').classList.add('d-none');
    document.getElementById('area-status').textContent = '';
}

function setStart(lat, lon, label = null) {
    if (startMarker) map.removeLayer(startMarker);
    startMarker = L.marker([lat, lon], {
        title: 'Start',
        alt: 'Route start point',
    }).addTo(map).bindPopup('Start').openPopup();
    document.getElementById('start-display').textContent = label || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    updateWorkflowState();
    // #488: coverage loads silently against the new start point instead of
    // requiring a separate "Load Coverage" step.
    loadCoverage();
}

function setEnd(lat, lon, label = null) {
    if (endMarker) map.removeLayer(endMarker);
    // Coral/red end marker to distinguish from the default blue start marker.
    endMarker = L.marker([lat, lon], {
        title: 'End',
        alt: 'Route end point',
        icon: L.divIcon({
            className: '',
            html: '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">' +
                  '<path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0z" fill="#C4483A"/>' +
                  '<circle cx="12.5" cy="12.5" r="5" fill="#fff"/>' +
                  '</svg>',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
        }),
    }).addTo(map).bindPopup('End').openPopup();
    document.getElementById('end-display').textContent = label || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    updateWorkflowState();
}

function clearEnd() {
    if (endMarker) { map.removeLayer(endMarker); endMarker = null; }
    document.getElementById('end-display').textContent = 'Click map or search to set';
    document.getElementById('end-search-input').value = '';
    updateWorkflowState();
}

// ── Route type toggle ───────────────────────────────────────────

function onRouteTypeChange() {
    const isPtp = document.getElementById('route-type-select').value === 'point_to_point';
    document.getElementById('end-location-group').classList.toggle('d-none', !isPtp);
    if (!isPtp) clearEnd();
    updateWorkflowState();
}

// ── Workflow step tracking (#361) ──────────────────────────────

function isCoverageReady() {
    const mode = getCoverageMode();
    return !!coverageData && !(mode === 'both' && !coverageDataSecondary);
}

function updateWorkflowState() {
    const coverageReady = isCoverageReady();
    const startReady = !!startMarker;
    const isPtp = document.getElementById('route-type-select').value === 'point_to_point';
    const ready = coverageReady && startReady && (!isPtp || !!endMarker);

    document.getElementById('workflow-step-1').classList.toggle('workflow-step-done', startReady);
    document.getElementById('workflow-step-2').classList.toggle('workflow-step-done', ready);

    if (!explorationWorker) return; // unsupported-worker state already disables the button with its own message

    const btn = document.getElementById('generate-route-btn');
    btn.disabled = !ready;
    // Coral (.btn-cta) is reserved for this one enabled CTA on the page (#361).
    btn.classList.toggle('btn-cta', ready);
    btn.classList.toggle('btn-outline-primary', !ready);

    // Workout combo button requires coverage loaded (start not required — uses workout start).
    const comboBtn = document.getElementById('workout-combo-btn');
    if (comboBtn) comboBtn.disabled = !coverageReady || !explorationWorker;

    const statusEl = document.getElementById('worker-status');
    if (!ready) {
        const missing = [];
        if (!startReady) missing.push('set a start point');
        if (startReady && !coverageReady) missing.push('wait for coverage to finish loading');
        if (isPtp && !endMarker) missing.push('set an end point');
        statusEl.textContent = `Next: ${missing.join(' and ')} to generate routes.`;
    } else {
        statusEl.textContent = 'Ready to generate routes.';
    }
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
        map.setView([result.lat, result.lon], 12);
        setStart(result.lat, result.lon, result.display_name);
    } catch (e) {
        statusEl.textContent = previousText;
        if (typeof showToast === 'function') showToast(e.message || 'Location search failed', 'error');
    } finally {
        btn.disabled = false;
    }
}

async function searchEndLocation() {
    const input = document.getElementById('end-search-input');
    const btn = document.getElementById('end-search-btn');
    const query = input.value.trim();
    if (!query) return;

    btn.disabled = true;
    const statusEl = document.getElementById('end-display');
    const previousText = statusEl.textContent;
    statusEl.textContent = 'Searching…';

    try {
        const result = await api.geocodeLocation(query);
        if (result.status !== 'success') {
            statusEl.textContent = previousText;
            if (typeof showToast === 'function') showToast(result.message || 'Location not found', 'warning');
            return;
        }
        setEnd(result.lat, result.lon, result.display_name);
        map.setView([result.lat, result.lon], 12);
    } catch (e) {
        statusEl.textContent = previousText;
        if (typeof showToast === 'function') showToast(e.message || 'Location search failed', 'error');
    } finally {
        btn.disabled = false;
    }
}

async function useMyLocation() {
    const btn = document.getElementById('use-my-location-btn');
    if (!navigator.geolocation) {
        if (typeof showToast === 'function') showToast('Geolocation is not supported by this browser', 'warning');
        return;
    }

    btn.disabled = true;
    const statusEl = document.getElementById('start-display');
    const previousText = statusEl.textContent;
    statusEl.textContent = 'Locating…';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            map.setView([latitude, longitude], 13);
            setStart(latitude, longitude);
            btn.disabled = false;
        },
        (err) => {
            statusEl.textContent = previousText;
            if (typeof showToast === 'function') showToast(err.message || 'Unable to determine your location', 'error');
            btn.disabled = false;
        },
        { enableHighAccuracy: false, timeout: 10000 },
    );
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

        // #488: coverage is loaded to feed the route generator, not to browse
        // on the map — clear any stale "new tile" highlight from a previous
        // start point/grid rather than rendering the full visited-tile grid.
        newTilesLayer.clearLayers();
        statusEl.textContent = `Updated ${new Date(coverageData.computed_at + 'Z').toLocaleTimeString()}`;
    } catch (e) {
        statusEl.textContent = `Error: ${e.message}`;
    } finally {
        clearTimeout(slowHintTimer);
        updateWorkflowState();
    }
}

// New tiles a route will claim: bright Squadrats-green
const TILE_STYLE_NEW = { color: '#2e7d32', weight: 0.5, fillColor: '#4caf50', fillOpacity: 0.65 };

/**
 * Render green highlight rectangles for the new (unvisited) tiles a route
 * will claim, computing each tile's lat/lon boundary from its zoom-level key.
 * newTilesByZoom: [{zoom, tiles: [{x, y}]}]
 *
 * When `direction` is given, any rectangles previously rendered for that
 * direction are removed first — this lets Phase 2 (#493) replace a
 * direction's speculative Phase-1 highlight with the set of tiles the real
 * road route actually crosses, without disturbing the other 3 directions.
 */
function renderNewTiles(newTilesByZoom, direction = null) {
    if (direction && _newTileRectsByDirection[direction]) {
        _newTileRectsByDirection[direction].forEach(r => newTilesLayer.removeLayer(r));
    }
    const rects = [];
    for (const { zoom, tiles } of newTilesByZoom || []) {
        const n = Math.pow(2, zoom);
        for (const { x, y } of tiles) {
            const west  = x / n * 360 - 180;
            const east  = (x + 1) / n * 360 - 180;
            const north = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)))       * 180 / Math.PI;
            const south = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n))) * 180 / Math.PI;
            const rect = L.rectangle([[south, west], [north, east]], {
                ...TILE_STYLE_NEW,
                interactive: false,
            });
            newTilesLayer.addLayer(rect);
            rects.push(rect);
        }
    }
    if (direction) _newTileRectsByDirection[direction] = rects;
}

// ── Route generation ────────────────────────────────────────────

/**
 * Tonal colour pairs per direction (#409).
 * base  = Phase-2 road polyline + badge swatch.
 * light = Phase-1 dashed preview (lower saturation).
 */
const ROUTE_PALETTE = {
    NE: { base: '#0d6efd', light: '#7ab5fe' },
    SE: { base: '#e8690e', light: '#f5ac71' },
    SW: { base: '#6f42c1', light: '#b094dd' },
    NW: { base: '#0f9e7a', light: '#6fd4bb' },
};
const _PALETTE_ORDER = ['NE', 'SE', 'SW', 'NW'];
function _paletteFor(dirOrIndex) {
    if (typeof dirOrIndex === 'string' && ROUTE_PALETTE[dirOrIndex]) return ROUTE_PALETTE[dirOrIndex];
    return ROUTE_PALETTE[_PALETTE_ORDER[dirOrIndex % 4]];
}

const DIRECTION_LABELS = { NE: 'Northeast', SE: 'Southeast', SW: 'Southwest', NW: 'Northwest' };
const SHAPE_LABELS = { loop: 'Loop', out_and_back: 'Out-and-back', point_to_point: 'Point-to-point' };

// Per-direction Phase-1 polyline references, keyed by direction ('NE', etc.)
const _phase1Polylines = {};
// Per-direction Phase-2 polyline references
const _phase2Polylines = {};
// Per-direction new-tile highlight rectangles (#493), so Phase 2 verification
// can replace one direction's highlight with ground truth without touching
// the other three directions' Phase-1 previews.
const _newTileRectsByDirection = {};

// ── Highlight / deselect state (#407 + #408) ─────────────────────

let _selectedDirection = null;
const _BASE_STYLE_P1 = { weight: 3, opacity: 0.8 };
const _BASE_STYLE_P2 = { weight: 4, opacity: 1.0 };
const _DIM_OPACITY    = 0.25;

function highlightRoute(dir) {
    if (_selectedDirection === dir) { clearHighlight(); return; }
    _selectedDirection = dir;
    Object.keys(_phase1Polylines).forEach(k => {
        _phase1Polylines[k].setStyle(k === dir ? { weight: 5, opacity: 1.0 } : { opacity: _DIM_OPACITY });
    });
    Object.keys(_phase2Polylines).forEach(k => {
        _phase2Polylines[k].setStyle(k === dir ? { weight: 6, opacity: 1.0 } : { opacity: _DIM_OPACITY });
    });
    document.querySelectorAll('.route-badge').forEach(el => {
        el.classList.toggle('route-badge--selected', el.dataset.direction === dir);
        el.classList.toggle('route-badge--dimmed',   el.dataset.direction !== dir);
    });
    const activeBadge = document.querySelector(`.route-badge[data-direction="${dir}"]`);
    if (activeBadge) activeBadge.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const active = _phase2Polylines[dir] || _phase1Polylines[dir];
    if (active) { try { map.fitBounds(active.getBounds(), { padding: [32, 32] }); } catch (_) {} }
}

function clearHighlight() {
    _selectedDirection = null;
    Object.keys(_phase1Polylines).forEach(k => _phase1Polylines[k].setStyle(_BASE_STYLE_P1));
    Object.keys(_phase2Polylines).forEach(k => _phase2Polylines[k].setStyle(_BASE_STYLE_P2));
    document.querySelectorAll('.route-badge').forEach(el =>
        el.classList.remove('route-badge--selected', 'route-badge--dimmed'));
}

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

    clearHighlight();
    waypointMarkers.clearLayers();
    newTilesLayer.clearLayers();
    routeLayer.clearLayers();
    document.getElementById('route-list').innerHTML = '';
    _phase1Candidates = {};
    Object.keys(_phase1Polylines).forEach(k => delete _phase1Polylines[k]);
    Object.keys(_phase2Polylines).forEach(k => delete _phase2Polylines[k]);
    Object.keys(_newTileRectsByDirection).forEach(k => delete _newTileRectsByDirection[k]);

    const startPos = startMarker.getLatLng();
    const distanceKm = await resolveTargetDistanceKm();
    const optimizeFor = document.getElementById('optimize-for-select').value;

    let routeCount = 0;

    const slowHintTimer = setTimeout(() => {
        statusEl.textContent += ' — still working, larger search areas can take longer…';
    }, 8000);

    const stopWorking = () => {
        spinnerEl.classList.add('d-none');
        clearTimeout(slowHintTimer);
        updateWorkflowState();
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
            // Highlight the new tiles this route will claim.
            renderNewTiles(msg.route.newTilesByZoom, msg.route.direction);
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

    const shape = document.getElementById('route-type-select').value; // 'loop' | 'out_and_back' | 'point_to_point'
    const routeType = shape === 'point_to_point' ? 'point_to_point' : 'round_trip';
    const endPos = (routeType === 'point_to_point' && endMarker) ? endMarker.getLatLng() : null;
    const wind = await getSessionWind();

    explorationWorker.postMessage({
        start: { lat: startPos.lat, lon: startPos.lng },
        end: endPos ? { lat: endPos.lat, lon: endPos.lng } : null,
        distanceKm,
        mode: 'tiles',
        routeType,
        shape,
        coverageData,
        coverageDataSecondary: mode === 'both' ? coverageDataSecondary : null,
        optimizeFor,
        areaBounds: selectedAreaBounds,
        windDirectionDeg: wind ? wind.windDirectionDeg : null,
        windSpeedKph: wind ? wind.windSpeedKph : null,
    });
}

/**
 * #405 — Workout combo: fetch today's recommendation, use its start location
 * and corridor to constrain the exploration worker toward nearby unvisited tiles.
 */
async function generateWorkoutCombo() {
    if (!explorationWorker || !isCoverageReady()) return;

    const statusEl = document.getElementById('worker-status');
    const spinnerEl = document.getElementById('worker-spinner');
    const comboBtn = document.getElementById('workout-combo-btn');
    comboBtn.disabled = true;
    spinnerEl.classList.remove('d-none');
    statusEl.textContent = 'Fetching today\'s workout recommendation…';

    let rec;
    try {
        rec = await api.getRecommendation();
    } catch (e) {
        statusEl.textContent = 'No workout recommendation available for today.';
        spinnerEl.classList.add('d-none');
        comboBtn.disabled = false;
        return;
    }

    if (!rec || rec.status !== 'success' || !rec.recommended_route) {
        statusEl.textContent = 'No workout recommendation available for today.';
        spinnerEl.classList.add('d-none');
        comboBtn.disabled = false;
        return;
    }

    const workoutRoute = rec.recommended_route;
    const coords = workoutRoute.coordinates || [];
    if (coords.length === 0) {
        statusEl.textContent = 'Workout recommendation has no route coordinates.';
        spinnerEl.classList.add('d-none');
        comboBtn.disabled = false;
        return;
    }

    // Derive start from first coordinate; set it on the map if not already set.
    const [startLat, startLon] = coords[0];
    if (!startMarker) setStart(startLat, startLon, `Workout start: ${workoutRoute.name || 'Route'}`);

    const distanceKm = workoutRoute.distance ? workoutRoute.distance / 1000 : parseFloat(document.getElementById('distance-slider').value);
    const optimizeFor = document.getElementById('optimize-for-select').value;
    const mode = getCoverageMode();

    clearHighlight();
    waypointMarkers.clearLayers();
    newTilesLayer.clearLayers();
    routeLayer.clearLayers();
    document.getElementById('route-list').innerHTML = '';
    _phase1Candidates = {};
    Object.keys(_phase1Polylines).forEach(k => delete _phase1Polylines[k]);
    Object.keys(_phase2Polylines).forEach(k => delete _phase2Polylines[k]);
    Object.keys(_newTileRectsByDirection).forEach(k => delete _newTileRectsByDirection[k]);

    let routeCount = 0;
    explorationWorker.onmessage = (e) => {
        const msg = e.data;
        if (msg.type === 'progress') { statusEl.textContent = msg.message; return; }
        if (msg.type === 'route') {
            renderRoute(msg.route, routeCount);
            // Label as workout combo.
            addRouteListItem(msg.route, routeCount, distanceKm, '· Workout combo');
            renderNewTiles(msg.route.newTilesByZoom, msg.route.direction);
            if (msg.candidates) _phase1Candidates[msg.route.direction] = msg.candidates;
            routeCount++;
            statusEl.textContent = `Found ${routeCount} workout-combo route${routeCount > 1 ? 's' : ''} so far…`;
            return;
        }
        if (msg.type === 'done') {
            spinnerEl.classList.add('d-none');
            statusEl.textContent = routeCount > 0
                ? `${routeCount} workout-combo route${routeCount > 1 ? 's' : ''} generated`
                : 'No nearby unvisited tiles found along the workout corridor — try a different day or move the start point';
            if (routeCount > 0 && routeLayer.getBounds().isValid()) {
                map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
            }
            comboBtn.disabled = false;
            updateWorkflowState();
            return;
        }
        if (msg.type === 'error') {
            spinnerEl.classList.add('d-none');
            statusEl.textContent = msg.message || 'Workout combo failed';
            comboBtn.disabled = false;
            updateWorkflowState();
        }
    };
    explorationWorker.onerror = (err) => {
        spinnerEl.classList.add('d-none');
        statusEl.textContent = 'Worker error: ' + err.message;
        comboBtn.disabled = false;
        updateWorkflowState();
    };

    statusEl.textContent = 'Generating workout-combo routes…';
    const wind = await getSessionWind();
    explorationWorker.postMessage({
        start: { lat: startLat, lon: startLon },
        end: null,
        distanceKm,
        mode: 'tiles',
        routeType: 'round_trip',
        shape: 'loop',
        coverageData,
        coverageDataSecondary: mode === 'both' ? coverageDataSecondary : null,
        optimizeFor,
        corridorConstraint: { coordinates: coords, maxDetourKm: 1.5 },
        windDirectionDeg: wind ? wind.windDirectionDeg : null,
        windSpeedKph: wind ? wind.windSpeedKph : null,
    });
}

function renderRoute(route, index) {
    const palette = _paletteFor(route.direction);
    const startPos = startMarker.getLatLng();
    const routeType = document.getElementById('route-type-select').value;
    const coords = [[startPos.lat, startPos.lng]];

    route.waypoints.forEach((wp, i) => {
        coords.push([wp.lat, wp.lon]);
        const marker = L.circleMarker([wp.lat, wp.lon], {
            radius: 6,
            color: palette.light,
            fillColor: palette.light,
            fillOpacity: 0.8,
        }).bindPopup(`${DIRECTION_LABELS[route.direction]} · Waypoint ${i + 1}`);
        waypointMarkers.addLayer(marker);
    });

    // For point-to-point close the preview at the end marker, not back to start.
    if (routeType === 'point_to_point' && endMarker) {
        const endPos = endMarker.getLatLng();
        coords.push([endPos.lat, endPos.lng]);
    } else {
        coords.push([startPos.lat, startPos.lng]);
    }

    const distanceLabel = window.formatDistance ? window.formatDistance(route.stats.distanceKm, 1) : `${route.stats.distanceKm.toFixed(1)} km`;
    const line = L.polyline(coords, {
        color: palette.light,
        weight: 3,
        dashArray: '8, 8',
        opacity: 0.8,
    }).bindPopup(`${routeDirLabel(route)} — ${distanceLabel}, ${newTilesLabel(route.stats)}`);
    line.on('click', (e) => { L.DomEvent.stopPropagation(e); highlightRoute(route.direction); });
    routeLayer.addLayer(line);
    addArrows(coords, palette.light);
    _phase1Polylines[route.direction] = line;
}

/** Direction label with an explicit shape tag (#489) so riders can see which
 *  shape a route actually got — loop and out-and-back both look like a
 *  "round trip" otherwise, with no way to tell them apart in the UI. */
function routeDirLabel(route) {
    const shapeTag = route.shape && SHAPE_LABELS[route.shape] && route.shape !== 'point_to_point'
        ? ` (${SHAPE_LABELS[route.shape]})` : '';
    return `${DIRECTION_LABELS[route.direction]}${shapeTag}`;
}

function newTilesLabel(stats) {
    if (stats.breakdown && stats.breakdown.length > 0) {
        return stats.breakdown.map(b => `${b.count} new ${b.label}`).join(' + ');
    }
    return `${stats.unvisited} new tiles`;
}

function addRouteListItem(route, index, targetDistanceKm, extraLabel = '') {
    const palette = _paletteFor(route.direction);
    const color = palette.base;
    const distanceLabel = window.formatDistance ? window.formatDistance(route.stats.distanceKm, 1) : `${route.stats.distanceKm.toFixed(1)} km`;
    const dir = route.direction;

    const badge = document.createElement('div');
    badge.className = 'route-badge flex-column align-items-start';
    badge.dataset.direction = dir;
    badge.style.gap = '4px';
    badge.innerHTML = `
        <div class="d-flex align-items-center gap-2 w-100">
            <span class="swatch"></span>
            <span class="route-label">${routeDirLabel(route)} · ${distanceLabel} · ${newTilesLabel(route.stats)}${extraLabel ? ' ' + extraLabel : ''}${route.windLabel ? ' · ' + route.windLabel : ''}</span>
            <button class="btn btn-xs btn-outline-primary ms-auto plot-road-btn" data-direction="${dir}"
                    aria-label="Plot road route for ${DIRECTION_LABELS[dir]}">
                <i class="bi bi-map" aria-hidden="true"></i> Plot road route
            </button>
        </div>
        <div class="route-phase2-info text-muted small d-none" data-direction="${dir}"></div>
    `;
    document.getElementById('route-list').appendChild(badge);
    badge.querySelector('.swatch').style.background = color;

    badge.addEventListener('click', (e) => {
        if (e.target.closest('.plot-road-btn')) return;
        highlightRoute(dir);
    });
    badge.querySelector('.plot-road-btn').addEventListener('click', () => {
        plotRoadRoute(dir, route, targetDistanceKm, color, badge);
    });
}

// ── Phase 2: Road routing ────────────────────────────────────────

/**
 * Displace a lat/lon point by `distKm` in the direction of `bearingDeg`.
 * Used to insert padding waypoints that force the router to travel farther.
 */
function displace(lat, lon, distKm, bearingDeg) {
    const R = 6371;
    const d = distKm / R;
    const b = bearingDeg * Math.PI / 180;
    const lat1 = lat * Math.PI / 180;
    const lon1 = lon * Math.PI / 180;
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b));
    const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
    return [lat2 * 180 / Math.PI, lon2 * 180 / Math.PI];
}

/**
 * Run one refinement loop targeting `targetKm`.
 * Returns the best result object, or null on failure.
 *
 * Strategy when too short: insert a displacement point pushed out along the
 * route's main bearing so the road router must travel farther out-and-back.
 * Strategy when too long: drop a padding waypoint first if one exists,
 * falling back to the furthest tile-claiming waypoint only when no padding
 * is left to sacrifice (#493 Phase B) — a purely distance-driven drop can
 * otherwise discard the exact corner waypoint a route claimed a tile
 * through while unrelated padding sits untouched.
 */
async function refineRoute(baseWaypoints, targetKm, surfacePref, candidateList, dirBearing, roadFilters = {}) {
    const TOLERANCE = 0.15;
    const MAX_ITERATIONS = 6;
    let waypoints = baseWaypoints.map(w => [...w]); // deep copy
    // Parallel to waypoints.slice(1, -1) (the inner/droppable waypoints):
    // true = tile-claiming corner from bestCornerPoint/candidates, false =
    // padding inserted purely to hit the distance target.
    let loadBearing = waypoints.slice(1, -1).map(() => true);
    let result = null;
    let candidates = candidateList.slice();

    // Build OSRM exclude list from road filter checkboxes (#411).
    const excludeClasses = [];
    if (roadFilters.noMotorways) excludeClasses.push('motorway', 'trunk');
    if (roadFilters.noUnpaved)   excludeClasses.push('ferry');   // OSRM doesn't natively exclude unpaved; handled via surface pref

    for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
        try {
            result = await api.getExplorationRoute({
                waypoints,
                surfacePreference: roadFilters.noUnpaved ? 'paved' : surfacePref,
                exclude: excludeClasses.length ? excludeClasses.join(',') : undefined,
            });
        } catch (err) {
            return null;
        }

        if (!result || result.status !== 'success') {
            // Surface over-restriction message (#411).
            if (result && result.status === 'no_route') return null;
            return null;
        }

        const ratio = result.distance_km / targetKm;
        if (Math.abs(ratio - 1) <= TOLERANCE) break; // within 15% — done

        if (ratio > 1 + TOLERANCE && waypoints.length > 3) {
            // Too long: drop a padding waypoint if one exists; only fall
            // back to the furthest load-bearing (tile-claiming) waypoint
            // once padding is exhausted.
            let dropIdx = loadBearing.indexOf(false);
            if (dropIdx === -1) dropIdx = loadBearing.length - 1; // furthest inner waypoint
            waypoints = [
                waypoints[0],
                ...waypoints.slice(1, 1 + dropIdx),
                ...waypoints.slice(2 + dropIdx, -1),
                waypoints[waypoints.length - 1],
            ];
            loadBearing = [...loadBearing.slice(0, dropIdx), ...loadBearing.slice(dropIdx + 1)];
        } else if (ratio < 1 - TOLERANCE) {
            // Too short: try adding next candidate zone first, then fall back
            // to pushing a displacement waypoint out along the route bearing.
            if (candidates.length > 0) {
                const next = candidates.shift();
                const wp = next.centroid || next;
                waypoints = [
                    waypoints[0],
                    ...waypoints.slice(1, -1),
                    [wp.lat, wp.lon],
                    waypoints[waypoints.length - 1],
                ];
                loadBearing.push(true); // new candidate corner claims a tile
            } else {
                // No more candidates — insert a padding point pushed out by
                // half the deficit distance along the main quadrant bearing.
                const deficitKm = (targetKm - result.distance_km) / 2;
                const start = waypoints[0];
                const padPt = displace(start[0], start[1], deficitKm, dirBearing);
                // Insert after start, before the existing inner waypoints.
                waypoints = [
                    waypoints[0],
                    padPt,
                    ...waypoints.slice(1),
                ];
                loadBearing.unshift(false); // pure padding, not tile-claiming
            }
        } else {
            break;
        }
    }

    return result;
}

/** Bearing (degrees) from the start toward the quadrant centre. */
const QUADRANT_BEARING = { NE: 45, SE: 135, SW: 225, NW: 315 };

/** Flatten a worker's newTilesByZoom into a flat [{x, y, zoom}] list (#493). */
function flattenNewTiles(newTilesByZoom) {
    const out = [];
    for (const { zoom, tiles } of newTilesByZoom || []) {
        for (const { x, y } of tiles) out.push({ x, y, zoom });
    }
    return out;
}

/**
 * Ask the backend which of the planned tiles a route's real coordinates
 * actually cross (#493), using the same exact tile-crossing math used to
 * score recorded activities. Returns null (not []) on failure so callers
 * can distinguish "verified, claims nothing" from "couldn't verify" and
 * fall back to leaving the Phase-1 preview alone rather than wrongly
 * clearing it because of a network hiccup.
 */
async function verifyClaimedTiles(coordinates, tiles) {
    if (!tiles.length) return [];
    try {
        const res = await api.verifyTileClaims({ coordinates, tiles });
        return (res && res.status === 'success') ? res.claimed : null;
    } catch (e) {
        return null;
    }
}

async function plotRoadRoute(direction, route, targetDistanceKm, color, badgeEl) {
    const plotBtn = badgeEl.querySelector('.plot-road-btn');
    const infoEl = badgeEl.querySelector('.route-phase2-info');

    plotBtn.disabled = true;
    plotBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Routing…';
    infoEl.textContent = 'Calling road routing service…';
    infoEl.classList.remove('d-none');

    const startPos = startMarker.getLatLng();
    const surfacePref = document.getElementById('surface-preference-select').value;
    const bearing = QUADRANT_BEARING[direction] || 45;

    // Collect road filter state (#411).
    const roadFilters = {
        noMotorways: document.getElementById('filter-no-motorways')?.checked || false,
        noUnpaved:   document.getElementById('filter-no-unpaved')?.checked   || false,
        avoidTraffic: document.getElementById('filter-avoid-traffic')?.checked || false,
    };

    const baseWaypoints = [
        [startPos.lat, startPos.lng],
        ...route.waypoints.map(wp => [wp.lat, wp.lon]),
        [startPos.lat, startPos.lng],
    ];

    const candidates = (_phase1Candidates[direction] || []).slice();
    const shortTarget = targetDistanceKm * 0.85;
    const longTarget  = targetDistanceKm * 1.15;

    // Run both variants in parallel.
    infoEl.textContent = 'Computing short and long variants…';
    const [shortResult, longResult] = await Promise.all([
        refineRoute(baseWaypoints, shortTarget,  surfacePref, candidates, bearing, roadFilters),
        refineRoute(baseWaypoints, longTarget,   surfacePref, candidates, bearing, roadFilters),
    ]);

    if (!shortResult && !longResult) {
        const errMsg = roadFilters.noMotorways || roadFilters.noUnpaved
            ? 'No route found with current road filters — try relaxing exclusions'
            : 'Road routing unavailable';
        if (typeof showToast === 'function') showToast(errMsg, 'warning');
        infoEl.textContent = errMsg;
        plotBtn.disabled = false;
        plotBtn.innerHTML = '<i class="bi bi-map" aria-hidden="true"></i> Plot road route';
        return;
    }

    // Remove old phase-1 dashed preview.
    if (_phase1Polylines[direction]) {
        routeLayer.removeLayer(_phase1Polylines[direction]);
        delete _phase1Polylines[direction];
    }
    if (_phase2Polylines[direction]) {
        routeLayer.removeLayer(_phase2Polylines[direction]);
        delete _phase2Polylines[direction];
    }

    // Render each variant on the map and build badge rows.
    let badgeRows = '';

    function renderVariant(result, label, opacity) {
        if (!result) return null;
        const latlngs = result.coordinates.map(([lat, lon]) => [lat, lon]);
        const line = L.polyline(latlngs, { color, weight: 4, opacity });
        const distLabel = window.formatDistance ? window.formatDistance(result.distance_km, 1) : `${result.distance_km} km`;
        line.bindPopup(`${DIRECTION_LABELS[direction]} ${label} — ${distLabel}, ${result.duration_min} min`);
        line.on('click', (e) => { L.DomEvent.stopPropagation(e); highlightRoute(direction); });
        routeLayer.addLayer(line);
        addArrows(latlngs, color);
        return { line, result, distLabel };
    }

    const short = renderVariant(shortResult, '(−)', 0.7);
    const long  = renderVariant(longResult,  '(+)', 1.0);

    // Store last (long preferred) as phase-2 ref for cleanup.
    _phase2Polylines[direction] = (long || short).line;

    // #493 — the Phase-1 green highlight is only a speculative claim (a
    // straight-line "corner" the router was aimed at, which may get snapped
    // to a road that never enters the tile, or dropped entirely while
    // refineRoute trims waypoints to hit the distance target). Re-check the
    // planned tiles against each variant's *actual* road-route coordinates
    // before trusting the claim.
    const plannedTiles = flattenNewTiles(route.newTilesByZoom);
    const [shortClaimed, longClaimed] = await Promise.all([
        short ? verifyClaimedTiles(shortResult.coordinates, plannedTiles) : Promise.resolve(null),
        long  ? verifyClaimedTiles(longResult.coordinates,  plannedTiles) : Promise.resolve(null),
    ]);
    const verified = shortClaimed !== null || longClaimed !== null;

    // Union of tiles either exportable variant genuinely reaches — replaces
    // the Phase-1 highlight for this direction with ground truth.
    const unionMap = new Map();
    for (const list of [shortClaimed, longClaimed]) {
        for (const t of list || []) unionMap.set(`${t.zoom}:${t.x},${t.y}`, t);
    }
    if (verified) {
        const byZoom = new Map();
        for (const t of unionMap.values()) {
            if (!byZoom.has(t.zoom)) byZoom.set(t.zoom, []);
            byZoom.get(t.zoom).push({ x: t.x, y: t.y });
        }
        renderNewTiles([...byZoom.entries()].map(([zoom, tiles]) => ({ zoom, tiles })), direction);
    }

    function variantRow(v, label, suffix, claimed) {
        if (!v) return '';
        const sb = v.result.surface_breakdown || {};
        const surfText = (sb.paved_pct != null)
            ? `${sb.paved_pct}% paved · ${sb.unpaved_pct}% unpaved · ${sb.unknown_pct}% unknown`
            : '';
        const tilesText = claimed == null ? '' : `· ${claimed.length} new tile${claimed.length === 1 ? '' : 's'}`;
        // #452: distinguish a route that efficiently covers new tiles both
        // ways from one where ORS genuinely found no alternate road for the
        // return leg — both look identical on the map/card otherwise.
        const outAndBackBadge = v.result.is_out_and_back
            ? '<span class="badge bg-secondary-subtle text-secondary-emphasis" title="No alternate road found nearby for the return leg">Out-and-back</span>'
            : '';
        const dataKey = `${direction}-${suffix}`;
        return `
            <div class="d-flex align-items-center gap-2 flex-wrap mt-4px">
                <span class="text-muted small">${label} ${v.distLabel} · ${v.result.duration_min} min
                    ${surfText ? `· ${surfText}` : ''} ${tilesText}</span>
                ${outAndBackBadge}
                <button class="btn btn-xs btn-outline-secondary export-gpx-btn ms-auto"
                        data-variant="${dataKey}"
                        aria-label="Export GPX ${label}">
                    <i class="bi bi-download" aria-hidden="true"></i> Export GPX
                </button>
            </div>`;
    }

    const labelEl = badgeEl.querySelector('.route-label');
    if (labelEl) {
        const parts = [];
        if (short) parts.push(`${short.distLabel} (−)`);
        if (long)  parts.push(`${long.distLabel} (+)`);
        const tilesSuffix = verified
            ? ` · ${unionMap.size} new tile${unionMap.size === 1 ? '' : 's'}${unionMap.size === 0 ? ' reached' : ''}`
            : '';
        labelEl.textContent = `${routeDirLabel(route)} · ${parts.join(' / ')}${tilesSuffix}`;
    }

    infoEl.innerHTML =
        variantRow(short, 'Short:', 'short', shortClaimed) +
        variantRow(long,  'Long:',  'long', longClaimed);
    infoEl.classList.remove('d-none');

    // Wire up GPX exports.
    infoEl.querySelectorAll('.export-gpx-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.dataset.variant;
            const coords = key.endsWith('-short')
                ? (shortResult && shortResult.coordinates)
                : (longResult  && longResult.coordinates);
            if (coords) downloadGpx(coords, direction);
        });
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
    if (!confirm('Clear cached coverage tile data? Coverage will be recomputed from your existing activity cache on next load.')) {
        return;
    }
    try {
        await api.invalidateCoverageCache();
        if (typeof showToast === 'function') showToast('Coverage cache cleared', 'info');
        loadCoverage();
    } catch (e) {
        if (typeof showToast === 'function') showToast('Failed to clear cache', 'error');
    }
}
