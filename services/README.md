# Services

## Return A2A (`services.return_a2a`)

Dedicated **ReturnAgent** (ADK `LlmAgent`) exposed with **`to_a2a()`** as a Starlette ASGI app. Tools:

- `check_return_eligibility`
- `initiate_return`

The main **SupportRouter** (`agents/customer_support`) includes a **`ReturnsSpecialist`** sub-agent implemented as **`RemoteA2aAgent`**, which calls this service over A2A using the agent card at `/.well-known/agent-card.json`.

### Run (required for returns routing)

From the **repository root**:

```bash
source .venv/bin/activate
export GOOGLE_API_KEY=...
# Defaults match SupportRouter: host 127.0.0.1, port 8001
python -m services.return_a2a
```

Or:

```bash
uvicorn services.return_a2a.app:app --host 127.0.0.1 --port 8001
```

Use the **same** `RETURN_A2A_HOST`, `RETURN_A2A_PORT`, and `RETURN_A2A_PROTOCOL` as in `.env` when you run `adk web agents`, or set **`RETURN_A2A_CARD_URL`** to the full card URL.

### Disable remote returns in the router

If you are not running this service:

```bash
export RETURN_A2A_DISABLED=true
adk web agents
```

Then `SupportRouter` only uses DataSpecialist and TriageSpecialist.

### Demo data

[`return_a2a/returns_logic.py`](return_a2a/returns_logic.py) uses sample orders consistent with [`supabase/seed.sql`](../supabase/seed.sql). Replace with Supabase-backed logic when you harden the stack.

### Integration tests and mini eval

**Integration tests** and the **YAML mini eval** ([`eval/README.md`](../eval/README.md)) expect this service to be reachable when exercising **returns** (unless the eval scenario is skipped or `RETURN_A2A_DISABLED` is set). Defaults (`127.0.0.1:8001`) should match `RETURN_A2A_*` in `.env`.
