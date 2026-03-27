#!/bin/bash
# Test runner script for Strava Commute Analyzer

set -e

echo "🧪 Running Strava Commute Analyzer Tests"
echo "========================================"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -r requirements.txt
fi

# Temporary file for test results
TEMP_RESULTS=$(mktemp)

# Run tests based on argument
case "${1:-all}" in
    "all")
        echo "📋 Running all tests..."
        pytest -v > "$TEMP_RESULTS" 2>&1 || true
        ;;
    "unit")
        echo "📋 Running unit tests only..."
        pytest -v -m unit > "$TEMP_RESULTS" 2>&1 || true
        ;;
    "integration")
        echo "📋 Running integration tests only..."
        pytest -v -m integration > "$TEMP_RESULTS" 2>&1 || true
        ;;
    "coverage")
        echo "📋 Running tests with coverage report..."
        pytest --cov=src --cov-report=html --cov-report=term > "$TEMP_RESULTS" 2>&1 || true
        cat "$TEMP_RESULTS"
        echo ""
        echo "📊 Coverage report generated in htmlcov/index.html"
        ;;
    "quick")
        echo "📋 Running quick tests (excluding slow tests)..."
        pytest -v -m "not slow" > "$TEMP_RESULTS" 2>&1 || true
        ;;
    "watch")
        echo "👀 Running tests in watch mode..."
        pytest-watch
        rm -f "$TEMP_RESULTS"
        exit 0
        ;;
    *)
        echo "Usage: ./run_tests.sh [all|unit|integration|coverage|quick|watch]"
        echo ""
        echo "Options:"
        echo "  all         - Run all tests (default)"
        echo "  unit        - Run only unit tests"
        echo "  integration - Run only integration tests"
        echo "  coverage    - Run tests with coverage report"
        echo "  quick       - Run tests excluding slow tests"
        echo "  watch       - Run tests in watch mode"
        rm -f "$TEMP_RESULTS"
        exit 1
        ;;
esac

# Parse results and create summary
echo ""
echo "=========================================="
echo "📊 TEST SUMMARY"
echo "=========================================="

# Extract test counts
PASSED=$(grep -o "[0-9]* passed" "$TEMP_RESULTS" | grep -o "[0-9]*" || echo "0")
FAILED=$(grep -o "[0-9]* failed" "$TEMP_RESULTS" | grep -o "[0-9]*" || echo "0")
TOTAL=$((PASSED + FAILED))

echo "✅ Passed: $PASSED/$TOTAL"
echo "❌ Failed: $FAILED/$TOTAL"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "=========================================="
    echo "❌ FAILED TESTS DETAILS"
    echo "=========================================="
    grep "FAILED" "$TEMP_RESULTS" | sed 's/FAILED /  • /' || echo "  (See full output above)"
    echo ""
    echo "=========================================="
    echo "🔧 REMEDIATION NEEDED"
    echo "=========================================="
    echo "Run with -v flag for detailed error messages:"
    echo "  pytest -v tests/test_<module>.py::TestClass::test_method"
    echo ""
    echo "Common issues:"
    echo "  • Type mismatches (datetime vs str, tuple vs Location)"
    echo "  • Missing attributes (commute, cache_dir)"
    echo "  • Mock object configuration"
    echo ""
fi

# Cleanup
rm -f "$TEMP_RESULTS"

if [ "$FAILED" -gt 0 ]; then
    exit 1
else
    echo ""
    echo "✅ All tests passed!"
    exit 0
fi

# Made with Bob
