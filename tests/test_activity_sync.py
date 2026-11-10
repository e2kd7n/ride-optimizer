"""Source-agnostic activity sync (#619, #620)."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.services import activity_sync
from src.json_storage import JSONStorage


class FakeCache:
    """Stands in for data/cache/activities.json."""

    def __init__(self, ids=()):
        self.ids = set(ids)

    def count(self):
        return len(self.ids)


def _container(tmp_path, *, strava=True, garmin=True, cache=None):
    cache = cache or FakeCache()
    creds = tmp_path / 'credentials.json'
    if strava:
        creds.write_text('{}')
    garmin_svc = Mock()
    garmin_svc.is_connected.return_value = garmin
    analysis = Mock()
    analysis.run_full_analysis.return_value = {'status': 'success'}
    analysis.cache_fetcher.load_cached_activities.side_effect = (
        lambda: [SimpleNamespace(id=i) for i in cache.ids])
    analysis.cache_fetcher.cache_activities.side_effect = (
        lambda acts, merge=True: cache.ids.update(a.id for a in acts))
    return SimpleNamespace(
        credentials_path=creds,
        get_garmin_service=lambda: garmin_svc,
        garmin=garmin_svc,
        analysis_service=analysis,
        exploration_service=Mock(),
        refresh_services=Mock(),
        storage=JSONStorage(str(tmp_path / 'data')),
        cache=cache,
    )


@pytest.fixture(autouse=True)
def _count_from_fake_cache(monkeypatch):
    holder = {}
    monkeypatch.setattr(activity_sync, '_cache_count', lambda: holder['cache'].count())
    return holder


def _use(holder, container):
    holder['cache'] = container.cache
    return container


@pytest.mark.unit
class TestConnectedSources:
    def test_both(self, tmp_path):
        assert activity_sync.connected_sources(_container(tmp_path)) == ['strava', 'garmin']

    def test_garmin_only(self, tmp_path):
        assert activity_sync.connected_sources(_container(tmp_path, strava=False)) == ['garmin']

    def test_none(self, tmp_path):
        assert activity_sync.connected_sources(_container(tmp_path, strava=False, garmin=False)) == []


@pytest.mark.unit
class TestRunSync:
    def test_garmin_only_merges_new_rides_and_analyses(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path, strava=False, cache=FakeCache({1})))
        c.garmin.fetch_activities.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

        result = activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 30))

        kwargs = c.garmin.fetch_activities.call_args.kwargs
        assert (kwargs['start_date'], kwargs['end_date']) == (date(2026, 9, 1), date(2026, 9, 30))
        # Only the new ride goes to the cache writer.
        assert [a.id for a in c.analysis_service.cache_fetcher.cache_activities.call_args.args[0]] == [2]
        assert result['status'] == 'done'
        assert result['new'] == 1
        assert result['sources']['garmin'] == {'status': 'ok', 'new': 1, 'fetched': 0, 'error': None}
        c.analysis_service.run_full_analysis.assert_called_once_with(force_refresh=False, skip_strava_fetch=True)
        c.refresh_services.assert_called_once_with('commute', 'planner')
        c.exploration_service.invalidate_caches.assert_called_once()
        assert result['analysed'] is True

    def test_strava_failure_does_not_stop_garmin(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path))
        c.analysis_service.data_fetcher.fetch_activities.side_effect = RuntimeError('ApplicationInactive')
        c.garmin.fetch_activities.return_value = [SimpleNamespace(id=7)]

        result = activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 30))

        assert result['sources']['strava']['status'] == 'error'
        assert 'ApplicationInactive' in result['sources']['strava']['error']
        assert result['sources']['garmin']['new'] == 1
        assert result['status'] == 'done'

    def test_strava_window_is_local_and_end_inclusive(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path, garmin=False))
        activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 30))
        kw = c.analysis_service.data_fetcher.fetch_activities.call_args.kwargs
        assert kw['after'].tzinfo is not None and kw['before'].tzinfo is not None
        assert (kw['after'].date(), kw['before'].date()) == (date(2026, 9, 1), date(2026, 10, 1))
        assert kw['merge_cache'] is True

    def test_all_sources_failing_is_an_error(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path))
        c.analysis_service.data_fetcher.fetch_activities.side_effect = RuntimeError('down')
        c.garmin.fetch_activities.side_effect = RuntimeError('down too')
        result = activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 2))
        assert result['status'] == 'error'
        c.analysis_service.run_full_analysis.assert_not_called()

    def test_nothing_new_skips_analysis(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path, strava=False, cache=FakeCache({1})))
        c.garmin.fetch_activities.return_value = [SimpleNamespace(id=1)]
        result = activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 2))
        assert result['new'] == 0
        c.analysis_service.run_full_analysis.assert_not_called()

    def test_no_sources(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path, strava=False, garmin=False))
        assert activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 2))['status'] == 'no_sources'

    def test_records_status_and_nightly_window(self, tmp_path, _count_from_fake_cache):
        c = _use(_count_from_fake_cache, _container(tmp_path, strava=False))
        c.garmin.fetch_activities.return_value = []
        activity_sync.run_sync(c, date(2026, 9, 1), date(2026, 9, 20))
        status = activity_sync.read_status(c)
        assert status['sources']['garmin']['synced_through'] == '2026-09-20'
        assert status['sources']['garmin']['last_status'] == 'ok'
        start, end = activity_sync.nightly_window(c, today=date(2026, 9, 25))
        assert (start, end) == (date(2026, 9, 18), date(2026, 9, 25))


@pytest.mark.unit
class TestNightlyWindow:
    def test_default_without_history(self, tmp_path, _count_from_fake_cache):
        c = _container(tmp_path)
        assert activity_sync.nightly_window(c, today=date(2026, 9, 25)) == (date(2026, 9, 18), date(2026, 9, 25))

    def test_capped(self, tmp_path, _count_from_fake_cache):
        c = _container(tmp_path)
        c.storage.write(activity_sync.SYNC_STATUS_FILE,
                        {'sources': {'garmin': {'synced_through': '2025-01-01'}}})
        start, _ = activity_sync.nightly_window(c, today=date(2026, 9, 25))
        assert (date(2026, 9, 25) - start).days == activity_sync.NIGHTLY_MAX_DAYS


@pytest.mark.unit
class TestSyncEndpoint:
    def test_no_sources_is_a_clear_400(self, client, monkeypatch):
        from launch import app
        monkeypatch.setattr(app.container, '_initialised', True)
        monkeypatch.setattr(activity_sync, 'connected_sources', lambda c: [])
        resp = client.post('/api/sync', json={'after_date': '2026-09-01', 'before_date': '2026-09-30'})
        assert resp.status_code == 400
        body = resp.get_json()
        assert body['status'] == 'no_sources'
        assert 'Settings' in body['message']
        assert app.container.jobs.fetch.get('status') == 'idle'

    def test_bad_dates(self, client):
        assert client.post('/api/sync', json={'after_date': 'nope'}).status_code == 400
        assert client.post('/api/sync', json={'after_date': '2026-09-30',
                                              'before_date': '2026-09-01'}).status_code == 400

    def test_starts_background_sync(self, client, monkeypatch):
        from launch import app
        monkeypatch.setattr(app.container, '_initialised', True)
        monkeypatch.setattr(activity_sync, 'connected_sources', lambda c: ['garmin'])
        seen = {}

        def fake_run(container, start, end, **kw):
            seen.update(start=start, end=end, sources=kw['sources'])
            return {'status': 'done', 'new': 2, 'total': 10, 'analysed': True,
                    'sources': {'garmin': {'status': 'ok', 'new': 2, 'fetched': 2, 'error': None}}}
        monkeypatch.setattr(activity_sync, 'run_sync', fake_run)

        class SyncThread:
            def __init__(self, target=None, daemon=None):
                self.target = target

            def start(self):
                self.target()
        monkeypatch.setattr('app.api.data_bp.threading.Thread', SyncThread)

        resp = client.post('/api/sync', json={'after_date': '2026-09-01', 'before_date': '2026-09-30'})
        assert resp.status_code == 200
        assert resp.get_json()['sources'] == ['garmin']
        assert seen == {'start': date(2026, 9, 1), 'end': date(2026, 9, 30), 'sources': ['garmin']}
        status = client.get('/api/sync/status').get_json()
        assert status['status'] == 'done'
        assert '2 new from Garmin' in status['label']
