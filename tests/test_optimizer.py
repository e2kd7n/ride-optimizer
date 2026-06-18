"""
Unit tests for optimizer module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Tuple, Optional

from src.optimizer import RouteOptimizer
from src.route_analyzer import Route, RouteGroup, RouteMetrics


def _make_route(activity_id=1, direction="home_to_work", distance=5000.0,
                duration=1200, elevation_gain=50.0, speed=4.17,
                coordinates=None):
    return Route(
        activity_id=activity_id,
        direction=direction,
        coordinates=coordinates or [(40.71, -74.00), (40.75, -73.98)],
        distance=distance,
        duration=duration,
        elevation_gain=elevation_gain,
        timestamp="2024-01-01T08:00:00+00:00",
        average_speed=speed,
    )


def _make_group(group_id="route_1", direction="home_to_work", n_routes=5,
                distance=5000.0, duration=1200, elevation=50.0, speed=4.17):
    routes = [_make_route(
        activity_id=i, direction=direction, distance=distance,
        duration=duration, elevation_gain=elevation, speed=speed,
    ) for i in range(n_routes)]
    return RouteGroup(
        id=group_id,
        direction=direction,
        routes=routes,
        representative_route=routes[0],
        frequency=n_routes,
    )


def _make_config(**overrides):
    defaults = {
        'units.system': 'metric',
        'optimization.weights.time': 0.35,
        'optimization.weights.distance': 0.25,
        'optimization.weights.safety': 0.25,
        'optimization.weights.weather': 0.15,
    }
    defaults.update(overrides)
    config = Mock()
    config.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return config


class TestRouteOptimizerInit:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_init_with_weather_disabled(self, mock_wind, mock_weather):
        groups = [_make_group("r1"), _make_group("r2", distance=8000, duration=2000)]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        assert optimizer.weather_fetcher is None
        assert optimizer.wind_calculator is None
        assert len(optimizer.metrics) == 2

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_metrics_calculated_for_all_groups(self, mock_wind, mock_weather):
        mock_weather.return_value.get_route_weather.return_value = None
        groups = [_make_group("r1"), _make_group("r2")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        assert "r1" in optimizer.metrics
        assert "r2" in optimizer.metrics

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_empty_route_group_skipped(self, mock_wind, mock_weather):
        empty = RouteGroup(
            id="empty", direction="home_to_work", routes=[],
            representative_route=_make_route(), frequency=0,
        )
        groups = [_make_group("r1"), empty]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        assert "empty" not in optimizer.metrics
        assert "r1" in optimizer.metrics


class TestWeatherScore:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_neutral_score_without_weather(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        group = groups[0]
        assert optimizer.calculate_weather_score(group) == 50

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_tailwind_increases_score(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        optimizer.weather_data["r1"] = {
            'avg_headwind_kph': -15,
            'avg_crosswind_kph': 0,
        }
        optimizer.enable_weather = True
        score = optimizer.calculate_weather_score(groups[0])
        assert score > 50

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_headwind_decreases_score(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        optimizer.weather_data["r1"] = {
            'avg_headwind_kph': 20,
            'avg_crosswind_kph': 0,
        }
        optimizer.enable_weather = True
        score = optimizer.calculate_weather_score(groups[0])
        assert score < 50

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_score_clamped_to_0_100(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        optimizer.weather_data["r1"] = {
            'avg_headwind_kph': 100,
            'avg_crosswind_kph': 50,
        }
        optimizer.enable_weather = True
        score = optimizer.calculate_weather_score(groups[0])
        assert 0 <= score <= 100


class TestTimeScore:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_fastest_route_gets_highest_score(self, mock_wind, mock_weather):
        g1 = _make_group("fast", duration=600)
        g2 = _make_group("slow", duration=2400)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        fast_score = optimizer.calculate_time_score(optimizer.metrics["fast"])
        slow_score = optimizer.calculate_time_score(optimizer.metrics["slow"])
        assert fast_score > slow_score

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_single_route_gets_max_score(self, mock_wind, mock_weather):
        groups = [_make_group("only")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        score = optimizer.calculate_time_score(optimizer.metrics["only"])
        assert score == 100


class TestDistanceScore:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_shorter_route_scores_higher(self, mock_wind, mock_weather):
        g1 = _make_group("short", distance=3000)
        g2 = _make_group("long", distance=10000)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        short_score = optimizer.calculate_distance_score(optimizer.metrics["short"])
        long_score = optimizer.calculate_distance_score(optimizer.metrics["long"])
        assert short_score > long_score


class TestSafetyScore:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_more_frequent_route_scores_higher(self, mock_wind, mock_weather):
        g1 = _make_group("frequent", n_routes=20)
        g2 = _make_group("rare", n_routes=2)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        freq_score = optimizer.calculate_safety_score(g1)
        rare_score = optimizer.calculate_safety_score(g2)
        assert freq_score > rare_score


class TestCompositeAndRanking:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_rank_routes_returns_sorted(self, mock_wind, mock_weather):
        g1 = _make_group("best", distance=3000, duration=600, n_routes=20)
        g2 = _make_group("worst", distance=15000, duration=3600, n_routes=1, elevation=500)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        ranked = optimizer.rank_routes()
        assert len(ranked) == 2
        assert ranked[0][0].id == "best"
        assert ranked[0][1] >= ranked[1][1]

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_get_optimal_route(self, mock_wind, mock_weather):
        g1 = _make_group("best", distance=3000, duration=600, n_routes=20)
        g2 = _make_group("worst", distance=15000, duration=3600, n_routes=1)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        group, score, breakdown = optimizer.get_optimal_route()
        assert group.id == "best"
        assert 'time' in breakdown
        assert 'distance' in breakdown
        assert 'safety' in breakdown
        assert 'weather' in breakdown

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_get_optimal_route_raises_when_empty(self, mock_wind, mock_weather):
        optimizer = RouteOptimizer([], _make_config(), enable_weather=False)
        with pytest.raises(ValueError, match="No routes"):
            optimizer.get_optimal_route()


class TestRecommendations:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_get_recommendations_includes_optimal(self, mock_wind, mock_weather):
        g1 = _make_group("r1", distance=3000, duration=600, n_routes=10)
        g2 = _make_group("r2", distance=8000, duration=1500, n_routes=5)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        recs = optimizer.get_route_recommendations()
        assert 'optimal' in recs
        assert recs['optimal']['id'] in ("r1", "r2")
        assert 'reason' in recs['optimal']

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_get_recommendations_includes_alternative(self, mock_wind, mock_weather):
        g1 = _make_group("r1")
        g2 = _make_group("r2", distance=8000, duration=1500)
        optimizer = RouteOptimizer([g1, g2], _make_config(), enable_weather=False)
        recs = optimizer.get_route_recommendations()
        assert 'alternative' in recs

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_empty_routes_returns_error(self, mock_wind, mock_weather):
        optimizer = RouteOptimizer([], _make_config(), enable_weather=False)
        recs = optimizer.get_route_recommendations()
        assert 'error' in recs


class TestRecommendationReason:
    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_fast_route_reason(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        reason = optimizer._generate_recommendation_reason({
            'time': 90, 'distance': 50, 'safety': 50, 'weather': 50
        })
        assert "fastest" in reason

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_headwind_warning_reason(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        reason = optimizer._generate_recommendation_reason({
            'time': 90, 'distance': 50, 'safety': 50, 'weather': 20
        })
        assert "headwind" in reason.lower()

    @patch('src.optimizer.WeatherFetcher')
    @patch('src.optimizer.WindImpactCalculator')
    def test_fallback_reason(self, mock_wind, mock_weather):
        groups = [_make_group("r1")]
        optimizer = RouteOptimizer(groups, _make_config(), enable_weather=False)
        reason = optimizer._generate_recommendation_reason({
            'time': 50, 'distance': 50, 'safety': 50, 'weather': 50
        })
        assert "best overall" in reason
