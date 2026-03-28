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

## Mini eval (YAML scenarios + scoring)

Declarative scenarios live in [`eval/scenarios.yaml`](../eval/scenarios.yaml): billing via **DataSpecialist** + MCP, returns via **ReturnsSpecialist** + A2A (skipped if the return server is down or `RETURN_A2A_DISABLED` is set), triage escalation, plus light greeting/capability checks. Dependencies match **integration tests** (Gemini, Supabase MCP, Node/`npx`, optional return service on port 8001 unless you override `RETURN_A2A_*`).

**Scoring:** each **rule** scores **1** (pass) or **0** (fail). The scenario **score** is a **weighted average** (default weight `1.0` per rule; override with `weight` on a rule). The scenario **passes** if `score >= pass_threshold` (default **1.0**, i.e. all rules must pass). See [`eval/README.md`](../eval/README.md) for rule types and schema.

**Pytest** (one parametrized test per scenario):

```bash
pip install -r requirements-dev.txt
export RUN_MINI_EVAL=1
export GOOGLE_API_KEY=...
export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
# Optional Terminal A for returns scenario:
python -m services.return_a2a
# Terminal B:
pytest tests/test_mini_eval.py -v
```

**CLI** (runs all scenarios, prints a text report, sets exit code):

```bash
pip install -r requirements-dev.txt
export GOOGLE_API_KEY=...
export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
python -m eval
# Optional custom file:
python -m eval path/to/scenarios.yaml
```

The CLI prints **PASS/FAIL/SKIP** per scenario, **score vs threshold**, each **rule’s score and weight**, failure lines for failed rules, and **mean score** across non-skipped scenarios. Exit code **0** = all non-skipped scenarios passed.

**ADK built-in eval:** `agents/customer_support/__init__.py` includes `from . import agent` so **`adk eval agents/customer_support path/to/evalset.test.json`** can load `root_agent` (see [ADK evaluate docs](https://google.github.io/adk-docs/evaluate/)). That path is separate from the YAML mini eval.

Full reference: [`eval/README.md`](../eval/README.md).

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
