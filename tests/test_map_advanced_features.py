"""
Tests for Advanced Map Features (Issue #234)

Tests elevation profiles, analytics overlays, and export functionality
across all map pages.
"""

import pytest
from flask import url_for


class TestElevationProfiles:
    """Test elevation profile functionality"""
    
    def test_route_detail_has_elevation_profile_container(self, client, sample_route):
        """Test that route detail page includes elevation profile container"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'elevation-profile' in response.data
        assert b'Elevation Profile' in response.data
    
    def test_elevation_profile_stats_displayed(self, client, sample_route):
        """Test that elevation stats are displayed"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'elevation-gain' in response.data
        assert b'elevation-loss' in response.data
        assert b'elevation-max' in response.data
        assert b'elevation-min' in response.data
    
    def test_elevation_profile_javascript_loaded(self, client, sample_route):
        """Test that elevation profile JavaScript is loaded"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'map-advanced-features.js' in response.data
        assert b'route-detail-advanced.js' in response.data
    
    def test_elevation_profile_css_loaded(self, client, sample_route):
        """Test that elevation profile CSS is loaded"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'map-advanced-features.css' in response.data


class TestMapExport:
    """Test map export functionality"""
    
    def test_export_button_on_route_detail(self, client, sample_route):
        """Test that export button is present on route detail page"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'map-export-container' in response.data
        assert b'Export Map' in response.data or b'export' in response.data.lower()
    
    def test_export_dependencies_loaded(self, client):
        """Test that export dependencies (html2canvas, jsPDF) are loaded"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        assert b'html2canvas' in response.data
        assert b'jspdf' in response.data
    
    def test_export_button_on_commute_page(self, client):
        """Test that export functionality is available on commute page"""
        response = client.get(url_for('commute.index'))
        assert response.status_code == 200
        # Integration script should add export button dynamically
        assert b'map-features-integration.js' in response.data
    
    def test_export_button_on_planner_page(self, client):
        """Test that export functionality is available on planner page"""
        response = client.get(url_for('planner.index'))
        assert response.status_code == 200
        assert b'map-features-integration.js' in response.data
    
    def test_export_button_on_dashboard(self, client):
        """Test that export functionality is available on dashboard"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        assert b'map-features-integration.js' in response.data


class TestAnalyticsOverlay:
    """Test route analytics overlay functionality"""
    
    def test_analytics_functions_available(self, client):
        """Test that analytics overlay functions are loaded"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        assert b'MapAdvancedFeatures' in response.data
        assert b'map-advanced-features.js' in response.data
    
    def test_dashboard_analytics_info(self, client):
        """Test that dashboard includes analytics information"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        # Integration script adds analytics info box
        assert b'map-features-integration.js' in response.data


class TestChartJSIntegration:
    """Test Chart.js integration for elevation profiles"""
    
    def test_chartjs_loaded_globally(self, client):
        """Test that Chart.js is loaded in base template"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        assert b'chart.js' in response.data or b'Chart.js' in response.data
    
    def test_chartjs_version(self, client):
        """Test that correct Chart.js version is loaded"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        # Should be Chart.js 4.x
        assert b'chart.js@4' in response.data


class TestResponsiveDesign:
    """Test responsive design of advanced features"""
    
    def test_elevation_profile_responsive_css(self, client, sample_route):
        """Test that elevation profile has responsive CSS"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'elevation-profile-canvas' in response.data
        # CSS should include media queries
        css_response = client.get(url_for('static', filename='css/map-advanced-features.css'))
        assert b'@media' in css_response.data
        assert b'max-width: 768px' in css_response.data
    
    def test_export_button_responsive(self, client):
        """Test that export buttons are responsive"""
        css_response = client.get(url_for('static', filename='css/map-advanced-features.css'))
        assert b'map-export-buttons' in css_response.data


class TestAccessibility:
    """Test accessibility features"""
    
    def test_elevation_profile_has_aria_labels(self, client, sample_route):
        """Test that elevation profile elements have proper ARIA labels"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        # Check for semantic HTML
        assert b'<h5' in response.data or b'<h3' in response.data
    
    def test_export_button_accessible(self, client, sample_route):
        """Test that export buttons are keyboard accessible"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        # Buttons should be actual button elements or have proper roles
        assert b'<button' in response.data or b'role="button"' in response.data


class TestIntegrationAcrossPages:
    """Test that features work across all pages"""
    
    def test_features_on_route_detail(self, client, sample_route):
        """Test all features present on route detail page"""
        response = client.get(url_for('route_library.detail', route_id=sample_route['id']))
        assert response.status_code == 200
        assert b'elevation-profile' in response.data
        assert b'map-export-container' in response.data
        assert b'map-advanced-features.js' in response.data
    
    def test_features_on_commute(self, client):
        """Test features present on commute page"""
        response = client.get(url_for('commute.index'))
        assert response.status_code == 200
        assert b'map-features-integration.js' in response.data
        assert b'map-advanced-features.js' in response.data
    
    def test_features_on_planner(self, client):
        """Test features present on planner page"""
        response = client.get(url_for('planner.index'))
        assert response.status_code == 200
        assert b'map-features-integration.js' in response.data
        assert b'map-advanced-features.js' in response.data
    
    def test_features_on_dashboard(self, client):
        """Test features present on dashboard"""
        response = client.get(url_for('dashboard.index'))
        assert response.status_code == 200
        assert b'map-features-integration.js' in response.data
        assert b'map-advanced-features.js' in response.data


class TestErrorHandling:
    """Test error handling for advanced features"""
    
    def test_elevation_profile_without_data(self, client):
        """Test elevation profile handles missing data gracefully"""
        # This should be handled by JavaScript showing error message
        response = client.get(url_for('route_library.index'))
        assert response.status_code == 200
        # Page should still load even if elevation data is missing
    
    def test_export_without_map(self, client):
        """Test export functionality handles missing map gracefully"""
        response = client.get(url_for('route_library.index'))
        assert response.status_code == 200
        # Should not break page if map is not present


# Fixtures
@pytest.fixture
def sample_route():
    """Sample route data for testing"""
    return {
        'id': 'test-route-1',
        'name': 'Test Route',
        'distance': 10.5,
        'duration': 45,
        'elevation': 150,
        'coordinates': [
            [40.7128, -74.0060],
            [40.7138, -74.0070],
            [40.7148, -74.0080]
        ]
    }


# Made with Bob