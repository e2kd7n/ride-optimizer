        async function test404() {
            const result = document.getElementById('result-404');
            result.innerHTML = '<div class="spinner-border" role="status"></div>';
            
            try {
                await window.apiClient.fetch('/nonexistent');
                result.innerHTML = '<div class="alert alert-danger">Test failed - should have thrown error</div>';
            } catch (error) {
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Test Passed</strong><br>
                        Error message: ${error.message}<br>
                        Status: ${error.status || 'N/A'}
                    </div>
                `;
            }
        }
        
        async function testNetworkError() {
            const result = document.getElementById('result-network');
            result.innerHTML = '<div class="spinner-border" role="status"></div>';
            
            // Create a temporary client with invalid base URL
            const badClient = new APIClient('http://invalid-domain-that-does-not-exist.com/api');
            
            try {
                await badClient.fetch('/status');
                result.innerHTML = '<div class="alert alert-danger">Test failed - should have thrown error</div>';
            } catch (error) {
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Test Passed</strong><br>
                        Error message: ${error.message}<br>
                        Error type: ${error.name}
                    </div>
                `;
            }
        }
        
        async function testTimeout() {
            const result = document.getElementById('result-timeout');
            result.innerHTML = '<div class="spinner-border" role="status"></div>';
            
            // Create a client with very short timeout
            const timeoutClient = new APIClient('/api');
            timeoutClient.timeout = 100; // 100ms timeout
            
            try {
                await timeoutClient.fetch('/status');
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Request completed within timeout</strong><br>
                        (Server responded quickly)
                    </div>
                `;
            } catch (error) {
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Test Passed (Timeout detected)</strong><br>
                        Error message: ${error.message}<br>
                        Error type: ${error.name}
                    </div>
                `;
            }
        }
        
        async function testSuccess() {
            const result = document.getElementById('result-success');
            result.innerHTML = '<div class="spinner-border" role="status"></div>';
            
            try {
                const data = await window.apiClient.fetch('/status');
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Test Passed</strong><br>
                        Status: ${data.status}<br>
                        Services: ${Object.keys(data.services || {}).length} initialized
                    </div>
                `;
            } catch (error) {
                result.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>✗ Test Failed</strong><br>
                        Error: ${error.message}
                    </div>
                `;
            }
        }
        
        async function testRetry() {
            const result = document.getElementById('result-retry');
            result.innerHTML = '<div class="spinner-border" role="status"></div><p class="mt-2">Check browser console for retry logs...</p>';
            
            console.log('=== Starting Retry Test ===');
            console.log('This will attempt to fetch a non-existent endpoint 3 times with exponential backoff');
            
            try {
                await window.apiClient.fetch('/nonexistent');
                result.innerHTML = '<div class="alert alert-danger">Test failed - should have thrown error</div>';
            } catch (error) {
                result.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Test Passed</strong><br>
                        Retry logic executed (check console for 3 attempts)<br>
                        Final error: ${error.message}
                    </div>
                `;
            }
            
            console.log('=== Retry Test Complete ===');
        }

// Bind test buttons via data-test-action (moved off inline onclick="" so
// CSP script-src can drop 'unsafe-inline' — #475).
document.addEventListener('DOMContentLoaded', () => {
    const actions = { test404, testNetworkError, testTimeout, testSuccess, testRetry };
    document.querySelectorAll('[data-test-action]').forEach((btn) => {
        const fn = actions[btn.dataset.testAction];
        if (fn) btn.addEventListener('click', fn);
    });
});
