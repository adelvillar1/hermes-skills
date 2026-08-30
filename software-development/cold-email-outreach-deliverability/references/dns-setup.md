# DNS Setup for Sending (SPF / DKIM / DMARC)

## Order of operations

The DNS records come **from the provider** — you don't invent them.

1. Add the domain in the provider dashboard FIRST (e.g. Resend → Domains → Add Domain).
2. The provider generates the DNS records (MX, SPF TXT, DKIM, DMARC suggestion).
3. Copy each record into your DNS host (GoDaddy, Cloudflare, Route53).
4. Click "Verify DNS Records" in the provider dashboard.
5. Propagation: usually 5-30 min, can take up to 24h.

## The #1 gotcha: relative host names (GoDaddy)

Provider "Host" values are **relative to the subdomain being verified**. DNS hosts
typically want the *relative* part in the Name field, which they append to the root.

For verifying `marketing.example.com`:

| Provider shows (Host) | You type in GoDaddy (Name) | Resulting record |
|---|---|---|
| `send` | `send.marketing` | `send.marketing.example.com` |
| `resend._domainkey` | `resend._domainkey.marketing` | `resend._domainkey.marketing.example.com` |
| `_dmarc` | `_dmarc.marketing` | `_dmarc.marketing.example.com` |
| `76e...` (CNAME) | `76e....marketing` | `76e....marketing.example.com` |

The most common failure is typing just `send` instead of `send.marketing`, creating
the record on the wrong domain. **Match the full hostname the provider expects.**

## Verify from the command line

```bash
dig +short MX send.marketing.example.com
dig +short TXT send.marketing.example.com          # SPF
dig +short TXT resend._domainkey.marketing.example.com  # DKIM (TXT key)
dig +short TXT _dmarc.marketing.example.com        # DMARC
```

Note: some providers use DKIM as a CNAME at a hash-prefixed name rather than a TXT
at `resend._domainkey`. If the TXT lookup is empty, check the provider's exact record
list — don't assume it's missing.

## DMARC policy lifecycle

Provider default is `p=none` (monitoring only — safe, won't block sends).

```
# Initial (monitoring)
"v=DMARC1; p=none; rua=mailto:dmarc@example.com"

# After ~2 clean weeks (tighten)
"v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; pct=100"
```

Don't jump to `p=reject` until confident. `quarantine` is the right steady state for
a small sender. Gmail/Outlook increasingly check for a DMARC record, so add one even
though providers don't strictly require it.
