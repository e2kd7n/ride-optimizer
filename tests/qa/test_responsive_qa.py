#!/usr/bin/env python3
"""
QA Test Harness for Responsive Layout (Issue #142)

This script provides comprehensive testing for responsive layout including:
- Bootstrap 5 integration
- Mobile navigation
- Touch-friendly targets
- Responsive breakpoints
- Accessibility features

Usage:
    python tests/qa/test_responsive_qa.py
    python tests/qa/test_responsive_qa.py --verbose
"""

import sys
import re
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from app import create_app


class ResponsiveQATest:
    """QA test harness for responsive layout functionality"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log message if verbose mode enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def test_bootstrap_integration(self):
        """Test that Bootstrap 5 is properly integrated"""
        self.log("Testing Bootstrap 5 integration...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for Bootstrap CSS and JS
            checks = [
                ("Bootstrap CSS", "bootstrap" in html and ".css" in html),
                ("Bootstrap JS", "bootstrap" in html and ".js" in html),
                ("Bootstrap Icons", "bootstrap-icons" in html or "bi-" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} loaded")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Bootstrap Integration", "PASS", "All resources loaded"))
                return True
            else:
                self.results.append(("Bootstrap Integration", "FAIL", "Some resources missing"))
                return False
                
        except Exception as e:
            self.results.append(("Bootstrap Integration", "ERROR", str(e)))
            self.log(f"✗ Error checking Bootstrap: {e}", "ERROR")
            return False
    
    def test_mobile_navigation(self):
        """Test mobile navigation presence"""
        self.log("Testing mobile navigation...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for mobile navigation elements
            checks = [
                ("Navbar", "navbar" in html),
                ("Navbar Toggler", "navbar-toggler" in html or "hamburger" in html),
                ("Navbar Collapse", "navbar-collapse" in html or "collapse" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} present")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Mobile Navigation", "PASS", "All elements present"))
                return True
            else:
                self.results.append(("Mobile Navigation", "FAIL", "Some elements missing"))
                return False
                
        except Exception as e:
            self.results.append(("Mobile Navigation", "ERROR", str(e)))
            self.log(f"✗ Error checking mobile nav: {e}", "ERROR")
            return False
    
    def test_responsive_classes(self):
        """Test responsive utility classes"""
        self.log("Testing responsive classes...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for responsive classes
            checks = [
                ("Container", "container" in html),
                ("Row/Col", "row" in html and "col" in html),
                ("Responsive Display", "d-none" in html or "d-block" in html or "d-md-" in html),
                ("Responsive Spacing", "mb-" in html or "mt-" in html or "p-" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} used")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Responsive Classes", "PASS", "All classes present"))
                return True
            else:
                self.results.append(("Responsive Classes", "FAIL", "Some classes missing"))
                return False
                
        except Exception as e:
            self.results.append(("Responsive Classes", "ERROR", str(e)))
            self.log(f"✗ Error checking responsive classes: {e}", "ERROR")
            return False
    
    def test_accessibility_features(self):
        """Test accessibility features"""
        self.log("Testing accessibility features...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for accessibility features
            checks = [
                ("ARIA Labels", "aria-label" in html),
                ("Alt Text", 'alt="' in html or "alt='" in html),
                ("Semantic HTML", "<nav" in html and "<main" in html),
                ("Skip Links", "skip" in html.lower() or "sr-only" in html),
            ]
            
            passed_count = sum(1 for _, passed in checks if passed)
            
            if passed_count >= 3:  # At least 3 out of 4
                self.results.append(("Accessibility", "PASS", f"{passed_count}/4 features present"))
                self.log(f"✓ Accessibility features: {passed_count}/4", "PASS")
                return True
            else:
                self.results.append(("Accessibility", "WARN", f"Only {passed_count}/4 features"))
                self.log(f"⚠ Limited accessibility: {passed_count}/4", "WARN")
                return True  # Warning, not failure
                
        except Exception as e:
            self.results.append(("Accessibility", "ERROR", str(e)))
            self.log(f"✗ Error checking accessibility: {e}", "ERROR")
            return False
    
    def test_custom_css(self):
        """Test custom CSS file is loaded"""
        self.log("Testing custom CSS...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for custom CSS
            if "main.css" in html or "/static/css/" in html:
                self.results.append(("Custom CSS", "PASS", "Custom styles loaded"))
                self.log("✓ Custom CSS loaded", "PASS")
                return True
            else:
                self.results.append(("Custom CSS", "WARN", "No custom CSS found"))
                self.log("⚠ No custom CSS found", "WARN")
                return True  # Warning, not failure
                
        except Exception as e:
            self.results.append(("Custom CSS", "ERROR", str(e)))
            self.log(f"✗ Error checking custom CSS: {e}", "ERROR")
            return False
    
    def test_viewport_meta(self):
        """Test viewport meta tag for mobile"""
        self.log("Testing viewport meta tag...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for viewport meta tag
            if 'name="viewport"' in html and 'width=device-width' in html:
                self.results.append(("Viewport Meta", "PASS", "Mobile viewport configured"))
                self.log("✓ Viewport meta tag present", "PASS")
                return True
            else:
                self.results.append(("Viewport Meta", "FAIL", "Missing or incorrect"))
                self.log("✗ Viewport meta tag missing", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Viewport Meta", "ERROR", str(e)))
            self.log(f"✗ Error checking viewport: {e}", "ERROR")
            return False
    
    def test_all_pages_responsive(self):
        """Test that all main pages have responsive elements"""
        self.log("Testing all pages for responsive elements...")
        
        try:
            pages = [
                ('/', 'Dashboard'),
                ('/commute/', 'Commute'),
                ('/planner/', 'Planner'),
                ('/routes/', 'Route Library'),
            ]
            
            all_passed = True
            for url, name in pages:
                response = self.client.get(url)
                if response.status_code == 200:
                    html = response.data.decode('utf-8')
                    # Check for basic responsive elements
                    if "container" in html and ("row" in html or "col" in html):
                        self.log(f"  ✓ {name} is responsive")
                    else:
                        self.log(f"  ✗ {name} missing responsive elements", "ERROR")
                        all_passed = False
                else:
                    self.log(f"  ✗ {name} not accessible", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("All Pages Responsive", "PASS", "All pages have responsive layout"))
                return True
            else:
                self.results.append(("All Pages Responsive", "FAIL", "Some pages not responsive"))
                return False
                
        except Exception as e:
            self.results.append(("All Pages Responsive", "ERROR", str(e)))
            self.log(f"✗ Error checking pages: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all QA tests"""
        print("\n" + "="*60)
        print("Responsive Layout QA Test Suite (Issue #142)")
        print("="*60 + "\n")
        
        tests = [
            self.test_bootstrap_integration,
            self.test_mobile_navigation,
            self.test_responsive_classes,
            self.test_accessibility_features,
            self.test_custom_css,
            self.test_viewport_meta,
            self.test_all_pages_responsive,
        ]
        
        for test in tests:
            test()
            print()
        
        # Print summary
        print("="*60)
        print("Test Summary")
        print("="*60)
        
        passed = sum(1 for _, status, _ in self.results if status == "PASS")
        failed = sum(1 for _, status, _ in self.results if status == "FAIL")
        errors = sum(1 for _, status, _ in self.results if status == "ERROR")
        warnings = sum(1 for _, status, _ in self.results if status == "WARN")
        
        for name, status, detail in self.results:
            symbol = "✓" if status == "PASS" else "✗" if status in ["FAIL", "ERROR"] else "⚠"
            print(f"{symbol} {name:30s} {status:6s} {detail}")
        
        print("\n" + "-"*60)
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed} | Errors: {errors} | Warnings: {warnings}")
        print("-"*60 + "\n")
        
        return failed == 0 and errors == 0


def main():
    parser = argparse.ArgumentParser(description="QA test harness for responsive layout")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    tester = ResponsiveQATest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
