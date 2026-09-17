# Prose-Claim Verification (Pitfall 11)

When a subagent delivers PROSE about a system (docs, specs, API references, architecture
write-ups, analysis), the deliverable can exist, be well-formatted, and read confidently
while containing wrong *factual claims*. Verify the claims against source before accepting.

## What to extract and verify

| Claim type | Example | Verify with |
|------------|---------|-------------|
| Counts | "12 tables", "45 endpoints", "9 tabs" | `grep -c <pattern> <source>` |
| Identifiers | table/field/route/env-var/function names | grep the schema / routes / config |
| Behaviors | "returns 403", "sets HttpOnly", "defaults to false" | read the actual handler / code |
| Business rules | "single=2 bottles", "paid is manual" | read the implementing function |
| Config values | cookie flags, TTLs, bootstrap env vars | read the config/auth source |

## Pass procedure

1. Skim the deliverable; list every concrete, checkable assertion (numbers, names,
   status codes, flags, defaults, rule values).
2. For each HIGH-LEVERAGE claim (easy to get wrong from a partial read AND would mislead a
   future reader), run the matching check against source. Do not re-derive from the prose.
3. Skip verifying prose *phrasing* — only the facts can be silently wrong.
4. If any claim fails, the deliverable is not trustworthy as-is: fix the specific claim
   (parent, surgical patch) or re-dispatch with the correction named.

## Grounding prompts (raise hit-rate, don't replace verification)

- "Read the actual source before writing; do NOT carry forward the stub's numbers/names."
- "List the real table/endpoint/route names from `<source file>`, not from memory."
- "Report every place where the code contradicts the existing text."

## Real case (Pampa, 2026-08-01)

Subagent filled two placeholder contract docs. Parent verified: schema table count
(`grep -c pgTable` → 12, stub had said 8), allotment logic (`couple ? 3 : 2`), `paid`
boolean default, cookie flags (`HttpOnly; SameSite=Lax`, `Secure` only in prod),
register→409 + `active:false`, delivery-photo IDOR→403, `/admin` route + `/club`→`/admin`
redirect, `ADMIN_EMAIL`/`ADMIN_BOOTSTRAP_PASSWORD` bootstrap vars. All correct — verification
is what made the deliverable safe to commit.
