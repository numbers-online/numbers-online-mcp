# Numbers Online — phone-intelligence MCP server

A hosted, read-only **Model Context Protocol** server that gives an AI voice agent
phone intelligence in a single call: *who is this inbound caller, and is this outbound
number one to think twice about dialing* — **before** it burns agent minutes.

- **Endpoint:** `POST https://numbers.online/api/v1/mcp` (Streamable HTTP, JSON-RPC 2.0)
- **Transport:** remote / hosted — **nothing to install or run.** Point your agent at the URL.
- **Auth:** `Authorization: Bearer <api_key>` for tool calls; discovery is public.
- **Docs:** https://numbers.online/docs/integrations · **Site:** https://numbers.online

> **Positioning.** Every output is an **advisory, low-confidence supplementary signal.**
> The calling agent keeps every routing and dialing decision and remains responsible for
> compliance. Nothing here asserts that a call is lawful, unlawful, "safe", or "spam".

---

## Tools

Five **read-only** tools (all annotated `readOnlyHint`, `idempotentHint`). Discover them
live with `tools/list` (no auth required).

| Tool | Returns | Billed |
|---|---|---|
| `phone_lookup` | Full bundle — validity, formatting, line type, range carrier, country, caller name (CNAM where available), STIR/SHAKEN verstat, a labeled spam signal, DNC + reassigned status, signed receipt | bundled per-call |
| `caller_risk` | Spam signal + verstat + DNC + reassigned status + receipt (no name dip) | bundled per-call |
| `line_type` | Deterministic only — validity, line type (mobile / fixed line / VoIP / …), carrier, country, formatting | free |
| `dnc_check` | First-party do-not-contact signal + signed receipt | free |
| `reassigned_check` | First-party reassigned-number signal + signed receipt | free |

### About the DNC / reassigned signal

`dnc_status` and `reassigned_status` are **first-party, consent-first** signals: they
reflect a do-not-contact preference **registered and verified by the number's own owner**
inside Numbers Online. They are **not** a copy, mirror, or replica of any government or
official do-not-call registry. A number returns a status once its owner has registered
one; otherwise the honest answer is **`unknown`** — no record on file for that number.
Treat it as a supplementary input to your own TCPA process, never a verdict that a call
is lawful.

---

## Connect

### Any MCP client (Claude Desktop, Claude Code, IDEs)

Add a **remote** server pointing at the endpoint. Example `mcp.json` fragment:

```json
{
  "mcpServers": {
    "numbers-online": {
      "type": "streamable-http",
      "url": "https://numbers.online/api/v1/mcp",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

A key needs the `mcp` use case. `initialize`, `ping`, and `tools/list` work without auth
(capability discovery); `tools/call` is fail-closed and requires the key.

### Vapi

Register Numbers Online as an MCP tool — the transport literal is **`shttp`**
(see [`integrations/mcp/vapi-mcp-tool.json`](integrations/mcp/vapi-mcp-tool.json)).
A Vapi custom-function-tool alternative lives at
[`integrations/vapi/numbers-online-tool.json`](integrations/vapi/numbers-online-tool.json).

### Retell

Point your agent's `call_inbound` webhook at the drop-in config in
[`integrations/retell/inbound-webhook.json`](integrations/retell/inbound-webhook.json).
It always returns HTTP 200 within Retell's budget (fail-open) so a slow lookup never
keeps the caller ringing.

Full walkthrough: [`docs/ai-voice-agents.md`](docs/ai-voice-agents.md).

---

## Quick smoke test

```bash
# discover tools (no auth)
curl -s https://numbers.online/api/v1/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# call a tool (needs an mcp-scoped key)
curl -s https://numbers.online/api/v1/mcp \
  -H "Authorization: Bearer $KEY" -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"phone_lookup","arguments":{"number":"+14155552671"}}}'
```

Runnable reference clients (zero-dependency) are in [`examples/`](examples/) —
[Node](examples/node/lookup.mjs) and [Python](examples/python/lookup.py).

---

## Signed receipts (verifiable "checked as of T" evidence)

Every billable answer can carry a `receipt_id` and an Ed25519 `response_signature`.
Fetch the receipt later — no API key required, the id is the capability:

```
GET https://numbers.online/api/v1/receipts/{id}
```

**No raw phone number is stored** — only `number_hash = sha256(E.164)`. Verify with the
public key at `GET https://numbers.online/api/v1/publickey`. A receipt is verifiable
evidence that a status was *checked at a point in time* — not proof that dialing was
lawful. Treat a receipt id as sensitive (a phone number is a small keyspace, so the hash
is bindable to a candidate number).

---

## Privacy

Raw phone numbers are never logged or stored; they are hashed (`sha256`). The MCP path is
read-only and stateless. Privacy policy: https://numbers.online/privacy

## Pricing

The full bundle is metered as one bundled per-call dip (validation + line type + risk +
DNC + reassigned in a single call). `line_type`, `dnc_check`, and `reassigned_check` are
free. See https://numbers.online for current rates.

---

**Developer:** Evergrow · **Product:** Numbers Online · **Contact:** contact@numbers.online
· **License:** [MIT](LICENSE)
