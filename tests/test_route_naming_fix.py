"""
Test for Issue #128: Fix "Unnamed Activity" display in Route Comparison

Verifies that routes never display as "Unnamed Activity" and have meaningful fallback names.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from app.services.route_library_service import RouteLibraryService


class TestRouteNamingFix:
    """Test route naming with fallback logic."""
    
    @pytest.fixture
    def service(self):
        """Create a RouteLibraryService instance with mock config."""
        mock_config = Mock()
        return RouteLibraryService(mock_config)
    
    def test_meaningful_route_name_with_valid_name(self, service):
        """Test that valid names are preserved."""
        
        result = service._get_meaningful_route_name(
            name="Morning Commute",
            distance_km=15.5,
            timestamp="2026-05-14T08:00:00Z",
            is_loop=False
        )
        
        assert result == "Morning Commute"
        assert result != "Unnamed Activity"
    
    def test_meaningful_route_name_with_unnamed_activity(self, service):
        """Test that 'Unnamed Activity' gets replaced with descriptive name."""
        result = service._get_meaningful_route_name(
            name="Unnamed Activity",
            distance_km=25.3,
            timestamp="2026-05-14T08:00:00Z",
            is_loop=False
        )
        
        assert result != "Unnamed Activity"
        assert "25.3km" in result
        assert "Route" in result
        assert "May 14, 2026" in result
    
    def test_meaningful_route_name_with_empty_name(self, service):
        """Test that empty names get replaced with descriptive name."""
        result = service._get_meaningful_route_name(
            name="",
            distance_km=18.7,
            timestamp="2026-03-20T14:30:00Z",
            is_loop=False
        )
        
        assert result != ""
        assert result != "Unnamed Activity"
        assert "18.7km" in result
    
    def test_meaningful_route_name_for_loop(self, service):
        """Test that loops are identified in the name."""
        result = service._get_meaningful_route_name(
            name="Unnamed Activity",
            distance_km=42.0,
            timestamp="2026-05-14T08:00:00Z",
            is_loop=True
        )
        
        assert "Loop" in result
        assert "42.0km" in result
        assert result != "Unnamed Activity"
    
    def test_format_long_ride_with_unnamed_activity(self, service):
        """Test that _format_long_ride handles 'Unnamed Activity' correctly."""
        # Test with dict format (from cache)
        ride_dict = {
            'activity_id': 12345678,
            'name': 'Unnamed Activity',
            'distance_km': 30.5,
            'duration_hours': 1.5,
            'elevation_gain': 250,
            'uses': 1,
            'is_loop': False,
            'timestamp': '2026-05-14T10:00:00Z',
            'type': 'Ride'
        }
        
        result = service._format_long_ride(ride_dict)
        
        assert result['name'] != 'Unnamed Activity'
        assert '30.5km' in result['name']
        assert 'Route' in result['name']
        assert result['sport_type'] == 'Ride'
    
    def test_format_long_ride_with_valid_name(self, service):
        """Test that _format_long_ride preserves valid names."""
        ride_dict = {
            'activity_id': 12345678,
            'name': 'Epic Mountain Ride',
            'distance_km': 50.0,
            'duration_hours': 3.0,
            'elevation_gain': 1200,
            'uses': 2,
            'is_loop': True,
            'timestamp': '2026-05-14T10:00:00Z',
            'type': 'Ride'
        }
        
        result = service._format_long_ride(ride_dict)
        
        assert result['name'] == 'Epic Mountain Ride'
        assert result['sport_type'] == 'Ride'
    
    def test_format_commute_route_with_unnamed_activity(self, service):
        """Test that _format_commute_route handles 'Unnamed Activity' correctly."""
        group_dict = {
            'id': 'test_route_1',
            'name': 'Unnamed Activity',
            'direction': 'home_to_work',
            'frequency': 5,
            'representative_route': {
                'distance': 15000,  # meters
                'duration': 1800,   # seconds
                'elevation_gain': 50,
                'sport_type': 'Ride'
            }
        }
        
        result = service._format_commute_route(group_dict)
        
        assert result['name'] != 'Unnamed Activity'
        assert 'Commute Route' in result['name']
        assert result['sport_type'] == 'Ride'
    
    def test_format_commute_route_with_valid_name(self, service):
        """Test that _format_commute_route preserves valid names."""
        group_dict = {
            'id': 'test_route_2',
            'name': 'Lakefront Trail → Downtown',
            'direction': 'home_to_work',
            'frequency': 10,
            'representative_route': {
                'distance': 16000,
                'duration': 2100,
                'elevation_gain': 75,
                'sport_type': 'Ride'
            }
        }
        
        result = service._format_commute_route(group_dict)
        
        assert result['name'] == 'Lakefront Trail → Downtown'
        assert result['sport_type'] == 'Ride'
    
    def test_all_routes_have_sport_type(self, service):
        """Test that all formatted routes include sport_type field."""
        # Test long ride
        long_ride = {
            'activity_id': 123,
            'name': 'Test Ride',
            'distance_km': 20.0,
            'duration_hours': 1.0,
            'elevation_gain': 100,
            'uses': 1,
            'is_loop': False,
            'timestamp': '2026-05-14T10:00:00Z',
            'type': 'GravelRide'
        }
        
        result = service._format_long_ride(long_ride)
        assert 'sport_type' in result
        assert result['sport_type'] == 'GravelRide'
        
        # Test commute route
        commute = {
            'id': 'test',
            'name': 'Test Commute',
            'direction': 'home_to_work',
            'frequency': 5,
            'representative_route': {
                'distance': 15000,
                'duration': 1800,
                'elevation_gain': 50,
                'sport_type': 'EBikeRide'
            }
        }
        
        result = service._format_commute_route(commute)
        assert 'sport_type' in result
        assert result['sport_type'] == 'EBikeRide'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# Made with Bob
