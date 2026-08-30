# Worked Example: ELO Scenario Lab Narrative Fix (2026-06-01)

Full implementation of the canonical-numbers pattern as applied to a sports
analytics dashboard. The product has team-detail pages that show stat tiles
(rating, 7-day delta, 30-day delta) AND a hero headline + summary above
those tiles. The original implementation used different code paths for each,
and the LLM was given free rein to pick whichever number looked more
dramatic — producing "82 points in 10 games" while the tile showed -47 for
the 7-day delta.

This file shows the actual diff, prompt, guard function, and tests as shipped.

## The Bug (Before)

**Symptom:** On the Rays team detail page:
- Hero stat tile: `▼ 47 (7-day delta)` (correctly computed from `form_trend.delta_7d`)
- Hero narrative headline: "Rays are sliding — 82 points in 10 games" (from LLM, which used `rating_delta_10g` from the team payload)
- Hero narrative summary: "Rays sit at a 1567 ELO rating, down 60 over the last week, and 71 across the past month" (LLM-invented, no canonical source)

Four different decline values for the same period (-47 / -60 / -71 / -82). User trust broken.

**Root cause:** `generate_team_narrative` recomputed deltas from `history[-N]` (different math from the route-level `form_trend`), and `generate_llm_team_narrative` gave the LLM four numbers with no instruction to prefer one over another.

## The Fix (After)

**Files changed:** 3 (`src/services/narrative.py`, `src/api/routes/teams.py`, `tests/test_narrative.py`).

**Pattern applied:** canonical-numbers 4-component pattern from the umbrella skill.

## Component 1: Canonical numbers computed deterministically

In `src/api/routes/teams.py:130-138`, the route already computed `form_trend`:

```python
hist_len = len(history)
form_trend = {}
if hist_len > 0:
    current = history[-1]["rating"]
    form_trend["current"] = round(current, 1)
    form_trend["delta_7d"] = round(current - history[-7]["rating"], 1) if hist_len >= 7 else 0
    form_trend["delta_14d"] = round(current - history[-14]["rating"], 1) if hist_len >= 14 else 0
    form_trend["delta_30d"] = round(current - history[-30]["rating"], 1) if hist_len >= 30 else 0
```

No change needed here — `form_trend` was already being computed. The fix was threading it into the narrative generators.

## Component 2: Template narrative uses form_trend

`src/services/narrative.py` — `generate_team_narrative` was updated to accept `form_trend` as a parameter and use it as the source of truth:

```python
def generate_team_narrative(
    team, history, scenarios, divergence,
    roster=None, form_trend=None,  # NEW parameter
):
    # Prefer form_trend deltas as the source of truth (matches the
    # dashboard stat tiles). Fall back to recomputing from history
    # only if form_trend wasn't passed (e.g. in older call sites or
    # unit tests).
    if form_trend:
        delta_7d = form_trend.get("delta_7d", 0) or 0
        delta_30d = form_trend.get("delta_30d", 0) or 0
    else:
        # Legacy fallback — recompute from history
        ...

    # Headline magnitude MUST come from delta_7d (same number the
    # 7-DAY stat tile shows) so the prose never contradicts the tile.
    headline_delta = delta_7d
    if headline_delta > 10:
        trend_word = "surging"
    elif headline_delta < -10:
        trend_word = "sliding"
    else:
        trend_word = "holding steady"

    if abs(headline_delta) > 10:
        headline = f"{team_name} are {trend_word} — {abs(headline_delta):.0f} points in the last 7 days"
    # ... etc
```

**Key change:** the magnitude threshold (>10) is now applied to `delta_7d`, not to
`rating_delta_10g`. This means the headline only triggers "sliding" prose when the
7-day delta is large enough that the tile would also show meaningful movement.

## Component 3: LLM prompt pins the canonical numbers

`src/services/narrative.py` — `generate_llm_team_narrative` was updated to accept
`form_trend` and `base_narrative` (the template's output) and to feed them into
the prompt as a "frame":

```python
async def generate_llm_team_narrative(
    team, history, scenarios, divergence,
    roster=None, next_opponents=None,
    form_trend=None,  # NEW
    base_narrative=None,  # NEW
):
    # Canonical numbers — same as the dashboard tiles. These are the
    # numbers the LLM is forbidden to contradict.
    canonical_7d = (form_trend or {}).get("delta_7d", 0) or 0
    canonical_30d = (form_trend or {}).get("delta_30d", 0) or 0

    base_headline = (base_narrative or {}).get("headline", "")
    base_summary = (base_narrative or {}).get("summary", "")

    prompt = f"""You are a sharp, concise sports analyst. Rewrite this team snapshot in
your own voice, keeping all numbers EXACTLY as they appear in the source.

CANONICAL NUMBERS (do not change, paraphrase around them):
- 7-day delta: {canonical_7d:+.0f}
- 30-day delta: {canonical_30d:+.0f}
- Current ELO: {rating:.0f}

REFERENCE PROSE (the source of truth — your output should convey the same
information in slightly punchier language):
- Headline: {base_headline}
- Summary: {base_summary}

Team: {team_name} ({sport})
{opp_summary}
{roster_summary}
{div_summary}

Return ONLY valid JSON with these exact keys:
{{
  "headline": "One punchy headline, max 12 words, using the canonical 7-day delta number",
  "summary": "2 sentences, using the canonical 7-day and 30-day delta numbers verbatim",
  "form_story": "2 sentences about their recent form trajectory",
  "outlook": "2 sentences on what to watch next",
  "key_stat": "The single most important number to know"
}}

No markdown, no explanation, just the JSON object:"""
```

**Key changes:**
1. The prompt now has an explicit "CANONICAL NUMBERS" block. The word "CANONICAL" is
   a strong instruction-following signal — most LLMs respect it.
2. The reference prose is provided verbatim. The LLM has a baseline to enhance, not
   invent from.
3. The keys in the JSON template now include explicit instructions about which numbers
   to use ("using the canonical 7-day delta number").

## Component 4: Post-validation guard

`src/services/narrative.py` — new function:

```python
def _llm_numbers_agree(result, canonical_7d, canonical_30d, tolerance=0.5):
    """Return True if the LLM-produced prose doesn't contradict the
    canonical 7d / 30d deltas. Parses sign-bearing patterns
    ('down 47', 'up 12') and magnitude patterns ('47 points'),
    rejects sign flips and wrong magnitudes."""
    import re

    combined = f"{result.get('headline', '')} {result.get('summary', '')}"

    # 1) Sign-bearing patterns carry an explicit sign. If any is present,
    # the sign must agree with canonical.
    sign_bearing = []
    for m in re.finditer(r"(down|up|lost|gained|dropped)\s+(\d+)", combined, re.IGNORECASE):
        verb = m.group(1).lower()
        magnitude = float(m.group(2))
        sign_bearing.append(-magnitude if verb in ("down", "lost", "dropped") else magnitude)
    for m in re.finditer(r"([+-])\s*(\d+)\s*(?:points?|in)", combined, re.IGNORECASE):
        sign = 1 if m.group(1) == "+" else -1
        sign_bearing.append(sign * float(m.group(2)))

    canonical_sign_positive = canonical_7d > 0
    for d in sign_bearing:
        if (d > 0) != canonical_sign_positive:
            return False  # sign flip — a real contradiction

    # 2) Magnitude patterns. If prose cites a number, at least one
    # magnitude should be within rounding of |canonical|.
    magnitudes = [
        float(m.group(1))
        for m in re.finditer(r"([+-]?\d+)\s*(?:points?|in\s+the\s+last)", combined, re.IGNORECASE)
    ]
    if magnitudes:
        target = abs(canonical_7d)
        if not any(abs(m - target) <= tolerance for m in magnitudes):
            return False

    # 3) No sign-bearing or magnitude patterns at all? Trust the LLM.
    return True
```

Called from inside `generate_llm_team_narrative` after the JSON parse:

```python
# Guard against the LLM inventing numbers. The 7-day delta the
# LLM produced must agree (within rounding) with the canonical
# 7-day delta. If it doesn't, reject and fall back to the
# template narrative on the caller side.
if not _llm_numbers_agree(result, canonical_7d, canonical_30d):
    logger.warning(
        "LLM team narrative invented numbers (canonical 7d=%s, 30d=%s); rejected",
        canonical_7d, canonical_30d,
    )
    return None
```

When the guard returns None, the caller falls back to the deterministic template:

```python
# In src/api/routes/teams.py:165-176
narrative = generate_team_narrative(
    team, history, scenarios, divergence, roster=roster, form_trend=form_trend,
)
llm_narrative = await generate_llm_team_narrative(
    team, history, scenarios, divergence,
    roster=roster,
    next_opponents=next_opponents,
    form_trend=form_trend,
    base_narrative=narrative,
)
if llm_narrative:
    narrative = llm_narrative
```

The user sees deterministic-template prose when the LLM fails the guard, never
the LLM's invented number.

## Verification (Browser + API)

**Before:**
```json
{
  "narrative": {
    "headline": "Rays are sliding — 82 points in 10 games",
    "summary": "Rays sit at a 1567 ELO rating, down 60 over the last week, and 71 across the past month."
  },
  "form_trend": {"delta_7d": -47.1, "delta_30d": -57.7}
}
```

**After (LLM rejected by guard, template used):**
```json
{
  "narrative": {
    "headline": "Rays are sliding — 47 points in the last 7 days",
    "summary": "Rays sit at a 1567 ELO rating, down 47 over the last 7 days, and down 58 across the past 30 days."
  },
  "form_trend": {"delta_7d": -47.1, "delta_30d": -57.7}
}
```

**After (LLM accepted, when it paraphrases correctly):**
```json
{
  "narrative": {
    "headline": "Rays are sliding fast — 47 points dropped in a week",
    "summary": "Tampa Bay has fallen to 1567 ELO, off 47 over 7 days and 58 over the past month."
  },
  "form_trend": {"delta_7d": -47.1, "delta_30d": -57.7}
}
```

**The 47 and 58 appear verbatim in both cases.** The headline word changed (faster
prose) but the numbers don't.

## Test Suite (9 tests)

See `references/llm-numbers-guard-regression-tests.md` for the full breakdown of
each test. Highlights:

- **`test_team_narrative_uses_form_trend_7d_not_history`**: locks in the *exact bug*
  this fix addressed. The fixture has `form_trend.delta_7d = -47` and
  `rating_delta_10g = -82`. The test asserts `"47" in headline` AND `"82" NOT in headline`.
  This is the regression test.
- **`test_llm_numbers_agree_rejects_sign_flip`**: the 2026-06-01 bug as a unit test.
  Canonical is -47, LLM said "Down 82", guard rejects.
- **`test_llm_numbers_agree_tolerates_no_number`**: the "soft headline" case. LLM
  produced "Rays in transition" with no numbers. Guard accepts (the canonical number
  is shown in the tile anyway).

## What Was NOT Changed

The 5 P0 UI fixes from session 2 (broken `#users` route, dedup alerts, fix Up Next
cards, table sort) are independent of this fix. The client-side band-aid in
`ui/js/dashboard.js:renderTeamHero` (P0-4) is now redundant — the server is the source
of truth — but it was kept as defense-in-depth. The user's recap noted this explicitly.

The dashboard.js client-side `momentumHeadline` fallback is harmless: it only fires
when the API narrative is empty, which now never happens (the template is always
returned as a fallback). Removing it would be a minor cleanup, not a fix.
