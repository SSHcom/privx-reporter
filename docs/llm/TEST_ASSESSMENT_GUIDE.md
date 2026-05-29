# Test Assessment Guide

A methodology for evaluating test quality, identifying over-testing and under-testing, and maintaining meaningful coverage without unnecessary permutations.

## Guiding Principle

**Most important things should always be tested. Extremely unlikely cases can be skipped.**

Good test coverage means:
- Core functionality is verified
- Error paths that users will encounter are tested
- Edge cases that could cause data corruption or security issues are covered
- Trivial variations of the same logic are not tested separately

## Assessment Process

### Step 1: Map Source to Tests

For each module in the target directory:

1. List all public functions/classes
2. Identify which have corresponding tests
3. Note functions with no tests (potential gaps)
4. Note functions with many tests (potential over-testing)

### Step 2: Evaluate Each Test File

For each test file, ask:

| Question | If Yes |
|----------|--------|
| Does this test verify behavior, not implementation? | Good |
| Could this test catch a real bug? | Keep it |
| Is this testing Python/library behavior rather than our code? | Remove candidate |
| Is this a slight variation of another test? | Consolidate candidate |
| Does this cover an extremely unlikely scenario? | Remove candidate |

### Step 3: Identify Gaps

Functions that need tests but often lack them:

- **Validation functions** - especially those that raise user-facing errors
- **String/data transformation** - functions that format output users see
- **Error handling paths** - what happens when external calls fail
- **Boundary conditions** - empty inputs, None values, maximum sizes

Functions that typically don't need dedicated tests:

- **Simple wrappers** - functions that only call another tested function
- **Pagination loops** - if the underlying fetch is tested, the loop rarely needs separate tests
- **Thin API wrappers** - if they follow an identical pattern to tested wrappers

## Patterns to Remove (Over-testing)

### 1. Testing Language Features

```python
# BAD: Tests Python's inheritance, not our code
def test_config_error_can_be_caught_as_report_error():
    with pytest.raises(ReportError):
        raise ConfigError("message")
```

If you're testing that `isinstance()` works or that subclasses can be caught as parent types, you're testing Python, not your application.

### 2. Exhaustive Input Variations

```python
# EXCESSIVE: 6 tests for microsecond parsing
test_parse_with_6_digit_microseconds()
test_parse_with_5_digit_microseconds()
test_parse_with_4_digit_microseconds()
test_parse_with_3_digit_microseconds()
test_parse_with_2_digit_microseconds()
test_parse_with_1_digit_microseconds()
```

If the same code path handles all variations, one or two representative tests suffice. Test the boundaries (none, some, maximum) not every permutation.

### 3. Extremely Unlikely Error Scenarios

```python
# UNLIKELY: Multiple HTTP status codes in a single error message
def test_error_with_multiple_status_codes_in_message():
    exception = APIException("Error 501 then 502")
```

Unless there's evidence this happens in production, skip edge cases that require contrived inputs.

### 4. Duplicate Assertions Across Tests

If multiple tests verify the same behavior with trivially different inputs, consolidate using `@pytest.mark.parametrize`:

```python
# BEFORE: 3 separate tests
def test_sanitize_uppercase(): ...
def test_sanitize_mixed_case(): ...
def test_sanitize_lowercase(): ...

# AFTER: 1 parametrized test
@pytest.mark.parametrize("input,expected", [
    ("UPPER", "upper"),
    ("MiXeD", "mixed"),
    ("lower", "lower"),
])
def test_sanitize_case_handling(input, expected): ...
```

## Patterns to Add (Under-testing)

### 1. User-Facing Validation

If a function produces error messages shown to users, test it directly:

```python
# These should have direct tests, not just be mocked elsewhere
def validate_date(date_str, param_name): ...
def validate_email(email): ...
```

### 2. Format Transformations

Functions that convert internal data to user-visible formats:

```python
# Should be tested: transforms CLI flags to UI-friendly text
def to_ui_message(message): ...
```

### 3. Happy Path + Primary Error Path

At minimum, each public function needs:
- One test for successful execution
- One test for the most common error case

### 4. Integration Points

Where your code interacts with external systems, test:
- Successful response handling
- Connection/timeout errors
- Invalid response formats

## Assessment Checklist

When reviewing a test directory, answer these questions:

```
[ ] Are all public functions in source files represented in test files?
[ ] Do tests focus on behavior rather than implementation details?
[ ] Are there obvious consolidation opportunities (many similar tests)?
[ ] Are there tests for Python/library features rather than app logic?
[ ] Are user-facing validation functions directly tested?
[ ] Are error messages and user output formats tested?
[ ] Is there at least one success + one failure test per public function?
```

## Output Format

After assessment, produce:

1. **Tests to Remove** - list with rationale (language feature, unlikely edge case, etc.)
2. **Tests to Add** - list with specific test scenarios
3. **Tests to Consolidate** - groups of tests that could become parametrized
4. **Functions Okay to Skip** - simple wrappers or patterns already covered

## Example Assessment Summary

```
## Module: lib/utils/date.py

### Coverage Status
- parse_iso_timestamp: 12 tests (over-tested)
- format_iso_timestamp: 3 tests (adequate)
- validate_date: 0 direct tests (under-tested)
- get_date_range: 0 tests (okay to skip - trivial)

### Recommendations
Remove: 4 microsecond variation tests (test same code path)
Add: 4 tests for validate_date (user-facing validation)
Skip: get_date_range (3-line function, trivial logic)

Net change: -4 + 4 = 0 tests, better coverage of important code
```

## Applying to New Directories

To assess `reports/` or `ui/`:

1. Run `find <dir> -name "*.py" | head -20` to understand structure
2. For each source file, find corresponding test file
3. Compare public functions to test functions
4. Apply the checklist above
5. Produce summary with remove/add/consolidate recommendations
