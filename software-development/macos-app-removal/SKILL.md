---
name: macos-app-removal
description: Use when fully removing a macOS app or agent CLI.
---

# macOS App Removal (kill + uninstall completely)

Removing an app cleanly = kill it **so it stays dead**, remove its service registrations, remove its binaries, then sweep residue. Do discovery first, present the full removal list, back up user data, then delete.

## 1. Discovery (build the full inventory before touching anything)

- `mdfind -name <appname>` — finds app bundles, plists, Library dirs in one shot.
- `pgrep -fl -i <name>` + `ps -o pid,ppid,user,comm -p <pid>` — running processes and parents.
- `launchctl list | grep -i <name>` — loaded launchd jobs (format: `PID Status Label`; `-` PID = not running, Status = last exit code).
- `ls ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons | grep -i <name>`.
- Package managers: `npm ls -g --depth=0`, `ls /opt/homebrew/bin /usr/local/bin | grep <name>`, `brew list | grep <name>`.
- Library residue checklist (bundle id or app name): `~/Library/{Application Support,Caches,Logs,WebKit,HTTPStorages,Preferences,Saved Application State}/`.
- `security find-generic-password -l <name>` for keychain entries.
- `crontab -l`, login items (`osascript -e 'tell application "System Events" to get the name of every login item'`), `sfltool dumpbtm` for BTM-registered background items.

## 2. Kill order — respawn loops

**If an app respawns after kill, kill the ENTIRE process tree in one command.** Agent-style apps spawn helper/CLI children (e.g. `openclaw`, `openclaw-node`) that watchdog-relaunch the parent when only the main PID is killed. `ppid=1` + `launchctl print` saying "submitted by runningboardd" is MISLEADING — the actual relauncher is often the app's own surviving child, not launchd. Fix: `pgrep -fl -i <name>`, then `kill -9 <all pids>` together, then `sleep 10` and re-verify.

- Remove the launchd job FIRST when one exists (`KeepAlive=true` jobs respawn their program).
- `launchctl bootout gui/$(id -u) <label>`; if bootout fails with `Input/output error` (common when the plist was just deleted or the job is in a failed state), use `launchctl remove <label>` instead.
- App Translocation path (`/private/var/folders/.../AppTranslocation/.../d/App.app`) means it was launched from a quarantined location (usually Downloads) — there is an original copy in Downloads to remove too. Trashing the original does NOT kill the translocated running copy.

## 3. Remove binaries

- **npm-prefix trap**: `npm uninstall -g <pkg>` uses whatever npm is first in PATH; the package may live under a DIFFERENT npm prefix (e.g. Homebrew node@24 at `/opt/homebrew/lib/node_modules` vs `/usr/local`). Symptom: npm prints `up to date in 2s` and removes nothing. Verify with `ls <prefix>/bin/<pkg>` after; if still present, remove manually: `rm -rf <prefix>/lib/node_modules/<pkg>` + `rm -f <prefix>/bin/<pkg>`.
- Trash app bundles recoverably: `osascript -e 'tell application "Finder" to delete POSIX file "/Applications/X.app"'` (handles Trash name conflicts natively).
- Leave shared runtimes alone (node, python) — other tools depend on them.

## 4. Data + residue

- **Back up before deleting**: `tar czf ~/<app>-data-backup-$(date +%F).tar.gz -C ~ .<appdata>` — data dirs (credentials, identity, memory, workspaces) are irreplaceable; report the backup path.
- `rm -rf` the residue dirs from the discovery checklist. the harness approval gates may block recursive deletes — if blocked, STOP, report state, and wait for the user; do not retry or rephrase.
- After final kill, re-check residue: a dying app can RECREATE its Library folders in its last minute alive; sweep again.
- Leave other apps' integration files alone (e.g. empty shim/config files inside a different app's Application Support dir belong to that app).

## 5. Final verification sweep

`pgrep -fl -i <name>` (empty), `launchctl list | grep -i <name>` (empty), `lsof -iTCP:<known-port> -sTCP:LISTEN` (empty), binary paths gone, `mdfind -name <name>` shows only intentional leftovers (backups, Trash, other apps' files).

## Session references

- `references/openclaw-removal-2026-08-31.md` — full worked example: ai.openclaw.mac app + gateway LaunchAgent + Homebrew-npm CLI, respawn-loop diagnosis, complete residue list.
