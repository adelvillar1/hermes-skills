#!/usr/bin/env python3
"""Refresh an expired xAI OAuth access token and print the new pair.

Reads XAI_REFRESH_TOKEN + XAI_CLIENT_ID from the environment (or .env.local).
Writes the fresh access_token + rotated refresh_token to
/tmp/xai-tokens.json so callers can push them to Railway/env files.

Usage:
    export XAI_REFRESH_TOKEN=*** XAI_CLIENT_ID=...   # or rely on .env.local
    python3 xai-token-refresh.py
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


def load_env_local(path: str = ".env.local") -> dict:
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def main() -> None:
    env = {**load_env_local(), **os.environ}
    refresh = env.get("XAI_REFRESH_TOKEN", "")
    client_id = env.get("XAI_CLIENT_ID", "")
    if not refresh or not client_id:
        print("ERROR: XAI_REFRESH_TOKEN and XAI_CLIENT_ID are required", file=__import__("sys").stderr)
        raise SystemExit(1)

    form = urllib.parse.urlencode(
        {"grant_type": "refresh_token", "refresh_token": refresh, "client_id": client_id}
    ).encode()
    req = urllib.request.Request(
        "https://auth.x.ai/oauth2/token",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} {e.read().decode()[:300]}", file=__import__("sys").stderr)
        raise SystemExit(1)

    at = d.get("access_token", "")
    rt = d.get("refresh_token", refresh)  # ROTATED — must persist this one
    if not at:
        print("ERROR: refresh returned no access_token", file=__import__("sys").stderr)
        raise SystemExit(1)

    out = {"access_token": at, "refresh_token": rt}
    with open("/tmp/xai-tokens.json", "w") as f:
        json.dump(out, f)
    print(f"OK access_token={at[:20]}... expires_in={d.get('expires_in')}")
    print(f"   refresh_token ROTATED (new prefix {rt[:10]}...) — persist it")
    print("   new pair saved to /tmp/xai-tokens.json")


if __name__ == "__main__":
    main()
