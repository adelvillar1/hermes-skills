---
name: design-an-interface
description: Generate multiple interface designs and compare them.
---

# Design an Interface

Based on "Design It Twice" from *A Philosophy of Software Design*: the first design is rarely the best. Generate multiple radically different interface designs, then compare them.

## Workflow

1. Gather requirements
   - What problem does this module solve?
   - Who are the callers?
   - What are the key operations and constraints?
   - What should be hidden vs. exposed?

2. Generate designs in parallel
   - Spawn 3+ sub-agents via `subagent dispatch`, each with a different constraint:
     - Agent 1: minimize method count (1-3 max).
     - Agent 2: maximize flexibility.
     - Agent 3: optimize for the most common case.
     - Agent 4: take inspiration from a specific paradigm or library.
   - Each outputs: interface signature, usage example, hidden internals, trade-offs.

3. Present designs
   - Show the interface signature, usage example, and what each design hides.

4. Compare
   - Interface simplicity.
   - General vs. specialized.
   - Implementation efficiency.
   - Depth: small interface hiding significant complexity.
   - Ease of correct use vs. misuse.

5. Synthesize
   - The best design often combines insights from several options.

## Evaluation criteria

- Simplicity: fewer methods are easier to learn.
- Generality: handle future cases without over-generalizing.
- Implementation efficiency: the shape should allow efficient internals.
- Depth: small interface, large hidden complexity is good.

## Anti-patterns

- Do not let sub-agents produce similar designs; enforce radical differences.
- Do not skip the comparison step.
- Do not implement; focus on interface shape.
- Do not evaluate based on implementation effort.
