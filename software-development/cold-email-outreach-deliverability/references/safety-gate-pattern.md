# Recipient-Whitelist Safety Gate

The structural pattern that makes it impossible to email a real lead before templates
are approved. This is the most important code in a cold outreach system.

## The gate

```ts
// HARD RULE: no real sends until templates approved.
const TEST_RECIPIENT = 'user@example.com';
const ALLOW_REAL_SENDS = args.includes('--allow-real-sends');

// In the send loop:
const baseSubject = tpl.subject(shape);
const subject = ALLOW_REAL_SENDS ? baseSubject : `[TEST] ${baseSubject}`;
const recipient = ALLOW_REAL_SENDS ? lead.email : TEST_RECIPIENT;

await resend.emails.send({ from, to: recipient, replyTo, subject, text: body });
```

Key properties:
- **Single assignment point** — `recipient` is assigned once and used once at the
  `to:` field. No other send path exists. No env-var override. Reviewers can verify
  "structurally unbypassable" by tracing the one variable.
- **`[TEST]` subject prefix** makes test emails obvious in the inbox.
- **Default is safe** — forgetting the flag means test mode, never a real blast.

## The webhook correlation gotcha (critical)

During test mode, `resend.emails.send()` sends to `TEST_RECIPIENT`, but the
send-tracking log stores `lead.email`. When a bounce/complaint webhook fires, the
provider's `data.to` is the **test address**, not the lead.

**Wrong:** suppress `data.to[0]` from the webhook → adds `user@example.com` to the
suppression list (data pollution) and never suppresses the actual lead, so the lead
gets re-contacted once real sends are enabled.

**Right:** correlate the webhook event to the send_log row via the provider email id
(`resend_id`), then suppress the `email` column from send_log:

```ts
async function suppressRecipient(resendId: string, reason: string) {
  const rows = await prisma.$queryRaw`
    SELECT email FROM leads.email_send_log WHERE resend_id = ${resendId} LIMIT 1`;
  const email = rows[0]?.email;
  if (!email) return;
  const domain = email.includes('@') ? email.split('@')[1] : null;
  await prisma.$executeRaw`
    INSERT INTO leads.suppression_list (id, email, domain, reason, added_at)
    VALUES (gen_random_uuid(), ${email}, ${domain}, ${reason}, NOW())
    ON CONFLICT (email) DO NOTHING`;
}
```

This requires logging the real `lead.email` (not the test recipient) in send_log even
during test mode — which the gate above already does.

## Lifting the gate

When the user approves templates, they run with `--allow-real-sends`. The warmup ramp
still applies (day 1 = 20/day). The gate and the ramp are independent safety layers —
the gate controls *who*, the ramp controls *how many*.
