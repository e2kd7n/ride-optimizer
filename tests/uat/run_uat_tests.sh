#!/bin/bash
# UAT Test Runner Script
# Runs all User Acceptance Test scenarios with comprehensive reporting

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Ride Optimizer UAT Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Please install: pip install pytest${NC}"
    exit 1
fi

# Parse command line arguments
MODE="${1:-all}"
REPORT_DIR="reports/uat"
mkdir -p "$REPORT_DIR"

# Function to run tests with specific marker
run_tests() {
    local marker=$1
    local description=$2
    
    echo -e "${YELLOW}Running: $description${NC}"
    
    if pytest tests/uat/ -v -m "$marker" \
        --html="$REPORT_DIR/${marker}_report.html" \
        --self-contained-html \
        --tb=short; then
        echo -e "${GREEN}✓ $description passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $description failed${NC}"
        return 1
    fi
}

# Function to run all tests in a file
run_scenario() {
    local file=$1
    local description=$2
    
    echo -e "${YELLOW}Running: $description${NC}"
    
    if pytest "$file" -v \
        --html="$REPORT_DIR/$(basename $file .py)_report.html" \
        --self-contained-html \
        --tb=short; then
        echo -e "${GREEN}✓ $description passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $description failed${NC}"
        return 1
    fi
}

# Track results
PASSED=0
FAILED=0

case "$MODE" in
    all)
        echo -e "${BLUE}Running all UAT scenarios...${NC}"
        echo ""
        
        # Run each scenario
        if run_scenario "tests/uat/test_scenario_1_daily_commuter.py" "Scenario 1: Daily Commuter"; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
        echo ""
        
        if run_scenario "tests/uat/test_scenario_2_weekend_warrior.py" "Scenario 2: Weekend Warrior"; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
        echo ""
        
        if run_scenario "tests/uat/test_scenario_3_data_enthusiast.py" "Scenario 3: Data Enthusiast"; then
            ((PASSED++))
        else
            ((FAILED++))
        fi
        ;;
        
    scenario1)
        echo -e "${BLUE}Running Scenario 1: Daily Commuter${NC}"
        echo ""
        run_scenario "tests/uat/test_scenario_1_daily_commuter.py" "Scenario 1: Daily Commuter"
        ;;
        
    scenario2)
        echo -e "${BLUE}Running Scenario 2: Weekend Warrior${NC}"
        echo ""
        run_scenario "tests/uat/test_scenario_2_weekend_warrior.py" "Scenario 2: Weekend Warrior"
        ;;
        
    scenario3)
        echo -e "${BLUE}Running Scenario 3: Data Enthusiast${NC}"
        echo ""
        run_scenario "tests/uat/test_scenario_3_data_enthusiast.py" "Scenario 3: Data Enthusiast"
        ;;
        
    mobile)
        echo -e "${BLUE}Running mobile-specific tests${NC}"
        echo ""
        run_tests "mobile" "Mobile Tests"
        ;;
        
    tablet)
        echo -e "${BLUE}Running tablet-specific tests${NC}"
        echo ""
        run_tests "tablet" "Tablet Tests"
        ;;
        
    desktop)
        echo -e "${BLUE}Running desktop-specific tests${NC}"
        echo ""
        run_tests "desktop" "Desktop Tests"
        ;;
        
    performance)
        echo -e "${BLUE}Running performance tests${NC}"
        echo ""
        run_tests "performance" "Performance Tests"
        ;;
        
    data)
        echo -e "${BLUE}Running data integrity tests${NC}"
        echo ""
        run_tests "data_integrity or data_accuracy" "Data Integrity Tests"
        ;;
        
    quick)
        echo -e "${BLUE}Running quick UAT smoke tests${NC}"
        echo ""
        # Run only the complete workflow tests
        pytest tests/uat/ -v -k "complete_workflow" \
            --html="$REPORT_DIR/quick_report.html" \
            --self-contained-html \
            --tb=short
        ;;
        
    coverage)
        echo -e "${BLUE}Running UAT tests with coverage${NC}"
        echo ""
        pytest tests/uat/ -v -m uat \
            --cov=app \
            --cov-report=html:htmlcov/uat \
            --cov-report=term \
            --html="$REPORT_DIR/coverage_report.html" \
            --self-contained-html
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/uat/index.html${NC}"
        ;;
        
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Modes:"
        echo "  all         - Run all UAT scenarios (default)"
        echo "  scenario1   - Run Scenario 1: Daily Commuter"
        echo "  scenario2   - Run Scenario 2: Weekend Warrior"
        echo "  scenario3   - Run Scenario 3: Data Enthusiast"
        echo "  mobile      - Run mobile-specific tests"
        echo "  tablet      - Run tablet-specific tests"
        echo "  desktop     - Run desktop-specific tests"
        echo "  performance - Run performance tests"
        echo "  data        - Run data integrity tests"
        echo "  quick       - Run quick smoke tests"
        echo "  coverage    - Run with coverage report"
        echo ""
        exit 1
        ;;
esac

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ "$MODE" = "all" ]; then
    echo -e "Scenarios Passed: ${GREEN}$PASSED${NC}"
    echo -e "Scenarios Failed: ${RED}$FAILED${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All UAT scenarios passed!${NC}"
        EXIT_CODE=0
    else
        echo -e "${RED}✗ Some UAT scenarios failed${NC}"
        EXIT_CODE=1
    fi
else
    echo -e "Mode: $MODE"
    EXIT_CODE=$?
fi

echo ""
echo -e "Reports generated in: ${BLUE}$REPORT_DIR/${NC}"
echo ""

# List generated reports
if [ -d "$REPORT_DIR" ]; then
    echo "Available reports:"
    ls -lh "$REPORT_DIR"/*.html 2>/dev/null | awk '{print "  - " $9}' || echo "  (No reports generated)"
fi

echo ""
echo -e "${BLUE}========================================${NC}"

exit $EXIT_CODE

# Made with Bob
