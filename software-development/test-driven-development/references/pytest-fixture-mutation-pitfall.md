## Pytest Fixture Mutation Pitfall (2026-06-12)

Tests that mutate their fixture data (dicts from module-level constants) without `copy.deepcopy()` corrupt the shared data for all subsequent tests.

### Symptoms
- Tests pass in isolation (`pytest tests/test_foo.py::test_bar -v`)
- Tests FAIL in full suite (`pytest tests/ -v`)
- Error messages point to unrelated fields or validators
- The failing test works fine when run alone

### Root Cause
Pytest function-scoped fixtures create fresh Python objects each time, BUT if the fixture returns a reference to a module-level dict (e.g., `MOCK_DATA[0]`), mutations by one test persist to the next test's fixture call.

```python
# Module level
MOCK_DATA = [{"id": 1, "name": "test"}]

# Fixture — returns a REFERENCE, not a copy
@pytest.fixture
def data():
    return MOCK_DATA[0]

# Test A mutates it
def test_a(data):
    data["extra"] = "contaminated"  # MOCK_DATA[0] is now contaminated!

# Test B gets the contaminated data
def test_b(data):
    assert "extra" not in data  # FAILS — data has "extra" from test_a
```

### Fix
Every test that modifies input data MUST deepcopy first:

```python
import copy

def test_a(data):
    d = copy.deepcopy(data)
    d["extra"] = "contaminated"
    validate(d)  # uses the copy, not the original

def test_b(data):
    validate(data)  # original is clean
```

### Prevention
- Add `import copy` at the top of test files that modify fixtures
- Use `copy.deepcopy()` in EVERY test that mutates input, not just some
- The `test_forbid_extra_fields` pattern (add unknown key, assert rejection) is the most common offender
- Invariant tests (modify one field to violate a constraint) are equally dangerous

### Real example (stock-predictor, 2026-06-12)
Four invariant tests mutated their fixture dicts without deepcopy. The bilateral contract tests (camelcase, round-trip, forbid) ran first and passed, but the invariant tests contaminated the mock data. The subsequent `test_contract_schemas` tests then failed with confusing "self-loop" errors on data that should have been valid. Cost: ~15 minutes of debugging.
