# Tournament Platform Test Suite

Comprehensive test coverage for the tournament platform, including Gherkin feature files, server-side Python tests, and client-side JavaScript tests.

## Directory Structure

```
tests/
├── features/           # Gherkin/BDD feature files
│   ├── elo_calculator.feature
│   ├── tournament_lifecycle.feature
│   ├── match_engine.feature
│   ├── state_machine.feature
│   ├── api_routes.feature
│   ├── subscription_manager.feature
│   └── name_generator.feature
├── unit/               # Python unit tests
│   ├── test_elo_calculator.py
│   ├── test_name_generator.py
│   ├── test_state_machine.py
│   ├── test_subscription_manager.py
│   └── test_tournament_registry.py
├── integration/        # Python integration tests
│   └── test_api_routes.py
├── client/             # JavaScript client-side tests
│   ├── package.json
│   ├── setup.js
│   ├── columnBracket.test.js
│   ├── hybridView.test.js
│   └── groupStandings.test.js
├── conftest.py         # Pytest fixtures
├── pytest.ini          # Pytest configuration
├── requirements-test.txt
├── run_tests.sh        # Test runner script
└── README.md
```

## Running Tests

### All Tests
```bash
./tests/run_tests.sh
# or
./tests/run_tests.sh all
```

### Python Server-Side Tests
```bash
./tests/run_tests.sh python

# Or directly with pytest
pytest tests/unit tests/integration -v
```

### JavaScript Client-Side Tests
```bash
./tests/run_tests.sh js

# Or directly with npm
cd tests/client && npm test
```

### With Coverage
```bash
# Python
pytest tests/unit tests/integration --cov=orchestrator --cov-report=html

# JavaScript
cd tests/client && npm test -- --coverage
```

## Test Categories

### Feature Files (Gherkin)
BDD-style specifications in `.feature` files:
- **elo_calculator.feature**: ELO rating calculations and probability math
- **tournament_lifecycle.feature**: Tournament state transitions and CRUD
- **match_engine.feature**: Match creation, results, standings
- **state_machine.feature**: State transitions and guards
- **api_routes.feature**: REST API endpoint behavior
- **subscription_manager.feature**: User subscription management
- **name_generator.feature**: Friendly name generation

### Unit Tests (Python)
- **test_elo_calculator.py**: `EloCalculator` class methods
- **test_name_generator.py**: Name generation functions
- **test_state_machine.py**: `TournamentStateMachine` transitions
- **test_subscription_manager.py**: `SubscriptionManager` operations
- **test_tournament_registry.py**: `TournamentRegistry` CRUD

### Integration Tests (Python)
- **test_api_routes.py**: Full API endpoint testing with Flask test client

### Client Tests (JavaScript/Jest)
- **columnBracket.test.js**: Bracket visualization component
- **hybridView.test.js**: Hybrid tournament view component
- **groupStandings.test.js**: Group standings display component

## Fixtures

Common fixtures in `conftest.py`:
- `app`: Flask test application
- `client`: Flask test client
- `db_session`: Database session with cleanup
- `sample_tournament`: Pre-created tournament
- `sample_hybrid_tournament`: Pre-created hybrid tournament
- `sample_teams`: Pre-created team set
- `sample_match`: Pre-created match
- `elo_calculator`: EloCalculator instance
- `mock_pubsub`: Mocked PubSub manager

## Adding New Tests

### Python Tests
1. Create test file in `tests/unit/` or `tests/integration/`
2. Name it `test_<module>.py`
3. Use fixtures from `conftest.py`
4. Run: `pytest tests/unit/test_<module>.py -v`

### JavaScript Tests
1. Create test file in `tests/client/`
2. Name it `<component>.test.js`
3. Use helpers from `setup.js`
4. Run: `cd tests/client && npm test -- <component>.test.js`

### Feature Files
1. Create `.feature` file in `tests/features/`
2. Write Gherkin scenarios
3. Implement step definitions if using pytest-bdd

## Coverage Goals

- Unit tests: 90%+ coverage
- Integration tests: Cover all API endpoints
- Client tests: Cover all JS component methods
