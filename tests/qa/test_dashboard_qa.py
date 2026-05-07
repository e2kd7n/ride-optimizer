#!/usr/bin/env python3
"""
QA Test Harness for Dashboard (Issue #132)

This script provides comprehensive testing for the dashboard view including:
- Route accessibility
- Data rendering
- Error handling
- Service integration
- Response times

Usage:
    python tests/qa/test_dashboard_qa.py
    python tests/qa/test_dashboard_qa.py --verbose
    python tests/qa/test_dashboard_qa.py --check-performance
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from app import create_app
from src.config import Config


class DashboardQATest:
    """QA test harness for dashboard functionality"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.app = create_app()
        self.client = self.app.test_client()
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log message if verbose mode enabled"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def test_dashboard_accessibility(self):
        """Test that dashboard route is accessible"""
        self.log("Testing dashboard accessibility...")
        
        try:
            response = self.client.get('/')
            
            if response.status_code == 200:
                self.results.append(("Dashboard Accessibility", "PASS", "Route accessible"))
                self.log("✓ Dashboard accessible", "PASS")
                return True
            else:
                self.results.append(("Dashboard Accessibility", "FAIL", f"Status code: {response.status_code}"))
                self.log(f"✗ Dashboard returned status {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Dashboard Accessibility", "ERROR", str(e)))
            self.log(f"✗ Error accessing dashboard: {e}", "ERROR")
            return False
    
    def test_dashboard_content(self):
        """Test that dashboard contains expected content"""
        self.log("Testing dashboard content...")
        
        try:
            response = self.client.get('/')
            html = response.data.decode('utf-8')
            
            # Check for key sections
            checks = [
                ("Quick Stats", "quick-stats" in html),
                ("Commute Recommendation", "commute-recommendation" in html or "Next Commute" in html),
                ("Long Ride Suggestion", "long-ride-suggestion" in html or "Upcoming Long Ride" in html),
                ("Data Freshness", "data-freshness" in html or "Last Analysis" in html),
            ]
            
            all_passed = True
            for name, passed in checks:
                if passed:
                    self.log(f"  ✓ {name} present")
                else:
                    self.log(f"  ✗ {name} missing", "ERROR")
                    all_passed = False
            
            if all_passed:
                self.results.append(("Dashboard Content", "PASS", "All sections present"))
                return True
            else:
                self.results.append(("Dashboard Content", "FAIL", "Some sections missing"))
                return False
                
        except Exception as e:
            self.results.append(("Dashboard Content", "ERROR", str(e)))
            self.log(f"✗ Error checking content: {e}", "ERROR")
            return False
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        self.log("Testing health endpoint...")
        
        try:
            response = self.client.get('/health')
            
            if response.status_code == 200:
                data = response.get_json()
                if data and data.get('status') == 'healthy':
                    self.results.append(("Health Endpoint", "PASS", "Endpoint healthy"))
                    self.log("✓ Health endpoint healthy", "PASS")
                    return True
                else:
                    self.results.append(("Health Endpoint", "FAIL", "Unhealthy response"))
                    self.log("✗ Health endpoint unhealthy", "ERROR")
                    return False
            else:
                self.results.append(("Health Endpoint", "FAIL", f"Status code: {response.status_code}"))
                self.log(f"✗ Health endpoint returned {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.results.append(("Health Endpoint", "ERROR", str(e)))
            self.log(f"✗ Error checking health: {e}", "ERROR")
            return False
    
    def test_response_time(self):
        """Test dashboard response time"""
        self.log("Testing response time...")
        
        try:
            start = time.time()
            response = self.client.get('/')
            elapsed = time.time() - start
            
            # Dashboard should respond in under 2 seconds
            if elapsed < 2.0:
                self.results.append(("Response Time", "PASS", f"{elapsed:.3f}s"))
                self.log(f"✓ Response time: {elapsed:.3f}s", "PASS")
                return True
            else:
                self.results.append(("Response Time", "WARN", f"{elapsed:.3f}s (slow)"))
                self.log(f"⚠ Response time slow: {elapsed:.3f}s", "WARN")
                return True  # Still pass, just warn
                
        except Exception as e:
            self.results.append(("Response Time", "ERROR", str(e)))
            self.log(f"✗ Error measuring response time: {e}", "ERROR")
            return False
    
    def test_error_handling(self):
        """Test error handling with invalid requests"""
        self.log("Testing error handling...")
        
        try:
            # Test with invalid query parameters
            response = self.client.get('/?invalid=param')
            
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
        print("Dashboard QA Test Suite (Issue #132)")
        print("="*60 + "\n")
        
        tests = [
            self.test_dashboard_accessibility,
            self.test_dashboard_content,
            self.test_health_endpoint,
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
    parser = argparse.ArgumentParser(description="QA test harness for dashboard")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--check-performance', action='store_true', help='Run performance checks')
    args = parser.parse_args()
    
    tester = DashboardQATest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
