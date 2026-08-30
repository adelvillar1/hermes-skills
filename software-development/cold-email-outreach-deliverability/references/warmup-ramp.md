# Warmup Ramp

A brand-new sending subdomain has **zero reputation**. Sending the full list in week 1
gets you flagged as spam regardless of list quality. Ramp daily volume over ~5 weeks.

## Schedule

| Week | Days since first | Max/day | Cumulative |
|------|------------------|---------|------------|
| 1 | 0-6 | 20 | 140 |
| 2 | 7-13 | 50 | 490 |
| 3 | 14-20 | 100 | 1,190 |
| 4 | 21-27 | 250 | 2,940 |
| 5+ | 28+ | 500 | 6,440+ |

At 500/day steady state, a 12K queue takes ~24 sending days. Slow sending = high
deliverability = more replies. That's the whole point.

## Enforce in code, not via env var

**Critical:** compute the cap from the first-send date in code. Do NOT let an env var
like `CAMPAIGN_DAILY_LIMIT=10000` override the ramp — a user (or a cron misconfig)
will torch the domain on day 1.

```ts
function rampMaxForDay(daysSinceFirst: number): number {
  if (daysSinceFirst <= 6) return 20;
  if (daysSinceFirst <= 13) return 50;
  if (daysSinceFirst <= 20) return 100;
  if (daysSinceFirst <= 27) return 250;
  return 500;
}

// First-send date from the run log
const firstRun = await prisma.$queryRaw`
  SELECT started_at FROM leads.run_log
  WHERE job_name = 'lead_campaign' ORDER BY started_at ASC LIMIT 1`;
const daysSinceFirst = firstRun.length === 0 ? 0
  : Math.floor((Date.now() - new Date(firstRun[0].started_at).getTime()) / 86_400_000);

const rampMax = rampMaxForDay(daysSinceFirst);

// Per-day cap: subtract what's already sent today
const alreadySentToday = /* count send_log rows for this campaign where sent_at >= today */;
const remainingToday = Math.max(0, rampMax - alreadySentToday);

// Effective limit is the MIN of all constraints — ramp can never be exceeded
const effectiveLimit = Math.min(envDailyLimit, rampMax, limitFlag, remainingToday);
```

The `Math.min` with `rampMax` is the load-bearing line — it makes the ramp a hard
ceiling that no env var or flag can lift.

## Reply-rate reality check

Cold outreach reply rates are 1-3% regardless of send speed. Sending 12K over 5 weeks
vs 4 weeks means replies trickle in over 5 vs 4 weeks — you're not closing deals
faster. If you get 0 replies from ~500 sends, the messaging is the problem, not the
volume. Fix copy before scaling.
