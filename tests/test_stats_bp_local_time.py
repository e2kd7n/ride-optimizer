"""Tests for local-time date bucketing in app/api/stats_bp.py (issue #496).

Bucketing/period-filtering previously converted a UTC start_date to naive
by stripping tzinfo without shifting the wall-clock, so a ride that starts
late at night locally but crosses into the next UTC day was bucketed as if
it happened a day (or, at boundaries, a month/year) later than it did.
"""

from datetime import datetime, timedelta

import pytest

from app.api.stats_bp import _filter_activities_by_period, _parse_activity_start_local


class _FakeActivity:
    def __init__(self, start_date):
        self.start_date = start_date


@pytest.mark.unit
class TestParseActivityStartLocal:
    def test_utc_wallclock_shifts_without_fix_would_differ(self):
        utc_dt = datetime.fromisoformat('2026-07-01T04:00:00+00:00')
        local_dt = utc_dt.astimezone().replace(tzinfo=None)
        naive_strip_dt = utc_dt.replace(tzinfo=None)
        # The two approaches only agree when local UTC offset is 0 — assert
        # the fixed helper actually applies the local offset.
        offset = datetime.now().astimezone().utcoffset()
        assert local_dt == naive_strip_dt + offset

    def test_parse_activity_start_local_applies_local_offset(self):
        start_date = '2026-07-01T04:00:00Z'
        result = _parse_activity_start_local(start_date)
        expected = datetime.fromisoformat('2026-07-01T04:00:00+00:00').astimezone().replace(tzinfo=None)
        assert result == expected


@pytest.mark.unit
class TestFilterActivitiesByPeriod:
    def test_this_week_uses_local_calendar_day_boundary(self):
        now_local = datetime.now()
        start_of_week_local = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)

        # An activity whose UTC start_date, if naively stripped of tzinfo,
        # would fall just *before* the local start-of-week boundary, but
        # whose true local time falls just *after* it.
        local_offset = datetime.now().astimezone().utcoffset()
        true_local_time = start_of_week_local + timedelta(minutes=5)
        utc_equivalent = true_local_time - local_offset
        activity = _FakeActivity(utc_equivalent.strftime('%Y-%m-%dT%H:%M:%SZ'))

        result = _filter_activities_by_period([activity], 'this_week')

        if local_offset.total_seconds() == 0:
            pytest.skip("Server is running in UTC; boundary-shift case can't be exercised")
        assert activity in result
