"""
E2E tests for dashboard features.

Tests weather display, stats, and quick actions.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestDashboard:
    """Test dashboard features."""
    
    def test_page_structure(self, page: Page, base_url: str):
        """Dashboard has correct structure."""
        page.goto(base_url)
        
        # Verify main sections exist
        expect(page.locator("#main-content")).to_be_visible()
        expect(page.locator(".container").first).to_be_visible()
    
    def test_weather_section_exists(self, page: Page, base_url: str, mock_api):
        """Weather section displays."""
        page.goto(base_url)
        page.wait_for_timeout(1000)  # Wait for API
        
        # Check for weather-related content
        weather_section = page.locator("text=/weather|temperature|conditions/i").first
        expect(weather_section).to_be_visible()
    
    def test_stats_section_exists(self, page: Page, base_url: str):
        """Stats section displays."""
        page.goto(base_url)
        
        # Check for stats-related content
        stats_section = page.locator("text=/rides|distance|time/i").first
        expect(stats_section).to_be_visible()
    
    def test_navigation_links_work(self, page: Page, base_url: str):
        """Quick action links navigate correctly."""
        page.goto(base_url)
        
        # Find and click commute link
        commute_link = page.locator("a[href='/commute.html']").first
        if commute_link.is_visible():
            commute_link.click()
            expect(page).to_have_url(f"{base_url}/commute.html")
    
    def test_responsive_layout(self, mobile_page: Page, base_url: str):
        """Dashboard is responsive on mobile."""
        mobile_page.goto(base_url)
        
        # Verify content is visible on mobile
        expect(mobile_page.locator(".container").first).to_be_visible()
        
        # Verify no horizontal scroll
        viewport_width = mobile_page.viewport_size["width"]
        body_width = mobile_page.evaluate("document.body.scrollWidth")
        assert body_width <= viewport_width + 1, "Horizontal scroll detected"
    
    def test_page_loads_quickly(self, page: Page, base_url: str):
        """Dashboard loads in reasonable time."""
        import time
        start = time.time()
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start
        
        assert load_time < 5.0, f"Page load time {load_time}s exceeds 5s"
    
    def test_no_javascript_errors(self, page: Page, base_url: str):
        """Dashboard has no critical JavaScript errors."""
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        
        # Filter out expected errors
        critical_errors = [e for e in errors if "Failed to fetch" not in e]
        assert len(critical_errors) == 0, f"JavaScript errors: {critical_errors}"
    
    def test_accessibility_landmarks(self, page: Page, base_url: str):
        """Dashboard has proper ARIA landmarks."""
        page.goto(base_url)
        
        # Check for navigation landmark
        expect(page.locator("nav[role='navigation'], nav").first).to_be_visible()
        
        # Check for main landmark
        expect(page.locator("main, [role='main'], #main-content")).to_be_visible()

# Made with Bob
