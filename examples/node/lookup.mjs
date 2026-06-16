#!/usr/bin/env node
// Minimal, zero-dependency reference client for the Numbers Online MCP server.
// Speaks the Streamable HTTP transport (JSON-RPC 2.0) with plain fetch — no SDK.
//
// Usage:
//   node lookup.mjs                       # tools/list only (no auth needed)
//   NUMBERS_ONLINE_KEY=... node lookup.mjs +14155552671   # phone_lookup (needs an mcp-scoped key)
//
// All outputs are supplementary, low-confidence signals; your agent keeps every
// routing and dialing decision.

const ENDPOINT = process.env.NUMBERS_ONLINE_MCP_URL || 'https://numbers.online/api/v1/mcp'
const KEY = process.env.NUMBERS_ONLINE_KEY || ''
const number = process.argv[2] || null

let nextId = 1

async function rpc(method, params) {
  const headers = {
    'content-type': 'application/json',
    accept: 'application/json, text/event-stream',
  }
  if (KEY) headers.authorization = `Bearer ${KEY}`
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id: nextId++, method, params }),
  })
  const text = await res.text()
  // The transport may answer as a single JSON object or an SSE `data:` frame.
  const json = text.startsWith('data:') ? text.replace(/^data:\s*/, '').trim() : text
  return JSON.parse(json)
}

const tools = await rpc('tools/list', {})
console.log('tools:', (tools.result?.tools ?? []).map((t) => t.name).join(', '))

if (number) {
  if (!KEY) {
    console.error('Set NUMBERS_ONLINE_KEY (an mcp-scoped key) to call phone_lookup.')
    process.exit(1)
  }
  const out = await rpc('tools/call', { name: 'phone_lookup', arguments: { number } })
  console.log(JSON.stringify(out.result?.structuredContent ?? out, null, 2))
}
