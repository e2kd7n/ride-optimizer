"""
Unit tests for RouteLibraryService.

Tests route library functionality:
- Route browsing and filtering
- Search capabilities
- Route details retrieval
- Statistics calculation
- Favorite management
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from app.services.route_library_service import RouteLibraryService
from src.route_analyzer import RouteGroup, Route
from src.long_ride_analyzer import LongRide
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock Config object."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'cache_dir': '/tmp/test_cache',
        'data_dir': '/tmp/test_data'
    }.get(key, default))
    return config


@pytest.fixture
def mock_route():
    """Create a mock Route object."""
    route = Mock(spec=Route)
    route.activity_id = 12345
    route.distance = 10000  # meters
    route.duration = 1800  # seconds
    route.elevation_gain = 100
    route.timestamp = datetime(2024, 1, 1, 8, 0)
    route.average_speed = 5.56  # m/s
    route.activity_name = "Morning Commute"
    route.coordinates = [(40.7128, -74.0060), (40.7580, -73.9855)]
    return route


@pytest.fixture
def mock_route_group(mock_route):
    """Create a mock RouteGroup object."""
    group = Mock(spec=RouteGroup)
    group.id = "route_group_1"
    group.name = "Home to Work"
    group.direction = "to_work"
    group.frequency = 25
    group.is_plus_route = False
    group.representative_route = mock_route
    group.routes = [mock_route]
    return group


@pytest.fixture
def mock_long_ride():
    """Create a mock LongRide object."""
    ride = Mock(spec=LongRide)
    ride.activity_id = 67890
    ride.name = "Weekend Century"
    ride.distance = 160000  # meters
    ride.distance_km = 160.0
    ride.duration_hours = 5.5
    ride.elevation_gain = 1500
    ride.uses = 3
    ride.is_loop = True
    ride.coordinates = [(40.7128, -74.0060), (40.7580, -73.9855)]
    ride.start_location = (40.7128, -74.0060)
    ride.end_location = (40.7128, -74.0060)
    ride.average_speed = 8.08  # m/s
    ride.activity_ids = [67890, 67891, 67892]
    ride.activity_dates = ["2024-01-15", "2024-02-20", "2024-03-10"]
    ride.type = "loop"
    return ride


@pytest.fixture
def route_library_service(mock_config):
    """Create a RouteLibraryService instance."""
    return RouteLibraryService(mock_config)


@pytest.fixture
def initialized_service(route_library_service, mock_route_group, mock_long_ride):
    """Create an initialized RouteLibraryService with test data."""
    route_library_service.initialize([mock_route_group], [mock_long_ride])
    return route_library_service


class TestRouteLibraryServiceInitialization:
    """Test service initialization."""
    
    def test_init_creates_service(self, mock_config):
        """Test that service can be created."""
        service = RouteLibraryService(mock_config)
        assert service is not None
        assert service.config == mock_config
        assert service._route_groups is None
        assert service._long_rides is None
        assert len(service._favorites) == 0
    
    def test_initialize_sets_data(self, route_library_service, mock_route_group, mock_long_ride):
        """Test that initialize sets route data."""
        route_library_service.initialize([mock_route_group], [mock_long_ride])
        assert route_library_service._route_groups == [mock_route_group]
        assert route_library_service._long_rides == [mock_long_ride]


class TestGetAllRoutes:
    """Test get_all_routes functionality."""
    
    def test_get_all_routes_uninitialized(self, route_library_service):
        """Test getting routes when service not initialized."""
        result = route_library_service.get_all_routes()
        assert result['status'] == 'error'
        assert 'not initialized' in result['message']
        assert result['routes'] == []
        assert result['total_count'] == 0
    
    def test_get_all_routes_success(self, initialized_service):
        """Test getting all routes successfully."""
        result = initialized_service.get_all_routes()
        assert result['status'] == 'success'
        assert len(result['routes']) == 2  # 1 commute + 1 long ride
        assert result['total_count'] == 2
        assert result['filters']['type'] == 'all'
        assert result['filters']['sort_by'] == 'uses'
    
    def test_get_commute_routes_only(self, initialized_service):
        """Test filtering for commute routes only."""
        result = initialized_service.get_all_routes(route_type='commute')
        assert result['status'] == 'success'
        assert len(result['routes']) == 1
        assert result['routes'][0]['type'] == 'commute'
        assert result['routes'][0]['name'] == 'Home to Work'
    
    def test_get_long_rides_only(self, initialized_service):
        """Test filtering for long rides only."""
        result = initialized_service.get_all_routes(route_type='long_ride')
        assert result['status'] == 'success'
        assert len(result['routes']) == 1
        assert result['routes'][0]['type'] == 'long_ride'
        assert result['routes'][0]['name'] == 'Weekend Century'
    
    def test_sort_by_distance(self, initialized_service):
        """Test sorting routes by distance."""
        result = initialized_service.get_all_routes(sort_by='distance')
        assert result['status'] == 'success'
        # Long ride (160km) should be first
        assert result['routes'][0]['type'] == 'long_ride'
        assert result['routes'][0]['distance'] == 160.0
    
    def test_sort_by_name(self, initialized_service):
        """Test sorting routes by name."""
        result = initialized_service.get_all_routes(sort_by='name')
        assert result['status'] == 'success'
        # "Home to Work" comes before "Weekend Century" alphabetically
        assert result['routes'][0]['name'] == 'Home to Work'
    
    def test_limit_results(self, initialized_service):
        """Test limiting number of results."""
        result = initialized_service.get_all_routes(limit=1)
        assert result['status'] == 'success'
        assert len(result['routes']) == 1
    
    def test_get_all_routes_error_handling(self, initialized_service):
        """Test error handling in get_all_routes."""
        # Force an error by making _route_groups raise exception
        initialized_service._route_groups = None
        initialized_service._long_rides = Mock()
        initialized_service._long_rides.__iter__ = Mock(side_effect=Exception("Test error"))
        
        result = initialized_service.get_all_routes()
        assert result['status'] == 'error'
        assert 'Failed to retrieve routes' in result['message']


class TestSearchRoutes:
    """Test search_routes functionality."""
    
    def test_search_uninitialized(self, route_library_service):
        """Test search when service not initialized."""
        result = route_library_service.search_routes("test")
        assert result['status'] == 'error'
        assert 'not initialized' in result['message']
        assert result['results'] == []
        assert result['count'] == 0
    
    def test_search_commute_route(self, initialized_service):
        """Test searching for commute route."""
        result = initialized_service.search_routes("Home")
        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['name'] == 'Home to Work'
    
    def test_search_long_ride(self, initialized_service):
        """Test searching for long ride."""
        result = initialized_service.search_routes("Century")
        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['name'] == 'Weekend Century'
    
    def test_search_case_insensitive(self, initialized_service):
        """Test that search is case insensitive."""
        result = initialized_service.search_routes("WEEKEND")
        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['name'] == 'Weekend Century'
    
    def test_search_no_results(self, initialized_service):
        """Test search with no matching results."""
        result = initialized_service.search_routes("NonexistentRoute")
        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['results'] == []
    
    def test_search_with_limit(self, initialized_service, mock_route):
        """Test search with result limit."""
        # Add more routes to test limit
        mock_group2 = Mock(spec=RouteGroup)
        mock_group2.id = "route_group_2"
        mock_group2.name = "Home to Gym"
        mock_group2.direction = "to_gym"
        mock_group2.frequency = 10
        mock_group2.is_plus_route = False
        mock_group2.representative_route = mock_route
        mock_group2.routes = [mock_route]
        initialized_service._route_groups.append(mock_group2)
        
        result = initialized_service.search_routes("Home", limit=1)
        assert result['status'] == 'success'
        assert result['count'] == 1
    
    def test_search_error_handling(self, initialized_service):
        """Test error handling in search."""
        # Force an error
        initialized_service._route_groups = Mock()
        initialized_service._route_groups.__iter__ = Mock(side_effect=Exception("Test error"))
        
        result = initialized_service.search_routes("test")
        assert result['status'] == 'error'
        assert 'Search failed' in result['message']


class TestGetRouteDetails:
    """Test get_route_details functionality."""
    
    def test_get_commute_route_details(self, initialized_service):
        """Test getting commute route details."""
        result = initialized_service.get_route_details("route_group_1", "commute")
        assert result['status'] == 'success'
        assert result['route']['id'] == "route_group_1"
        assert result['route']['name'] == 'Home to Work'
        assert 'routes' in result['route']  # Detailed view includes routes list
        assert 'coordinates' in result['route']
    
    def test_get_long_ride_details(self, initialized_service):
        """Test getting long ride details."""
        result = initialized_service.get_route_details("67890", "long_ride")
        assert result['status'] == 'success'
        assert result['route']['id'] == "67890"
        assert result['route']['name'] == 'Weekend Century'
        assert 'coordinates' in result['route']
        assert 'start_location' in result['route']
        assert 'end_location' in result['route']
    
    def test_get_route_details_not_found(self, initialized_service):
        """Test getting details for non-existent route."""
        result = initialized_service.get_route_details("nonexistent", "commute")
        assert result['status'] == 'error'
        assert 'not found' in result['message']


class TestGetRouteStatistics:
    """Test get_route_statistics functionality."""
    
    def test_get_statistics_empty(self, route_library_service):
        """Test statistics with no routes."""
        stats = route_library_service.get_route_statistics()
        assert stats['total_routes'] == 0
        assert stats['commute_routes'] == 0
        assert stats['long_rides'] == 0
        assert stats['total_distance'] == 0.0
        assert stats['total_activities'] == 0
        assert stats['most_used_route'] is None
        assert stats['longest_ride'] is None
    
    def test_get_statistics_with_routes(self, initialized_service):
        """Test statistics with routes."""
        stats = initialized_service.get_route_statistics()
        assert stats['total_routes'] == 2
        assert stats['commute_routes'] == 1
        assert stats['long_rides'] == 1
        assert stats['total_activities'] == 28  # 25 commutes + 3 long rides
        assert stats['total_distance'] > 0
    
    def test_most_used_route(self, initialized_service):
        """Test most used route calculation."""
        stats = initialized_service.get_route_statistics()
        assert stats['most_used_route'] is not None
        assert stats['most_used_route']['id'] == "route_group_1"
        assert stats['most_used_route']['uses'] == 25
        assert stats['most_used_route']['type'] == 'commute'
    
    def test_longest_ride(self, initialized_service):
        """Test longest ride calculation."""
        stats = initialized_service.get_route_statistics()
        assert stats['longest_ride'] is not None
        assert stats['longest_ride']['id'] == 67890
        assert stats['longest_ride']['distance'] == 160.0
        assert stats['longest_ride']['type'] == 'long_ride'


class TestFavoriteManagement:
    """Test favorite route management."""
    
    def test_toggle_favorite_add(self, initialized_service):
        """Test adding route to favorites."""
        result = initialized_service.toggle_favorite("route_group_1", True)
        assert result['status'] == 'success'
        assert result['route_id'] == "route_group_1"
        assert result['is_favorite'] is True
        assert "route_group_1" in initialized_service._favorites
    
    def test_toggle_favorite_remove(self, initialized_service):
        """Test removing route from favorites."""
        # First add it
        initialized_service.toggle_favorite("route_group_1", True)
        # Then remove it
        result = initialized_service.toggle_favorite("route_group_1", False)
        assert result['status'] == 'success'
        assert result['is_favorite'] is False
        assert "route_group_1" not in initialized_service._favorites
    
    def test_get_favorites_empty(self, initialized_service):
        """Test getting favorites when none exist."""
        result = initialized_service.get_favorites()
        assert result['status'] == 'success'
        assert result['count'] == 0
        assert result['favorites'] == []
    
    def test_get_favorites_with_routes(self, initialized_service):
        """Test getting favorite routes."""
        # Add favorites
        initialized_service.toggle_favorite("route_group_1", True)
        initialized_service.toggle_favorite("67890", True)
        
        result = initialized_service.get_favorites()
        assert result['status'] == 'success'
        assert result['count'] == 2
        assert len(result['favorites']) == 2
    
    def test_favorite_status_in_route_list(self, initialized_service):
        """Test that favorite status appears in route listings."""
        # Add a favorite
        initialized_service.toggle_favorite("route_group_1", True)
        
        result = initialized_service.get_all_routes()
        commute_route = next(r for r in result['routes'] if r['type'] == 'commute')
        long_ride = next(r for r in result['routes'] if r['type'] == 'long_ride')
        
        assert commute_route['is_favorite'] is True
        assert long_ride['is_favorite'] is False


class TestRouteFormatting:
    """Test route formatting methods."""
    
    def test_format_commute_route(self, initialized_service, mock_route_group):
        """Test commute route formatting."""
        formatted = initialized_service._format_commute_route(mock_route_group)
        assert formatted['id'] == "route_group_1"
        assert formatted['type'] == 'commute'
        assert formatted['name'] == 'Home to Work'
        assert formatted['direction'] == 'to_work'
        assert formatted['distance'] == 10.0  # km
        assert formatted['duration'] == 30.0  # minutes
        assert formatted['elevation'] == 100
        assert formatted['uses'] == 25
        assert formatted['is_plus_route'] is False
        assert 'is_favorite' in formatted
    
    def test_format_long_ride(self, initialized_service, mock_long_ride):
        """Test long ride formatting."""
        formatted = initialized_service._format_long_ride(mock_long_ride)
        assert formatted['id'] == "67890"
        assert formatted['type'] == 'long_ride'
        assert formatted['name'] == 'Weekend Century'
        assert formatted['distance'] == 160.0
        assert formatted['duration'] == 330.0  # 5.5 hours * 60
        assert formatted['elevation'] == 1500
        assert formatted['uses'] == 3
        assert formatted['is_loop'] is True
        assert 'is_favorite' in formatted
    
    def test_format_commute_route_detailed(self, initialized_service, mock_route_group):
        """Test detailed commute route formatting."""
        formatted = initialized_service._format_commute_route_detailed(mock_route_group)
        assert 'routes' in formatted
        assert 'coordinates' in formatted
        assert len(formatted['routes']) == 1
        assert formatted['routes'][0]['activity_id'] == 12345
    
    def test_format_long_ride_detailed(self, initialized_service, mock_long_ride):
        """Test detailed long ride formatting."""
        formatted = initialized_service._format_long_ride_detailed(mock_long_ride)
        assert 'coordinates' in formatted
        assert 'start_location' in formatted
        assert 'end_location' in formatted
        assert 'average_speed' in formatted
        assert 'activity_ids' in formatted
        assert 'activity_dates' in formatted
        assert 'ride_type' in formatted


class TestRouteSorting:
    """Test route sorting functionality."""
    
    def test_sort_by_uses(self, initialized_service):
        """Test sorting by usage count."""
        routes = [
            {'name': 'Route A', 'uses': 5, 'distance': 10},
            {'name': 'Route B', 'uses': 10, 'distance': 20},
            {'name': 'Route C', 'uses': 3, 'distance': 15}
        ]
        sorted_routes = initialized_service._sort_routes(routes, 'uses')
        assert sorted_routes[0]['uses'] == 10
        assert sorted_routes[1]['uses'] == 5
        assert sorted_routes[2]['uses'] == 3
    
    def test_sort_by_distance(self, initialized_service):
        """Test sorting by distance."""
        routes = [
            {'name': 'Route A', 'uses': 5, 'distance': 10},
            {'name': 'Route B', 'uses': 10, 'distance': 20},
            {'name': 'Route C', 'uses': 3, 'distance': 15}
        ]
        sorted_routes = initialized_service._sort_routes(routes, 'distance')
        assert sorted_routes[0]['distance'] == 20
        assert sorted_routes[1]['distance'] == 15
        assert sorted_routes[2]['distance'] == 10
    
    def test_sort_by_name(self, initialized_service):
        """Test sorting by name."""
        routes = [
            {'name': 'Charlie', 'uses': 5, 'distance': 10},
            {'name': 'Alpha', 'uses': 10, 'distance': 20},
            {'name': 'Bravo', 'uses': 3, 'distance': 15}
        ]
        sorted_routes = initialized_service._sort_routes(routes, 'name')
        assert sorted_routes[0]['name'] == 'Alpha'
        assert sorted_routes[1]['name'] == 'Bravo'
        assert sorted_routes[2]['name'] == 'Charlie'
    
    def test_sort_default(self, initialized_service):
        """Test default sorting (no change)."""
        routes = [
            {'name': 'Route A', 'uses': 5, 'distance': 10},
            {'name': 'Route B', 'uses': 10, 'distance': 20}
        ]
        sorted_routes = initialized_service._sort_routes(routes, 'recent')
        assert sorted_routes == routes  # Order unchanged


# Made with Bob