---
name: decode-whiteboard
description: "Build visual prototypes on the Decode MCP whiteboard."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [design, prototype, mcp, decode, whiteboard, visual]
    related_skills: [ui-redesign-planning, anti-ai-slop, impeccable, draft-feature-plan, claude-design, native-mcp]
---

# Decode Whiteboard Prototyping

Decode is a collaborative whiteboard for coding agents (local MCP server, default `http://localhost:9876/mcp`). Use it when the user asks for a visual representation, mockup, or prototype — deliver a runnable HTML "sketch" shape on the board, not a static image.

## When to Use

- User asks for a "visual representation" / mockup / prototype of a design direction
- A Decode board is open and the user references "the board", shapes, or sketches
- You need to hand a visual artifact to the user for approval before implementation

Pair with `ui-redesign-planning` (direction lock → tokens) and `anti-ai-slop` (gate the prototype), then `draft-feature-plan` (prototype becomes the binding contract).

## Tool Access — Two Paths

1. **Native MCP tools** — if Decode tools are already loaded in the session, call them directly.
2. **Raw JSON-RPC fallback** — if the server is configured but tools aren't surfaced, talk to it directly. Use `scripts/decode_mcp_client.py` (in this skill) or inline equivalent:
   - `POST /mcp` with `initialize` → capture `mcp-session-id` header → send `notifications/initialized` → then `tools/call`.
   - Responses are SSE: parse lines starting with `data: `.
   - Key tools: `create_shapes`, `set_sketch_file_from_path`, `edit_sketch_file`, `get_shapes`, `screenshot`, `get_instructions` (topics: overview, sketches, shapes, feedback, diagrams, media).

## Sketch Lifecycle (the core workflow)

A sketch is a sandboxed HTML/React app embedded on the board — build it as a real HTML file first, then load it:

1. **Write the prototype locally** (`/tmp/<name>.html`): self-contained, fonts via CDN or inline, tab-switcher for multi-screen previews, all design tokens inline in `:root`.
2. **Verify it yourself first**: open via `file://` in browser tools, click through every tab, run `browser_vision` per screen against the anti-slop checklist. Fix before it touches the board.
3. **Create the shape**: `create_shapes` with `{"shapes":[{"type":"sketch","x":100,"y":100,"agentWorking":true}]}` → returns `createdIds`.
4. **Load the file**: `set_sketch_file_from_path` with the shape id + `filePath` + `path:"/index.html"` + `agentWorking:false` on the final apply.
5. **Iterate**: edit the local HTML, re-run `set_sketch_file_from_path` (full replace each time is simplest).
6. **Archive**: copy the final HTML into the repo (e.g. `docs/design/prototype.html`) — the board is ephemeral, the repo file is the contract.

## Pitfalls

- **`screenshot` often fails on sketches** with `GUEST_VIEW_MANAGER_CALL: UnknownVizError` (view not ready/renderable). Don't retry-loop: verify visuals via `file://` + `browser_vision` instead and deliver those screenshots to the user.
- **The server can die mid-session** (port 9876 stops listening). The local HTML file is the source of truth — nothing is lost; re-sync with one `set_sketch_file_from_path` call if the server returns.
- **Text shapes need a `props` object** — passing `{type:"text", text:"..."}` flat fails schema validation. Skip decorative labels; put instructions inside the prototype UI itself (e.g., a labeled tab bar).
- **`update_shapes` requires `type` on every shape**, not just `id`.
- **Session ids expire**: the JSON-RPC session is per-connection in the fallback client; re-initialize per tool call (the provided script does this).
- **Don't put secrets or user data in prototypes** — boards are shared surfaces. Use obviously fake sample data.

## Handoff: Prototype → Binding Contract

Once the user approves the visual:
1. Archive the HTML in-repo (`docs/design/prototype.html`).
2. In the implementation plan, name the archived prototype as the **binding visual contract** and require every implementer subagent to read it first ("extract layout/tokens verbatim, do not re-derive").
3. Add grep gates in the plan's verification that encode the design rules (zero gradients/emoji/hardcoded hex, tokens-only).

## Verification Checklist

- [ ] Prototype renders locally via `file://` with all tabs/screens working
- [ ] `browser_vision` pass per screen against anti-slop checklist
- [ ] Sketch shape created + file loaded (`get_shapes` shows `entry: /index.html`, `fileCount: 1`)
- [ ] HTML archived in repo
- [ ] Plan references the archived path as binding contract
