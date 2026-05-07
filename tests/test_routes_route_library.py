"""
Unit tests for route_library routes.

Tests route library blueprint endpoints:
- Main library index with filtering and sorting
- Route detail views
- API search endpoint
- API favorite toggle
- API statistics endpoint
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from flask import Flask, g

from app.routes.route_library import bp, get_services


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def mock_config():
    """Create a mock Config object."""
    config = Mock()
    config.get = Mock(side_effect=lambda key, default=None: {
        'cache_dir': '/tmp/test_cache',
        'data_dir': '/tmp/test_data'
    }.get(key, default))
    return config


@pytest.fixture
def mock_route_library_service():
    """Create a mock RouteLibraryService."""
    service = Mock()
    service._favorites = set()
    
    # Mock get_all_routes
    service.get_all_routes.return_value = {
        'status': 'success',
        'routes': [
            {
                'id': 'route_1',
                'name': 'Morning Commute',
                'type': 'commute',
                'distance': 10.0,
                'uses': 25,
                'is_favorite': False
            },
            {
                'id': 'route_2',
                'name': 'Weekend Century',
                'type': 'long_ride',
                'distance': 160.0,
                'uses': 3,
                'is_favorite': False
            }
        ],
        'total_count': 2,
        'filters': {'type': 'all', 'sort_by': 'uses'}
    }
    
    # Mock get_favorites
    service.get_favorites.return_value = {
        'status': 'success',
        'favorites': [],
        'count': 0
    }
    
    # Mock search_routes
    service.search_routes.return_value = {
        'status': 'success',
        'results': [
            {
                'id': 'route_1',
                'name': 'Morning Commute',
                'type': 'commute'
            }
        ],
        'count': 1
    }
    
    # Mock get_route_details
    service.get_route_details.return_value = {
        'status': 'success',
        'route': {
            'id': 'route_1',
            'name': 'Morning Commute',
            'type': 'commute',
            'distance': 10.0
        }
    }
    
    # Mock get_route_statistics
    service.get_route_statistics.return_value = {
        'total_routes': 2,
        'commute_routes': 1,
        'long_rides': 1,
        'total_distance': 170.0,
        'total_activities': 28
    }
    
    # Mock toggle_favorite
    service.toggle_favorite.return_value = {
        'status': 'success',
        'route_id': 'route_1',
        'is_favorite': True
    }
    
    return service


@pytest.fixture
def mock_analysis_service():
    """Create a mock AnalysisService."""
    service = Mock()
    service.get_route_groups.return_value = []
    service.get_long_rides.return_value = []
    return service


@pytest.fixture
def mock_services(mock_route_library_service, mock_analysis_service):
    """Create mock services dict."""
    return {
        'library': mock_route_library_service,
        'analysis': mock_analysis_service
    }


class TestGetServices:
    """Test get_services helper function."""
    
    @patch('app.routes.route_library.AnalysisService')
    @patch('app.routes.route_library.RouteLibraryService')
    @patch('app.routes.route_library.Config')
    def test_get_services_creates_new(self, mock_config_cls, mock_library_cls, mock_analysis_cls, app):
        """Test that get_services creates new services when not in g."""
        with app.app_context():
            # Clear g to ensure fresh start
            if hasattr(g, 'route_library_services'):
                delattr(g, 'route_library_services')
            
            # Mock the service instances
            mock_config = Mock()
            mock_config_cls.return_value = mock_config
            
            mock_analysis = Mock()
            mock_analysis.get_route_groups.return_value = []
            mock_analysis.get_long_rides.return_value = []
            mock_analysis_cls.return_value = mock_analysis
            
            mock_library = Mock()
            mock_library.initialize = Mock()
            mock_library_cls.return_value = mock_library
            
            services = get_services()
            
            assert 'library' in services
            assert 'analysis' in services
            assert services['library'] == mock_library
            assert services['analysis'] == mock_analysis
            mock_library.initialize.assert_called_once()
    
    @patch('app.routes.route_library.AnalysisService')
    @patch('app.routes.route_library.RouteLibraryService')
    @patch('app.routes.route_library.Config')
    def test_get_services_handles_initialization_error(self, mock_config_cls, mock_library_cls,
                                                       mock_analysis_cls, app):
        """Test that get_services handles initialization errors gracefully."""
        with app.app_context():
            # Clear g
            if hasattr(g, 'route_library_services'):
                delattr(g, 'route_library_services')
            
            # Mock services
            mock_config = Mock()
            mock_config_cls.return_value = mock_config
            
            mock_analysis = Mock()
            mock_analysis.get_route_groups.side_effect = Exception("Test error")
            mock_analysis_cls.return_value = mock_analysis
            
            mock_library = Mock()
            mock_library_cls.return_value = mock_library
            
            # Should not raise exception
            services = get_services()
            
            assert 'library' in services
            assert 'analysis' in services
            # Error should be logged (but we can't easily assert on current_app.logger in this context)
    
    @patch('app.routes.route_library.Config')
    def test_get_services_returns_cached(self, mock_config_cls, app, mock_services):
        """Test that get_services returns cached services from g."""
        with app.app_context():
            # Pre-populate g with services
            g.route_library_services = mock_services
            
            services = get_services()
            
            assert services == mock_services
            # Config should not be called since we're using cached services
            mock_config_cls.assert_not_called()


class TestRouteLibraryIndex:
    """Test route library index endpoint."""
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_default_params(self, mock_get_services, mock_render, client, mock_services):
        """Test index with default parameters."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/')
        
        assert response.status_code == 200
        mock_services['library'].get_all_routes.assert_called_once_with(
            route_type='all',
            sort_by='uses'
        )
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        assert args[0] == 'routes/index.html'
        assert kwargs['page_title'] == 'Route Library'
        assert len(kwargs['routes']) == 2
        assert kwargs['sort_by'] == 'uses'
        assert kwargs['filter_by'] == 'all'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_with_sort_param(self, mock_get_services, mock_render, client, mock_services):
        """Test index with sort parameter."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/?sort=distance')
        
        assert response.status_code == 200
        mock_services['library'].get_all_routes.assert_called_once_with(
            route_type='all',
            sort_by='distance'
        )
        args, kwargs = mock_render.call_args
        assert kwargs['sort_by'] == 'distance'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_with_filter_param(self, mock_get_services, mock_render, client, mock_services):
        """Test index with filter parameter."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/?filter=commute')
        
        assert response.status_code == 200
        mock_services['library'].get_all_routes.assert_called_once_with(
            route_type='commute',
            sort_by='uses'
        )
        args, kwargs = mock_render.call_args
        assert kwargs['filter_by'] == 'commute'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_with_search_param(self, mock_get_services, mock_render, client, mock_services):
        """Test index with search parameter."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/?search=commute')
        
        assert response.status_code == 200
        mock_services['library'].search_routes.assert_called_once_with('commute', limit=100)
        args, kwargs = mock_render.call_args
        assert kwargs['search_term'] == 'commute'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_with_favorites_filter(self, mock_get_services, mock_render, client, mock_services):
        """Test index with favorites filter."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/?filter=favorite')
        
        assert response.status_code == 200
        mock_services['library'].get_favorites.assert_called_once()
        args, kwargs = mock_render.call_args
        assert kwargs['filter_by'] == 'favorite'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_pagination(self, mock_get_services, mock_render, client, mock_services):
        """Test index pagination."""
        # Create 25 routes for pagination testing
        routes = [{'id': f'route_{i}', 'name': f'Route {i}'} for i in range(25)]
        mock_services['library'].get_all_routes.return_value = {
            'status': 'success',
            'routes': routes,
            'total_count': 25,
            'filters': {'type': 'all', 'sort_by': 'uses'}
        }
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Library</html>'
        
        response = client.get('/routes/?page=2')
        
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert kwargs['page'] == 2
        assert kwargs['total_routes'] == 25
        assert kwargs['total_pages'] == 2
        assert len(kwargs['routes']) == 5  # 20 per page, so page 2 has 5
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_index_error_handling(self, mock_get_services, mock_render, client, mock_services):
        """Test index error handling."""
        mock_services['library'].get_all_routes.side_effect = Exception("Test error")
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Error</html>'
        
        response = client.get('/routes/')
        
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert 'error' in kwargs
        assert kwargs['routes'] == []
        assert kwargs['total_routes'] == 0


class TestRouteDetail:
    """Test route detail endpoint."""
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_detail_success(self, mock_get_services, mock_render, client, mock_services):
        """Test successful route detail retrieval."""
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Route Detail</html>'
        
        response = client.get('/routes/commute/route_1')
        
        assert response.status_code == 200
        mock_services['library'].get_route_details.assert_called_once_with('route_1', 'commute')
        args, kwargs = mock_render.call_args
        assert args[0] == 'routes/detail.html'
        assert 'route' in kwargs
        assert kwargs['route']['id'] == 'route_1'
        assert kwargs['route_type'] == 'commute'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_detail_not_found(self, mock_get_services, mock_render, client, mock_services):
        """Test route detail when route not found."""
        mock_services['library'].get_route_details.return_value = {
            'status': 'error',
            'message': 'Route not found'
        }
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Not Found</html>'
        
        response = client.get('/routes/commute/nonexistent')
        
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert 'error' in kwargs
        assert kwargs['error'] == 'Route not found'
        assert kwargs['page_title'] == 'Route Not Found'
    
    @patch('app.routes.route_library.render_template')
    @patch('app.routes.route_library.get_services')
    def test_detail_error_handling(self, mock_get_services, mock_render, client, mock_services):
        """Test route detail error handling."""
        mock_services['library'].get_route_details.side_effect = Exception("Test error")
        mock_get_services.return_value = mock_services
        mock_render.return_value = '<html>Error</html>'
        
        response = client.get('/routes/commute/route_1')
        
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert 'error' in kwargs
        assert kwargs['error'] == 'Failed to load route details'


class TestApiSearch:
    """Test API search endpoint."""
    
    @patch('app.routes.route_library.get_services')
    def test_api_search_success(self, mock_get_services, client, mock_services):
        """Test successful API search."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/search?q=commute')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['count'] == 1
        assert len(data['results']) == 1
        assert data['query'] == 'commute'
        mock_services['library'].search_routes.assert_called_once_with('commute', limit=10)
    
    @patch('app.routes.route_library.get_services')
    def test_api_search_with_limit(self, mock_get_services, client, mock_services):
        """Test API search with custom limit."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/search?q=route&limit=5')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['limit'] == 5
        mock_services['library'].search_routes.assert_called_once_with('route', limit=5)
    
    @patch('app.routes.route_library.get_services')
    def test_api_search_with_type_filter(self, mock_get_services, client, mock_services):
        """Test API search with type filter."""
        mock_services['library'].search_routes.return_value = {
            'status': 'success',
            'results': [
                {'id': 'route_1', 'name': 'Commute', 'type': 'commute'},
                {'id': 'route_2', 'name': 'Long Ride', 'type': 'long_ride'}
            ],
            'count': 2
        }
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/search?q=route&type=commute')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        # Should only return commute routes
        assert len(data['results']) == 1
        assert data['results'][0]['type'] == 'commute'
    
    @patch('app.routes.route_library.get_services')
    def test_api_search_empty_query(self, mock_get_services, client, mock_services):
        """Test API search with empty query."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/search')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['query'] == ''
        mock_services['library'].search_routes.assert_called_once_with('', limit=10)
    
    @patch('app.routes.route_library.get_services')
    def test_api_search_error_handling(self, mock_get_services, client, mock_services):
        """Test API search error handling."""
        mock_services['library'].search_routes.side_effect = Exception("Test error")
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/search?q=test')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Test error' in data['message']
        assert data['results'] == []
        assert data['count'] == 0


class TestApiToggleFavorite:
    """Test API toggle favorite endpoint."""
    
    @patch('app.routes.route_library.get_services')
    def test_toggle_favorite_add(self, mock_get_services, client, mock_services):
        """Test adding route to favorites."""
        mock_get_services.return_value = mock_services
        
        response = client.post('/routes/api/route_1/favorite',
                              json={'favorite': True})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['route_id'] == 'route_1'
        assert data['is_favorite'] is True
        mock_services['library'].toggle_favorite.assert_called_once_with('route_1', True)
    
    @patch('app.routes.route_library.get_services')
    def test_toggle_favorite_remove(self, mock_get_services, client, mock_services):
        """Test removing route from favorites."""
        mock_services['library'].toggle_favorite.return_value = {
            'status': 'success',
            'route_id': 'route_1',
            'is_favorite': False
        }
        mock_get_services.return_value = mock_services
        
        response = client.post('/routes/api/route_1/favorite',
                              json={'favorite': False})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['is_favorite'] is False
        mock_services['library'].toggle_favorite.assert_called_once_with('route_1', False)
    
    @patch('app.routes.route_library.get_services')
    def test_toggle_favorite_no_json(self, mock_get_services, client, mock_services):
        """Test toggle favorite with empty JSON body."""
        mock_get_services.return_value = mock_services
        
        # Send empty JSON object instead of no body
        response = client.post('/routes/api/route_1/favorite',
                              json={})
        
        assert response.status_code == 200
        # Should default to False when 'favorite' key is missing
        mock_services['library'].toggle_favorite.assert_called_once_with('route_1', False)
    
    @patch('app.routes.route_library.get_services')
    def test_toggle_favorite_error_handling(self, mock_get_services, client, mock_services):
        """Test toggle favorite error handling."""
        mock_services['library'].toggle_favorite.side_effect = Exception("Test error")
        mock_get_services.return_value = mock_services
        
        response = client.post('/routes/api/route_1/favorite',
                              json={'favorite': True})
        
        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Test error' in data['message']


class TestApiLibraryStats:
    """Test API library statistics endpoint."""
    
    @patch('app.routes.route_library.get_services')
    def test_api_stats_success(self, mock_get_services, client, mock_services):
        """Test successful statistics retrieval."""
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/stats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'statistics' in data
        assert data['statistics']['total_routes'] == 2
        assert data['statistics']['commute_routes'] == 1
        assert data['statistics']['long_rides'] == 1
        assert 'last_updated' in data
        mock_services['library'].get_route_statistics.assert_called_once()
    
    @patch('app.routes.route_library.get_services')
    def test_api_stats_error_handling(self, mock_get_services, client, mock_services):
        """Test statistics error handling."""
        mock_services['library'].get_route_statistics.side_effect = Exception("Test error")
        mock_get_services.return_value = mock_services
        
        response = client.get('/routes/api/stats')
        
        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Test error' in data['message']


# Made with Bob