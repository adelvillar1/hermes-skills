# zod v4 API notes — verified against zod 4.3.5 (2026-08-15)

Exact type signatures confirmed by reading `node_modules/zod` `.d.ts` files in a
live monorepo. Use these instead of v3 memory.

## `.refine()` method signature

From `node_modules/zod/v4/classic/schemas.d.ts` (line ~38):

```typescript
refine<Ch extends (arg: core.output<this>) => unknown | Promise<unknown>>(
  check: Ch,
  params?: string | core.$ZodCustomParams
): Ch extends (arg: any) => arg is infer R ? this & ZodType<R, core.input<this>> : this;
```

Second arg is EITHER a plain message string OR a params object. Both compile:

```typescript
z.string().refine(fn, "failure message");
z.object({...}).refine(fn, { error: "card is expired", path: ["expiryYear"] });
```

## Refine params object shape

`$ZodCustomParams = CheckTypeParams<schemas.$ZodCustom, "fn">` (core/api.d.ts:272),
which reduces via `Params<...>` to a partial of `$ZodCustomDef`. The def
(core/schemas.d.ts:1125):

```typescript
export interface $ZodCustomDef<O = unknown> extends $ZodTypeDef, checks.$ZodCheckDef {
    type: "custom";
    check: "custom";
    path?: PropertyKey[] | undefined;      // ← issue path for object-level refines
    error?: errors.$ZodErrorMap | undefined;
    params?: Record<string, any> | undefined;
    fn: (arg: O) => unknown;
}
```

So valid params keys: `error`, `path`, `params`. Additionally `Params<...>`
(core/api.d.ts:6-10) adds:

```typescript
error?: string | errors.$ZodErrorMap<IssueTypes> | undefined;
/** @deprecated This parameter is deprecated. Use `error` instead. */
message?: string | undefined;
```

**`message` still works in v4 but is officially deprecated — prefer `error`.**
Both were exercised in the 2026-08-15 session without compile errors.

## Verified runtime behavior of `path`

Object-level `.refine(..., { message: "card is expired", path: ["expiryYear"] })`
on a card schema produced, on a rejected parse:

```json
{"code":"custom","path":["expiryYear"],"message":"card is expired"}
```

i.e. `path` lands the issue exactly on the named field so UIs can anchor errors.

## Cross-field expiry check (canonical form)

Expiry spans two fields, so the check lives on the OBJECT, reported on one field:

```typescript
const CardUpsertSchema = z.object({
  expiryMonth: z.number().int().min(1).max(12),
  expiryYear: z.number().int().min(1000).max(9999),
}).refine(
  (card) => {
    const now = new Date();
    return (
      card.expiryYear > now.getFullYear() ||
      (card.expiryYear === now.getFullYear() &&
        card.expiryMonth >= now.getMonth() + 1)
    );
  },
  { error: "card is expired", path: ["expiryYear"] },
);
```

Note `getMonth()` is 0-based; compare against `now.getMonth() + 1`.

## Dependency-free Luhn helper

```typescript
/** Luhn checksum over a digits-only string. */
function luhnValid(digits: string): boolean {
  let sum = 0;
  let double = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let d = digits.charCodeAt(i) - 48;
    if (double) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
    double = !double;
  }
  return sum % 10 === 0;
}
```

Paired with strip-then-validate: `.refine((raw) => luhnValid(raw.replace(/[\s-]/g, "")), ...)`.

## How the API facts were confirmed (grep recipes)

```bash
# Where is zod installed?
ls -d node_modules/zod api/node_modules/zod 2>/dev/null
node -p "JSON.parse(require('fs').readFileSync('node_modules/zod/package.json','utf8')).version"

# refine method signature
grep -n 'refine' node_modules/zod/v4/classic/schemas.d.ts

# refine params (path/error/params)
grep -n -B2 -A10 'ZodCustomDef' node_modules/zod/v4/core/schemas.d.ts

# message deprecation + Params shape
sed -n '1,12p' node_modules/zod/v4/core/api.d.ts
```

## Probe transcript (member-card-vault Phase 1b, 2026-08-15)

`api/.tmp/probe-crypto.ts` run via `ENCRYPTION_KEY=$(openssl rand -hex 32) npx tsx .tmp/probe-crypto.ts`:

```
PASS: decrypt(encrypt(pan)) === pan
PASS: two encrypts of same plaintext differ
PASS: tampered ciphertext throws on decrypt
PASS: CardUpsertSchema rejects bad-Luhn 1234567890123456
PASS: CardUpsertSchema accepts 4242424242424242 / cvv 123 / future expiry
PASS: CardUpsertSchema rejects past expiry year
PASS: CardUpsertSchema rejects earlier month of current year
ALL PASS
```

Both directions covered (rejects AND accepts). Type gates:
`npx tsc --noEmit -p shared` and `-p api` → zero errors.
