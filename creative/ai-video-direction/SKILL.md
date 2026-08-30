---
name: ai-video-direction
description: "Use when writing or debugging T2V prompts for any model."
version: "1.0.0"
license: "MIT (derived from Emily2040/seedance-2.0, MIT)"
tags: [video-generation, prompt-engineering, directing, t2v]
---

# AI Video Direction

Model-agnostic craft for directing AI video generation. Extracted and generalized from Emily2040/seedance-2.0 (MIT). Works with Qwen Wan, MiniMax Hailuo, Seedance, Runway, Kling, or any diffusion-based T2V model.

**Core principle: Direct the model. Don't decorate the frame.**

---

## 1. The Directing Engine

The difference between "cinematic" and directed is motivation. A director decides what the scene must DO to the audience, then makes every craft choice serve that one decision.

### Step 1 — The Director's Read

Answer five questions before any technique:

1. **Function.** What is this scene for — introduce, deepen, turn, or pay off?
2. **The turn.** Name the single value flip: safe→threatened, hope→despair, stranger→ally. If nothing flips, cut or merge the scene.
3. **POV.** Whose experience are we inside? Where should the audience's body stand?
4. **Power.** Who has it, who wants it, where does it move?
5. **Subtext.** What is true but unsaid? Behavior in that gap IS the performance.

### Step 2 — The Coherence Principle (the one law)

**One intention, and every instrument plays the same note.**

Translate the read into one sentence: "make the audience feel her certainty crack." Then set each instrument to express it:

| Instrument | What it carries |
|---|---|
| Shot size | Distance = intimacy or judgment |
| Angle/height | Power and sympathy (low empowers, high diminishes) |
| Lens feel | Psychological space (long isolates, wide opens/pressures) |
| Camera movement | The audience's impulse (push-in leans toward realization) |
| Lighting | Emotional exposure (ratio, direction, color temperature) |
| Blocking | Relationship in space |
| Performance | One legible physical action that plays the subtext |
| Sound | Density, silence, one motivated cue |
| Cut/duration | Breath and pressure |

Every choice must be answerable with "because the intention is X."

### Step 3 — Scene-Type Setups

| Scene function | Coherent setup | Slop to refuse |
|---|---|---|
| Intimate dialogue | MCU-CU, eye-level, long lens, minimal motion, soft key, sparse sound | Roaming camera breaking intimacy |
| Confrontation | Opposed angles, height=power, lens isolates, light splits warm/cool | Symmetrical neutrality erasing the gap |
| Reveal | Withhold then disclose; camera discovers with subject | Showing everything at once |
| Decision/turn | Push-in to isolate; world quiets; one gesture commits | Dialogue doing the body's work |
| Arrival | Wide, motivated environmental light, move places subject in space | Pretty empty vista |
| Pursuit/action | Tracking energy, screen-direction discipline, sound thickens | Stacked micro-actions reading as chaos |
| Transformation | Locked camera so change is legible; light tracks the change | Spectacle with no anchor |
| Comedic beat | Locked frame, clean geography, deadpan hold, one absurd action | Busy camera stepping on timing |
| Emotional low | Distance, stillness, cool soft light, negative space, near-silence | Score-driven sentiment |
| Product hero | Controlled move context→detail, motivated hero light, locked identity | "Dynamic product camera" with drifting label |

### Step 4 — Directing Performance

T2V models render observable behavior, not internal states.

- **Emotion → behavior.** Not "grief" but "she folds the letter, presses it flat with both hands, does not look up."
- **Play an action, not a mood.** Objective + obstacle + tactic → one action verb per beat.
- **Subtext through contradiction.** Agreeing while stepping back. Smiling while gripping the cup.
- **One gesture per short clip.** A single specific legible action carries more than a list of feelings.
- **Register consistency.** Restrained realism, heightened theatricality, or stylized deadpan — pick one per scene.

### Step 5 — Lighting as Emotion

- **Ratio.** Low/high-key = safe, open. High/low-key = private, threatened.
- **Key direction.** Frontal protects; side reveals conflict; back/rim isolates; under-light unsettles; top-light judges.
- **Color temperature.** Warm = intimacy/memory/safety. Cool = distance/night/control. Mixed = internal split.
- **Motivation.** Every source needs a believable origin (window, lamp, screen, sun). Unmotivated "beauty light" = slop.
- **Light moves with the turn.** A cloud passes, a lamp switches, a door opens a beam. Light change = feeling change made visible.

### Step 6 — The Director's Voice

Set one voice per project. Deviate only to mark a major turn.

| Voice | Camera | Light | Color | Cut | Performance | Best for |
|---|---|---|---|---|---|---|
| Observational naturalist | Invisible, mostly still | Available, soft | Muted, true | Long holds | Restrained, lived-in | Grounded drama, documentary |
| Composed classicist | Deliberate, measured | Sculpted, clean | Controlled | Patient | Contained, precise | Prestige, premium ad |
| Kinetic visceral | Handheld, tracking, close | Hard, high contrast | Punchy, desaturated | Fast, percussive | Heightened effort | Action, sport, hype |
| Expressive stylist | Designed, bold framing | Dramatic, pushed | Saturated, signature | Musical, rhythmic | Stylized, gestural | Music video, fashion, fantasy |
| Intimate minimalist | Close lenses, small moves | Single soft source | Warm or restrained | Slow, few cuts | Micro, withheld | Personal, emotional, lonely |
| Graphic formalist | Locked, geometric | Hard, shaped | Limited, deliberate | Exact, deadpan | Stylized/deadpan | Design-forward brand, deadpan comedy |

### Step 7 — The Coherence Test (run before finalizing any shot)

1. State the intention in one sentence. If you can't, the read is incomplete.
2. Point check: does each instrument express that intention? Remove contradictions.
3. Behavior check: is performance a visible action, not an emotion word?
4. Motivation check: does light have a source? Does the camera move have a reason?
5. Voice check: does the setup match the project voice?
6. Fragility check: will the complexity hold faces, hands, logos, text? If not, simplify.

### Step 8 — Long-Form Spine (multi-clip stories)

- One voice, every clip. Never re-roll the look.
- Plan the progression: as tension rises, scale tightens, camera grows more active or pointedly stiller, contrast deepens, sound thickens. Resolution loosens.
- Mark the turn with contrast: the one clip that breaks the pattern (widest frame in a tight film, only still shot in a kinetic one).
- Each beat gets its own Step 1-7 pass; the spine biases, doesn't replace.

### Step 9 — Decision Procedure

1. Read the scene (function, turn, POV, power, subtext).
2. Set or inherit the project voice.
3. Derive the unified setup from scene-type + intention + voice.
4. Write performance as one true gesture per beat.
5. Run the coherence test.
6. Place in the long-form spine (arc position, trends, pattern break?).
7. Hand to prompt architecture.

---

## 2. Prompt Architecture

### Director Formula

`Subject + Action + Scene + Camera + Lighting/Style + Audio + Constraints`

Put subject and primary action FIRST — early clauses lock in who the shot is about.

| Slot | Pattern |
|---|---|
| Subject | The anchor the model must track |
| Action | The visible change with endpoint |
| Scene | Only what references don't already show |
| Camera | One primary move with start, speed, endpoint |
| Light/style | Physical source + direction + behavior |
| Audio | Ambient bed, SFX, dialogue, or silence |
| Constraints | What must not change |

### Mode Selection

| Mode | Priority | Common mistake | Repair |
|---|---|---|---|
| Text-to-Video | Build the whole shot in compact layers | Too many events | One visible beat, one endpoint |
| Image-to-Video | Preserve visible identity; add motion | Re-describing the image until drift | "Preserve reference exactly; add only dynamic changes" |
| Video-to-Video | Transfer motion/camera/timing | Copying unauthorized likeness | Restrict transfer role explicitly |
| Reference-to-Video | Assign separate roles per asset | One reference controlling everything | Split roles or prioritize |
| First/Last Frame | Describe only the continuous transition | Treating last frame as vague mood | State it as the final visual target |
| Edit | Preserve source, change one layer | Rewriting whole scene | "Source clip; change only..." |
| Extend | Continue from accepted footage only | Starting from planned ending | Use observed end state |

### Compression Order (cut in this sequence)

1. Duplicate style adjectives
2. Generic quality words
3. Background details visible in references
4. Secondary camera moves
5. Secondary actions
6. Speculative emotional labels

**Keep:** preservation constraints, action timing, reference role maps.

### Output Contract

Every prompt delivery includes: mode, reference role map (if any), final prompt, safety note (if relevant), and anti-slop confirmation.

---

## 3. Anti-Slop System

### Visibility Test

If a camera, microphone, light meter, or stopwatch cannot detect it, rewrite it.

### The Six Slop Classes

| Class | Looks like | Repair |
|---|---|---|
| Empty evaluators | `cinematic, epic, stunning, beautiful` | Convert to the one observable detail that earns it |
| Borrowed image tokens | `8K, masterpiece, trending on ArtStation, Unreal Engine` | Delete; quality is a setting, not prose |
| Tag salad | Comma-separated keyword dumps | Rewrite as shooting-brief prose: one sentence per element |
| Negation slop | `no blur, no artifacts, no extra fingers` | Describe what IS there; negation summons |
| Adjective stacking | `gorgeous, breathtaking, mesmerizing sunset` | Pick the single detail that matters |
| Feel-suffix words | `vibey, 电影感, 雰囲気のある, 감성적인` | Name the physical cause of the feeling |

### Replacement Table

| Weak | Replace with |
|---|---|
| cinematic | shot scale + camera move + lighting + grade |
| epic | physical scale, stakes, crowd size, lens distance |
| beautiful | color, texture, composition, material, light behavior |
| stunning/breathtaking | visible contrast, reveal, movement, or detail |
| dynamic | specific movement, speed, and endpoint |
| dramatic | blocking, shadow, silence, or camera pressure |
| ultra-realistic | material behavior, skin texture, lens artifacts, natural motion |
| cool transition | match cut, whip pan, dissolve, hard cut, object wipe |
| magical | particle behavior, glow source, motion path, interaction |
| professional | product lighting setup, clean background, controlled camera |
| masterpiece/award-winning | DELETE |
| 8K/ultra-HD/high quality | DELETE |
| atmosphere of mystery | what is hidden, by what: doorway, shadow, fog |
| insanely/highly detailed | the two details that matter, named |

### Position Cost

Early clauses take a larger share of the conditioning budget. One empty evaluator in the opening clause outranks three in the constraint tail. **Never let a slop word hold an opening position.** Give the opening to the subject and its action.

### Negation Rule

Naming a flaw plants it. Instead of `no blur, no extra fingers`, lock the positive: `hands rest still on the table`, `clean unbroken label`. Use negation only in the constraint slot where the platform expects it.

---

## 4. Model Mechanics (why the rules work)

Eight mechanisms common to diffusion-based T2V models. Use these to derive guidance for novel cases.

### 1. Attention is a budget
Every word competes for finite conditioning influence. Words naming visible things spend on pixels; evaluators spend on nothing. Earlier clauses win more influence. → Word order IS priority ranking. Short dense prompts beat long prose.

### 2. Generation pulls toward the familiar
The model samples near its training distribution. Common combinations (golden hour + warm rim) are cheap and stable; rare combinations wobble. → Name dense visual clusters (film noir, cel animation), not judgments. Style flicker = sampler hopping between clusters; repeat the exact anchor phrase.

### 3. There is no NOT
Text conditioning moves probability toward every concept mentioned. "No blood" still summons blood. → Describe what IS there. Reserve literal negation for platform constraint slots.

### 4. Time is a trajectory prior
The model prefers smooth, momentum-carrying, cause-and-effect motion. A described cause lets it compute consequences; disconnected micro-instructions have no trajectory. → One physical cause with visible consequences beats five stage directions.

### 5. Errors compound
Tiny identity errors accumulate across frames and amplify through chained generations. → Re-anchor with ORIGINAL references, never outputs. Keep fragile anchors locked and clips short. Expect drift after 4-5 chained generations.

### 6. References outrank text where they overlap
A reference image specifies more about appearance than a paragraph. Text re-describing a reference creates conflicting instructions → drift. → Prompt only what references cannot carry: change over time, camera, sound, constraints. Always state what must NOT transfer.

### 7. Detail capacity scales with screen area
A face at 2% of frame gets ~2% of representation. Small regions can't hold fine structure; motion worsens it. → Hero subject earns fidelity by being large. Distant faces, busy hands, small logos degrade first. A detail that matters gets its own shot.

### 8. Audio and video generate together
Sound denoises jointly with picture. Named sound events give synchronization targets. → Name each shot's specific sounds. Dialogue wants a stable face and short line.

### Deriving for Novel Cases

When no rule covers the request: (1) which mechanism dominates? (2) what does it predict? (3) choose the lever that works WITH the mechanism.

### Mechanism-Indexed Diagnosis

| Symptom | Mechanism | Lever |
|---|---|---|
| Generic despite long prompt | 1 — attention diluted | Cut slop, reorder priorities |
| Style/look flickers | 2 — cluster hopping | Repeat exact anchor phrase every shot |
| Excluded thing appears | 3 — negation summoned | Describe positive replacement |
| Action skipped/mushy | 4 — no trajectory | One cause, visible consequences, endpoint |
| Identity decays over time | 5 — compounding error | Shorter clip, original-reference re-anchor |
| Reference fights prompt | 6 — conflicting conditioning | Delete re-description, state non-transfer |
| Small detail breaks | 7 — capacity starvation | Enlarge in frame or give own shot |
| Lips/sound desync | 8 — joint constraint overloaded | Lock face, shorten line, name the sound |

---

## 5. Allocation Model

Every generation has a finite fidelity budget. Decide where it goes BEFORE writing.

### The Three Spends

| Spend | Buys | Strains |
|---|---|---|
| Identity fidelity | Stable faces, products, logos, costumes | Motion range |
| Motion boldness | Committed action, physics, choreography | Close-up identity detail |
| Scene density | Crowds, layered environments, weather | Per-subject stability |

### Method

1. Name the PRIMARY spend — one per generation.
2. Pick one secondary; economize everything else on purpose.
3. Offload fidelity to references (identity carried by a reference image frees text for motion/timing).
4. Pay for primary out of others: bold motion → stage emotion in body, ration close-ups; dense scene → keep hero large and few.
5. Re-anchor across a series: respend on identity (original references) every few clips.

### Trade Table

| If the shot needs | It pays with |
|---|---|
| Bold motion + close-up face | Choose one; put emotion in posture, or cut to separate CU |
| Many subjects | Per-subject precision; pick one hero, rest read as shapes |
| Readable on-screen text | Nothing — move text to post |
| Crowded frame + tiny product detail | The detail; isolate in its own shot |

---

## 6. Camera Contract

State: shot scale, angle, movement, speed, subject relationship, endpoint.

| Need | Strong phrase | Avoid |
|---|---|---|
| Emotional realization | `slow dolly-in from MCU to tight CU as she lowers the envelope` | `dramatic cinematic zoom` |
| Product reveal | `controlled slider from silhouette to front three-quarter hero, ending on label` | `dynamic product camera` |
| Scale | `low-angle crane up from boots to skyline, ending behind shoulder` | `epic wide moving shot` |
| Instability | `subtle handheld, small breathing sway, subject centered` | `shaky chaotic camera everywhere` |
| Precision detail | `locked macro, focus on watch gears while second hand clicks once` | `cool close-up details` |

### Move Selection

- **Locked-off:** lip-sync, product identity, text, logos, delicate VFX
- **Dolly/push-in:** discovery, realization, intimacy, product reveal
- **Lateral track:** travel, procession, choreography
- **Orbit:** product hero, statuesque subjects (avoid if identity stable from one angle only)
- **Crane/drone:** scale, arrival, geography (avoid for dialogue or tiny text)
- **Handheld:** realism/tension (keep subtle when identity matters)
- **Rack focus:** attention shift between two anchored objects

### Ending Profiles

| Profile | Final state | Use when |
|---|---|---|
| Resolve | Action completes, motion settles | Standalone clips, demos |
| Extension anchor | Motion still directionally live | Next clip continues this shot |
| Loop seam | Position/phase/exposure/audio match opening | Social loops, ambient backgrounds |
| Hero hold | Subject stable, legible long enough to read | Products, logos, packshots |
| Edit point | Clean visual/audio boundary | Cut/insert in larger edit |
| Reveal/punch | Peak lands on final frame | Scares, jokes, title handoffs |

---

## 7. Lighting Contract

State: key source, direction, color temperature, atmosphere, shadow behavior, transition.

| Mood/task | Prompt-ready lighting |
|---|---|
| Product luxury | `narrow warm strip light sweeps across brushed metal, black acrylic reflection clean` |
| Night drama | `warm practical lamp frame left, blue moonlight rim on shoulders, soft hallway shadows` |
| Discovery | `door crack opens, thin white beam widens across dust in air` |
| Food realism | `large soft window light from right, gentle bounce on plate, no harsh specular` |
| Storm | `cool overcast daylight, intermittent lightning briefly sharpens silhouette` |

### Source Selection

- **Practical lamps:** interiors, intimacy, visible motivation
- **Window light:** naturalism, food, lifestyle
- **Rim light:** separation
- **Hard light:** noir, harsh sun, graphic shadows
- **Soft light:** beauty, skin, product polish, family
- **Moving light:** visible change in the scene

---

## 8. Motion Contract

State: actor/object, action, force level, timing, physical consequence, endpoint.

| Type | Strong | Weak |
|---|---|---|
| Subtle acting | `she inhales, grips the cup tighter, sets it down without looking away` | `she feels nervous` |
| Product material | `condensation beads gather, merge, slide down the bottle neck` | `the product looks refreshing` |
| Choreography | `he ducks under the swinging bag, pivots left, stops in guarded stance` | `fast action fight scene` |
| Object physics | `paper receipt lifts in fan breeze, flips once, lands face-up` | `papers move dynamically` |
| Environmental | `rain streaks diagonally across backlight while puddle ripples spread from footsteps` | `stormy weather atmosphere` |

### Physics-Forward Pattern

Write causes, let the model compute consequences. State mass, force, material, then name one visible consequence: `the heavy oak door swings shut and the candle flames bend toward it` beats `the door closes dramatically`. One cause with 2-3 consequences reads stronger than three separate actions.

### Timing Pattern

Three-beat structure: setup → action → changed end state. Example: `0-2s: candle steady; 2-4s: door opens, flame bends; 4-6s: smoke curls toward hallway`.

### Stability Rules

Hands, faces, logos, product geometry drift under complex choreography. Lock camera for lip-sync. Keep hands in simple poses. Move light/environment instead of the identity anchor.

---

## 9. Character Contract

Assign each character a stable tag. After >1 character, no ambiguous pronouns.

| Field | Use |
|---|---|
| Tag | `Character A`, `the woman in red`, or reference-subject |
| Identity anchor | Age range, silhouette, hair, wardrobe, or reference image |
| Position | Foreground/background, left/right, seated/standing |
| Action | One assigned verb and endpoint |
| Expression | Observable behavior: blink, glance, smile, grip, pause |
| Constraint | What must stay unchanged |

### Three-Tier Action Hierarchy (multi-person stabilizer)

1. **Persistent micro-motion** — breathing, blinks, shoulder drift. Default for everyone NOT the focus.
2. **One focused response** — a single person gets one small reaction with explicit timing.
3. **Large actions — prohibited by default.** Exclude standing, walking, turning unless it's the shot's single beat.

### Hand/Face Stability

Keep hands visible but simple. Avoid rapid finger actions. Avoid face-touching during dialogue. Lock camera for lip-sync. Use props to show emotion when facial precision is fragile.

---

## 10. Multi-Shot Grammar (cuts inside one generation)

For models that support multiple shots in one generation:

- Label every cut: `Shot 1:` / `Shot 2:` / `Shot 3:` — labels give the model cut points.
- Per shot: one primary action + one camera move + its sound.
- Budget: ~4-6s per shot. Two shots ≈ 10s, three ≈ 12-15s.
- For unbroken takes, say so: "single continuous take, no cuts."

| Symptom | Fix |
|---|---|
| Renders as one continuous take | Clearer shot labels; reduce to two shots |
| Action skipped/compressed | Fewer shots; raise duration; one action per shot |
| Cut lands mid-action | End each shot's sentence on completed beat |
| Atmosphere breaks between shots | Declare persisting effect once for whole piece |

---

## 11. Event Density

**One generation = one visible beat with a changed endpoint.**

### Beat Buckets

- `already_happened`: do not replay
- `this_clip_only`: current prompt may perform
- `reserved_for_later`: do not show yet
- `do_not_show_yet`: excluded even if it explains motivation

### Splitting Triggers

Split when: several completed actions, multiple locations, several dialogue turns, complex physical contact, product proof + hero packshot, or story longer than model duration.

---

## 12. Troubleshooting Diagnostic Tree

Diagnose BEFORE rewriting. Do not add more adjectives.

| Symptom | Likely cause | First repair |
|---|---|---|
| Product/face changes | I2V re-described visible identity | Add preservation constraints; remove static detail |
| Camera jumps | Several incompatible moves or no endpoint | One move with start and finish |
| Generic output | Hollow style words, weak action | Physical action, source light, material, sound |
| Motion ignored | Static prompt, no visible consequence | Actor + verb + timing + changed end state |
| Lip-sync poor | Moving head/camera, long dialogue | Lock framing, shorten line, assign speaker |
| VFX noisy | No source, physics, or dissipation | Source + material + path + interaction + endpoint |
| Prompt blocked | Protected IP, real-person, bypass wording | Rewrite in safe production language |
| Extension degrades | No last-frame anchor, too many variables | Use returned last frame; change one variable |
| Audio reference ignored | Competing video sound, no beat mapping | Mute competing video; map one visible event to beat |
| Text/logos break | Small text asked to move | Keep text static, centered, protected |
| Continuation assumes planned ending | Observed end state ignored | Replace opening with actual observed state |
| Previous action restarts | Completed beat not marked | Add completed beat exclusion |
| Future beat leaks | Reserved beat in current prompt | Remove; stop earlier |
| Identity drifts through extensions | Continuity source displaced canonical reference | Re-anchor from canonical image |
| Screen direction flips | Axis not locked | State screen direction or declare reset |

### Repair Process

1. Quote the failing phrase or missing element.
2. Name the root cause (use mechanism-indexed diagnosis from §4).
3. Remove conflicts rather than adding complexity.
4. One primary repair variable.
5. Produce one conservative retry prompt.

### Conservative Retry Pattern

`[Reference role if any]. Preserve [identity/product/environment] exactly. One visible action: [verb + consequence]. Camera: [single move]. Lighting: [physical source]. Sound: [ambient/SFX]. Constraints: [what must not change].`

---

## 13. Retake Protocol

### Five Verdicts

| Verdict | When | Next move |
|---|---|---|
| **Keep** | Primary spend delivered, nothing fatal | Lock it, log it, move on |
| **Fix in post** | Flaw is color/text/sound/trim | Never burn takes on what an editor fixes |
| **Edit, don't regenerate** | Composition right, one layer wrong | Preserve take; change only failing layer |
| **Re-roll** | Prompt right, sample unlucky | Same prompt, new seed. Max 2-3 re-rolls |
| **Rewrite** | Same flaw in 2+ takes | Systematic. Diagnose by mechanism, change prompt |

### The One-Variable Rule

Change ONE thing per retake: one prompt clause, OR the seed, OR the mode, OR one reference. Change two things and the result is unreadable.

### Attempt Budget

Set before take one: a number (default 5 standard, 10 fast drafts) and a written "good enough." At half budget with no progress on the same flaw → change strategy (different mode, decomposition, or honest exit).

### Cost Awareness

- Draft cheap, lock expensive: explore on fast tier/short duration/low res; spend full quality only on locked design.
- Ten 4-second drafts answer more than one failed 15-second take.

### Shot Log

`Take N · changed: [one variable] · seed: [same/new] · verdict: [keep/post/edit/re-roll/rewrite] · evidence: [one sentence]`

Two takes with the same flaw = rewrite, by rule.

### When the Answer is "Don't Generate"

Dense on-screen text → post. Real product exact behavior → camera. Archival reality → licensing. Failed budget twice after decomposition → different idea. "Film this one for real" is a deliverable, not a failure.

---

## 14. Sequence & Continuation (multi-clip stories)

### Core Law

**Plan globally, generate locally.** The plan owns the whole story. The prompt owns only the current clip. Accepted footage is the source of truth, not the plan.

### Canon Rule

Accepted observed footage OVERRIDES planned state. If the plan says "reached the car door" but the clip ends two steps away, the next prompt begins two steps away. Rejected footage never updates canon.

### Continuation Types

| Type | Use when |
|---|---|
| Seamless continuation | Same shot, same geography, same open motion |
| Intentional next shot | Editorial cut appropriate; story continuity, not frame continuity |
| Bridge between known states | Defined start + end states to connect |
| Repair tail | Previous final seconds failed; fix before continuing |
| Re-anchor after drift | Identity/geography/motion degraded; return to canonical references |

### Chain Depth

Track consecutive output-sourced generations since last canonical re-anchor. Default max: 2, hard ceiling: 3. Re-anchor by schedule, not just when drift is visible.

### Build Process

1. Establish story promise and final outcome.
2. Set one directorial voice + long-form spine.
3. Extract ordered beats; assign status (planned/current/completed/omitted).
4. Group into scenes (one location/time envelope each).
5. Divide scenes into generation-sized clips.
6. Each clip: one narrative job, one felt_intent, one endpoint.
7. Define opening/ending states, continuity locks, allowed changes.
8. Store later clips as provisional intent cards, NOT final prompts.
9. Compile ONLY the first unresolved clip.
10. After generation: require clip/final frame → record observed state → reconcile canon → compile next.

### Required Input for Continuation

Before writing any continuation: project ID, clip ID, parent clip ID, accepted previous clip or final frame, observed end state, continuity locks, directorial voice, reference registry. If source unavailable: ASK for it. Do not invent.

---

## 15. Continuity QC

### Hard-Fail (never silently change)

Canonical identity, wardrobe, product identity/geometry, prop ownership, location, vehicle identity, persistent environment, reference tags, completed beat status, parent clip lineage.

### Warn Unless Declared

Pose, frame position, screen direction, motion vector, camera phase, focus state, lighting phase, emotional state, ambience, music phase, active dialogue.

### Boundary Check (before successor prompt ships)

- Predecessor accepted status ✓
- Successor parent_clip_id ✓
- Predecessor observed_end_state ✓
- Successor planned_start_state matches ✓
- Completed beats excluded ✓
- Future beats excluded ✓
- Reference tags preserved ✓
- Felt_intent present and served ✓
- Current prompt covers only current clip ✓

---

## 16. Quick Reference Checklist

| Gate | Pass condition |
|---|---|
| Mode | T2V/I2V/V2V/R2V/FLF2V/edit/extend is explicit |
| References | Each asset has exactly one primary role |
| Subject | Main subject in first clause with stable tags |
| Action | One visible beat with observable endpoint |
| Camera | One primary move: start, speed, relationship, endpoint |
| Lighting | Source, direction, color, atmosphere — physical |
| Audio | Dialogue/ambience/SFX/music/silence — intentional |
| Safety | Protected identity/IP rewritten or authorization-gated |
| Anti-slop | Hollow boosters replaced with observable language |
| Budget | Fits the active model's prompt budget |
| Sequence lineage | project_id, clip_id, parent when continuing |
| Actual state | Continuations start from observed, not planned |
| Clip scope | Completed beats excluded, future beats out |

### Fast Repair Phrases

| Failure | Add/replace |
|---|---|
| I2V drift | `preserve reference subject exactly; only motion, light, camera change` |
| Generic look | `physical light source + material behavior + specific camera endpoint` |
| Camera chaos | `one controlled [move] from [start] to [end]` |
| Weak action | `actor + verb + timing + consequence + final state` |
| Lip-sync instability | `locked MCU, short quoted line, no head turn during dialogue` |
| Noisy VFX | `source + material + path + interaction + dissipation endpoint` |
| Style/IP risk | `medium + texture + palette + composition + motion rhythm` |
| Planned ending mismatch | `begin from observed final frame: [actual visible state]` |
| Future beat leakage | `this clip stops at [endpoint]; do not show [reserved beat] yet` |

---

## 17. Model-Specific Adapter Notes

When targeting a specific model, verify and adapt:

- **Duration limits** (max seconds per generation)
- **Prompt budget** (character/token limit)
- **Reference syntax** (how to attach images/videos/audio)
- **Supported modes** (which of T2V/I2V/V2V/R2V/FLF2V/edit/extend exist)
- **Multi-shot support** (can it do labeled cuts in one generation?)
- **Audio behavior** (joint generation? separate? reference audio?)
- **Content filter patterns** (known false-positive triggers)
- **API specifics** (endpoints, async task polling, pricing)

### Known Model Profiles (verify live before use)

| Model | Strengths | Watch for |
|---|---|---|
| **HappyHorse 1.1** (Qwen/DashScope) — DEFAULT | Cinematic motion, R2V with up to 9 refs, 1080P, 3-15s | No native audio, no multi-shot; async-only API. **Full adapter: `references/happyhorse-adapter.md`** |
| **Grok Imagine** (xAI) — FALLBACK | Image + Video + Music/audio. 480P max, 8s max. OAuth auth (`~/.grok/auth.json`). TTS via Hermes `tts.xai` (voice: eve) | Lower quality than HappyHorse; use for rapid prototyping or when DashScope unavailable |
| Qwen Wan 2.7 | High-fidelity image gen for storyboards/first-frames | Pair with HappyHorse I2V for full Qwen-native pipeline |
| Qwen 3.5 Omni Plus | Multimodal text+audio output, 1M free tokens | Voice: Ethan; use for narration/voiceover via chat completions API |
| ~~MiniMax Hailuo~~ | ~~Full pipeline~~ | **CANCELLED 2026-08-02** — no active subscription. Adapter archived: `references/minimax-adapter.md` |
| Seedance 2.0 | Multi-shot, reference roles, audio-visual joint | Surface-specific behavior (Dreamina vs Volcengine vs Runway) |
| Runway Gen-4 | Cinematic quality, camera control | Shorter clips; credit-based pricing |
| Kling 2.0 | Motion, longer durations | Chinese-surface prompt conventions may differ |

---

## Attribution

Derived from [Emily2040/seedance-2.0](https://github.com/Emily2040/seedance-2.0) (MIT License, v6.7.0). Author: Iamemily2050 (@iamemily2050). The directing engine, anti-slop system, model mechanics, retake protocol, and sequence architecture are reproduced and generalized here under MIT terms. Platform-specific facts, model IDs, and surface constraints have been removed — verify live for your target model.