"""Tests for _parse_date_range in app/api/data_bp.py (issues #494, #495).

#494: bare "YYYY-MM-DD" dates from the Settings custom-range picker are a
local calendar date, not UTC — they must be localized before being handed
to stravalib, which treats naive datetimes as already UTC.

#495: before_date is used as an inclusive end date ("through this day"),
but Strava's before filter is a strict less-than, so a bare end date must
be bumped forward one day to include the whole selected day.
"""

from datetime import timezone

import pytest

from app.api.data_bp import _parse_date_range


@pytest.mark.unit
class TestParseDateRange:
    def test_bare_after_date_is_localized_not_utc(self):
        after, _ = _parse_date_range({'after_date': '2026-01-15'})
        assert after.tzinfo is not None
        assert after.tzinfo != timezone.utc
        assert (after.year, after.month, after.day) == (2026, 1, 15)
        assert after.hour == 0

    def test_bare_before_date_is_inclusive_of_whole_day(self):
        _, before = _parse_date_range({'before_date': '2026-01-31'})
        assert (before.year, before.month, before.day) == (2026, 2, 1)
        assert before.hour == 0
        assert before.tzinfo is not None

    def test_full_iso_datetime_before_is_not_bumped(self):
        _, before = _parse_date_range({'before_date': '2026-01-31T18:00:00'})
        assert (before.year, before.month, before.day) == (2026, 1, 31)
        assert before.hour == 18

    def test_full_iso_datetime_after_is_localized_unchanged(self):
        after, _ = _parse_date_range({'after_date': '2026-01-15T09:30:00'})
        assert (after.year, after.month, after.day) == (2026, 1, 15)
        assert after.hour == 9
        assert after.minute == 30

    def test_missing_keys_return_none(self):
        after, before = _parse_date_range({})
        assert after is None
        assert before is None

    def test_invalid_date_string_is_ignored(self):
        after, before = _parse_date_range({'after_date': 'not-a-date'})
        assert after is None
        assert before is None

    def test_both_dates_together(self):
        after, before = _parse_date_range({
            'after_date': '2026-01-01',
            'before_date': '2026-01-31',
        })
        assert (after.year, after.month, after.day) == (2026, 1, 1)
        assert (before.year, before.month, before.day) == (2026, 2, 1)
