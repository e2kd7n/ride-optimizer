#!/usr/bin/env python3
"""
QA Test Harness for Long Ride Planner (Issue #134)

This script provides comprehensive testing for the long ride planner view including:
- Route accessibility
- Ride recommendations display
- Weather forecast integration
- Workout fit display
- Route variety suggestions
- Response times

Usage:
    python tests/qa/test_planner_qa.py
    python tests/qa/test_planner_qa.py --verbose
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from app import create_app


class PlannerQATest:
    """QA test harness for long ride planner functionality"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log message if verbose mode enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def test_planner_accessibility(self):
        """Test that planner route is accessible"""
        self.log("Testing planner accessibility...")
        
        try:
            response = self.client.get('/planner/')
            
            if response.status_code == 200:
                self.results.append(("Planner Accessibility", "PASS", "Route accessible"))
                self.log("✓ Planner accessible", "PASS")
                return True
            else:
                self.results.append(("Planner Accessibility", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Planner returned {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Planner Accessibility", "ERROR", str(e)))
            self.log(f"✗ Error accessing planner: {e}", "ERROR")
            return False
    
    def test_planner_content_sections(self):
        """Test that planner page contains expected sections"""
        self.log("Testing planner content sections...")
        
        try:
            response = self.client.get('/planner/')
            html = response.data.decode('utf-8')
            
            # Check for key sections
            checks = [
                ("Ride Recommendations", "ride-recommendations" in html or "Recommended Rides" in html),
                ("Weather Forecast", "weather-forecast" in html or "7-Day Forecast" in html),
                ("Workout Fit", "workout-fit" in html or "Training Load" in html),
                ("Route Variety", "route-variety" in html or "Explore New Routes" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} present")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Planner Content", "PASS", "All sections present"))
                return True
            else:
                self.results.append(("Planner Content", "FAIL", "Some sections missing"))
                return False
                
        except Exception as e:
            self.results.append(("Planner Content", "ERROR", str(e)))
            self.log(f"✗ Error checking content: {e}", "ERROR")
            return False
    
    def test_date_range_parameter(self):
        """Test date range parameter handling"""
        self.log("Testing date range parameter...")
        
        try:
            # Test with specific date range
            response = self.client.get('/planner/?days=7')
            
            if response.status_code == 200:
                self.results.append(("Date Range Param", "PASS", "Parameter accepted"))
                self.log("✓ Date range parameter handled", "PASS")
                return True
            else:
                self.results.append(("Date Range Param", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Date range param failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Date Range Param", "ERROR", str(e)))
            self.log(f"✗ Error testing date range: {e}", "ERROR")
            return False
    
    def test_response_time(self):
        """Test planner page response time"""
        self.log("Testing response time...")
        
        try:
            start = time.time()
            response = self.client.get('/planner/')
            elapsed = time.time() - start
            
            # Should respond in under 3 seconds (weather API calls)
            if elapsed < 3.0:
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
            # Test with invalid date range
            response = self.client.get('/planner/?days=invalid')
            
            # Should still return 200 (graceful handling)
            if response.status_code == 200:
                self.results.append(("Error Handling", "PASS", "Graceful degradation"))
                self.log("✓ Handles invalid params gracefully", "PASS")
                return True
            else:
                self.results.append(("Error Handling", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Error handling failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Error Handling", "ERROR", str(e)))
            self.log(f"✗ Error testing error handling: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all QA tests"""
        print("\n" + "="*60)
        print("Long Ride Planner QA Test Suite (Issue #134)")
        print("="*60 + "\n")
        
        tests = [
            self.test_planner_accessibility,
            self.test_planner_content_sections,
            self.test_date_range_parameter,
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
    parser = argparse.ArgumentParser(description="QA test harness for long ride planner")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    tester = PlannerQATest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob