# Bob Skills - Development Guidelines & Best Practices

**Project:** Ride Optimizer
**Last Updated:** 2026-03-25  
**Purpose:** Consolidated development guidelines, coding standards, and workflow procedures for AI-assisted development

## Browser Preferences

**Default Browser:** Chrome  
**Authentication Browser:** Firefox

### Rules
- **All web links**: Open in Chrome (default browser)
- **Bob authentication requests**: Open in Firefox
  - This includes OAuth flows, login pages, and credential verification
  - Ensures separation between development browsing and authentication sessions

---
---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Workflow](#development-workflow)
3. [Coding Standards](#coding-standards)
4. [Security Guidelines](#security-guidelines)
5. [API Usage & Rate Limiting](#api-usage--rate-limiting)
6. [Testing Strategy](#testing-strategy)
7. [Documentation Standards](#documentation-standards)
8. [Code Review Process](#code-review-process)
9. [Issue Management](#issue-management)
10. [Maintenance Procedures](#maintenance-procedures)

---

## Project Overview

### Core Purpose
Analyze Strava cycling activities to determine optimal commute routes between home and work, considering time, distance, safety, and weather factors.

### Key Technologies
- **Python 3.8+**: Core language
- **stravalib**: Strava API client
- **pandas/numpy**: Data analysis
- **scikit-learn**: Clustering (DBSCAN)
- **folium**: Interactive maps
- **jinja2**: HTML templating
- **Open-Meteo API**: Weather data
- **Nominatim/OSM**: Geocoding

### Architecture Principles
- **Modular design**: Each module has single responsibility
- **Configuration-driven**: User preferences in YAML
- **Cache-first**: Minimize API calls
- **Error resilience**: Graceful degradation
- **Security-conscious**: Protect credentials and tokens

---

## Development Workflow

### 1. Task Planning

**Before Starting:**
- Review existing documentation (README, TECHNICAL_SPEC, PLAN)
- Check open issues in ISSUE_PRIORITIES.md
- Identify dependencies and potential conflicts
- Create TODO list for multi-step tasks

**Task Breakdown:**
```markdown
[ ] Research and design
[ ] Implementation
[ ] Testing
[ ] Documentation
[ ] Code review
[ ] Deployment
```

### 2. Implementation Process

**Step-by-Step:**
1. **Read relevant files** - Understand current implementation
2. **Make changes** - Use appropriate tools (apply_diff, write_to_file)
3. **Test changes** - Run commands to verify
4. **Update documentation** - Keep docs in sync
5. **Commit with clear messages** - Descriptive commit messages

**Tool Selection:**
- `apply_diff`: For targeted code changes
- `write_to_file`: For new files or complete rewrites
- `insert_content`: For adding lines at specific positions
- `read_file`: Always read related files together (up to 5)

### 3. Git Workflow

**Commit Message Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `security`: Security improvements

**Example:**
```
feat: Add wind-aware route optimization

- Implement WindImpactCalculator class
- Calculate headwind/tailwind/crosswind components
- Add weather scoring to route optimization
- Update report template with wind analysis

Closes #54
```

### 4. Testing Before Commit

**Always Test:**
```bash
# Verify imports
python3 -c "import src.module_name"

# Run specific functionality
python3 main.py --analyze

# Check for syntax errors
python3 -m py_compile src/*.py
```

---

## Coding Standards

### Python Style Guide

**Follow PEP 8 with these specifics:**

```python
# Imports: Standard library, third-party, local
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from stravalib.client import Client

from src.config import load_config
from src.auth import StravaAuthenticator

# Constants: UPPER_CASE
MAX_ACTIVITIES = 1000
DEFAULT_CACHE_DURATION = 3600

# Classes: PascalCase
class RouteAnalyzer:
    """Analyze and group similar routes."""
    
    def __init__(self, activities: List[Activity], config: Dict):
        """Initialize analyzer with activities and configuration."""
        self.activities = activities
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def analyze_routes(self) -> List[RouteGroup]:
        """Analyze routes and return grouped results."""
        pass

# Functions: snake_case
def calculate_similarity(route1: Route, route2: Route) -> float:
    """Calculate similarity between two routes using Fréchet distance.
    
    Args:
        route1: First route to compare
        route2: Second route to compare
    
    Returns:
        Similarity score between 0 and 1
    """
    pass

# Type hints: Always use for function signatures
def process_activities(
    activities: List[Activity],
    min_distance: float = 2.0,
    max_distance: float = 30.0
) -> List[Activity]:
    """Filter activities by distance criteria."""
    pass
```

### Error Handling

**Always handle errors gracefully:**

```python
import logging

logger = logging.getLogger(__name__)

def fetch_weather_data(lat: float, lon: float) -> Optional[Dict]:
    """Fetch weather data with error handling."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.warning("Weather API timeout, using cached data")
        return load_cached_weather()
    except requests.RequestException as e:
        logger.error(f"Weather API error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error fetching weather: {e}")
        return None
```

### Logging Standards

```python
import logging

# Module-level logger
logger = logging.getLogger(__name__)

# Log levels:
logger.debug("Detailed diagnostic information")
logger.info("General informational messages")
logger.warning("Warning messages for recoverable issues")
logger.error("Error messages for failures")
logger.exception("Error with full traceback")

# Security audit logging
security_logger = logging.getLogger('security_audit')
security_logger.info(f"AUTH_SUCCESS: {timestamp}")
```

### Documentation Standards

**Docstrings:**
```python
def calculate_route_score(
    route_group: RouteGroup,
    weights: Dict[str, float]
) -> float:
    """Calculate composite score for a route group.
    
    Combines time, distance, safety, and weather scores using
    configurable weights to produce a single optimization score.
    
    Args:
        route_group: RouteGroup containing route metrics
        weights: Dictionary of scoring weights
            - time: Weight for time score (0-1)
            - distance: Weight for distance score (0-1)
            - safety: Weight for safety score (0-1)
            - weather: Weight for weather score (0-1)
    
    Returns:
        Composite score between 0 and 100
    
    Raises:
        ValueError: If weights don't sum to 1.0
    
    Example:
        >>> weights = {'time': 0.4, 'distance': 0.3, 'safety': 0.3}
        >>> score = calculate_route_score(route_group, weights)
        >>> print(f"Score: {score:.2f}")
        Score: 87.50
    """
    pass
```

---

## Security Guidelines

### Critical Rules

**NEVER:**
- ❌ Commit `.env` files to git
- ❌ Hardcode API credentials in code
- ❌ Store tokens in plaintext (use encryption)
- ❌ Log sensitive data (tokens, passwords)
- ❌ Share credentials in screenshots or logs

**ALWAYS:**
- ✅ Use environment variables for credentials
- ✅ Encrypt tokens at rest
- ✅ Set restrictive file permissions (0o600)
- ✅ Validate OAuth state parameter (CSRF protection)
- ✅ Implement rate limiting
- ✅ Log security events to audit log

### Credential Management

```python
# .env file (NEVER commit this)
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
TOKEN_ENCRYPTION_KEY=your_encryption_key

# Load from environment
from dotenv import load_dotenv
import os

load_dotenv()
client_id = os.getenv('STRAVA_CLIENT_ID')
if not client_id:
    raise ValueError("STRAVA_CLIENT_ID not found in environment")
```

### Token Storage

```python
from cryptography.fernet import Fernet
import json

class SecureTokenStorage:
    """Encrypted token storage."""
    
    def save_tokens(self, tokens: Dict) -> None:
        """Save tokens with encryption."""
        # Encrypt
        encrypted = self.cipher.encrypt(json.dumps(tokens).encode())
        
        # Write with restrictive permissions
        with open(self.path, 'wb') as f:
            f.write(encrypted)
        os.chmod(self.path, 0o600)
```

### OAuth Security

```python
import secrets

def get_authorization_url(self) -> str:
    """Generate OAuth URL with CSRF protection."""
    # Generate secure state token
    self.state = secrets.token_urlsafe(32)
    
    url = client.authorization_url(
        client_id=self.client_id,
        redirect_uri=self.redirect_uri,
        state=self.state  # CSRF protection
    )
    return url

def validate_callback(self, received_state: str) -> bool:
    """Validate OAuth callback state parameter."""
    if received_state != self.state:
        logger.warning("CSRF attempt detected: invalid state")
        return False
    return True
```

---

## API Usage & Rate Limiting

### Strava API

**Rate Limits:**
- 100 requests per 15 minutes
- 1000 requests per day

**Best Practices:**
```python
# Cache aggressively
def fetch_activities(self, limit: int = 500) -> List[Activity]:
    """Fetch activities with caching."""
    # Check cache first
    cached = self.load_cached_activities()
    if cached and self._is_cache_valid():
        logger.info("Using cached activities")
        return cached
    
    # Fetch from API
    activities = self._fetch_from_api(limit)
    self.cache_activities(activities)
    return activities

# Implement exponential backoff
def _fetch_with_retry(self, url: str, max_retries: int = 3) -> Dict:
    """Fetch with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt
                logger.warning(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

### Nominatim (Geocoding)

**Rate Limits:**
- 1 request per second maximum
- Requires User-Agent header

**Implementation:**
```python
import time
from functools import wraps

def rate_limit(min_interval: float = 1.0):
    """Decorator to enforce rate limiting."""
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(min_interval=1.0)
def geocode_location(lat: float, lon: float) -> Optional[str]:
    """Geocode with rate limiting and caching."""
    # Check cache first
    cached = self._check_cache(lat, lon)
    if cached:
        return cached
    
    # Geocode with proper headers
    headers = {'User-Agent': 'StravaCommuteAnalyzer/1.0'}
    response = requests.get(url, headers=headers, timeout=10)
    
    # Cache result
    self._save_to_cache(lat, lon, result)
    return result
```

### Open-Meteo (Weather)

**Rate Limits:**
- 10,000 requests per day (free tier)
- No authentication required

**Caching Strategy:**
```python
def fetch_weather(self, lat: float, lon: float) -> Dict:
    """Fetch weather with spatial and temporal caching."""
    # Check cache (90-minute expiration)
    cached = self._get_cached_weather(lat, lon, max_age=5400)
    if cached:
        return cached
    
    # Fetch from API
    weather = self._fetch_from_api(lat, lon)
    
    # Save to persistent cache
    self._save_to_cache(lat, lon, weather)
    return weather
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_route_analyzer.py
import pytest
from src.route_analyzer import RouteAnalyzer

def test_calculate_similarity():
    """Test route similarity calculation."""
    route1 = create_mock_route([(0, 0), (1, 1)])
    route2 = create_mock_route([(0, 0), (1, 1)])
    
    similarity = calculate_similarity(route1, route2)
    assert similarity > 0.9, "Identical routes should have high similarity"

def test_group_similar_routes():
    """Test route grouping."""
    routes = create_mock_routes(10)
    analyzer = RouteAnalyzer(routes)
    
    groups = analyzer.group_similar_routes(threshold=0.85)
    assert len(groups) > 0, "Should create at least one group"
```

### Integration Tests

```python
def test_full_workflow():
    """Test complete analysis workflow."""
    # Mock Strava API
    with mock_strava_api():
        # Authenticate
        client = get_authenticated_client()
        
        # Fetch activities
        activities = fetch_activities(client, limit=10)
        assert len(activities) > 0
        
        # Identify locations
        home, work = identify_locations(activities)
        assert home is not None
        assert work is not None
        
        # Analyze routes
        routes = analyze_routes(activities, home, work)
        assert len(routes) > 0
```

### Manual Testing Checklist

Before committing:
- [ ] Run `python3 main.py --auth` (if auth changes)
- [ ] Run `python3 main.py --fetch` (if data fetching changes)
- [ ] Run `python3 main.py --analyze` (if analysis changes)
- [ ] Check generated HTML report opens correctly
- [ ] Verify no errors in console output
- [ ] Test with edge cases (few activities, no GPS data, etc.)

---

## Documentation Standards

### File-Level Documentation

Every Python file should have:
```python
"""Module for route analysis and similarity matching.

This module provides functionality to:
- Extract routes from Strava activities
- Calculate route similarity using Fréchet distance
- Group similar routes together
- Calculate route metrics and statistics

Example:
    >>> analyzer = RouteAnalyzer(activities, home, work)
    >>> groups = analyzer.group_similar_routes()
    >>> print(f"Found {len(groups)} route variants")
"""
```

### README Updates

When adding features, update README.md:
- Add to Features section
- Update Usage section with examples
- Add to Configuration section if configurable
- Update Troubleshooting if needed

### Technical Documentation

Keep these files synchronized:
- **TECHNICAL_SPEC.md**: API signatures, algorithms, data structures
- **IMPLEMENTATION_GUIDE.md**: Step-by-step implementation instructions
- **PLAN.md**: High-level architecture and roadmap
- **WORKFLOW.md**: Data flow diagrams and processes

### Inline Comments

```python
# Good: Explain WHY, not WHAT
# Use Fréchet distance because it considers point order,
# which is critical for route matching (like walking a dog)
frechet_dist = calculate_frechet_distance(route1, route2)

# Bad: Obvious comment
# Calculate Fréchet distance
frechet_dist = calculate_frechet_distance(route1, route2)
```

---

## Code Review Process

### 🔴 CRITICAL: Agent Separation for Code Reviews

**RULE: Code reviews MUST be performed by a different agent than the one who wrote the code.**

This ensures:
- Fresh perspective on the code
- Unbiased review of implementation choices
- Better error detection
- Knowledge transfer between agents

### Review Workflow

**1. Code Author (Agent A):**
```markdown
## Code Submission for Review

**Feature:** Wind-aware route optimization
**Files Changed:**
- src/optimizer.py (added WindImpactCalculator)
- src/weather_fetcher.py (added wind analysis)
- config/config.yaml (added weather weights)

**Changes Summary:**
- Implemented wind impact calculation
- Added weather scoring to optimization
- Updated configuration options

**Testing Done:**
- Unit tests for wind calculations
- Integration test with real weather data
- Manual testing with 50+ routes

**Review Focus Areas:**
- Algorithm correctness
- Performance implications
- Error handling
- Documentation completeness
```

**2. Code Reviewer (Agent B - DIFFERENT AGENT):**
```markdown
## Code Review Checklist

### Functionality
- [ ] Code implements stated requirements
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] Performance is acceptable

### Code Quality
- [ ] Follows coding standards
- [ ] Proper type hints
- [ ] Clear variable names
- [ ] No code duplication

### Security
- [ ] No hardcoded credentials
- [ ] Input validation present
- [ ] No SQL injection risks
- [ ] Proper error messages (no sensitive data)

### Documentation
- [ ] Docstrings complete
- [ ] README updated
- [ ] TECHNICAL_SPEC updated
- [ ] Inline comments where needed

### Testing
- [ ] Unit tests present
- [ ] Tests pass
- [ ] Edge cases tested
- [ ] Manual testing documented

### Review Comments:
1. Line 45: Consider caching wind calculations
2. Line 78: Add type hint for return value
3. Line 120: Error message could be more specific
4. Documentation: Add example to docstring

**Verdict:** ✅ APPROVED with minor changes
```

**3. Code Author Response:**
```markdown
## Review Response

**Changes Made:**
- ✅ Added caching for wind calculations (line 45)
- ✅ Added type hint (line 78)
- ✅ Improved error message (line 120)
- ✅ Added docstring example

**Ready for merge:** YES
```

### Review Standards

**Automatic Rejection Criteria:**
- ❌ No tests for new functionality
- ❌ Hardcoded credentials or secrets
- ❌ Missing documentation for public APIs
- ❌ Breaks existing functionality
- ❌ Security vulnerabilities

**Request Changes:**
- ⚠️ Poor error handling
- ⚠️ Missing type hints
- ⚠️ Unclear variable names
- ⚠️ Insufficient comments for complex logic
- ⚠️ Performance concerns

**Approve:**
- ✅ All checklist items passed
- ✅ Code is clear and maintainable
- ✅ Tests are comprehensive
- ✅ Documentation is complete

---

## Issue Management

### Priority Levels

**P0 - CRITICAL** (Drop Everything)
- Application is down or unusable
- Data loss or corruption
- Security vulnerabilities
- **Action:** Fix immediately

**P1 - HIGH** (Current Sprint)
- Core features broken
- Significant user pain points
- Blocks important workflows
- **Action:** Fix within 1-2 weeks

**P2 - MEDIUM** (Next Sprint)
- Feature improvements
- Moderate user pain points
- Quality of life enhancements
- **Action:** Plan for 2-4 weeks

**P3 - LOW** (Backlog)
- Minor UX improvements
- Edge cases
- Nice-to-have features
- **Action:** Address when time permits

**P4 - FUTURE** (Long-term)
- New features
- Major enhancements
- Long-term improvements
- **Action:** Plan for future releases

### Issue Lifecycle

```
New Issue → Triaged (Priority Assigned) → In Progress → Testing → Closed
```

### GitHub Labels

**Priority Labels:**
- `P0-critical` (#B60205 - Red): Critical priority - immediate attention required
- `P1-high` (#D93F0B - Orange): High priority - next sprint
- `P2-medium` (#FBCA04 - Yellow): Medium priority - backlog
- `P3-low` (#0E8A16 - Green): Low priority - nice to have
- `P4-future` (#C5DEF5 - Light Blue): Future consideration

**Category Labels:**
- `bug` (#d73a4a): Something isn't working
- `enhancement` (#a2eeef): New feature or request
- `documentation` (#0075ca): Improvements or additions to documentation
- `architecture` (#0E8A16): Architecture and infrastructure changes
- `performance` (#FBCA04): Performance improvements
- `testing` (#D4C5F9): Testing and QA
- `security` (#B60205): Security improvements

**Status Labels:**
- `duplicate`: This issue or pull request already exists
- `invalid`: This doesn't seem right
- `wontfix`: This will not be worked on
- `help wanted`: Extra attention is needed
- `good first issue`: Good for newcomers
- `question`: Further information is requested

### Issue Template

```markdown
## Issue Title
Brief description of the issue

### Type
- [ ] Bug
- [ ] Feature Request
- [ ] Enhancement
- [ ] Documentation

### Priority
- [ ] P0 - Critical
- [ ] P1 - High
- [ ] P2 - Medium
- [ ] P3 - Low
- [ ] P4 - Future

### Labels
Select appropriate labels:
- Priority: P0-critical, P1-high, P2-medium, P3-low, P4-future
- Category: bug, enhancement, documentation, architecture, performance, testing, security
- Status: duplicate, invalid, wontfix, help wanted, good first issue, question

### Description
Detailed description of the issue or feature request

### Steps to Reproduce (for bugs)
1. Step one
2. Step two
3. Expected vs actual behavior

### Proposed Solution
How this should be fixed or implemented

### Related Issues
Links to related issues or PRs
```

### Creating Issues with Labels

```bash
# Create issue with labels
gh issue create \
  --title "Issue title" \
  --body "Issue description" \
  --label "P1-high,enhancement"

# Add labels to existing issue
gh issue edit 42 --add-label "P3-low,testing"

# Remove labels
gh issue edit 42 --remove-label "bug"

# List issues by label
gh issue list --label "P1-high"
gh issue list --label "testing"
```

### Label Management

```bash
# List all labels
gh label list

# Create new label
gh label create "label-name" \
  --description "Label description" \
  --color "HEXCOLOR"

# Edit existing label
gh label edit "label-name" \
  --description "New description" \
  --color "NEWHEX"

# Delete label
gh label delete "label-name"

---

## Git Workflow

### Core Principles

**IMPORTANT:** Git operations (commits and pushes) should ONLY be performed at user direction. Never commit or push automatically without explicit user approval.

### Standard Workflow

1. **Make Changes**
   - Edit files using appropriate tools (apply_diff, write_to_file, etc.)
   - Test changes to ensure they work
   - Wait for user confirmation after each significant change

2. **Stage Changes (Only When User Approves)**
   ```bash
   # Stage specific files
   git add path/to/file1.py path/to/file2.md
   
   # Stage all changes (use cautiously)
   git add -A
   ```

3. **Commit Changes (Only When User Approves)**
   ```bash
   # Commit with descriptive message
   git commit -m "type: brief description
   
   - Detailed change 1
   - Detailed change 2
   - Detailed change 3"
   ```

4. **Push Changes (Only When User Approves)**
   ```bash
   # Push to remote repository
   git push origin main
   ```

### Commit Message Format

Follow conventional commits format:

```
type: brief description (50 chars or less)

- Detailed bullet point 1
- Detailed bullet point 2
- Detailed bullet point 3
- Related issue references (#123)
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, configs)
- `ci`: CI/CD changes
- `build`: Build system changes

**Examples:**
```bash
# Feature commit
git commit -m "feat: Add segment-based route naming

- Implemented route segment identification algorithm
- Added configuration options to config.yaml
- Updated route analyzer to use new naming system
- Resolves #60"

# Documentation commit
git commit -m "docs: Update TECHNICAL_SPEC.md with v2.3.0 features

- Added Route Namer section with algorithm details
- Updated Configuration section with new parameters
- Added Security section documenting SHA256 migration"

# Bug fix commit
git commit -m "fix: Correct issue #58 numbering discrepancy

- Clarified terminal wrapping entry was never created
- Documented actual issue #58 definition
- Prevents future confusion in archived docs"

# Chore commit
git commit -m "chore: Organize scripts into /scripts folder

- Created /scripts directory for utility scripts
- Moved 14 scripts from root to /scripts
- Added scripts/README.md with documentation
- Root directory now clean (only main.py remains)"
```

### Logical Commit Grouping

**Group related changes into single commits:**

✅ **Good - Logical grouping:**
```bash
# All route naming changes together
git add src/route_namer.py config/config.yaml cache/geocoding_cache.json
git commit -m "feat: Implement segment-based route naming"

# All documentation updates together
git add README.md TECHNICAL_SPEC.md TIME_TRACKING.md
git commit -m "docs: Update documentation for v2.3.0 release"
```

❌ **Bad - Fragmented commits:**
```bash
# Don't split related changes
git add src/route_namer.py
git commit -m "Update route namer"
git add config/config.yaml
git commit -m "Update config"
git add cache/geocoding_cache.json
git commit -m "Clear cache"
```

### Multi-Step Workflow Example

**Scenario: Implementing a new feature**

1. **User requests feature implementation**
   - User: "Implement segment-based route naming"

2. **Make changes and wait for confirmation**
   - Edit src/route_namer.py
   - Wait for user: "Looks good, continue"

3. **Make related changes**
   - Update config/config.yaml
   - Clear cache files
   - Wait for user: "Perfect, commit these changes"

4. **Stage and commit (only after user approval)**
   ```bash
   git add src/route_namer.py config/config.yaml cache/geocoding_cache.json
   git commit -m "feat: Implement segment-based route naming
   
   - Added route segment identification algorithm
   - Updated configuration with new parameters
   - Cleared geocoding cache for fresh analysis"
   ```

5. **Update documentation**
   - Edit README.md, TECHNICAL_SPEC.md
   - Wait for user: "Documentation looks good, commit it"

6. **Commit documentation separately**
   ```bash
   git add README.md TECHNICAL_SPEC.md
   git commit -m "docs: Document segment-based route naming feature"
   ```

7. **Push only when user approves**
   - User: "Push these changes"
   ```bash
   git push origin main
   ```

### When to Commit

**Commit after:**
- Completing a logical unit of work
- All related files are updated
- Changes have been tested
- User has approved the changes

**Don't commit:**
- Partial implementations
- Broken code
- Without user approval
- Before testing changes

### When to Push

**Push after:**
- One or more commits are ready
- User explicitly approves
- All tests pass
- Documentation is updated

**Don't push:**
- Automatically after every commit
- Without user approval
- Broken or untested code
- Incomplete features

### Checking Status

```bash
# Check what's changed
git status

# See detailed changes
git diff

# See staged changes
git diff --cached

# View commit history
git log --oneline -10

# View recent commits with details
git log --since="1 day ago" --oneline --no-merges
```

### Undoing Changes (If Needed)

```bash
# Unstage files (keep changes)
git reset HEAD path/to/file

# Discard uncommitted changes
git checkout -- path/to/file

# Amend last commit (before push)
git commit --amend -m "New message"

# Undo last commit (keep changes)
git reset --soft HEAD~1
```

### Best Practices

1. **Always wait for user approval before git operations**
2. **Group related changes into logical commits**
3. **Write clear, descriptive commit messages**
4. **Test changes before committing**
5. **Update documentation in same commit or immediately after**
6. **Push only when user explicitly requests it**
7. **Use conventional commit format for consistency**
8. **Reference issue numbers in commit messages**

```

### TODO Comments in Code

```python
# TODO: Implement wind-aware route selection using WindImpactCalculator
# Priority: P2, Assigned: Bob, Due: 2026-04-01
def select_optimal_route(routes: List[Route]) -> Route:
    # For now, return most frequent route
    return max(routes, key=lambda r: r.frequency)

# FIXME: This breaks with activities that have no GPS data
# Priority: P1, Assigned: Alice, Issue: #42
def extract_coordinates(activity: Activity) -> List[Tuple]:
    return decode_polyline(activity.polyline)  # Can be None!

# NOTE: This is a temporary workaround for rate limiting
# Will be replaced with proper exponential backoff in #54
time.sleep(1)
```

### ISSUE_PRIORITIES.md Format

The `ISSUE_PRIORITIES.md` file should follow this standardized format across all projects:

```markdown
# Issue Prioritization

**Last Updated:** YYYY-MM-DD

This file reflects the current state of GitHub issues by priority. Issues are managed via GitHub labels (P0-critical, P1-high, P2-medium, P3-low, P4-future).

## 🔴 P0 - CRITICAL (Drop Everything)
Issues that make the application unusable or cause data loss.

**No P0 issues currently open** ✅
(or list issues with #number - title)

## 🔴 P1 - HIGH (Current Sprint)
Issues that significantly impact core functionality or user experience.

- #number - Issue title
- #number - Issue title

## 🟡 P2 - MEDIUM (Next Sprint)
Important improvements that enhance functionality but don't block core workflows.

- #number - Issue title

## 🟢 P3 - LOW (Backlog)
Nice-to-have improvements and minor UX enhancements.

- #number - Issue title

## 📋 P4 - FUTURE ENHANCEMENTS
Feature requests and enhancements for future releases.

- #number - Issue title

## ⚠️ Unprioritized Issues
Issues without priority labels that need to be triaged.

- #number - Issue title

## Priority Guidelines

### P0 - CRITICAL
- Application is down or unusable
- Data loss or corruption
- Security vulnerabilities
- **Action:** Drop everything and fix immediately

### P1 - HIGH
- Core features broken or severely degraded
- Significant user pain points
- Blocks important workflows
- **Action:** Fix in current sprint (1-2 weeks)

### P2 - MEDIUM
- Feature improvements
- Moderate user pain points
- Quality of life enhancements
- **Action:** Plan for next sprint (2-4 weeks)

### P3 - LOW
- Minor UX improvements
- Edge cases
- Nice-to-have features
- **Action:** Backlog, address when time permits

### P4 - FUTURE
- New features
- Major enhancements
- Long-term improvements
- **Action:** Plan for future releases

## How to Update Priorities

1. Use GitHub labels to set priority (P0-critical, P1-high, P2-medium, P3-low, P4-future)
2. Update this file manually or via script
3. Commit changes with descriptive message
4. Communicate priority changes to team

## Summary Statistics

- **Total Open Issues:** X
- **P0 (Critical):** X
- **P1 (High):** X
- **P2 (Medium):** X
- **P3 (Low):** X
- **P4 (Future):** X
- **Unprioritized:** X

## Recommended Next Actions

1. Action item 1
2. Action item 2
3. Action item 3
```

**Key Elements:**
- Emoji indicators for each priority level (🔴 🟡 🟢 📋 ⚠️)
- Clear section headers with priority names and timeframes
- Issues listed as `- #number - title` format
- Priority guidelines section explaining each level
- Summary statistics showing issue counts
- Recommended next actions section
- Last updated date at top

**Updating Process:**
```bash
# List all open issues with priorities
gh issue list --state open --limit 100

# Update ISSUE_PRIORITIES.md manually based on current state
# Ensure format matches the template above

# Commit changes
git add ISSUE_PRIORITIES.md
git commit -m "Update issue priorities - [date]"
```

---

## Maintenance Procedures

### Weekly Tasks (Every Monday)

**1. Documentation Sync (30-45 minutes)**
```bash
# Review changes from past week
git log --since="7 days ago" --oneline --no-merges

# Update documentation
- [ ] Review PLAN.md vs implementation
- [ ] Update TECHNICAL_SPEC.md with changes
- [ ] Verify IMPLEMENTATION_GUIDE.md accuracy
- [ ] Update TIME_TRACKING.md
- [ ] Check all code examples still work
```

**2. Issue Triage**
```bash
# Review open issues
- [ ] Assign priorities to new issues
- [ ] Update status of in-progress issues
- [ ] Close completed issues
- [ ] Update ISSUE_PRIORITIES.md
```

**3. Dependency Updates**
```bash
# Check for outdated dependencies
pip list --outdated

# Update if needed
pip install --upgrade package_name

# Test after updates
python3 main.py --analyze
```

### Monthly Tasks

**1. Comprehensive Documentation Audit**
- Review all markdown files
- Check for broken links
- Update screenshots if UI changed
- Verify all examples work

**2. Security Review**
- Check for exposed credentials
- Review security audit logs
- Update dependencies for security patches
- Verify file permissions

**3. Performance Review**
- Profile slow operations
- Optimize caching strategies
- Review API usage patterns
- Check memory usage

### Quarterly Tasks

**1. Major Version Planning**
- Review feature requests
- Plan next major release
- Update roadmap
- Deprecate old features

**2. Code Quality Review**
- Run linting tools
- Check test coverage
- Review error handling patterns
- Update type hints

---

## Quick Reference

### Common Commands

```bash
# Authentication
python3 main.py --auth

# Fetch activities
python3 main.py --fetch --limit 100
python3 main.py --fetch --from-date 2024-01-01

# Analysis
python3 main.py --analyze
python3 main.py --analyze --parallel 4

# Combined
python3 main.py --fetch --analyze

# Statistics
python3 main.py --stats
```

### File Locations

```
commute/
├── src/                    # Source code
│   ├── auth.py            # Authentication
│   ├── data_fetcher.py    # Activity fetching
│   ├── location_finder.py # Location clustering
│   ├── route_analyzer.py  # Route analysis
│   ├── optimizer.py       # Route optimization
│   ├── weather_fetcher.py # Weather integration
│   └── report_generator.py # HTML reports
├── config/
│   ├── config.yaml        # User configuration
│   └── credentials.json   # OAuth tokens (gitignored)
├── cache/
│   ├── geocoding_cache.json
│   ├── weather_cache.json
│   └── route_similarity_cache.json
├── output/reports/        # Generated reports
└── logs/                  # Application logs
```

### Configuration Keys

```yaml
optimization:
  weather_enabled: true
  weights:
    time: 0.35
    distance: 0.25
    safety: 0.25
    weather: 0.15

location_detection:
  clustering:
    eps: 0.002  # ~200 meters
    min_samples: 5

route_filtering:
  min_distance_km: 2
  max_distance_km: 30
```

---

## Appendix: Algorithm Details

### Route Similarity (Fréchet Distance)

**Why Fréchet over Hausdorff:**
- Considers point order (like walking a dog on a leash)
- Better for routes that follow the same path
- More robust to GPS sampling differences
- Validated on 9,251 route pairs with 100% agreement

**Implementation:**
```python
from similaritymeasures import frechet_dist

def calculate_similarity(route1, route2):
    coords1 = np.array(route1.coordinates)
    coords2 = np.array(route2.coordinates)
    
    # Primary: Fréchet distance
    frechet = frechet_dist(coords1, coords2)
    frechet_sim = 1 / (1 + frechet / 300)  # 300m threshold
    
    # Secondary: Hausdorff validation
    hausdorff_sim = calculate_hausdorff_similarity(coords1, coords2)
    
    # Penalize if spatially far apart
    if hausdorff_sim < 0.50:
        return frechet_sim * 0.7
    return frechet_sim
```

### Wind Impact Calculation

```python
def calculate_wind_impact(route_coords, wind_speed, wind_direction):
    """Calculate wind impact on route performance."""
    total_headwind = 0
    total_crosswind = 0
    
    for i in range(len(route_coords) - 1):
        # Calculate segment bearing
        bearing = calculate_bearing(route_coords[i], route_coords[i+1])
        
        # Calculate relative wind angle
        relative_angle = (wind_direction - bearing) % 360
        
        # Decompose into headwind and crosswind
        headwind = wind_speed * cos(radians(relative_angle))
        crosswind = wind_speed * abs(sin(radians(relative_angle)))
        
        total_headwind += headwind
        total_crosswind += crosswind
    
    # Calculate time impact
    # Headwind: ~1.5% slower per 1 km/h
    # Crosswind: ~0.5% slower per 1 km/h
    avg_headwind = total_headwind / len(route_coords)
    avg_crosswind = total_crosswind / len(route_coords)
    
    time_penalty = (avg_headwind * 0.015) + (avg_crosswind * 0.005)
    return time_penalty
```

---

**End of Bob Skills Document**

*This document is a living guide. Update it as the project evolves and new best practices emerge.*