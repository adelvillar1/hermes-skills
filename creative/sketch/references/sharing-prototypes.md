# Sharing HTML Prototypes with Stakeholders

When a sketch is meant for stakeholder review (especially on mobile), a local `file://` or `localhost` URL is useless. Use a temporary public tunnel instead of uploading to a server.

## Cloudflare Tunnel (fastest — no account needed)

```bash
# 1. Serve the sketches directory locally
python3 -m http.server 8123 --directory sketches/

# 2. In another terminal, create a public tunnel
cloudflared tunnel --url http://127.0.0.1:8123
```

Output will show `https://something.trycloudflare.com`. Text that URL to the stakeholder. Tunnels stay alive as long as the command runs.

**Prerequisites:** `cloudflared` installed (`brew install cloudflare/cloudflare/cloudflared` on macOS).

## ngrok (alternative)

```bash
ngrok http 8123
```

Requires free ngrok account + authtoken.

## Cleanup

Kill the tunnel process when done. These are throwaway URLs — no need to preserve them.

## Pitfall: responsive prototyping

When building alternate mobile layouts for a page that already has a desktop table:
- **Never** hide desktop elements with `hidden md:block` unless the mobile layout is purely additive.
- Use breakpoint-only visibility classes (`md:hidden`, `hidden md:table-cell`) so each viewport gets exactly one layout.
- Keep desktop CSS intact — this is additive responsive behavior, not replacement.
- Test on actual devices: the tunnel URL loads on any phone browser.
