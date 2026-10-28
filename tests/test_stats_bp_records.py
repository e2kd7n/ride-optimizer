"""Tests for Personal Records activity links in app/api/stats_bp.py.

Records link out to the activity on whichever service it was imported from,
since there's no in-app activity detail page.
"""

import pytest

from app.api.stats_bp import _activity_url, _compute_records


class _FakeActivity:
    def __init__(self, id, source=None, distance=10000.0, kilojoules=None):
        self.id = id
        self.name = f'Ride {id}'
        self.source = source
        self.start_date = '2026-07-01T10:00:00Z'
        self.start_date_local = '2026-07-01T10:00:00Z'
        self.distance = distance
        self.average_speed = 6.0
        self.total_elevation_gain = 100.0
        self.moving_time = 3600
        self.kilojoules = kilojoules


@pytest.mark.unit
class TestActivityUrl:
    def test_strava_activity_links_to_strava(self):
        assert _activity_url(_FakeActivity(123, source='strava')) == 'https://www.strava.com/activities/123'

    def test_garmin_activity_links_to_garmin_connect(self):
        assert _activity_url(_FakeActivity(456, source='garmin')) == 'https://connect.garmin.com/modern/activity/456'

    def test_legacy_activity_without_source_links_to_strava(self):
        assert _activity_url(_FakeActivity(789)) == 'https://www.strava.com/activities/789'


@pytest.mark.unit
class TestComputeRecordsLinks:
    def test_each_record_carries_url_and_source(self):
        acts = [
            _FakeActivity(1, source='strava', distance=5000.0),
            _FakeActivity(2, source='garmin', distance=90000.0, kilojoules=2000.0),
        ]
        records = _compute_records(acts)

        assert records['longest_ride']['url'] == 'https://connect.garmin.com/modern/activity/2'
        assert records['longest_ride']['source'] == 'garmin'
        assert records['most_kilojoules']['url'] == 'https://connect.garmin.com/modern/activity/2'
        for rec in records.values():
            assert rec['url'].endswith(f"/{rec['id']}")

    def test_missing_source_reported_as_strava(self):
        records = _compute_records([_FakeActivity(7)])
        assert records['longest_ride']['source'] == 'strava'
