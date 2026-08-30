---
name: es-module-bare-identifier-trap
description: >
  Diagnose ReferenceErrors from bare global identifiers in ES modules.
  When extracting code from an IIFE or non-module context into an ES module,
  bare references to window globals (Auth, dashboard, config, etc.) silently
  break because ES modules run in strict mode — bare `Auth` is NOT `window.Auth`.
  Use when a button/feature "does nothing" after a modular refactor, or when
  migrating IIFE code to ES modules.
---

# ES Module Bare Identifier Trap

## The Bug

In a `<script>` tag (non-module), `Auth.authFetch(...)` resolves to `window.Auth.authFetch(...)` because the global scope chain includes `window`.

In an ES module (`<script type="module">` or `import`), **strict mode is always on**. Bare `Auth` is a `ReferenceError` — it does NOT fall through to `window.Auth`.

## Symptoms

- Button click "does nothing" — no network request, no error visible to user
- Error is silently caught by a `try/catch` block (the catch calls `toast(e.message)` which may flash briefly)
- Works in the IIFE but breaks after extracting to a module

## The Fix

Replace bare `Auth.authFetch(...)` with one of:
1. **`api()` helper** (preferred) — if one exists that wraps `window.Auth.authFetch`, use it
2. **`window.Auth.authFetch(...)`** — explicit window reference
3. **`globalThis.Auth.authFetch(...)`** — works in both module and non-module contexts

## Detection

```bash
# Find bare Auth.authFetch in ES module files (not in IIFE/dashboard.js)
grep -rn "Auth\.authFetch" ui/js/views/ ui/js/lib/ | grep -v "window\.\|globalThis\."

# Find other common globals that might have the same issue
grep -rn "\bdashboard\.\|config\.\|state\." ui/js/views/ | grep -v "import\|window\.\|globalThis\."
```

## Pattern: dual-export surface

When extracting from an IIFE to modules, the standard pattern is:
```js
// In the module (pipeline.js):
export function triggerPipeline() { ... }
if (typeof globalThis !== 'undefined') {
  globalThis.triggerPipeline = triggerPipeline;
}

// In the IIFE (dashboard.js):
function triggerPipeline() { return globalThis.triggerPipeline(); }
```

But the module's internal calls still need to use `window.*` or imported helpers for globals that live in the IIFE (Auth, config, etc.).

## Historical examples

- 2026-06-14: `pipeline.js` used bare `Auth.authFetch` in 6 places (trigger, MC simulate, calibrate, 3 poll loops). All broke silently after the PR3.8 extraction from dashboard.js.
- 2026-06-11: `dashboard.js` IIFE's `globalThis.loadView = loadView` clobbered router.js's version — same class of bug (global ownership conflict during modular refactor).