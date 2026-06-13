/**
 * setup.js - FTUE setup wizard logic (Issue #260)
 *
 * Controls the 4-step Strava credential setup wizard in setup.html.
 * Talks to /api/setup/* endpoints.
 */

(function () {
    'use strict';

    let currentStep = 1;
    const TOTAL_STEPS = 4;

    // ------------------------------------------------------------------
    // Step navigation
    // ------------------------------------------------------------------

    window.goToStep = function (step) {
        // Hide all panels
        document.querySelectorAll('.step-panel').forEach((el) => el.classList.remove('active'));
        // Show target
        const target = document.getElementById('step' + step);
        if (target) {
            target.classList.add('active');
            target.focus ? target.setAttribute('tabindex', '-1') : null;
        }
        // Update dots
        const dots = document.querySelectorAll('.step-dot');
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i + 1 === step);
            dot.classList.toggle('done', i + 1 < step);
        });
        // Update ARIA progressbar
        const indicator = document.getElementById('stepIndicator');
        if (indicator) {
            indicator.setAttribute('aria-valuenow', step);
        }

        currentStep = step;

        // Auto-trigger verify when arriving at step 3
        if (step === 3) {
            verifyCredentials();
        }
    };

    // ------------------------------------------------------------------
    // Toggle secret visibility
    // ------------------------------------------------------------------

    window.toggleSecret = function () {
        const input = document.getElementById('clientSecret');
        const icon = document.getElementById('toggleIcon');
        const btn = icon && icon.closest('button');
        if (!input) return;

        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        if (icon) {
            icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
        }
        if (btn) {
            btn.setAttribute('aria-pressed', String(isPassword));
            btn.setAttribute('aria-label', isPassword ? 'Hide Client Secret' : 'Show Client Secret');
        }
    };

    // ------------------------------------------------------------------
    // Form submission: save credentials then go to step 3
    // ------------------------------------------------------------------

    function initForm() {
        const form = document.getElementById('credentialsForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearErrors();

            const clientId = document.getElementById('clientId').value.trim();
            const clientSecret = document.getElementById('clientSecret').value.trim();

            // Client-side validation
            let valid = true;
            if (!clientId) {
                showFieldError('clientId', 'clientIdError', 'Client ID is required.');
                valid = false;
            } else if (!/^\d+$/.test(clientId)) {
                showFieldError('clientId', 'clientIdError', 'Client ID must contain only numbers.');
                valid = false;
            }
            if (!clientSecret) {
                showFieldError('clientSecret', 'clientSecretError', 'Client Secret is required.');
                valid = false;
            } else if (clientSecret.length < 8) {
                showFieldError('clientSecret', 'clientSecretError', 'Client Secret appears too short.');
                valid = false;
            }
            if (!valid) return;

            // Disable submit button while saving
            const saveBtn = document.getElementById('saveBtn');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving…';
            }

            try {
                const resp = await fetch('/api/setup/credentials', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
                });
                const data = await resp.json();
                if (data.success) {
                    goToStep(3);
                } else {
                    showSaveError(data.error || 'Failed to save credentials.');
                }
            } catch (err) {
                showSaveError('Network error — please try again.');
            } finally {
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = 'Save &amp; Verify <i class="bi bi-arrow-right ms-1" aria-hidden="true"></i>';
                }
            }
        });
    }

    // ------------------------------------------------------------------
    // Verify credentials via /api/setup/verify
    // ------------------------------------------------------------------

    async function verifyCredentials() {
        const spinner = document.getElementById('verifyingSpinner');
        const success = document.getElementById('verifySuccess');
        const fail = document.getElementById('verifyFail');
        const errorMsg = document.getElementById('verifyError');

        if (spinner) spinner.classList.remove('d-none');
        if (success) success.classList.add('d-none');
        if (fail) fail.classList.add('d-none');

        try {
            const resp = await fetch('/api/setup/verify', { method: 'POST' });
            const data = await resp.json();

            if (spinner) spinner.classList.add('d-none');

            if (data.valid) {
                if (success) success.classList.remove('d-none');
            } else {
                if (fail) fail.classList.remove('d-none');
                if (errorMsg) {
                    errorMsg.textContent = data.error || 'Credentials could not be verified.';
                }
            }
        } catch (err) {
            if (spinner) spinner.classList.add('d-none');
            if (fail) fail.classList.remove('d-none');
            if (errorMsg) errorMsg.textContent = 'Network error while verifying — please try again.';
        }
    }

    // ------------------------------------------------------------------
    // Error display helpers
    // ------------------------------------------------------------------

    function showFieldError(inputId, errorId, message) {
        const input = document.getElementById(inputId);
        const error = document.getElementById(errorId);
        if (input) input.classList.add('is-invalid');
        if (error) {
            error.textContent = message;
            error.classList.remove('d-none');
        }
    }

    function showSaveError(message) {
        const el = document.getElementById('saveError');
        if (el) {
            el.textContent = message;
            el.classList.remove('d-none');
        }
    }

    function clearErrors() {
        document.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
        document.querySelectorAll('.invalid-feedback').forEach((el) => {
            el.textContent = '';
            el.classList.add('d-none');
        });
        const saveError = document.getElementById('saveError');
        if (saveError) saveError.classList.add('d-none');
    }

    // ------------------------------------------------------------------
    // Check if already set up (OAuth callback lands here with ?connected=1)
    // ------------------------------------------------------------------

    function checkQueryParams() {
        const params = new URLSearchParams(window.location.search);
        if (params.get('connected') === '1') {
            goToStep(4);
        } else if (params.get('strava_error')) {
            // Returned from OAuth with error — land on step 3 with fail state
            goToStep(3);
            const fail = document.getElementById('verifyFail');
            const spinner = document.getElementById('verifyingSpinner');
            const errorMsg = document.getElementById('verifyError');
            if (spinner) spinner.classList.add('d-none');
            if (fail) fail.classList.remove('d-none');
            if (errorMsg) {
                errorMsg.textContent = 'Strava authorization failed: ' + params.get('strava_error').replace(/_/g, ' ');
            }
        }
    }

    // ------------------------------------------------------------------
    // Redirect the Strava OAuth callback back to setup success
    // ------------------------------------------------------------------

    function patchOAuthConnectLink() {
        const connectBtn = document.getElementById('connectBtn');
        if (connectBtn) {
            // Append a redirect hint so the callback page comes back here
            const url = new URL(connectBtn.href, window.location.origin);
            url.searchParams.set('setup_redirect', '1');
            connectBtn.href = url.toString();
        }
    }

    // ------------------------------------------------------------------
    // Init
    // ------------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', () => {
        initForm();
        checkQueryParams();
        patchOAuthConnectLink();
    });
})();
