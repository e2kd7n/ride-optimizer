# Privacy Policy

**Last Updated:** May 14, 2026  
**Effective Date:** May 14, 2026

## Introduction

Ride Optimizer ("we", "our", or "the application") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our cycling route optimization application.

## Information We Collect

### 1. Data from Third-Party Services

#### Strava Integration
When you connect your Strava account, we collect:
- **Activity data**: Routes, timestamps, distances, elevations, heart rate data
- **Athlete information**: Athlete ID (hashed in logs), activity preferences
- **GPS coordinates**: Route polylines and location data
- **Performance metrics**: Speed, power, cadence (if available)

**Legal basis (GDPR)**: Consent - You explicitly authorize access when connecting your Strava account.

#### Weather API Services
We collect weather data based on your activity locations:
- **Location coordinates**: Used to fetch relevant weather forecasts
- **Weather preferences**: Temperature units, wind speed preferences

**Legal basis (GDPR)**: Legitimate interest - Necessary to provide route recommendations.

### 2. Application-Generated Data

We create and store:
- **Route analysis**: Grouped routes, similarity scores, difficulty ratings
- **Recommendations**: Commute suggestions, long ride plans
- **User preferences**: Favorite routes, notification settings
- **Cache data**: Encrypted activity cache for performance optimization

### 3. Technical Data

We automatically collect:
- **Log data**: Application events, errors, performance metrics (with PII sanitization)
- **System information**: Browser type, operating system, IP address (not stored long-term)
- **Usage statistics**: Feature usage, API call patterns

## How We Use Your Information

We use collected information to:

1. **Provide core functionality**:
   - Analyze your cycling routes and identify patterns
   - Generate weather-aware route recommendations
   - Create personalized commute suggestions
   - Plan optimal long rides based on your history

2. **Improve the application**:
   - Debug technical issues
   - Optimize performance
   - Develop new features based on usage patterns

3. **Ensure security**:
   - Detect and prevent unauthorized access
   - Monitor for suspicious activity
   - Maintain audit logs for security events

## Data Storage and Security

### Encryption

- **OAuth tokens**: Encrypted using Fernet symmetric encryption (AES-128)
- **Cache data**: Encrypted with separate encryption keys
- **Encryption keys**: Auto-generated and stored in `config/` directory with 0600 permissions
- **In transit**: All API communications use HTTPS/TLS

### File Permissions

All sensitive files are automatically set to owner-only access (0600):
- `config/credentials.json` - OAuth tokens
- `config/.token_encryption_key` - Token encryption key
- `config/.cache_encryption_key` - Cache encryption key
- `cache/activities_cache.json` - Encrypted activity data

### PII Protection in Logs

We implement comprehensive PII sanitization for all logging:

#### Protected Information Types

1. **GPS Coordinates**: Masked to 2 decimal places (~1.1km precision)
   - Example: `41.8781136, -87.6297982` → `41.87xx, -87.62xx`

2. **Street Addresses**: Street names/numbers redacted, city/state preserved
   - Example: `123 Main Street, Chicago, IL` → `[STREET], Chicago, IL`

3. **User Identifiers**: Hashed using SHA256
   - Example: `user_id: 12345678` → `user_id: [ID:a665a45e]`

4. **Email Addresses**: Local part redacted, domain preserved
   - Example: `user@example.com` → `[EMAIL]@example.com`

5. **API Tokens**: Replaced with length indicator
   - Example: `Bearer abc123def456` → `Bearer [TOKEN:12]`

6. **Strava IDs**: Activity and athlete IDs hashed
   - Example: `activity_id: 12345678901` → `activity_id: [STRAVA:a665a45e]`

#### Implementation

All logging uses `SecureLogger` which automatically sanitizes PII:

```python
from src.secure_logger import SecureLogger
logger = SecureLogger(__name__)
logger.info("User at location: 41.8781136, -87.6297982")
# Logs: "User at location: 41.87xx, -87.62xx"
```

### Security Audit Log

Sensitive operations are logged separately:
- **Location**: `logs/security_audit.log`
- **Includes**: Authentication events, credential access, cache operations
- **Does not propagate**: Separate from console/main logs

## Data Retention

### Active Data
- **Activity cache**: Retained while you use the application
- **Route analysis**: Retained for recommendation generation
- **Preferences**: Retained until you delete them

### Logs
- **Application logs**: Rotated daily, retained for 30 days
- **Security audit logs**: Retained for 90 days
- **Error logs**: Retained for 60 days

### Deletion
You can request deletion of your data at any time (see "Your Rights" section).

## Data Sharing and Disclosure

### We DO NOT:
- Sell your personal information to third parties
- Share your data with advertisers
- Use your data for marketing purposes
- Transfer data outside necessary service providers

### We MAY share data:
- **With your consent**: When you explicitly authorize sharing
- **For legal compliance**: If required by law or legal process
- **To protect rights**: To enforce our terms or protect safety
- **Service providers**: Strava API, weather APIs (see below)

### Third-Party Services

#### Strava
- **Purpose**: Activity data retrieval
- **Data shared**: OAuth authorization token
- **Privacy policy**: https://www.strava.com/legal/privacy
- **Your control**: Revoke access anytime via Strava settings

#### Weather APIs
- **Purpose**: Weather forecast retrieval
- **Data shared**: GPS coordinates (approximate location)
- **Privacy policy**: Varies by provider (OpenWeatherMap, Weather.gov)
- **Data minimization**: Only coordinates needed for forecasts

## Your Rights

### Under GDPR (EU Residents)

You have the right to:

1. **Access**: Request a copy of your personal data
2. **Rectification**: Correct inaccurate data
3. **Erasure**: Request deletion of your data ("right to be forgotten")
4. **Restriction**: Limit how we process your data
5. **Portability**: Receive your data in a machine-readable format
6. **Object**: Object to processing based on legitimate interests
7. **Withdraw consent**: Revoke authorization at any time

### Under CCPA (California Residents)

You have the right to:

1. **Know**: What personal information we collect and how it's used
2. **Delete**: Request deletion of your personal information
3. **Opt-out**: Opt out of sale of personal information (we don't sell data)
4. **Non-discrimination**: Equal service regardless of privacy choices

### How to Exercise Your Rights

To exercise any of these rights:

1. **Email**: [Contact information to be added]
2. **GitHub Issue**: Open an issue with the `privacy` label
3. **In-app**: Use the "Delete My Data" feature (when available)

We will respond to requests within:
- **GDPR**: 30 days (may extend to 60 days for complex requests)
- **CCPA**: 45 days (may extend to 90 days with notice)

## Cookies and Tracking

### Current Implementation
The application currently does NOT use:
- Cookies for tracking
- Third-party analytics
- Advertising trackers
- Cross-site tracking

### Session Management
- **Local storage**: Used for temporary session data
- **No persistent tracking**: Session data cleared on logout

### Future Changes
If we implement cookies or tracking in the future:
- We will update this policy
- We will obtain your consent where required
- You will have opt-out options

## Children's Privacy

Ride Optimizer is not intended for users under 13 years of age. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately.

## International Data Transfers

### Current Deployment
The application is designed for self-hosted deployment. Data remains on your infrastructure.

### Cloud Deployment
If deployed to cloud services:
- Data may be transferred internationally
- We use appropriate safeguards (encryption, access controls)
- EU residents: We comply with GDPR transfer requirements

## Changes to This Policy

We may update this Privacy Policy periodically. Changes will be:

1. **Posted**: Updated policy published to this document
2. **Dated**: "Last Updated" date modified
3. **Notified**: Significant changes communicated via:
   - In-app notification
   - GitHub release notes
   - Email (if we have your contact information)

### Your Continued Use
Continued use of the application after policy changes constitutes acceptance of the updated policy.

## Data Breach Notification

In the event of a data breach:

1. **Assessment**: We will assess the scope and impact within 24 hours
2. **Notification**: Affected users notified within 72 hours (GDPR requirement)
3. **Remediation**: Immediate steps taken to secure data
4. **Transparency**: Public disclosure via GitHub security advisory

## Privacy by Design

Our privacy approach follows these principles:

1. **Proactive not reactive**: Privacy built into design from the start
2. **Privacy as default**: Maximum privacy settings by default
3. **Privacy embedded**: Integrated into functionality, not added later
4. **Full functionality**: Privacy without sacrificing features
5. **End-to-end security**: Protection throughout data lifecycle
6. **Visibility and transparency**: Clear documentation and open source
7. **User-centric**: Respect for user privacy above all

## Open Source Transparency

Ride Optimizer is open source. You can:

- **Review code**: Verify our privacy claims
- **Audit security**: Examine encryption and sanitization
- **Contribute**: Improve privacy protections
- **Fork**: Self-host with full control over your data

**Repository**: https://github.com/e2kd7n/ride-optimizer

## Compliance Certifications

### Current Status
- **GDPR**: Compliant with EU data protection requirements
- **CCPA**: Compliant with California privacy law
- **OWASP**: Follows OWASP logging and security guidelines

### Ongoing Compliance
We regularly review and update our practices to maintain compliance with:
- Data protection regulations
- Security best practices
- Industry standards

## Contact Information

For privacy-related questions, concerns, or requests:

### General Inquiries
- **GitHub Issues**: https://github.com/e2kd7n/ride-optimizer/issues (use `privacy` label)
- **Security Issues**: Use GitHub Security Advisories for sensitive matters

### Data Protection Officer
[To be designated if required by GDPR]

### Response Time
- **General inquiries**: 5 business days
- **Rights requests**: 30 days (GDPR), 45 days (CCPA)
- **Security issues**: 24 hours

## Definitions

- **Personal Data**: Information relating to an identified or identifiable person
- **Processing**: Any operation performed on personal data
- **Controller**: Entity determining purposes and means of processing (you, if self-hosted)
- **Processor**: Entity processing data on behalf of controller (the application)
- **PII**: Personally Identifiable Information (GPS, addresses, IDs, etc.)

## Legal Basis for Processing (GDPR)

| Data Type | Legal Basis | Purpose |
|-----------|-------------|---------|
| Strava activity data | Consent | Core functionality |
| Weather data | Legitimate interest | Route recommendations |
| Log data (sanitized) | Legitimate interest | Security and debugging |
| User preferences | Consent | Personalization |
| Security audit logs | Legal obligation | Security compliance |

## Acknowledgments

This privacy policy was created with reference to:
- GDPR requirements (EU Regulation 2016/679)
- CCPA requirements (California Civil Code §1798.100)
- OWASP Logging Cheat Sheet
- Privacy by Design principles (Ann Cavoukian)

---

**Version**: 1.0.0  
**Document ID**: PRIVACY-2026-05-14  
**Next Review**: August 14, 2026 (quarterly review)