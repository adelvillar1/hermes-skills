# `railway connect` — piped one-shot SQL (no PTY) + psql parsing + user provisioning

Proven 2026-08-10 on the school-dismissal SaaS staging (`Postgres-BsQl`). Extends the SKILL.md
`railway connect` variant.

## One-shot piped SQL works WITHOUT pty/background

The SKILL.md's "dies instantly without a PTY" applies to keeping a tunnel alive for
*follow-up local clients*. For a single batch of SQL, pipe stdin and let psql exit —
the tunnel lives exactly as long as the session needs:

```bash
echo "$SQL" | railway connect Postgres-BsQl
```

Ran clean in a plain foreground `terminal()` call (no `pty=true`, no background) — much
simpler than the interactive-PTY + process-submit workflow when you know the full SQL up
front. Multi-line SQL via heredoc into a variable is fine.

## Parsing psql tabular output: the dashes trap

psql prints:

```
 count
-------
     1
(1 row)
```

`grep -A1 "count" | tail -1` grabs the `-------` separator, not the value (cost a false
FAIL in a verification run). Extract numeric rows by shape instead:

```bash
... | grep -E "^\s+[0-9]+\s*$" | tail -1 | tr -d ' '
```

Or skip parsing entirely: `psql -t -A` — but you don't control psql flags through
`railway connect`, so grep-by-shape is the available tool.

## Recipe: provision an admin user when no credentials exist

Chicken-and-egg: the `POST /admin/super-admins` endpoint requires an existing super_admin,
and nobody wrote the bootstrap password down. Provision directly in the DB:

1. Generate the password hash **locally with the app's own hashing setup** (so the algo/rounds
   match) — a 3-line script run with the backend venv:

   ```python
   # scripts/hash_pw.py
   import sys
   from passlib.context import CryptContext
   print(CryptContext(schemes=["bcrypt"], deprecated="auto").hash(sys.argv[1]))
   ```

2. Idempotent INSERT (platform school + user) via the piped-SQL form above:

   ```sql
   INSERT INTO schools (slug, name, admin_email, subscription_status, subscription_plan, created_at, updated_at)
   SELECT 'platform','Platform Administration','you@example.com','active','enterprise',now(),now()
   WHERE NOT EXISTS (SELECT 1 FROM schools WHERE slug='platform');
   INSERT INTO users (school_id, email, hashed_password, first_name, last_name, role, is_active, created_at)
   SELECT id, 'you@example.com', '<HASH>', 'Staging', 'Platform', 'super_admin', true, now()
   FROM schools WHERE slug='platform'
   AND NOT EXISTS (SELECT 1 FROM users WHERE email='you@example.com');
   ```

   Note: SQLAlchemy column `default=func.now()` is CLIENT-side — raw INSERTs omitting those
   columns leave NULLs (fine when nullable, as `created_at` usually is).

3. Verify with a final SELECT joined to the school, then log in through the real
   `/api/auth/login` endpoint to prove the hash verifies end-to-end.
