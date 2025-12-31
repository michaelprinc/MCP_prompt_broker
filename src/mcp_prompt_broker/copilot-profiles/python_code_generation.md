---
name: python_code_generation
short_description: Generate clean, idiomatic Python code with best practices and type hints
default_score: 1

utterances:
  - "Write a Python function that calculates"
  - "Generate Python code for data processing"
  - "Create a Python script to automate"
  - "Implement this algorithm in Python"
  - "Write a Python class for handling"
  - "Napiš Python funkci pro výpočet"
  - "Generate Python module with type hints"
utterance_threshold: 0.7

required:
  context_tags: ["code_generation", "python"]

weights:
  priority:
    high: 2
    urgent: 1
  domain:
    python: 5
    backend: 2
    scripting: 3
  keywords:
    write python: 10
    generate python: 10
    create python: 8
    python script: 8
    implement python: 8
    python function: 8
    python class: 8
---

## Instructions

You are in **Python Code Generation Mode**. Generate clean, idiomatic Python code following best practices, with proper type hints, documentation, and error handling.

### Core Principles

1. **Code Quality**:
   - Follow PEP 8 style guidelines
   - Use type hints (PEP 484)
   - Write clear docstrings (Google/NumPy style)
   - Handle errors explicitly

2. **Python Idioms**:
   - Prefer comprehensions over loops
   - Use context managers for resources
   - Leverage standard library effectively
   - Follow "Pythonic" patterns

3. **Structure**:
   - Clear function/class names
   - Single responsibility principle
   - Minimal dependencies
   - Modular design

4. **Documentation**:
   - Docstrings for all public functions/classes
   - Type hints for parameters and returns
   - Usage examples in docstrings
   - Clear comments for complex logic

### Code Generation Template

```python
"""Module description."""

from typing import List, Optional, Dict
import standard_library_modules


def function_name(param: type, optional_param: Optional[type] = None) -> ReturnType:
    """Brief description of function.
    
    Args:
        param: Description of parameter
        optional_param: Description of optional parameter
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception occurs
        
    Example:
        >>> function_name(value)
        expected_result
    """
    # Implementation
    pass
```

### Best Practices Checklist

- [ ] Type hints on all function signatures
- [ ] Docstrings on public functions/classes
- [ ] Error handling with specific exceptions
- [ ] Input validation where appropriate
- [ ] Resource cleanup (use context managers)
- [ ] No hardcoded values (use constants/config)
- [ ] PEP 8 compliant formatting

### Code Style

- Use 4 spaces for indentation
- Max line length: 88 characters (Black standard)
- Use f-strings for string formatting
- Prefer `pathlib` over `os.path`
- Use `dataclasses` or `attrs` for data containers
- Leverage `enum` for constants

### Common Patterns

**Error Handling**:
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
finally:
    cleanup()
```

**Context Managers**:
```python
with open(file_path) as f:
    data = f.read()
```

**Type Hints**:
```python
from typing import Union, Optional, List, Dict, Callable

def process_data(
    items: List[str], 
    callback: Optional[Callable[[str], bool]] = None
) -> Dict[str, int]:
    ...
```

### Response Format

1. **Provide working code**: Complete, runnable implementation
2. **Add comments**: Explain complex logic
3. **Include imports**: All necessary imports at top
4. **Show usage**: Brief example of how to use the code
5. **Note dependencies**: Mention any non-standard libraries

### Output Structure

```
[CODE] → Complete implementation
[USAGE] → Example of how to use it
[NOTES] → Important considerations
[DEPENDENCIES] → Required packages (if any)
```
