# DATABASE_PUBLIC_URL — the auto-provisioned laptop-direct shortcut

Before reaching for `railway ssh`, the base64 ship, or `railway connect`, check
for Railway's **auto-provisioned public DB URL** on the Postgres plugin:

```bash
railway variables --service Postgres --environment <env> --json
# → look for "DATABASE_PUBLIC_URL"
```

If it's set (it usually is — the Postgres plugin provisions it automatically),
connect straight from your laptop with the app's own driver. No ssh, no tunnel,
no base64, no container round-trip:

```ts
import postgres from "postgres";
const sql = postgres(process.env.DATABASE_PUBLIC_URL, { max: 1 });
// ... then UPDATE/INSERT/SELECT; add ssl: "require" if the driver rejects the cert
```

## Key facts

- **Two URLs on the same service:** `DATABASE_URL` is the *private* host
  (`postgres.railway.internal` — laptop/`railway run` get `ENOTFOUND`), while
  `DATABASE_PUBLIC_URL` is the *public*, laptop-reachable endpoint. Don't mix
  them up; check the public one by name.
- **`railway run` is a trap for scripts.** `railway run --service api -- ... `
  injects the service's `DATABASE_URL` (private host) and runs the script
  *locally*, so it still fails with `getaddrinfo ENOTFOUND`. For laptop-direct
  access you must explicitly source `DATABASE_PUBLIC_URL` from the **Postgres**
  service, not the app service.
- **Worked 2026-08-19 (the D&D VTT project staging):** reset an admin password by rehashing
  (`scrypt$salt$hash`) and `UPDATE accounts SET password_hash=…` entirely from
  the laptop via `DATABASE_PUBLIC_URL` — no ssh.

## When to prefer this vs the alternatives

- `DATABASE_PUBLIC_URL` → fastest; use when a plain read/write against the DB is
  all you need and the driver is already in the repo (`postgres`, `pg`, drizzle).
- `railway ssh` → when you need the *container's* exact `node_modules`/driver
  version or the private-network context.
- `railway connect` → when you want local `psql`/GUI tooling over a tunnel.

Note: `railway variables --service Postgres --json` prints the public URL
(contains DB credentials) — pipe it into an env var rather than echoing it.
