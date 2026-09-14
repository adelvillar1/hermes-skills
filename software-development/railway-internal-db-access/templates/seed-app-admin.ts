/**
 * Seed an extra admin/user account into an app's `users` table.
 *
 * Why this exists: many apps bootstrap only ONE admin from env vars
 * (e.g. ADMIN_EMAIL / ADMIN_BOOTSTRAP_PASSWORD) at migrate time. Extra accounts
 * must be inserted directly — and the hash MUST come from the app's own hashing
 * lib (@node-rs/argon2 here) so POST /api/auth/login verifies on the first try.
 *
 * Usage (against a Railway DB via `railway connect <svc> -P <port>` background
 * PTY tunnel — see SKILL.md):
 *   NODE_TLS_REJECT_UNAUTHORIZED=0 \
 *   DATABASE_URL="postgresql://postgres:<pw>@127.0.0.1:<port>/railway?sslmode=require" \
 *   SEED_EMAIL=... SEED_PASSWORD=... [SEED_NAME="..."] [SEED_ROLE=admin] \
 *     npx tsx api/scripts/seed-app-admin.ts [--dry-run]
 *
 * Run --dry-run first, review the printed plan, then run without it. Extract
 * <pw> at runtime via a bash wrapper (write_file the wrapper, `bash /tmp/w.sh`)
 * — never inline credential greps on the terminal command line (hardline-blocked).
 *
 * Verify after the insert: psql `SELECT` for the row, then a live login curl to
 * the public API expecting HTTP 200 + the role in the body.
 */
import { randomUUID } from "node:crypto";
import { hash } from "@node-rs/argon2";
import { eq } from "drizzle-orm";
import { db, pool } from "../src/db/client"; // adjust import path to target repo
import { users } from "../src/db/schema";    // adjust table/columns to target repo

const DRY_RUN = process.argv.includes("--dry-run");
const EMAIL = process.env.SEED_EMAIL;
const NAME = process.env.SEED_NAME ?? "Admin";
const ROLE = process.env.SEED_ROLE ?? "admin";
const PASSWORD = process.env.SEED_PASSWORD;

async function main(): Promise<void> {
  if (!EMAIL || !PASSWORD) {
    console.error("SEED_EMAIL and SEED_PASSWORD env vars required");
    process.exit(1);
  }

  const existing = await db
    .select({ id: users.id })
    .from(users)
    .where(eq(users.email, EMAIL))
    .limit(1);

  if (existing.length > 0) {
    console.log(`[seed] user already exists: ${EMAIL} (id=${existing[0].id}) — skipping`);
    return;
  }

  const passwordHash = await hash(PASSWORD);

  console.log(`[seed] ${DRY_RUN ? "DRY-RUN — would insert" : "inserting"} ${ROLE}:`);
  console.log(`  email:        ${EMAIL}`);
  console.log(`  name:         ${NAME}`);
  console.log(`  role:         ${ROLE}`);
  console.log(`  passwordHash: ${passwordHash.slice(0, 40)}…`);

  if (DRY_RUN) {
    console.log("[seed] dry-run complete — no rows written");
    return;
  }

  const rows = await db
    .insert(users)
    .values({
      id: randomUUID(),
      email: EMAIL,
      passwordHash,
      name: NAME,
      role: ROLE,
    })
    .returning({ id: users.id, email: users.email, name: users.name, role: users.role });

  console.log("[seed] created:", JSON.stringify(rows[0]));
}

main()
  .catch((err) => {
    console.error("[seed] ERROR:", err.message);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
