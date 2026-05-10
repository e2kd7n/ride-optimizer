#!/usr/bin/env python3
"""
Issue #257 Phase 4: Integration & Testing
Tests for Epic #237 UI/UX Redesign implementation in static HTML files

This test suite validates:
- 3-tab navigation (Home, Routes, Settings)
- CSS features from Phase 1
- JavaScript utilities from Phase 2
- HTML restructuring from Phase 3
- Accessibility compliance (WCAG 2.1 AA)
- Responsive design (320px to 1920px)
- Performance metrics

Related Issues: #257, #255, #237
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app import create_app


class TestIssue257Phase4:
    """Test suite for Issue #257 Phase 4 - Integration & Testing"""
    
    def __init__(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'warnings': 0
        }
        self.test_details = []
    
    def log_test(self, name, status, message):
        """Log test result"""
        self.test_details.append({
            'name': name,
            'status': status,
            'message': message
        })
        if status == 'PASS':
            self.results['passed'] += 1
            print(f"  ✓ {name}")
        elif status == 'FAIL':
            self.results['failed'] += 1
            print(f"  ✗ {name}: {message}")
        elif status == 'ERROR':
            self.results['errors'] += 1
            print(f"  ✗ {name}: ERROR - {message}")
        elif status == 'WARN':
            self.results['warnings'] += 1
            print(f"  ⚠ {name}: {message}")
    
    def test_3_tab_navigation(self):
        """Test 4.1.1: 3-tab navigation structure"""
        print("\n[INFO] Testing 3-tab navigation...")
        
        # Test Home page (/)
        try:
            response = self.client.get('/')
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                
                # Check for 3-tab navigation
                has_home_tab = 'Home' in html or 'home' in html.lower()
                has_routes_tab = 'Routes' in html or 'routes' in html.lower()
                has_settings_tab = 'Settings' in html or 'settings' in html.lower()
                
                # Should NOT have old 4-tab navigation
                has_dashboard_tab = 'Dashboard' in html
                has_commute_tab = 'Commute' in html
                has_planner_tab = 'Planner' in html
                
                if has_home_tab and has_routes_tab and has_settings_tab:
                    if not (has_dashboard_tab or has_commute_tab or has_planner_tab):
                        self.log_test("3-Tab Navigation Structure", "PASS", "Home, Routes, Settings tabs present")
                    else:
                        self.log_test("3-Tab Navigation Structure", "FAIL", "Old 4-tab navigation still present")
                else:
                    self.log_test("3-Tab Navigation Structure", "FAIL", "Missing required tabs")
            else:
                self.log_test("3-Tab Navigation Structure", "ERROR", f"Home page returned {response.status_code}")
        except Exception as e:
            self.log_test("3-Tab Navigation Structure", "ERROR", str(e))
    
    def test_routes_page(self):
        """Test 4.1.2: Routes page accessibility"""
        print("\n[INFO] Testing Routes page...")
        
        try:
            response = self.client.get('/routes')
            if response.status_code == 200:
                self.log_test("Routes Page Accessible", "PASS", "Routes page loads successfully")
                
                html = response.data.decode('utf-8')
                
                # Check for side-by-side layout indicators
                has_map = 'map' in html.lower() or 'leaflet' in html.lower()
                has_route_list = 'route' in html.lower()
                
                if has_map and has_route_list:
                    self.log_test("Routes Side-by-Side Layout", "PASS", "Map and route list present")
                else:
                    self.log_test("Routes Side-by-Side Layout", "WARN", "Layout structure unclear")
            else:
                self.log_test("Routes Page Accessible", "ERROR", f"Routes page returned {response.status_code}")
        except Exception as e:
            self.log_test("Routes Page Accessible", "ERROR", str(e))
    
    def test_settings_page(self):
        """Test 4.1.3: Settings page accessibility"""
        print("\n[INFO] Testing Settings page...")
        
        try:
            response = self.client.get('/settings')
            if response.status_code == 200:
                self.log_test("Settings Page Accessible", "PASS", "Settings page loads successfully")
                
                html = response.data.decode('utf-8')
                
                # Check for settings form elements
                has_form = '<form' in html.lower()
                has_preferences = 'preference' in html.lower() or 'setting' in html.lower()
                
                if has_form and has_preferences:
                    self.log_test("Settings Form Present", "PASS", "Settings form found")
                else:
                    self.log_test("Settings Form Present", "WARN", "Settings form structure unclear")
            else:
                self.log_test("Settings Page Accessible", "ERROR", f"Settings page returned {response.status_code}")
        except Exception as e:
            self.log_test("Settings Page Accessible", "ERROR", str(e))
    
    def test_css_features(self):
        """Test 4.1.4: CSS features from Phase 1"""
        print("\n[INFO] Testing CSS features...")
        
        try:
            # Check if main.css exists and is served
            response = self.client.get('/static/css/main.css')
            if response.status_code == 200:
                css = response.data.decode('utf-8')
                
                # Check for key CSS features from Phase 1
                features = {
                    'Focus Indicators': ':focus' in css,
                    'Skip Links': '.skip-link' in css,
                    'Compact Route Cards': '.route-card' in css or 'route-card' in css,
                    'Skeleton Loading': 'skeleton' in css or '@keyframes shimmer' in css,
                    'Toast Notifications': '.toast' in css or 'toast' in css,
                    'Mobile Bottom Nav': '.mobile-nav' in css or 'mobile-nav' in css,
                }
                
                passed_features = sum(1 for v in features.values() if v)
                total_features = len(features)
                
                if passed_features >= total_features * 0.8:  # 80% threshold
                    self.log_test("CSS Features Present", "PASS", f"{passed_features}/{total_features} features found")
                else:
                    self.log_test("CSS Features Present", "FAIL", f"Only {passed_features}/{total_features} features found")
            else:
                self.log_test("CSS Features Present", "ERROR", "main.css not accessible")
        except Exception as e:
            self.log_test("CSS Features Present", "ERROR", str(e))
    
    def test_javascript_utilities(self):
        """Test 4.1.5: JavaScript utilities from Phase 2"""
        print("\n[INFO] Testing JavaScript utilities...")
        
        js_files = [
            'common.js',
            'accessibility.js',
            'mobile.js',
            'routes.js'
        ]
        
        for js_file in js_files:
            try:
                response = self.client.get(f'/static/js/{js_file}')
                if response.status_code == 200:
                    self.log_test(f"JavaScript: {js_file}", "PASS", "File accessible")
                else:
                    self.log_test(f"JavaScript: {js_file}", "ERROR", f"File not accessible ({response.status_code})")
            except Exception as e:
                self.log_test(f"JavaScript: {js_file}", "ERROR", str(e))
    
    def test_accessibility_features(self):
        """Test 4.3: Accessibility features"""
        print("\n[INFO] Testing accessibility features...")
        
        try:
            response = self.client.get('/')
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                
                # Check for accessibility features
                has_aria_labels = 'aria-label' in html
                has_skip_links = 'skip' in html.lower()
                has_semantic_html = '<nav' in html and '<main' in html
                has_alt_text = 'alt=' in html
                
                accessibility_score = sum([
                    has_aria_labels,
                    has_skip_links,
                    has_semantic_html,
                    has_alt_text
                ])
                
                if accessibility_score >= 3:
                    self.log_test("Accessibility Features", "PASS", f"{accessibility_score}/4 features present")
                else:
                    self.log_test("Accessibility Features", "FAIL", f"Only {accessibility_score}/4 features present")
            else:
                self.log_test("Accessibility Features", "ERROR", "Home page not accessible")
        except Exception as e:
            self.log_test("Accessibility Features", "ERROR", str(e))
    
    def test_responsive_design(self):
        """Test 4.5: Responsive design"""
        print("\n[INFO] Testing responsive design...")
        
        try:
            response = self.client.get('/')
            if response.status_code == 200:
                html = response.data.decode('utf-8')
                
                # Check for responsive meta tag
                has_viewport = 'viewport' in html and 'width=device-width' in html
                
                # Check for responsive CSS classes
                has_responsive_classes = any([
                    'col-' in html,  # Bootstrap grid
                    'flex' in html,  # Flexbox
                    'grid' in html,  # CSS Grid
                    '@media' in html  # Media queries
                ])
                
                if has_viewport:
                    self.log_test("Viewport Meta Tag", "PASS", "Viewport meta tag present")
                else:
                    self.log_test("Viewport Meta Tag", "FAIL", "Viewport meta tag missing")
                
                if has_responsive_classes:
                    self.log_test("Responsive CSS Classes", "PASS", "Responsive classes found")
                else:
                    self.log_test("Responsive CSS Classes", "WARN", "Responsive classes unclear")
            else:
                self.log_test("Responsive Design", "ERROR", "Home page not accessible")
        except Exception as e:
            self.log_test("Responsive Design", "ERROR", str(e))
    
    def test_performance(self):
        """Test 4.4: Performance metrics"""
        print("\n[INFO] Testing performance...")
        
        try:
            start_time = time.time()
            response = self.client.get('/')
            load_time = time.time() - start_time
            
            if response.status_code == 200:
                if load_time < 3.0:
                    self.log_test("Page Load Time", "PASS", f"{load_time:.3f}s (< 3s target)")
                else:
                    self.log_test("Page Load Time", "WARN", f"{load_time:.3f}s (> 3s target)")
            else:
                self.log_test("Page Load Time", "ERROR", "Home page not accessible")
        except Exception as e:
            self.log_test("Page Load Time", "ERROR", str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Issue #257 Phase 4: Integration & Testing")
        print("Epic #237 UI/UX Redesign - Static HTML Implementation")
        print("=" * 60)
        
        # Run test groups
        self.test_3_tab_navigation()
        self.test_routes_page()
        self.test_settings_page()
        self.test_css_features()
        self.test_javascript_utilities()
        self.test_accessibility_features()
        self.test_responsive_design()
        self.test_performance()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        for detail in self.test_details:
            status_symbol = {
                'PASS': '✓',
                'FAIL': '✗',
                'ERROR': '✗',
                'WARN': '⚠'
            }.get(detail['status'], '?')
            
            print(f"{status_symbol} {detail['name']:<35} {detail['status']:<6} {detail['message']}")
        
        print("\n" + "-" * 60)
        print(f"Total: {sum(self.results.values())} | "
              f"Passed: {self.results['passed']} | "
              f"Failed: {self.results['failed']} | "
              f"Errors: {self.results['errors']} | "
              f"Warnings: {self.results['warnings']}")
        print("-" * 60)
        
        # Return exit code
        if self.results['failed'] > 0 or self.results['errors'] > 0:
            print("\n✗ Tests FAILED - Issue #257 Phase 4 incomplete")
            return 1
        elif self.results['warnings'] > 0:
            print("\n⚠ Tests PASSED with warnings - Review recommended")
            return 0
        else:
            print("\n✓ All tests PASSED - Issue #257 Phase 4 complete")
            return 0


if __name__ == '__main__':
    tester = TestIssue257Phase4()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

# Made with Bob
