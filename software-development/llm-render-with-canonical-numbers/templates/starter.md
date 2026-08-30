# Starter: canonical-numbers pattern for a new use case

Copy this directory's files and modify. The two reusable pieces are:

1. **`guard.py`** — the post-validation guard. Reusable across any LLM-numbers
   use case. Configure the regex patterns to match the specific numbers and
   sign-bearing words your domain uses.
2. **`prompt_template.txt`** — the LLM prompt with CANONICAL NUMBERS block.
   Edit the `## Schema` and `## Domain` sections to match your use case.

## guard.py

```python
"""Post-validation guard for LLM responses that cite numeric values.

Reusable across any "LLM writes prose around a number the system
already knows" workflow. Rejects the LLM's response if it contradicts
the canonical values; on rejection, caller falls back to a
deterministic template.

To configure for a new domain:
- Update SIGN_BEARING_VERBS to include domain-specific sign words
  ("gained", "lost", "grew", "dropped", "improved", "declined", etc.)
- Update MAGNITUDE_REGEX to match the unit of measurement the LLM
  is expected to cite ("points", "%", "$", "kg", "tokens", etc.)
- Update the tolerance parameter if rounding precision is different
"""
import re
from typing import Optional


SIGN_BEARING_VERBS = {
    "down": -1, "up": 1, "lost": -1, "gained": 1,
    "dropped": -1, "declined": -1, "fell": -1,
    "rose": 1, "grew": 1, "improved": 1, "surged": 1,
    "slid": -1, "tanked": -1, "jumped": 1,
}


def llm_agrees_with_canonical(
    result: dict,
    canonical_values: dict[str, float],
    tolerance: float = 0.5,
) -> bool:
    """Return True if the LLM-produced prose doesn't contradict the
    canonical values. Rejects on sign flip (always wrong) and on
    magnitude disagreement > tolerance (rounding tolerance).

    Parameters
    ----------
    result : dict
        The LLM's response, expected to have string fields like
        'headline', 'summary', 'explanation', etc.
    canonical_values : dict
        Map from canonical-key (e.g. '7d_delta') to its numeric
        value. The keys here are referenced in the magnitude regex
        and the prompt.
    tolerance : float
        How close a cited number must be to the canonical to be
        accepted. 0.5 is the default (handles LLM rounding 47.4 to 47).

    Returns
    -------
    bool
        True if the LLM's response is consistent with the canonical
        values (or cites no numbers at all). False if any cited
        number contradicts the canonical sign or magnitude.
    """
    # Combine all string fields in the result
    combined = " ".join(
        str(v) for v in result.values() if isinstance(v, str)
    )

    # 1) Sign-bearing patterns carry an explicit sign. If any is
    # present, the sign must agree with canonical.
    sign_bearing = []
    verb_pattern = r"(" + "|".join(SIGN_BEARING_VERBS.keys()) + r")\s+(\d+(?:\.\d+)?)"
    for m in re.finditer(verb_pattern, combined, re.IGNORECASE):
        verb = m.group(1).lower()
        magnitude = float(m.group(2))
        sign_bearing.append(SIGN_BEARING_VERBS[verb] * magnitude)

    # Explicit +N / -N patterns
    for m in re.finditer(r"([+-])\s*(\d+(?:\.\d+)?)\s*(?:points?|%|kg|tokens?|\$|usd)", combined, re.IGNORECASE):
        sign = 1 if m.group(1) == "+" else -1
        sign_bearing.append(sign * float(m.group(2)))

    # Check signs against each canonical value
    for key, canonical in canonical_values.items():
        if canonical == 0:
            continue
        canonical_positive = canonical > 0
        for d in sign_bearing:
            if (d > 0) != canonical_positive:
                return False  # sign flip

    # 2) Magnitude patterns. If prose cites any number in a
    # domain-specific unit, at least one should be within rounding
    # of the corresponding canonical value.
    magnitude_pattern = r"(\d+(?:\.\d+)?)\s*(?:points?|%|kg|tokens?|\$|usd)"
    magnitudes = [float(m.group(1)) for m in re.finditer(magnitude_pattern, combined, re.IGNORECASE)]

    if magnitudes and canonical_values:
        # Check each magnitude against the closest canonical value.
        # Accept if at least one magnitude matches any canonical value
        # within tolerance.
        canonicals = list(canonical_values.values())
        if not any(
            any(abs(m - c) <= tolerance for c in canonicals)
            for m in magnitudes
        ):
            return False

    # 3) No sign-bearing or magnitude patterns at all? Trust the LLM.
    # (The canonical value is shown elsewhere — the tile, the chart —
    # so the user sees the truth even if the LLM paraphrases.)
    return True
```

## prompt_template.txt

```
You are a sharp, concise [YOUR DOMAIN] analyst. Rewrite this snapshot in
your own voice, keeping all numbers EXACTLY as they appear in the source.

CANONICAL NUMBERS (do not change, paraphrase around them):
[FOR EACH CANONICAL VALUE:]
- [HUMAN-READABLE LABEL]: [CANONICAL_VALUE]
  Example phrasing: "up X" / "down X" / "X"

REFERENCE PROSE (the source of truth — your output should convey the
same information in slightly punchier language):
- Headline: [BASE_HEADLINE]
- Summary: [BASE_SUMMARY]

[ANY ADDITIONAL CONTEXT THE LLM CAN USE TO ENHANCE THE PROSE — OPPONENT
MATCHUPS, ROSTER NOTES, INJURY UPDATES, ETC.]

Return ONLY valid JSON with these exact keys:
{
  "headline": "[1-LINE HEADLINE USING THE CANONICAL VALUES]",
  "summary": "[2-SENTENCE SUMMARY USING THE CANONICAL VALUES VERBATIM]",
  "[ANY ADDITIONAL FIELDS YOU NEED]"
}

No markdown, no explanation, just the JSON object:
```

## Usage

```python
# 1. Compute canonical values deterministically
canonical = {"7d_delta": -47.0, "30d_delta": -58.0, "rating": 1567.0}

# 2. Render the deterministic template
base = render_canonical_template(team, canonical)

# 3. Call the LLM with the canonical frame
llm_result = await call_llm(base, canonical)

# 4. Post-validate
if llm_result is None or not llm_agrees_with_canonical(llm_result, canonical):
    logger.warning("LLM rejected by guard; using template")
    narrative = base
else:
    narrative = llm_result
```
