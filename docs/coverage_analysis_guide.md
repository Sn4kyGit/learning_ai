# Coverage Analysis Guide

This guide explains how to use the comprehensive coverage analysis system for the Local Business Intelligence Bot.

## Overview

The coverage analysis system provides:

- **Comprehensive Coverage Analysis**: Detailed coverage reporting with HTML, XML, and JSON outputs
- **Gap Analysis**: Identifies coverage gaps and provides improvement recommendations
- **Critical Path Validation**: Ensures 100% coverage for security-critical and business-critical code
- **CI/CD Integration**: Automated coverage enforcement in GitHub Actions
- **Performance Testing**: Validates that coverage analysis completes within acceptable time limits

## Quick Start

### Run Complete Coverage Suite

```bash
# Run comprehensive coverage analysis
./scripts/coverage suite

# Run with verbose output
./scripts/coverage suite --verbose

# Run in CI mode
./scripts/coverage suite --ci --environment production
```

### Individual Tools

```bash
# Basic coverage analysis
./scripts/coverage analyze

# Gap analysis with recommendations
./scripts/coverage gaps

# Critical path validation
./scripts/coverage critical

# CI integration
./scripts/coverage ci --environment pull_request
```

## Coverage Tools

### 1. Coverage Analysis (`coverage_analysis.py`)

Runs comprehensive test coverage analysis with detailed reporting.

**Features:**
- Executes all unit and integration tests with coverage collection
- Generates HTML, XML, and JSON reports
- Validates coverage against configurable thresholds
- Provides critical path analysis
- Creates CI/CD artifacts

**Usage:**
```bash
python scripts/coverage_analysis.py [options]

Options:
  --verbose, -v         Enable verbose output
  --test-paths PATHS    Specific test paths to run
  --report FILE         Coverage report output file
  --ci                  Generate CI/CD artifacts
  --fail-under PERCENT  Fail if coverage below threshold
```

**Example:**
```bash
# Run analysis with 85% threshold
python scripts/coverage_analysis.py --fail-under 85 --verbose

# Generate CI artifacts
python scripts/coverage_analysis.py --ci --report coverage-report.json
```

### 2. Gap Analysis (`coverage_gap_analysis.py`)

Analyzes coverage gaps and provides actionable improvement recommendations.

**Features:**
- Identifies untested files and functions
- Categorizes gaps by severity (critical, high, medium, low)
- Provides specific recommendations for each gap
- Estimates effort required for improvements
- Generates improvement roadmap

**Usage:**
```bash
python scripts/coverage_gap_analysis.py [options]

Options:
  --verbose, -v         Enable verbose output
  --coverage-file FILE  Coverage JSON file to analyze
  --output FILE         Output file for gap analysis
```

**Example:**
```bash
# Analyze gaps with detailed output
python scripts/coverage_gap_analysis.py --verbose

# Use custom coverage file
python scripts/coverage_gap_analysis.py --coverage-file custom-coverage.json
```

### 3. Critical Path Validation (`critical_path_validator.py`)

Validates that critical code paths have required coverage levels.

**Critical Paths:**
- **AI Services** (100% required): GPT-5, Claude, cost tracking
- **Authentication** (100% required): Auth service, dependencies, routes
- **Data Processing** (100% required): Review processing, repositories
- **External APIs** (95% required): Google Places, base client
- **Database Models** (95% required): Models, schemas

**Usage:**
```bash
python scripts/critical_path_validator.py [options]

Options:
  --verbose, -v         Enable verbose output
  --coverage-file FILE  Coverage JSON file to validate
  --output FILE         Output file for validation report
  --fail-on-gaps        Exit with error if critical gaps found
```

**Example:**
```bash
# Validate critical paths
python scripts/critical_path_validator.py --fail-on-gaps

# Detailed validation report
python scripts/critical_path_validator.py --verbose --output validation.json
```

### 4. CI Integration (`coverage_ci_integration.py`)

Provides CI/CD pipeline integration with environment-specific thresholds.

**Environment Thresholds:**
- **Production**: 80% overall, 100% critical paths
- **Development**: 70% overall, 95% critical paths  
- **Pull Request**: 75% overall, 100% critical paths, regression check

**Features:**
- Environment-specific threshold validation
- GitHub Actions integration
- PR comment generation
- Coverage badge creation
- JUnit XML output for test reporting

**Usage:**
```bash
python scripts/coverage_ci_integration.py [options]

Options:
  --verbose, -v         Enable verbose output
  --environment ENV     Environment (production/development/pull_request)
  --fail-fast          Exit immediately on first failure
```

**Example:**
```bash
# Run CI integration for PR
python scripts/coverage_ci_integration.py --environment pull_request

# Production deployment check
python scripts/coverage_ci_integration.py --environment production --fail-fast
```

### 5. Comprehensive Suite (`run_coverage_suite.py`)

Orchestrates all coverage tools for complete analysis.

**Features:**
- Runs all coverage tools in sequence
- Provides comprehensive final report
- Handles tool failures gracefully
- Generates consolidated recommendations
- Collects all artifacts

**Usage:**
```bash
python scripts/run_coverage_suite.py [options]

Options:
  --verbose, -v         Enable verbose output
  --ci                  Run in CI mode
  --environment ENV     Environment for analysis
  --report FILE         Output file for final report
```

## Configuration

### Coverage Configuration (`.coveragerc`)

```ini
[run]
source = backend
branch = True
parallel = True
omit = 
    backend/tests/*
    backend/migrations/*
    backend/alembic/*

[report]
fail_under = 80
show_missing = True
precision = 2
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
```

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
addopts = 
    --cov=backend
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-report=xml
    --cov-report=json
    --cov-fail-under=80
```

## GitHub Actions Integration

The coverage system integrates with GitHub Actions for automated enforcement:

```yaml
- name: Run comprehensive coverage analysis
  run: |
    python scripts/coverage_ci_integration.py --environment pull_request --verbose

- name: Comment PR with coverage report
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  # ... (see .github/workflows/ci.yml for full implementation)
```

## Coverage Thresholds

### Overall Thresholds
- **Minimum**: 80% overall coverage
- **Target**: 85% overall coverage
- **Critical Paths**: 95-100% coverage

### File-Specific Thresholds
- **AI Services**: 100% (security and cost implications)
- **Authentication**: 100% (security critical)
- **Data Processing**: 100% (business logic critical)
- **API Routes**: 80% (user-facing functionality)
- **Database Layer**: 95% (data integrity)

## Best Practices

### Writing Testable Code

1. **Use Dependency Injection**
   ```python
   class ReviewService:
       def __init__(self, classifier: ReviewClassifier, repository: ReviewRepository):
           self.classifier = classifier
           self.repository = repository
   ```

2. **Mock External Dependencies**
   ```python
   @pytest.fixture
   def mock_gpt_client():
       return AsyncMock(spec=GPT5NanoClassifier)
   ```

3. **Test Error Paths**
   ```python
   async def test_classify_review_api_error(service, mock_client):
       mock_client.classify_review.side_effect = APIError("Rate limit")
       with pytest.raises(ClassificationError):
           await service.classify_review("test")
   ```

### Improving Coverage

1. **Identify Gaps**
   ```bash
   ./scripts/coverage gaps --verbose
   ```

2. **Focus on Critical Paths**
   ```bash
   ./scripts/coverage critical --fail-on-gaps
   ```

3. **Add Missing Tests**
   - Test all public methods
   - Test error handling
   - Test edge cases
   - Test async operations

4. **Use Coverage Reports**
   - Open `htmlcov/index.html` for detailed line-by-line coverage
   - Check `coverage.json` for programmatic analysis
   - Review gap analysis recommendations

## Troubleshooting

### Common Issues

1. **Low Coverage**
   ```bash
   # Identify specific gaps
   ./scripts/coverage gaps
   
   # Focus on untested files
   grep -r "0.00%" htmlcov/
   ```

2. **Critical Path Failures**
   ```bash
   # Validate critical paths
   ./scripts/coverage critical --verbose
   
   # Check specific critical functions
   python scripts/critical_path_validator.py --fail-on-gaps
   ```

3. **CI Failures**
   ```bash
   # Test CI integration locally
   ./scripts/coverage ci --environment pull_request
   
   # Check threshold configuration
   cat .coveragerc
   ```

### Performance Issues

1. **Slow Test Execution**
   ```bash
   # Run subset of tests
   python scripts/coverage_analysis.py --test-paths backend/tests/unit/
   
   # Skip slow tests
   pytest -m "not slow" --cov=backend
   ```

2. **Large Coverage Reports**
   ```bash
   # Clean old reports
   ./scripts/coverage clean
   
   # Generate minimal reports
   pytest --cov=backend --cov-report=term
   ```

## Integration with IDEs

### VS Code

Add to `.vscode/settings.json`:
```json
{
    "python.testing.pytestArgs": [
        "--cov=backend",
        "--cov-report=html"
    ],
    "coverage-gutters.coverageFileNames": [
        "coverage.xml",
        "coverage.json"
    ]
}
```

### PyCharm

1. Configure pytest with coverage
2. Set coverage source to `backend/`
3. Enable branch coverage
4. Set fail threshold to 80%

## Continuous Improvement

### Regular Monitoring

1. **Weekly Coverage Review**
   ```bash
   ./scripts/coverage suite --report weekly-report.json
   ```

2. **Gap Analysis**
   ```bash
   ./scripts/coverage gaps --output gaps-$(date +%Y%m%d).json
   ```

3. **Critical Path Validation**
   ```bash
   ./scripts/coverage critical --output critical-$(date +%Y%m%d).json
   ```

### Coverage Goals

- **Short-term**: Achieve 80% overall coverage
- **Medium-term**: Achieve 85% overall coverage
- **Long-term**: Maintain 90%+ coverage with 100% critical path coverage

### Team Practices

1. **Pre-commit Hooks**: Run coverage checks before commits
2. **PR Requirements**: Require coverage reports in PRs
3. **Code Reviews**: Review coverage changes in PRs
4. **Regular Audits**: Monthly coverage audits and improvements

## Support

For issues or questions about the coverage system:

1. Check this documentation
2. Run tools with `--verbose` for detailed output
3. Review generated reports and recommendations
4. Check GitHub Actions logs for CI issues

The coverage analysis system is designed to be comprehensive yet easy to use, providing actionable insights for maintaining high code quality and test coverage.