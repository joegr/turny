#!/bin/bash
# Test runner script for tournament platform

set -e

echo "=========================================="
echo "Tournament Platform Test Suite"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Navigate to project root
cd "$(dirname "$0")/.."

# Function to run Python tests
run_python_tests() {
    echo -e "\n${YELLOW}Running Python Server-Side Tests...${NC}\n"
    
    # Install test dependencies if needed
    if [ ! -f ".venv/bin/pytest" ] && [ ! -f "venv/bin/pytest" ]; then
        echo "Installing test dependencies..."
        pip install -r tests/requirements-test.txt
    fi
    
    # Run pytest with coverage
    python -m pytest tests/unit tests/integration \
        -v \
        --tb=short \
        --cov=orchestrator \
        --cov=shared \
        --cov-report=term-missing \
        --cov-report=html:tests/coverage/python \
        "$@"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ Python tests passed!${NC}"
    else
        echo -e "\n${RED}✗ Python tests failed!${NC}"
        exit 1
    fi
}

# Function to run JavaScript tests
run_js_tests() {
    echo -e "\n${YELLOW}Running JavaScript Client-Side Tests...${NC}\n"
    
    cd tests/client
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing JavaScript test dependencies..."
        npm install
    fi
    
    # Run Jest
    npm test -- --coverage --coverageDirectory=../coverage/javascript "$@"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ JavaScript tests passed!${NC}"
    else
        echo -e "\n${RED}✗ JavaScript tests failed!${NC}"
        exit 1
    fi
    
    cd ../..
}

# Function to run BDD tests
run_bdd_tests() {
    echo -e "\n${YELLOW}Running BDD Feature Tests...${NC}\n"
    
    python -m pytest tests/features \
        --gherkin-terminal-reporter \
        -v \
        "$@"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ BDD tests passed!${NC}"
    else
        echo -e "\n${RED}✗ BDD tests failed!${NC}"
        exit 1
    fi
}

# Parse arguments
case "${1:-all}" in
    python|py)
        run_python_tests "${@:2}"
        ;;
    js|javascript|client)
        run_js_tests "${@:2}"
        ;;
    bdd|features)
        run_bdd_tests "${@:2}"
        ;;
    all)
        run_python_tests
        run_js_tests
        echo -e "\n${GREEN}=========================================="
        echo "All tests passed!"
        echo -e "==========================================${NC}"
        ;;
    *)
        echo "Usage: $0 [python|js|bdd|all]"
        echo ""
        echo "Commands:"
        echo "  python, py       Run Python server-side tests"
        echo "  js, javascript   Run JavaScript client-side tests"
        echo "  bdd, features    Run BDD/Gherkin feature tests"
        echo "  all              Run all tests (default)"
        exit 1
        ;;
esac
