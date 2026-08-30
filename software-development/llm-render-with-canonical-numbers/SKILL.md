---
name: llm-render-with-canonical-numbers
description: "Use an LLM to write natural-language prose around a machine-computed number, with a guard that prevents the LLM from contradicting that number. The pattern: deterministic template produces the canonical narrative, LLM is asked to enhance the prose only, post-validator parses the LLM's response and rejects any sign/magnitude contradiction. Use whenever an LLM is asked to render human-readable text around a value the system already knows the truth about — team narratives, report summaries, model explanations, narration around pre-computed scores. Adjacent to llm-tool-answer-reliability (which covers tool-call hallucinations); this covers the different failure mode of 'LLM prose around canonical machine numbers.'"
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [llm, hallucination, narrative, canonical-data, post-validation, guardrail, determinism]
    related_skills: [llm-tool-answer-reliability, dual-emit-llm-generation, root-cause-first-debugging]
    category: software-development
---

# LLM as Renderer Around Canonical Numbers

The failure mode this skill addresses: a UI surface (or report, or API response) renders a number from one code path and renders prose explaining that number from another code path. The LLM that writes the prose sees multiple inconsistent numbers, picks one, and the prose contradicts the value the UI tile is showing.

**Concrete example:** a sports analytics dashboard. Stat tile shows `▼ 47 (7-day delta)`. LLM-generated headline on the same page says *"Rays are sliding — 82 points in 10 games."* Both numbers are real. Both come from real code. The user reads "47" in the tile and "82" in the headline and concludes the dashboard is broken. It's not broken — it's incoherent.

This bug is structurally hard to avoid with LLMs in the loop, because the LLM is being given a *choice* of which number to use. The only defense is to take the choice away.

## The Pattern (4 components)

### 1. Compute the canonical numbers deterministically (no LLM)

Before the LLM sees anything, the system has already computed the numbers the user will see. Lock them in a `form_trend` (or equivalent) object: `{ "delta_7d": -47.1, "delta_30d": -57.7, "current": 1567 }`. These are the **canonical numbers** — the only numbers the system will trust anywhere downstream.

```python
# In the API route, before any narrative generation
form_trend = {
    "current": round(current_rating, 1),
    "delta_7d": round(current - history[-7]["rating"], 1) if hist_len >= 7 else 0,
    "delta_30d": round(current - history[-30]["rating"], 1) if hist_len >= 30 else 0,
}
```

The UI tile, the LLM prompt, the post-validator, and the deterministic fallback all read from this same object. **One source of truth.**

### 2. Render the canonical narrative deterministically (template, no LLM)

Build a template-based narrative that uses the canonical numbers verbatim. This is your fallback AND the frame you give the LLM. The template doesn't have to be elegant — it just has to be correct.

```python
def render_canonical_narrative(team, form_trend):
    delta_7d = form_trend["delta_7d"]
    delta_30d = form_trend["delta_30d"]
    if abs(delta_7d) > 10:
        word = "surging" if delta_7d > 0 else "sliding"
        headline = f"{team.name} are {word} — {abs(delta_7d):.0f} points in the last 7 days"
    else:
        headline = f"{team.name} are holding steady"
    summary = (
        f"{team.name} sit at a {team.rating:.0f} ELO rating"
        + (f", down {abs(delta_7d):.0f} over the last 7 days" if delta_7d < 0 else f", up {delta_7d:.0f} over the last 7 days" if delta_7d > 0 else "")
        + (f", and down {abs(delta_30d):.0f} across the past 30 days" if delta_30d < 0 else f", and up {delta_30d:.0f} across the past 30 days" if delta_30d > 0 else "")
        + "."
    )
    return {"headline": headline, "summary": summary}
```

This output is your "ground truth" — the prose you'd ship if LLMs didn't exist. The headline and summary are now mathematically tied to the tile values.

### 3. Give the LLM the canonical prose as a frame, ask it to enhance wording only

The LLM is told explicitly: the numbers are sacred, the prose is what you're paying me to enhance. Use the canonical narrative as a `reference_prose` block in the prompt.

```python
base = render_canonical_narrative(team, form_trend)
prompt = f"""Rewrite this team snapshot in your own voice. All numbers are
CANONICAL — do not change them, paraphrase around them.

CANONICAL NUMBERS:
- 7-day delta: {form_trend['delta_7d']:+.0f}
- 30-day delta: {form_trend['delta_30d']:+.0f}
- Current ELO: {team['rating']:.0f}

REFERENCE PROSE (the source of truth — your output should convey the same
information in slightly punchier language):
- Headline: {base['headline']}
- Summary: {base['summary']}

Return ONLY valid JSON with these exact keys:
{{ "headline": "...", "summary": "...", "form_story": "...",
   "outlook": "...", "key_stat": "..." }}

No markdown, just the JSON object:"""
```

Three things the prompt must do explicitly:
1. Name the canonical numbers and tell the LLM not to change them.
2. Provide the reference prose so the LLM has a baseline to enhance, not invent.
3. Use the word "CANONICAL" — it's a strong instruction-following signal for most LLMs.

### 4. Post-validate the LLM's response, reject on contradiction, fall back to template

This is the guard. The LLM's response is parsed for any sign-bearing or magnitude-bearing number, and rejected if it contradicts the canonical values.

```python
import re

def llm_agrees_with_canonical(llm_result, canonical_7d, canonical_30d, tolerance=0.5):
    combined = f"{llm_result.get('headline','')} {llm_result.get('summary','')}"
    
    # 1) Sign-bearing patterns carry an explicit sign. If any disagrees
    # with the canonical sign, reject — a sign flip is always wrong.
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
            return False  # sign flip
    
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

Then the call site falls back to the canonical template if the LLM response fails the guard:

```python
llm_result = await generate_llm_narrative(team, form_trend, base)
if llm_result is None or not llm_agrees_with_canonical(llm_result, form_trend["delta_7d"], form_trend["delta_30d"]):
    logger.warning("LLM narrative contradicted canonical numbers; using template")
    narrative = base
else:
    narrative = llm_result
```

## Why This Works (and the Alternative Doesn't)

**Without the canonical-numbers frame**, the typical prompt is:

> *"You are an analyst. Write a 2-sentence team snapshot. Current ELO: 1567. 10-game delta: -82. 7-day delta: -47. 30-day delta: -58."*

The LLM sees three numbers. It picks one (the most recent, or the most narratively interesting, or just the one it noticed first). It writes "82 points in 10 games" because that's the largest magnitude and reads as more dramatic. The user sees a number that contradicts the tile. The system looks broken.

**With the canonical-numbers frame**, the LLM is told: there's one correct answer for each number, the reference prose shows you what it is, do not deviate. Most LLMs respect this when the instruction is explicit and the reference is concrete. When they don't, the guard catches it and the fallback preserves correctness.

The LLM is now strictly an *enhancer* — it can rephrase, add color, find a better word. It cannot change the numbers. The "trust the number" contract is preserved.

## The Guard Is Necessary, Not Optional

LLMs hallucinate numbers even with explicit instructions to the contrary. In production testing, the LLM will produce a correct response 90%+ of the time, and an invented number the rest. Without the guard, the user sees the wrong number 10% of the time — high enough to break trust, low enough to be hard to debug when it happens.

The guard also has a non-obvious second benefit: when the LLM starts to drift, you can *measure* it. The rejection rate from the guard is a metric you can chart over time. If it spikes, you know the prompt has drifted, or the LLM provider has changed behavior, or the canonical numbers have changed shape. Without the guard, drift is silent.

## Tests: Lock In the Contract

The 9 regression tests for this pattern (from a real fix on 2026-06-01) are in `references/llm-numbers-guard-regression-tests.md`. The minimum bar:

- **One test per "what can go wrong" failure mode**: sign flip, wrong magnitude, no number at all, rounding tolerance, LLM agreeing with canonical.
- **One test that the canonical narrative uses the canonical numbers** (locks in the template → canonical flow).
- **One test that the canonical narrative doesn't use non-canonical sources** (locks in "you must not use `rating_delta_10g` even if it's available" — the 2026-06-01 bug was that the narrative used a 10-game delta while the tile used a 7-day delta).

Without the test for "must NOT use non-canonical sources," a future refactor will quietly re-introduce the bug.

## When to Use This Pattern

Use it whenever:
- An LLM is asked to render prose around a specific value the system already knows.
- The same value is shown to the user in multiple places (a tile, a chart label, a card).
- The user is likely to compare the prose to the other places the value appears.

Don't use it when:
- The LLM is generating creative content unrelated to known values (no number-guard needed).
- The values are entirely LLM-generated and not displayed elsewhere (guard would just be a self-check).
- The downstream consumer is the LLM itself (e.g., a planning agent that reads its own output) — guard the next stage instead.

## Anti-Patterns to Avoid

- **"Pin the number in the prompt and trust the LLM."** Trust fails 5-10% of the time. The guard is the only thing that makes this production-safe.
- **"Use a smaller model and don't worry about guardrails."** Smaller models are *more* likely to invent numbers, not less.
- **"Parse the LLM's JSON for the exact same number I gave it."** A paraphrase of a paraphrase will not byte-equal the canonical number. You need tolerant parsing (rounding, sign-bearing patterns, magnitude patterns).
- **"Just disable the LLM in production."** That defeats the purpose. The LLM adds real value (better prose, more natural explanations). The cost is hallucination risk. The pattern is: keep the LLM, but make its output provably correct.
- **"Compare strings for equality."** `"47 points"` and `"47 points in the last 7 days"` are different strings. You need regex on the number, not string match.

## Worked Example: Sports Analytics Team Hub

The full implementation (Python + FastAPI + DeepSeek LLM + Jinja-style template) is in `references/elo-scenario-lab-narrative-fix.md`. Highlights:
- 9 regression tests in `tests/test_narrative.py` (3 for the template, 5 for the LLM guard, 1 for the empty-history edge case).
- The deterministic template builds headline + summary from form_trend only.
- The LLM prompt has 3 explicit "CANONICAL NUMBERS" lines and the reference prose block.
- The guard rejects the LLM's response if it cites a number with a different sign OR a magnitude off by more than 0.5 from canonical.
- On rejection, the template narrative is used — the user never sees a bad number.

The bug this fixed: a user's team detail page showed "Rays are sliding — 82 points in 10 games" while the stat tile showed -47 for the 7-day delta. After the fix, both cite the same -47 number, and the LLM can decorate the prose without breaking the contract.

## References

- `references/elo-scenario-lab-narrative-fix.md` — full worked example: prompt, code, tests
- `references/llm-numbers-guard-regression-tests.md` — the 9-test regression suite, with rationale per test
- `templates/starter.md` — copy-and-modify starter with `guard.py` and `prompt_template.txt` for a new use case
