# Cross-Source ID Format Mismatch Debugging

> When a system has multiple data sources that each produce IDs for the same entity type, silent ID format mismatches cause features to degrade without errors.

## The Pattern

A feature works in isolation (unit tests pass, backfill script produces correct data) but fails in production because two data sources use different ID formats for the same entity. The lookup silently returns nothing, and the system falls back to a default behavior with no error.

## Detection

1. **Query both sources** for the same entity type and compare ID formats
2. **Check overlap**: join on IDs — if zero rows, you have a mismatch
3. **Trace the creation path** for each source — normalizer, API response, backfill script, pipeline

## Common Mismatch Patterns

| Pattern | Example | Fix |
|---------|---------|-----|
| Prefix difference | `"669432"` vs `"mlb-669432"` | Normalize to one format |
| Name vs numeric | `"trevor-rogers"` vs `"mlb-669432"` | Use numeric ID, not name |
| Case difference | `"NYM"` vs `"nym"` | Normalize to uppercase |
| Delimiter difference | `"la-liga"` vs `"la_liga"` | Standardize delimiter |

## Real Example (2026-06-09, MLB Pitchers)

**Symptom:** Pitcher-aware engine producing identical probabilities to team-only engine. 267 pitcher ratings existed. No errors.

**Root cause:** Three different ID formats:
- Schedule: `"669432"` (raw ESPN numeric)
- Ratings: `"mlb-642547"` (mlb-{espn_id} from backfill)
- Probability function: `"trevor-rogers"` (mlb-{name})

Zero overlap → every game fell back to team-only mu.

**Fix:** Updated function to prefer `starter["id"]` → `f"mlb-{id}"`. Result: 66/69 matched (96%).

**Prevention:** After implementing any player-level engine, join schedule IDs with rating IDs and assert overlap > 0.
