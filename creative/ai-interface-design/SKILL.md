---
name: ai-interface-design
description: "Use when designing AI/agent UIs: loading, streaming."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Design, AI, UX, Agent, Interfaces]
    related_skills: [design-motion-principles, design-engineering, ui-implementation-review]
---

# AI / Agent Interface Design

Design the surfaces of AI-powered products: loading and reasoning states, streaming responses, tool activity, approvals, citations, and full conversational workspaces. The surface catalog comes from beUI's "Agent Interfaces" category (github.com/starc007/ui-components, ~20 components, MIT, published 2026-08-01/02) plus the stable-streaming craft rules of production AI UIs.

## When to Use

- Designing any AI/agent product surface: chat, generation, tool execution, review, streaming output.
- Adding loading/reasoning/streaming states to an LLM feature.
- Auditing an existing AI UI for missing state machinery (no loading, layout shift on stream, missing approvals/citations).
- Generating frames for an AI product in an LLM design app (doctrine application, below).

## The surface catalog (AI product completeness checklist)

beUI's agents category names the full set of AI UX surfaces — check an AI UI against it:

1. **Loading states (3 tiers):** (a) shimmering status text ("thinking shimmer" keeps the current status readable); (b) live agent progress — compact activity glyph + action verb + live timer for longer work; (c) cycling reasoning phrases — phrase-swap or per-letter scramble transitions.
2. **Reasoning display:** collapsible agent reasoning with thinking-state labels; output streams in place.
3. **Streaming message:** a *stable* response surface — content renders as it arrives WITHOUT layout shift; completion actions; expandable source summary.
4. **Message scroller:** reader-aware viewport — follows streamed output at the live edge and releases control when the reader moves away. Never fight the user's scroll.
5. **Citations:** inline citation markers paired with a collapsible, progressively rendered reference collection.
6. **Tool execution:** tool-result disclosure (syntax-highlighted output that collapses into a compact completed state); tool-approval permission cards (allow once / remember / deny).
7. **Human-in-the-loop approvals:** approval cards for single/multi-choice questions, custom responses, multi-step review flows.
8. **Planning:** collapsible todo list with morphing status marks, completion count, smooth list updates.
9. **Code / diffs:** syntax-highlighted code block with stable streaming updates, line numbers, focused lines, smooth following, copy feedback; file-diff disclosure with progressive rows and live change counts.
10. **Generated media:** image-generation surface moving queued → progressive refinement → completed WITHOUT layout shift.
11. **Composer:** auto-growing prompt input with prompt actions, model selection, keyboard submission, animated send/stop states.
12. **Full workspace:** chat app composing navigation, messages, streaming, planning, approvals, tools, code, diffs, generated media, sources, prompt input.

## Behavioral principles (the craft rules)

- **Streaming surfaces must not layout-shift.** Reserve space, render deltas in place, keep edges stable. (beUI: "stable response surface", "without layout shift".)
- **Follow the live edge, release on reader intervention.** Auto-scroll only while the reader is at the bottom; any manual scroll disengages.
- **Live-updating code/text stays stable:** keep line numbers stable, smooth-follow the active region, don't reflow.
- **Progressive → compact:** long output renders expanded/syntax-highlighted, then collapses into a compact completed state when done — progressive disclosure, not truncation.
- **Loading is informative, not decorative.** Three tiers (status text → activity + verb + timer → cycling phrases). Long-running work gets live progress truth, not shimmer.
- **Approvals are explicit decisions:** allow-once / remember / deny are distinct affordances; multi-step review flows get their own cards.
- **Reasoning is collapsible and labeled:** thinking-state labels, expand/collapse, in-place streaming.
- **Reduced-motion applies to AI chrome too:** shimmer/cycling states get a calm variant; never gate reading on motion.

## Design-canvas doctrine application

DesignCanvas (`lib/llm.ts` `DESIGN_PRINCIPLES`) has strong static + motion doctrine but NO agent-interface guidance — frames generated for AI products get generic loading/streaming. The missing doctrine line: "AI/agent product frames need the agent-interface surface catalog (loading tiers, streaming stability, citations, approvals); streaming surfaces never layout-shift; loading is informative, not decorative." Add as a doctrine section and consider an `ai-ux` review dimension (mirrors the `motion` dimension added 2026-08-08; same backward-compat discipline — normalize `?? 0` at every render site).

## Source

github.com/starc007/ui-components (beUI) — agents category. Component markdown (LLM-facing): `https://beui.dev/components/agents/{slug}.md`; index: `https://beui.dev/llms.txt`; raw source: `https://beui.dev/r/{slug}/raw`. MIT.

## Verification

- [ ] All state tiers present where applicable: loading / reasoning / streaming / complete / error
- [ ] Streaming surfaces are layout-shift-free
- [ ] Auto-scroll releases when the reader scrolls away
- [ ] Long output collapses to a compact completed state
- [ ] Approvals and citations have distinct, labeled affordances
- [ ] Reduced-motion variant for shimmer/cycling states
