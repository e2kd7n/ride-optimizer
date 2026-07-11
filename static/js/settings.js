/**
 * settings.js - Settings page: preferences, integrations (Strava/intervals.icu/ORS/Garmin/TrainerRoad), cache and analysis controls
 */

        // Canonical temperature (always stored/sent as Fahrenheit) + current display unit for the
        // outdoor-min-temp slider. See #375a.
        let _outdoorMinTempF = 40;
        let _isMetricTemp = false;

        function fToC(f) { return Math.round((f - 32) * 5 / 9); }
        function cToF(c) { return Math.round((c * 9 / 5) + 32); }

        function setOutdoorTempSliderUnit(isMetric) {
            const slider = document.getElementById('outdoor-min-temp');
            const label = document.getElementById('outdoor-min-temp-value');
            if (!slider || !label) return;
            _isMetricTemp = isMetric;
            if (isMetric) {
                slider.min = -20;
                slider.max = 30;
                slider.step = 5;
                const c = fToC(_outdoorMinTempF);
                slider.value = Math.min(Math.max(c, -20), 30);
                label.textContent = slider.value + '°C';
            } else {
                slider.min = 0;
                slider.max = 80;
                slider.step = 5;
                slider.value = Math.min(Math.max(_outdoorMinTempF, 0), 80);
                label.textContent = slider.value + '°F';
            }
        }

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            console.log('✓ Settings page initialized');

            // Load saved preferences
            loadUserPreferences();
            initThemeControl();

            // Setup event listeners
            setupEventListeners();
            bindGearAdminControls();
            setupDangerZoneToggle();

            // Load cache info and wire analysis button
            loadStravaStatus();
            loadIcuStatus();
            loadOrsStatus();
            initLocationCard();
            loadGarminStatus();
            loadTrainerRoadStatus();
            loadCacheInfo();
            setupFetchModeControls();
            document.getElementById('run-analysis-btn').addEventListener('click', runAnalysis);
            document.getElementById('fetch-btn').addEventListener('click', startFetch);

            // Restore progress UI if analysis or fetch is already running (e.g. after page reload)
            (async () => {
                try {
                    const job = await window.apiClient.getAnalysisStatus();
                    if (job.status === 'running') {
                        const btn = document.getElementById('run-analysis-btn');
                        const progressEl = document.getElementById('analysis-progress');
                        const spinnerEl = document.getElementById('analysis-spinner');
                        const statusEl = document.getElementById('analysis-status');
                        btn.disabled = true;
                        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Running…';
                        progressEl.style.display = '';
                        spinnerEl.style.display = '';
                        statusEl.textContent = job.label || 'Analysis in progress…';
                        pollAnalysisStatus();
                    }
                } catch (_) {}
            })();
            (async () => {
                try {
                    const job = await window.apiClient.fetch('/fetch/status');
                    if (job.status === 'running') {
                        const btn = document.getElementById('fetch-btn');
                        const progressEl = document.getElementById('fetch-progress');
                        const statusEl = document.getElementById('fetch-status');
                        btn.disabled = true;
                        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Fetching…';
                        progressEl.style.display = '';
                        statusEl.textContent = job.label || 'Fetch in progress…';
                        pollFetchStatus();
                    }
                } catch (_) {}
            })();

            // Handle OAuth redirect results
            const params = new URLSearchParams(window.location.search);
            if (params.get('strava_connected') === '1') {
                if (typeof showToast === 'function') showToast('Strava connected successfully!', 'success');
                history.replaceState({}, '', '/settings.html');
            } else if (params.get('strava_error')) {
                if (typeof showToast === 'function') showToast('Strava connection failed: ' + params.get('strava_error'), 'error');
                history.replaceState({}, '', '/settings.html');
            }

            // Setup form validation
            setupFormValidation();
        });

        function setupFormValidation() {
            const form = document.getElementById('settings-form');
            if (form) {
                form.addEventListener('submit', function(e) {
                    e.preventDefault();

                    // Validate form
                    if (form.checkValidity()) {
                        saveSettings();
                    } else {
                        form.classList.add('was-validated');
                        if (typeof showToast === 'function') {
                            showToast('Please fill in all required fields', 'error');
                        }
                    }
                });
            }
        }

        // Toggle collapse state + aria on a card-header-btn/collapse pair based on connected state
        function setCardExpanded(toggleId, bodyId, expand) {
            const toggleBtn = document.getElementById(toggleId);
            const bodyEl = document.getElementById(bodyId);
            if (!toggleBtn || !bodyEl || typeof bootstrap === 'undefined') return;
            const collapse = bootstrap.Collapse.getOrCreateInstance(bodyEl, { toggle: false });
            if (expand) {
                collapse.show();
            } else {
                collapse.hide();
            }
        }

        function setupDangerZoneToggle() {
            const toggleBtn = document.getElementById('danger-zone-toggle');
            const bodyEl = document.getElementById('danger-zone-body');
            if (!toggleBtn || !bodyEl) return;
            const label = toggleBtn.querySelector('.danger-zone-toggle-label');
            bodyEl.addEventListener('shown.bs.collapse', () => {
                if (label) label.textContent = 'Hide Danger Zone';
            });
            bodyEl.addEventListener('hidden.bs.collapse', () => {
                if (label) label.textContent = 'Show Danger Zone';
            });
        }

        // Appearance select mirrors the current data-theme (set on every page load via the
        // inline head script) and applies changes immediately — it's not gated on auto-save.
        function initThemeControl() {
            const select = document.getElementById('theme-preference');
            if (!select || !window.getFairWeatherTheme) return;
            select.value = window.getFairWeatherTheme();
            select.addEventListener('change', function() {
                window.setFairWeatherTheme(this.value);
            });
        }

        function applySettingsToForm(settings) {
            if (settings.unit_system || settings.unitSystem) {
                document.getElementById('unit-system').value = settings.unit_system || settings.unitSystem;
            }
            if (settings.default_view || settings.defaultView) {
                document.getElementById('default-view').value = settings.default_view || settings.defaultView;
            }
            if (settings.show_weather_details !== undefined || settings.showWeatherDetails !== undefined) {
                document.getElementById('show-weather-details').checked =
                    settings.show_weather_details !== undefined ? settings.show_weather_details : settings.showWeatherDetails;
            }
            if (settings.show_elevation !== undefined || settings.showElevation !== undefined) {
                document.getElementById('show-elevation').checked =
                    settings.show_elevation !== undefined ? settings.show_elevation : settings.showElevation;
            }
            if (settings.auto_save !== undefined || settings.autoSave !== undefined) {
                document.getElementById('auto-save').checked =
                    settings.auto_save !== undefined ? settings.auto_save : settings.autoSave;
            }

            // Outdoor workout preferences — canonical value always stored/sent in Fahrenheit;
            // only the displayed slider converts to Celsius when unit_system is metric (#375a).
            if (settings.outdoor_min_temp_f !== undefined) {
                _outdoorMinTempF = settings.outdoor_min_temp_f;
            }
            if (settings.outdoor_allow_rain !== undefined) {
                document.getElementById('outdoor-allow-rain').checked = settings.outdoor_allow_rain;
            }
            const unitSystem = document.getElementById('unit-system').value;
            setOutdoorTempSliderUnit(unitSystem === 'metric');
        }

        async function loadUserPreferences() {
            // Try server first, fall back to localStorage
            try {
                const res = await window.apiClient.fetch('/settings');
                if (res.status === 'success' && res.settings) {
                    applySettingsToForm(res.settings);
                    return;
                }
            } catch (_) {
                // Server unavailable — fall back to localStorage
            }
            const local = JSON.parse(localStorage.getItem('rideOptimizerSettings') || '{}');
            applySettingsToForm(local);
        }

        function setupEventListeners() {
            // Settings reset button (save is handled by form submit)
            document.getElementById('reset-settings').addEventListener('click', resetSettings);

            // Outdoor temp slider live display (unit-aware — #375a)
            const tempSlider = document.getElementById('outdoor-min-temp');
            const tempLabel = document.getElementById('outdoor-min-temp-value');
            if (tempSlider && tempLabel) {
                tempSlider.addEventListener('input', function() {
                    const val = Number(this.value);
                    if (_isMetricTemp) {
                        _outdoorMinTempF = cToF(val);
                        tempLabel.textContent = val + '°C';
                    } else {
                        _outdoorMinTempF = val;
                        tempLabel.textContent = val + '°F';
                    }
                });
            }

            // Keep the outdoor temp slider's display unit in sync if the user changes Unit System
            // before saving.
            const unitSelect = document.getElementById('unit-system');
            if (unitSelect) {
                unitSelect.addEventListener('change', function() {
                    setOutdoorTempSliderUnit(this.value === 'metric');
                });
            }

            // Export buttons
            document.getElementById('export-preferences').addEventListener('click', exportPreferences);
            document.getElementById('export-favorites').addEventListener('click', exportFavorites);

            // Clear buttons
            document.getElementById('clear-favorites').addEventListener('click', clearFavorites);
            document.getElementById('clear-all-data').addEventListener('click', clearAllData);

            // Auto-save on settings change
            const settingsInputs = document.querySelectorAll('input, select');
            settingsInputs.forEach(input => {
                input.addEventListener('change', function() {
                    if (document.getElementById('auto-save').checked) {
                        markUnsavedChanges();
                        // Debounced auto-save
                        clearTimeout(window.autoSaveTimeout);
                        window.autoSaveTimeout = setTimeout(saveSettings, 500);
                    } else {
                        markUnsavedChanges();
                    }
                });
            });
        }

        function markUnsavedChanges() {
            document.getElementById('unsaved-indicator').style.display = 'inline';
        }

        function clearUnsavedChanges() {
            document.getElementById('unsaved-indicator').style.display = 'none';
        }

        async function saveSettings() {
            const serverPayload = {
                unit_system: document.getElementById('unit-system').value,
                default_view: document.getElementById('default-view').value,
                show_weather_details: document.getElementById('show-weather-details').checked,
                show_elevation: document.getElementById('show-elevation').checked,
                auto_save: document.getElementById('auto-save').checked,
                outdoor_min_temp_f: _outdoorMinTempF,
                outdoor_allow_rain: document.getElementById('outdoor-allow-rain').checked,
            };

            // Always update localStorage as offline fallback
            const localPayload = {
                unitSystem: serverPayload.unit_system,
                defaultView: serverPayload.default_view,
                showWeatherDetails: serverPayload.show_weather_details,
                showElevation: serverPayload.show_elevation,
                autoSave: serverPayload.auto_save,
                savedAt: new Date().toISOString()
            };
            localStorage.setItem('rideOptimizerSettings', JSON.stringify(localPayload));

            // Persist to server
            try {
                await window.apiClient.fetch('/settings', {
                    method: 'PUT',
                    body: JSON.stringify(serverPayload),
                });
            } catch (_) {
                // Server save failed — localStorage still has the data
            }

            clearUnsavedChanges();

            const saveBtn = document.getElementById('save-settings');
            if (saveBtn) {
                const original = saveBtn.innerHTML;
                saveBtn.innerHTML = '<i class="bi bi-check-circle" aria-hidden="true"></i> Save Complete';
                setTimeout(() => { saveBtn.innerHTML = original; }, 2000);
            }
        }

        async function resetSettings() {
            if (confirm('Are you sure you want to reset all settings to defaults?')) {
                localStorage.removeItem('rideOptimizerSettings');

                // Reset on server
                try {
                    await window.apiClient.fetch('/settings', { method: 'DELETE' });
                } catch (_) {
                    // Server reset failed — local is already cleared
                }

                // Reset form to defaults
                document.getElementById('unit-system').value = 'imperial';
                document.getElementById('default-view').value = 'home';
                document.getElementById('show-weather-details').checked = true;
                document.getElementById('show-elevation').checked = true;
                document.getElementById('auto-save').checked = true;
                _outdoorMinTempF = 40;
                setOutdoorTempSliderUnit(false);
                document.getElementById('outdoor-allow-rain').checked = false;

                localStorage.removeItem('fairWeatherTheme');
                const systemTheme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'night' : 'day';
                window.setFairWeatherTheme(systemTheme);
                document.getElementById('theme-preference').value = systemTheme;

                clearUnsavedChanges();

                if (typeof showToast === 'function') {
                    showToast('Settings reset to defaults', 'info');
                } else {
                    alert('Settings reset to defaults');
                }
            }
        }

        function exportPreferences() {
            const settings = JSON.parse(localStorage.getItem('rideOptimizerSettings') || '{}');
            const dataStr = JSON.stringify(settings, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);

            const link = document.createElement('a');
            link.href = url;
            link.download = `ride-optimizer-preferences-${new Date().toISOString().split('T')[0]}.json`;
            link.click();

            URL.revokeObjectURL(url);

            if (typeof showToast === 'function') {
                showToast('Preferences exported successfully!', 'success');
            }
        }

        function exportFavorites() {
            const favorites = JSON.parse(localStorage.getItem('favoriteRoutes') || '[]');
            const dataStr = JSON.stringify(favorites, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);

            const link = document.createElement('a');
            link.href = url;
            link.download = `ride-optimizer-favorites-${new Date().toISOString().split('T')[0]}.json`;
            link.click();

            URL.revokeObjectURL(url);

            if (typeof showToast === 'function') {
                showToast('Favorites exported successfully!', 'success');
            }
        }

        function clearFavorites() {
            if (confirm('Are you sure you want to clear all favorites? This cannot be undone.')) {
                localStorage.removeItem('favoriteRoutes');

                if (typeof showToast === 'function') {
                    showToast('Favorites cleared', 'warning');
                } else {
                    alert('Favorites cleared');
                }
            }
        }

        function clearAllData() {
            if (confirm('Are you sure you want to clear ALL local data? This includes settings, favorites, and hidden routes. This cannot be undone.')) {
                if (confirm('This is your last chance. Are you absolutely sure?')) {
                    localStorage.clear();

                    if (typeof showToast === 'function') {
                        showToast('All local data cleared', 'warning');
                    } else {
                        alert('All local data cleared');
                    }

                    // Reload page after delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
            }
        }

        let _cacheEarliestDate = null;
        let _cacheLatestDate = null;
        let _currentFetchPreset = 'latest';

        function updateRunBtnLabel() {
            const btn = document.getElementById('run-analysis-btn');
            if (btn.disabled) return;
            btn.innerHTML = '<span class="step-badge">Step 2:</span> <i class="bi bi-play-fill" aria-hidden="true"></i> Run Analysis';
            btn.onclick = null;
        }

        function setupFetchModeControls() {
            document.querySelectorAll('.fetch-preset').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.fetch-preset').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    _currentFetchPreset = this.dataset.preset;
                    const isCustom = _currentFetchPreset === 'custom';
                    document.getElementById('custom-date-fields').style.display = isCustom ? '' : 'none';
                    const customBtn = document.querySelector('.fetch-preset[data-preset="custom"]');
                    if (customBtn) customBtn.setAttribute('aria-expanded', isCustom ? 'true' : 'false');
                    updateDatePresetHint();
                });
            });
        }

        function getPresetAfterDate(preset) {
            const earliest = _cacheEarliestDate ? new Date(_cacheEarliestDate) : null;
            const today = new Date();
            if (preset === '1yr') {
                const base = earliest || today;
                return new Date(base.getFullYear() - 1, base.getMonth(), base.getDate());
            }
            if (preset === '2yr') {
                const base = earliest || today;
                return new Date(base.getFullYear() - 2, base.getMonth(), base.getDate());
            }
            if (preset === 'alltime') return new Date('2009-01-01');
            return null;
        }

        function updateSmartPresetLabels() {
            const earliest = _cacheEarliestDate ? new Date(_cacheEarliestDate) : null;
            const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
            const btn1yr = document.getElementById('preset-1yr');
            const btn2yr = document.getElementById('preset-2yr');
            if (btn1yr) {
                const d = getPresetAfterDate('1yr');
                btn1yr.textContent = earliest ? `+1 year (back to ${fmt(d)})` : `Past year (from ${fmt(d)})`;
            }
            if (btn2yr) {
                const d = getPresetAfterDate('2yr');
                btn2yr.textContent = earliest ? `+2 years (back to ${fmt(d)})` : `Past 2 years (from ${fmt(d)})`;
            }
            updateDatePresetHint();
        }

        function updateDatePresetHint() {
            const hint = document.getElementById('date-preset-hint');
            if (!hint) return;
            const preset = _currentFetchPreset;
            const earliest = _cacheEarliestDate ? new Date(_cacheEarliestDate) : null;
            const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
            let msg = '';
            switch (preset) {
                case 'latest':
                    msg = _cacheLatestDate
                        ? `Fetches activities newer than your most recent cached ride (${fmt(new Date(_cacheLatestDate))}).`
                        : 'Cache is empty — fetches your most recent 300 activities.';
                    break;
                case '1yr':
                case '2yr': {
                    const from = getPresetAfterDate(preset);
                    msg = `Fetches activities from ${fmt(from)} to today.`;
                    if (earliest) {
                        if (earliest <= from) {
                            msg += ' Your cache already covers this range.';
                        } else {
                            const months = Math.round((earliest - from) / (30.5 * 24 * 3600 * 1000));
                            msg += ` Extends your history back ~${months} month${months !== 1 ? 's' : ''}.`;
                        }
                    }
                    break;
                }
                case 'alltime':
                    msg = earliest
                        ? `Fetches all activities back to 2009, extending your cache by ~${Math.round((earliest - new Date('2009-01-01')) / (365.25 * 24 * 3600 * 1000))} more years. May take several minutes.`
                        : 'Fetches all your Strava activities since 2009. May take several minutes.';
                    break;
                case 'custom':
                    msg = 'Specify exact start and end dates. Leave "To" blank to fetch up to today.';
                    break;
            }
            hint.textContent = msg;
        }

        async function loadIcuStatus() {
            const statusEl = document.getElementById('icu-connection-status');
            const athleteInput = document.getElementById('icu-athlete-id');
            const keyInput = document.getElementById('icu-api-key');
            const disconnectBtn = document.getElementById('icu-disconnect-btn');
            try {
                const s = await window.apiClient.fetch('/intervals/status');
                if (s.connected) {
                    statusEl.innerHTML = `<span class="badge bg-success"><i class="bi bi-check-circle"></i> intervals.icu connected</span> <span class="text-muted small">${s.athlete_name || s.athlete_id}</span>`;
                    athleteInput.value = s.athlete_id || '';
                    athleteInput.placeholder = s.athlete_id || 'e.g. i12345';
                    disconnectBtn.style.display = '';
                } else {
                    statusEl.innerHTML = '<span class="badge bg-secondary"><i class="bi bi-x-circle"></i> Not connected</span>';
                    disconnectBtn.style.display = 'none';
                }
                setCardExpanded('icu-card-toggle', 'icu-card-body', !!s.connected);
            } catch (e) {
                statusEl.innerHTML = '<span class="text-muted small">Not configured</span>';
                disconnectBtn.style.display = 'none';
                setCardExpanded('icu-card-toggle', 'icu-card-body', false);
            }

            disconnectBtn.addEventListener('click', async () => {
                if (!confirm('Disconnect intervals.icu? This will remove your saved credentials.')) return;
                try {
                    await window.apiClient.fetch('/intervals/disconnect', { method: 'POST' });
                    if (typeof showToast === 'function') showToast('intervals.icu disconnected', 'info');
                    athleteInput.value = '';
                    await loadIcuStatus();
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Failed to disconnect intervals.icu', 'error');
                }
            }, { once: true });

            document.getElementById('icu-connect-btn').addEventListener('click', async () => {
                const btn = document.getElementById('icu-connect-btn');
                const feedback = document.getElementById('icu-connect-feedback');
                const athleteId = athleteInput.value.trim();
                const apiKey = keyInput.value.trim();

                if (!athleteId || !apiKey) {
                    feedback.style.display = '';
                    feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Both Athlete ID and API Key are required.</span>';
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Connecting…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.fetch('/intervals/connect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ athlete_id: athleteId, api_key: apiKey })
                    });
                    if (res.success) {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle"></i> Connected as <strong>${res.athlete_name || athleteId}</strong>.</span>`;
                        keyInput.value = '';
                        await loadIcuStatus();
                        if (typeof showToast === 'function') showToast('intervals.icu connected!', 'success');
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${res.error || 'Connection failed'}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${e.message || 'Connection failed'}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-link-45deg"></i> Connect';
                }
            });
        }

        // ── OpenRouteService ─────────────────────────────────────

        async function loadOrsStatus() {
            const statusEl = document.getElementById('ors-connection-status');
            const disconnectBtn = document.getElementById('ors-disconnect-btn');
            try {
                const s = await window.apiClient.fetch('/ors/status');
                if (s.configured) {
                    statusEl.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> ORS configured</span>';
                    disconnectBtn.style.display = '';
                } else {
                    statusEl.innerHTML = '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> Not configured</span>';
                    disconnectBtn.style.display = 'none';
                }
                setCardExpanded('ors-card-toggle', 'ors-card-body', !!s.configured);
            } catch (e) {
                statusEl.innerHTML = '<span class="text-muted small">Status unknown</span>';
                disconnectBtn.style.display = 'none';
                setCardExpanded('ors-card-toggle', 'ors-card-body', false);
            }

            disconnectBtn.addEventListener('click', async () => {
                if (!confirm('Remove ORS API key? Road routing on the Explore page will be unavailable until you add a new key.')) return;
                try {
                    await window.apiClient.fetch('/ors/disconnect', { method: 'POST' });
                    if (typeof showToast === 'function') showToast('ORS API key removed', 'info');
                    document.getElementById('ors-api-key').value = '';
                    await loadOrsStatus();
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Failed to remove ORS key', 'error');
                }
            }, { once: true });

            document.getElementById('ors-save-btn').addEventListener('click', async () => {
                const btn = document.getElementById('ors-save-btn');
                const feedback = document.getElementById('ors-save-feedback');
                const keyInput = document.getElementById('ors-api-key');
                const apiKey = keyInput.value.trim();

                if (!apiKey) {
                    feedback.style.display = '';
                    feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> API key is required.</span>';
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.fetch('/ors/connect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ api_key: apiKey })
                    });
                    if (res.success) {
                        feedback.style.display = '';
                        feedback.innerHTML = '<span class="text-success small"><i class="bi bi-check-circle"></i> API key saved. Road routing is now available on the Explore page.</span>';
                        keyInput.value = '';
                        await loadOrsStatus();
                        if (typeof showToast === 'function') showToast('ORS API key saved!', 'success');
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${res.error || 'Save failed'}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${e.message || 'Save failed'}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-floppy"></i> Save';
                }
            });
        }

        // ── Garmin Connect ──────────────────────────────────────

        async function loadGarminStatus() {
            const statusEl = document.getElementById('garmin-connection-status');
            const connectForm = document.getElementById('garmin-connect-form');
            const connectedState = document.getElementById('garmin-connected-state');
            let connected = false;
            try {
                const s = await window.apiClient.fetch('/garmin/status');
                connected = !!s.connected;
                if (s.connected) {
                    statusEl.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Garmin connected</span>';
                    const nameEl = document.getElementById('garmin-display-name');
                    if (nameEl && s.display_name) nameEl.textContent = s.display_name;
                    connectForm.style.display = 'none';
                    connectedState.style.display = '';
                } else {
                    statusEl.innerHTML = '<span class="badge bg-secondary"><i class="bi bi-x-circle"></i> Not connected</span>';
                    connectForm.style.display = '';
                    connectedState.style.display = 'none';
                }
            } catch (e) {
                statusEl.innerHTML = '<span class="text-muted small">Not configured</span>';
            }
            setCardExpanded('garmin-card-toggle', 'garmin-card-body', connected);

            document.getElementById('garmin-connect-btn').addEventListener('click', async () => {
                const btn = document.getElementById('garmin-connect-btn');
                const feedback = document.getElementById('garmin-connect-feedback');
                const email = document.getElementById('garmin-email').value.trim();
                const password = document.getElementById('garmin-password').value;

                if (!email || !password) {
                    feedback.style.display = '';
                    feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Email and password are required.</span>';
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Connecting…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.fetch('/garmin/connect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password })
                    });
                    if (res.success) {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle"></i> Connected as <strong>${window.escapeHtml(res.display_name || email)}</strong>.</span>`;
                        document.getElementById('garmin-password').value = '';
                        await loadGarminStatus();
                        if (typeof showToast === 'function') showToast('Garmin Connect connected!', 'success');
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(res.error || 'Connection failed')}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(e.message || 'Connection failed')}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-link-45deg"></i> Connect';
                }
            });

            document.getElementById('garmin-sync-btn').addEventListener('click', async () => {
                const btn = document.getElementById('garmin-sync-btn');
                const feedback = document.getElementById('garmin-sync-feedback');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.fetch('/garmin/sync', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ days: 90 })
                    });
                    if (res.success) {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle"></i> Synced ${res.fetched} activities (${res.new} new)</span>`;
                        if (typeof showToast === 'function') showToast(`Garmin sync complete: ${res.new} new activities`, 'success');
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(res.error || 'Sync failed')}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(e.message || 'Sync failed')}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sync Activities';
                }
            });

            document.getElementById('garmin-disconnect-btn').addEventListener('click', async () => {
                if (!confirm('Disconnect Garmin? This will remove your saved credentials.')) return;
                try {
                    await window.apiClient.fetch('/garmin/disconnect', { method: 'POST' });
                    if (typeof showToast === 'function') showToast('Garmin disconnected', 'info');
                    await loadGarminStatus();
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Failed to disconnect', 'error');
                }
            });
        }

        // ── TrainerRoad ─────────────────────────────────────────

        const TR_TYPE_BADGES = {
            'Endurance':  'bg-info text-dark',
            'Tempo':      'bg-primary-subtle text-primary',
            'Threshold':  'bg-warning-subtle text-dark',
            'VO2Max':     'bg-danger-subtle text-danger',
            'Sprint':     'bg-danger-subtle text-danger',
            'Anaerobic':  'bg-danger-subtle text-danger',
            'Recovery':   'bg-success-subtle text-success',
        };

        async function loadTrainerRoadStatus() {
            const statusBadge = document.getElementById('tr-status-badge');
            const connectForm = document.getElementById('tr-connect-form');
            const connectedState = document.getElementById('tr-connected-state');
            const requiresNote = document.getElementById('outdoor-prefs-requires-note');
            let connected = false;

            try {
                const s = await window.apiClient.getTrainerRoadStatus();
                connected = !!s.connected;
                if (s.connected) {
                    statusBadge.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Connected</span>';
                    connectForm.style.display = 'none';
                    connectedState.style.display = '';

                    if (s.last_sync) {
                        const hours = Math.round((Date.now() - new Date(s.last_sync)) / 3600000);
                        const syncEl = document.getElementById('tr-sync-time');
                        if (hours > 24) {
                            syncEl.innerHTML = `<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> Last sync: ${hours}h ago</span>`;
                        } else {
                            syncEl.innerHTML = `<i class="bi bi-clock"></i> Last sync: ${hours}h ago`;
                        }
                    }

                    loadTrainerRoadWorkouts();
                } else {
                    statusBadge.innerHTML = '<span class="badge bg-secondary">Not connected</span>';
                    connectForm.style.display = '';
                    connectedState.style.display = 'none';
                }
            } catch (e) {
                statusBadge.innerHTML = '<span class="text-muted small">Not configured</span>';
            }
            setCardExpanded('tr-card-toggle', 'tr-card-body', connected);
            if (requiresNote) requiresNote.style.display = connected ? 'none' : '';

            // Connect button
            document.getElementById('tr-connect-btn').addEventListener('click', async () => {
                const btn = document.getElementById('tr-connect-btn');
                const feedback = document.getElementById('tr-connect-feedback');
                const urlInput = document.getElementById('tr-feed-url');
                const feedUrl = urlInput.value.trim();

                if (!feedUrl) {
                    feedback.style.display = '';
                    feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Feed URL is required.</span>';
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Connecting…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.connectTrainerRoad(feedUrl);
                    if (res.success) {
                        if (typeof showToast === 'function') showToast(`TrainerRoad connected! ${res.workouts_synced} workouts synced.`, 'success');
                        await loadTrainerRoadStatus();
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${res.error || 'Connection failed'}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${e.message || 'Connection failed'}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-link-45deg"></i> Connect';
                }
            });

            // Sync button
            document.getElementById('tr-sync-btn').addEventListener('click', async () => {
                const btn = document.getElementById('tr-sync-btn');
                const feedback = document.getElementById('tr-sync-feedback');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing…';
                feedback.style.display = 'none';

                try {
                    const res = await window.apiClient.syncTrainerRoad();
                    if (res.success) {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle"></i> Synced ${res.workouts_synced} workouts (${res.created} new, ${res.updated} updated)</span>`;
                        await loadTrainerRoadStatus();
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-x-circle"></i> Sync failed</span>';
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${e.message || 'Sync failed'}</span>`;
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sync Now';
                }
            });

            // Disconnect button
            document.getElementById('tr-disconnect-btn').addEventListener('click', async () => {
                if (!confirm('Disconnect TrainerRoad? This will remove your feed URL and cached workouts.')) return;
                try {
                    await window.apiClient.disconnectTrainerRoad();
                    if (typeof showToast === 'function') showToast('TrainerRoad disconnected', 'info');
                    await loadTrainerRoadStatus();
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Failed to disconnect', 'error');
                }
            });
        }

        async function loadTrainerRoadWorkouts() {
            const container = document.getElementById('tr-workouts-table');
            try {
                const data = await window.apiClient.getTrainerRoadWorkouts();
                const workouts = data.workouts || [];
                if (workouts.length === 0) {
                    container.innerHTML = '<p class="small text-muted mb-0">No workouts scheduled in the next 7 days.</p>';
                    return;
                }
                const esc = window.escapeHtml;
                const rows = workouts.map(w => {
                    const d = new Date(w.workout_date + 'T00:00:00');
                    const day = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
                    const badgeClass = TR_TYPE_BADGES[w.workout_type] || 'bg-secondary';
                    return `<tr>
                        <td class="fw-semibold">${esc(day)}</td>
                        <td>${esc(w.workout_name || '—')}</td>
                        <td><span class="badge ${badgeClass}">${esc(w.workout_type || '—')}</span></td>
                        <td>${w.duration_minutes ? w.duration_minutes + ' min' : '—'}</td>
                        <td class="d-none d-md-table-cell">${w.tss || '—'}</td>
                    </tr>`;
                }).join('');
                container.innerHTML = `
                    <table class="table table-sm table-borderless mb-0">
                        <thead><tr class="small text-muted">
                            <th>Date</th><th>Name</th><th>Type</th><th>Duration</th><th class="d-none d-md-table-cell">TSS</th>
                        </tr></thead>
                        <tbody>${rows}</tbody>
                    </table>`;
            } catch (e) {
                container.innerHTML = '<p class="small text-warning mb-0">Could not load workouts.</p>';
            }
        }

        async function loadStravaStatus() {
            const statusEl = document.getElementById('strava-connection-status');
            const connectBtn = document.getElementById('strava-connect-btn');
            const disconnectBtn = document.getElementById('strava-disconnect-btn');
            let connected = false;
            try {
                const s = await window.apiClient.getStravaStatus();
                connected = !!s.connected;
                if (s.connected) {
                    const exp = new Date(s.expires_at * 1000).toLocaleDateString();
                    statusEl.innerHTML = `<span class="badge bg-success"><i class="bi bi-check-circle"></i> Strava connected</span> <span class="text-muted small">token expires ${exp}</span>`;
                    connectBtn.style.display = 'none';
                    disconnectBtn.style.display = '';
                } else {
                    const reason = s.reason === 'token_expired' ? 'token expired' : 'not connected';
                    statusEl.innerHTML = `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Strava ${reason}</span>`;
                    connectBtn.style.display = '';
                    disconnectBtn.style.display = 'none';
                }
            } catch (e) {
                statusEl.innerHTML = '<span class="text-warning small"><i class="bi bi-exclamation-triangle"></i> Could not check Strava status</span>';
            }
            setCardExpanded('strava-card-toggle', 'strava-card-body', connected);

            disconnectBtn.addEventListener('click', async () => {
                if (!confirm('Disconnect Strava? This will remove your saved credentials and you will need to re-authenticate.')) return;
                try {
                    await window.apiClient.fetch('/strava/disconnect', { method: 'POST' });
                    if (typeof showToast === 'function') showToast('Strava disconnected', 'info');
                    await loadStravaStatus();
                } catch (e) {
                    if (typeof showToast === 'function') showToast('Failed to disconnect Strava', 'error');
                }
            }, { once: true });
        }

        async function loadCacheInfo() {
            const el = document.getElementById('cache-info');
            try {
                const info = await window.apiClient.getCacheInfo();
                if (info.status === 'no_cache') {
                    _cacheEarliestDate = null;
                    _cacheLatestDate = null;
                    el.innerHTML = '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> No local cache</span> <span class="text-muted small">No activities downloaded yet — use "Fetch Activities" to populate.</span>';
                    updateSmartPresetLabels();
                    return;
                }
                _cacheEarliestDate = info.date_earliest || null;
                _cacheLatestDate = info.date_latest || null;
                updateSmartPresetLabels();
                const fmt = (iso) => iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : '?';
                const ageText = info.cache_age_hours < 24
                    ? `${Math.round(info.cache_age_hours)}h ago`
                    : `${Math.round(info.cache_age_hours / 24)}d ago`;
                el.innerHTML = `
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-secondary"><i class="bi bi-activity"></i> ${info.activity_count.toLocaleString()} activities</span>
                        <span class="badge bg-secondary"><i class="bi bi-calendar-range"></i> ${fmt(info.date_earliest)} – ${fmt(info.date_latest)}</span>
                        <span class="badge bg-secondary"><i class="bi bi-clock"></i> Updated ${ageText}</span>
                        <span class="badge bg-secondary"><i class="bi bi-hdd"></i> ${info.cache_size_mb} MB</span>
                    </div>`;
            } catch (e) {
                el.innerHTML = '<span class="text-warning small"><i class="bi bi-exclamation-triangle"></i> Could not load cache info</span>';
            }
        }

        async function runAnalysis() {
            const btn = document.getElementById('run-analysis-btn');
            const progressEl = document.getElementById('analysis-progress');
            const spinnerEl = document.getElementById('analysis-spinner');
            const statusEl = document.getElementById('analysis-status');
            const previewMsg = document.getElementById('preview-ready-msg');

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Running…';
            progressEl.style.display = '';
            spinnerEl.style.display = '';
            previewMsg.style.display = 'none';
            previewMsg.dataset.shown = '';
            statusEl.textContent = 'Loading cached data…';

            try {
                await window.apiClient.triggerAnalysis({ fetchNew: false });
                pollAnalysisStatus();
            } catch (e) {
                btn.disabled = false;
                btn.innerHTML = '<span class="step-badge">Step 2:</span> <i class="bi bi-play-fill"></i> Run Analysis';
                progressEl.style.display = 'none';
                statusEl.textContent = 'Failed to start: ' + (e.message || 'Unknown error');
                if (typeof showToast === 'function') showToast('Failed to start analysis', 'error');
            }
        }

        function pollAnalysisStatus() {
            const btn = document.getElementById('run-analysis-btn');
            const progressEl = document.getElementById('analysis-progress');
            const spinnerEl = document.getElementById('analysis-spinner');
            const statusEl = document.getElementById('analysis-status');
            const progressBar = document.getElementById('analysis-progress-bar');
            const previewMsg = document.getElementById('preview-ready-msg');

            const phaseLabels = {
                starting: 'Starting…',
                loading: 'Loading cached activities…',
                fetching: 'Fetching activities from Strava…',
                processing_preview: 'Processing first activities for preview…',
                processing: 'Analyzing routes…',
                grouping: 'Grouping routes…',
            };

            const poll = setInterval(async () => {
                try {
                    const job = await window.apiClient.getAnalysisStatus();

                    // Update status text: prefer the server label, fall back to phase map
                    const label = job.label || phaseLabels[job.phase] || 'Running…';
                    statusEl.textContent = label;

                    // Real progress bar during grouping phase
                    if (job.phase === 'grouping' && job.routes_total > 0) {
                        const pct = Math.round((job.routes_done / job.routes_total) * 100);
                        progressBar.style.width = pct + '%';
                        progressBar.setAttribute('aria-valuenow', pct);
                        progressBar.style.animationDuration = '2s';

                    } else {
                        // Indeterminate for other phases
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', 100);

                        if (job.phase === 'fetching') {
                            progressBar.style.animationDuration = '0.75s';
                        } else {
                            progressBar.style.animationDuration = '2s';
                        }
                    }

                    // Show preview-ready link once (only when fetching from Strava)
                    if (job.preview_ready && !previewMsg.dataset.shown) {
                        previewMsg.style.display = '';
                        previewMsg.dataset.shown = '1';
                    }

                    if (job.status === 'done') {
                        clearInterval(poll);
                        spinnerEl.style.display = 'none';
                        progressBar.style.width = '100%';
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.style.animationDuration = '';
                        btn.disabled = false;
                        updateRunBtnLabel();
                        const r = job.result || {};
                        const acts = (r.activities_count || 0).toLocaleString();
                        const groups = r.route_groups_count || 0;
                        statusEl.textContent = `Done — ${acts} activities, ${groups} route group${groups !== 1 ? 's' : ''}`;
                        if (typeof showToast === 'function') showToast('Analysis complete', 'success');
                        loadCacheInfo();
                    } else if (job.status === 'stopped') {
                        clearInterval(poll);
                        spinnerEl.style.display = 'none';
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.style.animationDuration = '';
                        btn.disabled = false;
                        updateRunBtnLabel();
                        statusEl.textContent = 'Analysis stopped.';
                        if (typeof showToast === 'function') showToast('Analysis stopped', 'info');
                    } else if (job.status === 'error') {
                        clearInterval(poll);
                        spinnerEl.style.display = 'none';
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.classList.replace('bg-success', 'bg-danger');
                        btn.disabled = false;
                        updateRunBtnLabel();
                        const msg = (job.result || {}).message || 'Unknown error';
                        statusEl.textContent = 'Error: ' + msg;
                        if (typeof showToast === 'function') showToast('Analysis failed: ' + msg, 'error');
                    } else {
                        // Still running — show Stop button
                        btn.disabled = false;
                        btn.innerHTML = '<i class="bi bi-stop-fill" aria-hidden="true"></i> Stop';
                        btn.onclick = stopAnalysis;
                    }
                } catch (_) { /* network hiccup — keep polling */ }
            }, 3000);
        }

        async function stopAnalysis() {
            const btn = document.getElementById('run-analysis-btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Stopping…';
            try {
                await window.apiClient.fetch('/analyze/stop', { method: 'POST' });
            } catch (_) {}
        }

        async function startFetch() {
            const btn = document.getElementById('fetch-btn');
            const progressEl = document.getElementById('fetch-progress');
            const statusEl = document.getElementById('fetch-status');

            const preset = _currentFetchPreset;
            const isoDate = (d) => d.toISOString().slice(0, 10);
            let afterDate = null, beforeDate = null, limit = 1000;
            if (preset === 'latest') {
                if (_cacheLatestDate) {
                    // Incremental: only pull activities newer than the most recent cached one.
                    afterDate = _cacheLatestDate;
                } else {
                    // Empty cache: seed with a bounded initial pull instead of the full 1000 cap.
                    limit = 300;
                }
            } else {
                const d = getPresetAfterDate(preset);
                if (d) afterDate = isoDate(d);
                if (preset === 'custom') {
                    afterDate = document.getElementById('fetch-after').value || null;
                    beforeDate = document.getElementById('fetch-before').value || null;
                }
            }

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Fetching…';
            progressEl.style.display = '';
            statusEl.textContent = 'Connecting to Strava…';

            try {
                await window.apiClient.fetch('/fetch', {
                    method: 'POST',
                    body: JSON.stringify({ after_date: afterDate, before_date: beforeDate, limit }),
                });
                pollFetchStatus();
            } catch (e) {
                btn.disabled = false;
                btn.innerHTML = '<span class="step-badge">Step 1:</span> <i class="bi bi-cloud-download"></i> Fetch Activities';
                progressEl.style.display = 'none';
                if (typeof showToast === 'function') showToast('Failed to start fetch: ' + (e.message || 'Unknown error'), 'error');
            }
        }

        function pollFetchStatus() {
            const btn = document.getElementById('fetch-btn');
            const progressEl = document.getElementById('fetch-progress');
            const spinnerEl = document.getElementById('fetch-spinner');
            const statusEl = document.getElementById('fetch-status');

            const poll = setInterval(async () => {
                try {
                    const job = await window.apiClient.fetch('/fetch/status');
                    statusEl.textContent = job.label || 'Fetching…';

                    if (job.status === 'done') {
                        clearInterval(poll);
                        spinnerEl.style.display = 'none';
                        btn.disabled = false;
                        btn.innerHTML = '<span class="step-badge">Step 1:</span> <i class="bi bi-cloud-download"></i> Fetch Activities';
                        if (typeof showToast === 'function') showToast(job.label || 'Fetch complete', 'success');
                        loadCacheInfo();
                    } else if (job.status === 'error') {
                        clearInterval(poll);
                        spinnerEl.style.display = 'none';
                        btn.disabled = false;
                        btn.innerHTML = '<span class="step-badge">Step 1:</span> <i class="bi bi-cloud-download"></i> Fetch Activities';
                        statusEl.textContent = job.label || 'Fetch failed';
                        if (typeof showToast === 'function') showToast(job.label || 'Fetch failed', 'error');
                    }
                } catch (_) {}
            }, 3000);
        }

        // ── Gear admin (moved from Reports — #369b) ──────────────

        function bindGearAdminControls() {
            const syncBtn = document.getElementById('sync-gear-btn');
            const repairBtn = document.getElementById('repair-gear-btn');
            if (!syncBtn || !repairBtn) return;

            syncBtn.addEventListener('click', async () => {
                const feedback = document.getElementById('gear-admin-feedback');
                syncBtn.disabled = true;
                syncBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Syncing…';
                feedback.style.display = 'none';
                try {
                    const resp = await window.apiClient.fetch('/stats/refresh-gear', {
                        method: 'POST',
                        body: JSON.stringify({}),
                    });
                    if (resp.status === 'success') {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-success small"><i class="bi bi-check-circle"></i> ${window.escapeHtml(resp.message || 'Gear synced')}</span>`;
                        if (typeof showToast === 'function') showToast(resp.message || 'Gear synced', 'success');
                    } else {
                        feedback.style.display = '';
                        feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(resp.message || 'Sync failed')}</span>`;
                    }
                } catch (e) {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${window.escapeHtml(e.message || 'Sync failed')}</span>`;
                } finally {
                    syncBtn.disabled = false;
                    syncBtn.innerHTML = '<i class="bi bi-arrow-clockwise" aria-hidden="true"></i> Sync Gear';
                }
            });

            repairBtn.addEventListener('click', startGearRepair);
        }

        let _gearRepairPollInterval = null;

        async function startGearRepair() {
            const btn = document.getElementById('repair-gear-btn');
            const statusEl = document.getElementById('gear-cache-status-settings');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Repairing…';

            try {
                const resp = await window.apiClient.fetch('/stats/backfill-gear-ids', {
                    method: 'POST',
                    body: JSON.stringify({}),
                });
                if (resp.status === 'started' || resp.status === 'already_running') {
                    _gearRepairPollInterval = setInterval(pollGearRepair, 1500);
                } else {
                    if (typeof showToast === 'function') showToast(resp.message || 'Failed to start repair', 'error');
                    resetGearRepairBtn();
                }
            } catch (e) {
                if (typeof showToast === 'function') showToast(`Repair failed: ${e.message}`, 'error');
                resetGearRepairBtn();
            }
        }

        async function pollGearRepair() {
            const statusEl = document.getElementById('gear-cache-status-settings');
            try {
                const resp = await window.apiClient.fetch('/stats/backfill-gear-ids/status');
                if (resp.status === 'running') {
                    statusEl.textContent = resp.label || 'Repairing…';
                } else if (resp.status === 'done') {
                    clearInterval(_gearRepairPollInterval);
                    _gearRepairPollInterval = null;
                    if (typeof showToast === 'function') showToast(resp.label || 'Gear names repaired', 'success');
                    statusEl.textContent = '';
                    resetGearRepairBtn();
                } else if (resp.status === 'error') {
                    clearInterval(_gearRepairPollInterval);
                    _gearRepairPollInterval = null;
                    if (typeof showToast === 'function') showToast(resp.label || 'Repair error', 'error');
                    statusEl.textContent = '';
                    resetGearRepairBtn();
                }
            } catch (e) {
                // ignore transient poll errors
            }
        }

        function resetGearRepairBtn() {
            const btn = document.getElementById('repair-gear-btn');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-patch-check" aria-hidden="true"></i> Repair Gear Names';
        }

        // ── Home & Work Location (#472) ─────────────────────────

        let _locationMap = null;
        let _locationHomeMarker = null;
        let _locationWorkMarker = null;

        function _workPinIcon() {
            // Same coral-red pin used for the exploration end marker (explore.js) —
            // a functional map-data color, not a brand accent.
            return L.divIcon({
                className: '',
                html: '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">' +
                      '<path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0z" fill="#C4483A"/>' +
                      '<circle cx="12.5" cy="12.5" r="5" fill="#fff"/>' +
                      '</svg>',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
            });
        }

        function currentLocationTarget() {
            return document.getElementById('location-target-work').checked ? 'work' : 'home';
        }

        function initLocationMap() {
            const mapEl = document.getElementById('location-map');
            if (!mapEl || typeof L === 'undefined') return;
            _locationMap = L.map('location-map').setView([39.83, -98.58], 4);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 18,
            }).addTo(_locationMap);

            _locationMap.on('click', (e) => {
                setLocationPin(currentLocationTarget(), e.latlng.lat, e.latlng.lng);
            });

            // Leaflet can't size or fit-bounds itself correctly while its container is
            // inside a collapsed (display:none) card — defer both to when it becomes visible.
            const bodyEl = document.getElementById('location-card-body');
            if (bodyEl) {
                bodyEl.addEventListener('shown.bs.collapse', refitLocationMap);
            }
        }

        function refitLocationMap() {
            if (!_locationMap) return;
            _locationMap.invalidateSize();
            const pts = [];
            if (_locationHomeMarker) pts.push(_locationHomeMarker.getLatLng());
            if (_locationWorkMarker) pts.push(_locationWorkMarker.getLatLng());
            if (pts.length === 1) {
                _locationMap.setView(pts[0], 12);
            } else if (pts.length === 2) {
                _locationMap.fitBounds(pts, { padding: [40, 40] });
            }
        }

        function setLocationPin(target, lat, lon, label = null) {
            const display = label || `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
            if (target === 'home') {
                if (_locationHomeMarker) _locationMap.removeLayer(_locationHomeMarker);
                _locationHomeMarker = L.marker([lat, lon], { title: 'Home', alt: 'Home location' })
                    .addTo(_locationMap).bindPopup('Home');
                const el = document.getElementById('home-coords-display');
                el.textContent = display;
                el.classList.remove('text-muted');
            } else {
                if (_locationWorkMarker) _locationMap.removeLayer(_locationWorkMarker);
                _locationWorkMarker = L.marker([lat, lon], { title: 'Work', alt: 'Work location', icon: _workPinIcon() })
                    .addTo(_locationMap).bindPopup('Work');
                const el = document.getElementById('work-coords-display');
                el.textContent = display;
                el.classList.remove('text-muted');
            }
        }

        async function loadLocationStatus() {
            const statusEl = document.getElementById('location-status');
            let configured = false;
            try {
                const s = await window.apiClient.fetch('/location/status');
                configured = !!s.configured;
                statusEl.innerHTML = configured
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Configured</span>'
                    : '<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-triangle"></i> Not set</span>';

                if (s.home) setLocationPin('home', s.home.lat, s.home.lon);
                if (s.work) setLocationPin('work', s.work.lat, s.work.lon);
                refitLocationMap();
            } catch (e) {
                statusEl.innerHTML = '<span class="text-muted small">Status unknown</span>';
            }
            setCardExpanded('location-card-toggle', 'location-card-body', !configured);
        }

        async function searchLocationTarget() {
            const input = document.getElementById('location-search-input');
            const btn = document.getElementById('location-search-btn');
            const query = input.value.trim();
            if (!query) return;
            const target = currentLocationTarget();

            btn.disabled = true;
            try {
                const result = await window.apiClient.geocodeLocation(query);
                if (result.status !== 'success') {
                    if (typeof showToast === 'function') showToast(result.message || 'Location not found', 'warning');
                    return;
                }
                setLocationPin(target, result.lat, result.lon, result.short_name || result.display_name);
                if (_locationMap) _locationMap.setView([result.lat, result.lon], 13);
            } catch (e) {
                if (typeof showToast === 'function') showToast(e.message || 'Location search failed', 'error');
            } finally {
                btn.disabled = false;
            }
        }

        function useMyLocationForTarget() {
            const btn = document.getElementById('location-use-my-location-btn');
            if (!navigator.geolocation) {
                if (typeof showToast === 'function') showToast('Geolocation is not supported by this browser', 'warning');
                return;
            }
            const target = currentLocationTarget();
            btn.disabled = true;
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    setLocationPin(target, latitude, longitude);
                    if (_locationMap) _locationMap.setView([latitude, longitude], 13);
                    btn.disabled = false;
                },
                (err) => {
                    if (typeof showToast === 'function') showToast(err.message || 'Unable to determine your location', 'error');
                    btn.disabled = false;
                },
                { enableHighAccuracy: false, timeout: 10000 },
            );
        }

        async function saveLocations() {
            const btn = document.getElementById('location-save-btn');
            const feedback = document.getElementById('location-save-feedback');

            if (!_locationHomeMarker || !_locationWorkMarker) {
                feedback.style.display = '';
                feedback.innerHTML = '<span class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Set both a Home and a Work location before saving.</span>';
                return;
            }

            const home = _locationHomeMarker.getLatLng();
            const work = _locationWorkMarker.getLatLng();

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving…';
            feedback.style.display = 'none';

            try {
                const res = await window.apiClient.fetch('/location/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        home: { lat: home.lat, lon: home.lng },
                        work: { lat: work.lat, lon: work.lng },
                    }),
                });
                if (res.success) {
                    feedback.style.display = '';
                    if (res.warning) {
                        feedback.innerHTML = `<span class="text-warning small"><i class="bi bi-exclamation-triangle"></i> ${res.warning}</span>`;
                        if (typeof showToast === 'function') showToast(res.warning, 'warning');
                    } else {
                        feedback.innerHTML = '<span class="text-success small"><i class="bi bi-check-circle"></i> Locations saved.</span>';
                        if (typeof showToast === 'function') showToast('Home & work locations saved!', 'success');
                    }
                    await loadLocationStatus();
                } else {
                    feedback.style.display = '';
                    feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${res.error || 'Save failed'}</span>`;
                }
            } catch (e) {
                feedback.style.display = '';
                feedback.innerHTML = `<span class="text-danger small"><i class="bi bi-x-circle"></i> ${e.message || 'Save failed'}</span>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-floppy"></i> Save Locations';
            }
        }

        function updateLocationSearchPlaceholder() {
            const input = document.getElementById('location-search-input');
            const target = currentLocationTarget();
            input.placeholder = target === 'work' ? 'Search for work address' : 'Search for home address';
        }

        function initLocationCard() {
            initLocationMap();
            document.getElementById('location-search-btn').addEventListener('click', searchLocationTarget);
            document.getElementById('location-search-input').addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); searchLocationTarget(); }
            });
            document.getElementById('location-use-my-location-btn').addEventListener('click', useMyLocationForTarget);
            document.getElementById('location-save-btn').addEventListener('click', saveLocations);
            document.querySelectorAll('input[name="location-target"]').forEach((radio) => {
                radio.addEventListener('change', updateLocationSearchPlaceholder);
            });
            updateLocationSearchPlaceholder();
            loadLocationStatus();
        }
