# Test Coverage: report_generator.py (47% → 80%)

## Labels
`P1-high`, `testing`, `squad-2`, `test-coverage`

## Description
Improve test coverage for `src/report_generator.py` from 47% to 80% as part of the effort to reach 70% overall test coverage.

## Current Status
- **Current Coverage**: 47% (110/233 lines)
- **Target Coverage**: 80% (186 lines)
- **Lines to Cover**: +76 lines
- **Impact**: +1.1% to overall coverage

## Module Overview
`report_generator.py` handles **HTML report generation**:
- Generates comprehensive ride analysis reports
- Creates weather summaries and forecasts
- Formats route recommendations
- Generates PDF reports (via WeasyPrint)
- Handles template rendering
- Formats data for display (units, dates, etc.)

## Testing Strategy

### Phase 1: Report Data Preparation (Est: 30 lines)
Test data formatting and preparation:

```python
class TestReportDataPreparation:
    - test_format_route_data()
    - test_format_weather_data()
    - test_format_metrics()
    - test_format_dates()
    - test_unit_conversions()
    - test_missing_data_handling()
    - test_data_aggregation()
```

### Phase 2: HTML Generation (Est: 25 lines)
Test HTML report creation:

```python
class TestHTMLGeneration:
    - test_generate_html_report()
    - test_template_rendering()
    - test_route_section_generation()
    - test_weather_section_generation()
    - test_recommendations_section()
    - test_html_escaping()
    - test_responsive_layout()
```

### Phase 3: PDF Generation (Est: 21 lines)
Test PDF export functionality:

```python
class TestPDFGeneration:
    - test_generate_pdf_report()
    - test_pdf_from_html()
    - test_pdf_styling()
    - test_pdf_error_handling()
    - test_weasyprint_integration()
```

## Implementation Checklist

### Setup
- [ ] Review existing report generation code
- [ ] Understand template structure
- [ ] Set up test data for reports
- [ ] Mock WeasyPrint for PDF tests

### Data Formatting Tests
- [ ] Test route data formatting
- [ ] Test weather data formatting
- [ ] Test metric calculations
- [ ] Test date/time formatting
- [ ] Test unit conversions (metric/imperial)
- [ ] Test missing data handling

### HTML Generation Tests
- [ ] Test template rendering
- [ ] Test section generation
- [ ] Test data injection
- [ ] Test HTML structure
- [ ] Test responsive design elements

### PDF Generation Tests
- [ ] Test PDF creation
- [ ] Test PDF styling
- [ ] Test WeasyPrint integration
- [ ] Test error handling
- [ ] Test file output

### Edge Cases
- [ ] Test empty data sets
- [ ] Test missing templates
- [ ] Test invalid data
- [ ] Test large reports
- [ ] Test special characters in data
- [ ] Test PDF generation failures

### Verification
- [ ] Run tests: `pytest tests/test_report_generator.py -v`
- [ ] Check coverage: `pytest --cov=src/report_generator --cov-report=term-missing`
- [ ] Verify target: Coverage ≥ 80%
- [ ] Ensure all tests pass

## Test Data Requirements

### Sample Report Data
```python
# Create test data with:
- Multiple routes with complete data
- Weather forecasts
- Route recommendations
- Metrics and statistics
- Various date ranges
```

### Template Scenarios
```python
# Test with:
- Valid templates
- Missing templates
- Malformed templates
- Custom templates
```

## Success Criteria
- [ ] Coverage increases from 47% to ≥80%
- [ ] All new tests pass
- [ ] No existing tests broken
- [ ] Tests follow established patterns
- [ ] PDF generation tested
- [ ] Template rendering tested

## Dependencies
- Module: `src/report_generator.py`
- Templates: `templates/report_template.html`
- Library: `WeasyPrint` (for PDF generation)
- Related: `src/units.py` (unit conversions)

## Estimated Effort
- **Complexity**: Medium (template rendering, PDF generation)
- **Time**: 1-2 days
- **Lines of Test Code**: ~150-200 lines

## Related Issues
- Part of: Test Coverage Roadmap to 70%
- Related: #XXX (weather_service tests - already complete)
- Blocks: Overall 70% coverage target

## Notes
- Module is already 47% covered - focus on gaps
- PDF generation may require special test setup
- Mock WeasyPrint to avoid file system dependencies
- Test both HTML and PDF output
- Consider visual regression testing (optional)
- Document any template requirements