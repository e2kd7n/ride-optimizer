"""
Regression tests for CSRF enforcement (GHSA-x9vc-vwqr-c33q).

`/api/csrf-token` and `CSRFProtect(app)` existed but nothing actually
enforced the token: `WTF_CSRF_CHECK_DEFAULT` was hardcoded to False, which
skips Flask-WTF's automatic before_request check entirely, and no view
called `csrf.protect()` manually. These tests exercise the real app factory
(not the `TESTING`-patched shared singleton other integration tests use) so
the enforcement gap can't silently regress.
"""

import pytest

from app.factory import create_app


@pytest.fixture
def prod_like_client():
    """A fresh app instance with TESTING left at its default (False)."""
    app = create_app()
    with app.test_client() as client:
        yield client


@pytest.mark.integration
def test_mutating_request_without_csrf_token_is_rejected(prod_like_client):
    resp = prod_like_client.put('/api/settings', json={'foo': 'bar'})
    assert resp.status_code == 400


@pytest.mark.integration
def test_mutating_request_with_valid_csrf_token_is_accepted(prod_like_client):
    token = prod_like_client.get('/api/csrf-token').get_json()['csrf_token']
    resp = prod_like_client.put(
        '/api/settings', json={'foo': 'bar'}, headers={'X-CSRFToken': token}
    )
    assert resp.status_code == 200


@pytest.mark.integration
def test_mutating_request_with_bogus_csrf_token_is_rejected(prod_like_client):
    resp = prod_like_client.put(
        '/api/settings', json={'foo': 'bar'}, headers={'X-CSRFToken': 'not-a-real-token'}
    )
    assert resp.status_code == 400


@pytest.mark.integration
def test_get_request_does_not_require_csrf_token(prod_like_client):
    resp = prod_like_client.get('/api/settings')
    assert resp.status_code != 400


@pytest.mark.integration
def test_csrf_rejection_returns_json_not_html(prod_like_client):
    """Flask-WTF's default CSRFError handler returns a plain HTML error
    page, not JSON — api-client.js's fetch() wrapper calls response.json()
    on every non-ok response and silently swallows the resulting parse
    failure, so the real reason (e.g. "The CSRF session token is missing.")
    never reached the user or the console; they just saw the generic
    "Invalid request. Please check your input." fallback. The registered
    CSRFError handler must return the app's standard JSON error shape."""
    resp = prod_like_client.put('/api/settings', json={'foo': 'bar'})
    assert resp.status_code == 400
    assert resp.content_type.startswith('application/json')
    data = resp.get_json()
    assert data['status'] == 'error'
    assert 'CSRF' in data['message']


@pytest.mark.integration
def test_csrf_token_endpoint_is_not_cacheable(prod_like_client):
    """A cached /api/csrf-token response means the browser never actually
    revisits the server on a later fetch, so it can hand the client a
    token whose matching session cookie was never (re)written — producing
    "The CSRF session token is missing." with zero server-side trace."""
    resp = prod_like_client.get('/api/csrf-token')
    assert resp.headers.get('Cache-Control') == 'no-store'


@pytest.mark.integration
def test_csrf_enforcement_is_skipped_when_testing_flag_is_set(prod_like_client):
    """The TESTING flag (set by other test suites' shared-app fixtures) must
    still disable CSRF for convenience in tests, without weakening production."""
    prod_like_client.application.config['TESTING'] = True
    try:
        resp = prod_like_client.put('/api/settings', json={'foo': 'bar'})
        assert resp.status_code == 200
    finally:
        prod_like_client.application.config['TESTING'] = False
