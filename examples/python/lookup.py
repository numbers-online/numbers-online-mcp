#!/usr/bin/env python3
"""Minimal, stdlib-only reference client for the Numbers Online MCP server.

Speaks the Streamable HTTP transport (JSON-RPC 2.0) with urllib — no SDK, no deps.

Usage:
    python lookup.py                       # tools/list only (no auth needed)
    NUMBERS_ONLINE_KEY=... python lookup.py +14155552671   # phone_lookup (needs an mcp-scoped key)

All outputs are supplementary, low-confidence signals; your agent keeps every
routing and dialing decision.
"""
import json
import os
import sys
import urllib.request

ENDPOINT = os.environ.get("NUMBERS_ONLINE_MCP_URL", "https://numbers.online/api/v1/mcp")
KEY = os.environ.get("NUMBERS_ONLINE_KEY", "")

_next_id = 0


def rpc(method, params):
    global _next_id
    _next_id += 1
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "user-agent": "numbers-online-mcp-example/1.0",
    }
    if KEY:
        headers["authorization"] = "Bearer " + KEY
    body = json.dumps({"jsonrpc": "2.0", "id": _next_id, "method": method, "params": params})
    req = urllib.request.Request(ENDPOINT, data=body.encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        text = resp.read().decode()
    # The transport may answer as a single JSON object or an SSE `data:` frame.
    if text.startswith("data:"):
        text = text[len("data:"):].strip()
    return json.loads(text)


def main():
    number = sys.argv[1] if len(sys.argv) > 1 else None
    tools = rpc("tools/list", {})
    print("tools:", ", ".join(t["name"] for t in tools.get("result", {}).get("tools", [])))

    if number:
        if not KEY:
            sys.exit("Set NUMBERS_ONLINE_KEY (an mcp-scoped key) to call phone_lookup.")
        out = rpc("tools/call", {"name": "phone_lookup", "arguments": {"number": number}})
        result = out.get("result", {})
        print(json.dumps(result.get("structuredContent", out), indent=2))


if __name__ == "__main__":
    main()
