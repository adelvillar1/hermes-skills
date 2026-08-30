# Regression Tests for the LLM-Numbers Guard

A worked example: the 9-test regression suite for the `llm_numbers_agree` post-validator
and the `generate_team_narrative` canonical-numbers contract.

Sourced from a 2026-06-01 fix on the ELO Scenario Lab. The bug: a team's stat tile showed
`▼ 47 (7-day delta)` while the headline showed "Rays are sliding — 82 points in 10 games."
Both numbers were real (from different code paths), but the user couldn't tell which to
trust. The fix locks in the canonical-numbers pattern via these tests.

## Test File: `tests/test_narrative.py`

The full file structure (after the fix):

```python
"""Tests for the narrative service."""

import pytest
from src.services.narrative import (
    _llm_numbers_agree,
    generate_match_narrative,
    generate_team_narrative,
)
```

The imports include `_llm_numbers_agree` directly — testing the guard function in
isolation. If you only test it indirectly through the LLM call, you can't verify
edge cases like "what if the LLM cites zero numbers" without mocking.

## Test 1: The contract — narrative uses form_trend, NOT history

```python
def _sample_team():
    return {
        "id": "TB",
        "name": "Tampa Bay Rays",
        "sport": "MLB",
        "rating": 1567,
        "rating_delta_10g": -82,  # deliberately a different number — the
                                  # narrative must NOT use this
        "position_change": 3,
    }


def _sample_history(current=1567):
    return [
        {"date": f"2026-04-{i+1:02d}", "rating": current + (60 - i) * 1.5}
        for i in range(60)
    ]


def test_team_narrative_uses_form_trend_7d_not_history():
    """The deterministic narrative's headline/summary must cite the
    7-day delta from form_trend (the same number the dashboard tile
    shows), not a number derived from rating_delta_10g or a fresh
    recompute from history."""
    team = _sample_team()
    history = _sample_history()
    form_trend = {"delta_7d": -47, "delta_14d": -68, "delta_30d": -58, "current": 1567}

    result = generate_team_narrative(team, history, [], [], form_trend=form_trend)

    assert "47" in result["headline"], (
        f"headline must use the 7-day delta from form_trend (-47), got: {result['headline']!r}"
    )
    assert "82" not in result["headline"], (
        f"headline must NOT use rating_delta_10g (-82), got: {result['headline']!r}"
    )
    assert "47" in result["summary"]
    assert "58" in result["summary"]
```

**Why both positive and negative assertions:** the positive (`"47" in headline`) catches
the case where the function uses form_trend correctly. The negative (`"82" not in headline`)
catches the case where the function ignores form_trend and falls back to the bug
behavior (using `rating_delta_10g`). Both must pass.

## Test 2: Backward compat — fall back to history when form_trend absent

```python
def test_team_narrative_falls_back_to_history_when_no_form_trend():
    """If form_trend isn't passed, the function should still produce a
    narrative by recomputing from history (legacy behavior). This
    keeps the function usable in unit tests and in older call sites."""
    team = _sample_team()
    history = _sample_history()

    result = generate_team_narrative(team, history, [], [], form_trend=None)

    assert result["headline"]
    assert result["summary"]
    assert "Tampa Bay Rays" in result["headline"]
```

**Why this matters:** the function signature change is a breaking change. Older call sites
and unit tests that don't have form_trend should still work. Without this test, a future
refactor that makes `form_trend` required would silently break those callers.

## Test 3: Empty inputs don't crash

```python
def test_team_narrative_handles_empty_history():
    """If both history and form_trend are empty, the narrative should
    not crash and should still produce sane output."""
    team = _sample_team()
    result = generate_team_narrative(team, [], [], [], form_trend=None)
    assert result["headline"]
    assert result["summary"]
    assert "1567" in result["summary"]  # rating is preserved
```

**Edge case:** new teams with no rating history. The narrative should still produce
output, just without trend deltas. The rating itself is the fallback content.

## Test 4: Zero deltas don't claim movement

```python
def test_team_narrative_suppresses_zero_deltas():
    """When both deltas are ~0, the summary should NOT claim the team
    is moving (it isn't). Otherwise the prose contradicts the tile."""
    team = _sample_team()
    form_trend = {"delta_7d": 0, "delta_14d": 0, "delta_30d": 0, "current": 1567}
    history = _sample_history()

    result = generate_team_narrative(team, history, [], [], form_trend=form_trend)

    # Neither "down" nor "up" should appear in the summary prose
    assert " down " not in result["summary"]
    assert " up " not in result["summary"]
```

**Why this matters:** the threshold logic in the template decides when to say "up/down."
If the threshold is too low, the summary will say "down 0 over the last 7 days" — which
contradicts the tile (which shows 0). The prose should be silent when the number is 0.

## Test 5: The LLM agrees with canonical

```python
def test_llm_numbers_agree_matches_canonical():
    """When the LLM-produced prose cites the canonical number, accept."""
    result = {
        "headline": "Rays are sliding — 47 points in the last 7 days",
        "summary": "Rays sit at a 1567 ELO rating, down 47 over the last 7 days.",
    }
    assert _llm_numbers_agree(result, canonical_7d=-47, canonical_30d=-58) is True
```

The happy path: LLM cites the right number with the right sign. Accept.

## Test 6: The 2026-06-01 bug — sign flip rejects

```python
def test_llm_numbers_agree_rejects_sign_flip():
    """The 2026-06-01 bug: LLM said '82 points' (rating_delta_10g, but
    with the right sign for an 82-point drop), but the canonical was
    -47. Sign-disagreement is a contradiction, not a rounding error —
    reject."""
    result = {
        "headline": "Rays are sliding — 82 points in the last 7 days",
        "summary": "Down 82 over the last week.",
    }
    # Canonical is -47. The "Down 82" carries an explicit negative sign
    # that contradicts the canonical magnitude. Reject.
    assert _llm_numbers_agree(result, canonical_7d=-47, canonical_30d=-58) is False
    # If the canonical were -82 and the prose said "Down 82", sign and
    # magnitude agree → accept.
    assert _llm_numbers_agree(result, canonical_7d=-82, canonical_30d=-58) is True
```

**Why sign-flip is special:** a sign flip is never a rounding error. If the LLM says
"down 82" and canonical is "47" (any sign), either the LLM is wrong or the canonical
is wrong — but the prose must not be trusted. A magnitude disagreement of 0.5 might be
rounding, but `+82` vs `-47` is a real contradiction.

## Test 7: Wrong magnitude with right sign still rejects

```python
def test_llm_numbers_agree_rejects_wrong_magnitude():
    """Even with the right sign, a magnitude that disagrees by more than
    rounding is a contradiction."""
    result = {
        "headline": "Rays are sliding — 200 points in the last 7 days",
        "summary": "down 200 over the last week.",
    }
    assert _llm_numbers_agree(result, canonical_7d=-47, canonical_30d=-58) is False
```

**Why this test:** the LLM might use the right sign (negative) but invent a wildly
different magnitude. Without this test, a "sign-only" guard would let this through.

## Test 8: No number at all = trust the LLM

```python
def test_llm_numbers_agree_tolerates_no_number():
    """If the LLM's prose doesn't include a parseable number (e.g. it
    avoided quoting a delta altogether), trust it — the rest of the
    response was likely fine."""
    result = {
        "headline": "Rays in transition",
        "summary": "The team is reassessing strategy this week.",
    }
    assert _llm_numbers_agree(result, canonical_7d=-47, canonical_30d=-58) is True
```

**Why:** a strict guard would reject any LLM output that doesn't quote the canonical
number. But LLMs often produce good prose that *paraphrases* the trend ("in transition,"
"reassessing") without citing a specific number. Those responses are fine — the
canonical number is shown in the tile anyway. Rejecting them would force the fallback
on every "soft" headline, defeating the purpose of using an LLM at all.

The trade-off: a malicious LLM that produces no numbers at all would also pass. That's
acceptable because (a) the canonical number is still shown in the tile, so the user
sees the truth, and (b) the LLM gets no benefit from producing no numbers, so there's
no incentive to game it.

## Test 9: Rounding tolerance

```python
def test_llm_numbers_agree_tolerates_rounding():
    """LLM may round 47.4 to 47 — same sign, off by less than the
    tolerance passes."""
    result = {
        "headline": "Rays surging with +47 points in the last 7 days",
        "summary": "gained 47 over the last week.",
    }
    assert _llm_numbers_agree(result, canonical_7d=47.4, canonical_30d=58) is True
```

**Why 0.5:** the canonical number is computed with float arithmetic (e.g. `current -
history[-7].rating` = `47.4`). The LLM is given a rounded integer prompt. The prose
should round to the same integer. A 0.5 tolerance handles the "LLM rounds 47.4 to 47"
case without letting "LLM invents 200" through.

## Test Order Matters

The tests above are ordered from **most likely to fail** to **least likely to fail**:

1. **Test 1** (form_trend_7d_not_history) catches the *exact bug* this fix addresses. Run it first when you suspect a regression.
2. **Tests 5-7** (LLM guard) catch LLM-drift regressions. Run these when the LLM provider changes.
3. **Test 4** (zero deltas) catches template threshold regressions.
4. **Tests 2-3** (fallbacks) catch edge-case regressions. Lower priority because they're less likely to fire in production.

## The 10th Test You Didn't Write But Should

There's a test class for what happens when the LLM call itself **succeeds but the response is malformed JSON**. The fix should handle this in the LLM wrapper (return `None` on parse failure → caller falls back to template). If you're not testing the LLM wrapper directly, add an integration test:

```python
async def test_llm_narrative_falls_back_on_malformed_response(monkeypatch):
    """If the LLM returns malformed JSON, the caller should fall back
    to the deterministic template narrative."""
    async def fake_call(*args, **kwargs):
        return "this is not valid JSON {"

    monkeypatch.setattr("httpx.AsyncClient.post", fake_call)
    result = await generate_llm_team_narrative(team, ..., form_trend=form_trend, base_narrative=base)
    assert result is None  # wrapper returns None on parse failure
```

This test isn't in the 9-test regression suite but is the kind of test that catches
"we shipped a code path that crashes when the LLM provider is in a degraded state."
