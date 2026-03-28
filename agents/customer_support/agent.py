"""Multi-agent customer support: router + specialists (one uses Supabase MCP)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Load .env from repo root (parent of `agents/`)
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


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
        "and policy-style guidance when no database lookup is needed."
    ),
    instruction="""You improve support quality without database access.

- Classify urgency (low/normal/high) and suggest next steps.
- Draft short, empathetic customer-facing replies when asked.
- If the user needs order numbers, ticket status, or account facts from the database,
  state clearly that DataSpecialist must look them up and what identifiers (email, order id)
  are required.""",
)

root_agent = LlmAgent(
    name="SupportRouter",
    model=_model(),
    description="Front-door agent that routes customer issues to the right specialist.",
    instruction="""You are the primary customer support assistant.

Routing:
- Questions about specific customers, orders, shipping/payment status, ticket records, or
  anything needing SQL/database facts → transfer to DataSpecialist (use transfer_to_agent).
- Wording help, empathy, prioritization, templates, or general policy guidance without
  needing live data → transfer to TriageSpecialist.

After a specialist responds, you may combine their output into one clear answer for the user.
Use transfer_to_agent with the exact agent name: DataSpecialist or TriageSpecialist.""",
    sub_agents=[_data_specialist, _triage_specialist],
)
