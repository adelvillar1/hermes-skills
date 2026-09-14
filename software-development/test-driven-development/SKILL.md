---
name: test-driven-development
description: 'TDD: enforce RED-GREEN-REFACTOR, tests before code.'
platforms:
- linux
- macos
- windows
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask the user first):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor Cycle

### RED — Write Failing Test

Write one minimal test showing what should happen.

**Good test:**
```python
def test_retries_failed_operations_3_times():
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception('fail')
        return 'success'

    result = retry_operation(operation)

    assert result == 'success'
    assert attempts == 3
```
Clear name, tests real behavior, one thing.

**Bad test:**
```python
def test_retry_works():
    mock = MagicMock()
    mock.side_effect = [Exception(), Exception(), 'success']
    result = retry_operation(mock)
    assert result == 'success'  # What about retry count? Timing?
```
Vague name, tests mock not real code.

**Requirements:**
- One behavior per test
- Clear descriptive name ("and" in name? Split it)
- Real code, not mocks (unless truly unavoidable)
- Name describes behavior, not implementation

### Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
# Use terminal tool to run the specific test
pytest tests/test_feature.py::test_specific_behavior -v
```

Confirm:
- Test fails (not errors from typos)
- Failure message is expected
- Fails because the feature is missing

**Test passes immediately?** You're testing existing behavior. Fix the test.

**Test errors?** Fix the error, re-run until it fails correctly.

### GREEN — Minimal Code

Write the simplest code to pass the test. Nothing more.

**Good:**
```python
def add(a, b):
    return a + b  # Nothing extra
```

**Bad:**
```python
def add(a, b):
    result = a + b
    logging.info(f"Adding {a} + {b} = {result}")  # Extra!
    return result
```

Don't add features, refactor other code, or "improve" beyond the test.

**Cheating is OK in GREEN:**
- Hardcode return values
- Copy-paste
- Duplicate code
- Skip edge cases

We'll fix it in REFACTOR.

### Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
# Run the specific test
pytest tests/test_feature.py::test_specific_behavior -v

# Then run ALL tests to check for regressions
pytest tests/ -q
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix the code, not the test.

**Other tests fail?** Fix regressions now.

### REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers
- Simplify expressions

Keep tests green throughout. Don't add behavior.

**If tests fail during refactor:** Undo immediately. Take smaller steps.

### Repeat

Next failing test for next behavior. One cycle at a time.

## References

- `references/pytest-fixture-mutation-pitfall.md` — pytest fixtures that return references to module-level dicts silently contaminate other tests. Real debugging session (2026-06-12): 15 minutes lost to fixture mutation in bilateral contract tests. The fix is always `copy.deepcopy()` before mutation.

## Why Order Matters

**"I'll write tests after to verify it works"**

Tests written after code pass immediately. Passing immediately proves nothing:
- Might test the wrong thing
- Might test implementation, not behavior
- Might miss edge cases you forgot
- You never saw it catch the bug

Test-first forces you to see the test fail, proving it actually tests something.

**"I already manually tested all the edge cases"**

Manual testing is ad-hoc. You think you tested everything but:
- No record of what you tested
- Can't re-run when code changes
- Easy to forget cases under pressure
- "It worked when I tried it" ≠ comprehensive

Automated tests are systematic. They run the same way every time.

**"Deleting X hours of work is wasteful"**

Sunk cost fallacy. The time is already gone. Your choice now:
- Delete and rewrite with TDD (high confidence)
- Keep it and add tests after (low confidence, likely bugs)

The "waste" is keeping code you can't trust.

**"TDD is dogmatic, being pragmatic means adapting"**

TDD IS pragmatic:
- Finds bugs before commit (faster than debugging after)
- Prevents regressions (tests catch breaks immediately)
- Documents behavior (tests show how to use code)
- Enables refactoring (change freely, tests catch breaks)

"Pragmatic" shortcuts = debugging in production = slower.

**"Tests after achieve the same goals — it's spirit not ritual"**

No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

Tests-after are biased by your implementation. You test what you built, not what's required. Tests-first force edge case discovery before implementing.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for the code you touch. |

## Red Flags — STOP and Start Over

If you catch yourself doing any of these, delete the code and restart with TDD:

- Code before test
- Test after implementation
- Test passes immediately on first run
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write the wished-for API. Write the assertion first. Ask the user. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify the design. |

## the harness Integration

### Running Tests

Use the `terminal` tool to run tests at each step:

```python
# RED — verify failure
terminal("pytest tests/test_feature.py::test_name -v")

# GREEN — verify pass
terminal("pytest tests/test_feature.py::test_name -v")

# Full suite — verify no regressions
terminal("pytest tests/ -q")
```

### With subagent dispatch

When dispatching subagents for implementation, enforce TDD in the goal:

```python
spawn_subagent(
    goal="Implement [feature] using strict TDD",
    context="""
    Follow test-driven-development skill:
    1. Write failing test FIRST
    2. Run test to verify it fails
    3. Write minimal code to pass
    4. Run test to verify it passes
    5. Refactor if needed
    6. Commit

    Project test command: pytest tests/ -q
    Project structure: [describe relevant files]
    """,
    toolsets=['terminal', 'file']
)
```

### With systematic-debugging

Bug found? Write failing test reproducing it. Follow TDD cycle. The test proves the fix and prevents regression.

Never fix bugs without a test.

## Testing Anti-Patterns

- **Testing mock behavior instead of real behavior** — mocks should verify interactions, not replace the system under test
- **Testing implementation details** — test behavior/results, not internal method calls
- **Happy path only** — always test edge cases, errors, and boundaries
- **Brittle tests** — tests should verify behavior, not structure; refactoring shouldn't break them
- **Cookie/session leakage in API test fixtures** — When testing cookie-based auth (httpOnly JWT, session cookies), session-scoped `TestClient` fixtures leak cookies between tests. An "unauthenticated" test that runs after an "authenticated" test will receive the previous test's cookie and return 200 instead of the expected 401. **Fix:** Use function-scoped fixtures (not session-scoped) for the `TestClient` itself, and inject auth cookies per-test via a separate fixture that sets `client.cookies.set("access_token", token)`. The DB setup/seeding can stay session-scoped, but the HTTP client must be per-test.
- **TestClient silently passing auth tests for the wrong reason** — When the endpoint under test accepts MULTIPLE auth methods (cookie + `Authorization: Bearer` header, API key + JWT, etc.), a TestClient test that authenticates via method A will *also* send any prior method-A credentials via the cookie jar, so the test returns 200 even if method B is completely broken. The test passes, the suite passes, the bug ships to production. **Symptoms:** Task marked "auth wired up", `pytest tests/test_auth.py` green at 100%, but live `curl -H "Authorization: Bearer ..."` returns 401. **Fix pattern when extending an auth dependency to accept a new credential source:**
  1. **Test each auth path in isolation with a fresh TestClient.** Don't reuse a client that has a cookie set earlier in the same test or in a session-scoped fixture.
  2. **Explicitly assert the OTHER path is absent.** For the header test, do `client.cookies.clear()` and pass no other headers. For the cookie test, omit the `Authorization` header.
  3. **Or: use two independent TestClient instances** — one per auth path — instead of clearing state on a shared client. This makes the isolation structural, not behavioral.
  4. **Treat TestClient auth tests as a soft signal.** Live curl (or another real HTTP client) is the hard signal. Any auth refactor that adds a new credential source needs live curl QA as part of acceptance criteria, the same way `clean install before push` is a hard rule for dependency changes.
  5. **The diagnostic that catches this fast:** write a curl that exercises ONLY the new auth path against a freshly-started server. If the new path returns 200, the code works. If it returns 401/403, the test suite's green is misleading you.

  **Case study (2026-06-10, the ELO scenario lab):** Task 1.3 was "return `access_token` in login response so CLI can use `Authorization: Bearer`." The TestClient test asserted this worked. Suite went green at 100%. The bug: `get_current_user` only accepted the httpOnly cookie. TestClient was sending both, and the cookie path returned 200, masking that the header path was dead. Live curl at the end of the sprint caught it. The principle: **if your test fixture is the one sending both auth methods, your test cannot tell which one the response was authenticated with.**

- **Test env never reaches the production code path — the "empty test data" trap.** When the test environment has no real corpus data (empty SQLite, no seeded evidence_items, no market odds, no player stats), endpoints with an early-return guard like `if not games or not ratings: return empty report` exit before the real code runs. Your test passes, but production 500s on the first request with real data — because the code path your test never executed is broken. This is the most common reason "passes all tests, fails in prod" surprises ship.

  **The pattern, recognizable in the test source:**
  ```python
  def test_accuracy_nba(auth_client):
      r = auth_client.get("/api/accuracy/nba")
      assert r.status_code == 200  # ← passes because test DB has no NBA data
                                  #   → early-return path returns empty report
                                  #   → 200, but real code was never exercised
  ```

  **Three changes that make this fail loud instead of fail silent:**

  1. **Mock the data layer to return a minimal valid dataset.** Use `monkeypatch.setattr` on the corpus/DB/loader module to return 1 game, 2 teams, the required fields. The test now forces the code past the early-return and into the real engine/wiring code. This is the most direct fix — it converts the test from "exercises the empty path" to "exercises the real path with synthetic data."

  2. **For every endpoint with an early-return guard, write AT LEAST ONE test with a populated fixture.** Don't write only the "empty → 200/empty" case. The populated case is the one that catches wiring bugs. A pattern: write a `test_<endpoint>_empty` (asserts the early-return) AND a `test_<endpoint>_populated` (asserts the real path with mocked data).

  3. **Verify the test FAILS with the exact production error before fixing.** TDD's RED step matters even for bug fixes: revert your fix, run the test, confirm it fails with the exact stack trace the user reported. If it fails for a different reason (typo, missing import, wrong mock shape), the test isn't testing the right thing — fix the test first. Only re-apply the fix once you've seen the test fail the same way production failed.

  **When to apply this pattern proactively:**
  - Any endpoint with a `if not data: return empty` early-return
  - Any code path that depends on corpus data being populated (engine seeding, market odds, player stats, scenario derivation)
  - Any time the test SQLite is much smaller than production Postgres
  - Any time a code path was added recently (in this PR or a recent one) — those are the paths test coverage is most likely to have missed

  **Real case (2026-06-10, the ELO scenario lab):** `test_accuracy_mlb` and friends all passed at 200 because the test DB had no completed games. The NBA branch of `/api/accuracy/{sport}` had an `UnboundLocalError` on `team_stats` (loaded after the engine-seeding block referenced it). Production got 500 on every NBA request. Fix: added `test_accuracy_nba_does_not_500` that mocked `corpus.async_load_completed_games`, `async_load_ratings_for_prediction`, `async_load_player_stats_aggregated` to return a minimal 1-game NBA dataset. The test failed with the exact `UnboundLocalError` from production, then passed after hoisting the `team_stats` load. The "monkeypatch the corpus" pattern is reusable for any production-only code path.

  **The meta-rule:** if your test fixture is the empty case, your test cannot tell whether the populated case works. Force the populated case with mocked data.

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without the user's explicit permission.
