# Multiple machines: Connections, handles, per-source agents

Source: "Connecting Desktop to Many Hermes Instances" docs; Bot Mode's connections section.

## The registry

Everything lives on **Settings → Gateways** (older builds had separate Gateway/Connections pages; legacy
deep links redirect there). Three doors: the settings page itself (Cmd/Ctrl+,), the **plug button** at the
right end of the sidebar profile rail ("Connect another Hermes gateway…"), and the command palette
(Cmd/Ctrl+K → *Gateways*).

| Kind | What it is | Auth |
|---|---|---|
| **Local** | "The Hermes runtime managed by this app." | automatic |
| **Remote gateway** | A Hermes gateway reachable over HTTP(S) — LAN, Tailscale, or the internet | session token or OAuth |
| **SSH** | A Hermes install reached over SSH; the app opens the tunnel and starts the dashboard | SSH key + adopted token |
| **Hermes Cloud** | A hosted instance discovered through your Hermes Cloud account | portal sign-in |

## Rules that bite

- **Every connection needs a unique device name** ("Homelab", "Work laptop") — it shows up in roster
  badges, handles and update results. Uniqueness is case-insensitive (`Homelab` vs `homelab` cannot
  coexist); max 64 characters.
- The **local** entry is app-managed ("This device" pill) and **cannot be removed**. One connection is
  always **Primary** and owns the window backend (boot overlay, install/update machinery); removing the
  primary falls back to local.
- **Test** probes HTTP *and* WebSocket legs, so "Reachable" means chat will actually work. Removing a
  connection tears down its backends/tunnels — the instance itself is untouched.
- **Duplicates are rejected at save time**: one local entry; remote/cloud deduped on normalized URL
  (trimmed, trailing slashes stripped, lowercased, across both kinds); SSH deduped on normalized
  `user@host:port` plus remote profile.
- A remote backend must be a **running `hermes serve`** process (e.g. `http://homelab.lan:9119`) — the app
  attaches to it, it does not start it (SSH connections are the exception: the app starts the dashboard
  over the tunnel on demand). Reverse-proxy path prefixes work.

## The union roster (what Bot Mode renders)

- Every profile on every registered connection is an **agent**; the union roster is what multi-source
  surfaces and Bot Mode render.
- Same name on several sources ⇒ handle disambiguates as **`@name-device`** (`@research-homelab`); a
  profile unique across sources keeps its bare name.
- **Enumeration is eager, sockets are lazy**: agents are listed over REST without dialing every source's
  WebSocket; an unreachable source reports per row instead of breaking the roster; SSH sources stay
  connect-on-demand until first use (no surprise tunnels).
- Opening an agent dials **its own source** — chats, sessions and memory live on the machine that owns
  the profile. Each `(connection, profile)` pair gets its own backend and socket with the same
  idle-reaping as local backends, so background agents keep streaming while you look elsewhere.
- Clicking a Connections Bot does **not** hop your window onto that machine: stay in your chat and
  `@mention` it, seat it in a group chat, or create new agents on it with the **Create on** picker.
- Sidebar session list, cron jobs and messaging status are scoped to the **active profile**, and for a
  remote agent, to **that source's machine** — its sessions, its cron, its channels.
- **Update all instances** (Settings → Gateways, once >1 connection) dispatches `hermes update` across
  connections in parallel: local via the app pipeline, remote/SSH via their own backend, Hermes Cloud
  skipped ("Managed by Hermes Cloud"). One unreachable box never wedges the batch.

## Secrets

- Remote-gateway session tokens are encrypted at rest with Electron `safeStorage` (OS keychain) and stay
  in the main process; the renderer and plugins never see token bytes. OAuth tokens are stored the same
  way, keyed by gateway base URL, refreshed before expiry.
- On Linux without a usable keychain the app raises an explicit opt-in dialog before storing a token in
  plain text.
- The registry file (`connections.json` in the app user-data dir) holds labels, URLs and hosts; secrets
  only ever appear inside encrypted envelopes.

## Plugin SDK surface (for anything authoring over connections)

`host.connections()` (labels, kinds, primary — never token bytes), `host.agents()` (union roster with the
precomputed `@name-device` handle), `host.ensureAgent(connectionId, profile)` (activate an agent's
gateway for subsequent `host.request` calls), `host.warmAgent(connectionId, profile)` (fire-and-forget
pre-warm). All four are **feature-detected**: on an older desktop build they are absent and a plugin must
fall back to the single-source `profiles.list` flow. Bot Mode's multi-source roster is the reference
consumer.

## Troubleshooting

- **"Connection test failed"** — backend not reachable at that URL from this machine: is `hermes serve`
  running, is the port open, is the token current? Re-run **Test** after fixing.
- **An agent shows but won't open** — run **Test** on its connection; the WebSocket leg failing while
  HTTP passes usually means a proxy, firewall, or gateway auth/origin guard blocking `/api/ws`.
- **A remote source missing from the roster** — its backend is down/unreachable; the roster lists it under
  sources with the error. SSH sources show *connect-on-demand* until first use — by design.
- **"Update Hermes Desktop to chat with agents on other connections"** — the desktop app predates the
  multi-connection stack; the app itself needs updating.
- **"Could not save the connection"** — usually a missing/duplicate Name or a malformed Gateway URL /
  SSH host; the error names the exact violation.
