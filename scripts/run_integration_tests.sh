#!/bin/bash
# Run integration tests for Smart Static architecture

set -e

echo "=========================================="
echo "Ride Optimizer - Integration Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install with: pip install pytest pytest-cov"
    exit 1
fi

echo "Running integration tests..."
echo ""

# Run API integration tests
echo -e "${YELLOW}=== API Integration Tests ===${NC}"
pytest tests/test_api_integration.py -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API integration tests passed${NC}"
else
    echo -e "${RED}✗ API integration tests failed${NC}"
    exit 1
fi

echo ""

# Run API unit tests
echo -e "${YELLOW}=== API Unit Tests ===${NC}"
pytest tests/test_api.py -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API unit tests passed${NC}"
else
    echo -e "${RED}✗ API unit tests failed${NC}"
    exit 1
fi

echo ""

# Run JSON storage tests
echo -e "${YELLOW}=== JSON Storage Tests ===${NC}"
pytest tests/test_json_storage.py -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ JSON storage tests passed${NC}"
else
    echo -e "${RED}✗ JSON storage tests failed${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All integration tests passed!${NC}"
echo "=========================================="
echo ""

# Generate coverage report if requested
if [ "$1" == "coverage" ]; then
    echo "Generating coverage report..."
    pytest tests/test_api_integration.py tests/test_api.py tests/test_json_storage.py \
        --cov=api --cov=src.json_storage \
        --cov-report=html --cov-report=term
    
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
fi

exit 0

# Made with Bob
