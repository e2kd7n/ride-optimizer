"""
Unit tests for API input validation using Marshmallow schemas.

Tests validation for all API endpoints to ensure proper error handling
and helpful error messages for invalid input.
"""

import pytest
from marshmallow import ValidationError
from app.schemas import (
    WeatherQuerySchema,
    RecommendationQuerySchema,
    RoutesQuerySchema,
    MapQuerySchema
)


class TestWeatherQuerySchema:
    """Test validation for /api/weather endpoint."""
    
    def test_valid_coordinates(self):
        """Test valid latitude and longitude."""
        schema = WeatherQuerySchema()
        data = {'lat': 40.7128, 'lon': -74.0060}
        result = schema.load(data)
        assert result['lat'] == 40.7128
        assert result['lon'] == -74.0060
    
    def test_valid_with_location(self):
        """Test valid coordinates with location name."""
        schema = WeatherQuerySchema()
        data = {'lat': 40.7128, 'lon': -74.0060, 'location': 'New York'}
        result = schema.load(data)
        assert result['location'] == 'New York'
    
    def test_empty_params(self):
        """Test empty parameters (should be valid - uses defaults)."""
        schema = WeatherQuerySchema()
        result = schema.load({})
        assert result == {}
    
    def test_invalid_latitude_range(self):
        """Test latitude out of valid range."""
        schema = WeatherQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'lat': 91.0, 'lon': 0.0})
        assert 'lat' in exc_info.value.messages
        assert 'greater than or equal to -90' in str(exc_info.value.messages['lat'])
    
    def test_invalid_longitude_range(self):
        """Test longitude out of valid range."""
        schema = WeatherQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'lat': 0.0, 'lon': 181.0})
        assert 'lon' in exc_info.value.messages
        assert 'greater than or equal to -180' in str(exc_info.value.messages['lon'])
    
    def test_missing_longitude(self):
        """Test latitude without longitude."""
        schema = WeatherQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'lat': 40.7128})
        assert 'coordinates' in exc_info.value.messages
        assert 'Both latitude and longitude' in str(exc_info.value.messages['coordinates'])
    
    def test_missing_latitude(self):
        """Test longitude without latitude."""
        schema = WeatherQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'lon': -74.0060})
        assert 'coordinates' in exc_info.value.messages
    
    def test_invalid_latitude_type(self):
        """Test non-numeric latitude."""
        schema = WeatherQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'lat': 'invalid', 'lon': 0.0})
        assert 'lat' in exc_info.value.messages
    
    def test_location_too_long(self):
        """Test location name exceeding max length."""
        schema = WeatherQuerySchema()
        long_location = 'A' * 101
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'location': long_location})
        assert 'location' in exc_info.value.messages


class TestRecommendationQuerySchema:
    """Test validation for /api/recommendation endpoint."""
    
    def test_valid_to_work(self):
        """Test valid 'to_work' direction."""
        schema = RecommendationQuerySchema()
        result = schema.load({'direction': 'to_work'})
        assert result['direction'] == 'to_work'
    
    def test_valid_to_home(self):
        """Test valid 'to_home' direction."""
        schema = RecommendationQuerySchema()
        result = schema.load({'direction': 'to_home'})
        assert result['direction'] == 'to_home'
    
    def test_empty_params(self):
        """Test empty parameters (auto-detect direction)."""
        schema = RecommendationQuerySchema()
        result = schema.load({})
        assert result == {}
    
    def test_invalid_direction(self):
        """Test invalid direction value."""
        schema = RecommendationQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'direction': 'invalid'})
        assert 'direction' in exc_info.value.messages
        assert 'to_work' in str(exc_info.value.messages['direction'])
        assert 'to_home' in str(exc_info.value.messages['direction'])


class TestRoutesQuerySchema:
    """Test validation for /api/routes endpoint."""
    
    def test_valid_all_params(self):
        """Test all valid parameters."""
        schema = RoutesQuerySchema()
        data = {
            'type': 'commute',
            'sort': 'distance',
            'limit': 50,
            'search': 'Main St',
            'min_distance': 5.0,
            'max_distance': 20.0
        }
        result = schema.load(data)
        assert result['type'] == 'commute'
        assert result['limit'] == 50
    
    def test_valid_type_values(self):
        """Test all valid type values."""
        schema = RoutesQuerySchema()
        for type_val in ['all', 'commute', 'long_ride']:
            result = schema.load({'type': type_val})
            assert result['type'] == type_val
    
    def test_valid_sort_values(self):
        """Test all valid sort values."""
        schema = RoutesQuerySchema()
        for sort_val in ['uses', 'distance', 'recent', 'name']:
            result = schema.load({'sort': sort_val})
            assert result['sort'] == sort_val
    
    def test_empty_params(self):
        """Test empty parameters (use defaults)."""
        schema = RoutesQuerySchema()
        result = schema.load({})
        assert result == {}
    
    def test_invalid_type(self):
        """Test invalid type value."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'type': 'invalid'})
        assert 'type' in exc_info.value.messages
    
    def test_invalid_sort(self):
        """Test invalid sort value."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'sort': 'invalid'})
        assert 'sort' in exc_info.value.messages
    
    def test_limit_too_small(self):
        """Test limit below minimum."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'limit': 0})
        assert 'limit' in exc_info.value.messages
        assert 'greater than or equal to 1' in str(exc_info.value.messages['limit'])
    
    def test_limit_too_large(self):
        """Test limit above maximum."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'limit': 1001})
        assert 'limit' in exc_info.value.messages
    
    def test_search_too_long(self):
        """Test search query exceeding max length."""
        schema = RoutesQuerySchema()
        long_search = 'A' * 201
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'search': long_search})
        assert 'search' in exc_info.value.messages
    
    def test_negative_min_distance(self):
        """Test negative minimum distance."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'min_distance': -1.0})
        assert 'min_distance' in exc_info.value.messages
    
    def test_distance_range_invalid(self):
        """Test min_distance greater than max_distance."""
        schema = RoutesQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'min_distance': 20.0, 'max_distance': 10.0})
        assert 'distance_range' in exc_info.value.messages
        assert 'less than maximum' in str(exc_info.value.messages['distance_range'])
    
    def test_distance_range_valid(self):
        """Test valid distance range."""
        schema = RoutesQuerySchema()
        result = schema.load({'min_distance': 10.0, 'max_distance': 20.0})
        assert result['min_distance'] == 10.0
        assert result['max_distance'] == 20.0


class TestMapQuerySchema:
    """Test validation for /api/maps/<page_type> endpoint."""
    
    def test_valid_route_id(self):
        """Test valid route ID."""
        schema = MapQuerySchema()
        result = schema.load({'route_id': 'route_123'})
        assert result['route_id'] == 'route_123'
    
    def test_valid_route_type(self):
        """Test valid route type."""
        schema = MapQuerySchema()
        result = schema.load({'route_type': 'commute'})
        assert result['route_type'] == 'commute'
    
    def test_empty_params(self):
        """Test empty parameters."""
        schema = MapQuerySchema()
        result = schema.load({})
        assert result == {}
    
    def test_route_id_too_long(self):
        """Test route ID exceeding max length."""
        schema = MapQuerySchema()
        long_id = 'A' * 51
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'route_id': long_id})
        assert 'route_id' in exc_info.value.messages
    
    def test_invalid_route_type(self):
        """Test invalid route type."""
        schema = MapQuerySchema()
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'route_type': 'invalid'})
        assert 'route_type' in exc_info.value.messages

# Made with Bob
