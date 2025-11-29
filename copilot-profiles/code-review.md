# Code Review Profile

Instructions for performing comprehensive code reviews.

## Overview

This profile provides guidelines for reviewing code submissions to ensure quality, maintainability, and adherence to best practices.

## Review Checklist

Before approving any code change, ensure the following items are checked:

- [ ] Code follows project coding standards
- [ ] All tests pass and new tests are added for new functionality
- [ ] Documentation is updated for public APIs
- [ ] No security vulnerabilities introduced
- [ ] Performance considerations are addressed
- [ ] Error handling is comprehensive

## Guidelines

### Code Quality

1. Check for clear, descriptive variable and function names
2. Ensure functions are focused and have a single responsibility
3. Look for code duplication that could be refactored

### Security

1. Validate all user inputs
2. Use parameterized queries for database operations
3. Avoid exposing sensitive information in logs

### Performance

1. Check for unnecessary database queries
2. Look for potential memory leaks
3. Consider caching opportunities

## When to Use

Use this profile when:
- Reviewing pull requests
- Performing code audits
- Mentoring junior developers
