---
name: moodnode-prompt-expert
description: "Compose prompts from MoodNode's library and Director's Eye."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Prompting, Cinematography, Image, MoodNode, Reference]
    category: creative
---

# MoodNode Prompt Expert

Expert knowledge of MoodNode's two public prompt catalogs: the MoodLibrary (324+ ready-to-use image prompts at `https://moodnode.ai/tools/prompt-library`) and Director's Eye (114 cinematic technique prompts — angles, lighting, lens, composition, movement — at `https://moodnode.ai/tools/directors-eye`). This skill knows the URL scheme, the catalog anatomy, and the prompt-writing conventions, so you can look up, adapt, and run any of these prompts with Hermes image tools. It does NOT cover the MoodNode Canvas app itself (app.moodnode.ai login, model picker, in-app generation); treat the catalogs as a copyable source of prompt text.

## When to Use

- User wants a cinematic/portrait image and names a technique: "use a Dutch angle", "chiaroscuro lighting", "dolly zoom", "teal & orange grade".
- User asks for a film look, a specific shot scale, lighting setup, or lens feel.
- User wants character-consistent output from a reference photo ("keep the face identical", "same facial features").
- User pastes a moodnode.ai link and asks to use or adapt that prompt.
- Any image generation where a structured, layered prompt beats ad-hoc phrasing.

## Prerequisites

- No credentials — all catalog pages are public.
- `web_extract` to fetch catalog/detail pages; `image_generate` (or FLUX3 tools) to run the resulting prompt; `vision_analyze` to inspect thumbnails, references, or outputs.

## How to Run

1. `web_extract` the detail page for the prompt (URL scheme below); for Director's Eye pages also read the "When to use" and "Pro tips" blocks.
2. Take the full prompt text and adapt it to the target model — splice in the technique block, keep identity-lock phrases when a reference image will be attached.
3. Run it with `image_generate` (text-to-image) or pass the reference via `image_url` (image-to-image) when the prompt references an uploaded image.

## Quick Reference

URLs:

- Library index: `https://moodnode.ai/tools/prompt-library`
- Director's Eye index: `https://moodnode.ai/tools/directors-eye`
- Any prompt detail page: `https://moodnode.ai/tools/prompt-library/p/<slug>` (e.g. `p/chiaroscuro-lighting`, `p/high-angle-shot`)
- Canvas deep link: `https://app.moodnode.ai/login?prompt=<slug>`
- Full-size technique image: `https://cdn.moodnode.ai/seed-data/directors-eye-full/<slug>.webp`
- Library thumbnails: `https://cdn.moodnode.ai/seed-data/thumbnails/seed-<NNNN>.webp`

MoodLibrary filter tabs: All, Portrait, Editorial, Product, Landscape, Action, Food, Architecture, Concept, Cinematic, Street.

Director's Eye categories with counts: Camera 21, Lighting 28, Lens 13, Composition 20, Color 6, Creative 8, Movement 17, Time 1. Full 114-item list with slugs and short descriptions: `references/directors-eye-catalog.md`.

Detail-page anatomy (both catalogs): title, one-line description, full copyable prompt, "When to use", "Pro tips" (exact phrasings that make the technique work), a tag row (e.g. `directors-eyelightingintermediatecinematic`), Related prompts, Canvas deep link.

## Procedure

1. **Find the technique.** For Director's Eye, look up the slug in `references/directors-eye-catalog.md` (load with `your harness's skill loader` if needed). For the library, `web_search` the site or `web_extract` the index.
2. **Fetch the detail page** with `web_extract("https://moodnode.ai/tools/prompt-library/p/<slug>")` — this returns the complete prompt, unlike the truncated index entries.
3. **Read the craft hints.** "Pro tips" encode the exact terms, e.g. `"chiaroscuro lighting, extreme contrast, single hard light, deep black shadows"`, `"high angle shot, camera tilted down 45 degrees from above"`, `"90% shadow, 10% bright highlights"`.
4. **Compose the target prompt** by layering MoodLibrary conventions — subject/appearance; pose/action; environment; style/mood; camera/lens/framing; lighting — then splicing in the Director's Eye technique block.
5. **For reference-image prompts**, keep the identity lock language verbatim: "Use the same facial features, expression, and identity from the uploaded image without altering any facial structure, proportions, or features" (also seen: "DO NOT CHANGE THE FACE", `[UPLOADED IMAGE]` placeholder, `negative_prompt: "no face changes..."`). Pass the reference with `image_generate(image_url=...)`.
6. **Run and verify** with `image_generate`, then `vision_analyze` the output to confirm the technique reads as intended. If the user wants the prompt reused, save it with `write_file`.

## Pitfalls

- **Index pages truncate.** Library entries end with "..." and the library index is ~260K chars — `web_extract` returns head+tail with the full text cached to disk (page it with `read_file`). For one prompt, skip the index and fetch the `/p/<slug>` page.
- **Detail pages duplicate the prompt.** Extracted pages repeat the opening paragraph in a "TPrompt···" block — dedupe before sending to a model.
- **Titles are fragments.** Library titles like "Young woman" or "She has short" are truncated sentence starts; the slug is the stable identifier.
- **Identity-lock phrases need a reference image.** "[UPLOADED IMAGE]", "use the provided user face", "DO NOT CHANGE THE FACE" only make sense with a reference attached; strip them for pure text-to-image.
- **Director's Eye prompts are hyper-specific on purpose** — exaggerated angles ("12 feet HIGH ABOVE", "60 degree angle"), numeric light ratios, ALL-CAPS emphasis. That specificity is the craft; don't soften it when adapting.
- **Full-size reference images are fetchable** — `https://cdn.moodnode.ai/seed-data/directors-eye-full/<slug>.webp`. Download one with `terminal` curl when you want a local visual reference (or an image-to-image seed) before generating: `curl -sSL https://cdn.moodnode.ai/seed-data/directors-eye-full/chiaroscuro.webp -o /tmp/ref.webp`, then inspect with `vision_analyze`.
- **Some library prompts are risqué** (fashion/glamour prompts describing underwear or bare skin). Keep output context-appropriate.
- **"Previous/Next" links follow catalog order**, not semantic relevance; use the "Related" section for that.
- For heavier catalog dumps (e.g. extracting all 114 slugs), do it once with `execute_code` and cache the result — repeated `web_extract` of the 33K-char index is wasteful.

## Verification

`web_extract("https://moodnode.ai/tools/prompt-library/p/chiaroscuro-lighting")` must return the full prompt containing "tenebrist", plus a "When to use" section and Pro tips citing "Caravaggio painting style". If the extracted text lacks the full prompt block, the fetch failed — retry or use the browser tools.
