"""
Unit tests for app/services/garmin_service.py.

GPS polyline population (#430): Garmin ride activities used to reach
data/cache/activities.json with polyline=None (the activity list endpoint only
returns start/end lat-lng), so coverage_tracker silently skipped every Garmin
activity.

Client interface (#636): GarminService talks to Garmin only through the
GarminClient protocol, so these tests inject a fake client instead of patching
the garth module.
"""
from datetime import date
from unittest.mock import patch

import pytest

from app.services.garmin_service import GarminService


class FakeClient:
    """In-memory GarminClient."""

    def __init__(self, activities=None, details=None, resume_ok=True, login_name='rider'):
        self.activities = activities or []
        self.details = details if details is not None else (lambda activity_id: {})
        self.resume_ok = resume_ok
        self.login_name = login_name
        self.list_calls = []
        self.resumed_from = None

    def resume(self, token_dir):
        self.resumed_from = token_dir
        if isinstance(self.resume_ok, Exception):
            raise self.resume_ok
        return self.resume_ok

    def login(self, email, password, token_dir):
        token_dir.mkdir(parents=True, exist_ok=True)
        (token_dir / 'oauth1_token.json').write_text('{}')
        return self.login_name

    def list_activities(self, start_date, end_date, start, limit):
        self.list_calls.append((start_date, end_date, start, limit))
        return self.activities[start:start + limit]

    def activity_details(self, activity_id):
        return self.details(activity_id)


def _service(tmp_path, client, connected=True):
    svc = GarminService(token_dir=tmp_path / 'tokens', client_factory=lambda: client)
    svc._connected = connected
    return svc


def _raw_activity(activity_id=999):
    return {
        "activityId": activity_id,
        "activityName": "Evening Ride",
        "activityType": {"typeKey": "road_biking"},
        "startTimeLocal": "2026-07-01 18:00:00",
        "distance": 20000.0,
        "movingDuration": 3600,
        "duration": 3700,
        "elevationGain": 150.0,
        "startLatitude": 40.0,
        "startLongitude": -74.0,
        "endLatitude": 40.1,
        "endLongitude": -74.1,
    }


TRACK = {"geoPolylineDTO": {"polyline": [{"lat": 40.7128, "lon": -74.0060},
                                         {"lat": 40.7130, "lon": -74.0058}]}}


class TestFetchPolyline:
    def test_encodes_track_points_to_polyline(self, tmp_path):
        svc = _service(tmp_path, FakeClient(details=lambda i: TRACK))
        result = svc._fetch_polyline(12345)
        import polyline as polyline_codec
        decoded = polyline_codec.decode(result)
        assert len(decoded) == 2
        assert decoded[0] == pytest.approx((40.7128, -74.0060), abs=1e-4)

    def test_missing_geo_polyline_returns_none(self, tmp_path):
        svc = _service(tmp_path, FakeClient(details=lambda i: {}))
        assert svc._fetch_polyline(12345) is None

    def test_non_dict_response_returns_none(self, tmp_path):
        svc = _service(tmp_path, FakeClient(details=lambda i: None))
        assert svc._fetch_polyline(12345) is None

    def test_points_missing_lat_lon_are_skipped(self, tmp_path):
        details = {"geoPolylineDTO": {"polyline": [{"lat": None, "lon": -74.0060},
                                                   {"lat": 40.7130, "lon": -74.0058}]}}
        svc = _service(tmp_path, FakeClient(details=lambda i: details))
        import polyline as polyline_codec
        assert len(polyline_codec.decode(svc._fetch_polyline(12345))) == 1

    def test_client_exception_returns_none(self, tmp_path):
        def boom(i):
            raise RuntimeError("boom")
        svc = _service(tmp_path, FakeClient(details=boom))
        assert svc._fetch_polyline(12345) is None


class TestFetchActivities:
    def test_fetch_activities_attaches_polyline(self, tmp_path):
        svc = _service(tmp_path, FakeClient([_raw_activity()], details=lambda i: TRACK))
        activities = svc.fetch_activities(days=30)
        assert len(activities) == 1
        assert activities[0].polyline is not None
        assert activities[0].type == "Ride"

    def test_fetch_activities_survives_polyline_fetch_failure(self, tmp_path):
        """A GPS-track fetch failure for one activity must not drop the
        activity or blow up the whole sync."""
        def rate_limited(i):
            raise RuntimeError("rate limited")
        svc = _service(tmp_path, FakeClient([_raw_activity()], details=rate_limited))
        activities = svc.fetch_activities(days=30)
        assert len(activities) == 1
        assert activities[0].polyline is None

    def test_fetch_activities_raises_when_not_connected(self, tmp_path):
        svc = _service(tmp_path, FakeClient(), connected=False)
        with patch.object(GarminService, "is_connected", return_value=False):
            with pytest.raises(RuntimeError):
                svc.fetch_activities()

    def test_pages_until_limit(self, tmp_path):
        client = FakeClient([_raw_activity(i) for i in range(1, 251)])
        svc = _service(tmp_path, client)
        activities = svc.fetch_activities(days=None, limit=230)
        assert len(activities) == 230
        assert [c[2:] for c in client.list_calls] == [(0, 100), (100, 100), (200, 30)]

    def test_stops_on_short_page(self, tmp_path):
        client = FakeClient([_raw_activity(i) for i in range(1, 121)])
        svc = _service(tmp_path, client)
        assert len(svc.fetch_activities(days=None, limit=1000)) == 120
        assert len(client.list_calls) == 2

    def test_date_range_is_passed_through(self, tmp_path):
        client = FakeClient([])
        svc = _service(tmp_path, client)
        svc.fetch_activities(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
        assert client.list_calls[0][:2] == (date(2026, 9, 1), date(2026, 9, 30))

    def test_days_becomes_start_date(self, tmp_path):
        client = FakeClient([])
        svc = _service(tmp_path, client)
        svc.fetch_activities(days=10)
        start_date, end_date, _, _ = client.list_calls[0]
        assert end_date is None
        assert (date.today() - start_date).days in (10, 11)

    def test_progress_callback(self, tmp_path):
        seen = []
        svc = _service(tmp_path, FakeClient([_raw_activity(1), _raw_activity(2)]))
        svc.fetch_activities(days=5, progress_callback=seen.append)
        assert seen == [1, 2]


class TestConnection:
    def test_not_connected_without_token_dir(self, tmp_path):
        client = FakeClient()
        svc = _service(tmp_path, client, connected=False)
        assert svc.is_connected() is False
        assert client.resumed_from is None

    def test_resume_from_saved_tokens(self, tmp_path):
        client = FakeClient()
        svc = _service(tmp_path, client, connected=False)
        svc.token_dir.mkdir()
        assert svc.is_connected() is True
        assert client.resumed_from == svc.token_dir

    def test_resume_failure_is_not_connected(self, tmp_path):
        svc = _service(tmp_path, FakeClient(resume_ok=ValueError('bad token')), connected=False)
        svc.token_dir.mkdir()
        assert svc.is_connected() is False

    def test_connect_saves_and_reports_name(self, tmp_path):
        svc = _service(tmp_path, FakeClient(login_name='Jo'), connected=False)
        assert svc.connect('jo@example.com', 'pw') == {'success': True, 'display_name': 'Jo'}
        assert svc.is_connected()
        assert svc.get_status() == {'connected': True, 'display_name': 'Jo'}

    def test_connect_rate_limit_message(self, tmp_path):
        client = FakeClient()

        def limited(*a):
            raise RuntimeError('429 Too Many Requests')
        client.login = limited
        svc = _service(tmp_path, client, connected=False)
        result = svc.connect('jo@example.com', 'pw')
        assert result['success'] is False
        assert 'rate-limiting' in result['error']

    def test_disconnect_removes_tokens_and_client(self, tmp_path):
        made = []

        def factory():
            made.append(FakeClient())
            return made[-1]
        svc = GarminService(token_dir=tmp_path / 'tokens', client_factory=factory)
        svc.connect('jo@example.com', 'pw')
        svc.disconnect()
        assert not svc.token_dir.exists()
        assert svc.is_connected() is False
        svc.token_dir.mkdir()
        assert svc.is_connected() is True
        assert len(made) == 2  # a fresh client after disconnect


class TestGarthClient:
    def test_uses_a_private_client_with_timeout(self):
        """Each GarthClient owns its own garth.Client, not the global one."""
        pytest.importorskip('garth')
        import garth
        from app.services.garmin_client import GarthClient, GARMIN_TIMEOUT_SECONDS
        a, b = GarthClient(), GarthClient()
        assert a._client is not b._client
        assert a._client is not garth.client
        assert a._client.timeout == GARMIN_TIMEOUT_SECONDS

    def test_list_activities_builds_params(self):
        pytest.importorskip('garth')
        from app.services.garmin_client import GarthClient, ACTIVITY_LIST_PATH
        c = GarthClient()
        with patch.object(c._client, 'connectapi', return_value=[{'activityId': 1}]) as api:
            out = c.list_activities(date(2026, 9, 1), date(2026, 9, 30), 100, 50)
        assert out == [{'activityId': 1}]
        path = api.call_args.args[0]
        params = api.call_args.kwargs['params']
        assert path == ACTIVITY_LIST_PATH
        assert params == {'start': '100', 'limit': '50',
                          'startDate': '2026-09-01', 'endDate': '2026-09-30'}

    def test_list_activities_non_list_is_empty(self):
        pytest.importorskip('garth')
        from app.services.garmin_client import GarthClient
        c = GarthClient()
        with patch.object(c._client, 'connectapi', return_value=None):
            assert c.list_activities(None, None, 0, 10) == []
