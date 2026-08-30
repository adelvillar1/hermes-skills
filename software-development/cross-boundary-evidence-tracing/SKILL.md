---
name: cross-boundary-evidence-tracing
description: "Trace env/creds across process boundaries."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [debugging, environment, process, propagation, boundaries, evidence]
    related_skills: [systematic-debugging, hermes-agent]
---

# Cross-Boundary Evidence Tracing

## When to use

A value that exists at one layer "disappears" at another: a child process
doesn't see an env var its parent has, a subagent reports "upstream didn't give
me X," a credential reaches the app process but not the shell it spawns, a
payload is correct at the API but wrong after a middleware. The value is being
dropped (or transformed) at one specific boundary in the chain. This skill is
Phase 1 "gather evidence at each component boundary" applied to **hops between
processes and layers** rather than to code-level data flow.

Complements `systematic-debugging` (which owns the overall 4-phase method and
code-level tracing). This skill owns the *cross-process / cross-layer* case.

## The Iron Rule: inspect each hop directly, trust no self-report

A child process — or a subagent running inside one — can only see its OWN
environment. If a value was dropped at the boundary INTO it, the child cannot
tell the difference between "never injected" and "injected then stripped on the
way in." So a child's claim "my parent didn't give me X" is a hypothesis about
the parent, not evidence about it. **Inspect the parent's actual state before
accepting the diagnosis.** The child's vantage point is biased by exactly the
boundary that's broken.

Real example (Buzz + Hermes, 2026-07-30): a Buzz-managed Hermes agent reported
"Buzz Desktop isn't injecting BUZZ_AUTH_TAG; the relay returns 403
relay_membership_required." Walking the process chain showed Buzz injected all
three BUZZ_* vars correctly and they were present in the `hermes acp` process.
The real drop was one hop further: Hermes's terminal/code tools scrub child env
(see Pitfall 3), stripping `BUZZ_PRIVATE_KEY` (contains KEY) and `BUZZ_AUTH_TAG`
(contains AUTH) before the agent's shell saw them. The agent's diagnosis was
wrong by exactly one boundary. Verifying the tag directly (Pitfall 2) proved it
was valid all along.

## Technique: read every process's real environment

`ps eww -p <PID>` prints a process's full environment on macOS/Linux. Walk the
parent chain and check the value at EVERY hop; the drop is always at one
specific boundary.

```bash
# Walk the spawn chain from a child up to launchd/init
pid=<child_pid>
while [ "$pid" != "1" ] && [ -n "$pid" ]; do
  ps -o pid=,ppid=,command= -p "$pid"
  pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
done

# Check a var at a given hop
ps eww -p <PID> | tr ' ' '\n' | grep -m1 '^MYVAR='
```

### Pitfall 1 — parse `ps eww` cleanly, not with shell eval

`ps eww` separates env vars with SPACES, and values can be large or contain
JSON/special characters. The tempting `eval "$(ps eww | grep '^VAR=' | sed
's/^/export /')"` word-splits and CORRUPTS values — a JSON array gets mangled
into a "malformed" error that looks like a real bug but is your extraction
artifact. Parse by string index in Python:

```python
import subprocess
blob = subprocess.run(["ps","eww","-p",PID], capture_output=True, text=True).stdout
def extract(blob, key, json_array=False):
    i = blob.find(key + "=")
    if i == -1: return None
    rest = blob[i+len(key)+1:]
    if json_array:                      # value runs to the closing bracket
        return rest[:rest.find("]")+1]
    end = rest.find(" ")                # simple value runs to the next space
    return rest[:end] if end != -1 else rest.rstrip()
```

### Pitfall 2 — verify the credential WORKS before blaming the injector

Before concluding "X isn't giving me the credential," extract it from the
process that HAS it and test it directly with a clean env. If it works, the
injector is innocent and the problem is downstream propagation. A 403/401 the
child saw is usually a *symptom* of the missing value, not proof the value is
bad.

```python
import subprocess, os
clean = dict(os.environ)
clean["BUZZ_PRIVATE_KEY"] = extract(blob, "BUZZ_PRIVATE_KEY")
clean["BUZZ_AUTH_TAG"]    = extract(blob, "BUZZ_AUTH_TAG", json_array=True)
r = subprocess.run(["buzz","channels","list"], env=clean, capture_output=True, text=True)
# Real data back => credential valid; the failure was propagation, not the cred.
```

### Pitfall 3 — frameworks silently sanitize child env (Hermes example)

Many runtimes scrub secrets before handing env to a spawned child. Hermes's
terminal / execute_code tools run child env through `_scrub_child_env`
(`tools/code_execution_tool.py`), which drops ANY variable whose name contains
`KEY / TOKEN / SECRET / PASSWORD / CREDENTIAL / PASSWD / AUTH / DSN / WEBHOOK /
CREDS / BEARER / APIKEY`. So a var present in the `hermes` process is invisible
to anything it spawns.

The escape hatch is `terminal.env_passthrough` in config.yaml (or a skill's
`required_environment_variables`), but it REFUSES vars Hermes classifies as
provider credentials and fails closed (`tools/env_passthrough.py::
_is_hermes_provider_credential`) — so some vars are deliberately
un-allowlistable (GHSA-rhgp-j443-p4rf hardening). Check that function before
promising a config fix.

**When a legitimate tool genuinely needs a scrubbed value in a child:** prefer
a wrapper shim that runs in the parent's env (where the value IS present) and
re-exports just the needed vars before exec'ing the real binary — over patching
the scrubber (wiped on update, fights a deliberate security control). Writing
secrets to a disk file is a last resort and needs the user's explicit go-ahead.

This generalizes: Docker, sudo, systemd, ssh, and CI runners all have their own
env-filtering rules. When a value crosses into one of these and vanishes, read
THAT tool's env-passthrough/allowlist rules before assuming the source never
sent it.

## Diagnostic checklist

1. [ ] Walk the process tree; list every spawn boundary between source and consumer
2. [ ] `ps eww` each hop; locate the EXACT boundary where the value disappears
3. [ ] Parse values cleanly (Python index-slice, not shell eval) to avoid artifacts
4. [ ] Test the credential/value directly with a clean env to confirm it's valid
5. [ ] If the drop is at a tool/framework boundary, read that tool's env-sanitizing code
6. [ ] Never accept a child's "upstream didn't inject it" claim without inspecting upstream
