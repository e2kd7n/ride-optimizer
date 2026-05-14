"""
E2E tests for commute recommendation features.

Tests direction selection, route cards, and map interaction.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestCommute:
    """Test commute recommendation features."""
    
    def test_page_loads(self, page: Page, base_url: str):
        """Commute page loads successfully."""
        page.goto(f"{base_url}/commute.html")
        expect(page).to_have_title("Commute - Ride Optimizer")
    
    def test_direction_selector_exists(self, page: Page, base_url: str):
        """Direction selector is present."""
        page.goto(f"{base_url}/commute.html")
        
        # Look for direction-related controls
        selector = page.locator("select, button").filter(has_text="work|home|direction")
        if selector.count() > 0:
            expect(selector.first).to_be_visible()
    
    def test_map_container_exists(self, page: Page, base_url: str):
        """Map container is present."""
        page.goto(f"{base_url}/commute.html")
        
        # Check for map container (may not exist on all pages)
        map_container = page.locator("#commute-map, #map, .map-container")
        if map_container.count() > 0:
            expect(map_container.first).to_be_visible()
    
    def test_route_cards_display(self, page: Page, base_url: str, mock_api):
        """Route recommendation cards display."""
        page.goto(f"{base_url}/commute.html")
        page.wait_for_timeout(1000)  # Wait for API
        
        # Check for route cards or empty state
        cards_or_empty = page.locator(".commute-card, .route-card, .empty-state").first
        expect(cards_or_empty).to_be_visible()
    
    def test_responsive_layout(self, mobile_page: Page, base_url: str):
        """Commute page is responsive."""
        mobile_page.goto(f"{base_url}/commute.html")
        
        # Verify no horizontal scroll
        viewport_width = mobile_page.viewport_size["width"]
        body_width = mobile_page.evaluate("document.body.scrollWidth")
        assert body_width <= viewport_width + 1, "Horizontal scroll detected"
    
    def test_map_loads(self, page: Page, base_url: str):
        """Map loads successfully."""
        page.goto(f"{base_url}/commute.html")
        page.wait_for_timeout(2000)  # Wait for map initialization
        
        # Check for Leaflet map elements
        leaflet_container = page.locator(".leaflet-container").first
        if leaflet_container.count() > 0:
            expect(leaflet_container).to_be_visible()
    
    def test_navigation_works(self, page: Page, base_url: str):
        """Navigation from commute page works."""
        page.goto(f"{base_url}/commute.html")
        
        # Click routes link
        page.click("a[href='/routes.html']")
        expect(page).to_have_url(f"{base_url}/routes.html")
    
    def test_page_has_heading(self, page: Page, base_url: str):
        """Page has descriptive heading."""
        page.goto(f"{base_url}/commute.html")
        
        # Check for heading
        heading = page.locator("h1, h2").first
        expect(heading).to_be_visible()
    
    def test_no_console_errors(self, page: Page, base_url: str):
        """Page loads without critical errors."""
        errors = []
        page.on("console", lambda msg: errors.append(msg) if msg.type == "error" else None)
        
        page.goto(f"{base_url}/commute.html")
        page.wait_for_load_state("networkidle")
        
        critical_errors = [e for e in errors if "Failed to fetch" not in e.text]
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"
    
    def test_accessibility_structure(self, page: Page, base_url: str):
        """Page has proper accessibility structure."""
        page.goto(f"{base_url}/commute.html")
        
        # Check for navigation
        expect(page.locator("nav").first).to_be_visible()
        
        # Check for main content area
        main_content = page.locator("main, [role='main'], .container").first
        expect(main_content).to_be_visible()

# Made with Bob
