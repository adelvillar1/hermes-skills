---
name: hyperframes-expert
description: "HyperFrames expertise: docs map, conventions, and pitfalls."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Creative, Video, Animation, Reference, HyperFrames]
    category: creative
---

# HyperFrames Expert

Expert-level knowledge base distilled from the official HyperFrames documentation at `hyperframes.heygen.com`. It does **not** author videos itself — it makes the agent a HyperFrames expert: it maps the docs, encodes the framework's hard rules and vocabulary, and lets you answer questions or steer composition work with confidence. Pair it with the existing `hyperframes` skill (the authoring workflow) when the user actually wants to scaffold, animate, and render.

## When to Use

- The user asks how HyperFrames works, asks about its concepts, CLI, skills, or pipeline.
- The user says "make a video" or "animate X" but you need to confirm the right workflow before scaffolding.
- You see a broken composition (timeline mismatch, missing animation, determinism issue) and need the canonical fix.
- The user asks for "the HyperFrames way" of doing something (captions, transitions, audio-reactive visuals, TTS).
- You are picking between rendering targets (local, Docker, Lambda, Cloud Run, Cloud) and need the trade-offs.

## Prerequisites

None -- this is a knowledge skill. It uses the `web_extract` tool only if you need to fetch a docs page that is not in your training window; otherwise the cached knowledge below is sufficient.

If you need to actually run HyperFrames to verify something, see the `hyperframes` skill for `node`/`ffmpeg`/`npx` prerequisites.

## How to Run

- Load this skill: `skill_view(name="hyperframes-expert")`.
- Reference docs: every canonical URL is in **Quick Reference** below; use `web_extract` to fetch the `.md` alternate if a page is missing from your training data.
- Frame the answer with the docs language -- use the exact attribute names, command verbs, and framework terms listed here.
- When the user wants to **build**, hand off to the `hyperframes` authoring skill; do not try to author from this skill alone.

## Quick Reference

Docs index (single source of truth for the agent):

- Master index: `https://hyperframes.heygen.com/llms.txt` -- list of every page.
- Markdown alternates: append `.md` to any doc URL (e.g. `/guides/skills.md`, `/concepts/data-attributes.md`).
- GitHub source of truth for skills: `https://github.com/heygen-com/hyperframes/tree/main/skills`.

The skill catalog groups (from `/guides/skills`):

- **Router (1):** `/hyperframes` -- read first; routes "make me a..." to the right workflow.
- **Creation workflows (11):** `/product-launch-video`, `/website-to-video`, `/faceless-explainer`, `/pr-to-video`, `/embedded-captions`, `/talking-head-recut`, `/motion-graphics`, `/music-to-video`, `/slideshow`, `/general-video` (fallback), `/remotion-to-hyperframes`.
- **Domain skills:** `/hyperframes-core`, `/hyperframes-animation`, `/hyperframes-keyframes`, `/hyperframes-creative`, `/media-use`, `/hyperframes-cli`, `/hyperframes-registry`, `/figma`.

The seven-step pipeline (from `/guides/pipeline`):

1. **Capture** -> `capture/` (`npx hyperframes capture <url> -o ...`).
2. **Design** -> `DESIGN.md` (5 sections: theme, quick reference, components, spacing, iteration guide).
3. **Strategy & Messaging** -> lock the ONE message + narrative arc.
4. **Storyboard + Script** -> `STORYBOARD.md` + `SCRIPT.md` (concept-first, then narration).
5. **VO + Timing** -> `narration.wav`, `narration.txt`, `transcript.json` (`npx hyperframes tts` + `transcribe`).
6. **Build** -> `compositions/<beat>.html` (one per beat).
7. **Validate** -> `npx hyperframes lint`, `check`, `snapshot`.

CLI verbs (from `/packages/cli`, run via `npx hyperframes <verb>`):

- `init [name]` -- scaffold a project from an example (`--example blank|warm-grain|play-mode|swiss-grid|vignelli`; non-interactive mode requires `--example`).
- `compositions` -- list compositions in current project.
- `capture <url>` -- capture a website.
- `tts <text|file>` -- generate narration (Kokoro local).
- `transcribe <audio>` -- word-level timestamps (`--model small.en|medium.en|large-v3`).
- `remove-background <file>` -- transparent cutout (`.webm` alpha / `.mov` / `.png`).
- `add <name>` -- install a block/component from the registry.
- `catalog` -- browse the registry (`--type block|component`, `--json`).
- `preview [dir]` -- live Studio with hot reload.
- `publish [dir]` -- upload and get a stable `hyperframes.dev` URL.
- `lint [dir]` -- structural checks (`--json` for machine-readable).
- `check [dir]` -- one-pass lint + runtime + layout + motion + contrast (`--snapshots`, `--at 1.5,4,7.25`).
- `inspect [dir]` -- DEPRECATED alias for `check`.
- `snapshot [dir]` -- PNG frames at timestamps.
- `beats [dir]` -- detect BPM and write beat guide.
- `render --output X.mp4` -- local/Docker render; `--docker`, `--format webm|mov|gif|png-sequence`, `--quality draft|standard|high`, `--fps`, `--gpu`, `--variables '<json>'`.
- `auth login` -- OAuth / `--api-key` for CI.
- `cloud` / `lambda` / `cloudrun` -- managed cloud rendering.

Hard rules (must hold or render breaks -- from `/guides/common-mistakes`):

- `class="clip"` on every timed element + `data-start` + `data-duration` + `data-track-index`.
- Register GSAP timeline on `window.__timelines[<composition-id>]` with `{ paused: true }`; key must match `data-composition-id`.
- `<video>` elements must be `muted`; audio lives in separate `<audio>`.
- Never use `Math.random()` (breaks determinism) -- use a seeded PRNG.
- Never `play()` / `pause()` / set `currentTime` on media in scripts -- the framework owns playback.
- Never animate `width`/`height`/`top`/`left` directly on `<video>` -- wrap in a div and animate the wrapper.
- Timeline length must cover the longest clip -- extend with `tl.set({}, {}, DURATION)` if needed.
- Root composition's `data-duration` is **compile-time-fixed** (like width/height) -- `--variables` or a script cannot change it.
- Same-track clips cannot overlap in time (crossfades go on different tracks).

Vocabulary the skills map from natural-language adjectives (from `/guides/prompting`):

- Easing: smooth=`sine`/`power1`, snappy=`power4.out`, bouncy=`back.out`, springy=`elastic.out`, dramatic=`expo.out`, dreamy=`sine.inOut`.
- Caption tones: hype (heavy, scale-pop), corporate (clean sans, fade+slide), tutorial (monospace, typewriter), storytelling (serif, slow fade), social (rounded, bounce).
- Transitions: calm=blur/cross-warp; medium=push/whip-pan; high=zoom/glitch/ridged-burn.
- Audio-reactive: bass->scale, treble->glow, amplitude->opacity, mids->borderRadius.
- Marker highlights: `highlight`, `circle`, `burst`, `scribble`, `sketchout`.

Auth keys (from `/guides/authentication`):

- `HEYGEN_API_KEY` (alias `HYPERFRAMES_API_KEY`) -- HeyGen voice + music/SFX; credential also lives at `~/.heygen/credentials` (mode `0600`).
- `ELEVENLABS_API_KEY` -- used only when no HeyGen credential.
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` -- Lyria music; capture descriptions.
- `OPENROUTER_API_KEY` -- capture descriptions (takes priority over Gemini).
- Working offline is a normal state -- voice falls back to **Kokoro-82M**, music to **MusicGen**, SFX to a bundled library.

Frame Adapter contract (from `/concepts/frame-adapters`):

- `getDurationFrames(): number` -- finite integer >= 0.
- `seekFrame(frame)` -- idempotent, supports random order, clamps to range.
- `init(ctx) -> ready -> seekFrame(N times) -> destroy()` lifecycle.
- Adapter API is **v0 (experimental)** -- the contract is stable, signatures may evolve.
- Built-in runtime adapters: GSAP, Anime.js, CSS keyframes, Lottie, Three.js, WAAPI, TypeGPU.

Determinism (from `/concepts/determinism`):

- `t = frame / fps`; `normalizedFrame = clamp(Math.floor(frame), 0, durationFrames)`.
- No wall-clock (`Date.now`, `requestAnimationFrame`); no unseeded randomness; no render-time network fetches; fixed output params.
- Use `--docker` for cross-platform byte-identical output.

Composition contracts (from `/concepts/compositions` + `/concepts/data-attributes`):

- Root element: `data-composition-id`, `data-width`, `data-height`; root `data-duration` sets total render length.
- Clip types: `<video>`, `<img>`, `<audio>`, nested `<div data-composition-id>`.
- Sub-compositions: external via `data-composition-src` + `<template>` wrapper, OR inline.
- Relative timing: `data-start="<id>"` starts when that clip ends; `+ N` / `- N` adds gap/overlap (overlaps require different tracks).
- Variables: declare on root with `data-composition-variables` (id+type+label+default), override per-instance with `data-variable-values` (JSON), read via `window.__hyperframes.getVariables()`.
- Two layers -- HTML primitives vs GSAP scripts. Scripts never control media playback or visibility; data attributes do.

Rendering modes (from `/packages/cli` + `/deploy/*`):

- **Local** -- fast, platform-dependent fonts; default for iteration.
- **Docker** (`--docker`) -- exact Chrome + font set; byte-identical across machines.
- **Cloud** (`hyperframes cloud`) -- HeyGen-hosted, no local Chrome/FFmpeg.
- **AWS Lambda** (`hyperframes lambda deploy|render|render-batch|progress|destroy|policies`).
- **Cloud Run** (`hyperframes cloudrun deploy|render|render-batch|progress|destroy`).
- **HDR** -- MP4 only; auto-detects BT.2020/PQ/HLG sources; force via `--hdr`, opt out via `--sdr`.
- **4K** (`--resolution landscape-4k|portrait-4k|square-4k`) -- supersamples via Chrome `deviceScaleFactor`; not supported with `--hdr`.

## Procedure

1. **Identify intent.** Is the user asking a *knowledge* question (how HyperFrames works, what command to run, which skill to use) or an *authoring* task (make me a video)? If authoring, hand off to the `hyperframes` skill after answering any clarifying questions here.
2. **Locate the canonical doc.** Use **Quick Reference** above; if the page is not in your training window, fetch the `.md` alternate via `web_extract` (e.g. `https://hyperframes.heygen.com/concepts/data-attributes.md`). Always cite the canonical URL.
3. **Speak the framework's language.** Use exact attribute names (`data-start`, `data-duration`, `data-track-index`, `class="clip"`), exact CLI verbs (`init`, `render`, `check`, `compose`), and exact framework concepts (composition, frame adapter, determinism contract, frame clock). Never paraphrase critical identifiers.
4. **Enforce hard rules on sight.** Whenever the user describes or shows a composition, check it against the **Hard Rules** section. Flag missing `class="clip"`, unmuted `<video>`, unregistered timelines, `Math.random()`, animating `<video>` dimensions directly, or root `data-duration` set from a script.
5. **Recommend the right workflow.** For "make me a...", ask: is there an existing source (URL, PDF, CSV, GitHub repo, transcript, audio)? Map to the matching workflow skill: `/website-to-video` (URL), `/faceless-explainer` (text), `/pr-to-video` (PR), `/embedded-captions` (talking-head + captions), `/talking-head-recut` (talking-head + graphic cards), `/music-to-video` (audio), `/motion-graphics` (short, no narration), `/general-video` (fallback). Then `/product-launch-video` and `/slideshow` are explicit-format options.
6. **Map adjectives to behavior.** When the user describes motion, captions, or transitions in natural language, use the **Vocabulary** table to translate to framework settings. Cite the rule.
7. **Diagnose problems in this order.** Lint (`npx hyperframes lint`) -> timeline registered? key matches `data-composition-id`? -> GSAP-only animations? -> timeline long enough (`tl.set({}, {}, DURATION)`)? -> console errors? -> if still stuck, escalate to `/guides/troubleshooting`. This is the canonical debugging order from `/guides/common-mistakes`.
8. **Pick the right render target.** Local for iteration, Docker for reproducibility, Cloud when no Chrome is available, Lambda/Cloud-Run for batch + scale. HDR is MP4-only; 4K supersamples and is incompatible with HDR.

## Pitfalls

- **Two "hyperframes" skills exist in your profile.** This one (`hyperframes-expert`) is the **knowledge** skill. The sibling `hyperframes` skill is the **authoring workflow**. Do not conflate them -- load this for "what is / how does / which one" and the other for "make me a video."
- **Markdown alternates only exist for top-level guide pages.** Deeper URLs (e.g. `/sdk/reference/adapters`) still serve content but `.md` aliases are most reliable for `/concepts/*`, `/guides/*`, `/packages/*`, `/quickstart`, `/introduction`.
- **Do not use the `hyperframes` authoring skill's bundled skills verbatim.** Those slash commands target Claude Code, Cursor, etc. -- the user is asking you to be an expert via Hermes tools, not to register slash commands. Translate the same knowledge into `terminal`/`read_file`/`write_file`/`web_extract` invocations.
- **`web_extract` may fail** (no API key configured). Fall back to `terminal` with `curl -sSL https://hyperframes.heygen.com/<page>.md` -- the docs site exposes Markdown alternates via the `<link rel="alternate" type="text/markdown">` link.
- **Mintlify chrome at the top of every fetched page.** Every `.md` page begins with a `> ## Documentation Index` blockquote pointing at `/llms.txt`. That is expected -- it is the site navigation header, not content. Skip past it to find the actual `## <Heading>` content.
- **The "expert" goal is comprehensive, not exhaustive.** Do not dump every flag from the 1400-line CLI page. Surface the verbs and concepts; cite the docs page when the user needs detail.
- **Skills update on `main`, not the registry.** `npx skills add heygen-com/hyperframes --full-depth` is preferred over the unpinned default, which can lag by hours.
- **Drafting/authoring is out of scope here.** Do not try to write compositions from this skill; that is what the `hyperframes` authoring skill is for. This skill tells you *what* to do and *why*; the other skill shows you *how*.

## Verification

- The skill loaded with no parse errors: `skill_view(name="hyperframes-expert")` returns the full SKILL.md.
- A live fetch of the skills catalog matches this skill's catalog summary: `curl -sSL https://hyperframes.heygen.com/guides/skills.md` should return a page whose Router/Workflows/Domains sections match the structure recorded under **Quick Reference** above.
- When asked "how do I render an MP4 from this composition," the answer cites `npx hyperframes render --output X.mp4` (or the docker/lambda variants) and points to `/packages/cli` for flag details.
- When shown a broken composition, the diagnostic checklist (lint -> timeline key -> GSAP-only -> length -> console -> troubleshoot) is followed in order.
