---
name: cold-email-outreach-deliverability
description: "Build cold email outreach that lands in the inbox."
tags: [email, deliverability, outreach, resend, marketing, lead-generation]
related_skills: [webhook-signature-verification, government-registry-scraper]
version: 1.0.0
---

# Cold Email Outreach & Deliverability

Build outreach systems that actually reach the inbox without burning the sender's
domain reputation. The deliverability game is won or lost on **domain reputation**,
not on the email provider or the copy — every decision here optimizes for that.

## When to use

- Sending bulk cold B2B email (scraped/curated lead lists)
- Choosing between sending providers (Resend, Postmark, SES, etc.)
- Setting up sending subdomains + DNS (SPF/DKIM/DMARC)
- Warming up a new sending domain
- Wiring open/click/bounce tracking via webhooks
- Any time the user says "send emails to my leads" / "marketing outreach" / "cold email"

## Hard safety rule — recipient whitelist until templates approved

**Never send to real leads until the user has explicitly approved the email
templates.** This is a recurring user directive and the single most important rule
in this skill. Build it into the send script as a **structural gate**, not a
comment or a flag the user might forget:

- Default mode redirects EVERY send to a designated test address (the user's own
  inbox), regardless of what the lead query returns.
- Lifting the gate requires an explicit opt-in flag (e.g. `--allow-real-sends`).
- Tag test subjects with `[TEST]` so they're obvious in the inbox.
- Log the *real* lead email in the send-tracking table even during test mode — so
  bounce/complaint correlation still targets the actual lead (see webhook pitfall).

```ts
const TEST_RECIPIENT = 'user@example.com';
const ALLOW_REAL_SENDS = args.includes('--allow-real-sends');
// ...
const recipient = ALLOW_REAL_SENDS ? lead.email : TEST_RECIPIENT;
const subject = ALLOW_REAL_SENDS ? baseSubject : `[TEST] ${baseSubject}`;
```

This makes it impossible to email a real lead by accident. See
`references/safety-gate-pattern.md` for the full implementation and the webhook
correlation gotcha.

## The five pillars

1. **Provider selection** — for cold outreach, the provider's *acceptable-use
   policy* matters more than price or features. Postmark has best-in-class
   deliverability but **prohibits scraped/purchased lists** and suspends accounts
   mid-campaign; Resend is permissive and cheap. See `references/provider-selection.md`.

2. **Subdomain strategy** — send cold outreach from a **sacrificial subdomain**
   (`marketing.` / `outreach.`), never the root domain or the transactional
   subdomain. Reputation isolates *mostly* but not fully at the subdomain level —
   Gmail/Outlook also weigh the root domain, so don't split cold volume across the
   transactional subdomain "to go faster." See `references/subdomain-strategy.md`.

3. **DNS foundation** — SPF + DKIM + DMARC on the sending subdomain, verified
   before any send. DMARC starts at `p=none` (monitoring), tightens to
   `p=quarantine` after ~2 clean weeks. See `references/dns-setup.md`.

4. **Warmup ramp** — a brand-new subdomain has zero reputation. Ramp daily volume
   over ~5 weeks regardless of quota: 20 → 50 → 100 → 250 → 500/day. Enforce the
   ramp **in code** (compute from first-send date), not via an env var the user can
   accidentally set to 10000. See `references/warmup-ramp.md`.

5. **Send tracking + suppression** — log every send, ingest provider webhooks
   (delivered/opened/clicked/bounced/complained), and auto-suppress bounces and
   complaints immediately. Honor `List-Unsubscribe`. See `references/tracking-webhooks.md`.

## Plain-text-first cold email

Cold emails should be **plain text, no HTML, no images, no tracking pixels** in v1.
HTML + images + pixels are spam-classifier signals. Personalize beyond `{first_name}`
— reference the recipient's company, city, or specialty. Keep a `List-Unsubscribe`
header and honor suppressions the instant a complaint lands.

## Workflow

1. Confirm provider (default Resend for cold lists — see provider-selection).
2. Set up sacrificial sending subdomain + DNS (dns-setup), verify in provider dashboard.
3. Build send script with: recipient-whitelist safety gate, warmup ramp enforced in
   code, suppression check at send time, idempotency (no double-sends on crash),
   send-tracking log writes.
4. Build webhook receiver with signature verification → update send log → auto-suppress
   bounces/complaints (correlate via provider's email id, not the `to` address).
5. Send test batch to the user's own address. **Wait for explicit template approval.**
6. Lift the gate, start the warmup ramp, monitor bounce/complaint rates. If 0 replies
   from ~500 sends, revisit messaging before scaling.

## Pitfalls

- **Don't split cold volume across the transactional subdomain to "go faster."** The
  time saved (~1 week) isn't worth risking password-reset/welcome email deliverability.
  If you need more throughput, add a *third* sacrificial subdomain, never reuse `mail.`.
- **Don't suppress the webhook's `to` address during test mode** — it's the test
  recipient, not the lead. Correlate via the provider email id → send_log.email.
- **Don't trust the warmup limit to an env var.** A user who sets `DAILY_LIMIT=10000`
  on day 1 will torch the domain. Compute the cap from first-send date in code.
- **Don't pre-build 10 subdomains.** One sacrificial subdomain handles a 12K campaign
  comfortably. Add more only when volume genuinely demands it (100K+/mo).
- **Don't skip the test-approval gate** even if the user seems eager to send. Cold
  email to a scraped list with unreviewed copy is how domains get blacklisted.

## See also

- `references/provider-selection.md` — Resend vs Postmark vs SES for cold outreach
- `references/subdomain-strategy.md` — sacrificial vs pristine subdomains, why not to split
- `references/dns-setup.md` — SPF/DKIM/DMARC records + GoDaddy host-field gotcha
- `references/warmup-ramp.md` — ramp schedule + in-code enforcement
- `references/safety-gate-pattern.md` — recipient whitelist + webhook correlation gotcha
- `references/tracking-webhooks.md` — send log schema + Resend webhook event handling
