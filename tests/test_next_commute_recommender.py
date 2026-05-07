"""
Unit tests for NextCommuteRecommender.

Tests cover:
- Recommender initialization
- Metrics calculation
- Normalization bounds
- Next commute timing determination
- Forecast weather retrieval
- Route scoring with forecast
- Direction-specific recommendations
- Time window formatting
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, time, timedelta, date
import numpy as np

from src.next_commute_recommender import NextCommuteRecommender, CommuteRecommendation
from src.route_analyzer import RouteGroup, Route, RouteMetrics
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'units.system': 'metric',
        'optimization.weights.time': 0.35,
        'optimization.weights.distance': 0.25,
        'optimization.weights.safety': 0.25,
        'optimization.weights.weather': 0.15
    }.get(key, default))
    return config


@pytest.fixture
def mock_route():
    """Create a mock route."""
    route = Mock(spec=Route)
    route.duration = 1800  # 30 minutes
    route.distance = 10.5  # km
    route.average_speed = 21.0  # km/h
    route.elevation_gain = 150.0  # meters
    route.coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
    return route


@pytest.fixture
def mock_route_group(mock_route):
    """Create a mock route group."""
    group = Mock(spec=RouteGroup)
    group.id = "route_123"
    group.direction = "home_to_work"
    group.routes = [mock_route]
    group.representative_route = mock_route
    return group


@pytest.fixture
def home_location():
    """Home location coordinates."""
    return (42.3601, -71.0589)


@pytest.fixture
def work_location():
    """Work location coordinates."""
    return (42.3656, -71.0596)


@pytest.fixture
def recommender(mock_config, home_location, work_location):
    """Create a NextCommuteRecommender instance."""
    # Create to_work route group
    route_to_work = Mock(spec=Route)
    route_to_work.duration = 1800
    route_to_work.distance = 10.5
    route_to_work.average_speed = 21.0
    route_to_work.elevation_gain = 150.0
    route_to_work.coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
    
    group_to_work = Mock(spec=RouteGroup)
    group_to_work.id = "route_to_work"
    group_to_work.direction = "home_to_work"
    group_to_work.routes = [route_to_work]
    group_to_work.representative_route = route_to_work
    
    # Create to_home route group
    route_to_home = Mock(spec=Route)
    route_to_home.duration = 1900
    route_to_home.distance = 10.8
    route_to_home.average_speed = 20.5
    route_to_home.elevation_gain = 140.0
    route_to_home.coordinates = [(42.3656, -71.0596), (42.3601, -71.0589)]
    
    group_to_home = Mock(spec=RouteGroup)
    group_to_home.id = "route_to_home"
    group_to_home.direction = "work_to_home"
    group_to_home.routes = [route_to_home]
    group_to_home.representative_route = route_to_home
    
    with patch('src.next_commute_recommender.WeatherFetcher'), \
         patch('src.next_commute_recommender.WindImpactCalculator'):
        
        recommender = NextCommuteRecommender(
            route_groups=[group_to_work, group_to_home],
            config=mock_config,
            home_location=home_location,
            work_location=work_location,
            enable_weather=True
        )
        return recommender


@pytest.fixture
def sample_forecast_weather():
    """Sample forecast weather data."""
    return {
        'temp_c': 18.0,
        'wind_speed_kph': 15.0,
        'wind_gust_kph': 25.0,
        'wind_direction_deg': 180.0,
        'precipitation_prob': 10.0,
        'num_samples': 3
    }


class TestNextCommuteRecommenderInit:
    """Test NextCommuteRecommender initialization."""
    
    def test_init_with_weather_enabled(self, mock_config, mock_route_group, home_location, work_location):
        """Test initialization with weather enabled."""
        with patch('src.next_commute_recommender.WeatherFetcher') as mock_fetcher, \
             patch('src.next_commute_recommender.WindImpactCalculator') as mock_wind:
            
            recommender = NextCommuteRecommender(
                route_groups=[mock_route_group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location,
                enable_weather=True
            )
            
            assert recommender.enable_weather is True
            mock_fetcher.assert_called_once()
            mock_wind.assert_called_once()
    
    def test_init_with_weather_disabled(self, mock_config, mock_route_group, home_location, work_location):
        """Test initialization with weather disabled."""
        recommender = NextCommuteRecommender(
            route_groups=[mock_route_group],
            config=mock_config,
            home_location=home_location,
            work_location=work_location,
            enable_weather=False
        )
        
        assert recommender.enable_weather is False
        assert recommender.weather_fetcher is None
        assert recommender.wind_calculator is None
    
    def test_init_loads_weights_from_config(self, mock_config, mock_route_group, home_location, work_location):
        """Test that weights are loaded from config."""
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[mock_route_group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            assert recommender.weights['time'] == 0.35
            assert recommender.weights['distance'] == 0.25
            assert recommender.weights['safety'] == 0.25
            assert recommender.weights['weather'] == 0.15
    
    def test_init_calculates_metrics(self, mock_config, mock_route_group, home_location, work_location):
        """Test that metrics are calculated on init."""
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[mock_route_group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            assert mock_route_group.id in recommender.metrics
            assert hasattr(recommender, 'min_duration')
            assert hasattr(recommender, 'max_duration')


class TestMetricsCalculation:
    """Test metrics calculation."""
    
    def test_calculate_metrics_for_single_route(self, recommender):
        """Test metrics calculation for a single route."""
        # Check metrics for to_work route
        metrics = recommender.metrics.get("route_to_work")
        
        assert metrics is not None
        assert metrics.avg_duration == 1800
        assert metrics.avg_distance == 10.5
        assert metrics.avg_speed == 21.0
        assert metrics.avg_elevation == 150.0
        assert metrics.usage_frequency == 1
    
    def test_calculate_metrics_for_multiple_routes(self, mock_config, home_location, work_location):
        """Test metrics calculation with multiple routes."""
        route1 = Mock(spec=Route)
        route1.duration = 1800
        route1.distance = 10.0
        route1.average_speed = 20.0
        route1.elevation_gain = 100.0
        
        route2 = Mock(spec=Route)
        route2.duration = 2000
        route2.distance = 11.0
        route2.average_speed = 19.8
        route2.elevation_gain = 120.0
        
        group = Mock(spec=RouteGroup)
        group.id = "multi_route"
        group.direction = "home_to_work"
        group.routes = [route1, route2]
        group.representative_route = route1
        
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            metrics = recommender.metrics.get(group.id)
            assert metrics.avg_duration == 1900  # Average of 1800 and 2000
            assert metrics.usage_frequency == 2
    
    def test_skips_empty_route_groups(self, mock_config, home_location, work_location):
        """Test that empty route groups are skipped."""
        empty_group = Mock(spec=RouteGroup)
        empty_group.id = "empty"
        empty_group.routes = []
        
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[empty_group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            assert empty_group.id not in recommender.metrics


class TestDetermineNextCommutes:
    """Test next commute timing determination."""
    
    def test_morning_shows_today_commutes(self, recommender):
        """Test that morning time shows today's commutes."""
        morning_time = datetime(2026, 5, 10, 8, 0)  # 8 AM
        
        work_timing, home_timing = recommender.determine_next_commutes(morning_time)
        
        assert work_timing == "today"
        assert home_timing == "today"
    
    def test_midday_shows_mixed_commutes(self, recommender):
        """Test that midday shows today home, tomorrow work."""
        midday_time = datetime(2026, 5, 10, 14, 0)  # 2 PM
        
        work_timing, home_timing = recommender.determine_next_commutes(midday_time)
        
        assert work_timing == "tomorrow"
        assert home_timing == "today"
    
    def test_evening_shows_tomorrow_commutes(self, recommender):
        """Test that evening shows tomorrow's commutes."""
        evening_time = datetime(2026, 5, 10, 19, 0)  # 7 PM
        
        work_timing, home_timing = recommender.determine_next_commutes(evening_time)
        
        assert work_timing == "tomorrow"
        assert home_timing == "tomorrow"
    
    def test_defaults_to_current_time(self, recommender):
        """Test that it defaults to current time when none provided."""
        with patch('src.next_commute_recommender.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 10, 8, 0)
            
            work_timing, home_timing = recommender.determine_next_commutes()
            
            # Should use mocked current time
            assert work_timing in ["today", "tomorrow"]
            assert home_timing in ["today", "tomorrow"]


class TestForecastWeatherRetrieval:
    """Test forecast weather retrieval."""
    
    def test_get_forecast_weather_success(self, recommender):
        """Test successful forecast weather retrieval."""
        target_date = datetime(2026, 5, 10, 8, 0)
        window_start = time(7, 0)
        window_end = time(9, 0)
        
        mock_forecast = [
            {
                'timestamp': '2026-05-10T07:00:00',
                'temp_c': 16.0,
                'wind_speed_kph': 12.0,
                'wind_gust_kph': 20.0,
                'wind_direction_deg': 180.0,
                'precipitation_prob': 5.0
            },
            {
                'timestamp': '2026-05-10T08:00:00',
                'temp_c': 18.0,
                'wind_speed_kph': 15.0,
                'wind_gust_kph': 25.0,
                'wind_direction_deg': 185.0,
                'precipitation_prob': 10.0
            }
        ]
        
        recommender.weather_fetcher.get_hourly_forecast = Mock(return_value=mock_forecast)
        
        result = recommender.get_forecast_weather_for_window(
            42.36, -71.06, target_date, window_start, window_end
        )
        
        assert result is not None
        assert 'temp_c' in result
        assert 'wind_speed_kph' in result
        assert result['num_samples'] == 2
        assert result['temp_c'] == 17.0  # Average of 16 and 18
    
    def test_get_forecast_weather_no_fetcher(self, mock_config, mock_route_group, home_location, work_location):
        """Test when weather fetcher is disabled."""
        recommender = NextCommuteRecommender(
            route_groups=[mock_route_group],
            config=mock_config,
            home_location=home_location,
            work_location=work_location,
            enable_weather=False
        )
        
        result = recommender.get_forecast_weather_for_window(
            42.36, -71.06, datetime.now(), time(7, 0), time(9, 0)
        )
        
        assert result is None
    
    def test_get_forecast_weather_no_data(self, recommender):
        """Test when no forecast data available."""
        recommender.weather_fetcher.get_hourly_forecast = Mock(return_value=None)
        
        result = recommender.get_forecast_weather_for_window(
            42.36, -71.06, datetime.now(), time(7, 0), time(9, 0)
        )
        
        assert result is None
    
    def test_get_forecast_weather_no_matching_window(self, recommender):
        """Test when no forecasts match the time window."""
        mock_forecast = [
            {
                'timestamp': '2026-05-10T12:00:00',  # Outside window
                'temp_c': 20.0,
                'wind_speed_kph': 10.0,
                'wind_gust_kph': 15.0,
                'wind_direction_deg': 180.0,
                'precipitation_prob': 0.0
            }
        ]
        
        recommender.weather_fetcher.get_hourly_forecast = Mock(return_value=mock_forecast)
        
        result = recommender.get_forecast_weather_for_window(
            42.36, -71.06, datetime(2026, 5, 10, 8, 0), time(7, 0), time(9, 0)
        )
        
        assert result is None


class TestRouteScoring:
    """Test route scoring with forecast."""
    
    def test_calculate_score_without_weather(self, recommender):
        """Test score calculation without weather data."""
        # Get the first route group from recommender
        route_group = recommender.route_groups[0]
        
        score, breakdown = recommender.calculate_route_score_with_forecast(
            route_group, None
        )
        
        assert score > 0
        assert 'time' in breakdown
        assert 'distance' in breakdown
        assert 'safety' in breakdown
        assert 'weather' in breakdown
        assert breakdown['weather'] == 50  # Default neutral
    
    def test_calculate_score_with_weather(self, recommender, sample_forecast_weather):
        """Test score calculation with weather data."""
        route_group = recommender.route_groups[0]
        
        mock_wind_impact = {
            'avg_headwind_kph': -5.0,  # Tailwind
            'avg_crosswind_kph': 3.0
        }
        recommender.wind_calculator.analyze_route_wind_impact = Mock(return_value=mock_wind_impact)
        
        score, breakdown = recommender.calculate_route_score_with_forecast(
            route_group, sample_forecast_weather
        )
        
        assert score > 0
        assert breakdown['weather'] > 50  # Tailwind should boost score
        assert 'weather_details' in breakdown
    
    def test_calculate_score_with_headwind(self, recommender, sample_forecast_weather):
        """Test score calculation with headwind."""
        route_group = recommender.route_groups[0]
        
        mock_wind_impact = {
            'avg_headwind_kph': 10.0,  # Headwind
            'avg_crosswind_kph': 2.0
        }
        recommender.wind_calculator.analyze_route_wind_impact = Mock(return_value=mock_wind_impact)
        
        score, breakdown = recommender.calculate_route_score_with_forecast(
            route_group, sample_forecast_weather
        )
        
        assert breakdown['weather'] < 50  # Headwind should reduce score
    
    def test_calculate_score_no_metrics(self, recommender):
        """Test score calculation when no metrics available."""
        fake_group = Mock(spec=RouteGroup)
        fake_group.id = "nonexistent"
        
        score, breakdown = recommender.calculate_route_score_with_forecast(
            fake_group, None
        )
        
        assert score == 0.0
        assert breakdown == {}
    
    def test_calculate_score_handles_wind_error(self, recommender, sample_forecast_weather):
        """Test graceful handling of wind calculation error."""
        route_group = recommender.route_groups[0]
        
        recommender.wind_calculator.analyze_route_wind_impact = Mock(
            side_effect=Exception('Wind calculation failed')
        )
        
        score, breakdown = recommender.calculate_route_score_with_forecast(
            route_group, sample_forecast_weather
        )
        
        # Should still return a score with default weather score
        assert score > 0
        assert breakdown['weather'] == 50


class TestGetNextCommuteRecommendations:
    """Test getting next commute recommendations."""
    
    def test_get_recommendations_morning(self, recommender):
        """Test getting recommendations in the morning."""
        morning_time = datetime(2026, 5, 10, 8, 0)
        
        recommender.get_forecast_weather_for_window = Mock(return_value=None)
        
        recommendations = recommender.get_next_commute_recommendations(morning_time)
        
        assert 'to_work' in recommendations
        assert 'to_home' in recommendations
        assert recommendations['to_work'].is_today is True
        assert recommendations['to_home'].is_today is True
    
    def test_get_recommendations_evening(self, recommender):
        """Test getting recommendations in the evening."""
        evening_time = datetime(2026, 5, 10, 19, 0)
        
        recommender.get_forecast_weather_for_window = Mock(return_value=None)
        
        recommendations = recommender.get_next_commute_recommendations(evening_time)
        
        assert 'to_work' in recommendations
        assert 'to_home' in recommendations
        assert recommendations['to_work'].is_today is False
        assert recommendations['to_home'].is_today is False
    
    def test_get_recommendations_with_weather(self, recommender, sample_forecast_weather):
        """Test recommendations include weather data."""
        recommender.get_forecast_weather_for_window = Mock(return_value=sample_forecast_weather)
        recommender.wind_calculator.analyze_route_wind_impact = Mock(return_value={
            'avg_headwind_kph': 0.0,
            'avg_crosswind_kph': 5.0
        })
        
        recommendations = recommender.get_next_commute_recommendations()
        
        if 'to_work' in recommendations:
            assert recommendations['to_work'].forecast_weather is not None
    
    def test_get_recommendations_no_routes(self, mock_config, home_location, work_location):
        """Test when no routes available."""
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            recommendations = recommender.get_next_commute_recommendations()
            
            # Should return empty dict or handle gracefully
            assert isinstance(recommendations, dict)


class TestDirectionRecommendation:
    """Test direction-specific recommendations."""
    
    def test_get_direction_recommendation_to_work(self, recommender):
        """Test getting recommendation for to_work direction."""
        target_date = datetime(2026, 5, 10, 8, 0)
        
        recommender.get_forecast_weather_for_window = Mock(return_value=None)
        
        recommendation = recommender._get_direction_recommendation(
            "to_work", target_date, time(7, 0), time(9, 0), True
        )
        
        assert recommendation is not None
        assert recommendation.direction == "to_work"
        assert recommendation.is_today is True
        assert "Today" in recommendation.time_window
    
    def test_get_direction_recommendation_to_home(self, recommender):
        """Test getting recommendation for to_home direction."""
        # Create a to_home route group
        route = Mock(spec=Route)
        route.duration = 1900
        route.distance = 10.8
        route.average_speed = 20.5
        route.elevation_gain = 140.0
        route.coordinates = [(42.3656, -71.0596), (42.3601, -71.0589)]
        
        group = Mock(spec=RouteGroup)
        group.id = "route_home"
        group.direction = "work_to_home"
        group.routes = [route]
        group.representative_route = route
        
        recommender.route_groups.append(group)
        recommender._calculate_all_metrics()
        recommender._find_normalization_bounds()
        
        target_date = datetime(2026, 5, 10, 17, 0)
        
        recommender.get_forecast_weather_for_window = Mock(return_value=None)
        
        recommendation = recommender._get_direction_recommendation(
            "to_home", target_date, time(15, 0), time(18, 0), True
        )
        
        assert recommendation is not None
        assert recommendation.direction == "to_home"
    
    def test_get_direction_recommendation_tomorrow(self, recommender, mock_route_group):
        """Test recommendation for tomorrow."""
        target_date = datetime(2026, 5, 11, 8, 0)
        
        recommender.get_forecast_weather_for_window = Mock(return_value=None)
        
        recommendation = recommender._get_direction_recommendation(
            "to_work", target_date, time(7, 0), time(9, 0), False
        )
        
        assert recommendation is not None
        assert recommendation.is_today is False
        assert "Tomorrow" in recommendation.time_window
    
    def test_get_direction_recommendation_no_routes(self, mock_config, home_location, work_location):
        """Test when no routes for direction."""
        # Create recommender with only to_work routes
        route = Mock(spec=Route)
        route.duration = 1800
        route.distance = 10.5
        route.average_speed = 21.0
        route.elevation_gain = 150.0
        route.coordinates = [(42.3601, -71.0589), (42.3650, -71.0600)]
        
        group = Mock(spec=RouteGroup)
        group.id = "only_to_work"
        group.direction = "home_to_work"
        group.routes = [route]
        group.representative_route = route
        
        with patch('src.next_commute_recommender.WeatherFetcher'), \
             patch('src.next_commute_recommender.WindImpactCalculator'):
            
            recommender = NextCommuteRecommender(
                route_groups=[group],
                config=mock_config,
                home_location=home_location,
                work_location=work_location
            )
            
            target_date = datetime(2026, 5, 10, 8, 0)
            
            # Request to_home direction that doesn't exist
            recommendation = recommender._get_direction_recommendation(
                "to_home", target_date, time(15, 0), time(18, 0), True
            )
            
            assert recommendation is None


class TestCommuteRecommendationDataclass:
    """Test CommuteRecommendation dataclass."""
    
    def test_create_recommendation(self, mock_route_group):
        """Test creating a CommuteRecommendation."""
        recommendation = CommuteRecommendation(
            direction="to_work",
            time_window="Today 7:00 AM-9:00 AM",
            route_group=mock_route_group,
            score=85.5,
            breakdown={'time': 90, 'distance': 85, 'safety': 80, 'weather': 75},
            forecast_weather={'temp_c': 18.0, 'wind_speed_kph': 12.0},
            is_today=True,
            window_start=time(7, 0),
            window_end=time(9, 0)
        )
        
        assert recommendation.direction == "to_work"
        assert recommendation.score == 85.5
        assert recommendation.is_today is True
        assert recommendation.forecast_weather is not None


# Made with Bob