# E2E Testing Guide

End-to-end tests for the Ride Optimizer web application using Playwright.

## Test Coverage

**37 tests across 4 test files:**
- `test_navigation.py` - 7 tests (page loads, navigation, mobile menu)
- `test_dashboard.py` - 8 tests (weather, stats, responsive, accessibility)
- `test_commute.py` - 10 tests (direction, map, routes, responsive)
- `test_routes.py` - 12 tests (search, filters, map, responsive)

## Running Tests

### Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Run All E2E Tests
```bash
pytest tests/e2e/ -v
```

### Run Specific Test File
```bash
pytest tests/e2e/test_navigation.py -v
```

### Run with UI (Headed Mode)
```bash
pytest tests/e2e/ --headed
```

### Run on Specific Browser
```bash
pytest tests/e2e/ --browser firefox
pytest tests/e2e/ --browser webkit
```

### Generate HTML Report
```bash
pytest tests/e2e/ --html=report.html --self-contained-html
```

## Test Structure

```
tests/e2e/
├── conftest.py              # Fixtures (page, mobile_page, mock_api)
├── test_navigation.py       # Navigation and page load tests
├── test_dashboard.py        # Dashboard feature tests
├── test_commute.py          # Commute feature tests
├── test_routes.py           # Routes library tests
├── utils/
│   └── page_objects.py      # Page object models
└── fixtures/
    └── (future test data)
```

## Writing New Tests

### Basic Test Template
```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
class TestFeature:
    def test_something(self, page: Page, base_url: str):
        """Test description."""
        page.goto(f"{base_url}/page.html")
        expect(page.locator("h1")).to_be_visible()
```

### Using Page Objects
```python
from tests.e2e.utils.page_objects import DashboardPage

def test_with_page_object(self, page: Page, base_url: str):
    dashboard = DashboardPage(page, base_url)
    dashboard.navigate()
    expect(dashboard.get_weather_card()).to_be_visible()
```

### Using Mock API
```python
def test_with_mock_api(self, page: Page, base_url: str, mock_api):
    page.goto(base_url)
    # API calls will return mock data
```

## Debugging Failed Tests

### Run with Headed Mode
```bash
pytest tests/e2e/test_name.py --headed --slowmo 1000
```

### Add Breakpoint
```python
page.pause()  # Opens Playwright Inspector
```

### Check Screenshots
Failed tests automatically capture screenshots in `test-results/`

### View Trace
```bash
pytest tests/e2e/ --tracing on
playwright show-trace trace.zip
```

## Best Practices

1. **Use `.first` for multiple elements**: `page.locator("nav").first`
2. **Wait for network idle**: `page.wait_for_load_state("networkidle")`
3. **Use semantic selectors**: Prefer `get_by_role()`, `get_by_label()` over CSS
4. **Test user flows, not implementation**: Focus on what users see/do
5. **Keep tests independent**: Each test should work in isolation
6. **Use page objects**: Reduce duplication, improve maintainability

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Scheduled nightly builds

See `.github/workflows/e2e-tests.yml` for configuration.

## Troubleshooting

### Browser Not Found
```bash
playwright install chromium
```

### Port 8083 In Use
```bash
# Stop existing server
python stop.py
# Or change port in conftest.py
```

### Flaky Tests
- Add explicit waits: `page.wait_for_timeout(1000)`
- Use `wait_for_selector()` instead of `wait_for_timeout()`
- Check for race conditions in JavaScript

## Test Markers

- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.accessibility` - Accessibility tests
- `@pytest.mark.mobile` - Mobile responsive tests
- `@pytest.mark.performance` - Performance tests

Run specific markers:
```bash
pytest -m e2e
pytest -m "e2e and not slow"