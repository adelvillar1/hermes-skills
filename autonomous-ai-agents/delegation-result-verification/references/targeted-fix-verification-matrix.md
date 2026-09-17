# Targeted Fix Verification Matrix

After fixing review findings, verify each fix with a specific curl check — not a
generic smoke test. The matrix maps each finding to its test.

## Pattern

```bash
# Setup: fresh DB + server
docker rm -f pampa-pg-test 2>/dev/null
docker run --rm -d --name pampa-pg-test -e POSTGRES_PASSWORD=*** -e POSTGRES_DB=pampa -p 55432:5432 postgres:16
sleep 6
# Start server in background (use terminal background=true, NOT shell &)
# Wait for "admin created" watch pattern

B=http://localhost:3000
# Login
curl -s -c /tmp/ck.txt -X POST $B/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password": "***"}'

# --- FIX #1: IDOR guard ---
# Create two members, generate deliveries, upload proof for member A's delivery
# Admin views A's photo → 200
# (If member-user auth is available: member B views A's photo → 403)
curl -s -b /tmp/ck.txt -o /dev/null -w "[%{http_code}]" $B/api/deliveries/$D1/photo

# --- FIX #2: nosniff header ---
curl -s -b /tmp/ck.txt -D - -o /dev/null $B/api/deliveries/$D1/photo 2>/dev/null \
  | grep -i "x-content-type-options"
# Expected: x-content-type-options: nosniff

# --- FIX #3: FK validation (eventId) ---
curl -s -b /tmp/ck.txt -w " [%{http_code}]" -X POST $B/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"memberId":"'$M1'","eventId":"00000000-0000-0000-0000-000000000000","items":[{"wine":"X","qty":1,"unitPriceCents":100}]}'
# Expected: {"error":"event not found"} [404]

# --- FIX #4: Zod bounds ---
curl -s -b /tmp/ck.txt -w " [%{http_code}]" -X POST $B/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"memberId":"'$M1'","items":[{"wine":"X","qty":9999,"unitPriceCents":100}]}'
# Expected: {"error":"invalid request body"} [400]

# --- FIX #5: Indexes exist ---
docker exec pampa-pg-test psql -U postgres -d pampa -tAc \
  "SELECT indexname FROM pg_indexes WHERE tablename='orders' ORDER BY indexname;"
# Expected: orders_event_id_idx, orders_member_id_idx, orders_pkey

# --- FIX #6: deliveredAt preserved on re-delivery ---
# PATCH status=delivered again → deliveredAt timestamp unchanged
```

## Key principles

1. **One check per finding.** Don't bundle — if check 3 fails, you need to know
   exactly which fix broke.
2. **Test the NEGATIVE case.** FK validation → send a bad FK. Bounds → exceed them.
   IDOR → access another user's resource.
3. **Check headers, not just status codes.** nosniff, content-type, cache-control.
4. **Verify DB state for structural changes.** Indexes, constraints, migrations.
5. **Use `python3 -c` for JSON extraction** in curl pipelines (jq may not be installed).
   These get flagged by security scanners as "pipe to interpreter" — that's fine for
   local test scripts, auto-approved by smart approval.
6. **Cleanup:** kill server process + `docker rm -f pampa-pg-test` after verification.
