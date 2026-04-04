# Mini eval

## Layout

| Path | Role |
|------|------|
| [`scenarios.yaml`](scenarios.yaml) | Declarative scenarios (`id`, `prompt`, `rules`, optional `pass_threshold`, skips). |
| [`engine.py`](engine.py) | Loads YAML, runs the agent via ADK `Runner`, evaluates rules, computes **weighted scores**. |
| [`__main__.py`](__main__.py) | **`python -m eval`** entrypoint: loads `.env`, imports `root_agent`, prints report, sets **exit code**. |

Install **`requirements-dev.txt`** (includes **PyYAML**). Same env vars as agents: **`GOOGLE_API_KEY`**, **`SUPABASE_ACCESS_TOKEN`**, **`SUPABASE_PROJECT_REF`**, optional **`RETURN_A2A_*`** / **`RETURN_A2A_DISABLED`**.

**Langfuse:** `python -m eval` and pytest mini eval import [`customer_support/agent`](../agents/customer_support/agent.py). If **`LANGFUSE_ENABLED`** is on and [`requirements-observability.txt`](../requirements-observability.txt) is installed, those runs may **export OpenTelemetry traces** to Langfuse like a normal chat session. Unset Langfuse env vars (or disable tracing) if you want eval runs without observability noise.

## Two evaluation styles

1. **YAML mini eval (this folder)** — After each live run, rules check **authors**, **tool names**, and **response text**. Each rule scores **0 or 1**; the scenario score is a **weighted mean** compared to **`pass_threshold`** (default **1.0**). Optional **per-rule `weight`**. Same runtime needs as integration tests (Gemini, Supabase MCP via `npx`, optional Return A2A).

2. **ADK built-in eval** — `adk eval agents/customer_support path/to/evalset.test.json` using an [EvalSet](https://google.github.io/adk-docs/evaluate/) JSON file (ROUGE, trajectory metrics, etc.). `agents/customer_support/__init__.py` uses `from . import agent` so the ADK CLI resolves **`root_agent`**. Independent of the YAML runner.

## Run (YAML)

From **repository root**, with dev deps:

```bash
pip install -r requirements-dev.txt
export RUN_MINI_EVAL=1
export GOOGLE_API_KEY=...
export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
python -m services.return_a2a   # optional; returns scenario skips if unreachable
pytest tests/test_mini_eval.py -v
```

**CLI** (no `RUN_MINI_EVAL` required; always runs all scenarios from the default or given YAML path):

```bash
python -m eval
python -m eval /path/to/custom_scenarios.yaml
```

### CLI report and exit code

`python -m eval` prints:

- **SKIP** / **PASS** / **FAIL** per scenario (skipped scenarios include the reason).
- For each executed scenario: **`score=… (threshold …)`** and one line per **rule** (`rule[i] <type>=0.00|1.00 (w=…)`), plus error detail when a rule fails.
- Summary: counts and **mean score** over **non-skipped** scenarios.

Exit code **0** only if every **non-skipped** scenario **passes** (`scenario_score >= pass_threshold`). Exit code **2** if required env vars are missing before the agent loads.

**Pytest** asserts the same pass condition per scenario (`RUN_MINI_EVAL=1` gates collection); failures show score vs threshold in the assertion message.

## Scenario schema

Each item under `scenarios` supports:

| Field | Meaning |
|--------|--------|
| `id` | Stable id (pytest param id). |
| `prompt` | User message. |
| `rules` | List of checks; each contributes a binary score (1 = pass, 0 = fail). |
| `pass_threshold` | Optional; **0–1**. Scenario **passes** if weighted rule score ≥ this (default **1.0**). |
| `skip_if_truthy_env` | List of env var names; scenario skipped if any is `1`/`true`/`yes`. |
| `requires_return_a2a_server` | If true, skip when the return agent card URL is not HTTP 200. |

**Rule types** (see [`engine.py`](engine.py)):

- `authors_include` — `names: [SubAgentName, ...]` (each substring must appear in streamed `event.author` values).
- `tools_any` — `names: [tool_name, ...]` (at least one function call name).
- `text_contains_any` — `substrings: [...]`, optional `case_insensitive` (default true).
- `text_min_length` — `min: N` (character count on combined model text).
- `tools_or_text` — `tools_any` and/or `text_any`; passes if any tool matches **or** any substring appears in the reply.

Optional on any rule: **`weight`** (number, default `1.0`) — weights the rule in the scenario’s mean score.

Add or edit scenarios in [`scenarios.yaml`](scenarios.yaml); no Python changes needed for new cases that fit these rules. **Tests:** [`tests/test_mini_eval.py`](../tests/test_mini_eval.py) (marker `mini_eval`, gated by `RUN_MINI_EVAL=1`).
