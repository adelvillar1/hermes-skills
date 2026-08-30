---
name: cold-email-deliverability
description: "Use when sending cold/outbound email at scale."
version: 1.0
author: hermes
tags: [email, deliverability, outreach, marketing, resend, postmark, dns, warmup]
related_skills: [government-registry-scraper, draft-feature-plan]
---

# Cold Email Deliverability

Build the infrastructure that gets outbound/cold email into inboxes instead of spam. This is a **deliverability engineering** skill, not a copywriting skill — it covers provider selection, sending-domain architecture, DNS authentication, warmup discipline, and event tracking.

## When to load

- Building or wiring a cold-outreach / sales-email / lifecycle-email sender
- Choosing between email providers (Resend, Postmark, SES, SendGrid, Mailgun)
- Setting up a sending subdomain + DNS auth records
- Designing a warmup ramp or daily send limits
- Wiring bounce/complaint/open/click webhooks + suppression lists
- A user asks "should we use Mautic / a full marketing platform vs a lightweight script?"

## Core principle: reputation is the bottleneck, not quota

When a user wants to "send faster," the instinct is to raise the daily cap or split across more domains to multiply quota. **This is almost always wrong.** Modern mailbox providers (Gmail, Outlook) rate-limit and filter based on **sender reputation**, which is built slowly through consistent low-complaint sending. A fresh domain has zero reputation. Blasting volume on day 1 gets the domain flagged, and a flagged domain recovers slowly if at all.

The actual constraint on cold-email speed is the **warmup ramp** — how fast you can grow daily volume without tripping spam filters. Quota (e.g. 50K/mo) is rarely the binding constraint for a one-time campaign.

**Corollary — splitting across subdomains does NOT double your speed.** Two fresh subdomains each need their own warmup. You save ~1 week on a 12K campaign, not 2×. And every extra subdomain is extra DNS + warmup + monitoring overhead. Use the minimum number of domains that isolates risk (see below).

## Decision 1: Provider selection

For cold outreach specifically, **provider ToS matters more than price or deliverability marketing.** Read the acceptable-use policy before committing.

| Provider | Cold-email stance | Notes |
|----------|-------------------|-------|
| **Resend** | Permissive | Good default for cold B2B. Free tier 3K/mo; Pro ~50K/mo. SES-backed. |
| **Postmark** | **Hostile** | ToS prohibits purchased/rented/**scraped** lists. Accounts suspended mid-campaign for cold outreach. Best-in-class deliverability *because* they police this. Do NOT use for scraped leads. |
| **AWS SES** | Permissive but raw | Cheapest at volume, but you manage reputation/IP yourself. More ops burden. |
| **SendGrid / Mailgun** | Middle | Have been known to suspend cold senders; read current ToS. |

**The Postmark trap is the #1 thing to warn about.** Its deliverability reputation is genuinely excellent, so it's an easy recommendation on quality grounds — but a scraped-lead cold campaign violates its ToS and risks account termination at the worst possible moment. If the lead source is scraped (CLIA, registries, Maps), steer to Resend or SES.

See `references/provider-comparison.md` for the full pricing + feature table.

## Decision 2: Sending-domain architecture

**Never send cold outreach from the root domain or the transactional subdomain.** Cold email always carries some complaint/bounce rate; if it poisons the domain that sends your password resets and receipts, those start hitting spam too.

Recommended split (2 subdomains is usually enough — do NOT pre-build 10):

| Subdomain | Use | Risk profile |
|-----------|-----|--------------|
| root `example.com` | App + transactional (password reset, welcome, receipts) | Pristine — never touches cold |
| `marketing.example.com` | Cold outreach + newsletter + opt-in drips | Takes the reputation hit |

**Why not more subdomains:** each one needs its own SPF + DKIM + DMARC, its own warmup schedule, its own reputation monitoring. For a single 12K-scale campaign, one sacrificial marketing subdomain is right. Add a third (`outreach.`) only if you later want to split cold from opt-in marketing.

**Important nuance — reputation is evaluated at the root domain too.** Gmail/Outlook look at the root domain, not just the subdomain. A heavily-flagged `marketing.example.com` can drag down `example.com`. This is the real reason to keep cold volume conservative, not just a subdomain-isolation argument. Subdomain isolation helps, it is not a firewall.

See `references/dns-setup-godaddy.md` for the record-by-record DNS walkthrough (with the GoDaddy "Name field is relative" gotcha that breaks most first attempts).

## Decision 3: DNS authentication (SPF, DKIM, DMARC)

All three must be configured on the sending subdomain. The provider gives you the exact records — **add the domain in the provider dashboard FIRST, then copy the generated records into DNS.** You don't invent them.

- **SPF** (TXT): authorizes the provider's sending IPs
- **DKIM** (TXT or CNAME): cryptographic signature proving the email wasn't tampered with
- **DMARC** (TXT at `_dmarc.<subdomain>`): policy telling receivers what to do on SPF/DKIM failure

Start DMARC at `p=none` (monitoring only — safe, never blocks). After ~2 weeks of clean sending, tighten to `p=quarantine`. Don't jump to `p=reject` until you're confident.

**Verify from the CLI before the first send** (provider dashboards can show stale "verified"):
```bash
dig +short MX send.marketing.example.com
dig +short TXT send.marketing.example.com          # SPF
dig +short TXT resend._domainkey.marketing.example.com   # DKIM (name varies by provider)
dig +short TXT _dmarc.marketing.example.com        # DMARC
```
DNS propagation: usually 5-30 min, can take up to 24h.

## Decision 4: Warmup ramp

Hard-enforce a ramp in code — **do not leave it as an env var the user can override**, because "I'll just send a little more today" is exactly how domains get flagged.

| Week | Max/day | Cumulative |
|------|---------|------------|
| 1 | 20 | 140 |
| 2 | 50 | 490 |
| 3 | 100 | ~1,200 |
| 4 | 250 | ~3,000 |
| 5+ | 500 | ~6,500+ |

At 500/day steady state, a 12K queue takes ~24 sending days. That's fine — slow sending = high deliverability = more replies. Compute `effective_limit = min(env_cap, ramp_max_for_day, remaining_today)` where `remaining_today = ramp_max - already_sent_today` (count send-log rows with `sent_at` today).

**Gate scaling on real signal, not a calendar.** Don't ramp past the first tier until the first 100 sends show ≥1 reply and ~0 bounces/complaints. If 500 sends produce 0 replies, the messaging is the problem — fix it before sending more.

## Decision 5: Tracking + suppression

You need a **send log** and a **suppression list**, wired to the provider's webhooks.

Send log (one row per send): `entity_id, email, provider_message_id (unique), subject, template_id, status, from_address, campaign_name, sent_at, delivered_at, opened_at, clicked_at, bounced_at, last_error`. Statuses: `queued → sent → delivered → opened → clicked`, terminal `bounced` / `complained`.

Webhook receiver: verify the provider's signature (Resend uses **svix** — `new Webhook(secret).verify(payload, {svix-id, svix-timestamp, svix-signature})`). On `bounced`/`complained`, **auto-insert into the suppression list** (email + domain + reason). Return 200 fast.

**Suppression must be enforced at send time, not just at queue-build time.** A lead can bounce between when the queue was built and when you get to them. Check the suppression list inside the send loop.

**Idempotency:** skip any entity that already has a send-log row for this campaign. Scripts crash mid-run; without this check, a restart double-sends.

## Pitfalls

1. **Postmark for scraped leads** — ToS violation, mid-campaign suspension. Use Resend/SES. (See provider table.)
2. **Splitting across subdomains to "go faster"** — doesn't double speed (each needs warmup), adds ops overhead. Use 1 sacrificial subdomain.
3. **Cold outreach from the root/transactional domain** — poisons password-reset/receipt deliverability. Always a separate marketing subdomain.
4. **Warmup cap as an overridable env var** — users override it and get flagged. Hard-enforce the ramp in code.
5. **HTML emails on a cold campaign** — images, tracking pixels, and HTML increase spam score. Plain text only for v1.
6. **Missing List-Unsubscribe header** — required by Gmail/Yahoo bulk-sender rules; include `List-Unsubscribe: <mailto:reply@...?subject=unsubscribe>`.
7. **Suppression only at queue-build time** — a lead can bounce after the queue is built. Re-check at send time.
8. **No idempotency check** — script crash + restart = double-sends. Check the send log per entity.
9. **Trusting the provider dashboard "verified" over `dig`** — verify DNS from the CLI before the first send.
10. **`$executeRaw` jsonb without `::jsonb` cast** (Prisma) — passing `JSON.stringify(x)` to a jsonb column throws PG `42804`. Add `::jsonb`. (See `postgres-patterns` skill.)

## Verification before first real send

1. `dig` confirms MX + SPF + DKIM + DMARC all resolve on the sending subdomain
2. Send 1 test email to yourself; open headers; confirm `Authentication-Results: dkim=pass header.i=@marketing.example.com`
3. First real batch = **20 emails to the highest-confidence leads only** (e.g. score=5). Pause. Wait ~1 hour. Check send log: expect ~20 delivered, 0 bounced, 0 complained. Only then scale.

## References

- `references/provider-comparison.md` — Resend vs Postmark vs SES pricing + cold-email ToS detail
- `references/dns-setup-godaddy.md` — record-by-record SPF/DKIM/DMARC walkthrough with the GoDaddy relative-Name gotcha
