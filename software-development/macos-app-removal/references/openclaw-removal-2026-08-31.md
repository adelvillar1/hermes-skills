# OpenClaw removal (2026-08-31) — worked example

OpenClaw (bundle id `ai.openclaw.mac`) — AI agent app with a node gateway.

## Footprint found

- App bundles: `/Applications/OpenClaw.app`, `~/Downloads/OpenClaw.app` (2.6 GB each), installer zip in Downloads.
- LaunchAgent `~/Library/LaunchAgents/ai.openclaw.gateway.plist` — `RunAtLoad`+`KeepAlive`, ran `/opt/homebrew/opt/node@24/bin/node /opt/homebrew/lib/node_modules/openclaw/dist/index.js gateway --port 18789`.
- npm global package under Homebrew's node@24 prefix (`/opt/homebrew/lib/node_modules/openclaw`, bin `/opt/homebrew/bin/openclaw`) — invisible to the `/usr/local` npm; `npm uninstall -g openclaw` printed `up to date in 2s` and removed nothing. Fixed by manual rm.
- Data: `~/.openclaw`, `~/.kimi_openclaw` (credentials/identity/memory/cron/workspaces) — backed up to tarball first.
- Residue: `~/Library/{Application Support/OpenClaw, Logs/openclaw, Caches/ai.openclaw.mac, WebKit/ai.openclaw.mac, HTTPStorages/ai.openclaw.mac, Preferences/ai.openclaw.mac.plist, Preferences/ai.openclaw.shared.plist}`.
- Unrelated lookalikes left alone: empty `openclaw.json`/`openclaw-shim` inside `kimi-desktop/daimon-share` (Kimi Desktop's own files); Homebrew node@24.

## Respawn loop diagnosis (the hard part)

1. Killed main app PID → respawned within seconds, new PID, same AppTranslocation path.
2. Removed LaunchAgent plist → `launchctl bootout` failed with `Input/output error`; `launchctl remove ai.openclaw.gateway` worked. App STILL respawned.
3. `ps -o ppid` showed ppid=1; `launchctl print gui/$(id -u)/application.ai.openclaw.mac...` showed `path = (submitted by runningboardd.416)` — looked like launchd/RunningBoard was relaunching. Red herring.
4. Actual cause: `pgrep -fl -i openclaw` revealed TWO surviving children of the main app — `openclaw` (its CLI/gateway child) and `openclaw-node`. They watchdog-relaunched the parent every time only the parent was killed.
5. Fix: `kill -9 <main> <child1> <child2>` in one command → stayed dead. Verified with `sleep 10; pgrep` + port 18789 check.
6. After the final kill, the app had RECREATED `Application Support/OpenClaw`, `WebKit/ai.openclaw.mac`, `HTTPStorages/ai.openclaw.mac` during its last minute — required a second residue sweep.

## Approval-gate note

the harness command guard held `rm -rf` of user data dirs for interactive approval twice; timed out when the user was away. Batch destructive commands and expect to pause for the user between phases.
