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
        return [
            Activity(
                id=1, name="Morning Commute 1", type="Ride",
                start_date=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            ),
            Activity(
                id=2, name="Evening Commute 1", type="Ride",
                start_date=datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc),
                distance=5100.0, moving_time=1250, elapsed_time=1350,
                total_elevation_gain=55.0, average_speed=4.08, max_speed=7.5,
                start_latlng=(41.8819, -87.6278),
                end_latlng=(41.8781, -87.6298),
                polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            ),
            Activity(
                id=3, name="Morning Commute 2", type="Ride",
                start_date=datetime(2024, 1, 2, 8, 15, tzinfo=timezone.utc),
                distance=5050.0, moving_time=1220, elapsed_time=1320,
                total_elevation_gain=52.0, average_speed=4.14, max_speed=7.8,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="_p~iF~ps|U_ulLnnqC_mqNvxq`@"
            ),
        ]
    
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
    
    def test_route_extraction_and_grouping(self, sample_activities, mock_config):
        """Test route extraction and grouping."""
        home = (41.8781, -87.6298)
        work = (41.8819, -87.6278)
        
        analyzer = RouteAnalyzer(
            sample_activities, home, work, mock_config, n_workers=1
        )
        
        # Extract routes
        htw_routes = analyzer.extract_routes("home_to_work")
        wth_routes = analyzer.extract_routes("work_to_home")
        
        assert len(htw_routes) > 0
        assert len(wth_routes) > 0
        
        # Group similar routes
        all_routes = htw_routes + wth_routes
        groups = analyzer.group_similar_routes(all_routes)
        
        assert len(groups) > 0
        assert all(hasattr(g, 'id') for g in groups)
        assert all(hasattr(g, 'routes') for g in groups)
    
    def test_route_optimization(self, sample_activities, mock_config):
        """Test route optimization and ranking."""
        home = (41.8781, -87.6298)
        work = (41.8819, -87.6278)
        
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
                groups, mock_config, home, work,
                weather_fetcher=mock_weather
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
        
        fetcher = StravaDataFetcher(mock_client, mock_config)
        
        # Cache activities
        result = fetcher.cache_activities(sample_activities)
        
        assert 'cached_count' in result
        assert 'cache_file' in result
        assert result['cached_count'] == len(sample_activities)
        
        # Verify cache file exists
        cache_file = Path(result['cache_file'])
        assert cache_file.exists()
        
        # Load from cache
        cached_activities = fetcher.load_cached_activities()
        
        assert len(cached_activities) == len(sample_activities)
        assert all(isinstance(a, Activity) for a in cached_activities)
    
    @patch('src.report_generator.ReportGenerator._render_template')
    def test_report_generation(self, mock_render, sample_activities, 
                              mock_config, temp_dir):
        """Test report generation."""
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
            'home': {'lat': 41.8781, 'lon': -87.6298, 'activity_count': 2},
            'work': {'lat': 41.8819, 'lon': -87.6278, 'activity_count': 2},
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
            (home.lat, home.lon),
            (work.lat, work.lon),
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
                (home.lat, home.lon),
                (work.lat, work.lon),
                weather_fetcher=mock_weather
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
                'home': {'lat': home.lat, 'lon': home.lon},
                'work': {'lat': work.lat, 'lon': work.lon},
                'map_html': '<div>Map</div>',
                'route_names': {}
            }
            
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
        
        fetcher = StravaDataFetcher(mock_client, config)
        
        # Invalid polyline should return empty list or handle gracefully
        result = fetcher.decode_polyline("invalid_polyline_data")
        assert isinstance(result, list)

# Made with Bob
