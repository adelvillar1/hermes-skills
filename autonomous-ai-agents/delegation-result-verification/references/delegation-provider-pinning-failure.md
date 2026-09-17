# Delegation Provider Mispinning — Instant-Death Batch (case study, 2026-07-21)

## Incident

During the MCP-2099 build, a 3-task parallel `delegate_task` batch (`deleg_139c54e1`)
returned "dispatched" normally, but all three live transcripts showed death within one
second:

```
13:14:04 user     | kickoff: Build the cinematic WebGL Loader...
13:14:04 start    | Build the cinematic WebGL Loader...
13:14:04 final    | status=completed duration=0.27s summary: Messages.stream() got an
                   unexpected keyword argument 'output_config'
13:14:04 final    | end status=completed exit_reason=max_iterations (iteration budget exhausted)
```

All three tasks: identical error, `duration=0.27s`, zero tool calls executed.

## Why the signals mislead

- `exit_reason=max_iterations` suggests the agent looped itself out — it didn't; the very
  first LLM API call raised before any iteration completed.
- `status=completed` suggests success — it's just the wrapper's "process exited."
- The error text (`Messages.stream() ... 'output_config'`) looks like a Hermes internal
  bug, but it's the symptom of the pinned provider's API surface being incompatible with
  what the delegation client sends.

## Root cause found

`hermes config get delegation` showed:

```
model: kimi-k2.6
provider: kimi-coding
```

while the main session ran fine on `alibaba-coding-plan` / `qwen3.8-max-preview`.
Subagents pin provider/model from `delegation.*` config at dispatch time — they do NOT
inherit the parent session's live provider.

## Fix applied

```bash
hermes config set delegation.provider alibaba-coding-plan
hermes config set delegation.model qwen3.8-max-preview
```

Re-dispatched the identical batch (`deleg_a3dd4719`) with zero prompt changes. Verified
aliveness 45s later: each transcript showed ~30 real operations (read_file, search_files)
and climbing.

## Discriminator table

| Transcript signature | Diagnosis | Action |
|---|---|---|
| All tasks die <1s, identical API error | Provider mispinning (config) | `hermes config set delegation.*`, re-dispatch unchanged |
| One task dies, real duration, real error | Task/prompt problem | Fix prompt or scope, re-dispatch that task only |
| Tasks alive but slow | Normal | Keep monitoring; 600s timeout is a wall, not a verdict |

## Note on skill placement

This case study was originally drafted for `subagent-driven-development` (the skill that
was governing the session), but that skill is manually authored (created_by=None) and
refuses autonomous patches. It lives here under `delegation-result-verification` instead,
which is the editable umbrella for delegation failure modes. If `subagent-driven-development`
ever becomes editable, fold SKILL.md Pitfall 4's diagnosis/fix into its timeout-recovery
section and keep this file as the case study.
