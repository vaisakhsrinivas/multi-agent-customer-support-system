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
| `LANGFUSE_*` / `OTEL_EXPORTER_OTLP_*` | Optional | Send ADK OpenTelemetry traces to [Langfuse](https://langfuse.com) — see **Langfuse (observability)** below |

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

## Langfuse (observability)

Google ADK emits **OpenTelemetry** spans (invocations, GenAI attributes). This repo configures an **OTLP HTTP** exporter to **Langfuse** when enabled, using [`observability/langfuse_otel.py`](../observability/langfuse_otel.py). Bootstrap runs at import time in [`customer_support/agent.py`](customer_support/agent.py) (`service.name` **customer_support**) and in [`services/return_a2a/app.py`](../services/return_a2a/app.py) (**return_a2a**) so both `adk web agents` and the return microservice can export traces.

### Install

```bash
pip install -r requirements-observability.txt
```

### Enable (simplest)

Set in `.env` (see [`.env.example`](../.env.example)):

- `LANGFUSE_ENABLED=1`
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` from your Langfuse project
- `LANGFUSE_HOST` only if not on **EU** cloud (default `https://cloud.langfuse.com`). Examples: **US** `https://us.cloud.langfuse.com`, **self-hosted** `http://localhost:3000`.

The app builds the OTLP URL `…/api/public/otel/v1/traces` and `Authorization: Basic …` plus `x-langfuse-ingestion-version: 4` as in [Langfuse OpenTelemetry docs](https://langfuse.com/docs/opentelemetry/get-started).

Alternatively, set `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` yourself (no `LANGFUSE_ENABLED` required). Langfuse accepts **HTTP/protobuf or JSON** OTLP only (not gRPC).

### Optional: OpenInference for `google.genai`

Set `LANGFUSE_OPENINFERENCE=1` to load `openinference-instrumentation-google-genai` for extra Gemini client spans. Inspect traces in Langfuse for overlap with ADK’s own spans.

### PII / message content in spans

By default, ADK may **omit** message bodies from span attributes. To log prompts/responses (higher **PII** risk), set only if acceptable:

- `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=true`
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`

### Other backends / existing OTel

If you already use a global `TracerProvider`, the bootstrap **adds** a `BatchSpanProcessor` to it when possible. For multiple backends or collectors, follow [Langfuse: existing OpenTelemetry setup](https://langfuse.com/faq/all/existing-otel-setup).

### Troubleshooting

- **401 / “Invalid credentials… confirm host”:** Set **`LANGFUSE_HOST`** to the same **region** as your Langfuse project—**EU** `https://cloud.langfuse.com`, **US** `https://us.cloud.langfuse.com`. Use **public** and **secret** keys from that same project (not mixed regions).
- **`.env` changes:** Restart **`adk web agents`** and **`python -m services.return_a2a`**; running processes do not reload `.env`.
- **`python-dotenv`:** By default it does **not** override variables already set in your shell. If `LANGFUSE_*` or `OTEL_*` are wrong in the environment, unset them or export the correct values before starting the app.

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
