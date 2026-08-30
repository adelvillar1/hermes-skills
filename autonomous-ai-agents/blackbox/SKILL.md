---
name: blackbox
description: Delegate coding tasks to Blackbox AI via `blackbox --prompt` one-shots. Uses your Blackbox API key. Non-interactive, no TUI needed.
version: 2.1.0
author: Hermes Agent (Nous Research)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Blackbox, Code-Generation]
    related_skills: [claude-code, codex, hermes-agent]
---

# Blackbox — Coding Delegation for Hermes

Delegate coding tasks to [Blackbox AI](https://www.blackbox.ai/) via a single non-interactive command:

```
blackbox --prompt "<task description>" --yolo
```

Blackbox returns code and file changes directly. **No interactive TUI, no PTY, no `/auto` or `/agent` commands** — Hermes invokes it the same way it invokes `git` or `npm`.

## Hermes invocation pattern

```
terminal(command="blackbox --prompt 'Add a login endpoint with JWT auth' --yolo", workdir="/path/to/project")
```

Key flags:
- `--prompt "<task>"` — the coding task, fully self-contained
- `--yolo` — auto-approve all tool calls (required for non-interactive use)
- `--model <id>` — optional override. Useful if the default model is degraded upstream.

## Prerequisites

- Node.js 20+
- `npm install -g @blackboxai/cli`
- API key from [app.blackbox.ai/dashboard](https://app.blackbox.ai/dashboard)
- Run `blackbox configure` once to store the key

## Model selection

Blackbox's default model is configured in `~/.blackboxcli/settings.json`. Verify it's not degraded before delegating heavy work:

```
curl -s -H "Authorization: Bearer <key>" https://api.blackbox.ai/v1/models | jq '.data[].id'
```

If the default model returns 500s, override with `--model`:
- `blackboxai/blackbox-pro` — general-purpose (primary fallback)
- `blackboxai/openai/gpt-5.3-codex` — code generation
- `blackboxai/anthropic/claude-nemotron` — complex reasoning
- `blackboxai/deepseek/deepseek-v4-pro` — budget alternative

## Output expectations

Non-interactive one-shots return text — code blocks, explanations, or file content. They do not autonomously write files or run tests. Hermes should read the returned code and apply it with `write_file`/`patch`, then run tests itself.

## Known pitfalls

1. **`glm-5.2` upstream 500s** — This model occasionally returns LiteLLM proxy errors. Change the default to `blackboxai/blackbox-pro` in settings.json if the default model is down.
2. **`pty=true` is wrong for one-shots** — `blackbox --prompt` returns cleanly without PTY. PTY is only needed for the interactive TUI (which Hermes doesn't use).
3. **No file I/O in one-shot** — Blackbox returns code as text, not written files. Hermes is responsible for applying the result to the filesystem.
4. **Credits cost money** — every `blackbox --prompt` call consumes credits.

## TUI features (not used by Hermes)

Blackbox CLI also has an interactive TUI with `/auto`, `/agent set`, and `/multi-agent` commands for capability-based routing and parallel multi-agent execution. These require a human at the terminal and are outside Hermes' delegation path. See the Blackbox CLI documentation for details.

## Rules

1. Use `blackbox --prompt "<task>" --yolo` — no PTY, no interactive flags
2. Set `workdir` to the target project directory
3. Read and apply the returned code — Blackbox doesn't write files in non-interactive mode
4. Override the model with `--model` if the default returns 500s
5. Rotate API keys that appear in terminal output — generate a new key at the dashboard and run `blackbox configure`
