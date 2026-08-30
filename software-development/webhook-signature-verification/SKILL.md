---
name: webhook-signature-verification
description: Receive and verify HMAC-signed webhooks from third-party providers (Stripe, GitHub, Slack, Shopify, etc.) in any web framework. The core gotcha — signature verification needs the RAW request body bytes, but frameworks parse JSON before your handler runs — plus per-framework recipes and the security checklist (auth/CSRF exemption, fail-closed secret, idempotent reconciliation).
version: 1.0.0
triggers:
  - "webhook"
  - "verify webhook signature"
  - "stripe webhook"
  - "github webhook"
  - "constructEvent"
  - "x-hub-signature"
  - "webhook returns 400 / invalid signature"
---

# Webhook Signature Verification

Inbound webhooks from providers (Stripe, GitHub, Slack, Shopify…) are authenticated with an HMAC signature over the **raw request body**. Your handler must verify that signature before trusting the payload. The single most common integration bug: the framework's JSON body parser consumes the request stream and hands you a parsed object, so you no longer have the exact bytes that were signed — verification then fails (or, if you skip it, you accept forged events).

## The core rule

`verify(signature, rawBodyBytes, secret)` — you MUST pass the **raw body bytes**, not `JSON.parse`d output, not a re-serialized object (key order/whitespace differ → HMAC mismatch). Capture the raw bytes **before** any JSON parsing.

## Per-framework recipes

Each framework parses the body differently. See `references/framework-recipes.md` for full code. Summary:

| Framework | How to get the raw body |
|-----------|------------------------|
| **Fastify** | Encapsulated plugin + `addContentTypeParser("application/json", { parseAs: "buffer" })` that stashes the buffer on `req.rawBody` then hands parsed JSON to the handler. Scoped so only the webhook route is affected. |
| **Next.js (App Router)** | `export const runtime = "nodejs"`; read `await req.text()` (NOT `req.json()`); pass that string to verify. |
| **Express** | `express.raw({ type: "application/json" })` on the webhook route ONLY (mount before the global `express.json()`), so `req.body` is a Buffer. |

### Fastify (proven pattern)

The global JSON parser consumes the body, so capture the raw buffer in an **encapsulated plugin scope** — this overrides the parser only inside the webhook's scope, leaving every other route on the normal parser:

```ts
export async function registerWebhookRoutes(app: FastifyInstance, deps: Deps) {
  app.post("/billing/checkout", checkoutHandler);   // normal JSON parser (inherited)

  await app.register(async (scope) => {             // encapsulated — scoped parser
    scope.addContentTypeParser(
      "application/json",
      { parseAs: "buffer" },
      (req, body, done) => {
        const buf = body as Buffer;
        (req as any).rawBody = buf;                 // stash raw bytes for verify
        try { done(null, JSON.parse(buf.toString("utf8"))); }
        catch (e) { done(e as Error, undefined); }
      },
    );
    scope.post("/billing/webhook", async (req, reply) => {
      const sig = req.headers["stripe-signature"];
      if (!sig) return reply.status(400).send({ error: "missing_signature" });
      let event: Stripe.Event;
      try {
        event = getStripe().webhooks.constructEvent(
          (req as any).rawBody as Buffer,           // the RAW buffer, not req.body
          sig,
          process.env.STRIPE_WEBHOOK_SECRET ?? "",
        );
      } catch {
        return reply.status(400).send({ error: "invalid_signature" });
      }
      // ... reconcile from event, return { received: true }
    });
  });
}
```

## Security checklist (every webhook route)

1. **Verify the signature on the raw body** before touching the payload. Reject with 400 on missing/invalid signature.
2. **Exempt the route from CSRF and session/cookie auth.** The webhook authenticates via signature, not cookies — if your global CSRF guard or `requireSession` runs on it, providers get 403/401 and your state never syncs. Add the path to the CSRF exempt-paths set.
3. **Empty/unset secret must FAIL CLOSED.** `constructEvent` with an empty secret throws on HMAC mismatch (good). Never write a `if (!secret) return ok` shortcut — that accepts every forged event.
4. **Reconcile from the object's current state, not the event sequence.** Providers don't guarantee ordering and they retry. Make the handler **idempotent on replay** — upsert by the provider's stable id (e.g. `stripe_customer_id`), derive state from the subscription/resource snapshot, never assume "created came before updated."
5. **Grant access on provisional states.** For subscriptions, `trialing` must grant the tier (users need access during trial): flip entitlement when `status ∈ {active, trialing}`, not only `active`.
6. **Don't clobber manual overrides on cancellation.** Before downgrading a deleted/canceled subscription to the free tier, re-check any complimentary/manual-promotion list so an operator's override survives the webhook.
7. **Return 2xx promptly.** Do the DB work, return `{ received: true }` / `200`. Long work should be queued; a slow 200→timeout makes the provider retry and amplifies load.

## Testing

- **Unit:** mock the SDK's verify (`constructEvent`) to return a canned event; assert your handler upserts the right rows and is idempotent when the same event is delivered twice.
- **Negative:** send a request with a wrong/missing signature → expect 400, no DB writes. Send with an unset secret → expect rejection (fail closed), not acceptance.
- **Live (test mode):** trigger a real event with the provider's test fixtures (Stripe test card `4242 4242 4242 4242`, `stripe trigger`, or CLI `stripe listen --forward-to`) and assert the DB reconciled.

## Pitfalls

- **Re-serializing the parsed body to "recover" the raw bytes does not work** — JSON.stringify won't reproduce the exact byte order/whitespace the provider signed. You must capture the original buffer.
- **Overriding the JSON parser globally** (Fastify `addContentTypeParser` at the top level, or Express `express.raw()` app-wide) breaks every other route. Scope it to the webhook route only.
- **`current_period_end` and friends move between API versions** (e.g. newer Stripe APIs nest it under `subscription.items.data[0]`). Read defensively with a fallback; pin/verify your SDK's API version.
