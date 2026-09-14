# Verifying stored password hashes before rewriting them

Use when a report says "login is broken / rehash the admin password." Verify
BEFORE writing any data — rehashing permanently discards the user's real
password if the hash was actually fine. In the real 2026-08-05 case
(the wine-club app staging) the hash verified clean and zero DB writes were
needed; the report was wrong-password/wrong-env.

## Diagnosis ladder

1. **Structural validity.** argon2 hashes look like
   `$argon2id$v=19$m=<mem>,t=<iter>,p=<par>$<salt-b64>$<hash-b64>`.
   Corrupted signals: missing `$` segments, wrong length, whitespace/quotes,
   truncation. Compare the param prefix against the app's hashing library
   defaults (`@node-rs/argon2` defaults: `m=19456,t=2,p=1`) — matching params
   mean the same code path produced it, strong evidence it's sound.
2. **Verify against known candidate passwords.** Seeded admin accounts get
   their password from an env var (`ADMIN_BOOTSTRAP_PASSWORD` etc.) — pull it
   from `railway variables --service web --kv`. Never guess/brute-force.
   Verify with the app's OWN library + version (run from the repo's
   `node_modules`); argon2 implementations are not cross-compatible.
3. **Live endpoint test** with curl (password via env var, never argv).
   HTTP 200 → credentials work; failure cause is user error, rate limiting,
   or wrong environment.
4. Only if 1–3 establish the hash is genuinely broken: rehash with the app's
   own hash function and `UPDATE` the row — explicit approval, staging first.
   If the hash is structurally valid but nothing verifies, report to the user
   and ask for a new password; don't overwrite on speculation.

## Secret hygiene

- Never echo passwords or full DSNs; never pass secrets as argv (ps-visible).
- Dump `railway variables --service <svc> --kv` to a `chmod 600` temp file,
  extract with `grep '^VAR=' f | cut -d= -f2-` into shell vars, pass to
  node/python via environment. Build JSON bodies from env:
  `python3 -c 'import json,os; print(json.dumps({"email":"…","password":os.environ["PW"]}))'`
- Print booleans, lengths, hash prefixes only. `rm -f` temp files after.

## Verification script skeleton (node, app's own argon2)

```js
import { verify, hash } from "@node-rs/argon2"; // app's own lib/version
const stored = process.env.STORED_HASH;
const candidate = process.env.CANDIDATE;
console.log("prefix:", stored.slice(0, 29), "len:", stored.length);
console.log("verifies:", await verify(stored, candidate).catch(e => "threw: " + e.message));
const t = await hash("canary"); // self-test proves the library works
console.log("self-test:", await verify(t, "canary"));
```

## Pitfall: `.then(() => true)` masks verify failures (2026-08-12 the wine-club app)

A verification script like `await verify(stored, pw).then(() => true)` ALWAYS
prints `true` — the `.then(() => true)` swallows the resolved boolean. If the
password mismatches, `verify()` RESOLVES `false` (it does not throw), and the
`.then(() => true)` converts that into `true`. Result: "hash verifies clean"
when it doesn't — exactly the false-positive that wastes hours hunting a
"stale replica / wrong DATABASE_URL / rate limiter" ghost. The live login
(401) was right all along; the stored hash simply didn't match any candidate.

**Rule:** never chain `.then(() => true)` onto `verify()`. Capture the raw
result: `const r = await verify(stored, pw).catch(e => "threw: " + e.message);
console.log("verify:", r);` — print the real boolean. Self-tests
(`hash("canary")` then verify) are still useful, but also print the RAW result.

## Common false causes (hash is fine)

- Wrong password typed — top cause when the hash verifies.
- Auth rate limiter (e.g. in-memory 10 req/15 min) → 429 after retry storms.
- Testing the wrong environment (local dev with DB/API down vs deployed env).
- Email case-sensitivity mismatch (stored lowercase; login must normalize).
