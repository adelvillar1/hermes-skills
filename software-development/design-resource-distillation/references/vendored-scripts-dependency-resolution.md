# Vendored gate scripts: npm dependency resolution pitfall (2026-08-23, ux-ui-agent-skills fold)

When a fold vendors **runnable scripts** (not just knowledge) into a skill's `scripts/`:

## The pitfall

Gate scripts that resolve dependencies with ESM dynamic import — e.g. `await import('playwright')` — resolve relative to the **script's own path**, not the process cwd. Vendored into `your agent config dir<skill>/scripts/` and run from a project that has playwright installed, they still print `SKIPPED` (the scripts degrade gracefully by design, which masks the problem).

## The fix

Give each skill's `scripts/` its own tiny package:

```bash
cd your agent config dir<category>/<skill>/scripts
echo '{"name":"skill-gates","private":true,"type":"module"}' > package.json
npm install playwright   # browsers already live in the shared ~/Library/Caches/ms-playwright cache — the JS package alone suffices
```

## The gate for "folded"

The fold is not done when files are copied. It is done when **each vendored gate runs green against real output** — pick the most recent thing you shipped (e.g. a freshly built landing page in `apps/*/dist/`) and run every script against it. Record the result in the reply.

Verified 2026-08-23: `verify_keyboard.mjs` and `slop_tells.mjs` (folded into `wcag-accessibility` and `anti-ai-slop`) both green against `the mahjong VTT/apps/table/dist/landing/index.html` after the per-scripts-dir playwright install.
