# AI voice agents — MCP server, Vapi & Retell

Give an AI voice agent (Vapi, Retell, Pipecat, LiveKit) read-only phone intelligence in
one call: who is this inbound caller, and is this outbound number one to think twice about
dialing — *before* it burns agent minutes.

> **Positioning.** Numbers Online provides *advisory*, low-confidence supplementary
> signals. The agent keeps every routing and dialing decision and remains responsible for
> compliance. The API never asserts that a call is lawful, unlawful, "safe", or "spam".
> DNC and reassigned-number signals are **first-party** inputs to your own TCPA process
> (see below), not a compliance verdict.

There are three ways to integrate; all share one lookup backend and the same billing.

---

## 1. MCP server (recommended for Vapi, Pipecat, LiveKit)

A stateless **Model Context Protocol** server over Streamable HTTP:

```
POST https://numbers.online/api/v1/mcp
Authorization: Bearer <api_key>     # key needs the "mcp" use case
```

It speaks JSON-RPC 2.0 (`initialize` / `notifications/initialized` / `ping` /
`tools/list` / `tools/call`) and exposes five **read-only** tools (all annotated
`readOnlyHint`):

| Tool | Returns | Billed |
|---|---|---|
| `phone_lookup` | full bundle: validity, formatting, line type, range carrier, country, caller name (CNAM where available), verstat, spam signal, DNC + reassigned status, signed receipt | bundled per-call |
| `caller_risk` | spam signal + verstat + DNC + reassigned + receipt (no name dip) | bundled per-call |
| `line_type` | deterministic: validity, line type, carrier, country, formatting | free |
| `dnc_check` | first-party do-not-contact signal + signed receipt | free |
| `reassigned_check` | first-party reassigned-number signal + signed receipt | free |

`tools/call` requires a valid `mcp`-scoped key (fail-closed). `initialize`, `ping`, and
`tools/list` are public capability discovery. Every billable call meters the bundled
`mcp_call` rate and debits **after** delivery (fail-open: a metering hiccup never drops a
live call). A hard latency backstop keeps responses well under Vapi's 7.5s
assistant-request budget, degrading to a neutral "no signal" result rather than stalling.

### The DNC / reassigned signal is first-party

`dnc_status` and `reassigned_status` reflect a do-not-contact preference **registered and
verified by the number's own owner** inside Numbers Online — a consent-first, first-party
signal. They are **not** a copy, mirror, or replica of any government or official
do-not-call registry. A number returns a status once its owner has registered one;
otherwise the value is **`unknown`** (no record on file for that number). It is a
supplementary input to your own TCPA process, never a verdict that a call is lawful.

### Register in Vapi

Add an **MCP tool** to your assistant (see `integrations/mcp/vapi-mcp-tool.json`). The
transport literal is **`shttp`**, not `streamable-http`:

```json
{
  "type": "mcp",
  "function": { "name": "mcpTools" },
  "server": {
    "url": "https://numbers.online/api/v1/mcp",
    "headers": { "Authorization": "Bearer YOUR_API_KEY" }
  },
  "metadata": { "protocol": "shttp" }
}
```

Vapi opens a fresh connection per tool invocation and discovers the tools via
`tools/list` — there is no session to manage.

### Smoke test

```bash
# discover tools (no auth needed)
curl -s https://numbers.online/api/v1/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# call a tool (needs an mcp-scoped key)
curl -s https://numbers.online/api/v1/mcp \
  -H "Authorization: Bearer $KEY" -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"phone_lookup","arguments":{"number":"+14155552671"}}}'
```

A domain miss (number not found, supplier timeout) comes back as a `result` with
`isError: true` and an LLM-readable message — never a JSON-RPC error — so the agent can
verbalize a graceful fallback. Protocol faults (unknown tool, missing argument) are
JSON-RPC errors (`-32602`).

---

## 2. Retell — `call_inbound` webhook

Point your Retell agent's inbound webhook at:

```
https://numbers.online/api/v1/integrations/retell/inbound?key=YOUR_API_KEY
```

(Use the `?key=` query param with a dedicated, rotatable key — Retell may not send a
custom auth header.) On each inbound call Retell POSTs `call_inbound` and we return
dynamic variables for the agent prompt:

```json
{
  "call_inbound": {
    "dynamic_variables": {
      "caller_valid": "true",
      "caller_name": "ACME CORP",
      "caller_line_type": "mobile",
      "caller_spam_score": "12",
      "caller_risk": "low",
      "caller_on_dnc": "unknown",
      "caller_reassigned": "unknown",
      "caller_signal": "supplementary"
    },
    "metadata": { "provider": "numbers.online", "receipt_id": "nol_rec_…", "checked_at": "…" }
  }
}
```

Reference them in your prompt as `{{caller_risk}}`, `{{caller_on_dnc}}`, etc. The endpoint
**always** returns HTTP 200 within Retell's 10s budget — auth failure, a missing number,
or a supplier timeout degrade to neutral variables (fail-open on the live-call path) so a
slow lookup never keeps the caller ringing. See `integrations/retell/inbound-webhook.json`.

---

## 3. Vapi — custom (function) tool

An alternative to the MCP server for a Vapi `function` tool. Server URL:

```
https://numbers.online/api/v1/integrations/vapi/tool
Authorization: Bearer YOUR_API_KEY
```

Vapi POSTs `{message:{type:"tool-calls", toolCallList:[{id, arguments:{number}}]}}`; we
return `{results:[{toolCallId, result}]}` where `result` is the JSON-stringified
`phone_lookup` bundle. See `integrations/vapi/numbers-online-tool.json`.

---

## Signed receipts (TCPA-defense evidence)

Every billable agent answer can carry a `receipt_id` and an Ed25519 `response_signature`.
Retrieve a receipt later — no API key required, the id is the capability — to produce
verifiable "checked as of T" evidence:

```
GET https://numbers.online/api/v1/receipts/{id}
```

**No raw phone number is stored** — only `number_hash = sha256(E.164)`. To verify: fetch
the public key from `GET https://numbers.online/api/v1/publickey`, check
`response_signature` over the exact `signed_payload` bytes, then recompute
`sha256(your number)` and match it against `number_hash` to bind the receipt to a specific
number.

> **Treat a receipt id as sensitive.** `number_hash` is a number *binding*, not a strong
> anonymizer — a phone number is a small keyspace, so the hash is recomputable from a
> candidate number (that recomputation is exactly the verification step above). Share a
> receipt id only with parties entitled to know that number. The receipt is a
> supplementary signal, not a compliance assertion.

---

## Keys & billing

- Any key already entitled to `lookup` also has the `mcp` use case; new keys get it by
  default.
- The bundled per-call rate is metered only for valid, non-suppressed numbers; `line_type`,
  `dnc_check`, and `reassigned_check` are free.
- MSPs: mint a per-tenant sub-key so agent usage rolls up per customer on one prepaid
  balance, and per-tenant suppression lists apply to agent lookups too.
