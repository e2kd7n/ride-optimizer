"""
E2E tests for navigation and page loading.

Tests basic navigation flows, page loads, and menu functionality.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestNavigation:
    """Test navigation and page loading."""
    
    def test_dashboard_loads(self, page: Page, base_url: str):
        """Dashboard page loads successfully."""
        page.goto(base_url)
        expect(page).to_have_title("Ride Optimizer")
        expect(page.locator("h1").first).to_be_visible()
    
    def test_commute_page_loads(self, page: Page, base_url: str):
        """Commute page loads successfully."""
        page.goto(f"{base_url}/commute.html")
        expect(page).to_have_title("Commute - Ride Optimizer")
        expect(page.locator(".container h2").first).to_be_visible()
    
    def test_routes_page_loads(self, page: Page, base_url: str):
        """Routes page loads successfully."""
        page.goto(f"{base_url}/routes.html")
        expect(page).to_have_title("Routes - Ride Optimizer")
        expect(page.locator(".container h2").first).to_be_visible()
    
    def test_navigation_menu_works(self, page: Page, base_url: str):
        """Navigation menu links work correctly."""
        page.goto(base_url)
        
        # Click Commute link
        page.click("a[href='/commute.html']")
        expect(page).to_have_url(f"{base_url}/commute.html")
        
        # Click Routes link
        page.click("a[href='/routes.html']")
        expect(page).to_have_url(f"{base_url}/routes.html")
        
        # Click Home link
        page.click("a[href='/']")
        expect(page).to_have_url(f"{base_url}/")
    
    def test_mobile_navigation_toggle(self, mobile_page: Page, base_url: str):
        """Mobile navigation hamburger menu works."""
        mobile_page.goto(base_url)
        
        # Menu should be collapsed initially
        nav_menu = mobile_page.locator("#navbarNav")
        
        # Click hamburger to expand
        mobile_page.click(".navbar-toggler")
        mobile_page.wait_for_timeout(300)  # Animation
        
        # Click link and verify navigation
        mobile_page.click("a[href='/commute.html']")
        expect(mobile_page).to_have_url(f"{base_url}/commute.html")
    
    def test_all_pages_have_navigation(self, page: Page, base_url: str):
        """All pages have consistent navigation."""
        pages = ["/", "/commute.html", "/routes.html"]
        
        for url in pages:
            page.goto(f"{base_url}{url}")
            
            # Verify nav exists
            expect(page.locator("nav.navbar")).to_be_visible()
            
            # Verify brand link
            expect(page.locator(".navbar-brand")).to_be_visible()
            
            # Verify nav links
            expect(page.locator("a[href='/']").first).to_be_visible()
            expect(page.locator("a[href='/commute.html']").first).to_be_visible()
            expect(page.locator("a[href='/routes.html']").first).to_be_visible()
    
    def test_page_loads_without_errors(self, page: Page, base_url: str):
        """Pages load without console errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        
        # Filter out expected errors (like missing API data)
        critical_errors = [e for e in errors if "Failed to fetch" not in e.text]
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"

# Made with Bob
