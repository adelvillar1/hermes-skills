---
name: cdp-browser-driving
description: Drive web apps over raw Chrome CDP without Playwright.
---

# CDP Browser Driving (no Playwright, no deps)

Click/fill/verify in a live web app (login flows, panel checks, live feature verification) by talking to Chrome's DevTools Protocol directly — Node 24 built-in `fetch` + `WebSocket`, zero npm deps. This is the interaction sibling of `cdp-live-scene-capture` (frames) — use this one when you need to DRIVE the UI, not just capture it.

## When to Use

- Live UI verification of a feature (e.g. "does the Content Library show SRD spells and do the filters work") — prove it by clicking through the real app.
- `your browser tool` harness fails with `chrome-not-running` (it launches its own Chrome and can't attach; don't chase the popup — drive your own instance).
- Playwright not installed / `node_modules/.bin/playwright` missing.
- Logging into a real app with an account you registered via the API, then exercising authenticated UI.

## Prerequisites

1. Launch your own Chrome with a debug port (background):
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-cdp-X \
     --no-first-run --no-default-browser-check about:blank
   ```
2. Verify: `curl -s http://localhost:9222/json/version` → Chrome version.
3. App dev server running (confirm the RIGHT one — see pitfall 6).

## The zero-dep driver

Copy `templates/cdp-driver.mjs` (action-chain CLI: `open <url>`, `text`, `click <text>`, `fill <selector> <value>`, `press <key>`, `wait <ms>`, `eval <expr>`). Core pieces:

```js
// connect: fetch http://localhost:9222/json/list → page target → new WebSocket(webSocketDebuggerUrl)
// send(method, params): id-tagged request/response over the WS
// eval(expr): send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }).result.value
// click: find by trimmed innerText across button/a/[role=button]/input[type=submit]; exact match,
//        or startsWith for rows whose text concatenates label+meta ("Fireball\nSPELL")
```

## Pitfalls (each cost real debugging time in the field)

1. **Helpers are wiped by navigation.** Any `Page.navigate` / full reload resets the JS context — `window.__clickByText` etc. installed at connect time VANISH. Re-inject your helper functions before EVERY action, not once at startup.
2. **React controlled inputs ignore `.value = x`.** Use the native setter + input event:
   ```js
   Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v);
   el.dispatchEvent(new Event('input', { bubbles: true }));
   ```
   Selects: same with `HTMLSelectElement.prototype.value` + `new Event('change', { bubbles: true })`.
3. **`el.click()` on a WebGL canvas won't land** — three.js/etc. placement handlers need trusted pointer events. Verify via DOM state / op logs instead of forcing canvas clicks.
4. **Scope queries to the right container.** `find(d => d.innerText.includes('…'))` can match an inner container that does NOT contain the inputs you want (a list div vs the sibling form div). Find the outermost modal/panel, then `querySelector` inside it.
5. **`JSON.stringify` silently drops `undefined`.** A field value of `undefined` vanishes from the dump and looks like a bug. Guard: `name ? name.value : 'NO_INPUT'`.
6. **Port collisions with other projects' dev servers.** A leftover server from ANOTHER app can hold `:5173` (the school-dismissal SaaS vs the D&D VTT project). Dump `document.body.innerText` + `location.href` after the first navigate to confirm the right app; use Vite's auto-increment port rather than killing other sessions' processes.
7. **Synthetic events are not trusted.** Fine for React `onChange`/`onClick` (they don't check `isTrusted`); useless for canvas raycasters and some native widgets.

## Verification loop

- After each state change, re-dump text / re-query a scoped container — don't assume the click landed.
- For controlled fields, read back `el.value` after filling (the input event must have committed).
- End with the user-facing claim backed by real dumps (row lists, prefilled field values, filter results).

## Related

- `cdp-live-scene-capture` — frame/video capture over the same CDP infra (user-owned; consider `the harness curator adopt` if you need to extend it).
- `browser-automation` — kimi-webbridge mechanism (different tool; real login sessions, needs the Chrome extension).
