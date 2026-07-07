#!/bin/bash
# Test runner script for Strava Commute Analyzer
#
# NOTE: For cross-platform compatibility, use the Python wrapper:
#   python scripts/run_tests.py [all|unit|integration|coverage|quick|watch]
#
# This shell script delegates to the Python wrapper, which is maintained
# as the single source of truth for the test-runner logic.

set -e

if command -v python3 &> /dev/null; then
    python3 scripts/run_tests.py "$@"
    exit $?
fi

echo "Error: python3 not found on PATH." >&2
echo "Install Python 3, then run: python3 scripts/run_tests.py [all|unit|integration|coverage|quick|watch]" >&2
exit 1
