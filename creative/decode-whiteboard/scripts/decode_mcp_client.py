#!/usr/bin/env python3
"""Minimal MCP client for a local Decode server (default http://localhost:9876/mcp).

Use when Decode is configured in Hermes but its tools are NOT surfaced natively.
Re-initializes a fresh session per tool call (session ids expire).

Usage:
    python3 decode_mcp_client.py get_shapes '{}'
    python3 decode_mcp_client.py create_shapes '{"shapes":[{"type":"sketch","x":100,"y":100,"agentWorking":true}]}'
    python3 decode_mcp_client.py set_sketch_file_from_path '{"id":"shape:XXX","filePath":"/tmp/proto.html","path":"/index.html","agentWorking":false}'
    python3 decode_mcp_client.py get_instructions '{"topic":"sketches"}'

Env overrides: DECODE_URL (default http://localhost:9876/mcp)
"""
import json, os, sys, urllib.request, uuid

URL = os.environ.get("DECODE_URL", "http://localhost:9876/mcp")

def _post(payload, session=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["mcp-session-id"] = session
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    session_id = resp.headers.get("mcp-session-id") or session
    return session_id, resp.read().decode()

def _parse_sse(body):
    for line in body.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    try:
        return json.loads(body)
    except Exception:
        return {"raw": body[:2000]}

def call(method, params, session=None, notify=False):
    payload = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if not notify:
        payload["id"] = str(uuid.uuid4())
    session_id, body = _post(payload, session)
    if notify:
        return session_id, None
    return session_id, _parse_sse(body)

def tool(name, args):
    s, _ = call("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "hermes", "version": "1.0"},
    })
    call("notifications/initialized", None, session=s, notify=True)
    _, res = call("tools/call", {"name": name, "arguments": args}, session=s)
    return res

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    res = tool(name, args)
    content = res.get("result", {}).get("content", []) if res else []
    for c in content:
        print(c.get("text", ""))
    if not content and res:
        print(json.dumps(res, indent=2)[:3000])
