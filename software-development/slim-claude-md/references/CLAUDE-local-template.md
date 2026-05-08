# Local Environment Reference (NOT in git)

> Auto-loaded by Claude Code alongside `CLAUDE.md` but gitignored. Contains live connection strings and credentials. **Never paste these into commits, PRs, shared docs, web tools, or screenshots.**

---

## Environment quick-reference — read this BEFORE any DB or hosting operation

| Branch | Env name | URL | Hosting service |
|--------|----------|-----|-----------------|
{{#BRANCHES}}
| {{branch}} | {{env}} | {{url}} | {{service_name}} |
{{/BRANCHES}}

**Hard rules:**
- Default deploy/operation target is **{{DEFAULT_BRANCH}}**. Other environments require explicit user approval *in the current turn*. Approval for one action does not extend to others.
- Production has live customer data. Read-only by default. Any write must be explicitly authorized in the current turn.

---

{{#FOR_EACH_ENVIRONMENT}}

## {{env_name}}

- **URL**: {{url}}
- **Branch**: `{{branch}}`
- **Hosting service**: `{{service_name}}`
- **DB external**: `<paste-here>`
- **DB internal**: `<paste-here>`
{{#HAS_REDIS}}
- **Redis external**: `<paste-here>`
- **Redis internal**: `<paste-here>`
{{/HAS_REDIS}}
{{#HAS_OTHER_SERVICES}}
- **{{service_name}} external**: `<paste-here>`
- **{{service_name}} internal**: `<paste-here>`
- **{{service_name}} password**: `<paste-here>`
{{/HAS_OTHER_SERVICES}}

{{/FOR_EACH_ENVIRONMENT}}

---

## Local development

| Service | URL | Notes |
|---------|-----|-------|
| App | http://localhost:3000 | <stack> |
<!-- Add database, cache, mail catcher, etc. as applicable -->

---

## Run migrations against a remote env

```bash
# Example template — adapt to your stack:
DATABASE_URL="<staging-url>" <migration-command>
```

---

## API keys and external services

<!--
  One section per category of secret your project uses.
  Common categories:
  - DATABASE_URL / connection strings
  - Auth secrets (NEXTAUTH_SECRET, JWT signing keys, OAuth client secrets)
  - Payment provider keys (Stripe, Lemon Squeezy, etc.)
  - LLM/AI keys (Anthropic, OpenAI, etc.)
  - Email provider keys (Resend, SendGrid, Postmark)
  - Object storage (S3, R2)
  - Analytics (PostHog, Mixpanel)
  - Error tracking (Sentry)

  Don't list categories you don't use.
-->

```
<!-- ANTHROPIC_API_KEY=sk-ant-api03-... -->
<!-- STRIPE_SECRET_KEY=sk_live_... -->
<!-- RESEND_API_KEY=re_... -->
```

---

## Personal tokens

<!--
  Things like your GitHub PAT, team Slack webhook, etc.
  These rarely change but are useful to keep here so Claude can find them.
-->

```
<!-- github_pat_... -->
```

---

## Other infrastructure

<!--
  Anything else worth pinning so a future session doesn't ask:
  - Helpdesk URL
  - Analytics dashboard URL
  - Support email addresses
  - Internal admin URLs
-->

| Service | URL | Notes |
|---------|-----|-------|

---

## When you change anything in this file

This file is gitignored, so updates leave no trace in `git log`. When you change a credential, URL, or add a new environment, **mention it in the session recap** so the change is at least visible in the project's history. Example: `Updated CLAUDE.local.md: rotated production DB password.`
