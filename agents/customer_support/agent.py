"""Multi-agent customer support: router + specialists (one uses Supabase MCP)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Load .env from repo root (parent of `agents/`)
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from observability.langfuse_otel import configure_tracing

configure_tracing(service_name="customer_support")


def _str_env() -> dict[str, str]:
    return {k: str(v) for k, v in os.environ.items() if v is not None}


def _supabase_mcp_toolset() -> McpToolset:
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    project_ref = os.environ.get("SUPABASE_PROJECT_REF", "").strip()
    if not token or not project_ref:
        raise RuntimeError(
            "DataSpecialist needs Supabase MCP. Set SUPABASE_ACCESS_TOKEN and "
            "SUPABASE_PROJECT_REF in .env (see .env.example)."
        )

    env = _str_env()
    env["SUPABASE_ACCESS_TOKEN"] = token

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@supabase/mcp-server-supabase",
                    "--project-ref",
                    project_ref,
                    "--read-only",
                    "--features",
                    "database",
                ],
                env=env,
            ),
        ),
    )


def _model() -> str:
    return os.environ.get("ADK_MODEL", "gemini-2.5-flash")


def _returns_agent_card_url() -> str:
    """Agent card URL for the dedicated Return A2A service (must match running server)."""
    explicit = os.environ.get("RETURN_A2A_CARD_URL", "").strip()
    if explicit:
        return explicit
    host = os.environ.get("RETURN_A2A_HOST", "127.0.0.1")
    port = os.environ.get("RETURN_A2A_PORT", "8001")
    protocol = os.environ.get("RETURN_A2A_PROTOCOL", "http")
    return f"{protocol}://{host}:{port}/.well-known/agent-card.json"


def _returns_specialist() -> RemoteA2aAgent | None:
    if os.environ.get("RETURN_A2A_DISABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return None
    return RemoteA2aAgent(
        name="ReturnsSpecialist",
        agent_card=_returns_agent_card_url(),
        description=(
            "Remote A2A ReturnAgent: return eligibility (delivered, window, email match) and "
            "initiating returns. Run `python -m services.return_a2a` so this endpoint is up."
        ),
    )


_data_specialist = LlmAgent(
    name="DataSpecialist",
    model=_model(),
    description=(
        "Queries the live Supabase Postgres database (customers, orders, support_tickets) "
        "via MCP: list tables, run read-only SQL, inspect migrations. Use for factual lookups."
    ),
    instruction="""You answer with data from Supabase only—no guessing.

Use MCP tools to:
- Call `list_tables` when you need schema or table names.
- Use `execute_sql` for SELECT queries (read-only server; no writes).

Main tables: public.customers, public.orders, public.support_tickets.
Prefer filtering by email, order id, or ticket id when the user provides them.
Return concise summaries; include relevant IDs and statuses for the router to relay.""",
    tools=[_supabase_mcp_toolset()],
)

_triage_specialist = LlmAgent(
    name="TriageSpecialist",
    model=_model(),
    description=(
        "Handles qualitative support: tone, prioritization, reply drafts, categorization, "
        "escalation to humans, and policy-style guidance when no database lookup is needed."
    ),
    instruction="""You improve support quality without database access.

- Classify urgency (low/normal/high) and suggest next steps.
- Draft short, empathetic customer-facing replies when asked.
- Escalation: legal threats, harassment, safety issues, demands for a supervisor/manager,
  or clear refusal to accept policy → stay calm, acknowledge concern, outline next steps,
  and recommend a human agent / supervisor handoff with suggested internal priority (e.g. high).
- If the user needs order numbers, ticket status, or account facts from the database,
  state clearly that DataSpecialist must look them up and what identifiers (email, order id)
  are required.""",
)

_sub_agents: list = [_data_specialist, _triage_specialist]
_rs = _returns_specialist()
if _rs is not None:
    _sub_agents.append(_rs)

_ROUTER_NAMES = "DataSpecialist, TriageSpecialist"
if _rs is not None:
    _ROUTER_NAMES += ", ReturnsSpecialist"

root_agent = LlmAgent(
    name="SupportRouter",
    model=_model(),
    description="Front-door agent that routes customer issues to the right specialist.",
    instruction=f"""You are the primary customer support assistant.

Routing:
- Questions about specific customers, orders, shipping/payment status, ticket records,
  billing amounts, or anything needing SQL/database facts → transfer to DataSpecialist.
- Product returns, refunds for shipped items, return labels, or whether an order can be
  returned → transfer to ReturnsSpecialist (remote A2A). Ask for order id and email if missing.
- Anger, legal threats, supervisor/manager requests, harassment, safety, or human
  escalation → transfer to TriageSpecialist.
- Wording help, empathy, prioritization, templates, or general policy without DB or returns
  → transfer to TriageSpecialist.

After a specialist responds, you may combine their output into one clear answer for the user.
Use transfer_to_agent with the exact agent name. Available specialists: {_ROUTER_NAMES}.""",
    sub_agents=_sub_agents,
)
