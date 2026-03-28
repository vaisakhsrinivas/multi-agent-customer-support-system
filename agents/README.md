# ADK agents

## Layout

- [`customer_support/`](customer_support/) — `SupportRouter` (root) with sub-agents:
  - **DataSpecialist** — Supabase database access via MCP (`@supabase/mcp-server-supabase`, read-only, `database` features only).
  - **TriageSpecialist** — Qualitative support (tone, drafts, prioritization) without DB tools.
  - **ReturnsSpecialist** — `RemoteA2aAgent` calling the dedicated Return A2A app ([`services/return_a2a`](../services/return_a2a/)). Set `RETURN_A2A_DISABLED=true` if that service is not running.

## Setup

From the **repository root** (where `.env` lives):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Environment variables (see [../.env.example](../.env.example)):

| Variable | Required for | Purpose |
|----------|----------------|----------|
| `GOOGLE_API_KEY` | All agents | Gemini API access |
| `SUPABASE_ACCESS_TOKEN` | DataSpecialist | Supabase [personal access token](https://supabase.com/dashboard/account/tokens) |
| `SUPABASE_PROJECT_REF` | DataSpecialist | Project ref from the dashboard URL |
| `ADK_MODEL` | Optional | Defaults to `gemini-2.5-flash` |
| `RETURN_A2A_*` / `RETURN_A2A_CARD_URL` | ReturnsSpecialist | Must match the Return A2A server (see [services/README.md](../services/README.md)) |
| `RETURN_A2A_DISABLED` | Optional | `true` to omit ReturnsSpecialist when the return service is off |

You also need **Node.js** / `npx` on your PATH so the MCP server can start.

**Two processes for full functionality:** start the return service (`python -m services.return_a2a`) before or alongside `adk web agents` so ReturnsSpecialist can resolve the agent card.

## Integration tests (billing / returns / escalation)

Install dev deps and run with real keys (and `npx` for MCP; return A2A server on port 8001 unless overridden):

```bash
pip install -r requirements-dev.txt
export RUN_INTEGRATION_TESTS=1
export GOOGLE_API_KEY=...
export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
# Terminal A:
python -m services.return_a2a
# Terminal B:
pytest tests/test_support_scenarios.py -v
```

Or a single script:

```bash
chmod +x scripts/run_integration_scenarios.py
./scripts/run_integration_scenarios.py
```

## Run the web UI

```bash
cd /path/to/repo/root
adk web agents
```

Open the UI, pick **customer_support**, and chat.

### Agent-to-Agent (A2A) endpoint

```bash
adk web agents --a2a
```

This exposes the A2A protocol endpoint on the ADK web server for interoperable agent clients (see [ADK docs](https://google.github.io/adk-docs/)).

## Windows note

If MCP subprocesses fail with `_make_subprocess_transport NotImplementedError`, try:

```bash
adk web agents --no-reload
```
