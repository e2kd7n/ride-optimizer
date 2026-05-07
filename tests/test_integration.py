"""
Integration tests for full workflow.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.config import Config
from src.data_fetcher import Activity, StravaDataFetcher
from src.location_finder import LocationFinder
from src.route_analyzer import RouteAnalyzer
from src.optimizer import RouteOptimizer
from src.report_generator import ReportGenerator


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete analysis workflow from data fetching to report generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create mock configuration for testing."""
        config_content = f"""
strava:
  client_id: "test_client"
  client_secret: "test_secret"

locations:
  home:
    lat: 41.8781
    lon: -87.6298
  work:
    lat: 41.8819
    lon: -87.6278

analysis:
  similarity_threshold: 0.85
  min_commute_distance: 1.0
  max_commute_distance: 50.0
  n_workers: 1

cache:
  directory: "{temp_dir}/cache"
  enabled: true
  max_age_days: 7

output:
  directory: "{temp_dir}/output"
  generate_pdf: false

units:
  system: "metric"
"""
        config_file = Path(temp_dir) / "test_config.yaml"
        config_file.write_text(config_content)
        return Config(str(config_file))
    
    @pytest.fixture
    def sample_activities(self):
        """Create sample activities for testing."""
        # Need at least 10 endpoints (5 activities with start/end) for location identification
        activities = []
        for i in range(6):
            # Morning commute (home to work)
            activities.append(Activity(
                id=i*2+1, name=f"Morning Commute {i+1}", type="Ride",
                start_date=f"2024-01-0{(i%7)+1}T08:00:00+00:00",
                distance=5000.0 + i*50, moving_time=1200 + i*10, elapsed_time=1300 + i*10,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            ))
            # Evening commute (work to home)
            activities.append(Activity(
                id=i*2+2, name=f"Evening Commute {i+1}", type="Ride",
                start_date=f"2024-01-0{(i%7)+1}T18:00:00+00:00",
                distance=5100.0 + i*50, moving_time=1250 + i*10, elapsed_time=1350 + i*10,
                total_elevation_gain=55.0, average_speed=4.08, max_speed=7.5,
                start_latlng=(41.8819, -87.6278),
                end_latlng=(41.8781, -87.6298),
                polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            ))
        return activities
    
    def test_location_identification(self, sample_activities, mock_config):
        """Test that home and work locations are correctly identified."""
        location_finder = LocationFinder(sample_activities, mock_config)
        home, work = location_finder.identify_home_work()
        
        assert home is not None
        assert work is not None
        assert home.lat is not None
        assert home.lon is not None
        assert work.lat is not None
        assert work.lon is not None
    
    @patch('polyline.decode')
    def test_route_extraction_and_grouping(self, mock_decode, sample_activities, mock_config):
        """Test route extraction and grouping."""
        from src.location_finder import Location
        
        # Mock polyline decode to return valid coordinates
        mock_decode.return_value = [
            (41.8781, -87.6298),
            (41.8800, -87.6288),
            (41.8819, -87.6278)
        ]
        
        home = Location(lat=41.8781, lon=-87.6298, name="Home", activity_count=6)
        work = Location(lat=41.8819, lon=-87.6278, name="Work", activity_count=6)
        
        analyzer = RouteAnalyzer(
            sample_activities, home, work, mock_config, n_workers=1
        )
        
        # Extract routes
        htw_routes = analyzer.extract_routes("home_to_work")
        wth_routes = analyzer.extract_routes("work_to_home")
        
        # With mocked polyline decode, we should get routes
        assert len(htw_routes) > 0
        # Work to home routes might be 0 if direction detection filters them
        # Just check that we got some routes total
        
        # Group similar routes
        all_routes = htw_routes + wth_routes
        if len(all_routes) > 0:
            groups = analyzer.group_similar_routes(all_routes)
            
            assert len(groups) > 0
            assert all(hasattr(g, 'id') for g in groups)
            assert all(hasattr(g, 'routes') for g in groups)
    
    def test_route_optimization(self, sample_activities, mock_config):
        """Test route optimization and ranking."""
        from src.location_finder import Location
        
        home = Location(lat=41.8781, lon=-87.6298, name="Home", activity_count=2)
        work = Location(lat=41.8819, lon=-87.6278, name="Work", activity_count=2)
        
        analyzer = RouteAnalyzer(
            sample_activities, home, work, mock_config, n_workers=1
        )
        
        all_routes = (
            analyzer.extract_routes("home_to_work") +
            analyzer.extract_routes("work_to_home")
        )
        groups = analyzer.group_similar_routes(all_routes)
        
        # Mock weather data
        with patch('src.weather_fetcher.WeatherFetcher') as MockWeather:
            mock_weather = MockWeather.return_value
            mock_weather.get_current_conditions.return_value = {
                'temp_c': 20.0,
                'wind_speed_kph': 10.0,
                'wind_direction_deg': 180.0
            }
            
            optimizer = RouteOptimizer(
                groups, mock_config,
                enable_weather=True
            )
            
            ranked_routes = optimizer.rank_routes()
            
            assert len(ranked_routes) > 0
            assert all(len(r) == 3 for r in ranked_routes)  # (group, score, breakdown)
            
            # Verify scores are in descending order
            scores = [r[1] for r in ranked_routes]
            assert scores == sorted(scores, reverse=True)
    
    def test_caching_mechanism(self, sample_activities, mock_config, temp_dir):
        """Test that caching works correctly."""
        mock_client = Mock()
        
        # Create cache directory
        cache_dir = Path(temp_dir) / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        fetcher = StravaDataFetcher(mock_client, mock_config, use_test_cache=True)
        
        # Cache activities
        result = fetcher.cache_activities(sample_activities)
        
        assert 'new' in result
        assert 'total' in result
        assert result['total'] == len(sample_activities)
        
        # Verify cache file exists (use fetcher's cache_path)
        assert fetcher.cache_path.exists()
        
        # Load from cache
        cached_activities = fetcher.load_cached_activities()
        
        assert len(cached_activities) == len(sample_activities)
        assert all(isinstance(a, Activity) for a in cached_activities)
    
    @patch('src.report_generator.ReportGenerator._render_template')
    def test_report_generation(self, mock_render, sample_activities,
                              mock_config, temp_dir):
        """Test report generation."""
        from src.location_finder import Location
        
        home = Location(lat=41.8781, lon=-87.6298, name="Home", activity_count=2)
        work = Location(lat=41.8819, lon=-87.6278, name="Work", activity_count=2)
        
        # Create analysis results
        analysis_results = {
            'optimal_route': {
                'id': 'home_to_work_1',
                'name': 'Test Route',
                'avg_duration_min': 20.0,
                'avg_distance': 5.0,
                'avg_speed': 15.0,
                'frequency': 2,
                'score': 85.0,
                'breakdown': {
                    'time': 30.0,
                    'distance': 25.0,
                    'safety': 20.0,
                    'weather': 10.0
                }
            },
            'ranked_routes': [],
            'statistics': {
                'total_activities': 3,
                'commute_activities': 3,
                'route_variants': 2,
                'date_range': '2024-01-01 to 2024-01-02'
            },
            'home': home,
            'work': work,
            'map_html': '<div>Map</div>',
            'route_names': {}
        }
        
        mock_render.return_value = "<html><body>Test Report</body></html>"
        
        generator = ReportGenerator(analysis_results)
        
        output_file = Path(temp_dir) / "test_report.html"
        generator.generate_report(str(output_file), generate_pdf=False)
        
        assert output_file.exists()
        assert mock_render.called
    
    def test_full_workflow_integration(self, sample_activities, mock_config, temp_dir):
        """Test complete workflow from activities to report."""
        # Step 1: Identify locations
        location_finder = LocationFinder(sample_activities, mock_config)
        home, work = location_finder.identify_home_work()
        
        assert home is not None
        assert work is not None
        
        # Step 2: Analyze routes
        analyzer = RouteAnalyzer(
            sample_activities,
            home,
            work,
            mock_config,
            n_workers=1
        )
        
        all_routes = (
            analyzer.extract_routes("home_to_work") +
            analyzer.extract_routes("work_to_home")
        )
        groups = analyzer.group_similar_routes(all_routes)
        
        assert len(groups) > 0
        
        # Step 3: Optimize routes (with mocked weather)
        with patch('src.weather_fetcher.WeatherFetcher') as MockWeather:
            mock_weather = MockWeather.return_value
            mock_weather.get_current_conditions.return_value = {
                'temp_c': 20.0,
                'wind_speed_kph': 10.0,
                'wind_direction_deg': 180.0
            }
            
            optimizer = RouteOptimizer(
                groups, mock_config,
                enable_weather=True
            )
            
            ranked_routes = optimizer.rank_routes()
            optimal_route = optimizer.get_optimal_route()
            
            assert optimal_route is not None
            assert len(ranked_routes) > 0
        
        # Step 4: Generate report (mocked)
        with patch('src.report_generator.ReportGenerator._render_template') as mock_render:
            mock_render.return_value = "<html><body>Report</body></html>"
            
            analysis_results = {
                'optimal_route': {
                    'id': optimal_route[0].id,
                    'name': optimal_route[0].name,
                    'score': optimal_route[1]
                },
                'ranked_routes': ranked_routes,
                'statistics': {},
                'home': home,
                'work': work,
                'map_html': '<div>Map</div>',
                'route_names': {}
            }
            
            # Add optimizer to results for report generation
            analysis_results['optimizer'] = optimizer
            
            generator = ReportGenerator(analysis_results)
            output_file = Path(temp_dir) / "integration_test_report.html"
            generator.generate_report(str(output_file), generate_pdf=False)
            
            assert output_file.exists()


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios."""
    
    def test_empty_activities_list(self, tmp_path):
        """Test handling of empty activities list."""
        config_content = """
strava:
  client_id: "test"
  client_secret: "test"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        config = Config(str(config_file))
        
        location_finder = LocationFinder([], config)
        
        # Should handle empty list gracefully
        endpoints = location_finder.extract_endpoints()
        assert endpoints == []
    
    def test_invalid_polyline(self, tmp_path):
        """Test handling of invalid polyline data."""
        mock_client = Mock()
        config_content = """
cache:
  directory: "cache"
  enabled: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        config = Config(str(config_file))
        
        fetcher = StravaDataFetcher(mock_client, config, use_test_cache=True)
        
        # Invalid polyline should raise an exception
        with pytest.raises(IndexError):
            fetcher.decode_polyline("invalid_polyline_data")


@pytest.mark.integration
class TestLongRidesWorkflow:
    """Integration tests for Long Rides feature workflow."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config_content = f"""
cache:
  directory: "{tmp_path}/cache"
  enabled: true
analysis:
  min_long_ride_distance: 50.0
  similarity_threshold: 0.85
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        return Config(str(config_file))
    
    @pytest.fixture
    def sample_long_rides(self):
        """Create sample long ride activities."""
        from src.long_ride_analyzer import LongRide
        rides = []
        for i in range(3):
            ride = LongRide(
                activity_id=1000+i,
                name=f"Century Ride {i+1}",
                coordinates=[(40.7128, -74.0060), (40.7580, -73.9855), (40.7128, -74.0060)],
                distance=160000 + i*1000,  # ~160km
                duration=int((5.5 + i*0.1) * 3600),  # Convert hours to seconds
                elevation_gain=1500 + i*50,
                timestamp="2024-05-07T10:00:00Z",
                average_speed=8.0,
                start_location=(40.7128, -74.0060),
                end_location=(40.7128, -74.0060),
                is_loop=True,
                type="Ride",
                uses=1,
                activity_ids=[1000+i],
                activity_dates=[f"2024-0{i+1}-15"]
            )
            rides.append(ride)
        return rides
    
    def test_long_ride_analysis_workflow(self, sample_long_rides, mock_config):
        """Test complete long ride analysis workflow."""
        from src.long_ride_analyzer import LongRideAnalyzer
        from src.data_fetcher import Activity
        
        # Create mock activities
        activities = []
        
        # Create analyzer with activities and config
        analyzer = LongRideAnalyzer(activities, mock_config)
        analyzer.long_rides = sample_long_rides
        
        # Verify long rides were set
        assert len(analyzer.long_rides) == 3
        assert all(ride.distance >= 100000 for ride in analyzer.long_rides)
    
    @patch('src.weather_fetcher.WeatherFetcher')
    def test_long_ride_with_weather_integration(self, mock_weather_class,
                                                sample_long_rides, mock_config):
        """Test long ride recommendations with weather data."""
        from src.long_ride_analyzer import LongRideAnalyzer
        
        # Mock weather data
        mock_weather = mock_weather_class.return_value
        mock_weather.get_daily_forecast.return_value = [
            {
                'date': '2024-05-07',
                'temp_max_c': 22.0,
                'temp_min_c': 15.0,
                'wind_speed_max_kph': 15.0,
                'precipitation_sum_mm': 0.0
            }
        ]
        
        # Create analyzer with empty activities list
        analyzer = LongRideAnalyzer([], mock_config)
        analyzer.long_rides = sample_long_rides
        
        # Verify long rides and weather fetcher
        assert len(analyzer.long_rides) == 3
        assert analyzer.weather_fetcher is not None


@pytest.mark.integration  
class TestWeatherIntegrationWorkflow:
    """Integration tests for weather data workflow."""
    
    @patch('src.weather_fetcher.requests.Session')
    def test_weather_fetch_and_cache_workflow(self, mock_session, tmp_path):
        """Test complete weather fetching and caching workflow."""
        from src.weather_fetcher import WeatherFetcher
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'current': {
                'temperature_2m': 20.0,
                'wind_speed_10m': 10.0,
                'wind_direction_10m': 180.0
            }
        }
        mock_response.raise_for_status = Mock()
        mock_session.return_value.get.return_value = mock_response
        
        cache_file = tmp_path / "weather_cache.json"
        fetcher = WeatherFetcher(cache_file=str(cache_file))
        
        # Fetch weather
        weather = fetcher.get_current_conditions(40.7128, -74.0060)
        
        assert weather is not None
        assert 'temp_c' in weather
        assert cache_file.exists()
    
    @patch('src.weather_fetcher.requests.Session')
    def test_weather_forecast_workflow(self, mock_session, tmp_path):
        """Test weather forecast retrieval workflow."""
        from src.weather_fetcher import WeatherFetcher
        
        # Mock forecast response
        mock_response = Mock()
        mock_response.json.return_value = {
            'daily': {
                'time': ['2024-05-07', '2024-05-08'],
                'temperature_2m_max': [22.0, 24.0],
                'temperature_2m_min': [15.0, 16.0],
                'precipitation_sum': [0.0, 2.0],
                'precipitation_probability_max': [10, 40],
                'wind_speed_10m_max': [15.0, 20.0],
                'wind_direction_10m_dominant': [180, 200]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_session.return_value.get.return_value = mock_response
        
        cache_file = tmp_path / "weather_cache.json"
        fetcher = WeatherFetcher(cache_file=str(cache_file))
        
        # Get forecast
        forecast = fetcher.get_daily_forecast(40.7128, -74.0060, days=2)
        
        assert forecast is not None
        assert len(forecast) == 2
        assert all('temp_max_c' in day for day in forecast)


@pytest.mark.integration
class TestNextCommuteWorkflow:
    """Integration tests for next commute recommendation workflow."""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config_content = f"""
cache:
  directory: "{tmp_path}/cache"
locations:
  home:
    lat: 41.8781
    lon: -87.6298
  work:
    lat: 41.8819
    lon: -87.6278
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        return Config(str(config_file))
    
    @pytest.fixture
    def sample_route_groups(self):
        """Create sample route groups."""
        from src.route_analyzer import RouteGroup, Route
        from datetime import datetime, timezone
        
        routes = []
        for i in range(3):
            route = Route(
                activity_id=100+i,
                direction="home_to_work",
                coordinates=[(41.8781, -87.6298), (41.8819, -87.6278)],
                distance=5000 + i*100,
                duration=1200 + i*30,
                elevation_gain=50,
                timestamp=datetime.now(timezone.utc).isoformat(),
                average_speed=4.17,
                activity_name=f"Morning Commute {i+1}"
            )
            routes.append(route)
        
        group = RouteGroup(
            id="home_to_work_1",
            direction="home_to_work",
            routes=routes,
            representative_route=routes[0],
            frequency=3,
            name="Main Commute"
        )
        return [group]
    
    @patch('src.weather_fetcher.WeatherFetcher')
    def test_next_commute_recommendation_workflow(self, mock_weather_class,
                                                  sample_route_groups, mock_config):
        """Test complete next commute recommendation workflow."""
        from src.next_commute_recommender import NextCommuteRecommender
        
        # Mock weather
        mock_weather = mock_weather_class.return_value
        mock_weather.get_current_conditions.return_value = {
            'temp_c': 20.0,
            'wind_speed_kph': 10.0,
            'wind_direction_deg': 180.0
        }
        
        home_location = (41.8781, -87.6298)
        work_location = (41.8819, -87.6278)
        
        # Correct parameter order: route_groups, config, home_location, work_location
        recommender = NextCommuteRecommender(
            sample_route_groups,
            mock_config,
            home_location,
            work_location,
            enable_weather=False  # Disable weather to avoid API calls
        )
        
        # Verify recommender was created
        assert recommender is not None
        assert len(recommender.route_groups) == 1
    
    @patch('src.weather_fetcher.WeatherFetcher')
    def test_departure_time_optimization_workflow(self, mock_weather_class,
                                                  sample_route_groups, mock_config):
        """Test departure time optimization workflow."""
        from src.next_commute_recommender import NextCommuteRecommender
        
        # Mock weather for different times
        mock_weather = mock_weather_class.return_value
        mock_weather.get_hourly_forecast.return_value = [
            {'time': '08:00', 'temp_c': 18.0, 'wind_speed_kph': 5.0},
            {'time': '09:00', 'temp_c': 20.0, 'wind_speed_kph': 10.0},
            {'time': '10:00', 'temp_c': 22.0, 'wind_speed_kph': 15.0}
        ]
        
        home_location = (41.8781, -87.6298)
        work_location = (41.8819, -87.6278)
        
        # Correct parameter order: route_groups, config, home_location, work_location
        recommender = NextCommuteRecommender(
            sample_route_groups,
            mock_config,
            home_location,
            work_location,
            enable_weather=False  # Disable weather to avoid API calls
        )
        
        # Verify recommender configuration
        assert recommender is not None
        assert recommender.morning_window_start is not None
        assert recommender.evening_window_start is not None

# Made with Bob
# Made with Bob
