"""
Marshmallow validation schemas for API endpoints.

Provides input validation for all Flask API endpoints with helpful error messages.
"""

from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class WeatherQuerySchema(Schema):
    """Validation schema for /api/weather endpoint."""
    
    lat = fields.Float(
        required=False,
        validate=validate.Range(min=-90, max=90),
        error_messages={
            'invalid': 'Latitude must be a valid number',
            'validator_failed': 'Latitude must be between -90 and 90 degrees'
        }
    )
    lon = fields.Float(
        required=False,
        validate=validate.Range(min=-180, max=180),
        error_messages={
            'invalid': 'Longitude must be a valid number',
            'validator_failed': 'Longitude must be between -180 and 180 degrees'
        }
    )
    location = fields.String(
        required=False,
        validate=validate.Length(max=100),
        error_messages={
            'invalid': 'Location must be a string',
            'validator_failed': 'Location name must be 100 characters or less'
        }
    )
    
    @validates_schema
    def validate_coordinates(self, data, **kwargs):
        """Ensure lat and lon are both provided or both omitted."""
        lat = data.get('lat')
        lon = data.get('lon')
        
        if (lat is not None and lon is None) or (lat is None and lon is not None):
            raise ValidationError(
                'Both latitude and longitude must be provided together',
                field_name='coordinates'
            )


class RecommendationQuerySchema(Schema):
    """Validation schema for /api/recommendation endpoint."""
    
    direction = fields.String(
        required=False,
        validate=validate.OneOf(['to_work', 'to_home']),
        error_messages={
            'invalid': 'Direction must be a string',
            'validator_failed': 'Direction must be either "to_work" or "to_home"'
        }
    )


class RoutesQuerySchema(Schema):
    """Validation schema for /api/routes endpoint."""
    
    type = fields.String(
        required=False,
        validate=validate.OneOf(['all', 'commute', 'long_ride']),
        error_messages={
            'invalid': 'Type must be a string',
            'validator_failed': 'Type must be one of: all, commute, long_ride'
        }
    )
    sort = fields.String(
        required=False,
        validate=validate.OneOf(['uses', 'distance', 'recent', 'name']),
        error_messages={
            'invalid': 'Sort must be a string',
            'validator_failed': 'Sort must be one of: uses, distance, recent, name'
        }
    )
    limit = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=1000),
        error_messages={
            'invalid': 'Limit must be a valid integer',
            'validator_failed': 'Limit must be between 1 and 1000'
        }
    )
    search = fields.String(
        required=False,
        validate=validate.Length(max=200),
        error_messages={
            'invalid': 'Search query must be a string',
            'validator_failed': 'Search query must be 200 characters or less'
        }
    )
    min_distance = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=500),
        error_messages={
            'invalid': 'Minimum distance must be a valid number',
            'validator_failed': 'Minimum distance must be between 0 and 500 km'
        }
    )
    max_distance = fields.Float(
        required=False,
        validate=validate.Range(min=0, max=500),
        error_messages={
            'invalid': 'Maximum distance must be a valid number',
            'validator_failed': 'Maximum distance must be between 0 and 500 km'
        }
    )
    
    @validates_schema
    def validate_distance_range(self, data, **kwargs):
        """Ensure min_distance is less than max_distance."""
        min_dist = data.get('min_distance')
        max_dist = data.get('max_distance')
        
        if min_dist is not None and max_dist is not None and min_dist > max_dist:
            raise ValidationError(
                'Minimum distance must be less than maximum distance',
                field_name='distance_range'
            )


class MapQuerySchema(Schema):
    """Validation schema for /api/maps/<page_type> endpoint."""
    
    route_id = fields.String(
        required=False,
        validate=validate.Length(max=50),
        error_messages={
            'invalid': 'Route ID must be a string',
            'validator_failed': 'Route ID must be 50 characters or less'
        }
    )
    route_type = fields.String(
        required=False,
        validate=validate.OneOf(['commute', 'long_ride']),
        error_messages={
            'invalid': 'Route type must be a string',
            'validator_failed': 'Route type must be either "commute" or "long_ride"'
        }
    )


def validate_request_args(schema_class):
    """
    Decorator to validate Flask request.args using a Marshmallow schema.
    
    Usage:
        @app.route('/api/endpoint')
        @validate_request_args(MySchema)
        def my_endpoint():
            # request.args is now validated
            pass
    
    Args:
        schema_class: Marshmallow Schema class to use for validation
        
    Returns:
        Decorated function that validates request args before execution
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            schema = schema_class()
            try:
                # Validate and deserialize request args
                validated_data = schema.load(request.args)
                # Store validated data in request context for use in endpoint
                request.validated_args = validated_data
                return f(*args, **kwargs)
            except ValidationError as err:
                # Return 400 Bad Request with validation errors
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid request parameters',
                    'errors': err.messages
                }), 400
        
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# Made with Bob
