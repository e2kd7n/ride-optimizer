"""
Tests for PII sanitization module.

Verifies that sensitive information is properly sanitized from log messages
while maintaining debugging utility.
"""

import pytest
from src.pii_sanitizer import (
    sanitize_coordinates,
    sanitize_address,
    sanitize_user_id,
    sanitize_email,
    sanitize_token,
    sanitize_strava_id,
    sanitize_log_message,
    sanitize_dict,
)


class TestCoordinateSanitization:
    """Test GPS coordinate sanitization."""
    
    def test_sanitize_basic_coordinates(self):
        """Test basic coordinate format."""
        text = "Location: 41.8781136, -87.6297982"
        result = sanitize_coordinates(text)
        assert "41.87xx" in result
        assert "-87.62xx" in result
        assert "41.8781136" not in result
        assert "-87.6297982" not in result
    
    def test_sanitize_coordinates_in_parentheses(self):
        """Test coordinates in parentheses."""
        text = "Start point: (41.878, -87.630)"
        result = sanitize_coordinates(text)
        assert "(41.87xx, -87.63xx)" in result
    
    def test_sanitize_coordinates_with_labels(self):
        """Test coordinates with lat/lon labels."""
        text = "lat: 41.8781136, lon: -87.6297982"
        result = sanitize_coordinates(text)
        assert "lat: 41.87xx" in result
        assert "lon: -87.62xx" in result
    
    def test_preserve_low_precision_coordinates(self):
        """Test that already low-precision coordinates are preserved."""
        text = "Approximate location: 41.87, -87.62"
        result = sanitize_coordinates(text)
        # Should not add 'xx' to already 2-decimal coordinates
        assert "41.87" in result
        assert "-87.62" in result
    
    def test_multiple_coordinates(self):
        """Test multiple coordinate pairs in one message."""
        text = "Route from 41.8781, -87.6298 to 41.9012, -87.6543"
        result = sanitize_coordinates(text)
        assert "41.87xx" in result
        assert "-87.62xx" in result
        assert "41.90xx" in result
        assert "-87.65xx" in result


class TestAddressSanitization:
    """Test street address sanitization."""
    
    def test_sanitize_street_address(self):
        """Test basic street address."""
        text = "Located at 123 Main Street, Chicago, IL"
        result = sanitize_address(text)
        assert "[STREET]" in result
        assert "Chicago, IL" in result
        assert "123 Main Street" not in result
    
    def test_sanitize_avenue(self):
        """Test avenue address."""
        text = "456 Oak Avenue"
        result = sanitize_address(text)
        assert "[STREET]" in result
        assert "456 Oak Avenue" not in result
    
    def test_sanitize_abbreviated_street(self):
        """Test abbreviated street types."""
        text = "789 Elm St, Springfield"
        result = sanitize_address(text)
        assert "[STREET]" in result
        assert "Springfield" in result
    
    def test_preserve_city_state(self):
        """Test that city and state are preserved."""
        text = "100 Park Blvd, San Francisco, CA 94102"
        result = sanitize_address(text)
        assert "San Francisco, CA 94102" in result
        assert "100 Park Blvd" not in result


class TestUserIdSanitization:
    """Test user ID hashing."""
    
    def test_sanitize_numeric_id(self):
        """Test numeric user ID."""
        result = sanitize_user_id(12345678)
        assert result.startswith("[ID:")
        assert result.endswith("]")
        assert "12345678" not in result
        assert len(result) == 13  # [ID:xxxxxxxx]
    
    def test_sanitize_string_id(self):
        """Test string user ID."""
        result = sanitize_user_id("user_abc123")
        assert result.startswith("[ID:")
        assert "user_abc123" not in result
    
    def test_sanitize_none_id(self):
        """Test None user ID."""
        result = sanitize_user_id(None)
        assert result == "[NO_ID]"
    
    def test_sanitize_empty_id(self):
        """Test empty string ID."""
        result = sanitize_user_id("")
        assert result == "[NO_ID]"
    
    def test_consistent_hashing(self):
        """Test that same ID produces same hash."""
        id1 = sanitize_user_id(12345)
        id2 = sanitize_user_id(12345)
        assert id1 == id2


class TestEmailSanitization:
    """Test email address sanitization."""
    
    def test_sanitize_basic_email(self):
        """Test basic email address."""
        text = "Contact: user@example.com"
        result = sanitize_email(text)
        assert "[EMAIL]@example.com" in result
        assert "user@example.com" not in result
    
    def test_sanitize_complex_email(self):
        """Test complex email with dots and plus."""
        text = "Email: john.doe+test@company.org"
        result = sanitize_email(text)
        assert "[EMAIL]@company.org" in result
        assert "john.doe" not in result
    
    def test_preserve_domain(self):
        """Test that domain is preserved."""
        text = "admin@example.com"
        result = sanitize_email(text)
        assert "example.com" in result
    
    def test_multiple_emails(self):
        """Test multiple emails in one message."""
        text = "From: user1@example.com to user2@test.org"
        result = sanitize_email(text)
        assert "[EMAIL]@example.com" in result
        assert "[EMAIL]@test.org" in result


class TestTokenSanitization:
    """Test API token and key sanitization."""
    
    def test_sanitize_bearer_token(self):
        """Test Bearer token."""
        text = "Authorization: Bearer abc123def456ghi789"
        result = sanitize_token(text)
        assert "Bearer [TOKEN:" in result
        assert "abc123def456ghi789" not in result
    
    def test_sanitize_api_key(self):
        """Test API key."""
        text = "api_key=secret123456"
        result = sanitize_token(text)
        assert "api_key=[TOKEN:" in result
        assert "secret123456" not in result
    
    def test_sanitize_access_token(self):
        """Test access token."""
        text = "access_token: xyz789abc123"
        result = sanitize_token(text)
        assert "access_token=[TOKEN:" in result
        assert "xyz789abc123" not in result
    
    def test_sanitize_client_secret(self):
        """Test client secret."""
        text = "client_secret=verysecret123"
        result = sanitize_token(text)
        assert "client_secret=[TOKEN:" in result
        assert "verysecret123" not in result


class TestStravaIdSanitization:
    """Test Strava ID sanitization."""
    
    def test_sanitize_activity_id(self):
        """Test Strava activity ID."""
        text = "activity_id: 12345678901"
        result = sanitize_strava_id(text)
        assert "[STRAVA:" in result
        assert "12345678901" not in result
    
    def test_sanitize_athlete_id(self):
        """Test Strava athlete ID."""
        text = "athlete: 9876543"
        result = sanitize_strava_id(text)
        assert "[STRAVA:" in result
        assert "9876543" not in result
    
    def test_sanitize_strava_id_with_equals(self):
        """Test Strava ID with equals sign."""
        text = "strava_id=11223344556"
        result = sanitize_strava_id(text)
        assert "[STRAVA:" in result
        assert "11223344556" not in result


class TestLogMessageSanitization:
    """Test complete log message sanitization."""
    
    def test_sanitize_complex_message(self):
        """Test message with multiple PII types."""
        text = "User 12345 at 41.8781, -87.6298 contacted user@example.com from 123 Main St"
        result = sanitize_log_message(text)
        
        # Check coordinates sanitized
        assert "41.87xx" in result
        assert "-87.62xx" in result
        
        # Check email sanitized
        assert "[EMAIL]@example.com" in result
        
        # Check address sanitized
        assert "[STREET]" in result
    
    def test_sanitize_weather_api_call(self):
        """Test typical weather API log message."""
        text = "Fetching weather for location: 41.8781136, -87.6297982"
        result = sanitize_log_message(text)
        assert "41.87xx, -87.62xx" in result
        assert "41.8781136" not in result
    
    def test_sanitize_strava_api_call(self):
        """Test typical Strava API log message."""
        text = "Fetching activity_id: 12345678901 for athlete: 9876543"
        result = sanitize_log_message(text)
        assert "[STRAVA:" in result
        assert "12345678901" not in result
        assert "9876543" not in result
    
    def test_sanitize_preserves_non_pii(self):
        """Test that non-PII data is preserved."""
        text = "Route analysis complete: 15.5 miles, 45 minutes, elevation gain 500ft"
        result = sanitize_log_message(text)
        assert "15.5 miles" in result
        assert "45 minutes" in result
        assert "500ft" in result


class TestDictSanitization:
    """Test dictionary sanitization for structured logging."""
    
    def test_sanitize_coordinate_keys(self):
        """Test sanitizing coordinate keys."""
        data = {
            'lat': 41.8781136,
            'lon': -87.6297982,
            'distance': 15.5
        }
        result = sanitize_dict(data)
        
        # Coordinates should be truncated
        assert result['lat'] == 41.88
        assert result['lon'] == -87.63
        
        # Non-PII preserved
        assert result['distance'] == 15.5
    
    def test_sanitize_latlng_tuple(self):
        """Test sanitizing lat/lng tuple."""
        data = {
            'start_latlng': [41.8781136, -87.6297982],
            'name': 'Morning Commute'
        }
        result = sanitize_dict(data)
        
        # Coordinates truncated
        assert result['start_latlng'][0] == 41.88
        assert result['start_latlng'][1] == -87.63
        
        # Name preserved
        assert result['name'] == 'Morning Commute'
    
    def test_sanitize_user_id_key(self):
        """Test sanitizing user ID key."""
        data = {
            'user_id': 12345678,
            'activity_count': 100
        }
        result = sanitize_dict(data)
        
        # ID should be hashed
        assert result['user_id'].startswith('[ID:')
        assert '12345678' not in str(result['user_id'])
        
        # Count preserved
        assert result['activity_count'] == 100
    
    def test_sanitize_custom_keys(self):
        """Test sanitizing with custom key list."""
        data = {
            'secret_field': 'user@example.com at 41.8781, -87.6298',
            'public_field': 'public_data'
        }
        result = sanitize_dict(data, keys_to_sanitize=['secret_field'])
        
        # Only specified key sanitized (email and coordinates)
        assert '[EMAIL]@example.com' in str(result['secret_field'])
        assert '41.87xx' in str(result['secret_field'])
        assert 'user@example.com' not in str(result['secret_field'])
        assert result['public_field'] == 'public_data'


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_string(self):
        """Test empty string."""
        result = sanitize_log_message("")
        assert result == ""
    
    def test_none_value(self):
        """Test None value."""
        result = sanitize_log_message(None)
        assert result == "None"
    
    def test_numeric_value(self):
        """Test numeric value."""
        result = sanitize_log_message(12345)
        assert result == "12345"
    
    def test_no_pii_in_message(self):
        """Test message with no PII."""
        text = "Analysis complete: 10 routes processed"
        result = sanitize_log_message(text)
        assert result == text
    
    def test_unicode_characters(self):
        """Test message with unicode characters."""
        text = "Route: Café → Park 🚴"
        result = sanitize_log_message(text)
        assert "Café" in result
        assert "Park" in result
        assert "🚴" in result


@pytest.mark.unit
class TestSecureLoggerIntegration:
    """Test SecureLogger integration with sanitization."""
    
    def test_secure_logger_import(self):
        """Test that SecureLogger can be imported."""
        from src.secure_logger import SecureLogger
        logger = SecureLogger(__name__)
        assert logger is not None
    
    def test_secure_logger_sanitizes(self):
        """Test that SecureLogger applies sanitization."""
        from src.secure_logger import SecureLogger
        import logging
        from io import StringIO
        
        # Create logger with string handler
        logger = SecureLogger('test_logger')
        
        # Add string handler to capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log message with PII
        logger.info("User at location: 41.8781136, -87.6297982")
        
        # Check output is sanitized
        output = stream.getvalue()
        assert "41.87xx" in output
        assert "41.8781136" not in output

# Made with Bob
