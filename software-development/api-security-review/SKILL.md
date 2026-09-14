---
name: api-security-review
description: "API code review: TOCTOU, IDOR, identifier-normalization lockout, nosniff, FK, zod bounds."
version: 1.0.0
metadata:
  hermes:
    tags: [api, security, code-review, backend, hono, drizzle, postgresql]
    related_skills: [requesting-code-review, subagent-driven-development, github-code-review]
---

# API Security Review

Proven security and quality findings from multi-phase backend API code reviews. Use as the code-quality reviewer's checklist when dispatching review subagents for any HTTP API implementation, or as a self-review checklist before committing API routes.

## When to Use

- Dispatching a code-quality reviewer subagent for API route implementations
- Self-reviewing API code before commit (pairs with `requesting-code-review`)
- Reviewing subagent-produced API code (subagents consistently miss these patterns)
- Adding new CRUD endpoints, file upload/streaming, or batch operations

## The Checklist

### CRITICAL — Must fix before merge

#### 1. TOCTOU Race on Check-Then-Act

**Pattern:** App-level conflict/existence check followed by INSERT/UPDATE without a transaction. Two concurrent requests both pass the check → DB constraint violation → generic 500 instead of semantic 409.

**Detection:** `SELECT ... WHERE <conflict>` followed by `INSERT`/`UPDATE` on the same table, NOT in `db.transaction()`.

**Fix:** Wrap in transaction + catch PG error codes as safety net:
```typescript
try {
  await db.transaction(async (tx) => {
    const conflict = await tx.select().from(table).where(...).limit(1);
    if (conflict.length > 0) throw new Error("CONFLICT");
    await tx.insert(table).values(...);
  });
} catch (err) {
  if (err.message === "CONFLICT") return c.json({ error: "taken" }, 409);
  if ((err as any).code === "23505") return c.json({ error: "taken" }, 409);
  throw err;
}
```

**Key insight:** The DB unique index is the safety net, but the app MUST catch 23505 and return a semantic HTTP status. Without the catch, concurrent conflicts produce opaque 500s.

#### 1b. Identifier-Normalization Asymmetry Across Endpoints (auth lockout)

**Pattern:** One endpoint normalizes a unique identifier before storing it, but a *sibling* endpoint that looks the same identifier up does NOT apply the same normalization. The mismatch silently locks users out or creates phantom duplicates.

**Canonical case — email:** registration does `email.trim().toLowerCase()` before INSERT, but login queries `WHERE email = <raw input>`. Postgres `text` equality is **case-sensitive** (a plain `text` column is NOT `citext`). A user who registers `Foo@x.com` (stored `foo@x.com`) then logs in as `Foo@x.com` gets **401 invalid credentials** — permanent lockout despite a correct password. Any uppercase at login breaks login.

**Detection:** grep every read/write of a unique identifier (email, username, phone, slug). If ANY site normalizes (lower/trim/case-fold) and another site on the same column does not, that's the bug. Check the column type — `text`/`varchar` are case-sensitive; only `citext` or an explicit `LOWER()` functional index folds case.

**Fix:** extract ONE `normalizeEmail()` (or equivalent) helper and call it at **every** site that reads or writes the identifier — register, login, password-reset, "is this taken?" checks, admin lookups. Don't normalize in only the write path.
```typescript
// Emails are stored lowercase; normalize on BOTH register and login so a user
// who types "Foo@x.com" can still log in (Postgres text equality is case-sensitive).
function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}
```

**Key insight:** This is invisible in single-endpoint review — each endpoint looks correct in isolation. The bug only exists in the *asymmetry between* endpoints. Reviewers must compare the identifier handling across the register/login/reset trio explicitly, not review each route in a vacuum.

#### 2. IDOR — Auth ≠ Authorization

**Pattern:** Endpoint requires authentication (`requireAuth`) but doesn't check resource ownership. Any authenticated user can view/modify any resource by ID.

**Detection:** Any `GET/PATCH/DELETE /api/<resource>/:id` with `requireAuth` but NOT `requireAdmin`, and no `resource.ownerId === session.memberId` check.

**Especially dangerous on:** photo/file streaming endpoints — these often get `requireAuth` but skip ownership checks.

**Fix:**
```typescript
if (user.role !== "admin" && row.memberId !== c.get("memberId")) {
  return c.json({ error: "forbidden" }, 403);
}
```

#### 2b. SSRF — DNS-Rebinding TOCTOU in External URL Fetch

**Pattern:** Endpoint fetches a user-supplied URL (site analysis, link previews, image proxies, webhook validation). The naive "safe" implementation resolves the host, validates the IP is public, then calls `fetch(url)` — but `fetch()` re-resolves the hostname internally, so a hostile DNS can answer a public IP to the validator and a private/metadata IP to the actual request.

**Detection:** Any route that fetches a URL from the client where the validation and the connection are separate DNS lookups.

**Fix — pin the connection to the validated IP:** resolve → validate → then connect via `node:http`/`node:https` with `host: <validatedPublicIp>`, `headers: { Host: <originalHost> }`, and `servername: <originalHost>` (https only, preserves SNI + cert validation). Manual redirect loop (max ~4) that re-resolves and re-validates each hop. Full construction pattern + Node gotchas: `references/ssrf-safe-fetching.md`.

**Node gotchas that slip past reviewers:**
- `URL.hostname` keeps brackets on IPv6 (`new URL("http://[::1]:8080/").hostname === "[::1]"`) — strip before `net.isIP()`.
- `dns.lookup` doesn't resolve literal IPs — short-circuit literals through `net.isIP()` + private-range check instead of DNS.
- WHATWG URL parsing normalizes IPv4-mapped IPv6 to **hex** form (`http://[::ffff:127.0.0.1]/` → hostname `::ffff:7f00:1`) — a `::ffff:` branch that only decodes dotted form misses it.

### HIGH — Should fix before merge

#### 3. Missing `X-Content-Type-Options: nosniff` on Binary Responses

Without `nosniff`, browsers may MIME-sniff a disguised upload (HTML renamed to `.png`) and execute it. Always include on `new Response(stream, ...)` for file serving.

#### 4. Unhandled FK Violations → Generic 500

Accepting a UUID FK reference via `z.string().uuid()` without checking the target row exists. A valid-format UUID that doesn't exist throws PG 23503 → generic 500.

**Fix:** Pre-check existence (return 404) or catch 23503.

#### 5. Zod Schemas Without Upper Bounds

`z.number().int().min(1)` with no `.max()` allows `qty: 2_000_000_000`. Always set: `.max(1000)` for quantities, `.max(10_000_00)` for money-in-cents, `.max(200)` for names.

### MEDIUM — Fix when convenient

#### 6. Path Traversal Guard

Even with server-generated filenames, add `path.resolve()` + `startsWith(UPLOAD_DIR)` as defense-in-depth.

#### 7. Photo Utility Duplication

`validatePhoto()`, MIME map, `ALLOWED_PHOTO_EXTS`, `MAX_UPLOAD_BYTES`, streaming pattern duplicated across 3+ route files. Extract to shared `utils/photos.ts`.

#### 8. Non-Atomic Batch Generation

Sequential per-row inserts in a loop. Use `INSERT ... ON CONFLICT DO NOTHING` (Drizzle `.onConflictDoNothing()`) for idempotent batch operations.

#### 9. Timestamp Overwrite on Re-Delivery

Unconditionally stamping `deliveredAt = new Date()` on every status change. Guard: only set if existing value is null.

## Reviewer Dispatch Template

Include this in the code-quality reviewer's context when reviewing API routes:

```
CHECK THESE API-SPECIFIC PATTERNS:
1. TOCTOU: any check-then-insert/update NOT in a transaction? → CRITICAL
1b. Identifier-normalization asymmetry: does register lowercase/trim an email (or username/phone) but login/lookup query it raw? (Postgres text is case-sensitive → lockout) → CRITICAL
2. IDOR: any :id endpoint with requireAuth but no ownership check? → CRITICAL
2b. SSRF: any endpoint fetching a user-supplied URL — is the connection PINNED to a validated public IP (DNS-rebinding proof), are redirects re-validated per hop, is the body size-capped? → CRITICAL
3. nosniff: any binary streaming response without x-content-type-options? → HIGH
4. FK validation: any UUID FK accepted without existence check? → HIGH
5. Zod bounds: any min() without max()? → HIGH
6. Path traversal: any path.join without resolve+startsWith guard? → MEDIUM
7. Photo duplication: validatePhoto/MIME/streamPhoto copy-pasted across files? → MEDIUM
8. Batch atomicity: sequential inserts in loop instead of ON CONFLICT? → MEDIUM
9. Timestamp overwrite: unconditional deliveredAt/updatedAt stamp? → MEDIUM

Return findings as: | # | Severity | File:Line | Issue | Fix |
```

## Pitfalls

- **Subagents consistently miss items 1–5.** They implement the happy path correctly but skip concurrent-access handling, ownership checks, and response headers. Always include this checklist in the reviewer prompt, not just the implementer prompt.
- **The DB constraint is necessary but not sufficient.** A partial unique index catches double-bookings at the DB level, but without an app-level 23505 catch, the user sees a 500 instead of a 409. Both layers are required.
- **`requireAuth` feels like authorization but isn't.** It proves identity, not permission. Every non-admin endpoint that accesses a specific resource by ID needs an ownership check.
- **Photo streaming is the most commonly missed IDOR surface.** File-serving endpoints feel "read-only" and "safe" so reviewers skip them, but they expose private uploads (proof-of-delivery photos, user documents) to any authenticated user.

## Provenance

Distilled from Phase 4 (Table Reservations) and Phase 5+5b (Orders, Deliveries, Menu) code reviews on the Pampa Wine Club project (2026-07-31). Phase 4 review found 3 CRITICAL + 4 HIGH; Phase 5+5b review found 1 HIGH + 4 MEDIUM. Item 1b (identifier-normalization lockout) added from the Phase 7 (member portal + self-signup) review on 2026-08-01 — the quality reviewer caught a register-lowercases-but-login-doesn't email bug that would have locked out any user who typed uppercase at login. All patterns above were real findings that required code fixes before deployment.
