"""Tests for SecureTokenStorage's locking/atomic-write behavior.

Regression coverage for the settings-page auto-refresh race: GET
/api/strava/status runs on every settings.html page load and, if the
access token is expired, refreshes and overwrites config/credentials.json
as a side effect. Two concurrent refreshes (two open tabs, a page reload
mid-refresh) must not corrupt the file or lose the winning token pair.
"""
import threading

import pytest

from src.auth_secure import SecureTokenStorage


@pytest.fixture
def storage(tmp_path):
    return SecureTokenStorage(str(tmp_path / "credentials.json"))


class TestSecureTokenStorage:
    def test_save_and_load_roundtrip(self, storage):
        tokens = {'access_token': 'a', 'refresh_token': 'b', 'expires_at': 123}
        storage.save_tokens(tokens)
        assert storage.load_tokens() == tokens

    def test_load_missing_file_returns_none(self, storage):
        assert storage.load_tokens() is None

    def test_save_creates_sidecar_lock_file(self, storage):
        storage.save_tokens({'access_token': 'a'})
        lock_path = storage.credentials_path.parent / (storage.credentials_path.name + '.lock')
        assert lock_path.exists()

    def test_save_is_atomic_no_temp_file_left_behind(self, storage):
        storage.save_tokens({'access_token': 'a'})
        temp_path = storage.credentials_path.with_suffix('.tmp')
        assert not temp_path.exists()
        assert storage.credentials_path.exists()

    def test_concurrent_saves_never_corrupt_file(self, storage):
        """Hammer save_tokens from multiple threads; the file must always
        end up containing one complete, valid, decryptable token set —
        never a torn write or a lost update."""
        def _save(i):
            storage.save_tokens({'access_token': f'token-{i}', 'refresh_token': 'r', 'expires_at': i})

        threads = [threading.Thread(target=_save, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        result = storage.load_tokens()
        assert result is not None
        assert result['access_token'].startswith('token-')
