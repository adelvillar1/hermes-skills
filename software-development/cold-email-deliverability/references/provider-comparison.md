# Email Provider Comparison (for cold outreach)

Pricing and cold-email posture as of 2026. Verify current numbers before quoting — these move.

## Pricing (approximate)

| Volume | Resend | Postmark | AWS SES |
|--------|--------|----------|---------|
| Free tier | 3,000/mo, 100/day | 100 trial emails only | ~62K/mo free if sent from EC2 |
| 10K/mo | $20 | $15 | ~$1 |
| 50K/mo | $20 (Pro) | $60 | ~$5 |
| 100K/mo | $35 | $110 | ~$10 |
| One-time 12K blast | ~$0 (free tier over a few months) | ~$18 | ~$1.20 |

**Raw price winner: SES, then Resend.** For a one-time campaign Resend's free tier can cover the whole thing if spread over the daily cap.

## Cold-email posture (the deciding factor)

| Provider | Stance | Risk for scraped-lead cold outreach |
|----------|--------|--------------------------------------|
| Resend | Permissive | Low — the default choice |
| Postmark | **Prohibits purchased/rented/scraped lists** | **High — accounts suspended mid-campaign** |
| AWS SES | Permissive | Low, but you own reputation/IP management |
| SendGrid / Mailgun | Mixed | Medium — have suspended cold senders; read current ToS |

**Postmark's deliverability is genuinely top-tier** (consistently high inbox-placement in third-party tests) — which is exactly why it's tempting to recommend. But that reputation is maintained by aggressive policing of list quality. A CLIA/registry/Maps-scraped campaign is a ToS violation and a suspension risk at the worst moment. Reserve Postmark for transactional + opt-in email where its strengths apply without the risk.

## Feature notes

- **Resend**: SES-backed, simple API, single stream. Broadcast vs transactional separation is by domain (use separate subdomains). Webhook events via **svix** signatures.
- **Postmark**: separate "Broadcast" vs "Transactional" streams (protects transactional reputation natively), granular open/click tracking, famous support. Best for legitimate opt-in marketing + transactional.
- **SES**: raw infrastructure. Cheapest at scale. You configure IPs, reputation, feedback loops yourself. More ops, most control.

## Rule of thumb

- Scraped/cold leads → **Resend** (or SES at high volume)
- Transactional + opt-in newsletter → **Postmark** or Resend
- High-volume (>100K/mo) with ops capacity → **SES**
