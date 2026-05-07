#!/usr/bin/env python3
"""
QA Test Harness for Commute Views (Issue #133)

This script provides comprehensive testing for commute recommendation views including:
- Route accessibility
- Primary recommendation display
- Alternative routes
- Weather impact display
- Departure windows
- Score breakdowns

Usage:
    python tests/qa/test_commute_qa.py
    python tests/qa/test_commute_qa.py --verbose
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from app import create_app


class CommuteQATest:
    """QA test harness for commute functionality"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log message if verbose mode enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def test_commute_index_accessibility(self):
        """Test that commute index route is accessible"""
        self.log("Testing commute index accessibility...")
        
        try:
            response = self.client.get('/commute/')
            
            if response.status_code == 200:
                self.results.append(("Commute Index", "PASS", "Route accessible"))
                self.log("✓ Commute index accessible", "PASS")
                return True
            else:
                self.results.append(("Commute Index", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Commute index returned {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Commute Index", "ERROR", str(e)))
            self.log(f"✗ Error accessing commute index: {e}", "ERROR")
            return False
    
    def test_commute_content_sections(self):
        """Test that commute page contains expected sections"""
        self.log("Testing commute content sections...")
        
        try:
            response = self.client.get('/commute/')
            html = response.data.decode('utf-8')
            
            # Check for key sections
            checks = [
                ("Primary Recommendation", "primary-recommendation" in html or "Recommended Route" in html),
                ("Weather Impact", "weather-impact" in html or "Weather Conditions" in html),
                ("Score Breakdown", "score-breakdown" in html or "Route Score" in html),
                ("Alternative Routes", "alternatives" in html or "Other Options" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} present")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Commute Content", "PASS", "All sections present"))
                return True
            else:
                self.results.append(("Commute Content", "FAIL", "Some sections missing"))
                return False
                
        except Exception as e:
            self.results.append(("Commute Content", "ERROR", str(e)))
            self.log(f"✗ Error checking content: {e}", "ERROR")
            return False
    
    def test_departure_time_parameter(self):
        """Test departure time parameter handling"""
        self.log("Testing departure time parameter...")
        
        try:
            # Test with specific departure time
            response = self.client.get('/commute/?departure_time=08:00')
            
            if response.status_code == 200:
                self.results.append(("Departure Time Param", "PASS", "Parameter accepted"))
                self.log("✓ Departure time parameter handled", "PASS")
                return True
            else:
                self.results.append(("Departure Time Param", "FAIL", f"Status: {response.status_code}"))
                self.log(f"✗ Departure time param failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Departure Time Param", "ERROR", str(e)))
            self.log(f"✗ Error testing departure time: {e}", "ERROR")
            return False
    
    def test_response_time(self):
        """Test commute page response time"""
        self.log("Testing response time...")
        
        try:
            start = time.time()
            response = self.client.get('/commute/')
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
            # Test with invalid departure time
            response = self.client.get('/commute/?departure_time=invalid')
            
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
        print("Commute Views QA Test Suite (Issue #133)")
        print("="*60 + "\n")
        
        tests = [
            self.test_commute_index_accessibility,
            self.test_commute_content_sections,
            self.test_departure_time_parameter,
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
    parser = argparse.ArgumentParser(description="QA test harness for commute views")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    tester = CommuteQATest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
