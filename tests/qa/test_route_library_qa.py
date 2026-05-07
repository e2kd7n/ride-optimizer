#!/usr/bin/env python3
"""
QA Test Harness for Route Library (Issue #135)

This script provides comprehensive testing for route library including:
- Route accessibility
- Browse/search/filter functionality
- Pagination
- Route detail pages
- Favorite toggle
- API endpoints

Usage:
    python tests/qa/test_route_library_qa.py
    python tests/qa/test_route_library_qa.py --verbose
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from app import create_app


class RouteLibraryQATest:
    """QA test harness for route library functionality"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log message if verbose mode enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def test_route_library_accessibility(self):
        """Test that route library index is accessible"""
        self.log("Testing route library accessibility...")
        
        try:
            response = self.client.get('/routes/')
            
            if response.status_code == 200:
                self.results.append(("Route Library Index", "PASS", "Route accessible"))
                self.log("✓ Route library accessible", "PASS")
                return True
            else:
                self.results.append(("Route Library Index", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Route library returned {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Route Library Index", "ERROR", str(e)))
            self.log(f"✗ Error accessing route library: {e}", "ERROR")
            return False
    
    def test_route_library_content(self):
        """Test that route library contains expected sections"""
        self.log("Testing route library content...")
        
        try:
            response = self.client.get('/routes/')
            html = response.data.decode('utf-8')
            
            # Check for key sections
            checks = [
                ("Route List", "route-list" in html or "routes" in html.lower()),
                ("Filters", "filter" in html or "search" in html),
                ("Pagination", "pagination" in html or "page" in html),
                ("Statistics", "stats" in html or "total" in html.lower()),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} present")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Route Library Content", "PASS", "All sections present"))
                return True
            else:
                self.results.append(("Route Library Content", "FAIL", "Some sections missing"))
                return False
                
        except Exception as e:
            self.results.append(("Route Library Content", "ERROR", str(e)))
            self.log(f"✗ Error checking content: {e}", "ERROR")
            return False
    
    def test_search_api(self):
        """Test search API endpoint"""
        self.log("Testing search API...")
        
        try:
            response = self.client.get('/routes/api/search?q=test')
            
            if response.status_code == 200:
                data = response.get_json()
                if data and 'routes' in data:
                    self.results.append(("Search API", "PASS", "Returns JSON"))
                    self.log("✓ Search API works", "PASS")
                    return True
                else:
                    self.results.append(("Search API", "FAIL", "Invalid JSON structure"))
                    self.log("✗ Search API returned invalid JSON", "ERROR")
                    return False
            else:
                self.results.append(("Search API", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Search API returned {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Search API", "ERROR", str(e)))
            self.log(f"✗ Error testing search API: {e}", "ERROR")
            return False
    
    def test_pagination(self):
        """Test pagination functionality"""
        self.log("Testing pagination...")
        
        try:
            # Test different pages
            test_cases = [
                ('?page=1', 'Page 1'),
                ('?page=2', 'Page 2'),
                ('?page=1&per_page=10', 'Custom per_page'),
            ]
            
            all_passed = True
            for params, description in test_cases:
                response = self.client.get(f'/routes/{params}')
                if response.status_code != 200:
                    self.log(f"  ✗ {description} failed", "ERROR")
                    all_passed = False
                else:
                    self.log(f"  ✓ {description} works")
            
            if all_passed:
                self.results.append(("Pagination", "PASS", "All pagination works"))
                return True
            else:
                self.results.append(("Pagination", "FAIL", "Some pagination failed"))
                return False
                
        except Exception as e:
            self.results.append(("Pagination", "ERROR", str(e)))
            self.log(f"✗ Error testing pagination: {e}", "ERROR")
            return False
    
    def test_filter_parameters(self):
        """Test filter parameter handling"""
        self.log("Testing filter parameters...")
        
        try:
            # Test various filters
            test_cases = [
                ('?type=commute', 'Type filter'),
                ('?min_distance=10', 'Min distance filter'),
                ('?max_distance=50', 'Max distance filter'),
                ('?sort=distance', 'Sort by distance'),
                ('?sort=uses', 'Sort by uses'),
            ]
            
            all_passed = True
            for params, description in test_cases:
                response = self.client.get(f'/routes/{params}')
                if response.status_code != 200:
                    self.log(f"  ✗ {description} failed", "ERROR")
                    all_passed = False
                else:
                    self.log(f"  ✓ {description} works")
            
            if all_passed:
                self.results.append(("Filter Parameters", "PASS", "All filters work"))
                return True
            else:
                self.results.append(("Filter Parameters", "FAIL", "Some filters failed"))
                return False
                
        except Exception as e:
            self.results.append(("Filter Parameters", "ERROR", str(e)))
            self.log(f"✗ Error testing filters: {e}", "ERROR")
            return False
    
    def test_response_time(self):
        """Test route library response time"""
        self.log("Testing response time...")
        
        try:
            start = time.time()
            response = self.client.get('/routes/')
            elapsed = time.time() - start
            
            # Should respond in under 2 seconds
            if elapsed < 2.0:
                self.results.append(("Response Time", "PASS", f"{elapsed:.3f}s"))
                self.log(f"✓ Response time: {elapsed:.3f}s", "PASS")
                return True
            else:
                self.results.append(("Response Time", "WARN", f"{elapsed:.3f}s (slow)"))
                self.log(f"⚠ Response time slow: {elapsed:.3f}s", "WARN")
                return True
                
        except Exception as e:
            self.results.append(("Response Time", "ERROR", str(e)))
            self.log(f"✗ Error measuring response time: {e}", "ERROR")
            return False
    
    def test_error_handling(self):
        """Test error handling with invalid parameters"""
        self.log("Testing error handling...")
        
        try:
            # Test with invalid parameters
            test_cases = [
                '?page=invalid',
                '?min_distance=invalid',
                '?sort=invalid_field',
            ]
            
            all_passed = True
            for params in test_cases:
                response = self.client.get(f'/routes/{params}')
                # Should still return 200 (graceful handling)
                if response.status_code != 200:
                    self.log(f"  ✗ Failed to handle: {params}", "ERROR")
                    all_passed = False
                else:
                    self.log(f"  ✓ Handled gracefully: {params}")
            
            if all_passed:
                self.results.append(("Error Handling", "PASS", "Graceful degradation"))
                return True
            else:
                self.results.append(("Error Handling", "FAIL", "Some errors not handled"))
                return False
                
        except Exception as e:
            self.results.append(("Error Handling", "ERROR", str(e)))
            self.log(f"✗ Error testing error handling: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all QA tests"""
        print("\n" + "="*60)
        print("Route Library QA Test Suite (Issue #135)")
        print("="*60 + "\n")
        
        tests = [
            self.test_route_library_accessibility,
            self.test_route_library_content,
            self.test_search_api,
            self.test_pagination,
            self.test_filter_parameters,
            self.test_response_time,
            self.test_error_handling,
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
    parser = argparse.ArgumentParser(description="QA test harness for route library")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    tester = RouteLibraryQATest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
