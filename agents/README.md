# ADK agents

## Layout

- [`customer_support/`](customer_support/) — `SupportRouter` (root) with two sub-agents:
  - **DataSpecialist** — Supabase database access via MCP (`@supabase/mcp-server-supabase`, read-only, `database` features only).
  - **TriageSpecialist** — Qualitative support (tone, drafts, prioritization) without DB tools.

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

You also need **Node.js** / `npx` on your PATH so the MCP server can start.

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
