"""
Unit tests for app/services/garmin_service.py — GPS polyline population (#430).

Garmin ride activities used to reach data/cache/activities.json with
polyline=None (the activity list endpoint only returns start/end lat-lng),
so coverage_tracker silently skipped every Garmin activity. These tests
cover GarminService._fetch_polyline / fetch_activities populating a real
Google-encoded polyline, matching the shape coverage_tracker expects.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from app.services.garmin_service import GarminService


def _install_fake_garth(connectapi_side_effect):
    """Install a minimal fake `garth` module into sys.modules so `import garth`
    inside GarminService methods resolves without the real dependency."""
    fake_garth = types.ModuleType("garth")
    fake_garth.connectapi = MagicMock(side_effect=connectapi_side_effect)
    fake_garth.client = MagicMock(oauth1_token="token")
    sys.modules["garth"] = fake_garth
    return fake_garth


@pytest.fixture(autouse=True)
def _cleanup_fake_garth():
    yield
    sys.modules.pop("garth", None)


class TestFetchPolyline:
    def test_encodes_track_points_to_polyline(self):
        details = {
            "geoPolylineDTO": {
                "polyline": [
                    {"lat": 40.7128, "lon": -74.0060},
                    {"lat": 40.7130, "lon": -74.0058},
                ]
            }
        }
        _install_fake_garth(lambda *a, **k: details)
        svc = GarminService()
        svc._client = MagicMock()  # force is_connected() True path not needed here

        result = svc._fetch_polyline(12345)

        assert result is not None
        import polyline as polyline_codec
        decoded = polyline_codec.decode(result)
        assert len(decoded) == 2
        assert decoded[0] == pytest.approx((40.7128, -74.0060), abs=1e-4)

    def test_missing_geo_polyline_returns_none(self):
        _install_fake_garth(lambda *a, **k: {})
        svc = GarminService()
        assert svc._fetch_polyline(12345) is None

    def test_non_dict_response_returns_none(self):
        _install_fake_garth(lambda *a, **k: None)
        svc = GarminService()
        assert svc._fetch_polyline(12345) is None

    def test_points_missing_lat_lon_are_skipped(self):
        details = {
            "geoPolylineDTO": {
                "polyline": [
                    {"lat": None, "lon": -74.0060},
                    {"lat": 40.7130, "lon": -74.0058},
                ]
            }
        }
        _install_fake_garth(lambda *a, **k: details)
        svc = GarminService()
        result = svc._fetch_polyline(12345)
        import polyline as polyline_codec
        assert len(polyline_codec.decode(result)) == 1

    def test_connectapi_exception_returns_none(self):
        _install_fake_garth(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        svc = GarminService()
        assert svc._fetch_polyline(12345) is None


class TestFetchActivitiesPopulatesPolyline:
    def _raw_activity(self, activity_id=999):
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

    def test_fetch_activities_attaches_polyline(self):
        raw_list = [self._raw_activity()]
        details = {
            "geoPolylineDTO": {
                "polyline": [
                    {"lat": 40.0, "lon": -74.0},
                    {"lat": 40.05, "lon": -74.05},
                ]
            }
        }

        def side_effect(url, *a, **k):
            if "activitylist-service" in url:
                return raw_list
            return details

        _install_fake_garth(side_effect)
        svc = GarminService()
        svc._client = MagicMock()
        with patch.object(GarminService, "is_connected", return_value=True):
            activities = svc.fetch_activities(days=30)

        assert len(activities) == 1
        assert activities[0].polyline is not None
        assert activities[0].type == "Ride"

    def test_fetch_activities_survives_polyline_fetch_failure(self):
        """A GPS-track fetch failure for one activity must not drop the
        activity or blow up the whole sync — it should just carry no
        polyline, same as before this fix."""
        raw_list = [self._raw_activity()]

        def side_effect(url, *a, **k):
            if "activitylist-service" in url:
                return raw_list
            raise RuntimeError("rate limited")

        _install_fake_garth(side_effect)
        svc = GarminService()
        svc._client = MagicMock()
        with patch.object(GarminService, "is_connected", return_value=True):
            activities = svc.fetch_activities(days=30)

        assert len(activities) == 1
        assert activities[0].polyline is None

    def test_fetch_activities_raises_when_not_connected(self):
        svc = GarminService()
        with patch.object(GarminService, "is_connected", return_value=False):
            with pytest.raises(RuntimeError):
                svc.fetch_activities()
