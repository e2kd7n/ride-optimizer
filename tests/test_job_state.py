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
