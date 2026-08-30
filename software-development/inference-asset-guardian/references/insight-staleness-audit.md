# Insight Table Staleness Audit Template

Reusable SQL audit for any insight table stack. Run on **staging** (NOT production). Produces a per-table classification across four failure modes (orphan FK, prompt version rot, coverage gap, dead table). The pattern generalizes — substitute table/anchor names for any insight domain.

## The four-failure-mode framework

| Mode | Diagnostic | Why it matters |
|---|---|---|
| **A. Orphan FK rows** | `<fk_col> NOT IN (SELECT id FROM <anchor>)` count > 5% | Stale rows pointing at deleted anchors. Wastes storage, confuses metrics. |
| **B. Prompt version rot** | `DISTINCT prompt_version` returns >1, OR oldest is stale | Mixed-version rows or all-stale-version tables. Means latest generation never ran here. |
| **C. Coverage gap** | anchors in PG with no insight row at all | Different from orphans — these are current-world anchors with no insight. Backfill needed. |
| **D. Dead table** | zero consumers in code (grep -r table name), OR superseded by another table | Old tables not yet physically dropped. Truncate for hygiene. |

## Template SQL

```sql
-- ========================================================================
-- Insight table staleness audit. Edit table/anchor names per your domain.
-- Output: one row per table with columns: total, valid, orphan, pct_valid,
--         active, deprecated, plus per-table notes where applicable.
-- ========================================================================

\echo '========== <table_label> =========='
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE <fk_col> IN (SELECT id FROM <anchor>)) AS valid,
  count(*) FILTER (WHERE <fk_col> NOT IN (SELECT id FROM <anchor>)) AS orphan,
  round(100.0 * count(*) FILTER (WHERE <fk_col> IN (SELECT id FROM <anchor>)) / count(*), 1) AS pct_valid,
  count(*) FILTER (WHERE deprecated_at IS NULL) AS active,
  count(*) FILTER (WHERE deprecated_at IS NOT NULL) AS deprecated
FROM <insight_table>;
```

## Reference run: T1–T7 audit on staging (2026-07-13)

The complete audit that surfaced three new cleanup plans. All numbers are from staging on 2026-07-13. Copy and adapt.

### 1. `corridor_profiles` (T1+T3+T5 consolidated, current)

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors)) AS valid_corridor,
  count(*) FILTER (WHERE corridor_id NOT IN (SELECT id FROM route_corridors)) AS orphan_corridor,
  round(100.0 * count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors))/count(*), 1) AS pct_valid
FROM corridor_profiles;

-- Coverage gap: distinct valid corridors vs total route_corridors
SELECT count(DISTINCT corridor_id) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors)) AS have_profile,
       (SELECT count(*) FROM route_corridors) AS total_corridors,
       (SELECT count(*) FROM route_corridors WHERE id NOT IN (SELECT corridor_id FROM corridor_profiles)) AS missing_profile
FROM corridor_profiles;
```

**Expected result (staging 2026-07-13):** total=24,627, valid=14,132 (57.4%), orphan=10,495, missing=486 corridors (mostly "Repositioning 0-Port").

**Verdict:** Mode A (orphan) + Mode C (coverage gap). Same orphan set as `corridor_dep_hashes`.

### 2. `corridor_insights` (LEGACY T1/T3/T5)

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE deprecated_at IS NULL) AS active,
  count(*) FILTER (WHERE deprecated_at IS NOT NULL) AS deprecated,
  round(100.0 * count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors))/NULLIF(count(*),0), 1) AS pct_valid
FROM corridor_insights;
```

**Expected result (staging 2026-07-13):** total=6,600, active=6,600 (none deprecated!), pct_valid=98.6%.

**Verdict:** Mode D (dead). Schema comment says superseded by `corridor_profiles` since 2026-05-17, but DB shows 6,600 still alive. **Doc-state vs DB-state disagreement** — trust DB.

### 3. `corridor_upgrade_insights` (T2)

Two-FK audit (source + target):

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE source_corridor_id NOT IN (SELECT id FROM route_corridors)) AS stale_source,
  count(*) FILTER (WHERE target_corridor_id NOT IN (SELECT id FROM route_corridors)) AS stale_target,
  count(*) FILTER (WHERE source_corridor_id IN (SELECT id FROM route_corridors)
                     AND target_corridor_id IN (SELECT id FROM route_corridors)) AS valid_both,
  round(100.0 * count(*) FILTER (WHERE source_corridor_id IN (SELECT id FROM route_corridors)
                                   AND target_corridor_id IN (SELECT id FROM route_corridors))/count(*), 1) AS pct_valid
FROM corridor_upgrade_insights;

-- Per-definition breakdown
SELECT definition_id, count(*) AS rows,
  count(*) FILTER (WHERE source_corridor_id IN (SELECT id FROM route_corridors)
                  AND target_corridor_id IN (SELECT id FROM route_corridors)) AS valid_both
FROM corridor_upgrade_insights
GROUP BY definition_id;
```

**Expected result (staging 2026-07-13):** total=51,246, valid_both=13,184 (25.7%), three definitions (`nearest_cabin_score_tier_step`, `overlapping_ports_tier_step`, `same_region_tier_step`) all ~25% valid. Single prompt_version `t2@4.0.0-season-agnostic+personas@1.1.0`.

**Verdict:** Mode A (severe orphan) + Mode B (single 1.1.0 version, no 1.2.0 anywhere).

### 4. `corridor_family_insights` (T4)

**Schema gotcha**: `family_id` is `text` and references DIFFERENT tables per `family_grouping`. Generic single-block audit fails (returns 0 valid for clan/region rows).

```sql
-- Per-grouping breakdown with the right join for each.
SELECT cfi.family_grouping,
  count(*) AS rows,
  count(*) FILTER (WHERE ft.family_id IS NOT NULL) AS valid_ref,
  count(*) FILTER (WHERE ft.family_id IS NULL) AS orphan_ref
FROM corridor_family_insights cfi
LEFT JOIN family_topology ft ON ft.family_id = cfi.family_id
GROUP BY cfi.family_grouping
ORDER BY cfi.family_grouping;

-- Region grouping: heterogeneous IDs (UUIDs and slugs mixed). Validate against regions.
SELECT cfi.family_id,
  case when r.id::text = cfi.family_id then 'valid (uuid)'
       when r.slug = cfi.family_id then 'valid (slug)'
       else 'orphan' end as status
FROM corridor_family_insights cfi
LEFT JOIN regions r ON r.id::text = cfi.family_id OR r.slug = cfi.family_id
WHERE cfi.family_grouping='region';

-- Clan grouping: FK target is currently unknown. Result of audit:
-- 57 rows, all orphans against `route_clans.slug` and `family_topology.family_id`.
-- Needs further investigation; do NOT trigger Phase-1 deprecation yet.
```

**Expected result (staging 2026-07-13):**
- family: 4,540 rows, 4,536 valid (99.9%)
- super_family: 2,095 rows, 1,869 valid (89.2%; 226 orphans)
- region: 23 rows, all valid against regions table
- clan: 57 rows, **0 valid against known FK targets** — needs investigation

**Verdict:** Mode A (mild; 226 super_family orphans) + Mode D investigation (clan rows have no clear FK target).

### 5. `corridor_value_density` (T5 derived)

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors)) AS valid_corridor,
  count(*) FILTER (WHERE corridor_id NOT IN (SELECT id FROM route_corridors)) AS orphan_corridor,
  round(100.0 * count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors))/count(*), 1) AS pct_valid
FROM corridor_value_density;

WITH universe AS (SELECT id FROM route_corridors),
     have AS (SELECT corridor_id FROM corridor_value_density)
SELECT
  (SELECT count(*) FROM universe) AS total_corridors,
  (SELECT count(*) FROM have) AS corridors_with_value_density,
  (SELECT count(*) FROM universe WHERE id NOT IN (SELECT corridor_id FROM have)) AS corridors_missing_value_density;
```

**Expected result (staging 2026-07-13):** total=10,432, valid=10,432 (100%), but coverage only 71.4% (10,432/14,618 corridors).

**Verdict:** Clean orphan-wise (Mode A: 0%); Mode C partial coverage. Cheap coverage-fill (derived computation, no LLM cost).

### 6. `corridor_seasonal_profiles`

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE corridor_id IN (SELECT id FROM route_corridors)) AS valid_corridor,
  count(*) FILTER (WHERE corridor_id NOT IN (SELECT id FROM route_corridors)) AS orphan_corridor,
  count(DISTINCT corridor_id) AS distinct_corridor_ids
FROM corridor_seasonal_profiles;
```

**Expected result (staging 2026-07-13):** total=10,000, valid=10,000 (100%), 1,380 distinct corridor IDs (9.4% coverage).

**Verdict:** Clean orphan-wise but Mode C massive coverage gap. Fill 13,238 missing `corridor × season` cells.

### 7. `cruise_line_insights` (T7)

```sql
SELECT
  count(*) AS total,
  count(*) FILTER (WHERE cruise_line_id IN (SELECT id FROM cruise_lines WHERE status='active')) AS valid_active_line,
  count(*) FILTER (WHERE cruise_line_id IN (SELECT id FROM cruise_lines)) AS valid_any_line,
  count(*) FILTER (WHERE cruise_line_id NOT IN (SELECT id FROM cruise_lines)) AS orphan_line,
  (SELECT count(*) FROM cruise_lines WHERE status='active') AS active_cruise_lines_in_db
FROM cruise_line_insights;
```

**Expected result (staging 2026-07-13):** total=49, valid_active=49, orphan=0. **49 active lines, 49 insights — perfect 1:1.**

**Verdict:** Clean. The model citizen. No action.

### Cross-cutting checks

```sql
-- 1. orphan_corridor_id overlap between corridor_profiles and corridor_dep_hashes
WITH profile_orphans AS (
  SELECT DISTINCT corridor_id FROM corridor_profiles
  WHERE corridor_id NOT IN (SELECT id FROM route_corridors)
),
hash_orphans AS (
  SELECT DISTINCT corridor_id FROM corridor_dep_hashes
  WHERE corridor_id NOT IN (SELECT id FROM route_corridors)
)
SELECT
  (SELECT count(*) FROM profile_orphans) AS profile_only,
  (SELECT count(*) FROM hash_orphans) AS hash_only,
  (SELECT count(*) FROM profile_orphans po
   JOIN hash_orphans ho ON po.corridor_id = ho.corridor_id) AS both;

-- 2. prompt version diversity per table
SELECT '<table_name>' AS tbl, prompt_version, count(*)
FROM <table_name>
GROUP BY prompt_version;

-- 3. T6 baseline (for sanity check that other tables follow the same pattern)
SELECT persona_id,
  count(*) FILTER (WHERE deprecated_at IS NULL) AS active,
  count(*) FILTER (WHERE deprecated_at IS NOT NULL) AS deprecated,
  round(100.0 * count(*) FILTER (WHERE deprecated_at IS NULL) / 18980.0, 1) AS pct_of_pg_universe
FROM ship_corridor_insights
GROUP BY persona_id
ORDER BY persona_id;
```

## Output parsing rules

| pct_valid | active/total ratio | Diagnosis | Recommended action |
|-----------|-------------------|-----------|-------------------|
| < 50% | any | Mode A severe | Phase-1 deprecate plan (mirror T6 plan) |
| 50–80% | any | Mode A moderate | Same as above |
| 80–100% | active < total - deprecated | Mode A partially cleaned | Verify the cleanup ran fully |
| 80–100% | active = total | Mode B or C possible | Check `DISTINCT prompt_version` + coverage gap queries |
| 100% | active = total | Possibly Mode C only | Coverage-fill only |
| any | active = 0 | Mode D (empty/dead) | Consider TRUNCATE |
| any | table ≈ count(anchor_table) | T7-style clean | No action |

## Documentation-vs-DB hygiene

**Always re-verify doc-state against DB-state before quoting counts.** STATE-SNAPSHOT.md claimed `corridor_insights` was TRUNCATED; the audit showed 6,600 rows still alive. Document rot is silent.

## Audit cadence

Run this audit:
- After every monthly pipeline run (gate on insight stability)
- Before kicking off any Phase-2 multi-persona LLM campaign
- On user request ("are other insights stale?")
- Annually as part of platform health review

## Reference

For the full T1–T7 staleness plan context, see `docs/plans/2026-07-10-t6-staleness-cleanup-and-cross-persona-backfill.md` and `docs/recaps/SESSION-RECAP-2026-07-12-t6-staleness-cleanup-and-phase2-backfill.md`. §23 of `inference-asset-guardian` introduces this audit pattern.
