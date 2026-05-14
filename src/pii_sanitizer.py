"""
PII Sanitization Module

Provides utilities to sanitize Personally Identifiable Information (PII) from log messages
to protect user privacy while maintaining debugging utility.

Sanitizes:
- GPS coordinates (masks to ~1km precision)
- Street addresses (redacts street names, keeps city/state)
- User identifiers (hashes Strava IDs, tokens)
- Email addresses
- API tokens and keys
"""

import re
import hashlib
from typing import Any, Dict, List, Optional


def sanitize_coordinates(text: str) -> str:
    """
    Mask GPS coordinates to 2 decimal places (~1.1km precision).
    
    Protects exact location while preserving general area for debugging.
    
    Examples:
        "41.8781136, -87.6297982" -> "41.87xx, -87.62xx"
        "Location: (41.878, -87.630)" -> "Location: (41.87xx, -87.63xx)"
    
    Args:
        text: Text potentially containing coordinates
        
    Returns:
        Text with coordinates masked
    """
    # Match various coordinate formats:
    # - "41.8781136, -87.6297982"
    # - "(41.878, -87.630)"
    # - "lat: 41.878, lon: -87.630"
    
    # Pattern for decimal coordinates with 2+ decimal places
    pattern = r'(-?\d+\.\d{2})\d+'
    
    def mask_coord(match):
        """Replace digits after 2nd decimal place with 'xx'"""
        return match.group(1) + 'xx'
    
    return re.sub(pattern, mask_coord, text)


def sanitize_address(text: str) -> str:
    """
    Redact street addresses while keeping city/state for context.
    
    Examples:
        "123 Main Street, Chicago, IL" -> "[STREET], Chicago, IL"
        "456 Oak Ave" -> "[STREET]"
    
    Args:
        text: Text potentially containing addresses
        
    Returns:
        Text with street addresses redacted
    """
    # Match street addresses (number + street name + type)
    street_patterns = [
        r'\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Circle|Cir)',
        r'\d+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Circle|Cir)',
    ]
    
    result = text
    for pattern in street_patterns:
        result = re.sub(pattern, '[STREET]', result, flags=re.IGNORECASE)
    
    return result


def sanitize_user_id(user_id: Any) -> str:
    """
    Hash user IDs to protect identity while maintaining uniqueness.
    
    Uses SHA256 hash truncated to 8 characters for compact representation.
    
    Examples:
        12345678 -> "[ID:a665a45e]"
        "user_abc" -> "[ID:b3d8c9f2]"
        None -> "[NO_ID]"
    
    Args:
        user_id: User identifier (int, str, or None)
        
    Returns:
        Hashed identifier string
    """
    if user_id is None or user_id == '':
        return '[NO_ID]'
    
    # Convert to string and hash
    id_str = str(user_id)
    hash_obj = hashlib.sha256(id_str.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:8]
    
    return f"[ID:{hash_hex}]"


def sanitize_email(text: str) -> str:
    """
    Redact email addresses while preserving domain for debugging.
    
    Examples:
        "user@example.com" -> "[EMAIL]@example.com"
        "contact: john.doe@company.org" -> "contact: [EMAIL]@company.org"
    
    Args:
        text: Text potentially containing email addresses
        
    Returns:
        Text with email local parts redacted
    """
    # Match email pattern and replace local part
    pattern = r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
    return re.sub(pattern, r'[EMAIL]@\1', text)


def sanitize_token(text: str) -> str:
    """
    Redact API tokens and keys while preserving type information.
    
    Detects common token patterns:
    - Bearer tokens
    - API keys
    - OAuth tokens
    - Access tokens
    
    Examples:
        "Bearer abc123def456" -> "Bearer [TOKEN:8]"
        "api_key=xyz789" -> "api_key=[TOKEN:6]"
    
    Args:
        text: Text potentially containing tokens
        
    Returns:
        Text with tokens redacted
    """
    # Pattern for various token formats
    patterns = [
        (r'Bearer\s+([A-Za-z0-9_\-\.]+)', r'Bearer [TOKEN:\1]'),
        (r'(api[_-]?key|token|access[_-]?token|client[_-]?secret)\s*[=:]\s*([A-Za-z0-9_\-\.]+)', r'\1=[TOKEN:\2]'),
        (r'Authorization:\s*([A-Za-z0-9_\-\.]+)', r'Authorization: [TOKEN:\1]'),
    ]
    
    result = text
    for pattern, replacement in patterns:
        def replace_token(match):
            """Replace token with length indicator"""
            if len(match.groups()) == 1:
                token = match.group(1)
                return f"Bearer [TOKEN:{len(token)}]"
            else:
                key_name = match.group(1)
                token = match.group(2)
                return f"{key_name}=[TOKEN:{len(token)}]"
        
        result = re.sub(pattern, replace_token, result, flags=re.IGNORECASE)
    
    return result


def sanitize_strava_id(text: str) -> str:
    """
    Hash Strava activity IDs and athlete IDs.
    
    Examples:
        "activity_id: 12345678901" -> "activity_id: [STRAVA:a665a45e]"
        "athlete: 9876543" -> "athlete: [STRAVA:b3d8c9f2]"
    
    Args:
        text: Text potentially containing Strava IDs
        
    Returns:
        Text with Strava IDs hashed
    """
    # Pattern for Strava IDs (typically 8-11 digit numbers)
    patterns = [
        r'(activity[_-]?id|athlete[_-]?id|strava[_-]?id)\s*[=:]\s*(\d{7,11})',
        r'(activity|athlete)\s*[=:]\s*(\d{7,11})',
    ]
    
    result = text
    for pattern in patterns:
        def replace_id(match):
            """Replace ID with hash"""
            prefix = match.group(1)
            strava_id = match.group(2)
            hash_obj = hashlib.sha256(strava_id.encode('utf-8'))
            hash_hex = hash_obj.hexdigest()[:8]
            return f"{prefix}: [STRAVA:{hash_hex}]"
        
        result = re.sub(pattern, replace_id, result, flags=re.IGNORECASE)
    
    return result


def sanitize_log_message(message: Any) -> str:
    """
    Apply all sanitization rules to a log message.
    
    This is the main entry point for sanitizing log messages.
    Applies all sanitization functions in sequence.
    
    Args:
        message: Log message (any type, will be converted to string)
        
    Returns:
        Sanitized message string
    """
    # Convert to string if not already
    text = str(message)
    
    # Apply all sanitization rules
    text = sanitize_coordinates(text)
    text = sanitize_address(text)
    text = sanitize_email(text)
    text = sanitize_token(text)
    text = sanitize_strava_id(text)
    
    return text


def sanitize_dict(data: Dict[str, Any], keys_to_sanitize: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sanitize specific keys in a dictionary (for structured logging).
    
    Useful for sanitizing JSON payloads or structured log data.
    
    Args:
        data: Dictionary to sanitize
        keys_to_sanitize: List of keys to sanitize (default: common PII keys)
        
    Returns:
        Dictionary with sanitized values
    """
    # Define coordinate-related keys
    coordinate_keys = {'lat', 'latitude', 'lon', 'longitude', 'coordinates', 'latlng', 'start_latlng', 'end_latlng'}
    id_keys = {'user_id', 'athlete_id', 'activity_id'}
    
    if keys_to_sanitize is None:
        keys_to_sanitize = [
            'lat', 'latitude', 'lon', 'longitude',
            'coordinates', 'latlng', 'start_latlng', 'end_latlng',
            'address', 'street', 'location',
            'email', 'user_id', 'athlete_id', 'activity_id',
            'token', 'access_token', 'api_key', 'client_secret',
        ]
    
    sanitized = data.copy()
    
    for key in keys_to_sanitize:
        if key in sanitized:
            value = sanitized[key]
            
            # Handle different value types based on key type
            if key in coordinate_keys:
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    # Coordinate pair - truncate to 2 decimal places
                    sanitized[key] = [round(float(value[0]), 2), round(float(value[1]), 2)]
                elif isinstance(value, (int, float)):
                    # Single coordinate value - truncate to 2 decimal places
                    sanitized[key] = round(float(value), 2)
                else:
                    # Apply string sanitization
                    sanitized[key] = sanitize_log_message(value)
            elif key in id_keys:
                # Hash IDs
                sanitized[key] = sanitize_user_id(value)
            else:
                # Apply general sanitization for other PII types (including custom keys)
                sanitized[key] = sanitize_log_message(value)
    
    return sanitized

# Made with Bob
