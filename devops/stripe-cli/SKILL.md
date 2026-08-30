---
name: stripe-cli
description: "Operate Stripe: webhooks, triggers, logs, resources."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Stripe, CLI, Webhooks, Payments, Testing]
---

# Stripe CLI

Drive a Stripe integration from the command line: authenticate, call the API for any resource, tail request logs, and test webhooks locally via `listen`/`trigger`. This skill covers the official `stripe` binary as documented at https://docs.stripe.com/stripe-cli/use-cli and https://docs.stripe.com/cli. It does NOT cover server-side Stripe SDK billing logic (see `stripe-billing` for that).

## When to Use

- Testing a webhook handler locally without a tunnel (no Dashboard endpoint needed).
- Triggering Stripe events (`checkout.session.completed`, `payment_intent.succeeded`, ...) to exercise an integration.
- Creating test products, prices, customers, or payment intents from the terminal.
- Debugging API errors via real-time request logs.
- Standing up test-mode credentials without a Stripe account (sandbox).
- Reading API docs from the terminal without a browser.

## Prerequisites

- Install: `npm install -g @stripe/cli` (Node.js 18+). Run ad-hoc with `npx @stripe/cli <cmd>` (does not add `stripe` to PATH). Upgrade: `npm update -g @stripe/cli`.
- Auth (pick one, in precedence order):
  - `stripe login` — browser pairing; persists a restricted key locally.
  - `stripe login --interactive` — paste an existing secret key (CI-safe).
  - `stripe sandbox create --from-git --non-interactive` — throwaway test keys, no account; expires in 7 days, convert later with `stripe sandbox claim`.
  - `--api-key sk_test_...` flag, or env var `STRIPE_API_KEY` (highest precedence), or `stripe config --set test_mode_api_key sk_test_123`.
- Config lives at `~/.config/stripe/config.toml` (override with `XDG_CONFIG_HOME`); not removed on uninstall. Per-project configs via `--project-name <name>`.
- Telemetry is on by default; disable with `STRIPE_CLI_TELEMETRY_OPTOUT=1`.

## How to Run

All commands below are invoked through the `terminal` tool. `stripe listen` and `stripe logs tail` are long-running streams — start them with `terminal(background=true)`, or run `stripe listen --print-secret` for a one-shot. Keep `listen` open in one terminal while triggering events from another.

## Quick Reference

```bash
stripe login [--interactive] [--project-name=<name>]   # auth
stripe sandbox create --email <addr> | --from-git [--non-interactive]
stripe sandbox claim [--non-interactive]               # keep sandbox before 7-day expiry
stripe config --set <option> <value> | --unset | --list | --edit
stripe logout

stripe listen [--forward-to <url>] [--events a,b] [--load-from-webhooks-api] [--print-secret] [--skip-verify] [--latest] [--live]
stripe trigger <event> [--override res:path=val] [--add res:path=val] [--remove res:path] [--skip step] [--edit] [--stripe-account <id>]
stripe events resend <event_id> --webhook-endpoint=we_123456 [--account=<acct_id>] [-c]
stripe trigger --help                                 # list supported events

stripe logs tail [--filter-http-method POST] [--filter-status-code-type 4XX] [--filter-request-path /v1/charges] [--format <fmt>]

stripe products create --name="My First Product" --description="Created with the Stripe CLI"
stripe prices create --unit-amount=3000 --currency=usd --product="prod_..."
stripe customers create --email=billing@example.com --name="Jenny Rosen"
stripe customers retrieve cus_9s6XKzkNRiz8i3
stripe customers update cus_9s6XKzkNRiz8i3 -d "metadata[key]=value"
stripe resources                                    # list all API resources

stripe get /v1/... | stripe post /v1/... | stripe delete /v1/...   # raw HTTP
stripe fixtures ./fixtures.json                     # scripted multi-request flows

stripe docs /payments | stripe docs api product | stripe docs api charge.succeeded | stripe docs search "dispute evidence" [--no-pager] [--non-interactive]
stripe open dashboard/webhooks [--live] [--list]
stripe completion [--shell zsh]                     # bash/zsh on macOS/Linux
stripe version | stripe feedback

# API version pinning on any request:
stripe products create --name="My Product" --stripe-version 2026-07-29.dahlia
stripe products create --name="My Product" --latest
```

## Procedure

### 1. Authenticate

```bash
stripe login            # press Enter, confirm in browser
```
No browser? `stripe login --interactive` and paste a secret key. For a throwaway env: `stripe sandbox create --from-git --non-interactive` (keys auto-saved to profile).

### 2. Test a webhook endpoint locally

In one terminal (background via `terminal`):
```bash
stripe listen --events payment_intent.created,customer.created,payment_intent.succeeded,charge.succeeded,checkout.session.completed,charge.failed \
  --forward-to http://localhost:4242/webhook
```
Output prints `Ready! Your webhook signing secret is 'whsec_...' (^C to quit)` — capture that secret and configure it in the app for signature verification (it is stable across `listen` restarts). No Dashboard webhook endpoint is required. To mirror an already-registered endpoint instead: `stripe listen --load-from-webhooks-api --forward-to http://localhost:4242` (path + event list are parsed from your registered endpoint).

In a second terminal, fire the event:
```bash
stripe trigger checkout.session.completed
```
Watch the `listen` window show `--> checkout.session.completed [evt_...]`. To grab just the secret without streaming: `stripe listen --print-secret`.

### 3. Create a product and price (one-time)

```bash
stripe products create --name="My First Product" --description="Created with the Stripe CLI"
# -> "id": "prod_LTenIrmp8Q67sa"
stripe prices create --unit-amount=3000 --currency=usd --product="prod_LTenIrmp8Q67sa"
# -> "id": "price_1KzlAMJJDeE9fu01WMJJr79o"
```
`--unit-amount` is in the smallest currency unit (3000 = $30.00 USD).

### 4. Tail API request logs

```bash
stripe logs tail --filter-http-method POST --filter-status-code-type 4XX
```
Line format: `2022-01-28 09:47:46 [200] POST /v1/customers [req_abc123]`. Filters AND together; comma-separated values OR within a filter. Test mode only.

### 5. Script a multi-step flow with fixtures

Write a JSON fixture (see `templates/fixtures-example.json`) and run it:
```bash
stripe fixtures ./fixtures.json
```
Fixtures chain requests: `${cus_jenny_rosen:id}` references a prior named request's response attribute; `${.env:EMAIL|jane@stripe.com}` reads env with a default; list access `${res:subscriptions.data.#.id}`.

## Pitfalls

- `stripe trigger` creates real API objects as side effects and can fire cascading events (e.g. `payment_intent.succeeded` also emits `payment_intent.created`). It runs in test mode by default; `--live` sends live requests.
- `stripe logs tail` only shows **test mode** logs.
- Override syntax uses `resource:path.sub=value`; bracket indexing must be quoted: `--override "checkout_session:line_items[0].quantity=10"` (shell eats the brackets otherwise).
- `stripe trigger --edit` cannot be combined with `--add`/`--remove`/`--override`/`--skip`.
- Shell completion is bash/zsh on macOS/Linux only — not Windows.
- `stripe login` can't persist keys inside ephemeral Docker containers; use `docker run --rm -it stripe/stripe-cli listen --api-key sk_test_...` or the `STRIPE_API_KEY` env var.
- Webhook events received depend on your account's default API version unless you pass `--latest` or `--stripe-version`; the CLI secret is `whsec_...`, distinct from API keys.
- Sandbox credentials (`rkcs_test_...`) expire after 7 days — run `stripe sandbox claim` to keep them.
- Uninstalling the CLI does not remove `~/.config/stripe/config.toml` (contains saved keys).
- `listen` default is snapshot events; thin events require explicit `--thin-events` / `--forward-thin-to`.

## Verification

```bash
stripe version          # binary works
stripe trigger --help   # lists supported events, no auth/API needed
```
Full proof: with `stripe listen --forward-to http://localhost:4242/webhook` running, `stripe trigger payment_intent.succeeded` should print `Trigger succeeded!` and the `listen` stream should print `--> payment_intent.succeeded [evt_...]`.
