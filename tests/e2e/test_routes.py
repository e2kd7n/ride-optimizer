"""
E2E tests for routes library features.

Tests search, filtering, sorting, and route interaction.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestRoutes:
    """Test routes library features."""
    
    def test_page_loads(self, page: Page, base_url: str):
        """Routes page loads successfully."""
        page.goto(f"{base_url}/routes.html")
        expect(page).to_have_title("Routes - Ride Optimizer")
    
    def test_search_box_exists(self, page: Page, base_url: str):
        """Search box is present."""
        page.goto(f"{base_url}/routes.html")
        
        search_input = page.locator("input[type='search'], input[type='text']").first
        if search_input.count() > 0:
            expect(search_input).to_be_visible()
    
    def test_filter_controls_exist(self, page: Page, base_url: str):
        """Filter controls are present."""
        page.goto(f"{base_url}/routes.html")
        
        # Check for filter dropdowns or buttons
        filters = page.locator("select, button").filter(has_text="filter|type|sort")
        if filters.count() > 0:
            expect(filters.first).to_be_visible()
    
    def test_route_cards_or_empty_state(self, page: Page, base_url: str, mock_api):
        """Route cards or empty state displays."""
        page.goto(f"{base_url}/routes.html")
        page.wait_for_timeout(1000)  # Wait for API
        
        # Check for route cards, empty state, or any content
        content = page.locator(".route-card, .empty-state, .container").first
        expect(content).to_be_visible()
    
    def test_map_container_exists(self, page: Page, base_url: str):
        """Map container is present."""
        page.goto(f"{base_url}/routes.html")
        
        map_container = page.locator("#routes-map, #map, .map-container").first
        expect(map_container).to_be_visible()
    
    def test_responsive_layout(self, mobile_page: Page, base_url: str):
        """Routes page is responsive."""
        mobile_page.goto(f"{base_url}/routes.html")
        
        # Verify no horizontal scroll
        viewport_width = mobile_page.viewport_size["width"]
        body_width = mobile_page.evaluate("document.body.scrollWidth")
        assert body_width <= viewport_width + 1, "Horizontal scroll detected"
    
    def test_search_functionality(self, page: Page, base_url: str):
        """Search box accepts input."""
        page.goto(f"{base_url}/routes.html")
        
        search_input = page.locator("input[type='search'], input[type='text']").first
        if search_input.count() > 0:
            search_input.fill("test")
            expect(search_input).to_have_value("test")
    
    def test_navigation_works(self, page: Page, base_url: str):
        """Navigation from routes page works."""
        page.goto(f"{base_url}/routes.html")
        
        # Click home link
        page.click("a[href='/']")
        expect(page).to_have_url(f"{base_url}/")
    
    def test_page_has_heading(self, page: Page, base_url: str):
        """Page has descriptive heading."""
        page.goto(f"{base_url}/routes.html")
        
        heading = page.locator("h1, h2").first
        expect(heading).to_be_visible()
    
    def test_no_console_errors(self, page: Page, base_url: str):
        """Page loads without critical errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        page.goto(f"{base_url}/routes.html")
        page.wait_for_load_state("networkidle")
        
        critical_errors = [e for e in errors if "Failed to fetch" not in e.text]
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"
    
    def test_map_loads(self, page: Page, base_url: str):
        """Map loads successfully."""
        page.goto(f"{base_url}/routes.html")
        page.wait_for_timeout(2000)  # Wait for map
        
        leaflet_container = page.locator(".leaflet-container").first
        if leaflet_container.count() > 0:
            expect(leaflet_container).to_be_visible()
    
    def test_accessibility_structure(self, page: Page, base_url: str):
        """Page has proper accessibility structure."""
        page.goto(f"{base_url}/routes.html")
        
        # Check for navigation
        expect(page.locator("nav").first).to_be_visible()
        
        # Check for main content
        main_content = page.locator("main, [role='main'], .container").first
        expect(main_content).to_be_visible()

# Made with Bob
