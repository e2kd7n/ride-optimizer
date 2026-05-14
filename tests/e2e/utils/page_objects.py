"""
Page Object Models for E2E tests.

Provides reusable page objects for interacting with application pages.
"""

from playwright.sync_api import Page, expect


class BasePage:
    """Base page object with common functionality."""
    
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
    
    def navigate(self):
        """Navigate to the page."""
        self.page.goto(f"{self.base_url}{self.url}")
        self.page.wait_for_load_state("networkidle")
    
    def get_nav_link(self, href: str):
        """Get navigation link by href."""
        return self.page.locator(f"a[href='{href}']")


class DashboardPage(BasePage):
    """Dashboard page object."""
    
    url = "/"
    
    def get_weather_card(self):
        return self.page.locator("#weather-card")
    
    def get_stats_card(self):
        return self.page.locator("#stats-card")
    
    def click_commute_link(self):
        self.get_nav_link("/commute.html").click()
        self.page.wait_for_url("**/commute.html")


class CommutePage(BasePage):
    """Commute page object."""
    
    url = "/commute.html"
    
    def select_direction(self, direction: str):
        """Select commute direction (to_work or to_home)."""
        self.page.select_option("#direction-select", direction)
        self.page.wait_for_timeout(500)
    
    def get_recommendations(self):
        """Get all recommendation cards."""
        return self.page.locator(".commute-card")
    
    def click_route_card(self, index: int = 0):
        """Click a route card by index."""
        self.get_recommendations().nth(index).click()
    
    def get_active_card(self):
        """Get the currently active route card."""
        return self.page.locator(".commute-card.active")


class RoutesPage(BasePage):
    """Routes library page object."""
    
    url = "/routes.html"
    
    def search(self, query: str):
        """Search for routes."""
        self.page.fill("#route-search", query)
        self.page.wait_for_timeout(500)
    
    def filter_by_type(self, route_type: str):
        """Filter routes by type."""
        self.page.select_option("#type-filter", route_type)
        self.page.wait_for_timeout(500)
    
    def sort_by(self, sort_option: str):
        """Sort routes."""
        self.page.select_option("#sort-select", sort_option)
        self.page.wait_for_timeout(500)
    
    def get_route_cards(self):
        """Get all visible route cards."""
        return self.page.locator(".route-card:visible")
    
    def toggle_favorite(self, index: int = 0):
        """Toggle favorite status of a route."""
        self.get_route_cards().nth(index).locator(".favorite-btn").click()

# Made with Bob
