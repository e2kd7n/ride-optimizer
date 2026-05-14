"""
Pytest configuration for E2E tests using Playwright.

Provides fixtures for browser contexts, pages, and mock API responses.
"""

import pytest
from playwright.sync_api import Page, BrowserContext
from typing import Generator


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
        "timezone_id": "America/Chicago",
    }


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Create a new page for each test."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def mobile_page(context: BrowserContext) -> Generator[Page, None, None]:
    """Create mobile viewport page (iPhone SE)."""
    page = context.new_page()
    page.set_viewport_size({"width": 375, "height": 667})
    yield page
    page.close()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "http://localhost:8083"


@pytest.fixture
def mock_weather_data():
    """Mock weather API response."""
    return {
        "temperature": 72,
        "conditions": "sunny",
        "wind_speed": 5,
        "wind_direction": "NW"
    }


@pytest.fixture
def mock_routes_data():
    """Mock routes API response."""
    return {
        "routes": [
            {
                "id": "route_1",
                "name": "Lakefront Trail → North Lake Shore Drive",
                "distance": 16.3,
                "duration": 35.0,
                "type": "commute",
                "uses": 4,
                "difficulty": "Easy"
            }
        ]
    }


@pytest.fixture
def mock_api(page: Page, mock_weather_data, mock_routes_data):
    """Mock API responses for testing."""
    def handle_route(route, request):
        url = request.url
        if "/api/weather" in url:
            route.fulfill(json=mock_weather_data)
        elif "/api/routes" in url:
            route.fulfill(json=mock_routes_data)
        elif "/api/recommendation" in url:
            route.fulfill(json={"recommendations": []})
        elif "/api/status" in url:
            route.fulfill(json={"status": "ok", "cache_age": 0})
        else:
            route.continue_()
    
    page.route("**/api/**", handle_route)
    return page

# Made with Bob
