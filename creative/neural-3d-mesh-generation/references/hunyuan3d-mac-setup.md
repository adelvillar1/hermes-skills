# Hunyuan3D-2.1-mac on an M4 — install transcript & spike evidence (2026-08-12)

Verified working setup for running Tencent Hunyuan3D-2.1 image-to-3D locally on an Apple M4 (16GB unified, macOS). Everything below was executed successfully in the spike; the one caveat is the full diffusion run was still in progress at session end (model load confirmed, diffusion under swap pressure).

## Hardware baseline

- `sysctl -n machdep.cpu.brand_string` → Apple M4; Metal 4
- `sysctl -n hw.memsize` → 16 GB unified
- PyTorch 2.8 MPS available (`torch.backends.mps.is_available()` → True)
- 63 GB free disk

## Install (worked, in order)

```bash
# 1. Python 3.11 is REQUIRED — the fork's pinned torch 2.5.1 does not support 3.13.
/opt/homebrew/bin/python3.11 --version   # 3.11.15
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate

# 2. macOS torch (NOT the CUDA wheels from the original README)
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1

# 3. Fork deps (CUDA-free)
pip install -r requirements-macos.txt

# 4. pymeshlab is NOT in requirements-macos.txt but the shape pipeline imports it.
#    Heavy wheel — install separately, allow several minutes.
pip install pymeshlab

# 5. xatlas is needed by the texture pipeline (uvwrap). The fork README says skip it
#    due to CMake issues, but `pip install xatlas` resolves fine on ARM64 and
#    unlocks texture generation. Without it: ModuleNotFoundError on import.
pip install xatlas

# 6. Model weights — 14.9 GB, NOT gated on HF.
huggingface-cli download tencent/Hunyuan3D-2.1
#   shape model  hunyuan3d-dit-v2-1/model.fp16.ckpt    7.4 GB
#   texture      hunyuan3d-paintpbr-v2-1/...           5.4 GB (unet 3.9GB + encoders)
#   VAE          hunyuan3d-vae-v2-1/model.fp16.ckpt    0.65 GB
```

## Import smoke test (both pipelines)

```python
import sys
sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')
from platform_utils import get_platform, configure_torch_device
p = get_platform()
# -> platform: Darwin arm64, mps available: True, device: mps
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline   # shape
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig  # texture
```

Key gotchas discovered:
- `from_pretrained("tencent/Hunyuan3D-2.1")` with **no device args** auto-detects MPS via `_get_default_device()`. Do NOT copy `device_map="auto"`/`torch_dtype=` from the original repo's demo — those are CUDA-isms.
- The texture import prints `InPaint Function CAN NOT BE Imported!!!` and `Warning: bpy (Blender Python) not available` — both benign on Mac; the pipelines still import and run.
- Shape import fails first without `pymeshlab`; texture fails first without `xatlas`.

## Memory-conscious spike script pattern

The 7.4GB fp16 shape model **thrashes a 16GB machine during load**: measured `memory_pressure` free dropped 46% → **1%** → 25%, and `vm.swapusage` showed **12.7GB swap used**. This recovers after load completes, but plan for it.

Structure every long run as sequential phases so models are never co-resident:

```python
import gc, torch
def mem_report(tag):
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    print(f"[mem] {tag}: peak RSS ~{rss:.0f} MiB", flush=True)
    if torch.backends.mps.is_available():
        print(f"[mem] {tag}: MPS {torch.mps.current_allocated_memory()/1048576:.0f} MiB", flush=True)

def free_pipeline(pipe):
    del pipe; gc.collect()
    if torch.backends.mps.is_available(): torch.mps.empty_cache()

# phase 1: shape only
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2.1")
meshes = pipe(image=img, num_inference_steps=30, output_type="trimesh")
meshes[0][0].export(out_glb, file_type="glb")
free_pipeline(pipe)   # <-- REQUIRED before texture phase

# phase 2: texture (only after shape freed)
conf = Hunyuan3DPaintConfig(max_num_view=4, resolution=512)
conf.realesrgan_ckpt_path = "hy3dpaint/ckpt/RealESRGAN_x4plus.pth"
conf.multiview_cfg_path = "hy3dpaint/cfgs/hunyuan-paint-pbr.yaml"
conf.custom_pipeline = "hy3dpaint/hunyuanpaintpbr"
paint = Hunyuan3DPaintPipeline(conf)
paint(mesh_path=shape_glb, image_path=img, output_mesh_path=out_textured_glb)
```

Env for MPS runs:
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0
```

## Monitoring during a long run (no live output through pipes)

- `ps aux | grep <pid>` → CPU% + cumulative TIME (rising TIME = still working, not stuck)
- `memory_pressure -Q` → "System-wide memory free percentage"
- `sysctl vm.swapusage` → swap used / total (climbing swapouts = OOM pressure)
- `ls -la <target.glb>` → artifact existence (export is the last step)
- NOTE: piping the python process through `grep | tail` buffers ALL output until exit — you cannot distinguish model-load vs diffusion vs hung. Run the process unbuffered (`python -u`) or `tee` to a file, and poll process state separately.

## Pitfalls hit during the spike

1. **Python 3.13 breaks install** — torch 2.5.1 wheels for the fork require 3.11/3.12. Use `brew` python@3.11.
2. **`grep | tail` swallowed progress** — the whole run's output appeared only at exit, so mid-run state had to be inferred from `ps`/`memory_pressure`/target file.
3. **cwd drift** — a `cd /tmp/...` earlier in the session made a plan doc `write_file` land under `/tmp/hy3d-mac/docs/...` instead of the repo. Absolute paths or explicit `cd` back before repo writes.
4. **README "texture disabled on Mac" is stale** — the CPU rasterizer fallback + `--enable_tex` + `xatlas` provides a working texture path; verify by import rather than trusting the note.
5. **Swap is the real OOM signal on Apple Silicon** — free-memory percentage swings wildly during load; `vm.swapusage` climbing is what actually kills throughput.
