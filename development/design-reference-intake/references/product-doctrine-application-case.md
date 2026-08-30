# Product Doctrine Application — worked case (design-canvas, 2026-08-08)

Full implementation record for the design-reference-intake apply-extension: upgrading an LLM-design-generation product's prompt doctrine with our design skills, and adding a review dimension so the feedback loop closes. Use as a template for the next product-doctrine application.

## Target

DesignCanvas (`~/Projects/design-canvas`, Next.js 16 + TS + Prisma): a Claude-Design clone that generates self-contained HTML frames via LLM prompts. Generation pipeline in `lib/llm.ts` (`DESIGN_PRINCIPLES` doctrine constant injected into every generate/review/chat call; `REVIEW_SYSTEM` + `REVIEW_SCHEMA_HINT` for the reviewer; style presets in `lib/stylePresets.ts`).

## The audit finding

`DESIGN_PRINCIPLES` had strong static-visual coverage (anti-slop, typography, color tokens, layout) but motion was ONE line:
> "Motion (if any): motion clarifies state, never calls attention to itself. No loops without purpose, no delays that hide poor hierarchy. Respect prefers-reduced-motion."

Everything from our motion skills (escalation triggers, named curves, budgets, press feedback, hover gating) was absent — and the reviewer had no motion dimension to catch violations.

## The change (2 phases, plan `docs/plans/2026-08-08-motion-craft-doctrine.md`)

### Phase A — motion doctrine in `DESIGN_PRINCIPLES` (lib/llm.ts)

Replaced the one line with a compact doctrine (handed to the implementer VERBATIM — subagents invent weaker phrasing otherwise). Content:
- Never-list: no `transition: all`, no `scale(0)` entrances (start ≥ scale(0.9)+opacity), no `ease-in` on UI, no layout-property animation (transform/opacity only), no keyboard-initiated/frequent-action animation.
- Named curves: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`, `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)`, `--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1)`.
- Budgets: UI <300ms (press 100–160, tooltips/popovers 125–200, dropdowns 150–250, modals 200–500); exits faster than entrances.
- `:active { transform: scale(0.97) }` press feedback with fast ease-out transition.
- Hover gated behind `@media (hover: hover) and (pointer: fine)`.
- `prefers-reduced-motion` → gentler variant (keep opacity/color, drop movement), not zero.
- 30–80ms group stagger; never block interaction while staggering.

### Phase B — motion review dimension

- `lib/types.ts` `ReviewResult.scores` gains `motion: number`.
- `REVIEW_SYSTEM`: "Grade motion explicitly: flag transition: all, scale(0) entrances, ease-in on UI, durations over 300ms outside the allowed modal/drawer budget (200-500ms), animation on keyboard-initiated actions, missing prefers-reduced-motion, un-gated hover motion, and layout-property animation (width/height/top/left). Frames with no motion are fine — do not penalize static designs... When the screenshot is static, judge motion from the code."
- `REVIEW_SCHEMA_HINT` scores object gains `"motion": 0`.
- `ReviewPanel.tsx` `SCORE_DIMS` gains `["motion", "Motion", "M"]`; loading + empty copy updated.
- `reviews/route.ts` + main score grid both read with `?? 0` fallback.

## Pitfalls hit (each cost a review cycle)

1. **Reviewer/doctrine contradiction**: REVIEW_SYSTEM said "flag durations over 300ms" but doctrine allows modals 200–500ms. Quality reviewer caught it → reconciled to "over 300ms outside the allowed modal/drawer budget (200-500ms)". Always re-check escalation triggers against the doctrine's allowance table.
2. **Render-site normalization gap**: plan + implementer only added `?? 0` to the history-strip read path (`reviews/route.ts`). The ReviewPanel main score grid (`frame.review!.scores[key]` raw) rendered "Motion undefined/10" for pre-doctrine reviews. Spec reviewer caught it → `?? 0` at that site too. Audit EVERY `scores[key]` access, not just the route the plan named.
3. **Plan fidelity on curves**: plan said "the three named easing curves" but the implementer (and the delegation check) shipped only one. Spec reviewer flagged it. Keep the exact count in the AC and in the implementer context.
4. **Grep false-negatives through the terminal wrapper**: parent `grep -n "cubic-bezier(0.23, 1, 0.32, 1)" lib/llm.ts` returned "0 matches" even though the marker was present — the rtk wrapper mangles/compacts grep output. Re-read the file with `read_file` before trusting a negative grep (same class as ui-implementation-review pitfall 41, but for marker greps not diff anchors).
5. **xAI reviewer 500 in prod**: `REVIEWER_ROTATION` had `grok → deepseek`... actually `kimi → grok, grok → deepseek` originally; the failure was xAI's OAuth refresh ("xAI token refresh failed: HTTP 400") surfacing when a Grok-generated frame's default reviewer hit xAI. Fix: rotate to the best-taste reliable reviewer — `deepseek→kimi, kimi→deepseek, grok→kimi` (Kimi reviews everything it didn't generate; no self-grading preserved; xAI avoided entirely as reviewer). Verify with a live review on a frame from the previously-broken provider path.
6. **Wire-model smoke**: `k3` → `k3-256k` compiles clean; only a live review (HTTP 200 + scores) proved the model name is valid on the Kimi coding endpoint. Model-name typos compile fine and 500 at runtime.
7. **Prod deploy verification**: `railway status` showed Online; the real check was grepping the *served* JS chunk (`/_next/static/chunks/*.js` from the workspace route, logged in) for a client-visible marker (the "Motion" SCORE_DIMS entry + updated critique copy). Server-side doctrine text isn't in any client bundle — verify a client-side marker instead. This is the subagent-driven-development silent-deploy trap applied to a prompt change.
8. **Module-private prompt consts block import-based inspection** (AI/agent pass, 2026-08-08): `REVIEW_SYSTEM` / `REVIEW_SCHEMA_HINT` are `const`, NOT exported, so `import { REVIEW_SCHEMA_HINT } from "../lib/llm"` fails LSP with "declares locally, but it is not exported". `buildGenerateMessages` IS exported (generation-side assertions work with zero module changes). Fix: add the 2-token `export` as an explicit step in Phase C (the `.tmp/verify-aiux-doctrine.mts` script then imports them), or fall back to source grep for the review schema.
9. **Brief-class scoping for doctrine lines** (AI/agent pass): new doctrine that shouldn't apply to every frame opens with a scope guard — "when the brief is an AI product (chat, assistant, agent, copilot, generation tool), include the agent-interface surface set…" — and the reviewer instruction carries the mirror guard — "Frames that aren't AI products are fine without agent-interface surfaces — do not penalize non-AI designs; reward well-designed AI states when present." Without both, the model over-applies new surfaces to every generation and the reviewer punishes non-AI frames for lacking them.

## Verification chain (all passed)

- `pnpm exec tsc --noEmit`, `pnpm lint`, `pnpm build` clean.
- AC7 prompt-inspection: `.tmp/verify-motion-doctrine.mts` (npx tsx — node's native type-stripping can't resolve extensionless transitive imports in lib/llm.ts) asserted all doctrine markers + review schema in BUILT messages, not just source.
- AC8 local e2e: generated a frame with the new doctrine; it adopted ease tokens + reduced-motion; review returned `motion: 7` and flagged the frame's 0.6s/100ms-stagger entrance as over budget — proof the loop closes.
- Prod: after deploy, logged in via API, reviewed a real prod frame with DeepSeek → `motion: 8`, persisted read-back confirmed. Grok-frame default review still 500s until the rotation change shipped (deployed as separate follow-up commit `3421ad3`).

## Session 2 prod-verification deltas (2026-08-08, after deploy)

Application #2 deployed to prod; these findings correct/extend the verification guidance above (Pitfall 7 and the "prod bundle check" in Reusable artifacts):

- **The served-chunk grep does NOT transfer to Next 16 + Turbopack.** Chunk files are opaque hashes (`/chunks/<hash>.js`), both manifest endpoints 404 (`_buildManifest.js`, `app-build-manifest.json`), and route chunks are auth-gated — unauthenticated curl can't enumerate them. **Replacement: authenticated API smoke** — login (`POST /api/auth/login`, cookie jar, password from env never echoed) → `POST /api/projects` → `POST /api/generate` → `POST /api/review` on a generated frame → `DELETE /api/projects/<id>` cleanup. Verify (a) the generated frame HTML contains the doctrine's observable markers (AI-brief frames: loading/streaming/chat surfaces), and (b) the review response carries the new score key. **The review endpoint is the fast decisive proof**: 4K tokens vs 32K generation (fits under proxy timeouts), and `REVIEW_SYSTEM` embeds `DESIGN_PRINCIPLES`, so one new score key proves the whole new prompt chain is live.
- **Synchronous `/api/generate` can 524 behind Cloudflare** (>100s origin timeout) when the model is slow — NOT a deploy failure: the request completes server-side and frames persist. After a 524, GET the project and inspect frames (e.g. `frameCount` grew) instead of retrying or declaring failure.
- **Git-branch trap after the merge**: merging develop → main leaves you on main; the next docs commit (recap/CLAUDE.md state) lands on main unless you `git checkout develop` first. Recovery while unpushed: `git reset --hard <merge-hash>` on main + `git cherry-pick <docs-hash>` onto develop.

## Reusable artifacts

- Plan template: `docs/plans/2026-08-08-motion-craft-doctrine.md` (project-specific).
- The doctrine text above is directly reusable as a "motion craft" block for any LLM design-generation prompt.
- The 2-phase shape (doctrine upgrade + review dimension) generalizes to any skill → product-doctrine application: audit doctrine → upgrade → add/verify the review loop → backward-compat check → prompt-inspection + live e2e + prod bundle check.
- **Application #2 shipped 2026-08-08** (plan `2026-08-08-ai-interface-doctrine`, on develop): AI/agent-interface doctrine bullet (scope-guarded to AI-product briefs) + `aiUx` 7th review dimension, from the `ai-interface-design` skill. The same 2-phase shape held a second time: doctrine bullet → review dimension (`clampScore` + `SCORE_DIMS` + `?? 0` everywhere) → scope guard + mirror guard in the reviewer → verify. Verification added: prompt-inspection via `.tmp/verify-aiux-doctrine.mts` (REVIEW_SYSTEM/SCHEMA_HINT exported for import — pitfall 8) and a **pure-function e2e** — `generateFrame` + `reviewFrame` called directly (no dev server, no auth), regex-asserting the frame HTML for the doctrine's surface markers and asserting the new score key is numeric; live result `aiUx: 8`. Gotcha: `GenerateResponse.frames` is an ARRAY (variant fan-out), not `.frame`. Scripts deleted after use (motion precedent); the doctrine line in `ai-interface-design` records the baseline so application #3 extends rather than re-adds.
