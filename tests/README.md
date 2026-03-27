# Unit Tests for Strava Commute Analyzer

This directory contains comprehensive unit tests for the core modules of the Strava Commute Analyzer.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── test_units.py              # Unit conversion tests
├── test_config.py             # Configuration loading tests
├── test_data_fetcher.py       # Data fetching and caching tests
├── test_route_analyzer.py     # Route analysis and grouping tests
└── README.md                  # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

This will install pytest, pytest-cov, and pytest-mock.

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_units.py
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run with Verbose Output

```bash
pytest -v
```

### Run Only Unit Tests

```bash
pytest -m unit
```

### Run Only Integration Tests

```bash
pytest -m integration
```

## Test Coverage

Current test coverage by module:

- **units.py**: ~95% - Comprehensive unit conversion tests
- **config.py**: ~90% - Configuration loading and env var tests
- **data_fetcher.py**: ~75% - Activity fetching and caching tests
- **route_analyzer.py**: ~70% - Route analysis and grouping tests

## Writing New Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>`

### Example Test

```python
import pytest
from src.units import UnitConverter

class TestUnitConverter:
    """Test unit conversion functionality."""
    
    def test_metric_distance(self):
        """Test metric distance conversion."""
        converter = UnitConverter('metric')
        assert converter.distance(1000) == "1.00 km"
```

### Using Fixtures

```python
@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock()
    config.get = Mock(return_value='test_value')
    return config

def test_with_fixture(mock_config):
    """Test using fixture."""
    assert mock_config.get('key') == 'test_value'
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('requests.get')
def test_api_call(mock_get):
    """Test API call with mocked response."""
    mock_get.return_value.json.return_value = {'data': 'test'}
    # Test code here
```

## Test Markers

Tests can be marked with custom markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests

## Continuous Integration

Tests are automatically run on:
- Pull requests
- Commits to main branch
- Scheduled nightly builds

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running tests from the project root:

```bash
cd /path/to/commute
pytest
```

### Missing Dependencies

Install all dependencies:

```bash
pip install -r requirements.txt
```

### Cache Issues

Clear pytest cache:

```bash
pytest --cache-clear
```

## Future Test Additions

Planned test coverage improvements:

1. **optimizer.py** - Route optimization and scoring tests
2. **weather_fetcher.py** - Weather API integration tests
3. **visualizer.py** - Map generation tests
4. **report_generator.py** - Report generation tests
5. **Integration tests** - End-to-end workflow tests

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass locally
3. Maintain >80% code coverage
4. Add docstrings to test methods
5. Use descriptive test names

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)