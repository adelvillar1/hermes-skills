# Stale Data Verification

How to verify dynamic data before reporting it as fact in session warmups or plan reviews.

## The Problem

Static snapshot files (`docs/STATE-SNAPSHOT.md`, dated entity counts in plans, etc.) go stale within days. Reporting stale counts as current state causes incorrect assessments and wrong prioritization.

## The Pattern

1. **Identify the data point** — is it a live count (active itineraries, ships, etc.) or a static note?
2. **If live, query the source** — run a DB query, curl an API endpoint, or check the running service
3. **If static, note the date** — include the snapshot date when presenting counts
4. **Prefer git log over memory** — commit messages tell you what actually shipped

## DB Query Examples

```bash
# Count active records
DATABASE_URL="<connection_string>" npx tsx -e "
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();
const count = await prisma.ship.count({ where: { isActive: true } });
console.log({ count });
"
```

## Cross-Environment Verification

For deployment-related data (staging vs production), always verify both:

```bash
# Check staging
DATABASE_URL="$STAGING_DB" npx prisma db execute --stdin <<< "SELECT count(*) FROM ships;"
# Check production
DATABASE_URL="$PROD_DB" npx prisma db execute --stdin <<< "SELECT count(*) FROM ships;"
```

The delta between environments is often more informative than either count alone.
