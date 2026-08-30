---
name: text-to-lottie
description: Generate production-ready Lottie JSON animations.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Animation, Lottie, JSON, Skia]
---

# Text-to-Lottie

Author production-ready Lottie (Bodymovin) JSON animations and preview them with the Skia/Skottie player.

## Setup

Scaffold from the official player project using `terminal`:

```bash
npx degit diffusionstudio/lottie my-animation
cd my-animation
npm install
npm run dev
```

Then open `http://localhost:3030`.

## Folder structure

```text
public/projects/<project-slug>/<scene-N>/lottie.json
```

- `lottie.json` is required.
- `controls.json` is optional sidecar metadata.
- Images (.png/.jpg/.svg) go in the scene folder as assets.

## Rules

- Slugs are URL segments; keep them lowercase.
- Scene order is determined by the trailing `-N` suffix.
- Image assets are referenced by bare filename in `assets[].p`.
- Every animation must expose at least a background-color slot.

## Lottie JSON structure

- `v`: version.
- `fr`: framerate.
- `ip`/`op`: in/out points.
- `w`/`h`: dimensions.
- `nm`: name.
- `assets`: external images.
- `slots`: editable properties.
- `layers`: animation layers (`ty: 4` shape layers, `ks` transforms, `shapes` with `gr`, `el`, `fl`, etc.).

## Slots

Add a top-level `slots` object with unique slot IDs. Properties reference slots via `"sid"` instead of inline values.

Slot types:
- `scalar` → slider.
- `color` (RGBA 0-1) → color picker.
- `vec2` → two inputs.
- `text` → text input.

Optional `controls.json` maps slot IDs to labels and slider min/max/step.

## Verification

- Use `?frame=N` to seek and pause at a specific frame.
- Query `GET /__context` for the project tree, active scene, and playback state.
- New scenes: capture screenshots at frame 0, midpoint, and last frame.
- Small edits: capture 1-2 screenshots.
- Validate JSON with `node -e "JSON.parse(...)"` through `terminal`.

## Best practices

- Prefer easings over linear motion.
- Think about overall motion design, not single properties.
- For complex animations, write a generator script to emit the JSON.
