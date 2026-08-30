---
name: neural-3d-mesh-generation
description: "Generate 3D meshes via neural image-to-3D models."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ThreeJS, 3D, Generative, Game-Assets, MPS, image-to-3d]
    category: creative
    related_skills: [text-to-threejs-pipeline, img2threejs, ai-generated-asset-quality-diagnosis]
---

# Neural 3D Mesh Generation

Generate real, textured 3D assets (`GLB` + PBR maps) from a text description or reference image using **neural image-to-3D / text-to-3D models**, reaching the quality bar set by hosted services like Meshy (1 mesh, 1 PBR material, 4 texture maps: albedo/normal/metallic-roughness/emissive). This is the *neural* route. The **procedural** route (text → reference image → img2threejs forge → TS factory) is a separate class — see `text-to-threejs-pipeline`.

## When to Use

- "Generate a 3D mini / monster / prop as good as Meshy" — the bar is a paid hosted API's output and you want it in-house or cheaper.
- Choosing a text-to-3D / image-to-3D engine and sizing it against available hardware (Apple Silicon unified memory, GPU VRAM).
- Deciding local vs cloud (fal.ai / Meshy) for a mesh-generation pipeline.
- Wiring a mesh provider into an app that currently calls Meshy (provider-swap, see Integration pattern).

## Decision: cloud vs local (checked 2026-08)

**Nous Research subscription has NO 3D generation tool.** Verified against the official docs (`hermes portal tools` + docs): the Tool Gateway is exactly five tools — Firecrawl (web), FAL **2D** image models, OpenAI TTS, Browser Use, Modal sandbox. Do not search the Nous catalog for 3D.

The same FAL partner hosts the SOTA open 3D models as cheap managed APIs (no GPU needed on your side):

| Model on fal.ai | Price/run | Output | License |
|---|---|---|---|
| TRELLIS (image→3D, 2B) | $0.02 | mesh GLB + texture | MIT |
| TRELLIS.2 (image→3D, 4B, full PBR) | ~$0.02-0.10 | GLB + PBR | MIT |
| Hunyuan3D v3.1 rapid (text→3D) | $0.225 | OBJ+MTL+texture | Tencent community |
| Hunyuan3D v3.1 pro (text→3D, PBR) | $0.375 | GLB | Tencent community |

Rule of thumb: **precompute campaigns** (e.g. 334 SRD monsters) make cloud cost trivial — 334 × $0.02 = ~$7 — and skip the local-memory problem entirely. On-demand/interactive generation is where local or a hosted API with fast queues matters.

## Local model landscape (Apple Silicon, 2026-08)

| Model | VRAM/unified mem | Notes |
|---|---|---|
| **TRELLIS.2** (Microsoft, MIT) | 24GB needed (trellis-mac port) | SOTA, full PBR, ~3s at 512³ on CUDA; **too big for a 16GB Mac** |
| **Pixal3D** (Tencent, MIT) | claims 6GB, 1024-cascade | rides TRELLIS.2-4B decoders; `inference.py` is **CUDA-hardcoded** (no MPS path) |
| **Hunyuan3D-2.1** (Tencent, open weights) | light 6-8GB; full 12-16GB | MPS-capable Apple Silicon fork (Brainkeys/Hunyuan3D-2.1-mac); GLB export; ~3-10 min/shape on MPS; texture via CPU-rasterizer fallback |
| TripoSR / Stable Fast 3D | 4-8GB | faster, lower quality than the above |

**Hunyuan3D-2.1 is the realistic local choice on a 16GB M4.** License is the Tencent Community License — commercial use OK for a US-based product (you own the Outputs), but the license explicitly excludes EU/UK/South Korea territory; TRELLIS is MIT if you must avoid that.

## Local setup (Hunyuan3D-2.1-mac on M4)

Full install transcript + working spike script in `references/hunyuan3d-mac-setup.md`. Essentials:

- **Python 3.11/3.12 required** (the fork's PyTorch pin does not support 3.13). `pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1` then `requirements-macos.txt`.
- Shape pipeline import needs `pymeshlab` (heavy wheel) and `sys.path` inserts for `hy3dshape` + `hy3dpaint`. Texture import needs **`xatlas`** — the fork's README says skip it, but `pip install xatlas` works on ARM64 and unlocks texture gen.
- Model: `huggingface-cli download tencent/Hunyuan3D-2.1` — **14.9GB** (shape 7.4GB fp16 + paint 5.4GB + VAE 0.65GB), not gated.
- `from_pretrained("tencent/Hunyuan3D-2.1")` with no device args auto-detects MPS — don't pass CUDA-only kwargs like `device_map`/`torch_dtype` from the original README.
- Pipeline is **image-to-3D** (not text-to-3D): every mesh needs a reference image first. This matches how Meshy works internally — plan for a reference-image stage.

## Memory strategy (16GB unified — the hard constraint)

The 7.4GB fp16 shape model load **thrashes a 16GB Mac**: swap usage hit ~12.7GB and free memory dipped to ~1% during the spike's model load. It recovered, but treat this as the expected baseline.

- **Sequential load → generate → free.** NEVER keep the shape model and the texture model resident simultaneously (7.4 + 5.4 + activations). `del pipeline; gc.collect(); torch.mps.empty_cache()` between phases; peak RSS then stays ~one model, not the sum.
- `PYTORCH_ENABLE_MPS_FALLBACK=1` for unsupported ops; `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0` lets MPS use the full unified pool.
- Monitor with `memory_pressure -Q` (free percentage), `sysctl vm.swapusage`, and `torch.mps.current_allocated_memory()`. Watch `swapouts` climbing — that is the real OOM signal on Apple Silicon.
- Plan ~5+ min per shape under swap pressure; batch work as a **background precompute campaign** (durable, resume-safe), never a foreground interactive call.

## Integration pattern (provider swap)

Shape the local/cloud mesh client **exactly like the existing Meshy client** (same `generateModel(prompt, onProgress) → Buffer<GLB>` signature, same `{phase, phaseProgress, overallProgress}` progress shape) so app call sites swap providers via a one-line env gate:

```
MESHGEN_URL set (local service healthy) → local neural
else MESHY_API_KEY set                    → Meshy
else                                      → parametric builder (last resort)
```

Precompute pattern: per-entity definition rows (e.g. `content_ai_definitions.kind = 'monster_mesh'`) already hold the canonical LLM prompt; extend the row with a `meshAssetId` after generation so spawn-time lookup is instant (skip-if-exists resume, run-summary row — the insights-precompute skeleton).

## Pitfalls

- **Background-process output buffering**: piping a long ML run through `grep | tail` hides ALL progress until exit — you cannot tell load vs diffusion vs stuck. Run the heavy process directly (or `tee` to a file) and poll the actual process/artifacts (`ps` CPU time, target-file existence, `memory_pressure`) instead of the pipe.
- **cwd drift**: a `cd` into a spike dir makes subsequent relative writes (plan docs!) land in the wrong tree. Verify absolute paths or `cd` back before writing repo files.
- **Don't trust the fork README's "texture disabled on Mac"** — the CPU rasterizer fallback + `--enable_tex` + `xatlas` does work; the README's caution is stale. Verify by import, not by assumption.
- **Reference image quality is the ceiling** — a bad image (scene shot, baked shadows, text on surfaces) produces a bad mesh. Reuse the intake prompt recipe (front orthographic, neutral background, no text) from `text-to-threejs-pipeline`.
- **License territory clauses** — Tencent community licenses exclude EU/UK/KR; if the product may serve those regions, prefer MIT (TRELLIS) or a cloud API.

## References

- `references/hunyuan3d-mac-setup.md` — full install transcript, working spike script, memory measurements from the 2026-08-12 M4 spike.
