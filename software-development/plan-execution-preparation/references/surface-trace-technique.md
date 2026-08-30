# Surface Trace Technique — Worked Example

## Scenario

A draft plan proposes adding Monte Carlo simulation to a sports forecasting system. The plan lists ~10 files and estimates 10-14 hours. Before committing, trace every actual code surface.

## Technique

### 1. Read the plan, then read the code

The plan said "replace scenario generation with Monte Carlo." But reading the codebase revealed **two separate scenario systems**:

- **Pipeline-level** (`pipeline.py` → `ScenarioSimulator`): CLI-only, runs offline, outputs JSON report. Not user-facing.
- **API-level** (`routes/scenarios.py` + `services/probabilities.py`): Dashboard-facing, per-game injury-driven branches, called on every page load.

The plan treated them as one system. They share no code.

### 2. Follow the call graph

Starting from `routes/scenarios.py`, traced:
- `generate_injury_scenarios()` in `probabilities.py` → also called by `compute_game_probabilities()` → feeds the Schedule page, not just Scenarios
- `renderScenarios()` in `dashboard.js` (lines 464-583) → renders scenario cards with branches → would need new visualization code for MC distributions
- `renderAccuracy()` in `dashboard.js` (lines 790+) → plan adds "before/after calibration" section

The plan listed 10 files. The dependency graph showed **16 surfaces**.

### 3. Build the blast-radius table

| # | Surface | File(s) | What changes | Blast radius |
|---|---------|---------|-------------|-------------|
| 1 | New MC Engine | `src/monte_carlo.py` (new) | Core simulation engine | **New file, no deps** |
| 2 | Pipeline ScenarioSimulator | `src/pipeline.py` | Replace stub with MC call | Medium — CLI-only |
| 3 | API scenarios endpoint | `src/api/routes/scenarios.py` | Replace/augment deterministic branches | **High** — dashboard-facing |
| 4 | Injury scenario generator | `src/services/probabilities.py` | Augment with MC outputs | **High** — schedule + scenarios |
| 5 | API models | `src/api/models.py` | New MC result shape | Medium |
| 6 | Frontend scenarios view | `ui/js/dashboard.js` | New visualizations (violin/box plots) | **High** |
| 7 | Frontend accuracy view | `ui/js/dashboard.js` | New calibration section | Medium |
| ... | ... | ... | ... | ... |

### 4. Flag conflation and parameter mismatches

**Conflation:** Plan says "replace scenarios." But the API scenarios (injury-driven branches with player names, narrative descriptions) answer a *different question* than MC distributions. One says "what specific events could shift this?" The other says "what's the range of outcomes?" The plan should augment, not replace.

**Parameter mismatch:** Plan lists K-factor as a tunable parameter. But the engine is Glicko-2 — it uses tau/sigma/phi, not K-factor. The actual tunable constants in `constants.py` are `INJURY_SEVERITY_MULTIPLIER`, `STARTER_SCORE_WEIGHT`, `BULLPEN_SCORE_WEIGHT`, `HOME_FIELD_ADVANTAGE`, `DRAW_RATES`. The plan's parameter grid doesn't match reality.

### 5. Propose phased scoping

- **Phase A (low risk, ~3-4 hrs):** New `monte_carlo.py`, replace pipeline stub, `simulate_game()` on engine, CLI command, tests. No user-facing surfaces touched.
- **Phase B (higher risk, ~6-8 hrs):** Pre-computed MC distributions, augment API scenarios, frontend visualizations, admin calibration page. All user-facing.

## Key Principle

The plan's file list is the author's aspiration. The dependency graph is reality. Always trace the graph.
