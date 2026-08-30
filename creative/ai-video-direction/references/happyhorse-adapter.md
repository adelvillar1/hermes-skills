# HappyHorse 1.1 — Model Adapter (Qwen / DashScope)

Verified: 2026-08-01 from official Alibaba Cloud Model Studio docs.
Models: `happyhorse-1.1-t2v`, `happyhorse-1.1-i2v`, `happyhorse-1.1-r2v`
Tagline: "Cinematic creative generation, ultimate dynamic details"

---

## API Pattern

All three modes share the same async workflow:

1. **POST** `/api/v1/services/aigc/video-generation/video-synthesis` → get `task_id`
2. **GET** `/api/v1/tasks/{task_id}` → poll until `SUCCEEDED` (1-5 min, poll every 15s)
3. Download video from `video_url` (valid **24 hours**, MP4 H.264)

### Required Headers

```
Content-Type: application/json
Authorization: Bearer $DASHSCOPE_API_KEY
X-DashScope-Async: enable          ← REQUIRED, sync not supported
```

### Regions & Endpoints

| Region | Endpoint |
|---|---|
| Singapore | `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com` |
| US (Virginia) | (check console) |
| China (Beijing) | `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com` |
| Germany (Frankfurt) | (check console) |
| China (Hong Kong) | (check console) |
| Japan (Tokyo) | (check console) |

Legacy domains (`dashscope.aliyuncs.com` / `dashscope-intl.aliyuncs.com`) may still work for generic keys, but **workspace-bound keys are REJECTED on them** — see the verified failure below.

**Model, endpoint URL, and API key must all belong to the same region.** Cross-region calls fail.

### Verified setup (2026-08-08, Hermes user)

- Workspace ID: `token-plan`, region Singapore. Full base: `https://token-plan.ap-southeast-1.maas.aliyuncs.com` — use it for BOTH the create call and task polling.
- **Legacy domains fail with this key.** POST to `dashscope-intl.aliyuncs.com` returns `{"code":"InvalidApiKey","message":"Invalid API-key provided."}`. This is the #1 integration mistake — always use `https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`.
- Credentials live in `~/.hermes/.env`: `DASHSCOPE_API_KEY` (secret) and workspace id `token-plan` (also visible in `ALIBABA_CODING_PLAN_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`).
- Working example (this user): `happyhorse-1.1-t2v`, 720P, 16:9, 8s, `watermark:false` → SUCCEEDED in ~2 min, downloaded MP4 h264 1280×720 24fps.

---

## Mode: Text-to-Video (`happyhorse-1.1-t2v`)

```json
{
  "model": "happyhorse-1.1-t2v",
  "input": {
    "prompt": "A miniature city built from cardboard and bottle caps comes to life at night. A cardboard train slowly passes through, with small lights dotting the scene."
  },
  "parameters": {
    "resolution": "720P",
    "ratio": "16:9",
    "duration": 5
  }
}
```

### Parameters

| Param | Values | Default |
|---|---|---|
| `resolution` | `480P`, `720P`, `1080P` | `1080P` |
| `ratio` | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `4:5`, `5:4`, `9:21`, `21:9` | `16:9` |
| `duration` | 3–15 (integer, seconds) | 5 |
| `watermark` | `true` / `false` | `true` |
| `seed` | 0–2147483647 | random |

### Prompt Budget

- Max **5,000 non-Chinese characters** or **2,500 Chinese characters**
- Excess is truncated
- Supports any language

---

## Mode: Image-to-Video (`happyhorse-1.1-i2v`)

First-frame driven. The image IS the opening frame; prompt describes motion.

```json
{
  "model": "happyhorse-1.1-i2v",
  "input": {
    "prompt": "A cat running on the grass",
    "media": [
      {
        "type": "first_frame",
        "url": "https://example.com/image.png"
      }
    ]
  },
  "parameters": {
    "resolution": "720P",
    "duration": 5
  }
}
```

### Parameters

| Param | Values | Default |
|---|---|---|
| `resolution` | `480P`, `720P`, `1080P` | `1080P` |
| `duration` | 3–15 (integer, seconds) | 5 |
| `watermark` | `true` / `false` | `true` |
| `seed` | 0–2147483647 | random |

Note: No `ratio` param for I2V — output preserves the input image's aspect ratio.

### Image Constraints (first_frame)

- Formats: JPEG, JPG, PNG, WEBP
- Min resolution: 300×300 px
- Aspect ratio: between 1:2.5 and 2.5:1
- Max file size: 20 MB
- Input: public URL (HTTP/HTTPS) or Base64 (`data:{MIME};base64,{data}`)

### Prompt for I2V

- **Optional** (but recommended for motion direction)
- Same 5,000/2,500 char limit
- Describe only MOTION, CAMERA, TIMING, AUDIO — the image already carries identity
- Per the directing skill: "Preserve reference exactly; add only dynamic changes"

---

## Mode: Reference-to-Video (`happyhorse-1.1-r2v`)

Multiple reference images composited into a scene. The most powerful mode for product/brand work.

```json
{
  "model": "happyhorse-1.1-r2v",
  "input": {
    "prompt": "A woman in a red qipao from [Image 1] is shown in a profile medium shot. She unfolds the fan from [Image 2] while the tassel earrings from [Image 3] sway. The scene ends with a close-up of her face.",
    "media": [
      {"type": "reference_image", "url": "https://example.com/woman.jpg"},
      {"type": "reference_image", "url": "https://example.com/fan.jpg"},
      {"type": "reference_image", "url": "https://example.com/earrings.jpg"}
    ]
  },
  "parameters": {
    "resolution": "720P",
    "ratio": "16:9",
    "duration": 5
  }
}
```

### Parameters

Same as T2V: `resolution`, `ratio`, `duration`, `watermark`, `seed`.

### Reference Image Rules

- **1 to 9 reference images**
- Referenced in prompt as `[Image 1]`, `[Image 2]`, ... `[Image 9]`
- Order in `media` array = order of `[Image N]` references
- **Specify the object**: "the woman in a red qipao in [Image 1]" not just "[Image 1]"
- Formats: JPEG, JPG, PNG, WEBP
- Min resolution: shortest side ≥ 400 px (720P+ recommended)
- Max file size: 20 MB each
- Input: public URL or Base64

### Prompt for R2V

- **Required**
- Same 5,000/2,500 char limit
- Use `[Image N]` syntax to bind references to roles
- Per the directing skill: assign each reference ONE primary role (identity, environment, motion, style, prop)
- State what must NOT transfer if needed

---

## Mapping to Directing Skill Concepts

| Skill concept | HappyHorse implementation |
|---|---|
| Director Formula (Subject+Action+Scene+Camera+Light+Audio+Constraints) | Goes in `prompt` field |
| Mode selection | Choose model: `t2v` / `i2v` / `r2v` |
| Reference role binding | `[Image N]` syntax in R2V prompt |
| I2V preservation | Image carries identity; prompt adds only motion/camera/timing |
| Allocation model | Duration 3-15s; resolution 480P-1080P; budget accordingly |
| Anti-slop | 5,000 char budget is generous but early-clause priority still applies |
| Seed for reproducibility | `seed` param (0–2147483647); same seed ≠ guaranteed identical |
| Retake protocol | Same prompt + new seed = re-roll; same seed + prompt change = controlled experiment |
| Multi-shot | NOT supported natively — use sequence workflow (multiple generations) |
| Audio | NOT mentioned in API — likely no native audio; add in post |
| Watermark | Default ON; set `watermark: false` for production |

---

## Practical Notes

### Draft Cheap, Lock Expensive

- Draft at `480P` + `duration: 3` → fast iteration
- Lock at `1080P` + full duration only when the prompt is proven
- Ten 3-second 480P drafts answer more than one failed 15-second 1080P take

### No Native Multi-Shot

HappyHorse does not support labeled cuts inside one generation. For multi-shot stories, use the sequence workflow from the directing skill: plan globally, generate one clip at a time, chain from accepted footage.

### Image Generation (wan2.7-image / wan2.7-image-pro)

User's token plan includes `wan2.7-image` and `wan2.7-image-pro` for image generation. Use in the video pipeline:

1. **Storyboard:** Generate key frames before committing to video
2. **First-frame for I2V:** Generate the exact opening composition with wan2.7-image-pro → feed as `first_frame` to `happyhorse-1.1-i2v`
3. **Reference images for R2V:** Generate product/brand/character references → feed as `reference_image` to `happyhorse-1.1-r2v`
4. **Style exploration:** Test visual directions cheaply before spending video generation budget

Workflow: `wan2.7-image-pro` (compose frame) → `happyhorse-1.1-i2v` (animate it) = full Qwen-native production.

wan2.7-image-pro strengths (from Alibaba docs): interactive editing, long-text rendering, precise prompt following.

### Audio via Qwen-Audio-3.0-TTS-Plus

HappyHorse generates NO native audio. However, the user's token plan includes `Qwen-Audio-3.0-TTS-Plus` for speech synthesis. Production workflow:

1. Generate video with HappyHorse (silent)
2. Generate voiceover/narration with `Qwen-Audio-3.0-TTS-Plus`
3. Combine via ffmpeg: `ffmpeg -i video.mp4 -i narration.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4`
4. Add music/SFX in post (CapCut, Premiere, DaVinci)

For dialogue scenes: keep lines short (per directing skill §8), generate TTS per line, sync to the locked-face footage.

### Watermark

Default `true` — shows "HappyHorse" in lower-right. Set `false` for any production use.

### Task Lifecycle

- `PENDING` → `RUNNING` → `SUCCEEDED` / `FAILED`
- `task_id` valid for 24 hours
- `video_url` valid for 24 hours — download immediately
- Do NOT create duplicate tasks; poll the existing one

### Billing (usage object)

```json
{
  "duration": 5,
  "input_video_duration": 0,
  "output_video_duration": 5,
  "video_count": 1,
  "SR": 720,
  "ratio": "16:9"
}
```

Billed on output duration × resolution tier.

---

## Quick-Start Script

```bash
#!/bin/bash
# HappyHorse T2V quick test
# Requires: DASHSCOPE_API_KEY (in ~/.hermes/.env) and WORKSPACE_ID env vars.
# WORKSPACE_ID is auto-derived below when unset (workspace-bound keys are rejected on legacy domains).
export DASHSCOPE_API_KEY=$(grep -E '^DASHSCOPE_API_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2- | tr -d '"')
export WORKSPACE_ID=${WORKSPACE_ID:-$(grep -oE 'https://[a-z0-9-]+\.ap-southeast-1\.maas' "$HOME/.hermes/.env" | head -1 | sed -E 's#https://([a-z0-9-]+)\..*#\1#')}

RESPONSE=$(curl -s --location \
  "https://${WORKSPACE_ID}.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis" \
  -H 'X-DashScope-Async: enable' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "happyhorse-1.1-t2v",
    "input": {
      "prompt": "A glass of Malbec wine on a dark wooden table. Candlelight from the left catches the ruby color. A hand lifts the glass slowly, revealing the cow-head brand mark on the label. Camera: slow push-in from medium to close-up. Sound: silence, one soft clink."
    },
    "parameters": {
      "resolution": "720P",
      "ratio": "16:9",
      "duration": 5,
      "watermark": false
    }
  }')

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['output']['task_id'])")
echo "Task: $TASK_ID"
echo "Polling..."

while true; do
  sleep 15
  RESULT=$(curl -s "https://${WORKSPACE_ID}.ap-southeast-1.maas.aliyuncs.com/api/v1/tasks/${TASK_ID}" \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['output']['task_status'])")
  echo "  Status: $STATUS"
  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['output']['video_url'])"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "$RESULT"
    break
  fi
done
```
