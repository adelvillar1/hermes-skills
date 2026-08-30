---
name: zod-schema-patterns
description: "Use when writing or extending shared zod validation schemas."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [zod, validation, typescript, schemas, dto]
    related_skills: [bilateral-api-contracts, api-security-review, monorepo-typescript-verification]
---

# Zod Schema Patterns

Authoring and extending zod DTO/validation schemas shared between web and api workspaces. House invariant across projects: **every endpoint zod-validated**, schemas live in a shared package consumed by both sides. Covers the house DTO conventions, the zod v4 refine API (which differs from v3), strip-then-validate + checksum refines, cross-field object checks, and throwaway-tsx-probe verification.

## When to use

- Adding request/response DTOs to a shared package (`@*/shared`, `packages/shared`, `shared/src`)
- Adding validation with `.refine` / cross-field checks — especially under zod v4, whose refine-params API differs from v3
- Implementing checksum or format validation (card numbers, IDs, codes) inside a schema

## Step 0 — Find the REAL home before writing

Plans and even project docs (AGENTS.md) can name a file that does not exist. Before adding schemas:

1. List the shared package's actual files (`search_files` / `ls shared/src`).
2. Read the package entry (`shared/src/index.ts`) and match its exact conventions: declaration style, export style, section headers.
3. If the plan named a missing file (e.g. plan says `shared/src/schemas.ts`, reality is everything in `shared/src/index.ts`), extend the real home — never create the plan-named file just to satisfy the text. Flag the mismatch in your summary. (Real case 2026-08-15: both the member-card-vault plan and AGENTS.md named a nonexistent `shared/src/schemas.ts`; the DTOs went into `shared/src/index.ts`.)

Also check how the package is consumed: if `package.json` `main`/`exports` point at `./src/*.ts` (no build step), per-workspace `npx tsc --noEmit -p <ws>` is the full type gate. If they point at `dist/`, consumers need a rebuild after schema changes (see `monorepo-typescript-verification`).

## House conventions (match what's already there)

Observed conventions in existing shared packages — copy them, don't invent:

- `export const XSchema = z.object({...});` followed by `export type X = z.infer<typeof XSchema>;`
- Section headers as comments: `// ---- Members ----`
- Double quotes, semicolons, brief doc comments (`/** ... */`) for non-obvious shapes
- Plain TS types (not zod infer) for response shapes that have no matching schema — precedent: `export type EventWine = { ... }`

## zod v4 API facts (verified against zod 4.3.5, 2026-08-15)

v4 refine signature: `refine(check, params?: string | $ZodCustomParams)` — the second arg is either a message string or a params object. The params object accepts (from `$ZodCustomDef`):

- `error` — the preferred message key in v4
- `message` — still works but officially deprecated ("Use `error` instead")
- `path` — `PropertyKey[]`, sets the issue path (critical for object-level refines)
- `params` — freeform `Record<string, any>`

Key recipes:

```typescript
// String message shorthand works:
z.string().refine(fn, "failure message");

// Cross-field check lives on the OBJECT; report it against one field:
z.object({ expiryMonth: ..., expiryYear: ... }).refine(
  (v) => v.expiryYear > now.getFullYear() ||
    (v.expiryYear === now.getFullYear() && v.expiryMonth >= now.getMonth() + 1),
  { error: "card is expired", path: ["expiryYear"] },
);
// Verified: safeParse issue lands at { code: "custom", path: ["expiryYear"], message: ... }
```

When unsure about any v4 API shape, read the installed types instead of guessing (v3 memory is unreliable):

```bash
grep -n -B2 -A10 'refine' node_modules/zod/v4/classic/schemas.d.ts      # method signatures
grep -n -B2 -A10 'ZodCustomDef' node_modules/zod/v4/core/schemas.d.ts   # refine params (path/error/params)
grep -n -B2 -A12 'export type Params<' node_modules/zod/v4/core/api.d.ts # message deprecation
```

See `references/zod-v4-api-notes.md` for the exact verified signatures and where they live.

## Pattern: strip-then-validate + checksum

For user-entered identifiers (card numbers, IDs) accept cosmetic separators, then validate the canonical form:

```typescript
cardNumber: z.string()
  .refine((raw) => /^\d{13,19}$/.test(raw.replace(/[\s-]/g, "")), "card number must be 13-19 digits")
  .refine((raw) => luhnValid(raw.replace(/[\s-]/g, "")), "card number failed Luhn check"),
```

Checksum helpers are dependency-free, right-to-left (Luhn shown in `references/zod-v4-api-notes.md`). Keep the helper in the same file as the schema — no new packages for validation logic.

## Verify with a throwaway tsx probe (not just tsc)

Type-checking proves the schema compiles; only a probe proves it validates correctly. Pattern:

1. Create `api/.tmp/probe-<name>.ts` (add `.tmp/` to `.gitignore` if absent — check first, and confirm the ignore works with `git check-ignore`).
2. Use `safeParse` and print PASS/FAIL lines, exit non-zero on failure:

```typescript
let failures = 0;
function check(name: string, ok: boolean): void {
  console.log(`${ok ? "PASS" : "FAIL"}: ${name}`);
  if (!ok) failures++;
}
// ... checks ...
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
```

3. Cover BOTH directions: invalid inputs rejected (bad checksum, past dates, wrong formats) AND valid inputs accepted — a schema that rejects everything also passes a reject-only probe.
4. Run: `npx tsx .tmp/probe-<name>.ts` (prepend any needed env vars inline, e.g. `ENCRYPTION_KEY=$(openssl rand -hex 32) npx tsx ...`).
5. Include the probe output verbatim in your summary; the probe file itself is never committed.

## Pitfalls

1. **v3 muscle memory.** zod v4 changed the params object for checks; don't assume v3 options compile. Grep the installed `.d.ts` files (commands above) before writing non-trivial refines.
2. **Object-level refine without `path`.** Without `path`, the error reports against the whole object and UIs can't anchor it to a field. Always set `path: [<one field>]` for cross-field checks.
3. **Creating a plan-named file that doesn't exist** instead of extending the real schema home (Step 0). Duplicate schema homes break imports and split conventions.
4. **Forgetting the accept case.** Probes that only assert rejections pass even when the schema rejects valid input. Always probe at least one fully-valid payload.
5. **Response types as schemas.** Pure response shapes with no validation need don't need zod objects — plain exported TS types match the house precedent and avoid dead schemas.

## Linked Resources

- `references/zod-v4-api-notes.md` — verified zod 4.3.5 type signatures, exact `.d.ts` locations, the Luhn helper, and the probe run transcript.
