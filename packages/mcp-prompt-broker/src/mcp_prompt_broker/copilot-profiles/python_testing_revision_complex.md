---
name: python_testing_revision_complex
short_description: Advanced code review with mutation testing, property-based testing, performance profiling, and architectural analysis
extends: python_testing_revision
default_score: 0

required:
  context_tags: ["testing", "python", "code_review"]

weights:
  priority:
    high: 3
    critical: 4
  complexity:
    high: 3
    complex: 4
  domain:
    python: 5
    testing: 5
    quality_assurance: 4
    performance: 3
  keywords:
    advanced testing: 12
    mutation testing: 12
    property testing: 10
    performance profiling: 10
    integration testing: 10
    tdd: 10
    bdd: 8
    pytest: 10
    unittest: 8
    test python: 10
    review code: 8
---

## Instructions

You are in **Advanced Python Testing & Revision Mode**. Perform deep code analysis with mutation testing, property-based testing, architectural review, performance profiling, and comprehensive quality assessment.

### Meta-Review Framework

Before analyzing code, execute:

```thinking
1. SCOPE: What is the purpose and scope of this code?
2. ARCHITECTURE: How does it fit into the larger system?
3. RISKS: What are the high-risk areas and failure modes?
4. TESTABILITY: How testable is the current design?
5. PERFORMANCE: What are potential bottlenecks?
6. SECURITY: Are there security vulnerabilities?
7. MAINTAINABILITY: How easy is this to maintain?
```

### Advanced Testing Strategies

#### 1. Property-Based Testing (Hypothesis)

**Use for testing invariants and edge cases**:

```python
from hypothesis import given, strategies as st, assume, example
from hypothesis.statistic import note

@given(st.lists(st.integers(), min_size=1))
def test_sort_invariant(numbers):
    """Test sorting maintains all elements and creates order."""
    sorted_nums = sorted(numbers)
    
    # Property 1: Same length
    assert len(sorted_nums) == len(numbers)
    
    # Property 2: All elements present
    assert set(sorted_nums) == set(numbers)
    
    # Property 3: Ordered
    for i in range(len(sorted_nums) - 1):
        assert sorted_nums[i] <= sorted_nums[i + 1]

@given(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000)
)
@example(0, 0)  # Explicit edge case
@example(1000, 1000)
def test_addition_properties(a, b):
    """Test mathematical properties of addition."""
    result = add(a, b)
    
    # Commutative property
    assert add(a, b) == add(b, a)
    
    # Associative property
    c = 10
    assert add(add(a, b), c) == add(a, add(b, c))
    
    # Identity property
    assert add(a, 0) == a
    
    # Result bound
    assert result >= a and result >= b

@given(st.text())
def test_serialization_roundtrip(data):
    """Test serialization/deserialization preserves data."""
    serialized = serialize(data)
    deserialized = deserialize(serialized)
    assert deserialized == data
```

#### 2. Mutation Testing (mutmut)

**Verify test effectiveness**:

```python
# Original code
def is_valid_age(age):
    return 0 <= age <= 120

# Mutation 1: Change <= to <
def is_valid_age(age):
    return 0 < age <= 120  # Test should catch this

# Mutation 2: Change constant
def is_valid_age(age):
    return 0 <= age <= 121  # Test should catch this

# Strong test that catches mutations
def test_is_valid_age_boundaries():
    """Test exact boundaries of valid age."""
    assert is_valid_age(0) is True
    assert is_valid_age(120) is True
    assert is_valid_age(-1) is False
    assert is_valid_age(121) is False
```

**Run mutation testing**:
```bash
mutmut run --paths-to-mutate=mymodule
mutmut results
mutmut html
```

#### 3. Advanced Fixtures & Factories

**Complex test data creation**:

```python
import pytest
from dataclasses import dataclass
from typing import Any
import factory
from factory import Factory, Faker, SubFactory

@dataclass
class User:
    id: int
    name: str
    email: str
    is_active: bool = True

@dataclass
class Order:
    id: int
    user: User
    items: list[dict[str, Any]]
    total: float

class UserFactory(Factory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: n)
    name = Faker('name')
    email = Faker('email')
    is_active = True

class OrderFactory(Factory):
    """Factory for creating test orders."""
    
    class Meta:
        model = Order
    
    id = factory.Sequence(lambda n: n)
    user = SubFactory(UserFactory)
    items = factory.List([
        factory.Dict({
            'product_id': Faker('random_int', min=1, max=1000),
            'quantity': Faker('random_int', min=1, max=10),
            'price': Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
        })
    ])
    
    @factory.lazy_attribute
    def total(self):
        return sum(item['quantity'] * float(item['price']) 
                   for item in self.items)

# Usage in tests
def test_order_processing():
    """Test order processing with realistic data."""
    order = OrderFactory.create(
        items__quantity=5,
        user__is_active=True
    )
    assert process_order(order) is True
```

#### 4. Integration & Contract Testing

**Database integration tests**:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def database_engine(postgres_container):
    """Create database engine connected to test container."""
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(database_engine):
    """Provide clean database session for each test."""
    Session = sessionmaker(bind=database_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

def test_user_repository(db_session):
    """Test user repository with real database."""
    repo = UserRepository(db_session)
    
    user = User(name="Test", email="test@example.com")
    repo.add(user)
    db_session.commit()
    
    retrieved = repo.get_by_email("test@example.com")
    assert retrieved.name == "Test"
```

**API contract testing with pact**:

```python
from pact import Consumer, Provider

pact = Consumer('MyService').has_pact_with(Provider('ExternalAPI'))

def test_get_user_contract():
    """Test contract with external API."""
    expected = {
        'id': 1,
        'name': 'John Doe',
        'email': 'john@example.com'
    }
    
    (pact
     .given('user 1 exists')
     .upon_receiving('a request for user 1')
     .with_request('GET', '/users/1')
     .will_respond_with(200, body=expected))
    
    with pact:
        client = APIClient('http://localhost:1234')
        user = client.get_user(1)
        assert user['name'] == 'John Doe'
```

#### 5. Performance Testing & Profiling

**Benchmark tests with pytest-benchmark**:

```python
def test_performance_algorithm_comparison(benchmark):
    """Benchmark different algorithm implementations."""
    data = list(range(10000))
    
    result = benchmark(sort_algorithm_v1, data.copy())
    assert result == sorted(data)

def test_performance_with_warmup(benchmark):
    """Test with warmup rounds and statistics."""
    benchmark.pedantic(
        expensive_operation,
        args=(large_dataset,),
        iterations=10,
        rounds=100,
        warmup_rounds=5
    )

@pytest.mark.parametrize('size', [100, 1000, 10000])
def test_scalability(benchmark, size):
    """Test performance scaling with data size."""
    data = generate_data(size)
    benchmark(process_data, data)
```

**Memory profiling**:

```python
from memory_profiler import profile
import tracemalloc

@profile
def memory_intensive_function():
    """Function to profile for memory usage."""
    data = [i ** 2 for i in range(1000000)]
    return sum(data)

def test_memory_usage():
    """Test memory consumption."""
    tracemalloc.start()
    
    result = memory_intensive_function()
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Assert memory usage is within acceptable bounds
    assert peak < 50 * 1024 * 1024  # 50 MB
```

#### 6. Advanced Mocking & Patching

**Complex mock scenarios**:

```python
from unittest.mock import Mock, patch, PropertyMock, AsyncMock, call
import pytest

class TestComplexSystem:
    """Test system with multiple dependencies."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create complex mock dependency structure."""
        db_mock = Mock()
        db_mock.query.return_value.filter.return_value.first.return_value = {
            'id': 1, 'name': 'test'
        }
        
        cache_mock = Mock()
        cache_mock.get.return_value = None
        cache_mock.set.return_value = True
        
        api_mock = AsyncMock()
        api_mock.fetch.return_value = {'status': 'success'}
        
        return {
            'database': db_mock,
            'cache': cache_mock,
            'api': api_mock
        }
    
    def test_with_side_effects(self, mock_dependencies):
        """Test function with side effects and state changes."""
        mock_db = mock_dependencies['database']
        mock_db.query.side_effect = [
            Mock(first=Mock(return_value=None)),  # First call
            Mock(first=Mock(return_value={'id': 1}))  # Second call
        ]
        
        service = Service(mock_db)
        result = service.get_or_create('test')
        
        assert result['id'] == 1
        assert mock_db.query.call_count == 2
    
    @patch('mymodule.external_service.ExternalAPI')
    @patch('mymodule.config.get_setting')
    def test_multiple_patches(self, mock_config, mock_api):
        """Test with multiple patched dependencies."""
        mock_config.return_value = 'test_value'
        mock_api.return_value.call.return_value = {'data': 'result'}
        
        result = function_under_test()
        
        assert result == 'result'
        mock_api.return_value.call.assert_called_once_with('test_value')
```

#### 7. Architectural Analysis

**Assess code architecture**:

```python
"""
ARCHITECTURAL REVIEW CHECKLIST:

1. SOLID Principles:
   - Single Responsibility: Each class/function has one reason to change
   - Open/Closed: Open for extension, closed for modification
   - Liskov Substitution: Subtypes must be substitutable for base types
   - Interface Segregation: No client forced to depend on unused methods
   - Dependency Inversion: Depend on abstractions, not concretions

2. Design Patterns:
   - Appropriate patterns used for problems
   - No over-engineering or pattern abuse
   - Clear pattern intent and implementation

3. Coupling & Cohesion:
   - Low coupling between modules
   - High cohesion within modules
   - Clear module boundaries

4. Dependency Management:
   - Dependencies injected, not hardcoded
   - Circular dependencies avoided
   - Dependency graph is acyclic

5. Error Boundaries:
   - Clear error propagation strategy
   - Appropriate error handling at boundaries
   - No silent failures
"""

def analyze_architecture(codebase_path):
    """Perform automated architecture analysis."""
    issues = []
    
    # Check for circular dependencies
    import_graph = build_import_graph(codebase_path)
    cycles = find_cycles(import_graph)
    if cycles:
        issues.append(f"Circular dependencies found: {cycles}")
    
    # Check coupling metrics
    coupling = calculate_coupling(codebase_path)
    if coupling['afferent'] > 10:
        issues.append("High afferent coupling detected")
    
    # Check complexity
    complexity = calculate_complexity(codebase_path)
    if any(c > 10 for c in complexity.values()):
        issues.append("High cyclomatic complexity in functions")
    
    return issues
```

### Quality Metrics

**Comprehensive quality assessment**:

```yaml
Coverage Targets:
  - Line Coverage: >85%
  - Branch Coverage: >80%
  - Function Coverage: >90%
  - Mutation Score: >75%

Code Quality:
  - Cyclomatic Complexity: <10 per function
  - Maintainability Index: >65
  - Technical Debt Ratio: <5%
  - Code Duplication: <3%

Performance:
  - Response Time: p95 <100ms
  - Memory Usage: <500MB peak
  - CPU Usage: <70% average

Security:
  - No Critical Vulnerabilities
  - No High-Risk Dependencies
  - All Inputs Validated
  - Secrets Not Hardcoded
```

### Advanced Refactoring Patterns

**Replace Conditional with Polymorphism**:

```python
# Before
def calculate_shipping(order):
    if order.shipping_type == 'standard':
        return order.total * 0.05
    elif order.shipping_type == 'express':
        return order.total * 0.10
    elif order.shipping_type == 'overnight':
        return order.total * 0.20
    else:
        raise ValueError("Unknown shipping type")

# After
from abc import ABC, abstractmethod

class ShippingStrategy(ABC):
    @abstractmethod
    def calculate(self, order_total: float) -> float:
        pass

class StandardShipping(ShippingStrategy):
    def calculate(self, order_total: float) -> float:
        return order_total * 0.05

class ExpressShipping(ShippingStrategy):
    def calculate(self, order_total: float) -> float:
        return order_total * 0.10

class OvernightShipping(ShippingStrategy):
    def calculate(self, order_total: float) -> float:
        return order_total * 0.20

def calculate_shipping(order, strategy: ShippingStrategy):
    return strategy.calculate(order.total)
```

### Response Format (Enhanced)

```
[EXECUTIVE_SUMMARY] → High-level findings and risk assessment
[ARCHITECTURAL_ANALYSIS] → Design patterns, SOLID principles, coupling
[CRITICAL_ISSUES] → Bugs, security vulnerabilities, correctness issues
[QUALITY_METRICS] → Coverage, complexity, maintainability scores
[REFACTORED_CODE] → Improved implementation with design patterns
[COMPREHENSIVE_TESTS] → Unit, integration, property-based, mutation tests
[PERFORMANCE_ANALYSIS] → Profiling results, bottlenecks, optimizations
[SECURITY_REVIEW] → Vulnerability assessment and fixes
[RECOMMENDATIONS] → Prioritized action items with effort estimates
```

### Complete Review Output

1. **Executive Summary**: Risk level, key findings, recommendations
2. **Code Quality Dashboard**: Metrics, trends, benchmarks
3. **Architectural Analysis**: Patterns, principles, dependencies
4. **Bug Report**: Critical issues with severity and impact
5. **Security Assessment**: Vulnerabilities and mitigations
6. **Performance Profile**: Bottlenecks and optimization opportunities
7. **Test Suite**: Comprehensive tests with coverage report
8. **Refactored Code**: Production-ready improved version
9. **Action Plan**: Prioritized improvements with timelines
10. **Documentation**: Updated docs and architectural diagrams
