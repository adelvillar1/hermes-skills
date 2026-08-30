# DNS Setup for a Sending Subdomain (GoDaddy example)

The order matters: **add the domain in the provider dashboard FIRST.** The provider generates the exact DNS records to add — you copy them into your registrar, you don't invent them.

## Step 1 — Add the domain in the provider (Resend example)

1. Resend → **Domains** → **Add Domain**
2. Enter the full subdomain: `marketing.example.com`
3. Region: `us-east-1` (closest to recipients)
4. Add → Resend shows a list of records, roughly:
   - `MX`  host `send`  → `feedback-smtp.us-east-1.amazonses.com` (priority 10)
   - `TXT` host `send`  → `v=spf1 include:amazonses.com ~all`
   - `TXT` host `resend._domainkey` → `p=MIGfMA0...` (DKIM public key)
   - `CNAME` × 3 (DKIM CNAMEs, hash-prefixed hosts)
   - `TXT` host `_dmarc` → suggested DMARC

Keep this tab open.

## Step 2 — Add records in GoDaddy

GoDaddy → your domain → **DNS** → **Add New Record** for each.

### The #1 gotcha: GoDaddy's "Name" field is RELATIVE to the root domain

When you verify a **subdomain** (`marketing.example.com`), the provider's host values are relative to that subdomain. In GoDaddy you must append the subdomain part:

| Provider shows (Host) | Type in GoDaddy (Name) | Resulting FQDN |
|---|---|---|
| `send` | `send.marketing` | `send.marketing.example.com` |
| `resend._domainkey` | `resend._domainkey.marketing` | `resend._domainkey.marketing.example.com` |
| `_dmarc` | `_dmarc.marketing` | `_dmarc.marketing.example.com` |
| `76e...` (CNAME) | `76e....marketing` | `76e....marketing.example.com` |

Typing just `send` creates the record on the **root** domain — the most common failure. Match the full FQDN the provider expects. (Some provider UIs show the full expected hostname — match that exactly.)

TTL: leave default (1h / Automatic). Save each record.

## Step 3 — Verify

In the provider dashboard: **Verify DNS Records** (goes green when propagated).

Independently, from the CLI (don't trust the dashboard alone — it can show stale state):
```bash
dig +short MX send.marketing.example.com
dig +short TXT send.marketing.example.com                 # SPF
dig +short TXT resend._domainkey.marketing.example.com    # DKIM
dig +short TXT _dmarc.marketing.example.com               # DMARC
```
Propagation: usually 5-30 min, up to 24h.

## Step 4 — DMARC policy

Provider default is `p=none` (monitoring only). Recommended record:
```
Type: TXT   Name: _dmarc.marketing
Value: "v=DMARC1; p=none; rua=mailto:dmarc@example.com"
```
After ~2 weeks clean sending → `p=quarantine`. Don't go `p=reject` until confident. `rua=` gets you aggregate reports.

## Note: DKIM record type varies by provider

Resend exposes DKIM as a **TXT** record at `resend._domainkey.<subdomain>` (a `p=...` public key). Other providers (SES, some Resend configs) use **CNAME** DKIM records with hash-prefixed hosts. Copy whatever the provider gives you — don't assume the type.
