# Testing Best Practices

Comprehensive guide for writing effective tests.

## Overview

This profile outlines best practices for writing unit tests, integration tests, and end-to-end tests.

## Testing Checklist

- [ ] Unit tests cover all public methods
- [ ] Edge cases are tested
- [ ] Tests are isolated and don't depend on external state
- [ ] Mock dependencies appropriately
- [ ] Test names clearly describe what is being tested
- [ ] Tests run quickly (under 100ms each)
- [x] CI/CD pipeline includes test execution

## Test Structure

### Unit Tests

Focus on testing individual units of code in isolation:

```typescript
describe('Calculator', () => {
  it('should add two numbers correctly', () => {
    expect(add(2, 3)).toBe(5);
  });
});
```

### Integration Tests

Test how multiple components work together:

- Test API endpoints
- Test database operations
- Test external service integrations

### End-to-End Tests

Test complete user workflows:

- Login flows
- Purchase processes
- Form submissions

## Coverage Goals

- Aim for 80% or higher code coverage
- Focus on critical business logic first
- Don't sacrifice test quality for coverage numbers
