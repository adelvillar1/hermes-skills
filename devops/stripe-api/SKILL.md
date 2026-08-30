---
name: stripe-api
description: "Call Stripe REST endpoints with auth, errors, pagination."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Stripe, REST, Payments, API, Idempotency]
---

# Stripe REST API

Call the Stripe API directly over HTTP: authenticated requests, error handling, idempotency, pagination, expansion, and the v1/v2 namespace differences, as documented at https://docs.stripe.com/apis and https://docs.stripe.com/api. It covers raw REST mechanics, NOT CLI usage (see `stripe-cli`) and NOT project billing logic (see `stripe-billing`). Tested against curl; SDKs follow the same contracts.

## When to Use

- Making one-off Stripe API calls from a script or shell (create/list/retrieve objects).
- Debugging a Stripe integration: interpreting error codes, 4xx/5xx statuses, and retry behavior.
- Fetching related objects efficiently with `expand` instead of N+1 requests.
- Walking large lists (customers, charges, invoices) with cursor pagination.
- Choosing between v1 and v2 endpoints and their different conventions.
- Safely retrying failed POSTs with `Idempotency-Key`.

## Prerequisites

- An API key: test `sk_test_...`, live `sk_live_...`, restricted `rk_...` (recommended; permission-scoped), or publishable `pk_...` (client-side only). The key in use determines sandbox vs live mode.
- Auth via curl basic auth with the key as username and empty password — the trailing colon stops curl's password prompt:
  `curl https://api.stripe.com/v1/charges -u sk_test_BQokikJ...2HlWgH4olfQ2:`
- v2 endpoints additionally require `-H "Stripe-Version: 2026-07-29.dahlia"` and use `-H "Authorization: Bearer <key>"` instead of `-u`.
- All requests over HTTPS; plain HTTP or missing auth fails.

## How to Run

Invoke curl through the `terminal` tool. Use `-G` with `-d` for GET query params, `-X POST` for writes, `-D "-"` to dump response headers (request IDs live there). Never put keys inline in committed code — read from env (`STRIPE_API_KEY`) or a secrets vault.

## Quick Reference

```bash
# Base URL
https://api.stripe.com

# Auth (v1) — colon prevents password prompt
curl https://api.stripe.com/v1/charges -u sk_test_...:

# Auth (v2) — Bearer + required Stripe-Version header
curl -G https://api.stripe.com/v2/core/event_destinations \
  -H "Authorization: Bearer $STRIPE_API_KEY" \
  -H "Stripe-Version: 2026-07-29.dahlia"

# Common v1 endpoints
GET  /v1/customers            # list (paginated)
POST /v1/customers            # create
GET  /v1/customers/cus_123    # retrieve
POST /v1/customers/cus_123    # update
DEL  /v1/customers/cus_123    # delete
GET  /v1/charges, /v1/payment_intents, /v1/products, /v1/prices,
     /v1/subscriptions, /v1/invoices, /v1/refunds, /v1/balance

# Idempotent write
curl https://api.stripe.com/v1/customers \
  -u sk_test_...: \
  -H "Idempotency-Key: KG5LxwFBepaKHyUD" \
  -d description="My First Test Customer"

# Expand a related object / nested / in lists
-d "expand[]=customer"
-d "expand[]=payment_intent.payment_method"   # max 4 levels
-d "expand[]=data.payment_method"             # every item in list

# Metadata
-d "metadata[order_id]=6735"

# Pagination (v1) — cursor based
-d limit=100 -d starting_after={{LAST_OBJECT_ID}}   # next page
-d ending_before={{FIRST_OBJECT_ID}}                # previous page

# Search (v1)
-d query="name:'Jenny' AND metadata['order_id']:'6735'"
-d page={{next_page}}                              # subsequent pages

# Connect / related-account requests
-H "Stripe-Account: acct_1032D82eZvKYlo2C"          # legacy
-H "Stripe-Context: acct_111/acct_111a"             # supersedes; platform/connected
```

## Procedure

### 1. Authenticate

Pick the key for the mode: test (`sk_test_`/`rk_test_`) for sandbox, live (`sk_live_`/`rk_live_`) for real money. Sandbox and live objects never mix — a test product can't be used in a live payment. Restricted keys (`rk_`) limit blast radius and are preferred over secret keys. Only `pk_` publishable keys are safe in frontend code.

### 2. Create an object with idempotency

```bash
curl https://api.stripe.com/v1/customers \
  -u "$STRIPE_API_KEY:" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d description="My First Test Customer" \
  -d "metadata[order_id]=6735"
```
Send `Idempotency-Key` on every POST so a network retry can't double-create. Stripe saves the first response (including errors) per key; v1 replays it for 24 hours, v2 for 30 days (and v2 also retries failed requests without side effects). Keys: up to 255 chars, V4 UUIDs recommended, never sensitive data. Don't send the header on GET/DELETE — it has no effect. Reusing a key with different params returns `409 Conflict`.

### 3. Fetch related data with expand

```bash
curl -G https://api.stripe.com/v1/checkout/sessions/{{SESSION_ID}} \
  -u "$STRIPE_API_KEY:" \
  -d "expand[]=customer" \
  -d "expand[]=payment_intent.payment_method"
```
- Only fields labeled "Expandable" in the API reference can be expanded.
- Max depth is 4 levels (`property1.property2.property3.property4`).
- Lists use the `data` keyword: `expand[]=data.payment_method` expands that property on every item.
- Some properties are excluded by default and only appear when expanded (e.g. Checkout Session `line_items`, Issuing Card `number`/`cvc`).
- Webhook event payloads are ALWAYS minimal — you can't auto-expand; retrieve the object inside your handler.
- Deep expansions on lists are slow — keep them shallow.

### 4. Paginate a list

```bash
# page 1
curl -G https://api.stripe.com/v1/customers -u "$STRIPE_API_KEY:" -d limit=100
# response: { "object":"list", "data":[...], "has_more":true, "url":"/v1/customers" }
# page 2 — pass the last object's ID
curl -G https://api.stripe.com/v1/customers -u "$STRIPE_API_KEY:" \
  -d limit=100 -d starting_after={{LAST_CUSTOMER_ID}}
```
Objects come in reverse chronological order (newest first). Loop while `has_more` is true. `starting_after` and `ending_before` are mutually exclusive; `ending_before` returns pages in chronological order. `limit` ranges 1–100, default 10. v2 lists differ: use the `page` token and follow `next_page_url`/`previous_page_url` from the response, and don't change filters mid-walk.

### 5. Handle errors

Parse the JSON error object: `type` (one of `api_error`, `card_error`, `idempotency_error`, `invalid_request_error`), `code`, `message`, `param`, `decline_code`, `doc_url`, `request_log_url`. The response header `Request-Id` (starts with `req`) identifies the request for support.

| Status | Meaning | Action |
|---|---|---|
| 200 | OK | — |
| 400 | Bad request, missing param | Fix request |
| 401 | No valid API key | Check key |
| 402 | Valid params, request failed (declined card) | Show `message` to user; check `decline_code` |
| 403 | Key lacks permission (RAK scope) | Use a key with the needed permission |
| 404 | Resource doesn't exist | Verify ID |
| 409 | Idempotency key reused with different request | New key, or match original |
| 429 | Rate limited | Exponential backoff + jitter; read `Stripe-Rate-Limited-Reason` header |
| 5xx | Stripe server error (rare) | Retry with backoff; idempotent request so it's safe |

Card declines (`card_error`) are the most common expected error — `402` with a `message` you can surface to the user. For `429`, back off exponentially with randomness (avoid thundering herd); a `429` with code `lock_timeout` means concurrent access to one object — make those requests serial.

### 6. Rate limit budget

Per-account limits: global 100 req/s live (25 in sandbox), 25 req/s per endpoint; Payment Intents capped at 1000 updates/object/hour; Subscriptions at 10 new invoices/sub/minute. Read requests are additionally allocated ~500 per transaction over a rolling 30 days (min 10,000/month); writes are unlimited. Treat limits as maximums and filter list calls to avoid walking everything.

## Pitfalls

- `curl -u sk_test_...` without the trailing colon prompts for a password and hangs interactive shells.
- v1 uses form-encoding (`-d`), v2 uses JSON bodies (`--json`) — mixing them fails.
- v2 REQUIRES the `Stripe-Version` header on every request; v1 pins its version per account (SDKs/CLI pin automatically). Current version: `2026-07-29.dahlia`. Major releases (named) are breaking; monthly releases are backward-compatible.
- No bulk updates — the API works on exactly one object per request.
- Idempotent replays: v1 returns the original response even if it was an error, and only for POST; v2 covers POST and DELETE and retries failed requests. Reusing a key across different endpoints/params errors — use a fresh UUID per logical operation.
- Metadata: max 50 keys, key names ≤40 chars, values ≤500 chars, no square brackets in keys, no sensitive data. v1 removes a key by setting it to `""`; v2 by setting it to `null`.
- `Stripe-Account` is superseded by `Stripe-Context` (supports platform→connected→recipient chains as `acct_111/acct_111a`); both are per-request headers.
- v2 request logs appear in Workbench only, not the Developers Dashboard; v2 events are thin events (no object snapshot).
- Expansions can't cross into webhook payloads — handlers must re-fetch.
- A 429 without the `Stripe-Rate-Limited-Reason` header is a lock timeout, not a rate limit.

## Verification

A real round-trip with a test key — this must return a `200` with a customer object containing the metadata you set:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.stripe.com/v1/customers \
  -u "$STRIPE_API_KEY:" -d "metadata[probe]=1" -d "limit=1" -X GET
```
Expect `200`. A wrong key returns `401`, which also confirms the error-shape handling works.
