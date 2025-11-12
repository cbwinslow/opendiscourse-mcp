# Testing Guide for OpenDiscourse MCP Server

This document provides comprehensive guidance for testing the OpenDiscourse MCP Server, including testing strategies, setup instructions, and best practices.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Architecture](#test-architecture)
3. [Setup and Installation](#setup-and-installation)
4. [Running Tests](#running-tests)
5. [Writing Tests](#writing-tests)
6. [Test Categories](#test-categories)
7. [Mocking and Fixtures](#mocking-and-fixtures)
8. [Coverage Requirements](#coverage-requirements)
9. [CI/CD Integration](#ci-cd-integration)
10. [Performance Testing](#performance-testing)
11. [Debugging Tests](#debugging-tests)
12. [Best Practices](#best-practices)

## Testing Overview

The OpenDiscourse testing system is designed to ensure:

- **Reliability**: All components work correctly under various conditions
- **Performance**: System performs well under load
- **Security**: No vulnerabilities in the codebase
- **Maintainability**: Code changes don't break existing functionality

### Key Testing Principles

- **Test Pyramid**: Unit tests (bottom) → Integration tests (middle) → E2E tests (top)
- **Fast Feedback**: Unit tests run quickly, integration tests validate interactions
- **Isolation**: Tests don't depend on external systems
- **Realistic Data**: Use representative test data
- **Continuous Integration**: Automated testing on every change

## Test Architecture

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_main.py            # FastAPI application tests
├── test_db.py              # Database utility tests
├── test_ingestion_cli.py   # CLI tool tests
├── test_enhanced_ingestion.py  # Enhanced ingestion system tests
├── test_congress_client.py     # Congress API client tests
├── test_openstates_client.py   # OpenStates API client tests
├── test_govinfo_client.py      # GovInfo API client tests
└── test_xml_ingest.py          # XML ingestion utility tests
```

### Test Configuration

- **pytest.ini**: Main pytest configuration with coverage and marker settings
- **conftest.py**: Shared fixtures for mocking APIs, databases, and test data
- **CI/CD**: GitHub Actions workflow for automated testing

## Setup and Installation

### Prerequisites

```bash
# Python 3.9+
python --version

# PostgreSQL (for integration tests)
# Redis (for enhanced features)

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Test Dependencies

```bash
# Core testing
pytest>=7.0
pytest-cov>=4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0

# Code quality
flake8>=6.0
black>=23.0
isort>=5.12.0
mypy>=1.0

# Security
bandit>=1.7.0
safety>=2.3.0

# Performance
pytest-benchmark>=4.0.0
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server

# Run specific test file
pytest tests/test_main.py

# Run specific test
pytest tests/test_main.py::TestTokenRegistration::test_register_token_success

# Run tests with markers
pytest -m unit
pytest -m integration
pytest -m e2e
pytest -m slow
```

### Test Options

```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show coverage report
pytest --cov=mcp_server --cov-report=html

# Run failed tests only
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Debug mode
pytest --pdb
```

### Coverage Analysis

```bash
# Terminal coverage report
pytest --cov=mcp_server --cov-report=term-missing

# HTML coverage report
pytest --cov=mcp_server --cov-report=html
open htmlcov/index.html

# Coverage for specific module
pytest --cov=mcp_server.clients --cov-report=term-missing
```

## Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestComponentName:
    """Test class for ComponentName."""

    def test_success_case(self):
        """Test successful operation."""
        # Arrange
        fixture_data = {"key": "value"}

        # Act
        result = function_under_test(fixture_data)

        # Assert
        assert result == expected_value

    def test_error_case(self):
        """Test error handling."""
        # Arrange
        invalid_data = {"invalid": "data"}

        # Act & Assert
        with pytest.raises(ValueError):
            function_under_test(invalid_data)

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test asynchronous function."""
        # Arrange
        async_fixture = await create_async_fixture()

        # Act
        result = await async_function_under_test(async_fixture)

        # Assert
        assert result.status == "success"
```

### Test Markers

```python
@pytest.mark.unit
def test_unit_function():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_integration_function():
    """Integration test requiring database."""
    pass

@pytest.mark.e2e
def test_end_to_end():
    """Full end-to-end test."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Slow-running test."""
    pass

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    """Test for future implementation."""
    pass
```

## Test Categories

### Unit Tests

- Test individual functions and methods
- Mock all external dependencies
- Fast execution (< 100ms per test)
- High coverage target (90%+)

```python
@patch('mcp_server.clients.requests.Session')
def test_api_client_method(mock_session):
    """Test API client method with mocked HTTP."""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_session.return_value.get.return_value = mock_response

    client = APIClient()
    result = client.get_data()

    assert result == {"data": "test"}
```

### Integration Tests

- Test complete workflows and component interactions
- Test error handling and edge cases
- Validate data flow between components
- Include security and performance testing

```python
def test_complete_workflow(client):
    """Test end-to-end workflow integration."""
    # Register token
    response = client.post("/mcp/register_token", json={
        "site": "congress",
        "user_id": "test_user",
        "api_key": "test_key"
    })
    assert response.status_code == 200

    # Execute function and verify integration
    # ... complete workflow testing
```

### Component Integration Tests

- Test component interactions
- Use test databases
- Validate data flow between components
- Medium execution time

```python
@pytest.mark.integration
def test_database_ingestion(sqlite_db):
    """Test data ingestion into database."""
    # Setup test data
    test_data = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})

    # Execute ingestion
    ingester = DataIngester(sqlite_db)
    result = ingester.ingest_data(test_data)

    # Verify database state
    cursor = sqlite_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM test_table")
    count = cursor.fetchone()[0]
    assert count == 2
```

### End-to-End Tests

- Test complete user workflows
- Use real services where possible
- Validate system behavior
- Slow execution, run less frequently

```python
@pytest.mark.e2e
def test_full_ingestion_workflow(client, api_keys):
    """Test complete ingestion workflow."""
    # Register API keys
    client.post("/mcp/register_token", json={
        "site": "congress",
        "user_id": "test_user",
        "api_key": api_keys["congress"]
    })

    # Execute ingestion
    response = client.post("/mcp/ingest_data", json={
        "user_id": "test_user",
        "site": "congress",
        "database_url": "postgresql://test:test@localhost/testdb"
    })

    assert response.status_code == 200
    assert "completed" in response.json()["message"]
```

## Mocking and Fixtures

### Shared Fixtures (conftest.py)

```python
@pytest.fixture
def api_keys():
    """Sample API keys for testing."""
    return {
        "congress": "test_congress_key",
        "openstates": "test_openstates_key",
        "govinfo": "test_govinfo_key"
    }

@pytest.fixture
def mock_http_session():
    """Mock HTTP session for API testing."""
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "success"}
    session.get.return_value = response
    return session

@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame."""
    return pd.DataFrame({
        "id": ["doc1", "doc2"],
        "title": ["Doc 1", "Doc 2"],
        "date": ["2025-01-01", "2025-01-02"]
    })
```

### API Mocking

```python
@pytest.fixture
def mock_congress_api():
    """Mock Congress.gov API responses."""
    with patch('mcp_server.clients.congress_client.requests.Session') as mock_session:
        mock_response = Mock()
        mock_response.json.return_value = {
            "bills": [
                {
                    "billType": "hr",
                    "billNumber": "1234",
                    "title": "Test Bill"
                }
            ]
        }
        mock_session.return_value.get.return_value = mock_response
        yield mock_session
```

### Database Mocking

```python
@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection."""
    conn = Mock()
    cursor = Mock()
    cursor.fetchall.return_value = [("data1", "data2")]
    cursor.description = [("col1",), ("col2",)]
    conn.cursor.return_value = cursor
    return conn
```

## Coverage Requirements

### Coverage Targets

- **Overall**: 80% minimum
- **Main application** (`main.py`): 90% minimum
- **Core utilities**: 85% minimum
- **API clients**: 80% minimum
- **New code**: 90% minimum

### Coverage Configuration

```ini
# pytest.ini
[tool:pytest]
cov-report = term-missing, html, xml
cov-fail-under = 80
cov-branch = True
```

### Coverage Badges

```markdown
[![Coverage Status](https://coveralls.io/repos/github/username/opendiscourse/badge.svg)](https://coveralls.io/github/username/opendiscourse)
```

## CI/CD Integration

### GitHub Actions Workflow

The CI/CD pipeline includes:

1. **Unit Tests**: Fast feedback on code changes
2. **Integration Tests**: Validate component interactions
3. **E2E Tests**: Full workflow validation
4. **Security Scanning**: Automated vulnerability checks
5. **Performance Tests**: Benchmarking (daily)
6. **Code Quality**: Linting, formatting, type checking

### Local CI Simulation

```bash
# Run full CI pipeline locally
./scripts/run_ci.sh

# Or run individual stages
pytest --cov=mcp_server --cov-fail-under=80
flake8 mcp_server tests
black --check mcp_server tests
mypy mcp_server
```

## Performance Testing

### Benchmark Tests

```python
@pytest.mark.slow
def test_ingestion_performance(benchmark, sample_dataframe):
    """Benchmark data ingestion performance."""
    ingester = DataIngester()

    def run_ingestion():
        return ingester.process_data(sample_dataframe)

    result = benchmark(run_ingestion)

    # Assert performance requirements
    assert result.stats.mean < 1.0  # Less than 1 second average
```

### Load Testing

```python
@pytest.mark.slow
def test_concurrent_requests(client, api_keys):
    """Test concurrent API requests."""
    import asyncio
    import aiohttp

    async def make_request(session, request_id):
        async with session.post("/mcp/execute", json={
            "user_id": f"user_{request_id}",
            "site": "congress",
            "function": "search_bills"
        }) as response:
            return await response.json()

    async def run_load_test():
        async with aiohttp.ClientSession() as session:
            tasks = [make_request(session, i) for i in range(100)]
            results = await asyncio.gather(*tasks)
            return results

    results = asyncio.run(run_load_test())

    # Verify all requests succeeded
    assert all(r["status"] == "success" for r in results)
```

## Debugging Tests

### Common Debugging Techniques

```bash
# Run with detailed output
pytest -v -s

# Debug specific test
pytest --pdb tests/test_main.py::TestTokenRegistration::test_register_token_success

# Show print statements
pytest -s

# Run tests in specific order
pytest --co -q | head -20

# Profile test performance
pytest --durations=10
```

### Debugging Fixtures

```python
# Add debug prints to fixtures
@pytest.fixture
def debug_api_keys(api_keys):
    print(f"Using API keys: {list(api_keys.keys())}")
    return api_keys

# Use breakpoint in tests
def test_debug_example():
    data = setup_test_data()
    breakpoint()  # Will drop into debugger
    result = process_data(data)
    assert result is not None
```

### Test Isolation Issues

```python
# Ensure test cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Cleanup code here
    clear_test_database()
    reset_mocks()
```

## Best Practices

### Test Organization

1. **One Concept Per Test**: Each test should validate one behavior
2. **Descriptive Names**: Test names should explain what they validate
3. **Arrange-Act-Assert**: Clear test structure
4. **DRY Principle**: Use fixtures and helper functions
5. **Independent Tests**: Tests should not depend on each other

### Code Quality in Tests

```python
# Good: Clear, focused test
def test_user_registration_with_valid_data(client):
    response = client.post("/register", json={"email": "test@example.com"})
    assert response.status_code == 201

# Bad: Multiple concerns, unclear intent
def test_registration():
    # Setup, test, and assertions all mixed together
    client = TestClient(app)
    data = {"email": "test@example.com", "password": "123"}
    resp = client.post("/register", json=data)
    assert resp.status_code == 201
    assert "id" in resp.json()
    # Also testing login in the same test!
    login_resp = client.post("/login", json=data)
    assert login_resp.status_code == 200
```

### Mocking Best Practices

1. **Mock at the Right Level**: Mock external dependencies, not internal logic
2. **Realistic Mock Data**: Use representative data structures
3. **Verify Interactions**: Check that mocked methods were called correctly
4. **Avoid Over-Mocking**: Don't mock everything - test real code where possible

```python
# Good: Mock external API, test real business logic
@patch('requests.get')
def test_api_client_parses_response_correctly(mock_get):
    mock_get.return_value.json.return_value = {"data": "test"}

    client = APIClient()
    result = client.fetch_and_parse_data()

    assert result.processed_data == "TEST"
    mock_get.assert_called_once()

# Bad: Mocking internal methods
@patch('APIClient._parse_response')  # Don't mock private methods
@patch('APIClient._make_request')
def test_api_client(mock_parse, mock_request):
    # This test doesn't validate real behavior
    pass
```

### Performance Considerations

1. **Fast Unit Tests**: Keep unit tests under 100ms
2. **Selective Integration Tests**: Run expensive tests less frequently
3. **Parallel Execution**: Use pytest-xdist for parallel test execution
4. **Resource Cleanup**: Properly clean up test resources

### Security Testing

```python
def test_sql_injection_protection(client):
    """Test protection against SQL injection."""
    malicious_input = "'; DROP TABLE users; --"

    response = client.post("/query", json={
        "table": "safe_table",
        "where_clause": f"id = '{malicious_input}'"
    })

    # Should not execute dangerous SQL
    assert response.status_code == 400
    # Verify table still exists and no data was compromised
```

### Documentation

1. **Docstrings**: Every test should have a clear docstring
2. **Comments**: Explain complex test setup or assertions
3. **Test Data**: Document the purpose of test data fixtures
4. **Edge Cases**: Document why edge cases are important

---

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure 90%+ coverage for new code
3. Add appropriate markers (`unit`, `integration`, `e2e`)
4. Update this documentation if needed
5. Run full test suite before submitting PR

## Troubleshooting

### Common Issues

**Tests failing randomly**: Check for test isolation issues or race conditions

**Slow test suite**: Profile tests with `pytest --durations=10`

**Coverage not updating**: Clear `.coverage` file and pytest cache

**Import errors**: Ensure test dependencies are installed

### Getting Help

- Check existing tests for patterns
- Review pytest documentation
- Ask in development discussions
- Check CI/CD logs for failures

---

This testing guide ensures the OpenDiscourse MCP Server maintains high quality and reliability. Follow these practices to contribute effectively to the project's testing infrastructure.
