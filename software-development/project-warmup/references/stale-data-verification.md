# Stale Data Verification

This reference file documents the pattern for verifying dynamic data before reporting it as fact in session warmups or plan reviews.

## The Problem

Static snapshot files (`docs/STATE-SNAPSHOT.md`, dated entity counts in plans, etc.) go stale within days. Reporting stale counts as current state causes:
- Incorrect "blocked" assessments (e.g., "T6 still running" when it finished)
- Wrong prioritization decisions
- User frustration at having to correct basic facts

## Detection Pattern

Before reporting any of these as current state, verify with a live query:

| Data source | Snapshot file | Live query |
|-------------|--------------|------------|
| Table row counts | `docs/STATE-SNAPSHOT.md` | `SELECT COUNT(*) FROM table_name` |
| Backfill completion % | Plan frontmatter (`updated:`) | `SELECT COUNT(*) FROM insight_table WHERE narration IS NOT NULL` |
| Feature flag state | `docs/RAILWAY-ENV-VARS.md` | `railway variables -e <env> --kv` |
| Deployment counts | `docs/STATE-SNAPSHOT.md` | `SELECT COUNT(*) FROM ship_deployments` |
| Environment parity | CLAUDE.md "All environments in sync" | `railway deployment list` diff |

## Verification Query Template

For PostgreSQL on Railway:
```bash
psql "$STAGING_DB" -At -F'\t' -c "
SELECT 'table_name', COUNT(*) FROM table_name;
"
```

If `$STAGING_DB` is not set, read the connection string from `CLAUDE.local.md` or the environment-specific URL from the project's local reference file.

## Decision Tree

When a plan/status file claims a number or completion status:
1. **If the file has an explicit `updated:` or timestamp** — verify if it's within the last 24h. If not, assume stale.
2. **If the claim is about row counts, backfill progress, or deployment state** — always run a live query unless the user explicitly told you the number is current.
3. **If the claim is about feature flags or environment variables** — query the live environment rather than trusting any file.
4. **If the claim matches a recent session recap** (e.g., "T6 done per 2026-04-30 recap") — this is higher-trust than a static snapshot. Cross-reference the recap with a live query for critical decisions.

## When to Skip Verification

- The user explicitly stated the number in the same turn (you don't need to re-verify what they just told you)
- The data is clearly a hardcoded config (e.g., `regions: 24` — this changes only when a new region is added by a human developer, not by a pipeline)
- The data is from a `.env.example` or documented constant

## Example of Correct vs Incorrect Handling

**Incorrect:**
> T6 is in progress (~400K cells, 48–60h ETA per docs/STATE-SNAPSHOT.md)
> → Source is an untrusted 3-week-old snapshot. Never report this as fact.

**Correct:**
> Let me verify current T6 status before reporting... [runs query] T6 is 415,088 rows with narration / 415,098 total = effectively 100% complete.
> → Verified from live database. Confident reporting.

---

## Git Log Verification (Post-Recap Work)

Recaps are written at a point in time but work continues. Always check for commits after the latest recap:

```bash
# Get the latest recap's modification time
LATEST=$(ls -t docs/recaps/SESSION-RECAP-*.md 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  RECAP_DATE=$(date -r "$LATEST" "+%Y-%m-%d %H:%M" 2>/dev/null || stat -f "%Sm" "$LATEST")
  echo "=== Post-recap commits (since $RECAP_DATE) ==="
  git log --since="$RECAP_DATE" --oneline -30
fi
```

**What to look for:**

| Recap open item | Matching commit pattern | Status |
|-----------------|------------------------|--------|
| "Port description backfill" | `feat: backfill port descriptions on prod` | ✅ Resolved |
| "Scraper-worker redeploy" | `fix: ... scraper ...` or `feat: trigger pipeline` | ✅ Potentially resolved |
| "Raw SQL audit" | No matching commit | ❌ Still open |
| "Any item" | No commits since latest recap | ❓ Can't verify — assume still open |

**Common mistake:** Reading only the recap's "Open questions" section and the CLAUDE.md "Today's state" section without checking git log. A long workday may produce 15+ commits after the recap was written. Skipping this step means you present stale state to the user, who then has to correct you — the exact source of frustration this file exists to prevent.

---

## Related

- `docs/STATE-SNAPSHOT.md` refresh protocol: defined in CLAUDE.md housekeeping section. Should be refreshed after:
  - Any pipeline run (scraper-worker, insight backfill)
  - Monthly hygiene pass
  - When the agent notices the snapshot is >1 week old during any session
