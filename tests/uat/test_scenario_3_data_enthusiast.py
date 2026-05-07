"""
UAT Scenario 3: Route Library Management - "The Data Enthusiast"

User Story: As a data-driven cyclist, I want to view my complete route history, 
analyze performance trends, and organize my route library efficiently.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import json


@pytest.mark.uat
@pytest.mark.scenario3
class TestDataEnthusiastScenario:
    """Complete workflow test for route library management"""
    
    @pytest.fixture
    def mock_route_library_summary(self):
        """Mock route library dashboard summary"""
        return {
            'total_routes': 47,
            'total_distance_miles': 1234.5,
            'most_popular_routes': [
                {'route_name': 'Harrison via Damen', 'uses_count': 45},
                {'route_name': 'Milwaukee Trail', 'uses_count': 38},
                {'route_name': 'Lakefront Path', 'uses_count': 32},
                {'route_name': 'North Shore Loop', 'uses_count': 28},
                {'route_name': 'Fox River Trail', 'uses_count': 24}
            ],
            'recently_added': [
                {'route_name': 'New Trail Discovery', 'added_date': '2026-05-05'},
                {'route_name': 'Scenic Backroads', 'added_date': '2026-05-03'}
            ]
        }
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock route search results"""
        return [
            {
                'route_id': 'route_123',
                'route_name': 'Harrison via Damen',
                'distance_miles': 5.2,
                'uses_count': 45,
                'last_ridden_date': '2026-05-06',
                'average_speed_mph': 14.2
            },
            {
                'route_id': 'route_124',
                'route_name': 'Harrison via Ashland',
                'distance_miles': 5.4,
                'uses_count': 38,
                'last_ridden_date': '2026-05-05',
                'average_speed_mph': 13.8
            }
        ]
    
    @pytest.fixture
    def mock_route_history(self):
        """Mock complete activity history for a route"""
        activities = []
        base_date = datetime.now(timezone.utc)
        
        for i in range(10):
            date = base_date - timedelta(days=i * 3)
            activities.append({
                'activity_id': f'activity_{1000 + i}',
                'date': date.isoformat(),
                'duration_minutes': 22 + (i % 5),
                'average_speed_mph': 14.0 + (i % 3) * 0.5,
                'weather_conditions': ['Clear', 'Cloudy', 'Partly Cloudy'][i % 3],
                'notes': f'Ride {i + 1}' if i % 3 == 0 else None
            })
        
        return activities
    
    @pytest.fixture
    def mock_route_comparison(self):
        """Mock route comparison data"""
        return {
            'side_by_side_stats': {
                'route_1': {
                    'route_name': 'Harrison via Damen',
                    'distance_miles': 5.2,
                    'elevation_gain_feet': 120,
                    'average_speed_mph': 14.2,
                    'uses_count': 45
                },
                'route_2': {
                    'route_name': 'Harrison via Ashland',
                    'distance_miles': 5.4,
                    'elevation_gain_feet': 95,
                    'average_speed_mph': 13.8,
                    'uses_count': 38
                }
            },
            'route_similarity_score': 87,
            'polyline_overlay': {
                'route_1_polyline': 'encoded_polyline_1',
                'route_2_polyline': 'encoded_polyline_2'
            },
            'performance_comparison': {
                'faster_route': 'Harrison via Damen',
                'easier_route': 'Harrison via Ashland',
                'time_difference_minutes': 1.2
            },
            'recommendation': 'Use Harrison via Damen for speed, Harrison via Ashland for easier ride'
        }
    
    @pytest.fixture
    def mock_analytics_summary(self):
        """Mock overall cycling analytics"""
        return {
            'total_rides_count': 234,
            'total_distance_miles': 1234.5,
            'total_time_hours': 87.3,
            'average_speed_mph': 14.1,
            'most_ridden_route': 'Harrison via Damen',
            'favorite_time_of_day': 'Morning (6-9am)',
            'monthly_trends': [
                {'month': '2026-04', 'rides': 28, 'distance': 145.6},
                {'month': '2026-03', 'rides': 24, 'distance': 125.2},
                {'month': '2026-02', 'rides': 18, 'distance': 93.4}
            ]
        }
    
    def test_step_1_access_route_library_dashboard(self, client):
        """Step 1: User opens route library dashboard"""
        response = client.get('/routes')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        assert 'route' in html.lower()
    
    @patch('app.services.route_library_service.RouteLibraryService.search_routes')
    def test_step_2_search_routes_by_name(self, mock_search, client, mock_search_results):
        """Step 2: User searches for routes by name"""
        mock_search.return_value = mock_search_results
        
        response = client.get('/api/routes?search=Harrison')
        assert response.status_code == 200
        
        routes = response.get_json()
        assert isinstance(routes, list)
        
        # Verify all results contain search term
        for route in routes:
            assert 'Harrison' in route['route_name']
            
            # Verify required fields
            assert 'route_id' in route
            assert 'distance_miles' in route
            assert 'uses_count' in route
            assert 'last_ridden_date' in route
            assert 'average_speed_mph' in route
    
    @patch('app.services.route_library_service.RouteLibraryService.get_route_history')
    def test_step_3_view_route_performance_history(self, mock_history, client, mock_route_history):
        """Step 3: User views complete activity history for a route"""
        mock_history.return_value = mock_route_history
        
        route_id = 'route_123'
        response = client.get(f'/api/routes/{route_id}/history')
        assert response.status_code == 200
        
        history = response.get_json()
        assert isinstance(history, list)
        assert len(history) > 0
        
        # Verify each activity has required fields
        for activity in history:
            assert 'activity_id' in activity
            assert 'date' in activity
            assert 'duration_minutes' in activity
            assert 'average_speed_mph' in activity
            assert 'weather_conditions' in activity
        
        # Verify sorted by date descending (most recent first)
        dates = [datetime.fromisoformat(a['date'].replace('Z', '+00:00')) for a in history]
        assert dates == sorted(dates, reverse=True), "History should be sorted by date descending"
    
    @patch('app.services.route_library_service.RouteLibraryService.compare_routes')
    def test_step_4_compare_similar_routes(self, mock_compare, client, mock_route_comparison):
        """Step 4: User compares two similar routes"""
        mock_compare.return_value = mock_route_comparison
        
        response = client.post('/api/routes/compare', json={
            'route_ids': ['route_123', 'route_124']
        })
        
        assert response.status_code == 200
        comparison = response.get_json()
        
        # Verify comparison structure
        assert 'side_by_side_stats' in comparison
        assert 'route_similarity_score' in comparison
        assert 'polyline_overlay' in comparison
        assert 'performance_comparison' in comparison
        assert 'recommendation' in comparison
        
        # Verify similarity score range
        assert 0 <= comparison['route_similarity_score'] <= 100
        
        # Verify side-by-side stats
        assert 'route_1' in comparison['side_by_side_stats']
        assert 'route_2' in comparison['side_by_side_stats']
    
    @patch('app.services.route_library_service.RouteLibraryService.export_routes')
    def test_step_5_export_route_data(self, mock_export, client):
        """Step 5: User exports route library to JSON"""
        mock_export_data = {
            'export_date': datetime.now(timezone.utc).isoformat(),
            'total_routes': 47,
            'routes': [
                {
                    'route_id': 'route_123',
                    'route_name': 'Harrison via Damen',
                    'distance_miles': 5.2,
                    'polyline': 'encoded_polyline',
                    'statistics': {
                        'uses_count': 45,
                        'average_speed_mph': 14.2
                    },
                    'activities': []
                }
            ]
        }
        mock_export.return_value = mock_export_data
        
        response = client.get('/api/routes/export?format=json')
        assert response.status_code == 200
        
        # Verify response is JSON
        data = response.get_json()
        assert 'routes' in data
        assert 'total_routes' in data
        assert isinstance(data['routes'], list)
    
    @patch('app.services.analytics_service.AnalyticsService.get_summary')
    def test_step_6_view_analytics_dashboard(self, mock_analytics, client, mock_analytics_summary):
        """Step 6: User views overall cycling analytics"""
        mock_analytics.return_value = mock_analytics_summary
        
        response = client.get('/api/analytics/summary')
        assert response.status_code == 200
        
        analytics = response.get_json()
        
        # Verify analytics structure
        assert 'total_rides_count' in analytics
        assert 'total_distance_miles' in analytics
        assert 'total_time_hours' in analytics
        assert 'average_speed_mph' in analytics
        assert 'most_ridden_route' in analytics
        assert 'favorite_time_of_day' in analytics
        assert 'monthly_trends' in analytics
        
        # Verify data validity
        assert analytics['total_rides_count'] > 0
        assert analytics['total_distance_miles'] > 0
        assert analytics['average_speed_mph'] > 0
        
        # Verify monthly trends
        assert isinstance(analytics['monthly_trends'], list)
        for month in analytics['monthly_trends']:
            assert 'month' in month
            assert 'rides' in month
            assert 'distance' in month
    
    @patch('app.services.route_library_service.RouteLibraryService.get_summary')
    @patch('app.services.route_library_service.RouteLibraryService.search_routes')
    @patch('app.services.route_library_service.RouteLibraryService.get_route_history')
    @patch('app.services.route_library_service.RouteLibraryService.compare_routes')
    @patch('app.services.route_library_service.RouteLibraryService.export_routes')
    @patch('app.services.analytics_service.AnalyticsService.get_summary')
    def test_complete_route_library_workflow(
        self,
        mock_analytics,
        mock_export,
        mock_compare,
        mock_history,
        mock_search,
        mock_summary,
        client,
        mock_route_library_summary,
        mock_search_results,
        mock_route_history,
        mock_route_comparison,
        mock_analytics_summary
    ):
        """Complete end-to-end workflow for route library management"""
        # Setup mocks
        mock_summary.return_value = mock_route_library_summary
        mock_search.return_value = mock_search_results
        mock_history.return_value = mock_route_history
        mock_compare.return_value = mock_route_comparison
        mock_export.return_value = {'routes': [], 'total_routes': 47}
        mock_analytics.return_value = mock_analytics_summary
        
        # Step 1: Access route library
        response = client.get('/routes')
        assert response.status_code == 200
        
        # Step 2: Search routes
        response = client.get('/api/routes?search=Harrison')
        assert response.status_code == 200
        routes = response.get_json()
        assert all('Harrison' in r['route_name'] for r in routes)
        
        # Step 3: View route history
        route_id = routes[0]['route_id']
        response = client.get(f'/api/routes/{route_id}/history')
        assert response.status_code == 200
        history = response.get_json()
        assert isinstance(history, list)
        assert all('activity_id' in activity for activity in history)
        
        # Step 4: Compare routes
        route_ids = [routes[0]['route_id'], routes[1]['route_id']]
        response = client.post('/api/routes/compare', json={
            'route_ids': route_ids
        })
        assert response.status_code == 200
        comparison = response.get_json()
        assert 'side_by_side_stats' in comparison
        assert 'route_similarity_score' in comparison
        
        # Step 5: Export data
        response = client.get('/api/routes/export?format=json')
        assert response.status_code == 200
        export_data = response.get_json()
        assert 'routes' in export_data
        
        # Step 6: View analytics
        response = client.get('/api/analytics/summary')
        assert response.status_code == 200
        analytics = response.get_json()
        assert 'total_rides_count' in analytics
        assert 'total_distance_miles' in analytics
        assert analytics['total_rides_count'] > 0
        
        # Verify workflow completed successfully
        assert True  # All steps passed


@pytest.mark.uat
@pytest.mark.scenario3
@pytest.mark.desktop
class TestDataEnthusiastDesktopExperience:
    """Test desktop-specific aspects of route library management"""
    
    def test_desktop_viewport_compatibility(self, client):
        """Verify desktop layout works on large screens (1920px)"""
        response = client.get('/routes')
        assert response.status_code == 200
        
        html = response.data.decode('utf-8')
        # Verify responsive design supports desktop
        assert 'viewport' in html.lower()
    
    @patch('app.services.route_library_service.RouteLibraryService.search_routes')
    def test_search_performance(self, mock_search, client, mock_search_results):
        """Search should return results instantly (< 1 second)"""
        import time
        
        mock_search.return_value = mock_search_results
        
        start_time = time.time()
        response = client.get('/api/routes?search=Harrison')
        end_time = time.time()
        
        assert response.status_code == 200
        
        search_time = end_time - start_time
        assert search_time < 1.0, f"Search took {search_time:.2f}s"


@pytest.mark.uat
@pytest.mark.scenario3
@pytest.mark.data_integrity
class TestDataEnthusiastDataIntegrity:
    """Test data integrity and accuracy for route library"""
    
    @patch('app.services.route_library_service.RouteLibraryService.get_route_history')
    def test_route_history_completeness(self, mock_history, client, mock_route_history):
        """Route history should include all activities"""
        mock_history.return_value = mock_route_history
        
        response = client.get('/api/routes/route_123/history')
        assert response.status_code == 200
        
        history = response.get_json()
        
        # Verify no duplicate activities
        activity_ids = [a['activity_id'] for a in history]
        assert len(activity_ids) == len(set(activity_ids)), "No duplicate activities"
        
        # Verify all activities have valid data
        for activity in history:
            assert activity['duration_minutes'] > 0
            assert activity['average_speed_mph'] > 0
            
            # Verify date is valid ISO format
            date = datetime.fromisoformat(activity['date'].replace('Z', '+00:00'))
            assert date <= datetime.now(timezone.utc)
    
    @patch('app.services.route_library_service.RouteLibraryService.compare_routes')
    def test_route_comparison_accuracy(self, mock_compare, client, mock_route_comparison):
        """Route comparison should provide accurate statistics"""
        mock_compare.return_value = mock_route_comparison
        
        response = client.post('/api/routes/compare', json={
            'route_ids': ['route_123', 'route_124']
        })
        assert response.status_code == 200
        
        comparison = response.get_json()
        stats = comparison['side_by_side_stats']
        
        # Verify statistics are reasonable
        for route_key in ['route_1', 'route_2']:
            route = stats[route_key]
            assert route['distance_miles'] > 0
            assert route['average_speed_mph'] > 0
            assert route['uses_count'] >= 0
            assert route['elevation_gain_feet'] >= 0
    
    @patch('app.services.analytics_service.AnalyticsService.get_summary')
    def test_analytics_accuracy(self, mock_analytics, client, mock_analytics_summary):
        """Analytics should be accurate within 1%"""
        mock_analytics.return_value = mock_analytics_summary
        
        response = client.get('/api/analytics/summary')
        assert response.status_code == 200
        
        analytics = response.get_json()
        
        # Verify calculated average speed matches total distance/time
        calculated_avg_speed = analytics['total_distance_miles'] / analytics['total_time_hours']
        reported_avg_speed = analytics['average_speed_mph']
        
        # Allow 1% margin of error
        margin = calculated_avg_speed * 0.01
        assert abs(calculated_avg_speed - reported_avg_speed) <= margin, \
            f"Average speed mismatch: calculated {calculated_avg_speed:.2f}, reported {reported_avg_speed:.2f}"


@pytest.mark.uat
@pytest.mark.scenario3
@pytest.mark.export
class TestDataEnthusiastExportFunctionality:
    """Test export functionality for route library"""
    
    @patch('app.services.route_library_service.RouteLibraryService.export_routes')
    def test_export_json_format(self, mock_export, client):
        """Export should generate valid JSON"""
        mock_export.return_value = {
            'export_date': datetime.now(timezone.utc).isoformat(),
            'total_routes': 2,
            'routes': [
                {'route_id': 'route_123', 'route_name': 'Test Route 1'},
                {'route_id': 'route_124', 'route_name': 'Test Route 2'}
            ]
        }
        
        response = client.get('/api/routes/export?format=json')
        assert response.status_code == 200
        
        # Verify valid JSON
        data = response.get_json()
        assert data is not None
        
        # Verify can be serialized back to JSON string
        json_string = json.dumps(data)
        assert len(json_string) > 0
    
    @patch('app.services.route_library_service.RouteLibraryService.export_routes')
    def test_export_file_size(self, mock_export, client):
        """Export file should be reasonable size (< 5MB for 100 routes)"""
        # Mock 100 routes
        routes = [
            {
                'route_id': f'route_{i}',
                'route_name': f'Route {i}',
                'distance_miles': 5.0 + i * 0.1,
                'polyline': 'x' * 1000  # Simulate polyline data
            }
            for i in range(100)
        ]
        
        mock_export.return_value = {
            'export_date': datetime.now(timezone.utc).isoformat(),
            'total_routes': 100,
            'routes': routes
        }
        
        response = client.get('/api/routes/export?format=json')
        assert response.status_code == 200
        
        # Check file size
        data_size = len(response.data)
        max_size = 5 * 1024 * 1024  # 5MB
        assert data_size < max_size, f"Export file too large: {data_size / 1024 / 1024:.2f}MB"

# Made with Bob
