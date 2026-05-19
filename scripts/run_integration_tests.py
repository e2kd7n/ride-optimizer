#!/usr/bin/env python3
"""
Cross-platform integration test runner for Ride Optimizer.
Replaces run_integration_tests.sh with Python for Windows compatibility.

Usage:
    python scripts/run_integration_tests.py [coverage]
"""

import sys
import subprocess
import shutil
from pathlib import Path


class Color:
    """ANSI color codes (work in most terminals including Windows 10+)."""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def check_pytest():
    """Check if pytest is installed."""
    if not shutil.which('pytest'):
        print(f"{Color.RED}Error: pytest not found{Color.NC}")
        print("Install with: pip install pytest pytest-cov")
        return False
    return True


def run_test_suite(test_file, description):
    """Run a specific test suite."""
    print(f"{Color.YELLOW}=== {description} ==={Color.NC}")
    
    cmd = [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short']
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"{Color.GREEN}✓ {description} passed{Color.NC}")
        return True
    else:
        print(f"{Color.RED}✗ {description} failed{Color.NC}")
        return False


def main():
    """Run integration test suite."""
    print("=" * 40)
    print("Ride Optimizer - Integration Test Suite")
    print("=" * 40)
    print()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    # Activate virtual environment if it exists
    venv_path = project_root / "venv"
    if venv_path.exists():
        print("Virtual environment detected...")
        # Note: Virtual env activation is handled by the Python interpreter
        # that's already running this script
    
    # Check if pytest is installed
    if not check_pytest():
        return 1
    
    print("Running integration tests...")
    print()
    
    # Track results
    all_passed = True
    
    # Run API integration tests
    if not run_test_suite('tests/test_api_integration.py', 'API Integration Tests'):
        all_passed = False
    print()
    
    # Run API unit tests
    if not run_test_suite('tests/test_api.py', 'API Unit Tests'):
        all_passed = False
    print()
    
    # Run JSON storage tests
    if not run_test_suite('tests/test_json_storage.py', 'JSON Storage Tests'):
        all_passed = False
    print()
    
    # Summary
    print("=" * 40)
    if all_passed:
        print(f"{Color.GREEN}All integration tests passed!{Color.NC}")
    else:
        print(f"{Color.RED}Some integration tests failed!{Color.NC}")
    print("=" * 40)
    print()
    
    # Generate coverage report if requested
    if len(sys.argv) > 1 and sys.argv[1] == 'coverage':
        print("Generating coverage report...")
        cmd = [
            sys.executable, '-m', 'pytest',
            'tests/test_api_integration.py',
            'tests/test_api.py',
            'tests/test_json_storage.py',
            '--cov=launch',
            '--cov=src.json_storage',
            '--cov=app.services',
            '--cov-report=html',
            '--cov-report=term'
        ]
        subprocess.run(cmd)
        print()
        print("Coverage report generated in htmlcov/index.html")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob