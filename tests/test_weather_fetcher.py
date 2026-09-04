"""Tests for src/weather_fetcher.py — daily-forecast caching (#554).

get_daily_forecast() previously made a fresh Open-Meteo HTTP call on every
invocation with zero caching (unlike get_current_conditions, which already had
a radius+TTL cache). That let PlannerService.get_recommendations() fire one
external call per (ride, day) with no dedup even when many rides shared the
same start location — confirmed on production data to take 12+ minutes and
starve the app's 4-thread gunicorn pool. These tests cover the new
forecast-cache layer added to close that gap.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.weather_fetcher import WeatherFetcher


def _mock_daily_response(dates, temp_max=22.0):
    """Build a fake Open-Meteo /v1/forecast 'daily' JSON payload for `dates`."""
    return {
        'daily': {
            'time': dates,
            'temperature_2m_max': [temp_max] * len(dates),
            'temperature_2m_min': [temp_max - 7] * len(dates),
            'precipitation_sum': [0.0] * len(dates),
            'precipitation_probability_max': [10] * len(dates),
            'wind_speed_10m_max': [15.0] * len(dates),
            'wind_direction_10m_dominant': [180] * len(dates),
        }
    }


@pytest.fixture
def mock_session():
    with patch('src.weather_fetcher.requests.Session') as mock_session_cls:
        yield mock_session_cls


@pytest.fixture
def fetcher(mock_session, tmp_path):
    """A WeatherFetcher with an isolated cache_file — forecast_cache_file
    should default alongside it (same tmp_path), not the real cache/ dir."""
    return WeatherFetcher(cache_file=str(tmp_path / "weather_cache.json"))


def _set_response(mock_session, dates):
    response = Mock()
    response.json.return_value = _mock_daily_response(dates)
    response.raise_for_status = Mock()
    mock_session.return_value.get.return_value = response
    return response


class TestForecastCacheIsolation:
    def test_forecast_cache_file_defaults_alongside_cache_file(self, fetcher, tmp_path):
        """A caller isolating cache_file (e.g. via tmp_path) must get an
        isolated forecast cache too, not a write into the real cache/ dir."""
        assert fetcher.forecast_cache_file.parent == tmp_path
        assert fetcher.forecast_cache_file.name == "daily_forecast_cache.json"


class TestGetDailyForecastCaching:
    def test_first_call_hits_the_api(self, fetcher, mock_session):
        dates = ['2026-01-01', '2026-01-02']
        _set_response(mock_session, dates)

        result = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)

        assert len(result) == 2
        mock_session.return_value.get.assert_called_once()

    def test_second_call_same_location_and_days_is_cached(self, fetcher, mock_session):
        dates = ['2026-01-01', '2026-01-02']
        _set_response(mock_session, dates)

        first = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)
        second = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)

        mock_session.return_value.get.assert_called_once()
        assert first == second

    def test_nearby_location_within_radius_is_cached(self, fetcher, mock_session):
        """Same dedup radius as get_current_conditions (cache_radius_km, default 2km)."""
        dates = ['2026-01-01']
        _set_response(mock_session, dates)

        fetcher.get_daily_forecast(40.7128, -74.0060, days=1)
        # ~1km away — within the default 2km cache_radius_km.
        result = fetcher.get_daily_forecast(40.7218, -74.0060, days=1)

        mock_session.return_value.get.assert_called_once()
        assert result is not None

    def test_far_location_is_not_cached(self, fetcher, mock_session):
        dates = ['2026-01-01']
        _set_response(mock_session, dates)

        fetcher.get_daily_forecast(40.7128, -74.0060, days=1)
        fetcher.get_daily_forecast(51.5074, -0.1278, days=1)  # London — nowhere close

        assert mock_session.return_value.get.call_count == 2

    def test_cached_forecast_longer_than_requested_is_trimmed(self, fetcher, mock_session):
        """A 5-day forecast already cached satisfies a later 2-day request
        without a new API call, trimmed to the requested length."""
        dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05']
        _set_response(mock_session, dates)

        fetcher.get_daily_forecast(40.7128, -74.0060, days=5)
        result = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)

        mock_session.return_value.get.assert_called_once()
        assert len(result) == 2

    def test_cached_forecast_shorter_than_requested_refetches(self, fetcher, mock_session):
        """A 2-day cached forecast does NOT satisfy a later 5-day request."""
        _set_response(mock_session, ['2026-01-01', '2026-01-02'])
        fetcher.get_daily_forecast(40.7128, -74.0060, days=2)

        _set_response(mock_session, ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'])
        result = fetcher.get_daily_forecast(40.7128, -74.0060, days=5)

        assert mock_session.return_value.get.call_count == 2
        assert len(result) == 5

    def test_expired_forecast_cache_refetches(self, fetcher, mock_session):
        dates = ['2026-01-01']
        _set_response(mock_session, dates)
        fetcher.get_daily_forecast(40.7128, -74.0060, days=1)

        # Force the cached entry to look older than forecast_cache_duration_hours.
        key = (40.7128, -74.0060)
        fetcher.forecast_cache[key]['timestamp'] = (
            datetime.now() - timedelta(hours=fetcher.forecast_cache_duration_hours + 1)
        )

        fetcher.get_daily_forecast(40.7128, -74.0060, days=1)

        assert mock_session.return_value.get.call_count == 2

    def test_forecast_cache_persists_to_disk(self, fetcher, mock_session):
        _set_response(mock_session, ['2026-01-01'])
        fetcher.get_daily_forecast(40.7128, -74.0060, days=1)

        assert fetcher.forecast_cache_file.exists()

        reloaded = WeatherFetcher(cache_file=str(fetcher.cache_file))
        assert (40.7128, -74.0060) in reloaded.forecast_cache

    def test_none_response_is_not_cached(self, fetcher, mock_session):
        """A response missing 'daily' returns None and must not poison the cache."""
        response = Mock()
        response.json.return_value = {}
        response.raise_for_status = Mock()
        mock_session.return_value.get.return_value = response

        result = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)

        assert result is None
        assert (40.7128, -74.0060) not in fetcher.forecast_cache

    def test_forecast_cache_eviction_caps_size(self, mock_session, tmp_path):
        fetcher = WeatherFetcher(cache_file=str(tmp_path / "weather_cache.json"), max_cache_entries=3)
        _set_response(mock_session, ['2026-01-01'])

        for i in range(5):
            fetcher.get_daily_forecast(40.0 + i, -74.0, days=1)

        assert len(fetcher.forecast_cache) == 3
