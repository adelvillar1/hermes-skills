# Subdomain Strategy for Sending

## The model: sacrificial vs pristine

| Subdomain | Use | Risk profile |
|-----------|-----|--------------|
| `mail.example.com` | Transactional (password resets, welcome, receipts) | Pristine — never touches cold |
| `marketing.example.com` | Cold outreach, newsletter, drips | Sacrificial — takes the reputation hit |
| `outreach.example.com` | (Optional) second cold stream if volume demands | Also sacrificial |

Cold outreach is the *riskiest* email you send (scraped list, some complaint rate
is inevitable). It gets the sacrificial subdomain. Transactional gets the clean name.

## Why NOT split cold volume across transactional "to go faster"

Users often ask: "can we split the load between both domains to reach leads faster?"

**The bottleneck isn't quota, it's reputation.** The actual constraint is warmup —
how fast you can ramp daily volume before Gmail/Outlook flag you. Splitting across
two domains saves ~1 week on a 12K campaign (4 weeks vs 5). Not worth the risk.

**The real danger:** Gmail and Outlook evaluate reputation at the **root domain
level too**, not just subdomain. If `marketing.example.com` gets flagged for spam,
it can drag down `mail.example.com` (password resets) and the root domain. Subdomain
isolation helps but is not a firewall. The more cold volume you push, the more risk
you put on the root domain your business depends on.

**If you genuinely need more throughput:** add a *third* sacrificial subdomain
(`outreach.example.com`), never reuse the transactional one.

## When N subdomains make sense

- Sending 100K+/month
- Distinct streams you want reputation-isolated (cold vs newsletter vs transactional)
- Parallel campaigns with different content/audiences

**For a 12K one-time campaign: one sacrificial subdomain is plenty.** Don't pre-build
infrastructure you won't use. Each extra subdomain = separate SPF/DKIM/DMARC, separate
warmup (2-3 weeks each), separate reputation to monitor.

## Cost of each extra subdomain

- Separate SPF + DKIM + DMARC DNS records
- Separate warmup schedule
- Separate reputation to monitor
- More DNS clutter to manage
