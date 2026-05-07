#!/bin/bash
# Master script to run all Frontend Squad QA test harnesses
# Usage: ./tests/qa/run_all_qa_tests.sh [--verbose]

set -e  # Exit on first failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
VERBOSE=""
if [[ "$1" == "--verbose" ]] || [[ "$1" == "-v" ]]; then
    VERBOSE="--verbose"
fi

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Frontend Squad QA Test Suite - Master Runner${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Test Directory: $SCRIPT_DIR"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_file=$1
    local test_name=$2
    local issue_num=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}------------------------------------------------------------${NC}"
    echo -e "${BLUE}Running: $test_name (Issue #$issue_num)${NC}"
    echo -e "${BLUE}------------------------------------------------------------${NC}"
    
    if python3 "$test_file" $VERBOSE; then
        echo -e "${GREEN}✓ $test_name PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ $test_name FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Run all tests
echo -e "${YELLOW}Starting QA test suite...${NC}"
echo ""

# Test 1: Dashboard (Issue #132)
run_test "$SCRIPT_DIR/test_dashboard_qa.py" "Dashboard" "132" || true
echo ""

# Test 2: Commute Views (Issue #133)
run_test "$SCRIPT_DIR/test_commute_qa.py" "Commute Views" "133" || true
echo ""

# Test 3: Long Ride Planner (Issue #134)
run_test "$SCRIPT_DIR/test_planner_qa.py" "Long Ride Planner" "134" || true
echo ""

# Test 4: Route Library (Issue #135)
run_test "$SCRIPT_DIR/test_route_library_qa.py" "Route Library" "135" || true
echo ""

# Test 5: Responsive Layout (Issue #142)
run_test "$SCRIPT_DIR/test_responsive_qa.py" "Responsive Layout" "142" || true
echo ""

# Print final summary
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Final Test Summary${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Total Test Suites: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All QA test suites passed!${NC}"
    echo -e "${GREEN}Frontend Squad deliverables are ready for merge.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some QA test suites failed.${NC}"
    echo -e "${YELLOW}Please review the failures above and fix issues before merge.${NC}"
    exit 1
fi

# Made with Bob
