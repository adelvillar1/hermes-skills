---
name: design-spec-agent-prompts
description: "Encode a design spec as a self-contained agent prompt."
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Design, Handoff, Agents, Prompts, UI, Motion]
    related_skills: [design-motion-principles, design-handoff, subagent-driven-development, design-engineering]
---

# Design Spec → Agent Prompts

Turn a finished screen or design reference (animated splash, onboarding flow, welcome screen) into a **copy-paste prompt** a coding agent (Codex, Claude Code, Cursor, or a Hermes subagent) can execute inside an existing app without further clarification.

Pattern source: github.com/Appllama/top-welcome-screens — 10 per-screen prompts that hand agents exact file paths, a public API contract, motion-fidelity requirements, and concrete validation steps. That repo is also the reference for measured motion timings (see `design-motion-principles` → Measured Motion Data).

## When to Use

- The user wants to reuse a screen/component from one app (or a reference repo) inside another.
- Handing off a design implementation to a coding agent and you cannot afford ambiguity.
- Any design handoff where the receiving agent has zero conversation context (subagents, fresh sessions, external CLIs).

## Prompt Anatomy (in order)

1. **Scope line** — "You are working inside my existing {stack} repository. Use {reference} as a read-only technical reference. Integrate only the {name} implementation. Do not turn my app into the gallery and do not modify unrelated features."
2. **Reference files** — exact paths, in order: component source, assets dir, motion spec section, shared helpers (only transitive imports), root layout ONLY as font/asset preload reference, legal notice.
3. **Public API contract** — Component name, screen ID, font aliases, semantic action IDs, relevant packages. This makes the agent's output testable.
4. **Numbered requirements** — the strict clauses (below).
5. **Validation steps** — concrete checks, not "test it".
6. **Summary requirement** — "Finish by summarizing every file and dependency changed."

## The 10 Requirement Clauses (the load-bearing ones)

1. **Inspect before editing** — check the existing SDK versions, router, package manager, font loading, routes, dependencies.
2. **Copy only transitive imports** — the component + its selected assets + the shared helpers it actually imports. Explicitly forbid copying the demo router, gallery, or unrelated screens.
3. **Preserve architecture** — existing package versions, navigation, state architecture, app config, native projects. Install only missing compatible packages.
4. **Preload fonts/assets** — load the exact font aliases and image assets before revealing the React tree; adapt to the app's loading pattern, don't replace the root layout.
5. **Full-height mount** — component inside a full-height surface, no visible nav header, no surrounding safe-area padding; the component owns its calibrated canvas and status bar.
6. **Motion fidelity** — reproduce the authored timeline exactly: timing, easing, phases, reveal masks, autoplay and replayKey API, reduced-motion behavior, accessibility labels, interaction gates. **Do not replace the motion with a generic fade.** (This is the #1 clause agents silently violate.)
7. **Wire semantic actions** — every action through the callback to existing routes.
8. **IP clause** — educational prototype; before release replace every third-party name, logo, mascot, phrase, color system with original branding and make the composition meaningfully unique.
9. **Validate both platforms** — autoplay, autoplay={false}, replay, reduced motion, every action, typecheck, lint, primary platform simulator + one secondary viewport.
10. **Summarize** — every file and dependency changed.

## Template

```
You are working inside my existing {stack} repository.

Use {reference_repo_or_url} as a read-only technical reference. Integrate only the {name}-inspired implementation into my app. Do not turn my app into the gallery and do not modify unrelated features.

Reference files:
- {component_path}
- {assets_path}
- {motion_spec_section}
- {shared_helpers_paths} (only the transitive imports used by the component)
- {root_layout_path} only as a font and asset preloading reference
- {NOTICE_or_IP_doc}

Public API:
- Component: {ComponentName}
- Screen ID: {screen-id}
- Fonts: {FontA} and {FontB}
- Semantic actions: {prefix}.action-one and {prefix}.action-two
- Relevant packages: {pkg1}, {pkg2}, ...

Requirements:
1. Before editing, inspect my {stack} version, router, package manager, font loading, auth routes, and existing dependencies.
2. Copy only this component, its selected assets, and the transitive shared helpers it actually imports. Do not copy the demo router, gallery, or unrelated screens.
3. Preserve my package versions, navigation, state architecture, app configuration, and native projects. Install only missing compatible packages.
4. Load the exact font aliases and selected image assets before revealing the React tree. Adapt the loading pattern to my app instead of replacing my root layout.
5. Mount the component inside a full-height surface with no visible navigation header and no surrounding safe-area padding; the component owns its calibrated canvas and status bar.
6. Reproduce the reference behavior accurately: keep the {canvas_size} canvas, authored {animation} timing, easing, phases, reveal mask, autoplay and replayKey API, reduced-motion behavior, accessibility labels, and interaction gates. Do not replace the motion with a generic fade.
7. Wire every semantic action through the action callback to my existing {routes}.
8. Treat this as an educational prototype. Before any public or commercial release, replace every third-party name, logo, mascot, phrase, image, and brand color with authorized original branding, then make the final composition and motion meaningfully unique.
9. Validate autoplay, autoplay={false}, replay, reduced motion, every action, typecheck, lint, an {ios} simulator, and one {android} viewport.
10. Finish by summarizing every file and dependency changed.
```

## Pitfalls

- **Generic-fade substitution**: agents replace authored timelines with a single fade unless clause 6 is explicit. Always keep "Do not replace the motion with a generic fade."
- **Gallery sprawl**: without clause 2, agents copy the whole demo app/router/store into the target.
- **Context starvation**: subagents and CLI agents know nothing of the conversation — embed every path, ID, and constraint in the prompt itself.
- **Brand/IP**: clause 8 is mandatory for any third-party-inspired design; copying brand assets unchanged is a legal liability.
- **Reduced-motion omission**: agents skip reduced-motion + a11y handling unless the validation step names them.
- **ReferenceCanvas trick**: fixed-size calibrated canvases (e.g. 640×1385) with box() geometry make the prompt's fidelity testable — pixel boxes are auditable, flex hacks are not.

## Verification

After the agent runs the prompt, verify like any subagent work (see `delegation-result-verification`): check the component actually mounts, autoplay off works, reduced motion is honored, actions fire with the right IDs, and typecheck/lint pass. Never trust the agent's summary alone.
