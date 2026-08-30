---
name: product-walkthrough-videos
description: "Use when making walkthrough videos with TTS voiceover."
version: "1.0.0"
tags: [video-production, tts, ffmpeg, screen-recording, saas, walkthrough]
---

# Product Walkthrough Videos

Produce short (~12-18s) feature walkthrough videos for SaaS products by combining screen-recorded product footage with natural-sounding TTS voiceover. This is the standard approach for landing pages, feature announcements, and onboarding flows where showing the *actual* UI matters more than cinematic flair.

**This skill covers screen recording + TTS + ffmpeg assembly.** For AI-generated video (T2V prompts, HappyHorse, etc.), see `ai-video-direction` instead. Use this skill when the user wants to show the *real product*, not a generated interpretation.

---

## 1. When to use this vs AI-generated video

| Approach | Use when | Don't use when |
|----------|----------|----------------|
| **Screen recording + TTS** (this skill) | Showing real product UI, feature walkthroughs, landing page demos | You need cinematic B-roll, fantasy scenes, or no product exists yet |
| **AI-generated video** (`ai-video-direction`) | Concept videos, social ads, mood pieces, no product to film | You need to show the actual UI accurately |

**Rule:** If the user says "walkthrough," "feature demo," "how it works," or "show the product" — use this skill. If they say "cinematic," "concept," "trailer," or "AI video" — use `ai-video-direction`.

---

## 2. Voice selection

For SaaS walkthroughs, the voice must sound natural, professional, and upbeat — not robotic.

| Provider | Voice | Profile | When to use |
|----------|-------|---------|-------------|
| **OpenAI** `gpt-4o-mini-tts` | **Nova** | Female, warm, friendly, upbeat, professional | Default for female walkthrough voice |
| **OpenAI** `gpt-4o-mini-tts` | **Shimmer** | Female, warmer, more elegant/soothing | When you want less upbeat, more sophisticated |
| **xAI** | **eve** | Female, natural | Fallback if OpenAI unavailable |
| **Qwen** | Ethan | Male | Default for male voice (Qwen's default is male) |

**Generate via Hermes `text_to_speech` tool** with `provider: "openai"`. The tool returns an `.mp3` file.

**Always generate a test clip first** before producing all videos. Voice preference is subjective — let the user hear a sample before committing to 10+ generations.

---

## 3. Script writing

Each video needs a tight voiceover script. Formula:

```
[Hook: 1 sentence — what this solves]
[Proof: 1-2 sentences — what the viewer sees on screen]
[Payoff: 1 sentence — why it matters to the user]
```

**Target: 25-35 words = ~10-14s of natural-paced speech.**

**Sources for scripts:**
- Matching blog posts (pull key selling points, not full text)
- Feature page copy
- Landing page feature descriptions

**Rules:**
- Lead with the benefit, not the feature name
- Use "you" and "your client" — speak to the viewer
- One idea per sentence — no compound clauses
- Read aloud at natural pace to time it. If >14s, cut words.

---

## 4. The audio-before-video constraint (CRITICAL)

**The voiceover must end 1-2 seconds before the video ends.** If the audio runs to the final frame, encoders can clip the last syllable — the video feels abruptly cut.

**How to enforce it:**

1. **Measure TTS duration first** (`ffprobe` on the generated `.mp3`).
2. **Set video duration = audio duration + 2.0s** (minimum 1.0s gap, 2.0s is safer).
3. **Audio fades out over the last 0.5s** (`afade=t=out:st=<audio_dur-0.5>:d=0.5`).
4. **Video fades out over the last 0.5s** (`fade=t=out:st=<vid_dur-0.5>:d=0.5:alpha=1`).
5. **Verify after assembly:** `ffprobe` audio duration < video duration by ≥1.0s.

**The apad trap:** Do NOT use `apad` on the audio filter — it stretches silence to fill the entire video duration, making the audio track as long as the video. Use `asetpts=PTS-STARTPTS` + `afade` out instead.

---

## 5. Screen recording guidelines

**Tool:** macOS `Cmd+Shift+5` (built-in) or OBS (free, more control).

**Settings:**
- Resolution: 1920×1080 (or 1440×900, scaled up in post)
- Frame rate: 30fps
- Show the actual product — staging environment or local dev
- No sensitive data (use sanitized/sample data)
- Record 2-3s longer than the audio duration to allow for trimming

**What to record:**
- A specific workflow (not just navigation)
- The "aha moment" — where the feature delivers value
- Before/after states when relevant

---

## 6. Ken Burns from static images

When screen recording isn't possible (no access, feature not built yet, or you only have a screenshot), create a slow zoom/pan video from a static image.

**ffmpeg zoompan expression:**
```
zoompan=z='1+0.000159*in':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30:d=<total_frames>
```

**Important:** Use `in` (the input frame number), NOT `n`. Using `n` causes `Undefined constant or missing '(' in 'n'` error in ffmpeg.

**Full pipeline for image + audio → video:**
```bash
ffmpeg -y -loop 1 -t <total_dur> -i <image> -i <audio.mp3> -filter_complex "
  [0:v]scale=1920:1200,crop=1920:1080:0:60,zoompan=z='1+<zoom_per_frame>*in':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30:d=<total_frames>,setpts=PTS-STARTPTS,fade=t=out:st=<total_dur-0.5>:d=0.5:alpha=1[vout];
  [1:a]asetpts=PTS-STARTPTS,afade=t=out:st=<audio_dur-0.5>:d=0.5[aout]
" -map "[vout]" -map "[aout]" -c:v libx264 -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -t <total_dur> <output.mp4>
```

Where:
- `total_dur = audio_dur + 2.0`
- `total_frames = int(total_dur * 30)`
- `zoom_per_frame = 0.075 / total_frames` (7% total zoom over the duration)

---

## 7. Assembly pipeline

### Per-video structure

| Segment | Duration | Content |
|---------|----------|---------|
| Screen recording / Ken Burns | 10-14s | Feature in action |
| Tail silence | 1.5-2.0s | Visual hold, audio faded out |
| **Total** | **12-18s** | |

Voiceover occupies the first 10-14s only. The tail is visual-only with a gentle fade-out.

### Output specs

- Format: MP4
- Resolution: 1920×1080
- Frame rate: 30fps
- Video codec: h.264 (`libx264`)
- Pixel format: yuv420p
- Audio codec: AAC, 128kbps
- Max file size: ~5MB (typically <1MB for short Ken Burns clips)

### Verification commands

```bash
# Video duration
ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4

# Audio duration
ffprobe -v error -show_entries stream=duration -of csv=p=0 -select_streams a:0 video.mp4

# File size
ls -la video.mp4
```

**Pass condition:** `video_duration - audio_duration >= 1.0` AND `file_size <= 5MB`.

---

## 8. Workflow summary

1. **Identify features** — list the features to cover (from landing page, blog posts, or user direction).
2. **Fetch source material** — pull key selling points from matching blog posts or feature pages.
3. **Write scripts** — 25-35 words each, hook/proof/payoff formula.
4. **Generate TTS** — OpenAI Nova (or user-approved alternative). Measure each clip with `ffprobe`.
5. **Create visuals** — screen recording OR Ken Burns from static image.
6. **Assemble** — ffmpeg: visual + audio + fade-out. Video duration = audio duration + 2.0s.
7. **Verify** — ffprobe confirms audio < video by ≥1.0s. Spot-listen for quality.
8. **Deliver** — MP4 files, ready for web embedding.

---

## Pitfalls

| Pitfall | Cause | Fix |
|---------|-------|-----|
| Audio clips at video end | `apad` filter stretches audio to fill video | Remove `apad`, use `afade` out instead |
| `Undefined constant or missing '(' in 'n'` | Used `n` instead of `in` in zoompan | Change `n` to `in` |
| Voice sounds robotic | Wrong TTS voice or provider | Use OpenAI Nova or Shimmer; avoid basic TTS |
| Video feels too short | Audio is long but video was trimmed to match | Always set video = audio + 2.0s, not the reverse |
| Music muddies voiceover | Music volume too high or competing frequencies | Default to no music. If music, keep at ~8% volume and duck under voice. |
| Script runs long | Too many words for the time budget | Cut to 25-35 words max. Read aloud to time it. |

---

## See also

- `ai-video-direction` — for AI-generated video (T2V prompts, HappyHorse, etc.)
- `split-screen-video` — for ffmpeg split-screen compositions
