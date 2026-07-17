"""Tests for local-time date bucketing in app/api/stats_bp.py (issue #496).

Bucketing/period-filtering must peg an activity to the calendar day it
started on *in the timezone where the ride began*, not the server's
timezone and not UTC. Strava's `start_date_local` carries the ride's local
wall-clock time (mislabeled with a trailing `Z`), so the fix takes its
date/time components at face value instead of converting through any
timezone.
"""

from datetime import datetime, timedelta

import pytest

from app.api.stats_bp import (
    _activity_local_date_str,
    _activity_local_start,
    _filter_activities_by_period,
)


class _FakeActivity:
    def __init__(self, start_date=None, start_date_local=None):
        self.start_date = start_date
        self.start_date_local = start_date_local


@pytest.mark.unit
class TestActivityLocalStart:
    def test_uses_start_date_local_wall_clock_verbatim(self):
        # A ride that started at 11pm in a timezone far ahead of UTC: the
        # UTC start_date has already rolled to the next day, but
        # start_date_local still shows the ride's own calendar day.
        activity = _FakeActivity(
            start_date='2026-07-02T09:00:00Z',
            start_date_local='2026-07-01T23:00:00Z',
        )
        result = _activity_local_start(activity)
        assert result == datetime(2026, 7, 1, 23, 0, 0)

    def test_crosses_month_boundary_correctly(self):
        activity = _FakeActivity(
            start_date='2026-08-01T05:30:00Z',
            start_date_local='2026-07-31T22:30:00Z',
        )
        assert _activity_local_start(activity).strftime('%Y-%m') == '2026-07'

    def test_crosses_year_boundary_correctly(self):
        activity = _FakeActivity(
            start_date='2027-01-01T06:00:00Z',
            start_date_local='2026-12-31T22:00:00Z',
        )
        assert _activity_local_start(activity).year == 2026

    def test_falls_back_to_server_tz_conversion_without_start_date_local(self):
        # Legacy cached activities predating this field: best-effort
        # fallback via the server's own timezone, not a bare tzinfo strip.
        activity = _FakeActivity(start_date='2026-07-01T04:00:00Z')
        result = _activity_local_start(activity)
        expected = datetime.fromisoformat('2026-07-01T04:00:00+00:00').astimezone().replace(tzinfo=None)
        assert result == expected


@pytest.mark.unit
class TestActivityLocalDateStr:
    def test_formats_local_calendar_date(self):
        activity = _FakeActivity(
            start_date='2026-07-02T09:00:00Z',
            start_date_local='2026-07-01T23:00:00Z',
        )
        assert _activity_local_date_str(activity) == '2026-07-01'

    def test_returns_none_without_any_date(self):
        assert _activity_local_date_str(_FakeActivity()) is None


@pytest.mark.unit
class TestFilterActivitiesByPeriod:
    def test_this_week_uses_ride_local_calendar_day_boundary(self):
        now_local = datetime.now()
        start_of_week_local = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)

        # An activity whose ride-local start time falls just after the
        # start-of-week boundary, encoded (as Strava does) with a
        # misleading UTC 'Z' marker rather than a real offset.
        true_local_time = start_of_week_local + timedelta(minutes=5)
        activity = _FakeActivity(
            start_date=true_local_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            start_date_local=true_local_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        )

        result = _filter_activities_by_period([activity], 'this_week')

        assert activity in result

    def test_ride_local_time_just_before_boundary_is_excluded(self):
        now_local = datetime.now()
        start_of_week_local = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)

        true_local_time = start_of_week_local - timedelta(minutes=5)
        activity = _FakeActivity(
            start_date=true_local_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            start_date_local=true_local_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        )

        result = _filter_activities_by_period([activity], 'this_week')

        assert activity not in result
