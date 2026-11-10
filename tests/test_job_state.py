"""Tests for thread-safe job state (issue #458).

Covers the JobState/JobRegistry primitives in app/jobs/job_state.py and the
blueprint wiring that replaced the unsynchronized module-level dict globals
in data_bp.py and stats_bp.py.
"""

import threading
import types
from unittest.mock import Mock

import pytest

from app.jobs.job_state import JobRegistry, JobState


# ---------------------------------------------------------------------------
# JobState unit tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestJobState:
    def test_update_and_get(self):
        job = JobState()
        job.update(status='running', fetched=3)
        assert job.get('status') == 'running'
        assert job.get('fetched') == 3
        assert job.get('missing', 'default') == 'default'

    def test_snapshot_is_a_copy(self):
        job = JobState()
        job.update(status='running')
        snap = job.snapshot()
        snap['status'] = 'mutated'
        assert job.get('status') == 'running'

    def test_reset_replaces_state(self):
        job = JobState()
        job.update(status='done', result={'x': 1})
        job.reset({'status': 'idle'})
        assert job.snapshot() == {'status': 'idle'}

    def test_try_start_claims_idle_job(self):
        job = JobState()
        job.reset({'status': 'idle'})
        assert job.try_start({'status': 'running', 'label': 'go'}) is True
        assert job.snapshot() == {'status': 'running', 'label': 'go'}

    def test_try_start_rejects_running_job(self):
        job = JobState()
        job.reset({'status': 'running', 'label': 'first'})
        assert job.try_start({'status': 'running', 'label': 'second'}) is False
        assert job.get('label') == 'first'

    def test_try_start_is_atomic_under_contention(self):
        """Only one of many concurrent starters may claim the job."""
        job = JobState()
        job.reset({'status': 'idle'})
        barrier = threading.Barrier(20)
        wins = []

        def racer(i):
            barrier.wait()
            if job.try_start({'status': 'running', 'winner': i}):
                wins.append(i)

        threads = [threading.Thread(target=racer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(wins) == 1
        assert job.get('winner') == wins[0]

    def test_concurrent_updates_do_not_lose_keys(self):
        """Interleaved multi-key updates never expose a torn write."""
        job = JobState()
        job.reset({'status': 'running'})
        errors = []

        def writer(tag):
            for i in range(200):
                job.update(fetched=i, label=f'{tag}-{i}')

        def reader():
            for _ in range(200):
                snap = job.snapshot()
                if 'status' not in snap:
                    errors.append(snap)

        threads = [threading.Thread(target=writer, args=(t,)) for t in 'ab']
        threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert job.get('status') == 'running'


# ---------------------------------------------------------------------------
# JobRegistry unit tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestJobRegistry:
    def test_seeds_idle_defaults(self):
        reg = JobRegistry()
        assert reg.analysis.snapshot() == {'status': 'idle', 'started_at': None, 'result': None}
        assert reg.fetch.snapshot() == {'status': 'idle', 'fetched': 0, 'label': '', 'started_at': None}
        assert reg.backfill.snapshot() == {'status': 'idle'}
        assert reg.refresh_gear.snapshot() == {'status': 'idle'}
        assert reg.garmin_sync.snapshot() == {'status': 'idle'}
        assert not reg.analysis_stop.is_set()


# ---------------------------------------------------------------------------
# Blueprint wiring — endpoints must read/write the container's JobRegistry
# ---------------------------------------------------------------------------

@pytest.fixture
def job_client():
    """Fresh app instance so job state doesn't leak across tests."""
    from app.factory import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, app


@pytest.mark.integration
class TestJobEndpoints:
    def test_status_endpoints_report_idle_defaults(self, job_client):
        client, _ = job_client
        assert client.get('/api/analyze/status').get_json()['status'] == 'idle'
        assert client.get('/api/fetch/status').get_json()['status'] == 'idle'
        assert client.get('/api/stats/backfill-gear-ids/status').get_json()['status'] == 'idle'
        assert client.get('/api/stats/refresh-gear/status').get_json()['status'] == 'idle'
        assert client.get('/api/garmin/sync/status').get_json()['status'] == 'idle'

    def test_stop_when_not_running_returns_400(self, job_client):
        client, _ = job_client
        resp = client.post('/api/analyze/stop')
        assert resp.status_code == 400
        assert resp.get_json()['status'] == 'not_running'

    def test_analyze_rejects_when_registry_says_running(self, job_client):
        client, app = job_client
        app.container.jobs.analysis.update(status='running')
        resp = client.post('/api/analyze', json={})
        assert resp.status_code == 409
        assert resp.get_json()['status'] == 'already_running'

    def test_analyze_defaults_force_refresh_false(self, job_client, monkeypatch):
        """A POST /api/analyze body that omits force_refresh must NOT take
        the destructive full-reanalysis path by default. The frontend's
        triggerAnalysis() never sends force_refresh at all, so a stale
        True default meant every ordinary 'reanalyze' click unconditionally
        deleted and rebuilt cache/route_groups_cache.json instead of using
        the cheap incremental cache-hit path."""
        client, app = job_client
        app.container._initialised = True  # skip real service init
        mock_analysis_service = Mock()
        mock_analysis_service.run_full_analysis.return_value = {
            'status': 'success', 'activities_count': 0,
        }
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        # Patch only the `threading` name as seen inside data_bp, not the
        # shared stdlib module object — setting `threading.Thread` directly
        # mutates the real module (modules are singletons) and breaks
        # unrelated code (e.g. flask-limiter's cleanup Timer, whose
        # __init__ resolves `Thread` via a module-global lookup at call
        # time) for the duration of the test.
        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.data_bp.threading', fake_threading)

        resp = client.post('/api/analyze', json={})
        assert resp.status_code == 200
        _, kwargs = mock_analysis_service.run_full_analysis.call_args
        assert kwargs['force_refresh'] is False

    def test_bad_input_after_claim_does_not_wedge_the_job(self, job_client, monkeypatch):
        """#664: `int('abc')` after try_start left fetch 'running' -> 409 forever."""
        client, app = job_client
        app.container._initialised = True
        monkeypatch.setattr(app.container, 'analysis_service', Mock())
        resp = client.post('/api/fetch', json={'limit': 'abc'})
        assert resp.status_code == 400
        assert client.get('/api/fetch/status').get_json()['status'] == 'idle'

    def test_exception_after_claim_releases_the_job(self, job_client, monkeypatch):
        client, app = job_client
        app.config['PROPAGATE_EXCEPTIONS'] = False

        def boom():
            raise RuntimeError('init failed')
        monkeypatch.setattr(app.container, 'initialise', boom)
        for path, status_path in (('/api/fetch', '/api/fetch/status'),
                                  ('/api/analyze', '/api/analyze/status'),
                                  ('/api/stats/refresh-gear', '/api/stats/refresh-gear/status'),
                                  ('/api/stats/backfill-gear-ids', '/api/stats/backfill-gear-ids/status')):
            assert client.post(path, json={}).status_code == 500, path
            assert client.get(status_path).get_json()['status'] != 'running', path

    def test_released_claim_restores_previous_state(self):
        from app.jobs.job_state import JobState
        job = JobState()
        job.reset({'status': 'done', 'label': 'last run'})
        previous = job.try_claim({'status': 'running'})
        assert previous == {'status': 'done', 'label': 'last run'}
        assert job.try_claim({'status': 'running'}) is None
        job.restore_if_running(previous)
        assert job.snapshot() == {'status': 'done', 'label': 'last run'}

    @pytest.mark.parametrize('outcome,job_status', [
        ({'status': 'error', 'message': 'boom', 'activities_count': 0}, 'error'),
        ({'status': 'stopped', 'activities_count': 3}, 'stopped'),
    ])
    def test_failed_or_stopped_analysis_is_not_published(self, job_client, monkeypatch,
                                                         outcome, job_status):
        """#663: an error used to show as "Done — 0 activities", and both a
        failed and a stopped run rebuilt Commute/Planner from partial data."""
        client, app = job_client
        app.container._initialised = True
        mock_analysis_service = Mock()
        mock_analysis_service.run_full_analysis.return_value = outcome
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)
        refresh = Mock()
        monkeypatch.setattr(app.container, 'refresh_services', refresh)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        monkeypatch.setattr('app.api.data_bp.threading', types.SimpleNamespace(Thread=SyncThread))

        assert client.post('/api/analyze', json={}).status_code == 200
        status = client.get('/api/analyze/status').get_json()
        assert status['status'] == job_status
        assert 'previous results kept' in status['label']
        refresh.assert_not_called()

    def test_analyze_honors_explicit_force_refresh_true(self, job_client, monkeypatch):
        client, app = job_client
        app.container._initialised = True
        mock_analysis_service = Mock()
        mock_analysis_service.run_full_analysis.return_value = {
            'status': 'success', 'activities_count': 0,
        }
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.data_bp.threading', fake_threading)

        resp = client.post('/api/analyze', json={'force_refresh': True})
        assert resp.status_code == 200
        _, kwargs = mock_analysis_service.run_full_analysis.call_args
        assert kwargs['force_refresh'] is True

    def test_fetch_rejects_when_registry_says_running(self, job_client):
        client, app = job_client
        app.container.jobs.fetch.update(status='running')
        resp = client.post('/api/fetch', json={})
        assert resp.status_code == 409

    def test_backfill_rejects_when_registry_says_running(self, job_client):
        client, app = job_client
        app.container.jobs.backfill.update(status='running')
        resp = client.post('/api/stats/backfill-gear-ids')
        assert resp.status_code == 409

    def test_refresh_gear_rejects_when_registry_says_running(self, job_client):
        client, app = job_client
        app.container.jobs.refresh_gear.update(status='running')
        resp = client.post('/api/stats/refresh-gear')
        assert resp.status_code == 409
        assert resp.get_json()['status'] == 'already_running'

    def test_refresh_gear_runs_in_background_and_updates_job_state(self, job_client, monkeypatch):
        """#598 follow-up: refresh-gear previously called Strava synchronously
        on the request thread — a stravalib rate-limit hit could sleep that
        thread for up to Strava's rate-limit window. It must now background
        the call like every sibling Strava-fetch endpoint and report
        progress via /api/stats/refresh-gear/status."""
        client, app = job_client
        app.container._initialised = True
        mock_analysis_service = Mock()
        mock_analysis_service.data_fetcher.fetch_athlete_gear.return_value = {
            'bikes': [{'id': '1'}, {'id': '2'}],
            'shoes': [{'id': '3'}],
        }
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.stats_bp.threading', fake_threading)

        resp = client.post('/api/stats/refresh-gear')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'started'
        mock_analysis_service.data_fetcher.fetch_athlete_gear.assert_called_once()

        status = client.get('/api/stats/refresh-gear/status').get_json()
        assert status['status'] == 'done'
        assert status['bikes'] == 2
        assert status['shoes'] == 1

    def test_garmin_sync_rejects_when_registry_says_running(self, job_client):
        client, app = job_client
        app.container.jobs.garmin_sync.update(status='running')
        resp = client.post('/api/garmin/sync', json={})
        assert resp.status_code == 409
        assert resp.get_json()['status'] == 'already_running'

    def test_garmin_sync_runs_in_background_and_updates_job_state(self, job_client, monkeypatch):
        """#598 follow-up: garmin_sync previously called Garmin synchronously
        on the request thread — GarminService.fetch_activities() makes one
        HTTP call per activity (polyline fetch), all sequential. It must now
        background the call like every Strava-fetch endpoint and report
        progress via /api/garmin/sync/status."""
        client, app = job_client
        app.container._initialised = True

        mock_activity = Mock(id=123)
        mock_garmin_service = Mock()
        mock_garmin_service.is_connected.return_value = True
        mock_garmin_service.fetch_activities.return_value = [mock_activity]
        app.container.garmin_service = mock_garmin_service

        mock_analysis_service = Mock()
        mock_analysis_service.cache_fetcher.load_cached_activities.return_value = []
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.integrations_bp.threading', fake_threading)

        resp = client.post('/api/garmin/sync', json={'days': 90})
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'started'
        mock_garmin_service.fetch_activities.assert_called_once()
        # Local cache only (no Strava auth), and only the new rides are passed:
        # cache_activities merges them against what's on disk under its lock.
        mock_analysis_service.cache_fetcher.cache_activities.assert_called_once_with([mock_activity])

        status = client.get('/api/garmin/sync/status').get_json()
        assert status['status'] == 'done'
        assert status['fetched'] == 1
        assert status['new'] == 1

    def test_garmin_sync_not_connected_resets_job_and_returns_400(self, job_client):
        client, app = job_client
        app.container._initialised = True
        mock_garmin_service = Mock()
        mock_garmin_service.is_connected.return_value = False
        app.container.garmin_service = mock_garmin_service

        resp = client.post('/api/garmin/sync', json={})
        assert resp.status_code == 400
        assert app.container.jobs.garmin_sync.get('status') == 'idle'

    def test_garmin_sync_failure_reports_error_status(self, job_client, monkeypatch):
        client, app = job_client
        app.container._initialised = True
        mock_garmin_service = Mock()
        mock_garmin_service.is_connected.return_value = True
        mock_garmin_service.fetch_activities.side_effect = RuntimeError("Garmin unavailable")
        app.container.garmin_service = mock_garmin_service

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.integrations_bp.threading', fake_threading)

        resp = client.post('/api/garmin/sync', json={})
        assert resp.get_json()['status'] == 'started'

        status = client.get('/api/garmin/sync/status').get_json()
        assert status['status'] == 'error'
        assert 'Garmin unavailable' in status['label']

    def test_refresh_gear_failure_reports_error_status(self, job_client, monkeypatch):
        client, app = job_client
        app.container._initialised = True
        mock_analysis_service = Mock()
        mock_analysis_service.data_fetcher.fetch_athlete_gear.side_effect = RuntimeError("Strava unavailable")
        monkeypatch.setattr(app.container, 'analysis_service', mock_analysis_service)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self._target = target

            def start(self):
                self._target()

        fake_threading = types.SimpleNamespace(Thread=SyncThread)
        monkeypatch.setattr('app.api.stats_bp.threading', fake_threading)

        resp = client.post('/api/stats/refresh-gear')
        assert resp.get_json()['status'] == 'started'

        status = client.get('/api/stats/refresh-gear/status').get_json()
        assert status['status'] == 'error'
        assert 'Strava unavailable' in status['label']

    def test_stop_sets_event_and_updates_label(self, job_client):
        client, app = job_client
        jobs = app.container.jobs
        jobs.analysis.update(status='running')
        resp = client.post('/api/analyze/stop')
        assert resp.status_code == 200
        assert jobs.analysis_stop.is_set()
        assert jobs.analysis.get('label') == 'Stopping…'

    def test_status_reflects_registry_updates(self, job_client):
        client, app = job_client
        app.container.jobs.fetch.update(status='running', fetched=42, label='Fetching…')
        data = client.get('/api/fetch/status').get_json()
        assert data['status'] == 'running'
        assert data['fetched'] == 42
