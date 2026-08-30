# Retrospective Document Structure

Template for the output document produced by a full git-history-analysis session.
Adapt section count to the project's actual workstream count.

---

```markdown
# {Project Name} — Project Retrospective

**Period:** {first commit date} – {last commit date} ({duration})
**Generated:** {date}, from full GitHub commit history ({N} commits)

---

## 1. The Numbers

| Metric | Value |
|---|---|
| Total commits | N |
| Files (primary language) | N |
| Lines of code | N |
| Contributors | N |
| Staging deploys | N |
| Production deploys | N |
| Staging-to-prod gate ratio | N:1 |
| Busiest day | {date} ({N} commits) |
| Busiest day of week | {day} ({N} commits) |

### Commit type distribution
(table: type | count | share)

### The monthly arc
(table: month | commits | fix | feat | fix:feat | phase label)

Narrative paragraph: what the ratio arc tells about the project's maturity journey.

---

## 2. The Blank Slate / Origin Story

How the project started. What was known vs. unknown.
The three discovery questions: sources, data shapes, connections.
Key "aha" moments with exact commit timestamps.

---

## 3. The Workstreams

One subsection per workstream (3.1, 3.2, ...). Each contains:

### 3.N {Name} — {Difficulty Type} ({N} commits, {N}% fix rate)

**The challenge:** one sentence framing why this was hard.

**The arc:** chronological bullet points with dates, grouped into phases.
Use exact commit messages as evidence (quoted).

**Why it was hard:** the structural reason (not just "lots of bugs").
Map to a difficulty type:
- Integration convergence (many systems arriving at one surface)
- Inference without ground truth (no correct answer to check against)
- Geographic/rendering (edge cases from the physical world)
- Multi-source integration (many external APIs that must agree)
- Normalization + volume (messy real-world data → queryable schema)
- Bottom-up discovery (hierarchy emerges from data, not assumptions)
- Scale + computation (deterministic but large)
- Pipeline design + cost engineering (making AI affordable at scale)

---

## 4. The Difficulty Ranking

| Rank | Feature | Commits | Fix rate | Difficulty type |
|---|---|---|---|---|

**The pattern:** one paragraph on what separates hard from easy
(integration surfaces and inference layers are hardest per-commit;
deterministic computation is easiest despite being largest).

---

## 5. Key Patterns & Lessons

Numbered subsections (5.1, 5.2, ...). Each is one lesson with evidence.
Aim for 5-8 lessons. Good lesson types:
- "Integration surfaces break the most"
- "Front-loaded difficulty is healthier than distributed difficulty"
- "Bottom-up is more expensive but produces truth"
- "The staging gate is real discipline"
- "Tests are the known gap"
- "The cache is the product, not the optimization"
- "Design-first makes migrations bounded"

---

## 6. The Product That Emerged

Bullet inventory of what was actually built. Concrete numbers.
End with a one-paragraph "from X to Y" statement capturing the journey.

---

*Generated from {N} commits on the `{branch}` branch of `{repo}`, retrieved via GitHub API on {date}.*
```

---

## Writing Guidelines

- Lead each workstream section with the *structural* reason it was hard, not just "lots of commits"
- Use exact commit messages as evidence (they're more convincing than paraphrases)
- When the user states a hypothesis, confirm it AND add the dimension they didn't see
- The difficulty ranking should surprise — the largest workstream isn't always the hardest per-commit
- End lessons with strategic implications, not just observations
- The "Product That Emerged" section should make the reader feel the distance traveled
