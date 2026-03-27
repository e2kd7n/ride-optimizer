"""
Unit tests for route_analyzer module.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.route_analyzer import Route, RouteGroup, RouteMetrics, RouteAnalyzer
from src.data_fetcher import Activity


class TestRoute:
    """Test Route dataclass."""
    
    def test_route_creation(self):
        """Test creating a Route instance."""
        route = Route(
            activity_id=12345,
            direction="home_to_work",
            coordinates=[(41.8781, -87.6298), (41.8819, -87.6278)],
            distance=5000.0,
            duration=1200,
            elevation_gain=50.0,
            timestamp=datetime.now(timezone.utc),
            average_speed=4.17,
            is_plus_route=False
        )
        
        assert route.activity_id == 12345
        assert route.direction == "home_to_work"
        assert len(route.coordinates) == 2
        assert route.distance == 5000.0
        assert route.is_plus_route is False


class TestRouteGroup:
    """Test RouteGroup dataclass."""
    
    def test_route_group_creation(self):
        """Test creating a RouteGroup instance."""
        route1 = Route(
            activity_id=1, direction="home_to_work",
            coordinates=[(41.8781, -87.6298), (41.8819, -87.6278)],
            distance=5000.0, duration=1200, elevation_gain=50.0,
            timestamp=datetime.now(timezone.utc), average_speed=4.17,
            is_plus_route=False
        )
        
        group = RouteGroup(
            id="home_to_work_1",
            direction="home_to_work",
            routes=[route1],
            representative_route=route1,
            frequency=1,
            name="Morning Commute",
            is_plus_route=False
        )
        
        assert group.id == "home_to_work_1"
        assert group.frequency == 1
        assert len(group.routes) == 1
        assert group.is_plus_route is False


class TestRouteMetrics:
    """Test RouteMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating RouteMetrics instance."""
        metrics = RouteMetrics(
            avg_duration=1200.0,
            std_duration=60.0,
            avg_distance=5000.0,
            avg_speed=4.17,
            avg_elevation=50.0,
            consistency_score=0.95,
            usage_frequency=10
        )
        
        assert metrics.avg_duration == 1200.0
        assert metrics.consistency_score == 0.95
        assert metrics.usage_frequency == 10


class TestRouteAnalyzer:
    """Test RouteAnalyzer class."""
    
    @pytest.fixture
    def mock_activities(self):
        """Create mock activities for testing."""
        return [
            Activity(
                id=1, name="Morning Commute", type="Ride",
                start_date=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
                distance=5000.0, moving_time=1200, elapsed_time=1300,
                total_elevation_gain=50.0, average_speed=4.17, max_speed=8.0,
                start_latlng=(41.8781, -87.6298),
                end_latlng=(41.8819, -87.6278),
                polyline="encoded_polyline_1"
            ),
            Activity(
                id=2, name="Evening Commute", type="Ride",
                start_date=datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc),
                distance=5100.0, moving_time=1250, elapsed_time=1350,
                total_elevation_gain=55.0, average_speed=4.08, max_speed=7.5,
                start_latlng=(41.8819, -87.6278),
                end_latlng=(41.8781, -87.6298),
                polyline="encoded_polyline_2"
            ),
        ]
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.get = Mock(side_effect=lambda key, default=None: {
            'analysis.similarity_threshold': 0.85,
            'analysis.n_workers': 1,
            'cache.directory': 'cache',
            'cache.enabled': True
        }.get(key, default))
        return config
    
    @pytest.fixture
    def home_location(self):
        """Home location coordinates."""
        return (41.8781, -87.6298)
    
    @pytest.fixture
    def work_location(self):
        """Work location coordinates."""
        return (41.8819, -87.6278)
    
    def test_analyzer_initialization(self, mock_activities, home_location, 
                                    work_location, mock_config):
        """Test RouteAnalyzer initialization."""
        analyzer = RouteAnalyzer(
            mock_activities, home_location, work_location, 
            mock_config, n_workers=1
        )
        
        assert analyzer.activities == mock_activities
        assert analyzer.home == home_location
        assert analyzer.work == work_location
        assert analyzer.config == mock_config
    
    def test_determine_direction(self, mock_activities, home_location,
                                work_location, mock_config):
        """Test route direction determination."""
        analyzer = RouteAnalyzer(
            mock_activities, home_location, work_location,
            mock_config, n_workers=1
        )
        
        # First activity: home to work
        direction1 = analyzer._determine_direction(mock_activities[0])
        assert direction1 == "home_to_work"
        
        # Second activity: work to home
        direction2 = analyzer._determine_direction(mock_activities[1])
        assert direction2 == "work_to_home"
    
    @patch('polyline.decode')
    def test_extract_routes(self, mock_decode, mock_activities, home_location,
                           work_location, mock_config):
        """Test route extraction from activities."""
        mock_decode.return_value = [
            (41.8781, -87.6298),
            (41.8800, -87.6288),
            (41.8819, -87.6278)
        ]
        
        analyzer = RouteAnalyzer(
            mock_activities, home_location, work_location,
            mock_config, n_workers=1
        )
        
        routes = analyzer.extract_routes("home_to_work")
        
        assert isinstance(routes, list)
        # Should extract routes going from home to work
        assert all(isinstance(r, Route) for r in routes)
    
    def test_calculate_route_metrics(self, home_location, work_location, mock_config):
        """Test route metrics calculation."""
        routes = [
            Route(
                activity_id=i, direction="home_to_work",
                coordinates=[(41.8781, -87.6298), (41.8819, -87.6278)],
                distance=5000.0 + i*100, duration=1200 + i*10,
                elevation_gain=50.0, timestamp=datetime.now(timezone.utc),
                average_speed=4.17, is_plus_route=False
            )
            for i in range(5)
        ]
        
        group = RouteGroup(
            id="test_group", direction="home_to_work",
            routes=routes, representative_route=routes[0],
            frequency=5, name="Test Route", is_plus_route=False
        )
        
        analyzer = RouteAnalyzer(
            [], home_location, work_location, mock_config, n_workers=1
        )
        
        metrics = analyzer.calculate_route_metrics(group)
        
        assert isinstance(metrics, RouteMetrics)
        assert metrics.avg_duration > 0
        assert metrics.avg_distance > 0
        assert metrics.usage_frequency == 5
        assert 0 <= metrics.consistency_score <= 1

# Made with Bob
