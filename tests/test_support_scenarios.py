"""Integration tests: billing (Supabase MCP), returns (Remote A2A), escalation (triage).

Run from repository root:

  export RUN_INTEGRATION_TESTS=1
  export GOOGLE_API_KEY=...
  export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
  # Terminal A: python -m services.return_a2a
  pytest tests/test_support_scenarios.py -v

Requires Node/npx for MCP. Returns scenario needs the return A2A server reachable at RETURN_A2A_CARD_URL.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    load_dotenv(_ROOT / ".env")


def _tool_names_from_event(event) -> list[str]:
    names: list[str] = []
    if not event.content or not event.content.parts:
        return names
    for p in event.content.parts:
        fc = getattr(p, "function_call", None)
        if fc is not None and getattr(fc, "name", None):
            names.append(fc.name)
    return names


async def _run_prompt(agent, prompt: str) -> dict:
    runner = InMemoryRunner(agent=agent, app_name="support_scenario_test")
    authors: list[str] = []
    tool_names: list[str] = []
    texts: list[str] = []
    session_id = f"test-{uuid.uuid4().hex}"
    async for event in runner.run_async(
        user_id="integration-tester",
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        ),
    ):
        authors.append(event.author)
        tool_names.extend(_tool_names_from_event(event))
        if event.content and event.content.parts:
            for p in event.content.parts:
                if getattr(p, "text", None):
                    texts.append(p.text)
    return {
        "authors": authors,
        "tool_names": tool_names,
        "text": "\n".join(texts),
    }


async def _agent_card_reachable(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            return r.status_code == 200
    except OSError:
        return False


@pytest.fixture(scope="module")
def support_root_agent():
    _load_env()
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    if not os.environ.get("SUPABASE_ACCESS_TOKEN") or not os.environ.get(
        "SUPABASE_PROJECT_REF"
    ):
        pytest.skip("SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF required for import")
    # Import after env (agent module reads env at import)
    if "customer_support.agent" in sys.modules:
        del sys.modules["customer_support.agent"]
    from customer_support import agent as agent_mod

    return agent_mod.root_agent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_billing_uses_mcp_data_specialist(support_root_agent):
    """Order/billing facts → DataSpecialist + Supabase MCP (execute_sql)."""
    prompt = (
        "For billing verification: what is total_cents and currency for order "
        "bbbbbbbb-0001-4000-8000-000000000001? Use the database."
    )
    out = await _run_prompt(support_root_agent, prompt)
    assert "DataSpecialist" in out["authors"], f"authors={out['authors']}"
    assert (
        "execute_sql" in out["tool_names"] or "4999" in out["text"]
    ), f"tools={out['tool_names']} text[:500]={out['text'][:500]!r}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_returns_uses_remote_a2a(support_root_agent):
    """Return eligibility → ReturnsSpecialist + check_return_eligibility (A2A side)."""
    card_url = os.environ.get("RETURN_A2A_CARD_URL", "").strip()
    if not card_url:
        host = os.environ.get("RETURN_A2A_HOST", "127.0.0.1")
        port = os.environ.get("RETURN_A2A_PORT", "8001")
        protocol = os.environ.get("RETURN_A2A_PROTOCOL", "http")
        card_url = f"{protocol}://{host}:{port}/.well-known/agent-card.json"
    if os.environ.get("RETURN_A2A_DISABLED", "").lower() in ("1", "true", "yes"):
        pytest.skip("ReturnsSpecialist disabled via RETURN_A2A_DISABLED")
    reachable = await _agent_card_reachable(card_url)
    if not reachable:
        pytest.skip(
            f"Return A2A server not reachable at {card_url} — start: python -m services.return_a2a"
        )

    prompt = (
        "Can I return order bbbbbbbb-0001-4000-8000-000000000001? "
        "My email is ava.chen@example.com. Check eligibility."
    )
    out = await _run_prompt(support_root_agent, prompt)
    assert "ReturnsSpecialist" in out["authors"], f"authors={out['authors']}"
    # Tool calls may appear on the remote A2A agent's trace; also accept clear eligibility text.
    assert (
        "check_return_eligibility" in out["tool_names"]
        or "eligible" in out["text"].lower()
    ), f"tools={out['tool_names']} text[:500]={out['text'][:500]!r}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_escalation_uses_triage_specialist(support_root_agent):
    """Supervisor / legal threat → TriageSpecialist with escalation guidance."""
    prompt = (
        "I am furious. I will sue your company if you do not fix this today. "
        "I demand a supervisor now and will not accept a bot."
    )
    out = await _run_prompt(support_root_agent, prompt)
    assert "TriageSpecialist" in out["authors"], f"authors={out['authors']}"
    lower = out["text"].lower()
    assert any(
        k in lower for k in ("supervisor", "human", "escalat", "manager", "agent")
    ), f"expected escalation language in: {out['text'][:800]}"
