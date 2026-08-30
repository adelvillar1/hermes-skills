---
name: kinetics-expert
description: "Choose and tune Kinetics spring-physics UI presets."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Creative, UI, Motion, Animation, Reference]
    category: creative
---

# Kinetics Expert

Expert knowledge base for **Kinetics** — a single-page gallery at `kinetics.colorion.co` of 99 spring-physics micro-interactions for web apps. It does **not** itself render motion; it makes the agent an expert so it can pick the right preset by intent, read the canonical snippet (CSS / React / Prompt), tune the physics, and port it into any project. Pair it with `hyperframes-expert` when the motion is destined for a video rather than a DOM app.

## When to Use

- The user asks for a micro-interaction (button press, ripple, toggle, accordion, count-up, swipe-to-dismiss, hold-to-confirm, etc.) and you want to pick a proven preset instead of inventing the easing.
- The user wants to know what Kinetics is, how its physics parameter readouts work, or how to tune stiffness/damping.
- You are porting motion from a Figma prototype, a Lottie file, or a GSAP timeline into vanilla CSS/React and need a closer-to-stock reference.
- You want to generate copy-paste AI prompts for an LLM that should reproduce a specific micro-interaction.

## Prerequisites

None — Kinetics is a static single-page reference site with no API, no login, and no install. The dev source lives at `github.com/ckissi/kinetics` (MIT) but you only need it if you want to run the site locally.

To copy code from the site, fetch the HTML and parse the `<pre data-lang="css|react|prompt">` blocks per card (see **Procedure**). Each card has all three code samples embedded in the same markup.

## How to Run

- Load this skill: `read the SKILL.md for '`kinetics-expert`' via your harness's skill loader`.
- Treat the **Quick Reference** catalog as the index; do not memorize snippets — locate by intent, then fetch the snippet.
- Fetch the page via `terminal` with `curl -sSL https://kinetics.colorion.co/` (there is no `.md` alternate; this is a hand-rolled single page), or via `web_extract` if available. Parse the 99 cards; each has a `.card` with three `<pre data-lang="...">` panels.
- Translate the chosen snippet to the user\'s stack: vanilla CSS works everywhere, React snippets assume `useState`/`useRef`, Prompt snippets are plain English suitable for an LLM.

## Quick Reference

The page URL the user pointed at: `https://kinetics.colorion.co/#library`. Three top-level anchors:

- `#library` — the 99 motion presets (the main deliverable).
- `#physics` — 590-char explainer: "Two numbers, not a duration. ... stiffness + damping instead of duration + easing. Interrupt it mid-motion and it just keeps integrating from its current velocity — no snap, no restart."
- `#about` — "Built for the copy-paste workflow. Every demo above ships in both plain CSS and React. No build step, no animation library dependency ... MIT licensed."

The 99 presets are split into three equal categories, each labelled `33 / 99`:

**Interaction & Input** (33) — direct user input or manipulation:
Card Resize, Magnetic Button, Number Counter, Toast Overshoot, Tab Pill Glide, Accordion Spring, Drag to Dismiss, Ripple Feedback, Hold to Confirm, Rubber-band Slider, Like Burst, Cursor Trail, Push Button, Star Rating, Floating Label, Copy Button, Quantity Stepper, Choice Chips, PIN Input, Password Meter, Pointer Tooltip, Swipe to Reveal, Rotary Knob, Reorderable List, Expanding Search, Squish Button, Toggle Pills, Value Scrubber, Speed-Dial FAB, Swatch Picker, Slide to Unlock, Tag Input, Keycap Press.

**Feedback & State** (33) — state transitions and affordances:
Scramble Reveal, Momentum Marquee, Stagger Entrance, Icon Morph Swap, Underline Draw, Elastic Progress, Delayed Tooltip, Switch Spring, Checkbox Draw, Typewriter, Odometer Count-up, Status Pill, Pulse Badge, Success Check, Segment Loader, Orbit Spinner, Progress Ring, Notification Slide-in, Step Progress, Undo Snackbar, Submit States, Countdown Ring, Skeleton to Content, Toast Stack, Indeterminate Bar, Pulse Badge (2nd), Shimmer Skeleton, Typing Indicator, Heartbeat Monitor, Battery Charge, Signal Bars, Badge Counter, Bookmark Toggle.

**Surface & Motion** (33) — ambient/decorative motion:
Error Shake, Confetti Burst, Parallax Tilt, Wave Loader, Skeleton Sweep, Page Peel, Cursor Spotlight, Flip Card, Glitch Text, Border Beam, Aurora Drift, Shine Sweep, Breathing Orb, Float Bob, Liquid Blob, Gradient Shimmer Text, Neon Glow Pulse, Equalizer Bars, Radar Pulse, Newton\'s Cradle, Bouncing Ball, Marquee Reveal, Gradient Border Morph, Text Split Reveal, Hover Lift, Sheen Sweep, Clip Wipe, 3D Cube Rotate, Jelly Wobble, Folding Doors, Before / After, Depth Stack, Text Wave.

Pattern vocabulary (how to pick by intent, not by name):

- **Press feedback**: Push Button, Squish Button, Keycap Press, Jelly Wobble — pure CSS transform on `:active`.
- **State toggle**: Toggle Pills, Choice Chips, Switch Spring, Swatch Picker — selection state with spring scale.
- **Numerical input**: Number Counter, Quantity Stepper, Star Rating, Value Scrubber, Odometer Count-up, Password Meter, PIN Input.
- **Drag / gesture**: Magnetic Button, Drag to Dismiss, Reorderable List, Rotary Knob, Swipe to Reveal, Slide to Unlock, Rubber-band Slider, Value Scrubber, Before / After.
- **Confirmation / commit**: Hold to Confirm, Copy Button, Submit States, Undo Snackbar.
- **Loading / progress**: Orbit Spinner, Pulse Badge, Progress Ring, Elastic Progress, Segment Loader, Indeterminate Bar, Skeleton Sweep, Skeleton to Content, Heartbeat Monitor, Battery Charge, Signal Bars, Countdown Ring.
- **Status / message**: Toast Overshoot, Notification Slide-in, Toast Stack, Status Pill, Bookmark Toggle, Badge Counter.
- **Reveal / entrance**: Stagger Entrance, Tab Pill Glide, Underline Draw, Scramble Reveal, Icon Morph Swap, Typewriter, Gradient Shimmer Text, Text Split Reveal, Text Wave.
- **Attention / error**: Error Shake, Like Burst, Confetti Burst, Glitch Text, Pulse Badge, Neon Glow Pulse.
- **Ambient / decorative**: Aurora Drift, Breathing Orb, Float Bob, Liquid Blob, Marquee Reveal, Equalizer Bars, Border Beam, Gradient Border Morph, Shine Sweep, Sheen Sweep, Hover Lift, Depth Stack, Cursor Spotlight, Cursor Trail, Pointer Tooltip, Floating Label, Expanding Search, Momentum Marquee, Clip Wipe, Flip Card, 3D Cube Rotate, Folding Doors, Page Peel, Parallax Tilt, Wave Loader, Typing Indicator, Delayed Tooltip, Bouncing Ball, Newton\'s Cradle.
- **Layout**: Card Resize, Accordion Spring, Password Meter (segments).

Parameter conventions (read this when tuning):

- **`spring(stiffness, damping)`** — the canonical readout. Stiffness 200-360, damping 18-28 are the sweet spot. Spring math is integrated by browser CSS; the cubic-bezier `cubic-bezier(0.34, 1.56, 0.64, 1)` is the cheap stand-in when you want zero JS.
- **`overshoot(x)` / `spring scale N`** — bounce scale on top of the standard spring.
- **`magnet(factor)`** — 0..1; cursor pull strength.
- **`friction(0..1)`** — higher = sticks sooner, lower = slips longer.
- **`decay(Nms)`** / **`hold(Nms)`** / **`timer(N)`** — explicit duration in milliseconds.
- **`glide(Ns, custom)`** — duration + custom easing keyword.
- **`draw(check|line, Nms)`** — SVG stroke-dashoffset animation.
- **`stagger(Nms)`** — sequential delay between items.
- **`burst(particles: N)`** — particle count for radial effects.
- **`scramble(Nms/frame)`** — frame interval for glyph cycling.
- **`tilt(Ndeg max)`** — 3D tilt magnitude.
- **`lerp(0..1)`** — pointer-follow damping.
- **`rotate(0..Ndeg)`** — angle range for knob-style controls.
- **`press(Nms)`** — tactile press-down duration.
- **`pulse(Ns)`** / **`spin(Ns)`** / **`sweep(Ns loop)`** / **`drift(Ns)`** / **`marquee(Ns loop)`** — duration + `loop` keyword for infinite motion.

Where motion lives in code:

- All 99 cards embed three tabs in `data-lang="css"`, `data-lang="react"`, `data-lang="prompt"` `<pre>` blocks.
- CSS samples are copy-pasteable into any stylesheet; many include a JS comment like `/* JS computes offset from pointer to center, ... */` to flag what is not in the CSS alone.
- React samples use `useState`/`useRef`; assume a function component, no external animation library.
- Prompt samples are written as imperative instructions ("Build a ... that ...") and target an LLM, not a human.

## Procedure

1. **Identify the intent.** What micro-interaction does the user want? Map it to one of the ten intent buckets in **Pattern vocabulary** (press, toggle, numerical input, drag, confirmation, loading, status, reveal, attention, ambient).
2. **Pick 1-3 candidates.** Within the bucket, choose presets that match the visual energy the user described (snappy vs slow, decorative vs functional, with/without JS). Read the desc on each candidate from the on-page card.
3. **Fetch the snippet.** Pull `https://kinetics.colorion.co/` via `terminal` (curl) or `web_extract`. Locate the card by name; extract the `<pre data-lang="css">` (default), `<pre data-lang="react">`, or `<pre data-lang="prompt">` block as needed. If the snippet is long enough to repeat, save the parsed file with `write_file` and read the matching card with `read_file`. Strip HTML entities (`&lt;` -> `<`, `&#x27;` -> `'`, `&amp;` -> `&`).
4. **Tune the physics readout.** If the user said "snappier" / "more bouncy" / "slower" / "more weight", adjust the two numbers in the readout header:
   - Stiffness +20-40 = faster snap, less travel.
   - Stiffness -40-80 = lazier, more drift.
   - Damping <18 = oscillates (multiple bounces).
   - Damping 22-28 = critically damped (one overshoot, settle).
   - Damping >30 = overdamped (no overshoot, slower settle).
5. **Port to the user\'s stack.** CSS samples drop into any stylesheet. React samples assume `useState`/`useRef`; if the user is on Vue/Svelte/Solid, translate the state + JSX by hand but keep the CSS verbatim — the look is the same. Prompt samples are already LLM-ready; pipe them straight into the user\'s model of choice.
6. **Wire the trigger.** Most cards assume a click/hover/focus event. Confirm the trigger in the user\'s context (e.g. button `onClick`, input `onFocus`, list item `onPointerDown`). Wire the state class that the CSS expects (e.g. `.expanded`, `.bump`, `.open`).
7. **Respect reduced motion.** Kinetics does not bundle `@media (prefers-reduced-motion: reduce)` handlers. When porting, wrap any infinite or large-motion animation in `prefers-reduced-motion: reduce { animation: none }` unless the user explicitly opts in to motion.
8. **Verify locally.** Render the snippet in a sandbox (`open in browser`, a Storybook, or the user\'s app) and confirm the trigger fires, the spring settles, and there is no layout thrash on rapid re-trigger.

## Pitfalls

- **No API, no JSON dump, no RSS.** The catalog exists only as the rendered HTML of `kinetics.colorion.co/`. If you need to enumerate all 99 in code, fetch the page with `terminal` curl and parse `<div class="card">` blocks (99 of them) — `search_files` and `read_file` are not relevant because the source is a remote single-page app. The README in `github.com/ckissi/kinetics` confirms the structure: `src/content/body.html` holds all 99 cards.
- **CSS snippets often need a JS partner.** Many cards contain a CSS-only stub plus a `/* JS computes ... */` comment flagging the JS you still need to write (drag tracking, pointer math, scrub mapping, hold timer). Do not assume "the CSS does it all."
- **Cubic-bezier stand-ins are not springs.** When a snippet uses `transition: ... cubic-bezier(0.34, 1.56, 0.64, 1)`, that is the cheap CSS-only approximation of a spring — it does NOT interrupt cleanly. If the user needs interrupt-safe motion, push them toward Framer Motion, Motion One, or `@react-spring/web`, which run the real physics solver. The cubic-bezier is the portable fallback.
- **React samples use functional `useState`/`useRef`.** If the user is on class components or a non-React framework, translate by hand; the CSS portion is the same.
- **No TypeScript types are shipped.** Treat the React snippets as TS-compatible but untyped — wrap in your own interfaces if your project is strict.
- **The 99 count is hard-coded** as `33 / 99` on every category badge; do not trust any text that suggests more or fewer effects.
- **Pulse Badge appears twice.** Once in Feedback & State (`pulse(1.8s)`) and once again as `ring 1.8s ease-out`. They are sibling presets, not a duplicate bug.
- **No `prefers-reduced-motion` baked in.** Add it yourself; the library does not.
- **The library is MIT but the site itself is by Csaba Kissi / Colorion.** Credit is appreciated if you ship a large bundle of the snippets verbatim into a public product.
- **Do not invent presets that are not in the catalog.** If the user wants something the 99 do not cover (e.g. parallax scroll-jacking, scroll-linked 3D, view transitions API), say so — those are out of Kinetics\' scope. Kinetics is micro-interactions, not full-page choreography.

## Verification

- A live `terminal` `curl -sSL https://kinetics.colorion.co/` returns a single-page HTML containing 99 `<div class="card">` blocks (count the opens after fetching).
- The page has only three top-level section IDs (`#library`, `#physics`, `#about`) and the GitHub repo is `github.com/ckissi/kinetics`. There is no `/docs` or Markdown alternate.
- Given an intent (e.g. "loading spinner"), you can name 1-3 candidate presets from the catalog without re-reading the page.
- Given a snippet choice, you can explain what physics readout to tune and how to wire the trigger in a vanilla HTML/CSS/JS context.
