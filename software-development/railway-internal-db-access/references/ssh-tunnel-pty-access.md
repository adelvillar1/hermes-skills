# Reaching a Railway service DB from your local machine

Railway Postgres is only reachable inside the Railway network (`*.railway.internal`)
or over an SSH tunnel. Two dead-ends to avoid, then the working recipe.

## Dead ends
- **`railway connect <Service>` in foreground / non-interactive mode** opens the tunnel
  then the command *exits immediately*, tearing the tunnel down. You'll see
  `Opening SSH tunnel: 127.0.0.1:<PORT>` and then a `Connection refused` on that port.
- **`railway run --service <Service> -- <cmd>`** injects the service's env vars but does
  NOT grant network access — `postgres.railway.internal` still fails to resolve locally
  (`could not translate host name`).
- **`DATABASE_PUBLIC_URL`** often has an *empty host* (`postgresql://user:pw@:/railway`)
  because public networking is disabled. Don't rely on it.

## Working recipe: background tunnel held open by a PTY
1. Start the tunnel in a **background terminal with `pty=true`** so it stays alive and
   drops into an interactive `psql` prompt while holding the port:
   ```
   terminal(background=true, pty=true, command="railway connect Postgres",
            watch_patterns=["Opening SSH tunnel"])
   ```
2. Poll the process; read the local port from `Opening SSH tunnel: 127.0.0.1:<PORT> → service :5432`.
3. Get credentials: `railway variables --service Postgres --kv` → `PGPASSWORD` (user is `postgres`, db is usually `railway`).

### Connect with psql
```
export PGPASSWORD='<pw>'
psql "postgresql://postgres@127.0.0.1:<PORT>/railway?sslmode=require" -c "..."
```
(Pass the whole DSN as ONE quoted arg — splitting host=/port=/user= across words gets
ignored by psql and it falls back to localhost:5432.)

### Connect from Node / Drizzle / pg
Railway PG uses a **self-signed cert** → pg throws `SELF_SIGNED_CERT_IN_CHAIN`. For a
one-off script, disable verification and point the app's own client at the tunnel:
```
NODE_TLS_REJECT_UNAUTHORIZED=0 \
DATABASE_URL="postgresql://postgres:<pw>@127.0.0.1:<PORT>/railway?sslmode=require" \
  npx tsx path/to/script.ts
```
(`sslmode=require` prints a deprecation warning about verify-full aliases — harmless.)

## Pitfalls
- The tunnel **times out on long idle** (`Timeout, server ssh.railway.com not responding`).
  Kill the background process and reopen; the new tunnel gets a NEW port — re-capture it.
- Reuse the app's own Drizzle client (`import { db, pool } from "./api/src/db/client"`)
  so schema types, password hashing (`@node-rs/argon2`), and column names stay correct.
  Remember to `await pool.end()` before exit.
- A standalone `tsc --noEmit` on a seed script reports false Drizzle overload errors
  (it lacks the project tsconfig). The project runs via `tsx`, which transpiles without
  typechecking — trust `tsx` execution, not standalone `tsc`.
