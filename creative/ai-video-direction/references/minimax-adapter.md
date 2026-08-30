# MiniMax — Model Adapter (Token Plan + mmx-cli)

> ⚠️ **STATUS: CANCELLED (2026-08-02)** — User's MiniMax subscription is no longer active. This adapter is archived for reference only. Do NOT use `mmx` commands unless the user confirms a new subscription. TTS → use `qwen-audio-3.0-tts-plus` or `qwen3.5-omni-plus` via DashScope. Music → no current replacement; use royalty-free libraries.

Verified: 2026-08-01 from platform.minimax.io/docs.
CLI: `mmx-cli` (npm install -g mmx-cli)
Note: MiniMax H3 launched 2026-08 but is NOT part of the user's token plan. Video model = existing Hailuo line.

---

## Why MiniMax

Single token plan covers the FULL production pipeline:

| Stage | Command | Notes |
|---|---|---|
| Video generation | `mmx video generate` | Async (task → poll → download) |
| Voiceover/narration | `mmx speech synthesize` | Multiple voices, streaming |
| Music/score | `mmx music generate` | With-lyrics OR instrumental modes |
| Image (storyboard/ref) | `mmx image generate` | Aspect ratio controls, batch |
| Vision QA | `mmx vision describe` | Analyze generated footage |
| Web search | `mmx search query` | Research/reference |
| Language | `mmx text chat` | Multi-turn, streaming, JSON output |

Output files saved to `minimax-output/` in current directory.

---

## Setup

```bash
# Install
npm install -g mmx-cli

# Auth (auto-detects region from key)
mmx auth login --api-key sk-xxxxx

# If 401 errors, set region manually:
mmx config set --key region --value global   # overseas
mmx config set --key region --value cn       # mainland China

# Verify quota
mmx quota

# Dashboard
mmx   # opens CLI panel with commands, flags, usage
```

### API Keys

- **Overseas:** Subscribe at platform.minimax.io → API Key
- **China:** Subscribe at platform.minimaxi.com → API Key

---

## Video Generation

```bash
mmx video generate "at sunset, a cat sits by the window looking into the distance"
```

Async workflow (same pattern as HappyHorse): create task → poll status → download result.

For directing-skill integration: write the prompt using the Director Formula (Subject + Action + Scene + Camera + Light + Audio + Constraints), then pass as the generation prompt.

### Video + Directing Skill Mapping

| Skill concept | MiniMax implementation |
|---|---|
| Director Formula | Prompt string to `mmx video generate` |
| Anti-slop | Apply before passing prompt — no "cinematic", name physical details |
| Allocation model | One primary spend per generation; MiniMax H3 strengths = motion quality |
| Retake protocol | Re-run with modified prompt (one variable change) |
| Sequence workflow | Generate clip by clip; use `mmx vision describe` to observe end state |

---

## Speech Synthesis (TTS)

```bash
mmx speech synthesize \
  --text "Your narration text here." \
  --voice "English_CaptivatingStoryteller" \
  --sample-rate 44100 \
  --bitrate 256000 \
  --speed 0.92 \
  --out /tmp/output.mp3
```

### Quality Settings (USER-APPROVED 2026-08-01)

**ALWAYS use these settings — defaults cause audible breakup:**

| Setting | Default (BAD) | Use this |
|---|---|---|
| `--sample-rate` | 32000 | **44100** |
| `--bitrate` | 128000 | **256000** |
| `--speed` | 1.0 | **0.92** (slightly slower, more gravitas) |
| `--voice` | English_expressive_narrator | **English_CaptivatingStoryteller** |

The 32kHz/128kbps default is optimized for streaming bandwidth, not quality. At 44.1kHz/256kbps the artifacts disappear.

### Available Voices (English)

Warm/brand: `English_CaptivatingStoryteller`, `English_Magnetic_Voiced_Man`, `English_Deep-VoicedGentleman`, `English_Graceful_Lady`
Neutral: `English_Trustworth_Man`, `English_CalmWoman`, `English_FriendlyPerson`
Energetic: `English_Upbeat_Woman`, `English_PassionateWarrior`

### Directing Skill Audio Mapping

| Skill guidance | MiniMax implementation |
|---|---|
| "Name each shot's specific sounds" | Write TTS script per clip |
| "Dialogue wants a stable face and short line" | Keep TTS lines short; sync to locked-face footage |
| "Sound thins at intimacy, thickens at threat" | Choose voice + pacing accordingly |
| Audio as clock of the edit | Generate TTS first, cut video to match timing |
| Narration timing | Delay voice 1.5s after video starts; keep TTS duration < video duration - 1s |

---

## Music Generation

```bash
# Instrumental (background score)
mmx music generate --prompt "A slow, intimate Argentine tango. Bandoneon and soft strings. Dark, warm, romantic." --instrumental

# With lyrics
mmx music generate --prompt "upbeat jazz about summer" --lyrics "Write lyrics about..."
```

**IMPORTANT:** `--prompt` is REQUIRED. For instrumental, add `--instrumental` flag. Without it, the CLI errors asking for `--lyrics`.

Two modes:
- **Instrumental** (`--instrumental`) — background score, ambience
- **With lyrics** (`--lyrics "..."`) — songs, jingles, branded audio

Generation takes 60-120+ seconds. Use background process or generous timeout.

### Production Use

- Generate score per scene/mood
- Layer under video in post (ffmpeg or editor)
- Match music energy to the directing spine's arc (open → rising → climax → release)
- Mix at 15-20% volume under narration (see assembly below)

---

## Image Generation

```bash
mmx image generate "cyberpunk city night scene" --ratio 16:9
```

Use for:
- Storyboard frames before video generation
- Reference images for I2V workflows (generate → use as first frame)
- Thumbnails and social cards
- Visual style exploration before committing to video

---

## Vision (QA / Continuity)

```bash
mmx vision describe ./minimax-output/video-frame.png
```

Use for:
- Describing the final frame of a generated clip (continuity handoff)
- QA checks: "does this frame match the brand guidelines?"
- Extracting observed end state for sequence continuation

---

## Full Production Workflow (MiniMax + Qwen hybrid)

```
1. mmx image generate / wan2.7-image-pro → storyboard / style frames
2. happyhorse-1.1-t2v (or mmx video)    → clip (apply directing engine)
3. mmx vision describe                   → observe end state (for sequences)
4. mmx speech synthesize                 → narration (44.1kHz, 256kbps, speed 0.92)
5. mmx music generate --instrumental     → score / ambience
6. ffmpeg                                → mux video + voice + music
7. Repeat per clip in sequence
```

### ffmpeg Assembly (USER-APPROVED mix settings 2026-08-01)

```bash
ffmpeg -y \
  -i video.mp4 \
  -i voice.mp3 \
  -i music.mp3 \
  -filter_complex "\
    [1:a]volume=1.0,adelay=1500|1500[voice];\
    [2:a]volume=0.18,afade=t=in:st=0:d=2,afade=t=out:st=8.5:d=1.5[music];\
    [voice][music]amix=inputs=2:duration=longest:dropout_transition=2[aout]" \
  -map 0:v -map "[aout]" \
  -c:v copy -c:a aac -b:a 256k \
  -t <video_duration> \
  output.mp4
```

**Mix rules (proven in Pampa Wine Club promo v3):**
- Voice: 100% volume, delayed 1.5s (let video establish first)
- Music: 18% volume, 2s fade-in, 1.5s fade-out ending at video_length - 1.5s
- TTS duration must be < video_duration - 1s (prevents cutoff)
- Output AAC at 256kbps (not 192 — matches the 44.1kHz source quality)
- Use `-t <video_duration>` to hard-trim to video length

---

## Comparison: MiniMax vs Qwen (HappyHorse)

| Dimension | MiniMax (mmx-cli) | Qwen (HappyHorse 1.1) |
|---|---|---|
| Video | ✅ Hailuo / H3 | ✅ T2V / I2V / R2V |
| Reference images | ❓ (check H3 docs) | ✅ Up to 9 refs with [Image N] |
| Speech/TTS | ✅ Multiple voices | ✅ Qwen-Audio-3.0-TTS-Plus |
| Music | ✅ With-lyrics + instrumental | ❌ Not available |
| Image gen | ✅ Built-in | ❌ Separate (Qwen-Image) |
| Vision QA | ✅ Built-in | ❌ Separate (Qwen-VL) |
| CLI agent integration | ✅ mmx-cli + SKILL | ❌ Raw API only |
| API style | CLI-first (API also available) | REST API (async) |
| Max resolution | Check H3 docs | 1080P |
| Duration | Check H3 docs | 3-15s |

### When to use which

- **MiniMax:** Full pipeline in one platform. Best when you need video + music + voice together. CLI-first workflow. Agent-friendly.
- **Qwen HappyHorse:** When you need precise reference-image control (R2V with 9 images + [Image N] binding). Best for product/brand work with specific visual assets.

---

## Agent Integration

MiniMax publishes an official SKILL for agent integration:

```bash
npx skills add MiniMax-AI/cli -y -g
```

This teaches the agent to call mmx commands accurately. Compatible with: OpenClaw, Claude Code, Hermes Agent, Cursor, TRAE, Codex, and others.

### Hermes Agent Setup

```bash
# Install CLI
npm install -g mmx-cli

# Auth
mmx auth login --api-key $MINIMAX_API_KEY

# Install SKILL (teaches Hermes the commands)
npx skills add MiniMax-AI/cli -y -g
```

After setup, natural language works: "Generate a video: at sunset, a cat sits by the window looking into the distance"
