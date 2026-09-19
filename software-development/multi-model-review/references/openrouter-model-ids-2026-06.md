# OpenRouter model IDs — working reference (2026-06-14)

OpenRouter model IDs change frequently and the IDs advertised in upstream docs are often not what the router actually routes. This file records the IDs that worked and failed in live calls during ELO Scenario Lab sessions.

## Verified working IDs

| Model | OpenRouter ID | Notes |
|-------|---------------|-------|
| Claude Sonnet 4 | `anthropic/claude-sonnet-4-20250514` | Works reliably. Default choice when credits are available. |

## Verified failing IDs (as of 2026-06-14)

| Model | OpenRouter ID tried | Error |
|-------|---------------------|-------|
| MiniMax-M3 | `minimax/minimax-m3` | 404 / invalid model ID |
| Mimo-m2.5-pro | `xiaomi/mimo-m2.5-pro` | 404 / invalid model ID |
| DeepSeek-V4-Pro | `deepseek/deepseek-v4-pro` | 404 / invalid model ID |

## Practical fallback strategy

When the user names specific models that fail on OpenRouter:

1. Try the exact ID they named first.
2. If that 404s, try the vendor-prefixed variants:
   - `minimax/m3`
   - `xiaomi/mimo`
   - `deepseek/deepseek-v4` (without `-pro`)
   - `deepseek/deepseek-v4-0324`
3. If all fail, call the best available configured model and tell the user honestly which models were reachable.
4. Do **not** continue retrying dozens of variants. Two attempts per model is enough.

## Credit-limit handling

OpenRouter returns 402 with a token budget in the error body. Reduce `max_tokens` to that budget minus 200 and retry the **same** model. Don't immediately switch models when the message says "you can only afford N tokens."
