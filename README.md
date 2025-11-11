# Expect Test Framework for Python

A Python implementation of "expect tests" (snapshot testing) inspired by Jane Street's OCaml testing approach. This library makes test writing interactive and eliminates the tedium of manually specifying expected outputs.

## Features

- **Interactive test development**: Start with blank expectations and let the system fill them in
- **Automatic snapshot management**: Outputs are stored in JSON files, not embedded in code
- **Intelligent conflict resolution**: Multiple strategies for handling changes
- **Editor-agnostic**: No dependency on specific editors or IDEs
- **Rich diff display**: Colored terminal diffs show exactly what changed
- **CI-friendly**: Automatic failure mode for continuous integration
- **Flexible serialization**: Handles complex Python objects, exceptions, and custom types

## Installation

```python
# Simply copy expect_test.py to your project
# No external dependencies required (uses only Python stdlib)
```

## Basic Usage

### 1. Simple Decorator Pattern

```python
from expect_test import expect

def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

@expect("fibonacci_test")
def test_fibonacci():
    return fibonacci(15)

# First run: Creates snapshot with value 610
# Subsequent runs: Compares against stored snapshot
test_fibonacci()
```

### 2. Inline Context Manager

```python
from expect_test import expect_inline

def test_calculation():
    with expect_inline("my_calculation") as e:
        result = sum(range(100))
        e.capture(result)
```

## Conflict Resolution Strategies

When a test output differs from the stored snapshot, the library offers several resolution strategies:

### Interactive Mode (Default)
```python
# User is prompted to accept/reject changes
# Shows colored diff in terminal
```

### Auto-Accept Mode
```python
from expect_test import auto_accept

auto_accept(True)  # Automatically accept all new values
```

### CI Mode
```python
# Set CI=true environment variable
# Tests will fail on any snapshot mismatch
export CI=true
```

### Programmatic Configuration
```python
from expect_test import set_conflict_resolution, ConflictResolution

set_conflict_resolution(ConflictResolution.ACCEPT_NEW)  # Auto-accept
set_conflict_resolution(ConflictResolution.KEEP_OLD)    # Keep existing
set_conflict_resolution(ConflictResolution.FAIL)        # Always fail
set_conflict_resolution(ConflictResolution.INTERACTIVE) # Prompt user
```

## Snapshot Storage

Snapshots are stored in JSON files in a `.expect_snapshots/` directory:

```
project/
├── my_tests.py
└── .expect_snapshots/
    └── my_tests.json
```

Each snapshot contains:
- The serialized test output
- Timestamp of last update
- Source file location and line number
- Hash for change detection

Example snapshot file:
```json
{
  "fibonacci_test": {
    "value": 610,
    "timestamp": "2024-01-15T10:30:00",
    "file_path": "/path/to/test.py",
    "line_number": 42,
    "hash": "a1b2c3d4..."
  }
}
```

## Advanced Features

### Testing Exceptions

```python
@expect("division_error")
def test_error():
    return 1 / 0  # Exception is captured in snapshot

# Snapshot will contain:
# {"exception": "ZeroDivisionError", "message": "division by zero"}
```

### Complex Object Serialization

```python
class CustomObject:
    def __init__(self):
        self.data = [1, 2, 3]
        self.metadata = {"key": "value"}

@expect("custom_object_test")
def test_object():
    return CustomObject()

# Automatically serializes to JSON-compatible format
```

### Table-Style Testing

```python
@expect("comprehensive_test_table")
def test_multiple_cases():
    cases = [1, 5, 10, 15, 20]
    return {
        "results": [
            {"input": n, "fibonacci": fibonacci(n)} 
            for n in cases
        ]
    }
```

## Workflow Benefits

1. **Exploratory Development**: Start with blank expects, see what your code produces
2. **Documentation**: Snapshots serve as examples of expected behavior
3. **Regression Detection**: Any unexpected change triggers a diff
4. **Reduced Typing**: No manual calculation or copying of expected values
5. **Implicit Coverage**: Captures entire state, not just explicit assertions

## Comparison with Traditional Testing

### Traditional (pytest/unittest):
```python
def test_fibonacci():
    assert fibonacci(10) == 55  # Must calculate manually
    assert fibonacci(15) == 610  # Tedious for complex values
```

### Expect Tests:
```python
@expect("fibonacci_test")
def test_fibonacci():
    return {"f(10)": fibonacci(10), "f(15)": fibonacci(15)}
    # Values filled in automatically on first run
```

## Configuration Options

```python
from expect_test import config

# Set snapshot directory
config.snapshot_dir = "my_snapshots"

# Enable/disable diff display
config.show_diffs = True

# CI mode (from environment)
config.ci_mode = True  # Fails on any mismatch
```

## Best Practices

1. **Keep tests focused**: Each expect test should test one concept
2. **Use descriptive names**: Test names become snapshot keys
3. **Serialize thoughtfully**: Structure output to be human-readable
4. **Review diffs carefully**: Don't blindly accept changes
5. **Version control snapshots**: Commit snapshot files to track changes
6. **Use in CI**: Set `CI=true` to catch regressions automatically

## Interactive Prompt Commands

When a conflict is detected in interactive mode:
- `y` - Accept new value
- `n` - Keep old value (test fails)
- `d` - Show diff again
- `q` - Quit test run

## Integration with Test Runners

The library works with standard Python test runners:

```python
# With pytest
def test_with_pytest():
    @expect("pytest_integration")
    def inner_test():
        return {"status": "works"}
    inner_test()

# With unittest
import unittest

class TestExpect(unittest.TestCase):
    def test_example(self):
        @expect("unittest_integration")
        def inner_test():
            return {"framework": "unittest"}
        inner_test()
```

## Philosophy

Following Jane Street's approach, this library embraces the idea that:
- Tests should be easy and pleasant to write
- The computer should do the tedious work of figuring out expected values
- Tests serve triple duty as exploration tools, documentation, and regression guards
- Seeing actual output is often more valuable than writing specific assertions

## License

MIT License - Use freely in your projects

## Contributing

This is a standalone implementation inspired by the Jane Street article. Feel free to extend and adapt for your needs.
