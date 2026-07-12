/**
 * reports.js — Ride statistics and gear reporting
 */

const api = new APIClient('/api');

let currentPeriod = 'this_year';
let currentGearId = null;   // null = all gear
let statsData = null;       // last /api/stats response
let gearData = null;        // last /api/stats/gear response
let gearMeta = {};          // gear_id -> gear object

// -----------------------------------------------------------------------
// Boot
// -----------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    bindPeriodButtons();
    bindGearControls();
    bindActivityFilters();
    loadStats();
    loadGear();
    initCalendar();
});

// -----------------------------------------------------------------------
// Period buttons
// -----------------------------------------------------------------------
function bindPeriodButtons() {
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            loadStats();
            loadActivities();
        });
    });
}

// -----------------------------------------------------------------------
// Stats loading
// -----------------------------------------------------------------------
async function loadStats() {
    setLoading(true);
    try {
        const resp = await api.get(`/stats?period=${currentPeriod}`);
        if (resp.status === 'no_data') {
            showNoData('No activities cached. Use Settings → Fetch Activities to sync from Strava.');
            return;
        }
        if (resp.status !== 'success') throw new Error(resp.message || 'Unknown error');
        statsData = resp.data;
        renderHeadlineStats(statsData.summary);
        renderRecords(statsData.records);
        renderTypeBreakdown(statsData.by_type);
        renderMonthlyChart(statsData.by_month);
        renderDistributionChart(statsData.speed_distribution, 'speed-chart', 'speed-chart-label', 'mph');
        renderDistributionChart(statsData.elevation_distribution, 'elevation-chart', 'elevation-chart-label', 'ft');
    } catch (e) {
        showToast(`Failed to load stats: ${e.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function renderHeadlineStats(s) {
    setText('stat-rides', fmt(s.total_rides));
    // Backend returns distance in miles (`_mi` fields). Label is dynamic per unit
    // preference (#375b) — the value must convert too, or a metric user sees a
    // "Kilometers" label on a number that's still in miles.
    const distUnit = typeof window.getDistanceUnit === 'function' ? window.getDistanceUnit() : 'mi';
    const toDisplayDistance = (mi) => (mi == null ? null : (distUnit === 'km' ? window.milesToKm(mi) : mi));
    setText('stat-distance', fmt(toDisplayDistance(s.total_distance_mi)));
    setText('stat-distance-label', distUnit === 'km' ? 'Kilometers' : 'Miles');
    setText('stat-time', fmt(s.total_time_h));
    setText('stat-elevation', fmtInt(s.total_elevation_ft));
    setText('stat-avg-distance', s.total_rides ? `avg ${fmt(toDisplayDistance(s.avg_distance_mi))} ${distUnit} / ride` : '');
    setText('stat-avg-speed', s.avg_speed_mph ? `avg ${fmt(s.avg_speed_mph)} mph` : '');
    setText('stat-avg-elevation', s.avg_elevation_ft ? `avg ${fmtInt(s.avg_elevation_ft)} ft / ride` : '');

    // Secondary stats (Avg HR / Kilojoules / Kudos): hide whichever are null/zero, and
    // reflow the remaining columns evenly rather than leaving a blank gap (#369a).
    const extras = [
        { col: 'stat-hr-col', has: !!s.avg_heartrate, render: () => setText('stat-hr', `${fmt(s.avg_heartrate)} bpm`) },
        { col: 'stat-kj-col', has: !!s.total_kilojoules, render: () => setText('stat-kj', fmtInt(s.total_kilojoules)) },
        { col: 'stat-kudos-col', has: !!s.total_kudos, render: () => setText('stat-kudos', fmt(s.total_kudos)) },
    ];
    const visible = extras.filter(e => e.has);
    const colClass = visible.length === 1 ? 'col-12' : visible.length === 2 ? 'col-6' : 'col-4';
    extras.forEach(e => {
        const col = document.getElementById(e.col);
        if (!col) return;
        if (e.has) {
            e.render();
            col.className = colClass;
            col.style.display = '';
        } else {
            col.style.display = 'none';
        }
    });
    const row = document.getElementById('extra-stats-row');
    if (row) row.style.display = visible.length ? '' : 'none';
}

// Personal Records are computed server-side, filtered to cycling sport types only (#376, #434) —
// so "Fastest Speed" can't surface a non-cycling session, and the record search isn't capped at
// the 1000-activity page-size limit /api/activities used to impose.
function renderRecords(r) {
    const qualifierEl = document.getElementById('records-qualifier');
    if (qualifierEl) qualifierEl.textContent = (r && Object.keys(r).length) ? '(cycling only)' : '';

    if (!r || !Object.keys(r).length) return;

    if (r.longest_ride) {
        setText('rec-longest', `${fmt(r.longest_ride.distance_mi)} mi`);
        setText('rec-longest-name', r.longest_ride.name);
        setText('rec-longest-date', r.longest_ride.date);
    }
    if (r.most_elevation) {
        setText('rec-elev', `${fmtInt(r.most_elevation.elevation_ft)} ft`);
        setText('rec-elev-name', r.most_elevation.name);
        setText('rec-elev-date', r.most_elevation.date);
    }
    if (r.fastest_speed) {
        setText('rec-speed', `${fmt(r.fastest_speed.speed_mph)} mph`);
        setText('rec-speed-name', r.fastest_speed.name);
        setText('rec-speed-date', r.fastest_speed.date);
    }
    if (r.most_kilojoules) {
        setText('rec-kj', `${fmtInt(r.most_kilojoules.kilojoules)} kJ`);
        setText('rec-kj-name', r.most_kilojoules.name);
        setText('rec-kj-date', r.most_kilojoules.date);
        document.getElementById('rec-kj-card').style.display = '';
    } else {
        document.getElementById('rec-kj-card').style.display = 'none';
    }
}

function renderTypeBreakdown(byType) {
    const el = document.getElementById('type-breakdown');
    if (!byType || !byType.length) { el.innerHTML = '<div class="text-muted small">No data</div>'; return; }

    const rows = byType.map(t => {
        const icon = sportIcon(t.sport_type);
        return `<div class="d-flex align-items-center justify-content-between py-1" style="border-bottom:1px solid var(--color-border);">
            <div class="d-flex align-items-center gap-2">
                <span style="font-size:14px;">${icon}</span>
                <span class="fw-medium" style="font-size:var(--font-size-sm);">${escapeHtml(t.sport_type)}</span>
            </div>
            <div class="d-flex gap-3 text-end">
                <span class="metric-pill"><strong>${fmt(t.total_rides)}</strong> rides</span>
                <span class="metric-pill"><strong>${fmt(t.total_distance_mi)}</strong> mi</span>
                <span class="metric-pill"><strong>${fmtInt(t.total_elevation_ft)}</strong> ft</span>
            </div>
        </div>`;
    }).join('');
    el.innerHTML = rows;
}

function renderMonthlyChart(byMonth) {
    const el = document.getElementById('monthly-chart');
    const labelEl = document.getElementById('monthly-chart-label');
    if (!byMonth || !byMonth.length) { el.innerHTML = '<div class="text-muted small">No data</div>'; return; }

    const maxDist = Math.max(...byMonth.map(m => m.total_distance_mi), 1);
    el.innerHTML = byMonth.map(m => {
        const h = Math.max(Math.round((m.total_distance_mi / maxDist) * 100), 2);
        const label = m.month;
        return `<div class="bar" style="height:${h}%;" title="${label}: ${fmt(m.total_distance_mi)} mi, ${fmt(m.total_rides)} rides" aria-label="${label}"></div>`;
    }).join('');

    // Show first and last month label
    const first = byMonth[0].month;
    const last = byMonth[byMonth.length - 1].month;
    labelEl.textContent = first === last ? first : `${first} – ${last}`;
}

function renderDistributionChart(data, chartId, labelId, unit) {
    const el = document.getElementById(chartId);
    const labelEl = document.getElementById(labelId);
    if (!data || !data.length) { el.innerHTML = '<div class="text-muted small">No data</div>'; return; }

    const maxCount = Math.max(...data.map(b => b.count), 1);
    el.innerHTML = data.map(b => {
        const h = Math.max(Math.round((b.count / maxCount) * 100), 2);
        return `<div class="bar" style="height:${h}%;" title="${b.label} ${unit}: ${b.count} rides" aria-label="${b.label} ${unit}"></div>`;
    }).join('');

    const first = data[0].label;
    const last = data[data.length - 1].label;
    labelEl.textContent = `${first} – ${last} ${unit}`;
}

// -----------------------------------------------------------------------
// Gear
// -----------------------------------------------------------------------
async function loadGear() {
    try {
        const resp = await api.get('/stats/gear');
        if (resp.status !== 'success') return;
        gearData = resp.data;

        // Build lookup
        gearMeta = {};
        for (const g of gearData.gear) gearMeta[g.id] = g;

        renderGearCards(gearData);
        // Load activities after gear so we can show gear names
        loadActivities();
    } catch (e) {
        showToast(`Failed to load gear: ${e.message}`, 'warning');
        loadActivities(); // still load activities without gear
    }
}

function gearDisplayName(g) {
    if (g.name && g.name !== g.id) return g.name;
    const typeLabel = g.type === 'bike' ? 'Bike' : g.type === 'shoe' ? 'Shoes' : 'Gear';
    return `${typeLabel} (${g.id.slice(-4)})`;
}

function renderGearCards(data) {
    const container = document.getElementById('gear-cards');
    const statusEl = document.getElementById('gear-cache-status');
    statusEl.textContent = data.gear_cache_available ? '' : 'No gear names — sync gear from Settings → Strava';

    if (!data.gear.length && !data.unassigned.total_rides) {
        container.innerHTML = '<div class="text-muted small">No gear data. Re-fetch activities from Strava after syncing gear.</div>';
        return;
    }

    const cards = data.gear.map(g => {
        const typeIcon = g.type === 'bike' ? '🚲' : g.type === 'shoe' ? '👟' : '⚙️';
        const primary = g.primary ? '<span class="badge bg-success ms-1" style="font-size:9px;">Primary</span>' : '';
        const lastUsed = g.last_used ? `Last used ${g.last_used}` : '';
        const displayName = gearDisplayName(g);
        return `<div class="col-12 col-md-6">
            <div class="card gear-card p-2" data-gear-id="${escapeHtml(g.id)}" role="button"
                 tabindex="0" aria-label="Filter by ${escapeHtml(displayName)}">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span style="font-size:14px;">${typeIcon}</span>
                        <span class="gear-name ms-1">${escapeHtml(displayName)}</span>${primary}
                    </div>
                </div>
                <div class="gear-meta">${escapeHtml(g.brand_name || '')} ${escapeHtml(g.model_name || '')} ${escapeHtml(lastUsed)}</div>
                <div class="gear-stats">
                    <div class="gear-stat"><span class="gear-stat-value">${fmt(g.total_rides)}</span><span class="gear-stat-label">rides</span></div>
                    <div class="gear-stat"><span class="gear-stat-value">${fmt(g.total_distance_mi)}</span><span class="gear-stat-label">mi</span></div>
                    <div class="gear-stat"><span class="gear-stat-value">${fmtInt(g.total_elevation_ft)}</span><span class="gear-stat-label">ft</span></div>
                    <div class="gear-stat"><span class="gear-stat-value">${fmt(g.total_time_h)}</span><span class="gear-stat-label">hrs</span></div>
                </div>
            </div>
        </div>`;
    }).join('');

    // Unassigned row if any
    const u = data.unassigned;
    const unassignedCard = u.total_rides ? `<div class="col-12 col-md-6">
        <div class="card gear-card p-2" data-gear-id="__unassigned__" role="button" tabindex="0" aria-label="Filter unassigned rides">
            <div class="gear-name text-muted">⚙️ No Gear Assigned</div>
            <div class="gear-stats">
                <div class="gear-stat"><span class="gear-stat-value">${fmt(u.total_rides)}</span><span class="gear-stat-label">rides</span></div>
                <div class="gear-stat"><span class="gear-stat-value">${fmt(u.total_distance_mi)}</span><span class="gear-stat-label">mi</span></div>
            </div>
        </div>
    </div>` : '';

    container.innerHTML = cards + unassignedCard;

    // Bind click handlers
    container.querySelectorAll('.gear-card').forEach(card => {
        card.addEventListener('click', () => selectGear(card.dataset.gearId));
        card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') selectGear(card.dataset.gearId); });
    });
}

function selectGear(gearId) {
    const cards = document.querySelectorAll('.gear-card');
    const clearBtn = document.getElementById('clear-gear-filter-btn');

    if (currentGearId === gearId) {
        // Deselect
        currentGearId = null;
        cards.forEach(c => c.classList.remove('active'));
        clearBtn.style.display = 'none';
    } else {
        currentGearId = gearId;
        cards.forEach(c => c.classList.toggle('active', c.dataset.gearId === gearId));
        clearBtn.style.display = '';
    }
    loadActivities();
}

function bindGearControls() {
    // Sync Gear / Repair Gear Names now live in Settings → Strava (#369b) — only the
    // Clear Filter control remains here, and only shown while a gear filter is active.
    document.getElementById('clear-gear-filter-btn').addEventListener('click', () => {
        currentGearId = null;
        document.querySelectorAll('.gear-card').forEach(c => c.classList.remove('active'));
        document.getElementById('clear-gear-filter-btn').style.display = 'none';
        loadActivities();
    });
}

// -----------------------------------------------------------------------
// Activity list
// -----------------------------------------------------------------------
function bindActivityFilters() {
    document.getElementById('activity-type-filter').addEventListener('change', loadActivities);
    document.getElementById('activity-sort').addEventListener('change', loadActivities);
}

async function loadActivities() {
    const sportType = document.getElementById('activity-type-filter').value;
    const sort = document.getElementById('activity-sort').value;

    let url = `/activities?period=${currentPeriod}&sort=${sort}&limit=200`;
    if (currentGearId && currentGearId !== '__unassigned__') url += `&gear_id=${encodeURIComponent(currentGearId)}`;
    if (sportType) url += `&sport_type=${encodeURIComponent(sportType)}`;

    const tbody = document.getElementById('activity-table-body');
    const footer = document.getElementById('activity-table-footer');
    const title = document.getElementById('activity-list-title');
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted small ps-2">Loading…</td></tr>';

    try {
        const resp = await api.get(url);
        if (resp.status !== 'success') throw new Error(resp.message || 'Error');

        const { activities, total } = resp.data;

        // Filter unassigned client-side (API doesn't support gear_id=null filter)
        const list = currentGearId === '__unassigned__'
            ? activities.filter(a => !a.gear_id)
            : activities;

        // Gear name for title
        let gearLabel = '';
        if (currentGearId && currentGearId !== '__unassigned__') {
            const g = gearMeta[currentGearId];
            gearLabel = g ? `— ${gearDisplayName(g)}` : `— ${currentGearId}`;
        } else if (currentGearId === '__unassigned__') {
            gearLabel = '— No Gear Assigned';
        }
        title.textContent = gearLabel;

        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-muted small ps-2">No activities</td></tr>';
            footer.textContent = '';
            return;
        }

        tbody.innerHTML = list.map(a => {
            const gearObj = a.gear_id && gearMeta[a.gear_id] ? gearMeta[a.gear_id] : null;
            const rawName = a.gear_name || (gearObj ? gearObj.name : '');
            const gearName = (rawName && rawName !== a.gear_id) ? rawName : (gearObj ? gearDisplayName(gearObj) : '');
            const gearType = a.gear_type || (gearObj ? gearObj.type : '');
            const gearIcon = gearType === 'bike' ? '🚲' : gearType === 'shoe' ? '👟' : gearType ? '⚙️' : '';
            const gearLabel = gearName ? `${gearIcon} ${escapeHtml(gearName)}` : '';
            const hrCell = a.average_heartrate ? `${Math.round(a.average_heartrate)}` : '—';
            const typeBadge = typeBadgeHtml(a.sport_type);
            return `<tr class="activity-row">
                <td class="ps-2">
                    <div class="activity-name" title="${escapeHtml(a.name)}">${escapeHtml(a.name)}</div>
                    <div style="font-size:10px; color:var(--color-text-muted);">${a.date} ${typeBadge} ${gearLabel ? '· ' + gearLabel : ''}</div>
                </td>
                <td class="text-end">${fmt(a.distance_mi)}</td>
                <td class="text-end">${fmtTime(a.time_h)}</td>
                <td class="text-end">${fmtInt(a.elevation_ft)}</td>
                <td class="text-end">${fmt(a.speed_mph)}</td>
                <td class="text-end pe-2">${hrCell}</td>
            </tr>`;
        }).join('');

        const shown = list.length;
        footer.textContent = shown < total
            ? `Showing ${shown} of ${total} activities`
            : `${total} ${total === 1 ? 'activity' : 'activities'}`;
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-danger small ps-2">Error: ${escapeHtml(e.message)}</td></tr>`;
        footer.textContent = '';
    }
}

// -----------------------------------------------------------------------
// Calendar (#485) — per-day activity counts + Strava backfill for a
// specific month, so gaps left by the 500-most-recent fetch cap (#486)
// can be filled in by date range instead of only "fetch newest."
// -----------------------------------------------------------------------
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
const DOW_NAMES = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth() + 1; // 1-12

function initCalendar() {
    const monthSel = document.getElementById('cal-month');
    monthSel.innerHTML = MONTH_NAMES.map((m, i) => `<option value="${i + 1}">${m}</option>`).join('');

    const yearSel = document.getElementById('cal-year');
    const nowYear = new Date().getFullYear();
    const years = [];
    for (let y = nowYear + 1; y >= 2000; y--) years.push(y);
    yearSel.innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');

    monthSel.value = String(calMonth);
    yearSel.value = String(calYear);

    monthSel.addEventListener('change', () => { calMonth = parseInt(monthSel.value, 10); loadCalendar(); });
    yearSel.addEventListener('change', () => { calYear = parseInt(yearSel.value, 10); loadCalendar(); });

    document.getElementById('cal-prev').addEventListener('click', () => shiftCalendar(-1));
    document.getElementById('cal-next').addEventListener('click', () => shiftCalendar(1));
    document.getElementById('cal-backfill-btn').addEventListener('click', backfillCurrentMonth);

    loadCalendar();
}

function shiftCalendar(delta) {
    calMonth += delta;
    if (calMonth > 12) { calMonth = 1; calYear++; }
    if (calMonth < 1) { calMonth = 12; calYear--; }
    document.getElementById('cal-month').value = String(calMonth);
    document.getElementById('cal-year').value = String(calYear);
    loadCalendar();
}

async function loadCalendar() {
    const grid = document.getElementById('cal-grid');
    const summaryEl = document.getElementById('cal-summary');
    grid.innerHTML = '<div class="text-muted small">Loading…</div>';
    summaryEl.textContent = '';

    try {
        const resp = await api.get(`/stats/calendar?year=${calYear}&month=${calMonth}`);
        if (resp.status !== 'success') throw new Error(resp.message || 'Error');
        renderCalendar(resp.data);
    } catch (e) {
        grid.innerHTML = `<div class="text-danger small">Error: ${escapeHtml(e.message)}</div>`;
    }
}

function renderCalendar(data) {
    const grid = document.getElementById('cal-grid');
    const summaryEl = document.getElementById('cal-summary');
    const { days, month_summary: s } = data;

    const firstDow = new Date(data.year, data.month - 1, 1).getDay(); // 0=Sun
    const todayIso = new Date().toISOString().slice(0, 10);
    const maxCount = Math.max(...days.map(d => d.count), 1);

    let html = DOW_NAMES.map(d => `<div class="cal-dow">${d}</div>`).join('');
    for (let i = 0; i < firstDow; i++) html += '<div class="cal-day cal-day-empty"></div>';

    html += days.map(d => {
        const dayNum = parseInt(d.date.slice(-2), 10);
        const isToday = d.date === todayIso;
        const cls = ['cal-day'];
        if (isToday) cls.push('cal-today');
        let style = '';
        let title = `${d.date}: no activities`;
        if (d.count > 0) {
            cls.push('cal-has-activity');
            const opacity = 0.35 + 0.65 * (d.count / maxCount);
            style = `style="background-color:var(--color-primary); opacity:${opacity.toFixed(2)};"`;
            title = `${d.date}: ${d.count} ${d.count === 1 ? 'ride' : 'rides'}, ${fmt(d.distance_mi)} mi`;
        }
        return `<div class="${cls.join(' ')}" ${style} title="${escapeHtml(title)}">
            <span>${dayNum}</span>${d.count > 0 ? `<span class="cal-day-count">${d.count}</span>` : ''}
        </div>`;
    }).join('');

    grid.innerHTML = html;

    if (s.total_rides > 0) {
        summaryEl.textContent = `${s.total_rides} ${s.total_rides === 1 ? 'ride' : 'rides'} · ${fmt(s.total_distance_mi)} mi · ${fmtInt(s.total_elevation_ft)} ft this month`;
    } else {
        summaryEl.textContent = 'No activities cached for this month — use "Backfill this month" if you expect rides here.';
    }
}

async function backfillCurrentMonth() {
    const btn = document.getElementById('cal-backfill-btn');
    const statusEl = document.getElementById('cal-backfill-status');
    const daysInMonth = new Date(calYear, calMonth, 0).getDate();
    const afterDate = `${calYear}-${String(calMonth).padStart(2, '0')}-01`;
    const beforeDate = `${calYear}-${String(calMonth).padStart(2, '0')}-${String(daysInMonth).padStart(2, '0')}`;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Requesting…';
    statusEl.classList.remove('d-none');
    statusEl.textContent = 'Connecting to Strava…';

    try {
        await api.post('/fetch', { after_date: afterDate, before_date: beforeDate, limit: 1000 });
        pollCalendarBackfillStatus();
    } catch (e) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-cloud-download"></i> Backfill this month';
        const msg = e && e.status === 409
            ? 'Another fetch is already running — try again shortly.'
            : ((e && e.message) || 'Failed to start backfill');
        statusEl.textContent = msg;
        if (typeof showToast === 'function') showToast(msg, 'error');
    }
}

function pollCalendarBackfillStatus() {
    const btn = document.getElementById('cal-backfill-btn');
    const statusEl = document.getElementById('cal-backfill-status');

    const poll = setInterval(async () => {
        try {
            const job = await api.get('/fetch/status');
            statusEl.textContent = job.label || 'Fetching…';

            if (job.status === 'done' || job.status === 'error') {
                clearInterval(poll);
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-cloud-download"></i> Backfill this month';
                if (typeof showToast === 'function') {
                    showToast(job.label || (job.status === 'done' ? 'Backfill complete' : 'Backfill failed'),
                        job.status === 'done' ? 'success' : 'error');
                }
                if (job.status === 'done') {
                    loadCalendar();
                    loadStats();
                    loadActivities();
                }
            }
        } catch (_) { /* network hiccup — keep polling */ }
    }, 3000);
}

// -----------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------
function setLoading(on) {
    document.getElementById('loading-indicator').classList.toggle('d-none', !on);
}

function showNoData(msg) {
    document.getElementById('stat-rides').textContent = '—';
    document.getElementById('stat-distance').textContent = '—';
    document.getElementById('stat-time').textContent = '—';
    document.getElementById('stat-elevation').textContent = '—';
    showToast(msg, 'warning', { duration: 0 });
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
}

function fmt(n) {
    if (n == null) return '—';
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function fmtInt(n) {
    if (n == null) return '—';
    return Math.round(n).toLocaleString();
}

function fmtTime(hours) {
    if (hours == null) return '—';
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function sportIcon(type) {
    const icons = {
        'Ride': '🚴', 'GravelRide': '🪨', 'EBikeRide': '⚡', 'VirtualRide': '💻',
        'Run': '🏃', 'Walk': '🚶', 'Hike': '🥾', 'Swim': '🏊',
        'WeightTraining': '🏋️', 'Yoga': '🧘',
    };
    return icons[type] || '🏅';
}

function typeBadgeHtml(type) {
    const colors = {
        'Ride': 'primary', 'GravelRide': 'warning', 'EBikeRide': 'success',
        'VirtualRide': 'secondary', 'Run': 'info',
    };
    const cls = colors[type] || 'light';
    return `<span class="badge bg-${cls} type-badge">${escapeHtml(type || '')}</span>`;
}
