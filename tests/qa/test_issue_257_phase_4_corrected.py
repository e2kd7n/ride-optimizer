#!/usr/bin/env python3
"""
Issue #257 Phase 4: Integration & Testing (CORRECTED)
Tests for Epic #237 UI/UX Redesign implementation in static HTML files

This test suite validates the CORRECT application (launch.py + static/ files),
NOT the deprecated Flask app factory (app/__init__.py).

Related Issues: #257, #255, #237
"""

import sys
import time
import requests
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8083"
TIMEOUT = 5


class TestIssue257Phase4Corrected:
    """Test suite for Issue #257 Phase 4 - Testing launch.py application"""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'warnings': 0
        }
        self.test_details = []
    
    def log_test(self, name, status, message=""):
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
    
    def test_server_running(self):
        """Test that launch.py server is running"""
        print("\n[INFO] Testing server availability...")
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                self.log_test("Server Running", "PASS")
                return True
            else:
                self.log_test("Server Running", "FAIL", f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Server Running", "ERROR", str(e))
            return False
    
    def test_3_tab_navigation(self):
        """Test 4.1.1: 3-tab navigation structure in static/index.html"""
        print("\n[INFO] Testing 3-tab navigation...")
        
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                html = response.text
                
                # Check for 3-tab navigation
                has_home_tab = 'id="home-tab"' in html or 'data-target="home"' in html
                has_routes_tab = 'id="routes-tab"' in html or 'data-target="routes"' in html
                has_settings_tab = 'id="settings-tab"' in html or 'data-target="settings"' in html
                
                # Check for tab content panes
                has_home_pane = 'id="home"' in html and 'role="tabpanel"' in html
                has_routes_pane = 'id="routes"' in html and 'role="tabpanel"' in html
                has_settings_pane = 'id="settings"' in html and 'role="tabpanel"' in html
                
                if has_home_tab and has_routes_tab and has_settings_tab:
                    if has_home_pane and has_routes_pane and has_settings_pane:
                        self.log_test("3-Tab Navigation Structure", "PASS")
                    else:
                        self.log_test("3-Tab Navigation Structure", "FAIL", "Tab panes missing")
                else:
                    self.log_test("3-Tab Navigation Structure", "FAIL", "Missing required tabs")
            else:
                self.log_test("3-Tab Navigation Structure", "ERROR", f"Status {response.status_code}")
        except Exception as e:
            self.log_test("3-Tab Navigation Structure", "ERROR", str(e))
    
    def test_static_files(self):
        """Test that all static files are accessible"""
        print("\n[INFO] Testing static file accessibility...")
        
        files_to_test = [
            ('/static/css/main.css', 'CSS File'),
            ('/static/js/common.js', 'common.js'),
            ('/static/js/accessibility.js', 'accessibility.js'),
            ('/static/js/mobile.js', 'mobile.js'),
            ('/static/js/routes.js', 'routes.js'),
            ('/static/js/dashboard.js', 'dashboard.js'),
            ('/static/js/api-client.js', 'api-client.js'),
        ]
        
        for path, name in files_to_test:
            try:
                response = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
                if response.status_code == 200:
                    self.log_test(f"Static File: {name}", "PASS")
                else:
                    self.log_test(f"Static File: {name}", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log_test(f"Static File: {name}", "ERROR", str(e))
    
    def test_api_endpoints(self):
        """Test that API endpoints are working"""
        print("\n[INFO] Testing API endpoints...")
        
        endpoints = [
            ('/api/status', 'Status API'),
            ('/api/weather', 'Weather API'),
            ('/api/recommendation', 'Recommendation API'),
            ('/api/routes', 'Routes API'),
        ]
        
        for path, name in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success' or 'status' in data:
                        self.log_test(f"API: {name}", "PASS")
                    else:
                        self.log_test(f"API: {name}", "WARN", "Unexpected response format")
                else:
                    self.log_test(f"API: {name}", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log_test(f"API: {name}", "ERROR", str(e))
    
    def test_css_features(self):
        """Test that CSS features are present"""
        print("\n[INFO] Testing CSS features...")
        
        try:
            response = requests.get(f"{BASE_URL}/static/css/main.css", timeout=TIMEOUT)
            if response.status_code == 200:
                css = response.text
                
                features = {
                    'Skip Links': '.skip-link' in css,
                    'Focus Indicators': ':focus' in css,
                    'Skeleton Loading': '.skeleton' in css,
                    'Toast Notifications': '.toast' in css,
                    'Mobile Bottom Nav': '.bottom-nav' in css,
                    'Route Cards': '.route-card' in css or '.route-row' in css,
                }
                
                found = sum(1 for v in features.values() if v)
                total = len(features)
                
                if found == total:
                    self.log_test("CSS Features", "PASS", f"All {total} features present")
                elif found >= total * 0.7:
                    self.log_test("CSS Features", "WARN", f"{found}/{total} features found")
                else:
                    self.log_test("CSS Features", "FAIL", f"Only {found}/{total} features found")
                    
                # Log missing features
                for feature, present in features.items():
                    if not present:
                        print(f"    Missing: {feature}")
            else:
                self.log_test("CSS Features", "ERROR", f"Status {response.status_code}")
        except Exception as e:
            self.log_test("CSS Features", "ERROR", str(e))
    
    def test_accessibility_features(self):
        """Test accessibility features in HTML"""
        print("\n[INFO] Testing accessibility features...")
        
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                html = response.text
                
                features = {
                    'Skip Links': 'class="skip-link"' in html,
                    'ARIA Labels': 'aria-label=' in html,
                    'ARIA Roles': 'role=' in html,
                    'Alt Text': 'alt=' in html or 'aria-hidden="true"' in html,
                    'Semantic HTML': '<nav' in html and '<main' in html,
                    'Viewport Meta': 'viewport' in html,
                }
                
                found = sum(1 for v in features.values() if v)
                total = len(features)
                
                if found == total:
                    self.log_test("Accessibility Features", "PASS", f"All {total} features present")
                elif found >= total * 0.8:
                    self.log_test("Accessibility Features", "WARN", f"{found}/{total} features found")
                else:
                    self.log_test("Accessibility Features", "FAIL", f"Only {found}/{total} features found")
            else:
                self.log_test("Accessibility Features", "ERROR", f"Status {response.status_code}")
        except Exception as e:
            self.log_test("Accessibility Features", "ERROR", str(e))
    
    def test_responsive_design(self):
        """Test responsive design features"""
        print("\n[INFO] Testing responsive design...")
        
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                html = response.text
                
                features = {
                    'Viewport Meta': 'viewport' in html,
                    'Bootstrap Grid': 'col-' in html,
                    'Mobile Classes': 'd-md-' in html or 'd-lg-' in html,
                    'Bottom Nav': 'bottom-nav' in html,
                }
                
                found = sum(1 for v in features.values() if v)
                total = len(features)
                
                if found == total:
                    self.log_test("Responsive Design", "PASS", f"All {total} features present")
                elif found >= total * 0.75:
                    self.log_test("Responsive Design", "WARN", f"{found}/{total} features found")
                else:
                    self.log_test("Responsive Design", "FAIL", f"Only {found}/{total} features found")
            else:
                self.log_test("Responsive Design", "ERROR", f"Status {response.status_code}")
        except Exception as e:
            self.log_test("Responsive Design", "ERROR", str(e))
    
    def test_performance(self):
        """Test page load performance"""
        print("\n[INFO] Testing performance...")
        
        try:
            start = time.time()
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            load_time = time.time() - start
            
            if response.status_code == 200:
                if load_time < 1.0:
                    self.log_test("Page Load Time", "PASS", f"{load_time:.2f}s")
                elif load_time < 2.0:
                    self.log_test("Page Load Time", "WARN", f"{load_time:.2f}s (target: <1s)")
                else:
                    self.log_test("Page Load Time", "FAIL", f"{load_time:.2f}s (too slow)")
            else:
                self.log_test("Page Load Time", "ERROR", f"Status {response.status_code}")
        except Exception as e:
            self.log_test("Page Load Time", "ERROR", str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Issue #257 Phase 4: Integration & Testing (CORRECTED)")
        print("Testing launch.py + static/ files (Smart Static Architecture)")
        print("=" * 60)
        
        # Check server is running first
        if not self.test_server_running():
            print("\n[ERROR] Server not running at", BASE_URL)
            print("[ERROR] Please start server with: python3 launch.py")
            return False
        
        # Run all tests
        self.test_3_tab_navigation()
        self.test_static_files()
        self.test_api_endpoints()
        self.test_css_features()
        self.test_accessibility_features()
        self.test_responsive_design()
        self.test_performance()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"✓ Passed:   {self.results['passed']}")
        print(f"✗ Failed:   {self.results['failed']}")
        print(f"✗ Errors:   {self.results['errors']}")
        print(f"⚠ Warnings: {self.results['warnings']}")
        print("=" * 60)
        
        total_tests = sum(self.results.values())
        success_rate = (self.results['passed'] / total_tests * 100) if total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if self.results['failed'] == 0 and self.results['errors'] == 0:
            print("\n✓ ALL TESTS PASSED!")
            return True
        else:
            print("\n✗ SOME TESTS FAILED")
            return False


if __name__ == '__main__':
    tester = TestIssue257Phase4Corrected()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

# Made with Bob
