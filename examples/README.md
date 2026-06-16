# Reference clients

Zero-dependency examples that call the hosted Numbers Online MCP server over the
Streamable HTTP transport. They list the tools (public) and, with a key, run a
`phone_lookup`.

### Node (18+)

```bash
node node/lookup.mjs                                  # discovery only
NUMBERS_ONLINE_KEY=sk_... node node/lookup.mjs +14155552671
```

### Python (3.8+, stdlib only)

```bash
python python/lookup.py                               # discovery only
NUMBERS_ONLINE_KEY=sk_... python python/lookup.py +14155552671
```

Override the endpoint with `NUMBERS_ONLINE_MCP_URL` if needed. A key needs the `mcp`
use case — get one at https://numbers.online. Every result is a supplementary,
low-confidence signal; your agent keeps every routing and dialing decision.
