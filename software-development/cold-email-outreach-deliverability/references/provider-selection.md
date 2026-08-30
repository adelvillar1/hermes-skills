# Provider Selection for Cold Outreach

## The key insight: ToS risk > price > features

For cold email (scraped or purchased lists), the provider's **acceptable-use policy**
is the deciding factor, not deliverability benchmarks or pricing. A provider with
perfect inbox placement that suspends your account mid-campaign is worthless.

## Comparison (as of 2026)

| Factor | Resend | Postmark | SES |
|--------|--------|----------|-----|
| **Cold email policy** | Permissive | **Prohibits scraped/purchased lists** | Permissive (AWS ToS) |
| **Account suspension risk** | Low | **High** — actively polices | Low |
| **Deliverability reputation** | Good | Best-in-class | Good (depends on config) |
| **Free tier** | 3,000/mo, 100/day | 100 trial emails only | 62K/mo (from EC2) |
| **50K/mo cost** | ~$20 (Pro plan) | ~$60 | ~$5 |
| **Setup friction** | 5 min (API key + domain) | 30+ min (sender review, can reject) | High (IAM, config sets) |
| **Webhook/tracking** | Yes (svix-signed) | Yes, granular | SNS notifications |
| **Support** | Email | Famous fast human support | AWS tiers |

## Recommendation by use case

- **Cold outreach to scraped/curated lists → Resend.** Permissive ToS, cheap,
  fast setup, good enough deliverability. The deliverability gap vs Postmark is
  smaller than the gap between "properly warmed domain with SPF/DKIM/DMARC" and
  "not" — domain setup matters more than provider choice.
- **Transactional email (password resets, receipts) → Postmark or SES.**
  Best deliverability where it matters most, and these are opt-in so ToS is fine.
- **High-volume newsletter (opt-in) → SES or Resend.** Cheapest at scale.

## Why NOT Postmark for cold email

Postmark's [Acceptable Use Policy](https://postmarkapp.com/policies) explicitly
prohibits "purchased, rented, or scraped lists." Their deliverability is great
*because* they police this aggressively — accounts get suspended mid-campaign for
cold B2B outreach. This is a real, documented risk, not theoretical.

## Resend specifics

- SDK: `npm install resend` — `import { Resend } from 'resend'`
- Webhooks: svix-signed. Verify with `new Webhook(secret).verify(payload, headers)`.
  Secret from Resend dashboard → Webhooks → Signing secret.
- Event types: `email.delivered`, `email.opened`, `email.clicked`, `email.bounced`,
  `email.complained`. Payload shape: `{ type, data: { email_id, to: string[], ... } }`.
- `resend.emails.send()` returns `{ data: { id }, error }` — the `id` is the
  correlation key for webhooks (`data.email_id`).
- Pro plan: 50K emails/mo. Daily send limit configurable in dashboard.
