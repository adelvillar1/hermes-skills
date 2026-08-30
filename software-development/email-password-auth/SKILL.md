---
name: email-password-auth
description: Zero-dep email/password auth for Next.js + Prisma apps.
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [auth, authentication, login, sessions, cookies, security, idor, nextjs, prisma, scrypt]
    related_skills: [prisma-setup-migrations, api-security-review, react-spa-api-client, cross-origin-spa-auth, viewer-scoped-delivery, aes-256-gcm-encryption]
---

# Email/Password Authentication (zero-dependency)

## When to Use

- "Implement authentication with email/password", "add login/register/logout", "seed X as a user".
- Protecting API routes and pages behind a session; scoping data to the owning user (IDOR prevention).
- Any Node server + SQL DB where you want auth WITHOUT adding bcrypt/argon2/jose/iron-session deps (native-module risk on Railway, supply chain, bundle weight).

## Process rule (user preference — security-critical work)

**Auth is security-critical: implement it DIRECTLY in the parent session. Do NOT delegate to subagents.** The user is explicitly skeptical of subagents for auth/security/infra. Delegation is fine for parallelizable build work, not for the credential/session layer.

## Architecture (all stdlib, no new deps)

1. **Password hashing — Node `crypto.scrypt`** (memory-hard, timing-safe, no native module):
   ```ts
   import { randomBytes, scrypt as scryptCb, timingSafeEqual } from "crypto";
   import { promisify } from "util";
   const scrypt = promisify(scryptCb) as (...a: any[]) => Promise<Buffer>;
   const N = 16384, r = 8, p = 1, KEYLEN = 64;
   export async function hashPassword(pw: string) {
     const salt = randomBytes(16);
     const key = await scrypt(pw, salt, KEYLEN, { N, r, p });
     return `s1$${salt.toString("hex")}$${key.toString("hex")}`;
   }
   export async function verifyPassword(pw: string, stored: string) {
     const [ver, saltHex, keyHex] = stored.split("$");
     if (ver !== "s1" || !saltHex || !keyHex) return false;
     const key = await scrypt(pw, Buffer.from(saltHex, "hex"), KEYLEN, { N, r, p });
     const expected = Buffer.from(keyHex, "hex");
     return key.length === expected.length && timingSafeEqual(key, expected);
   }
   ```
2. **Sessions — DB-backed, revocable, no JWT/secret needed.** Random 32-byte token in an httpOnly cookie; store only its SHA-256 hash in a `Session` table (DB leak ≠ usable sessions):
   ```ts
   const TOKEN_HASH = (t: string) => createHash("sha256").update(t).digest("hex");
   // Session row: id, tokenHash @unique, userId, expiresAt (30d)
   export async function createSession(userId: string) {
     const token = randomBytes(32).toString("hex");
     await prisma.session.create({ data: { tokenHash: TOKEN_HASH(token), userId, expiresAt: new Date(Date.now() + 30*24*3600e3) } });
     return token;
   }
   ```
3. **Cookie**: `httpOnly, sameSite: "lax", path: "/", secure: process.env.NODE_ENV === "production", maxAge: 30d`. Set via `NextResponse` / `res.cookies.set(...)`. Logout = delete row + clear cookie.
4. **Reading the session** — parse the raw `Cookie` header (don't rely on `cookies()` in helper libs so it works in both route handlers and standalone scripts):
   ```ts
   export async function getSessionUser(req: Request) {
     const raw = req.headers.get("cookie") ?? "";
     const m = raw.split(";").map(s => s.trim()).find(c => c.startsWith("dc_session="));
     const token = m?.slice("dc_session=".length);
     if (!token) return null;
     const s = await prisma.session.findUnique({ where: { tokenHash: TOKEN_HASH(token) }, include: { user: true } });
     if (!s || s.expiresAt.getTime() < Date.now()) return null;
     return { id: s.user.id, email: s.user.email };
   }
   export const unauthorized = () => NextResponse.json({ error: "Not authenticated" }, { status: 401 });
   ```
5. **Schema** — `User` (id, email @unique, passwordHash, timestamps), `Session` (tokenHash @unique, userId → User, expiresAt), and an owner column on owned resources (`Project.userId String?`).

## Route wiring

- Auth routes: `POST /api/auth/register|login|logout`, `GET /api/auth/me`.
- Register: validate email format + password ≥ 8, normalize email to lowercase, 409 on duplicate, hash, create user + session, set cookie.
- Login: verify password (generic "Invalid email or password" on either failure — don't leak which), create session, set cookie.
- **Guard EVERY existing route** that touches user data: `const user = await getSessionUser(req); if (!user) return unauthorized();` at the top of the handler.

## IDOR / ownership scoping (the security core)

- List: filter by owner — `where: { userId: user.id }`.
- Detail/update/delete: **return 404, not 403, when the resource isn't the caller's** — 404 avoids confirming the resource exists (403 leaks it). **Use STRICT ownership: `userId: null` is "not owned" → 404.** Do NOT write `project.userId && project.userId !== user.id` — that leaks unclaimed rows (they pass the guard) until a seed backfills them; there is a window between migration and seed on prod where a freshly-registered user can read them. Pattern:
  ```ts
  const project = await prisma.project.findUnique({ where: { id } });
  if (!project || project.userId !== user.id)
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  ```
- Guard **nested/derived routes too**: frame preview routes must resolve frame → project → `project.userId` via `include: { project: { select: { userId: true } } }`. Review/chat/generate routes that take a `projectId` in the body must ownership-check that project before doing work.
- Auth-only routes (stateless LLM review, site fetch) just require a session; they don't need ownership if they carry no resource id.

## Seed + backfill of the initial admin

Standalone script (`scripts/seed-user.mjs`) — NOT `prisma db seed` config:
- **Pitfall: `dotenv/config` loads `.env`, NOT `.env.local`.** Load explicitly:
  ```js
  import { config as loadEnv } from "dotenv";
  loadEnv({ path: ".env.local" });
  ```
- Use the same `PrismaPg` adapter as the app (`@prisma/adapter-pg`).
- Upsert the admin by email; then **backfill unowned rows** so pre-auth data isn't orphaned:
  ```js
  const claimed = await prisma.project.updateMany({ where: { userId: null }, data: { userId: user.id } });
  ```
- Generate a strong password (`openssl rand -base64 18 | tr -d '/+=' | head -c 16`), write `SEED_USER_PASSWORD` to `.env.local`, **never echo it in tool output**. Read it in scripts via `process.env.SEED_USER_PASSWORD`. For prod: set `SEED_USER_PASSWORD` as a Railway masked variable, then run the seed **inside the container** — the seed script ships with the deploy (it's committed), so it's already at `/app`:
  ```bash
  railway ssh --service web -- "cd /app && node scripts/seed-user.mjs"
  ```
  **Do NOT use `railway run node scripts/seed-user.mjs` for the prod seed** — `railway run` executes the command LOCALLY with env injected, and the prod `DATABASE_URL` points at `postgres.railway.internal`, which only resolves inside Railway's network (fails with P1001 `DatabaseNotReachable`). See the `railway-internal-db-access` skill for the full pattern. Probe first that the script + deps shipped: `railway ssh --service web -- "pwd && ls scripts/ && ls node_modules | grep -E '^(dotenv|@prisma)$'"`.
- Seed BEFORE deploy or right after migration — migrations first, then seed, then app code. `railway.toml` startCommand running `prisma migrate deploy && pnpm start` applies migrations automatically at boot.

## E2E verification recipe (prove the guards, don't assume)

Use curl with a cookie jar; the password comes from `.env.local`, never typed in the transcript:
```bash
PW=$(grep '^SEED_USER_PASSWORD=' .env.local | cut -d= -f2-)
JAR=$(mktemp)
curl -s -c "$JAR" -X POST localhost:3000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@x.com\",\"password\":\"$PW\"}" -w "\nHTTP %{http_code}\n"
```
Verify matrix:
- unauth `GET /api/projects` and `/api/auth/me` → 401
- login → cookie → `me` → 200; create project → 201; logout → `me` → 401
- **register a second user** and confirm: their list is `[]`, reading the owner's project → 404, generate/chat/preview on owner's ids → 404. This is the IDOR proof.
- `tsc --noEmit` clean + `pnpm lint` clean before committing.
- **After deploy, repeat the same matrix against the prod URL** (not just localhost): same curl recipe with the seed password, same 401→200→401 sequence. Then a real browser login (type seed creds into the form) and confirm the authed home renders with the user's projects. Also verify the login page visually — the design-system render is part of the acceptance.

## Pitfalls

- **LSP diagnostics after `prisma generate` are stale** — trust `tsc --noEmit`; see `prisma-setup-migrations` skill.
- Don't put `userId` in `ProjectWhereInput` selects blindly — nullable `userId` on legacy rows: backfill them in the seed, and treat `userId: null` as "not owned" (404) so unclaimed rows aren't a hole.
- Duplicate-email register must be a 409, not a 500 (use `findUnique` first).
- Don't echo `Set-Cookie` tokens in terminal output either — write them to temp files if a browser test needs them.
- Remote/browser automation (Browserbase) can't reach your local clipboard, and **`document.cookie` CANNOT set httpOnly cookies** (the session cookie is invisible to page JS — minting a token via curl and injecting it with `document.cookie` silently no-ops). The reliable browser-login path: type the real seed credentials into the form via `browser_type` (email is public, password comes from `.env.local` `SEED_USER_PASSWORD`), or verify the UI error path (wrong password → visible error) + the success path via curl. Browserbase is a remote browser — `cmd+v` paste won't reach it; do not pbcopy.
