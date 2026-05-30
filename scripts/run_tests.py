#!/usr/bin/env python3
"""
Cross-platform test runner for Ride Optimizer.
Replaces run_tests.sh with Python for Windows compatibility.

Usage:
    python scripts/run_tests.py [all|unit|integration|coverage|quick|watch]
"""

import sys
import subprocess
import shutil
import argparse
from pathlib import Path
import re


class Color:
    """ANSI color codes (work in most terminals including Windows 10+)."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def check_pytest():
    """Check if pytest is installed."""
    if not shutil.which('pytest'):
        print(f"{Color.RED}❌ pytest not found. Installing test dependencies...{Color.END}")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        return False
    return True


def run_tests(test_type='all'):
    """Run tests based on type."""
    print(f"{Color.BLUE}🧪 Running Ride Optimizer Tests{Color.END}")
    print("=" * 40)
    print()
    
    check_pytest()
    
    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest', '-v']
    
    if test_type == 'unit':
        print("📋 Running unit tests only...")
        cmd.extend(['-m', 'unit'])
    elif test_type == 'integration':
        print("📋 Running integration tests only...")
        cmd.extend(['-m', 'integration'])
    elif test_type == 'coverage':
        print("📋 Running tests with coverage report...")
        cmd.extend(['--cov=src', '--cov=app', '--cov-report=html', '--cov-report=term'])
    elif test_type == 'quick':
        print("📋 Running quick tests (excluding slow tests)...")
        cmd.extend(['-m', 'not slow'])
    elif test_type == 'watch':
        print("👀 Running tests in watch mode...")
        if not shutil.which('pytest-watch'):
            print(f"{Color.YELLOW}Installing pytest-watch...{Color.END}")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pytest-watch'])
        subprocess.run(['pytest-watch'])
        return 0
    else:
        print("📋 Running all tests...")
    
    # Run tests and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    # Print output
    print(output)
    
    # Parse results
    print()
    print("=" * 40)
    print(f"{Color.BOLD}📊 TEST SUMMARY{Color.END}")
    print("=" * 40)
    
    # Extract test counts
    passed_match = re.search(r'(\d+) passed', output)
    failed_match = re.search(r'(\d+) failed', output)
    
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    total = passed + failed
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    
    if failed > 0:
        print()
        print("=" * 40)
        print(f"{Color.RED}❌ FAILED TESTS DETAILS{Color.END}")
        print("=" * 40)
        
        # Extract failed test names
        failed_tests = re.findall(r'FAILED (.*?) -', output)
        for test in failed_tests:
            print(f"  • {test}")
        
        print()
        print("=" * 40)
        print(f"{Color.YELLOW}🔧 REMEDIATION NEEDED{Color.END}")
        print("=" * 40)
        print("Run with -v flag for detailed error messages:")
        print("  pytest -v tests/test_<module>.py::TestClass::test_method")
        print()
        print("Common issues:")
        print("  • Type mismatches (datetime vs str, tuple vs Location)")
        print("  • Missing attributes (commute, cache_dir)")
        print("  • Mock object configuration")
        print()
    
    if test_type == 'coverage':
        print()
        print(f"{Color.BLUE}📊 Coverage report generated in htmlcov/index.html{Color.END}")
    
    if failed == 0:
        print()
        print(f"{Color.GREEN}✅ All tests passed!{Color.END}")
        return 0
    else:
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run Ride Optimizer tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py              # Run all tests
  python scripts/run_tests.py unit         # Run unit tests only
  python scripts/run_tests.py integration  # Run integration tests only
  python scripts/run_tests.py coverage     # Run with coverage report
  python scripts/run_tests.py quick        # Run quick tests (exclude slow)
  python scripts/run_tests.py watch        # Run in watch mode
        """
    )
    
    parser.add_argument(
        'test_type',
        nargs='?',
        default='all',
        choices=['all', 'unit', 'integration', 'coverage', 'quick', 'watch'],
        help='Type of tests to run (default: all)'
    )
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    sys.exit(run_tests(args.test_type))


if __name__ == '__main__':
    main()

