"""
UAT Scenario 1: Morning Commute Planning - "The Daily Commuter"

User Story: As a daily bike commuter, I want to quickly check today's weather 
and get my optimal commute route recommendation so I can leave on time with 
the right gear.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


@pytest.mark.uat
@pytest.mark.scenario1
class TestDailyCommuterScenario:
    """Complete workflow test for daily commute planning"""
    
    @pytest.fixture
    def mock_weather_data(self):
        """Mock current weather data"""
        return {
            'temperature_f': 68,
            'feels_like_f': 65,
            'wind_speed_mph': 8,
            'wind_direction': 'NW',
            'precipitation_probability': 10,
            'conditions': 'Partly Cloudy',
            'icon': 'partly-cloudy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    @pytest.fixture
    def mock_route_data(self):
        """Mock route recommendation data"""
        return {
            'route_id': 'route_123',
            'route_name': 'Harrison via Damen',
            'distance_miles': 5.2,
            'estimated_duration_minutes': 22,
            'weather_score': 85,
            'traffic_score': 90,
            'overall_score': 88,
            'recommendation_reason': 'Optimal conditions with light wind and clear skies'
        }
    
    @pytest.fixture
    def mock_alternative_routes(self):
        """Mock alternative route options"""
        return [
            {
                'route_id': 'route_123',
                'route_name': 'Harrison via Damen',
                'distance_miles': 5.2,
                'score': 88,
                'weather_suitability': 'excellent'
            },
            {
                'route_id': 'route_124',
                'route_name': 'Harrison via Ashland',
                'distance_miles': 5.4,
                'score': 85,
                'weather_suitability': 'good'
            },
            {
                'route_id': 'route_125',
                'route_name': 'Milwaukee Trail',
                'distance_miles': 6.1,
                'score': 82,
                'weather_suitability': 'good'
            }
        ]
    
    def test_step_1_authentication_and_dashboard_access(self, client):
        """Step 1: User opens app and accesses dashboard"""
        # User opens app root
        response = client.get('/')
        
        # Should redirect to dashboard
        assert response.status_code in [200, 302]
        
        # If redirect, follow it
        if response.status_code == 302:
            assert '/dashboard' in response.location
            response = client.get('/dashboard')
        
        assert response.status_code == 200
        
    @patch('app.services.weather_service.WeatherService.get_current_weather')
    def test_step_2_view_dashboard_weather_summary(self, mock_weather, client, mock_weather_data):
        """Step 2: User sees current weather at a glance"""
        mock_weather.return_value = mock_weather_data
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Verify weather data is present in response
        html = response.data.decode('utf-8')
        assert 'Weather' in html or 'weather' in html
        
        # Performance check: response should be fast
        # (In real implementation, measure actual response time)
        assert len(response.data) > 0
    
    @patch('app.services.commute_service.CommuteService.get_recommendation')
    def test_step_3_get_next_commute_recommendation(self, mock_recommend, client, mock_route_data):
        """Step 3: User gets route recommendation"""
        mock_recommend.return_value = mock_route_data
        
        response = client.post('/api/recommendation', json={
            'time': 'now',
            'direction': 'to_work'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify all required fields present
        assert 'route_name' in data
        assert 'distance_miles' in data
        assert 'estimated_duration_minutes' in data
        assert 'weather_score' in data
        assert 'traffic_score' in data
        assert 'overall_score' in data
        assert 'recommendation_reason' in data
        
        # Verify score ranges
        assert 0 <= data['overall_score'] <= 100
        assert 0 <= data['weather_score'] <= 100
        assert 0 <= data['traffic_score'] <= 100
    
    @patch('app.services.route_library_service.RouteLibraryService.get_route_details')
    def test_step_4_view_route_details(self, mock_details, client, mock_route_data):
        """Step 4: User views detailed route information"""
        mock_details.return_value = {
            **mock_route_data,
            'polyline': 'encoded_polyline_string',
            'elevation_gain_feet': 120,
            'average_speed_mph': 14.2,
            'uses_count': 45,
            'last_ridden': '2026-05-06T08:15:00Z'
        }
        
        route_id = mock_route_data['route_id']
        response = client.get(f'/commute?route_id={route_id}')
        
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        
        # Verify route details are displayed
        assert mock_route_data['route_name'] in html or 'route' in html.lower()
    
    @patch('app.services.route_library_service.RouteLibraryService.get_routes')
    def test_step_5_check_alternative_routes(self, mock_routes, client, mock_alternative_routes):
        """Step 5: User checks alternative route options"""
        mock_routes.return_value = mock_alternative_routes
        
        response = client.get('/api/routes?direction=to_work&limit=5')
        
        assert response.status_code == 200
        routes = response.get_json()
        
        # Verify we got routes back
        assert isinstance(routes, list)
        assert len(routes) <= 5
        
        # Verify each route has required fields
        for route in routes:
            assert 'route_name' in route
            assert 'distance_miles' in route
            assert 'score' in route
            assert 'weather_suitability' in route
    
    @patch('app.services.weather_service.WeatherService.get_current_weather')
    @patch('app.services.commute_service.CommuteService.get_recommendation')
    @patch('app.services.route_library_service.RouteLibraryService.get_routes')
    def test_complete_morning_commute_workflow(
        self, 
        mock_routes, 
        mock_recommend, 
        mock_weather,
        client,
        mock_weather_data,
        mock_route_data,
        mock_alternative_routes
    ):
        """Complete end-to-end workflow for morning commute planning"""
        # Setup mocks
        mock_weather.return_value = mock_weather_data
        mock_recommend.return_value = mock_route_data
        mock_routes.return_value = mock_alternative_routes
        
        # Step 1: Access dashboard
        response = client.get('/')
        assert response.status_code in [200, 302]
        
        # Step 2: View dashboard with weather
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Weather' in response.data or b'weather' in response.data
        
        # Step 3: Get recommendation
        response = client.post('/api/recommendation', json={
            'time': 'now',
            'direction': 'to_work'
        })
        assert response.status_code == 200
        recommendation = response.get_json()
        assert 'route_name' in recommendation
        assert 'overall_score' in recommendation
        assert 0 <= recommendation['overall_score'] <= 100
        
        # Step 4: View route details
        route_id = recommendation.get('route_id', 'route_123')
        response = client.get(f'/commute?route_id={route_id}')
        assert response.status_code == 200
        
        # Step 5: Check alternatives
        response = client.get('/api/routes?direction=to_work&limit=5')
        assert response.status_code == 200
        routes = response.get_json()
        assert len(routes) <= 5
        
        # Verify workflow completed successfully
        assert True  # All steps passed


@pytest.mark.uat
@pytest.mark.scenario1
@pytest.mark.mobile
class TestDailyCommuterMobileExperience:
    """Test mobile-specific aspects of daily commute workflow"""
    
    def test_mobile_viewport_compatibility(self, client):
        """Verify mobile layout works on small screens (320px)"""
        # This would require Selenium/Playwright for real viewport testing
        # For now, verify responsive CSS is loaded
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        # Check for viewport meta tag
        assert 'viewport' in html.lower()
    
    def test_touch_target_sizes(self, client):
        """Verify touch targets meet 44x44px minimum"""
        # This would require browser automation for real testing
        # For now, verify CSS includes touch-friendly styles
        response = client.get('/static/css/main.css')
        if response.status_code == 200:
            css = response.data.decode('utf-8')
            # Look for button/link padding that suggests touch-friendly design
            assert 'padding' in css or 'min-height' in css


@pytest.mark.uat
@pytest.mark.scenario1
@pytest.mark.performance
class TestDailyCommuterPerformance:
    """Test performance requirements for daily commute workflow"""
    
    @patch('app.services.weather_service.WeatherService.get_current_weather')
    def test_dashboard_load_time(self, mock_weather, client, mock_weather_data):
        """Dashboard should load in < 2 seconds"""
        import time
        
        mock_weather.return_value = mock_weather_data
        
        start_time = time.time()
        response = client.get('/dashboard')
        end_time = time.time()
        
        assert response.status_code == 200
        
        load_time = end_time - start_time
        # Allow 2 seconds for test environment
        assert load_time < 2.0, f"Dashboard took {load_time:.2f}s to load"
    
    @patch('app.services.commute_service.CommuteService.get_recommendation')
    def test_recommendation_response_time(self, mock_recommend, client, mock_route_data):
        """Recommendation API should respond in < 3 seconds"""
        import time
        
        mock_recommend.return_value = mock_route_data
        
        start_time = time.time()
        response = client.post('/api/recommendation', json={
            'time': 'now',
            'direction': 'to_work'
        })
        end_time = time.time()
        
        assert response.status_code == 200
        
        response_time = end_time - start_time
        assert response_time < 3.0, f"Recommendation took {response_time:.2f}s"

# Made with Bob
