# Privacy & PII Protection

This document describes the privacy protections implemented in the Ride Optimizer application to protect user data.

## Overview

The Ride Optimizer implements comprehensive PII (Personally Identifiable Information) sanitization for all logging to ensure that sensitive user data is never logged in plain text. This protects user privacy while maintaining debugging utility.

## What is Protected

The following types of sensitive information are automatically sanitized in all log messages:

### 1. GPS Coordinates
- **Protection**: Coordinates are masked to 2 decimal places (~1.1km precision)
- **Example**: `41.8781136, -87.6297982` → `41.87xx, -87.62xx`
- **Rationale**: Preserves general area for debugging while preventing exact location tracking

### 2. Street Addresses
- **Protection**: Street names and numbers are redacted, city/state preserved
- **Example**: `123 Main Street, Chicago, IL` → `[STREET], Chicago, IL`
- **Rationale**: Maintains geographic context while protecting exact addresses

### 3. User Identifiers
- **Protection**: User IDs, athlete IDs, and activity IDs are hashed using SHA256
- **Example**: `user_id: 12345678` → `user_id: [ID:a665a45e]`
- **Rationale**: Maintains uniqueness for debugging while preventing identity correlation

### 4. Email Addresses
- **Protection**: Local part redacted, domain preserved
- **Example**: `user@example.com` → `[EMAIL]@example.com`
- **Rationale**: Preserves domain information for debugging while protecting identity

### 5. API Tokens & Keys
- **Protection**: Token values replaced with length indicator
- **Example**: `Bearer abc123def456` → `Bearer [TOKEN:12]`
- **Rationale**: Prevents credential leakage while showing token presence

### 6. Strava IDs
- **Protection**: Activity and athlete IDs are hashed
- **Example**: `activity_id: 12345678901` → `activity_id: [STRAVA:a665a45e]`
- **Rationale**: Prevents correlation with Strava accounts while maintaining uniqueness

## Implementation

### Automatic Sanitization

All logging in the application uses the `SecureLogger` wrapper which automatically sanitizes PII before writing to logs:

```python
from src.secure_logger import SecureLogger

logger = SecureLogger(__name__)
logger.info("User at location: 41.8781136, -87.6297982")
# Logs: "User at location: 41.87xx, -87.62xx"
```

### Files Using Secure Logging

The following critical files have been updated to use secure logging:

- `launch.py` - API server logging
- `src/weather_fetcher.py` - Weather API calls with coordinates
- `app/services/commute_service.py` - Commute recommendations
- `src/location_finder.py` - Location clustering and geocoding

### Manual Sanitization

For cases where you need to manually sanitize data (e.g., in error messages or structured logging):

```python
from src.pii_sanitizer import sanitize_log_message, sanitize_dict

# Sanitize a string message
safe_message = sanitize_log_message("User 12345 at 41.8781, -87.6298")

# Sanitize a dictionary (for structured logging)
data = {'lat': 41.8781136, 'lon': -87.6297982, 'user_id': 12345}
safe_data = sanitize_dict(data)
```

## Testing

Comprehensive tests verify that PII sanitization works correctly:

```bash
# Run PII sanitization tests
python3 -m pytest tests/test_pii_sanitizer.py -v
```

The test suite includes 40+ tests covering:
- Coordinate sanitization in various formats
- Address redaction
- User ID hashing
- Email sanitization
- Token redaction
- Strava ID hashing
- Edge cases and error handling

## Security Audit

All PII sanitization events are logged to the security audit log:

- **Location**: `logs/security_audit.log`
- **Separate from main logs**: Does not propagate to console
- **Includes**: Authentication events, credential access, cache operations

## Best Practices

When adding new logging:

1. **Always use SecureLogger**: Import from `src.secure_logger`, not `logging`
2. **Test with real data**: Verify PII is sanitized in development
3. **Review logs**: Periodically audit logs to ensure no PII leakage
4. **Add new patterns**: If you identify new PII types, add sanitization rules to `src/pii_sanitizer.py`

## Privacy by Design

The PII sanitization system follows privacy-by-design principles:

- **Default protection**: All logging is sanitized by default
- **Minimal data**: Only log what's necessary for debugging
- **Transparency**: Clear documentation of what's protected and how
- **Testing**: Comprehensive test coverage ensures protection works
- **Auditability**: Security audit log tracks sensitive operations

## Compliance

This implementation helps meet privacy requirements:

- **GDPR**: Minimizes personal data in logs
- **CCPA**: Protects California residents' location data
- **General best practices**: Follows OWASP logging guidelines

## Future Enhancements

Potential improvements to consider:

- [ ] Configurable sanitization levels (strict/moderate/minimal)
- [ ] Log encryption at rest
- [ ] Automated log rotation and secure deletion
- [ ] PII detection in database queries
- [ ] Real-time PII scanning in production logs

## Questions?

For questions about privacy protections or to report potential PII leakage, please open a GitHub issue with the `security` label.