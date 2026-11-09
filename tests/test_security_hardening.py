"""Regression tests for the 2026-11-08 security/robustness fixes."""
import threading

import pytest


@pytest.mark.unit
class TestWriteEnv:
    def test_concurrent_writers_keep_every_key(self, tmp_path, monkeypatch):
        """Unlocked read-modify-write used to drop keys (e.g. HOME_LATITUDE)."""
        from app.credentials import env_helpers
        target = tmp_path / 'runtime_overrides.env'
        monkeypatch.setattr(env_helpers, 'runtime_env_path', lambda: target)

        def writer(i):
            for j in range(20):
                env_helpers.write_env({f'KEY_{i}': str(j)})

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        parsed = env_helpers._parse_env_file(target)
        assert {f'KEY_{i}' for i in range(6)} <= set(parsed)
        assert all(parsed[f'KEY_{i}'] == '19' for i in range(6))
        # No temp files left behind.
        assert [p.name for p in tmp_path.iterdir()] == ['runtime_overrides.env']

    def test_updates_existing_key_and_strips_newlines(self, tmp_path, monkeypatch):
        from app.credentials import env_helpers
        target = tmp_path / 'runtime_overrides.env'
        target.write_text('# comment\nA=1\nB=2\n', encoding='utf-8')
        monkeypatch.setattr(env_helpers, 'runtime_env_path', lambda: target)
        env_helpers.write_env({'A': 'x\ny', 'C': '3'})
        text = target.read_text(encoding='utf-8')
        assert text == '# comment\nA=xy\nB=2\nC=3\n'


@pytest.mark.unit
class TestProxyFix:
    def test_client_ip_comes_from_the_proxy_header(self, client):
        """Behind Caddy every client was 127.0.0.1, so per-IP limits were global."""
        from flask import request
        from launch import app

        seen = {}

        @app.route('/__test_remote_addr')
        def _remote_addr():  # pragma: no cover - trivial
            seen['addr'] = request.remote_addr
            seen['secure'] = request.is_secure
            return 'ok'

        resp = client.get('/__test_remote_addr', headers={
            'X-Forwarded-For': '192.168.4.23', 'X-Forwarded-Proto': 'https'})
        assert resp.status_code == 200
        assert seen == {'addr': '192.168.4.23', 'secure': True}


@pytest.mark.unit
class TestCoordinateValidation:
    def test_validate_bbox_rejects_nan_and_out_of_range(self):
        from app.api.planner_bp import _validate_bbox
        nan = float('nan')
        assert _validate_bbox(nan, -87.7, 41.9, -87.6)
        assert _validate_bbox(41.8, -87.7, 41.9, float('inf'))
        assert _validate_bbox(95.0, -87.7, 95.1, -87.6)
        assert _validate_bbox(41.8, -87.7, 41.9, -87.6) is None

    def test_tiles_endpoint_rejects_nan_bbox(self, client):
        resp = client.get('/api/exploration/tiles?south=nan&west=-87.7&north=41.9&east=-87.6')
        assert resp.status_code == 400

    def test_lat_lon_pairs_reject_non_finite(self):
        from app.api.planner_bp import _parse_lat_lon_pairs
        assert _parse_lat_lon_pairs([[41.8, -87.6]]) == [(41.8, -87.6)]
        assert _parse_lat_lon_pairs([['nan', -87.6]]) is None
        assert _parse_lat_lon_pairs([[41.8, 200]]) is None
        assert _parse_lat_lon_pairs([[41.8]]) is None


@pytest.mark.unit
@pytest.mark.skipif(__import__('sys').platform == 'win32', reason='POSIX permission bits')
def test_garmin_tokens_are_owner_only(tmp_path):
    import os
    import stat
    from app.services.garmin_service import _secure_token_dir
    token_dir = tmp_path / '.garmin_tokens'
    token_dir.mkdir(mode=0o755)
    (token_dir / 'oauth1_token.json').write_text('{}')
    os.chmod(token_dir / 'oauth1_token.json', 0o644)
    _secure_token_dir(token_dir)
    assert stat.S_IMODE(token_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE((token_dir / 'oauth1_token.json').stat().st_mode) == 0o600


@pytest.mark.unit
class TestStravaCallback:
    def test_error_param_is_url_encoded(self, client):
        resp = client.get('/api/strava/callback?error=access_denied%26injected%3D1')
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert 'injected=1' not in location
        assert 'access_denied%26injected%3D1' in location
