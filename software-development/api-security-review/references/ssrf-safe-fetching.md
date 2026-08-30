# SSRF-Safe External URL Fetching (DNS-Rebinding Proof)

Full construction pattern for a server-side fetcher that takes user-supplied URLs.
Distilled from `lib/fetchSite.ts` in design-canvas (2026-08-07) — a reference-site
feature that fetches an arbitrary site URL and extracts its "design DNA".

## The core failure mode

The naive "safe" fetcher:

```
1. resolve(url.hostname) → [ip]
2. if isPrivate(ip) → reject
3. fetch(url)                    // ❌ re-resolves hostname internally!
```

Step 3 issues a SECOND DNS lookup. An attacker controls DNS for their own domain
and can answer the step-1 lookup with a public IP (validator passes) and the
step-3 lookup with 127.0.0.1 / 169.254.169.254 / a private host. Classic
DNS-rebinding TOCTOU. The validator and the connection MUST share one resolution.

## The fix: pin the connection to the validated IP

Resolve once, validate, then connect directly to the validated IP while keeping
the original hostname for the Host header and TLS SNI:

```ts
import http from "node:http";
import https from "node:https";

function requestPinned(u: URL, ip: string, timeoutMs: number, maxBytes: number) {
  return new Promise((resolve, reject) => {
    const lib = u.protocol === "https:" ? https : http;
    const req = lib.request({
      host: ip,                          // connect to the VALIDATED ip
      port: u.port || (u.protocol === "https:" ? 443 : 80),
      path: u.pathname + u.search,
      method: "GET",
      headers: {
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml",
        Host: u.host,                    // original hostname (vhost routing)
        Connection: "close",
      },
      servername: u.hostname,            // https only: SNI + cert validation
      rejectUnauthorized: true,
    });
    req.setTimeout(timeoutMs, () => req.destroy(new Error("timeout")));
    // collect body, enforce maxBytes, resolve on 'end', reject on 'error'
    req.end();
  });
}
```

- `host: ip` — the connect target is the validated address, so no second lookup.
- `headers.Host = u.host` — virtual-host routing still sees the real hostname.
- `servername` — https uses SNI + certificate hostname validation against the
  real hostname (default `rejectUnauthorized: true`). A rebinding MITM to a
  different IP fails cert validation.
- Redirects: manual loop (max ~4). Each hop: `new URL(loc, currentUrl)` →
  scheme check → re-resolve + re-validate → requestPinned. Re-validate EVERY hop.

## Node gotchas (each cost debugging time)

### 1. `URL.hostname` keeps brackets on IPv6

```js
new URL("http://[::1]:8080/").hostname === "[::1]"   // brackets INCLUDED
```

Strip brackets before `net.isIP()`, or `net.isIP("[::1]")` returns 0 and the
code falls through to a DNS lookup that fails with a generic error.

### 2. `dns.lookup` does not resolve literal IPs

For literal IP hostnames, `dns.lookup` may throw ENODATA. Short-circuit literals
through `net.isIP()` + the private-range check directly — faster AND produces the
precise "Private IP target" error instead of a misleading "DNS resolution failed".

### 3. WHATWG URL normalizes IPv4-mapped IPv6 to HEX form

```js
new URL("http://[::ffff:127.0.0.1]/").hostname
// → "::ffff:7f00:1"   (NOT "::ffff:127.0.0.1")
```

An `isPrivateIp` branch that handles `::ffff:` by slicing the dotted tail
(`isPrivateIp(tail)`) silently MISSES the hex form. Decode the last two hextets
into the embedded IPv4:

```ts
if (lower.startsWith("::ffff:")) {
  const tail = lower.slice(7);
  if (tail.includes(".")) return isPrivateIp(tail);           // dotted form
  const hextets = tail.split(":");
  const last = hextets.slice(-2).map(h => h.padStart(4, "0")).join("");
  // last = e.g. "7f000001" → 127.0.0.1
  const ipv4 = [0,2,4,6].map(i => parseInt(last.slice(i, i+2), 16)).join(".");
  return isPrivateIp(ipv4);
}
```

### 4. Block hostname strings too

Reject `localhost`, `*.localhost`, `metadata`, `metadata.google.internal`, and
bracketless lowercase trailing-dot hosts (`host.` → `host`) BEFORE resolving.
IP-range checks catch CNAME chains to internal hosts; the string check gives
precise errors and catches localhost-name edge cases early.

## Private-range checklist (isPrivateIp must cover ALL of these)

| Range | Notes |
|---|---|
| `10.0.0.0/8` | private |
| `127.0.0.0/8` | loopback |
| `169.254.0.0/16` | link-local / cloud metadata |
| `172.16.0.0/12` | private |
| `192.168.0.0/16` | private |
| `0.0.0.0/8` | unspecified |
| `100.64.0.0/10` | CGNAT |
| `224.0.0.0/4` | multicast |
| `::1`, `::` | IPv6 loopback / unspecified |
| `fe80::/10` | link-local |
| `fc00::/7` | ULA |
| `ff00::/8` | multicast |
| `::ffff:<v4>` | IPv4-mapped — decode embedded v4, re-check |

Note: a URL like `http://2130706433/` (integer IPv4) is NOT caught by URL parsing —
Node's resolver treats it as a hostname and typically fails with ENOTFOUND, so it
fails closed (request never connects). Acceptable; don't rely on it.

## Other hard requirements

- Scheme whitelist: http/https only. Reject `file:`, `ftp:`, `javascript:`, and
  URLs with embedded credentials (`user:pass@host`).
- Body size cap (e.g. 2 MB) enforced WHILE streaming, not after.
- Timeout (~12s) that destroys the request.
- Content-type check: accept only `text/html` (allow `; charset=` suffix).

## Verification

Write a unit suite that exercises `isPrivateIp` / `assertPublicUrl` / `fetchSite`
DIRECTLY (no network for negative cases — blocked targets must throw before any
connection). The 55→58-case suite in design-canvas `scripts/ssrf-check.mjs`
caught TWO real bugs during development:

1. IPv6 literals gave "DNS resolution failed" instead of the precise block error
   (gotcha #2 — fixed with the literal-IP short-circuit).
2. Hex-normalized IPv4-mapped loopback `::ffff:7f00:1` slipped through the
   `::ffff:` dotted-tail branch (gotcha #3 — fixed with hextet decoding).

Include in the negative battery: `http://localhost:5435`, `http://127.0.0.1/`,
`http://169.254.169.254/latest/meta-data/`, `http://10.0.0.1/`,
`http://metadata.google.internal/`, `file:///etc/passwd`, IPv6 literals
(`[::1]`, `[fe80::1]`, `[fd00::1]`, `[ff00::1]`, `[::ffff:7f00:1]`), integer
IPv4. Positive battery: a real public site (e.g. `https://example.com`).

Run via Node's native TS type-stripping when tsx isn't installed:
`node scripts/ssrf-check.mjs` importing the `.ts` module directly (Node 24+).
