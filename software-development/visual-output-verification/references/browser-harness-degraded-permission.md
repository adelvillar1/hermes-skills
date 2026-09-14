# Browser-harness degraded by pending macOS permission (2026-08-23)

Sibling to `browser-harness-vs-playwright.md` (all-black WebGL screenshots). This variant: the harness doesn't black out — it silently degrades, and a progressive-enhancement page shows its **fallback**, which looks exactly like a production regression.

## Incident

Production verification of the the mahjong project site landing (WebGL hero + PNG fallback). The browser automation harness screenshot showed the static PNG fallback with no canvas. Live DOM probe: canvas present, WebGL available, but never `is-ready`. Meanwhile the harness stderr carried: `Chrome is asking "Allow remote debugging?" — run browser-harness mac-approve or click Allow`. Playwright against the same production URL: `is-ready`, opacity 1, scene fully rendering — no regression.

## Rule

Before declaring a production visual regression from a `your browser tool`/`your screenshot tool` result:

1. **Check the harness stderr for a pending-permission warning** (`Allow remote debugging?`). If present, the session is degraded — its screenshots are not evidence of page state.
2. **Cross-check the same URL with Playwright** (`chromium.launch()` + `page.goto` + state probe + screenshot). Only trust the regression if both drivers agree.

Note the flip side observed in the same session: the page's silent-fallback design worked as intended — the degraded browser got a clean static hero with zero console errors. When a feature is built with progressive enhancement, "fallback visible in one driver" is weak evidence of anything except that driver's health.
