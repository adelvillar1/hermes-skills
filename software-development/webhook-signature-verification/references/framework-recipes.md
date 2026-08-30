# Webhook raw-body capture — per-framework recipes

The core problem: signature verification needs the **raw request bytes**, but web frameworks parse JSON before your handler runs. Each framework needs a different capture strategy. All recipes below keep the raw-body handling **scoped to the webhook route only** so the rest of the app keeps its normal JSON parser.

## Fastify

The global JSON parser consumes the stream. Override it inside an **encapsulated plugin scope** so only routes registered in that scope get the buffer parser:

```ts
import type { FastifyInstance } from "fastify";
import Stripe from "stripe";

export async function registerWebhookRoutes(app: FastifyInstance, stripe: Stripe) {
  // Other billing routes inherit the normal JSON parser:
  app.post("/billing/checkout", checkoutHandler);

  await app.register(async (scope) => {
    scope.addContentTypeParser(
      "application/json",
      { parseAs: "buffer" },
      (req, body, done) => {
        const buf = body as Buffer;
        (req as any).rawBody = buf;                       // stash raw bytes
        try { done(null, JSON.parse(buf.toString("utf8"))); }
        catch (e) { done(e as Error, undefined); }
      },
    );

    scope.post("/billing/webhook", async (req, reply) => {
      const sig = req.headers["stripe-signature"];
      if (!sig) return reply.status(400).send({ error: "missing_signature" });
      let event: Stripe.Event;
      try {
        event = stripe.webhooks.constructEvent(
          (req as any).rawBody as Buffer,                 // RAW buffer
          sig,
          process.env.STRIPE_WEBHOOK_SECRET ?? "",        // empty → throws (fail closed)
        );
      } catch {
        return reply.status(400).send({ error: "invalid_signature" });
      }
      await reconcile(event);
      return { received: true };
    });
  });
}
```

Alternative without `as any`: declare a Fastify request decorator (`app.decorateRequest("rawBody", null)`) and set it in the parser, then read `req.rawBody` typed. The `as any` stash is the quick version.

Do **not** call `app.addContentTypeParser("application/json", ...)` at the top level — that replaces the parser for every route in the app.

## Express

Mount `express.raw()` on the webhook path **before** the global `express.json()`:

```js
import express from "express";
import Stripe from "stripe";
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

const app = express();

// Webhook FIRST — needs req.body as a Buffer
app.post("/billing/webhook", express.raw({ type: "application/json" }), (req, res) => {
  const sig = req.headers["stripe-signature"];
  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }
  reconcile(event);
  res.json({ received: true });
});

// Everything else gets normal JSON parsing
app.use(express.json());
```

## Next.js (App Router)

Read the body as text — never `req.json()`:

```ts
// app/api/stripe/webhooks/route.ts
import Stripe from "stripe";
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export const runtime = "nodejs";   // edge runtime can't do raw body the same way

export async function POST(req: Request) {
  const sig = req.headers.get("stripe-signature");
  const rawBody = await req.text();           // RAW text, not req.json()
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig!, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (err) {
    return new Response(`Webhook Error: ${(err as Error).message}`, { status: 400 });
  }
  await reconcile(event);
  return Response.json({ received: true });
}
```

Note: in App Router route handlers there's no automatic body parsing, so `req.text()` already gives you the raw bytes — no special config needed beyond not calling `.json()`.

## Non-Stripe signature schemes

The raw-body rule is identical; only the verify step differs:

- **GitHub** (`X-Hub-Signature-256`): `crypto.timingSafeEqual(Buffer.from("sha256=" + hmacSha256Hex(rawBody, secret)), Buffer.from(sigHeader))`. Use `timingSafeEqual`, not `===`, to avoid timing attacks.
- **Slack** (`X-Slack-Signature`, `X-Slack-Request-Timestamp`): basestring = `v0:${timestamp}:${rawBody}`; HMAC-SHA256 with the signing secret; compare `v0=<hex>` with `timingSafeEqual`. Reject if the timestamp is >5 min old (replay protection).
- **Shopify** (`X-Shopify-Hmac-Sha256`): HMAC-SHA256 of raw body, base64-encoded; compare with the header.

## Why re-serializing the parsed body fails

A tempting "fix" is `JSON.stringify(req.body)` to reconstruct the raw body. This does **not** reproduce the signed bytes: key order may differ, whitespace is normalized, unicode escaping may change, and numeric formatting can shift. The HMAC is over the exact bytes on the wire — you must capture them before parsing. There is no shortcut.
