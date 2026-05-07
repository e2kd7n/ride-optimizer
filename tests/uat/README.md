# User Acceptance Test (UAT) Suite

## Overview
Comprehensive automated UAT scenarios for the Ride Optimizer web platform. These tests simulate real user workflows from end-to-end, validating functionality, performance, and user experience.

## Test Scenarios

### Scenario 1: Morning Commute Planning - "The Daily Commuter"
**File**: `test_scenario_1_daily_commuter.py`  
**User Persona**: Sarah - Daily bike commuter checking weather and route recommendations  
**Duration**: ~30 seconds  
**Tests**: 10 test methods

**Workflow**:
1. Authentication & dashboard access
2. View weather summary
3. Get route recommendation
4. View route details
5. Check alternative routes

**Success Criteria**:
- Complete workflow in < 30 seconds
- All API calls return valid data
- Mobile layout works on 320px viewport
- Weather data current (< 1 hour old)
- No JavaScript errors

### Scenario 2: Weekend Long Ride Planning - "The Weekend Warrior"
**File**: `test_scenario_2_weekend_warrior.py`  
**User Persona**: Mike - Recreational cyclist planning 50-mile weekend ride  
**Duration**: ~2 minutes  
**Tests**: 12 test methods

**Workflow**:
1. Access route planner
2. View 7-day weather forecast
3. Filter routes by distance (45-55 miles)
4. View route library with map
5. Analyze long ride conditions

**Success Criteria**:
- Complete workflow in < 2 minutes
- Weather forecast accurate and up-to-date
- Route filtering works correctly
- Map visualization loads and is interactive
- Long ride analysis provides actionable insights

### Scenario 3: Route Library Management - "The Data Enthusiast"
**File**: `test_scenario_3_data_enthusiast.py`  
**User Persona**: Alex - Power user analyzing performance trends  
**Duration**: ~3 minutes  
**Tests**: 15 test methods

**Workflow**:
1. Access route library dashboard
2. Search routes by name
3. View route performance history
4. Compare similar routes
5. Export route data
6. View analytics dashboard

**Success Criteria**:
- Complete workflow in < 3 minutes
- Search returns accurate results instantly
- Route history loads all activities
- Route comparison provides meaningful insights
- Export generates valid JSON file
- Analytics dashboard shows accurate statistics

## Running Tests

### Run All UAT Scenarios
```bash
pytest tests/uat/ -v -m uat
```

### Run Specific Scenario
```bash
# Scenario 1: Daily Commuter
pytest tests/uat/test_scenario_1_daily_commuter.py -v

# Scenario 2: Weekend Warrior
pytest tests/uat/test_scenario_2_weekend_warrior.py -v

# Scenario 3: Data Enthusiast
pytest tests/uat/test_scenario_3_data_enthusiast.py -v
```

### Run by Test Marker
```bash
# Run all scenario 1 tests
pytest tests/uat/ -v -m scenario1

# Run all scenario 2 tests
pytest tests/uat/ -v -m scenario2

# Run all scenario 3 tests
pytest tests/uat/ -v -m scenario3

# Run mobile-specific tests
pytest tests/uat/ -v -m mobile

# Run tablet-specific tests
pytest tests/uat/ -v -m tablet

# Run desktop-specific tests
pytest tests/uat/ -v -m desktop

# Run performance tests
pytest tests/uat/ -v -m performance

# Run data integrity tests
pytest tests/uat/ -v -m data_integrity
```

### Generate HTML Report
```bash
pytest tests/uat/ -v -m uat --html=reports/uat_report.html --self-contained-html
```

### Run with Coverage
```bash
pytest tests/uat/ -v -m uat --cov=app --cov-report=html
```

### Quick Test Runner Script
```bash
./tests/uat/run_uat_tests.sh
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.uat` | All UAT tests |
| `@pytest.mark.scenario1` | Daily commuter workflow |
| `@pytest.mark.scenario2` | Weekend warrior workflow |
| `@pytest.mark.scenario3` | Data enthusiast workflow |
| `@pytest.mark.mobile` | Mobile-specific tests (320px) |
| `@pytest.mark.tablet` | Tablet-specific tests (768px) |
| `@pytest.mark.desktop` | Desktop-specific tests (1920px) |
| `@pytest.mark.performance` | Performance benchmarks |
| `@pytest.mark.data_integrity` | Data accuracy tests |
| `@pytest.mark.data_accuracy` | Data validation tests |
| `@pytest.mark.export` | Export functionality tests |

## Performance Benchmarks

### Response Time Targets
- Dashboard load: < 2 seconds
- API calls: < 3 seconds
- Route analysis: < 5 seconds
- Search results: < 1 second

### Mobile Performance
- First Contentful Paint: < 1.5 seconds
- Time to Interactive: < 3 seconds
- Lighthouse Score: > 90

### Data Accuracy
- Weather data: < 1 hour old
- Route statistics: Real-time
- Activity history: Complete and accurate

## Test Data

### Mock Data Fixtures
All scenarios use mock data fixtures to ensure:
- Consistent test results
- Fast test execution
- No external API dependencies
- Predictable test outcomes

### Test Data Location
- Mock weather data: Defined in test fixtures
- Mock route data: Defined in test fixtures
- Mock activity data: Defined in test fixtures

## CI/CD Integration

### GitHub Actions Workflow
```yaml
name: UAT Tests
on: [pull_request, push]
jobs:
  uat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-html pytest-cov
      - name: Run UAT Tests
        run: pytest tests/uat/ -v -m uat --html=uat_report.html
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: uat-report
          path: uat_report.html
```

## Success Metrics

### Scenario 1 (Daily Commuter)
- ✅ 95% of users complete workflow in < 30 seconds
- ✅ 0 JavaScript errors
- ✅ 100% mobile compatibility

### Scenario 2 (Weekend Warrior)
- ✅ 90% of users find suitable route in < 2 minutes
- ✅ Weather forecast accuracy > 85%
- ✅ Route recommendations relevant

### Scenario 3 (Data Enthusiast)
- ✅ All data operations complete successfully
- ✅ Export files valid and complete
- ✅ Analytics accurate within 1%

## Troubleshooting

### Common Issues

#### Tests Failing Due to Missing Mocks
**Problem**: Tests fail with "AttributeError: Mock object has no attribute..."  
**Solution**: Ensure all service methods are properly mocked in test fixtures

#### Performance Tests Timing Out
**Problem**: Performance tests fail due to slow response times  
**Solution**: Check if mocks are properly configured to return immediately

#### Import Errors
**Problem**: "ModuleNotFoundError: No module named 'app'"  
**Solution**: Ensure PYTHONPATH includes project root: `export PYTHONPATH=$PYTHONPATH:$(pwd)`

### Debug Mode
Run tests with verbose output and no capture:
```bash
pytest tests/uat/ -v -s -m uat
```

### Run Single Test Method
```bash
pytest tests/uat/test_scenario_1_daily_commuter.py::TestDailyCommuterScenario::test_complete_morning_commute_workflow -v
```

## Maintenance

### Update Frequency
- Review scenarios: Quarterly
- Update test data: Monthly
- Verify API contracts: Weekly

### Adding New Scenarios
1. Create new test file: `test_scenario_N_persona_name.py`
2. Define user persona and story
3. Create workflow steps as test methods
4. Add complete workflow test
5. Add performance and data integrity tests
6. Update this README

### Updating Existing Scenarios
1. Review user feedback and analytics
2. Identify workflow changes
3. Update test methods
4. Update mock data if needed
5. Verify all tests pass
6. Update documentation

## Related Documentation
- [Main Test Suite](../README.md)
- [Integration Tests](../test_integration.py)
- [QA Test Harnesses](../qa/README.md)
- [User Acceptance Test Scenarios](USER_ACCEPTANCE_TEST_SCENARIOS.md)

## Contact
For questions or issues with UAT tests, contact the QA Squad Lead.