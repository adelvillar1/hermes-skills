# Send Tracking + Webhooks

## Send log schema

Track every send so you can correlate provider events and compute open/click rates.

```prisma
model email_send_log {
  id           String    @id @default(uuid())
  entityId     String    @map("entity_id")
  email        String                       // the LEAD's real email (not test recipient)
  resendId     String?   @unique @map("resend_id")  // provider correlation key
  subject      String
  templateId   String    @map("template_id")        // for A/B variant comparison
  status       String    @default("queued")         // queued|sent|delivered|opened|clicked|bounced|complained
  fromAddress  String    @map("from_address")
  campaignName String    @map("campaign_name")
  sentAt       DateTime? @map("sent_at")
  deliveredAt  DateTime? @map("delivered_at")
  openedAt     DateTime? @map("opened_at")
  clickedAt    DateTime? @map("clicked_at")
  bouncedAt    DateTime? @map("bounced_at")
  lastError    String?   @map("last_error")
  createdAt    DateTime  @default(now()) @map("created_at")
  @@index([entityId]) @@index([status]) @@index([campaignName, sentAt])
  @@map("email_send_log") @@schema("leads")
}
```

## Crash-safe send sequence

Insert the send_log row **before** calling the provider, then update with the provider
id on success. If the process crashes mid-send, the row still marks the lead as
attempted (idempotency on re-run).

```ts
const [logRow] = await prisma.$queryRaw`
  INSERT INTO leads.email_send_log (id, entity_id, email, subject, template_id, status, from_address, campaign_name, sent_at)
  VALUES (gen_random_uuid(), ${lead.id}, ${lead.email}, ${subject}, ${tpl.id}, 'sent', ${from}, ${campaign}, NOW())
  RETURNING id`;

const { data, error } = await resend.emails.send({ from, to: recipient, replyTo, subject, text: body });

if (error) {
  await prisma.$executeRaw`UPDATE leads.email_send_log SET status='queued', last_error=${error.message} WHERE id=${logRow.id}`;
} else {
  await prisma.$executeRaw`UPDATE leads.email_send_log SET resend_id=${data?.id ?? null} WHERE id=${logRow.id}`;
}
```

## Idempotency

Skip leads already in send_log for this campaign — prevents double-sends on crash/restart:

```sql
WHERE NOT EXISTS (
  SELECT 1 FROM leads.email_send_log sl
  WHERE sl.entity_id = q.id AND sl.campaign_name = ${campaign}
)
```

## Webhook receiver (Resend)

Verify the svix signature, then dispatch on event type. Return 200 quickly.

```ts
import { Webhook } from 'svix';  // npm install svix

const wh = new Webhook(process.env.RESEND_WEBHOOK_SECRET!);
const payload = await req.text();
wh.verify(payload, {
  'svix-id': req.headers.get('svix-id')!,
  'svix-timestamp': req.headers.get('svix-timestamp')!,
  'svix-signature': req.headers.get('svix-signature')!,
});
const event = JSON.parse(payload);  // { type, data: { email_id, to: string[] } }
```

Event handling (correlate via `data.email_id` = `resend_id`):

| Event | Action |
|-------|--------|
| `email.delivered` | status='delivered', delivered_at=NOW() |
| `email.opened` | opened_at=NOW(), status='opened' (skip if bounced/complained) |
| `email.clicked` | clicked_at=NOW(), status='clicked' |
| `email.bounced` | status='bounced', bounced_at, last_error + **suppress lead** |
| `email.complained` | status='complained' + **suppress lead** |

Suppress via `resend_id` → send_log.email (see safety-gate-pattern.md — NOT `data.to`).

Register the webhook URL in the provider dashboard pointing at your deployed endpoint.

## Admin dashboard metrics

- Queue status cards: in-queue, sent, delivered, opened, clicked, bounced, complained
- Daily send volume (last 30 days) — CSS bars, no chart lib needed
- Template performance: per templateId sent/opened/clicked + open rate % + click rate %
- Recent sends table (last 50): email, subject, template, status, sent_at
