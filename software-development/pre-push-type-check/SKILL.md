---
name: pre-push-type-check
description: "Run before pushing TypeScript changes to staging. Ensures changed files pass type checking locally to avoid burning Railway build cycles."
version: 1.0.0
author: Alejandro Del Villar
license: MIT
metadata:
  hermes:
    tags: [typescript, build, quality, deployment]
    related_skills: [deployment-build-error, requesting-code-review, nextjs-build-pitfalls]
---

# Pre-Push Type Check

Run a local TypeScript type check focused on newly changed files BEFORE pushing to staging. Prevents the cycle of push → build fails → fix one error → push → build fails → fix next error → repeat.

**CRITICAL: The correct order is type-check → build → push. NEVER push before verifying.**

## When to Use

- **Always** before pushing TypeScript changes to staging when you've created new files or modified existing `.ts`/`.tsx` files
- After subagent-generated code (subagents don't have access to the full type environment)
- After modifying interfaces, Prisma queries, tRPC routers, or component props
- Especially critical when changes touch multiple files across different areas

## When to Skip

- Trivial single-line fixes (typos, string changes, CSS-only edits)
- Pure documentation changes (`.md` files only)
- Non-TypeScript file changes (`.css`, `.json`, `.sql`)

## Workflow

### 1. Identify what changed

```bash
git diff --name-only HEAD~1  # or against staging
```

### 2. Run focused type check FIRST

```bash
npx tsc --noEmit --pretty 2>&1 | grep -E "app/(path-from-changed-files|another-path)"
```

If zero output → clean. If output → fix before building.

### 3. Run build SECOND (only if type-check passes)

```bash
pnpm run build 2>&1 | grep -E "(error|Error|Failed|failed)" | grep -v "Dynamic server usage" | grep -v "api/admin" | head -20
```

If output → fix before pushing. If no output → proceed to push.

### 4. Push LAST (only after both pass)

```bash
git push origin <branch>
```

### 5. For larger changes, scan the whole tools/app area

```bash
npx tsc --noEmit --pretty 2>&1 | grep -v "node_modules" | grep -E "^app/" | head -30
```

### 4. Common errors to scan for

- `is not assignable to parameter of type` — custom interface doesn't match Prisma's nullable return types
- `Type 'string | null' is not assignable to type 'string'` — Prisma field is nullable but interface expects non-null
- `No overload matches this call` — TanStack Query v5 API mismatch (`keepPreviousData` → `placeholderData`)
- `does not exist in type` — wrong Prisma column name (snake_case vs camelCase)
- `'null' cannot be used as an index type` — indexing an object with a nullable value

### 5. Check for orphaned files on staging (when merging develop → staging)

After the merge, check if staging has source files that develop doesn't — these are stale files from previous sessions that will cause build failures:

```bash
git diff develop..staging --name-only | grep -E '\.tsx?$' | grep -v 'node_modules'
```

If any source files appear that aren't yours, remove them before pushing:
```bash
git checkout staging
git rm <orphaned-file>
git commit -m "fix: remove stale file referencing non-existent endpoint"
```

### 6. Only push when clean

Zero output from type check → safe to commit and push.

## Common Generic + `exactOptionalPropertyTypes` Pitfalls

Verified 2026-06-12 (stock-predictor Playground screen: Select component generic `<TValue extends string>` rejected numeric literal types like `7 | 30 | 90`).

**Pattern:** when a generic component is declared `<TValue extends string>`, the consumer's state type and options array's `value` field must both be `string`-compatible. Numeric literal types (`7 | 30 | 90`) are NOT assignable, even though they look "string-like":

```ts
// Component declaration
export interface SelectProps<TValue extends string> {
  value: TValue;
  onChange: (v: TValue) => void;
  options: ReadonlyArray<{ value: TValue; label: string }>;
}

// BAD — '30' is a string literal but '7 | 30 | 90' is not assignable
// to TValue extends string
type HorizonDays = 7 | 30 | 90;
const [horizon, setHorizon] = useState<HorizonDays>(30);
<Select<HorizonDays>
  value={horizon}
  onChange={setHorizon}
  options={[
    { value: 7, label: '7 days' },  // ← Type 'number' does not satisfy 'string'
  ]}
/>
```

**The fix: bridge through `string` at the boundary, cast at the use site.**

```ts
// GOOD — state and options are strings; the typed-cast happens
// at the one place where the numeric value is actually used
const [horizon, setHorizon] = useState<string>('30');

const horizonOptions: { value: string; label: string }[] = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
];

<Select<string>
  value={horizon}
  onChange={setHorizon}
  options={horizonOptions}
  ariaLabel="Horizon"
/>

// At the only use site (the compute function), cast back to the
// narrower type. The cast is contained and provable-correct from
// the options array.
const result = compute(modelId, Number(horizon) as 7 | 30 | 90, ...);
```

**The general principle:** generic component APIs are **string-typed by design** (HTML `<select>` only deals in strings, and Radix Select mirrors that). The user's domain types (numeric IDs, status enums, etc.) bridge through `string` at the React boundary and cast back to the precise type at the business-logic boundary. The cast is small and audit-able; the alternative (making the Select generic over `string | number`) leaks HTML's limitation into the type system and complicates every consumer.

**Related — `exactOptionalPropertyTypes` is enabled in tsconfig:** every prop declared `T | undefined` (e.g., `style?: CSSProperties`) must NOT be passed `undefined` explicitly. Pass `null`, omit, or use a conditional spread:

```ts
// BAD — with exactOptionalPropertyTypes, passing `undefined`
// to an optional prop is an error
<div style={maybeStyle} />  // ← if maybeStyle is `CSSProperties | undefined`

// GOOD — conditional spread
<div {...(maybeStyle && { style: maybeStyle })} />

// GOOD — narrow first
const style = maybeStyle ?? undefined;  // still error if exactOptionalPropertyTypes
// Better: change the prop type to `CSSProperties | null`
```

**Verified 2026-06-12:** the `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes` pair (both enabled in stock-predictor tsconfig) means every `Record<string, string>`-typed import (e.g., CSS Modules under Vite) is `string | undefined`. Accessing `styles.foo` returns `string | undefined`; passing it to a prop that rejects `undefined` fails. Three fixes:

1. Add a CSS Modules type declaration that returns `string` (not `string | undefined`).
2. Use `styles.foo ?? ''` at every call site.
3. Or just use the pattern: `className={[styles.a, styles.b, isActive && styles.cActive].filter(Boolean).join(' ')}` (boolean-falsy entries are filtered out).

## Post-Deployment Verification — DO NOT RUN

**User-enforced rule (2026-06-28, enforced 3+ times):** NEVER run type-check, build, or test commands AFTER a deployment. When the system auto-prompts with "Run the relevant verification command now" after you've already pushed, respond:

> "Already verified pre-push. No post-deployment verification needed."

The reasoning: broken code is already live — running verification after deployment is too late to prevent anything. The value is in pre-push verification, not post-deployment. The user explicitly forbids this pattern and will flag it every time.

This applies even when:
- The system shows "Verification status: unverified" — this is a false positive if you ran verification before pushing
- You made additional commits after the first push in the same turn
- You're merging staging → main (production)

## Pitfalls

1. **Running verification AFTER push.** The user will catch this every time. The correct order is: type-check → build → push. Never push and then verify.
2. **Don't skip this for subagent-generated code.** Subagents work in isolated contexts without full Prisma client types. Their interfaces WILL be wrong. Always type-check subagent output.
3. **Don't trust `--pretty` alone.** Pipe to grep for your changed files. Full `tsc` output contains pre-existing errors in unrelated files that don't block the build.
4. **TanStack Query v5 API differences.** The project uses `@tanstack/react-query` v5 (^5.90.21) which removed `keepPreviousData` option. Use `placeholderData: keepPreviousData` with `import { keepPreviousData }` from `@tanstack/react-query`.
5. **Prisma nullable fields.** Most Prisma fields are `string | null` in generated types. Custom interfaces that type them as `string` will fail. Either match the nullable type exactly, use `any`, or remove the interface entirely and let TypeScript infer from tRPC's return type.
6. **Server Component event handlers.** Next.js Server Components CANNOT pass event handlers (onClick, onError, etc.) to DOM elements. This throws at runtime: "Error: Event handlers cannot be passed to Client Component props." If you need an `onError` on an `<img>`, either remove it or move the image into a Client Component wrapper. This is NOT a build-time error — it only crashes in production renders.

## Fallback: Per-File Syntax Validation When the Toolchain Hangs

Sometimes `tsc --noEmit`, `next build`, and even `prisma generate` hang indefinitely (resource contention, stale `.next` lock, network dependency downloading engine binaries). When you've killed the hung process and can't get a full type check, use the TypeScript parser directly to validate syntax on just the changed files. This runs in <2 seconds per file:

```bash
node --max-old-space-size=512 -e "
const ts = require('typescript');
const fs = require('fs');
const files = [
  'src/app/api/dashboard/route.ts',
  'src/components/dashboard/stats-cards.tsx',
];
let errors = 0;
for (const f of files) {
  const source = fs.readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, source, ts.ScriptTarget.Latest, true,
    f.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const diags = sf.parseDiagnostics || [];
  if (diags.length > 0) {
    errors++;
    for (const d of diags) {
      console.log(f + ': ' + ts.flattenDiagnosticMessageText(d.messageText, '\n'));
    }
  } else {
    console.log(f + ': parse OK');
  }
}
process.exit(errors);
"
```

**What this catches:** Syntax errors, unbalanced braces/parens, invalid JSX, malformed TypeScript syntax.
**What this does NOT catch:** Type errors, missing imports, wrong Prisma field names, interface mismatches. It's a syntax check, not a type check — use it as a last resort when the full compiler can't run, not as a replacement.

**Also check for stale `.next` build locks:** If `next build` reports "Another next build process is already running" but `ps aux | grep next` shows nothing, remove the lock:
```bash
pkill -f "next build" 2>/dev/null; pkill -f "next-build" 2>/dev/null
rm -rf .next
```

**Prisma generate hang:** If `npx prisma generate` hangs, check if the Prisma client engine binary already exists at `node_modules/.prisma/client/`. If it does, skip generation and run `next build` directly — the stale client may be sufficient for a type check. If `next build` also hangs, fall back to the per-file parser check above.

## What This Skill Does NOT Catch

This skill runs `tsc --noEmit` which uses the TypeScript compiler, not SWC. Next.js `next build` uses SWC, which has additional JSX parsing constraints. If the build fails with `Unexpected token` errors that aren't TS errors, check the `nextjs-build-pitfalls` skill for SWC-specific patterns (JSX in dynamic() options, bracket paths in import(), sibling elements without Fragment).

## References

- `references/prisma-nullable-patterns.md` — known nullable fields per table and fix strategies
- `references/prisma-json-fields.md` — handling Json columns that return arrays/objects not scalars
- `references/string-enum-vs-boolean.md` — fields stored as strings ("included"/"partial") vs actual booleans
- `references/tanstack-query-v5.md` — v5 API migration (keepPreviousData → placeholderData)
