#!/usr/bin/env python3
"""Run the same three scenarios as tests/test_support_scenarios.py (stdout only).

Usage (from repo root):

  export GOOGLE_API_KEY=...
  export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
  python scripts/run_integration_scenarios.py

Start `python -m services.return_a2a` first for the returns scenario.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    load_dotenv(_ROOT / ".env")
    if not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("Set GOOGLE_API_KEY")
    if not os.environ.get("SUPABASE_ACCESS_TOKEN") or not os.environ.get(
        "SUPABASE_PROJECT_REF"
    ):
        sys.exit("Set SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF")

    sys.path.insert(0, str(_ROOT / "agents"))
    if "customer_support.agent" in sys.modules:
        del sys.modules["customer_support.agent"]
    from customer_support import agent as agent_mod

    asyncio.run(_run_all(agent_mod.root_agent))


async def _run_all(agent) -> None:
    scenarios = [
        (
            "billing (MCP)",
            "For billing: what is total_cents and currency for order "
            "bbbbbbbb-0001-4000-8000-000000000001? Use the database.",
            lambda authors, tools, text: "DataSpecialist" in authors
            and ("execute_sql" in tools or "4999" in text),
        ),
        (
            "returns (A2A)",
            "Can I return order bbbbbbbb-0001-4000-8000-000000000001? "
            "Email ava.chen@example.com. Check eligibility only.",
            lambda authors, tools, text: "ReturnsSpecialist" in authors
            and ("check_return_eligibility" in tools or "eligible" in text.lower()),
        ),
        (
            "escalation",
            "I will sue you if this is not fixed. I need a supervisor immediately.",
            lambda authors, tools, text: "TriageSpecialist" in authors
            and any(
                k in text.lower()
                for k in ("supervisor", "human", "escalat", "manager", "agent")
            ),
        ),
    ]

    for name, prompt, check in scenarios:
        authors, tools, text = await _run_prompt(agent, prompt)
        ok = check(authors, tools, text)
        status = "PASS" if ok else "FAIL"
        print(f"\n=== {name} [{status}] ===")
        print("authors:", authors)
        print("tools:", tools)
        print("text (excerpt):", text[:1200])
        if not ok:
            sys.exit(1)


async def _run_prompt(agent, prompt: str):
    runner = InMemoryRunner(agent=agent, app_name="support_scenario_cli")
    authors: list[str] = []
    tools: list[str] = []
    texts: list[str] = []
    async for event in runner.run_async(
        user_id="cli-user",
        session_id=f"cli-{uuid.uuid4().hex}",
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        authors.append(event.author)
        if event.content and event.content.parts:
            for p in event.content.parts:
                fc = getattr(p, "function_call", None)
                if fc is not None and getattr(fc, "name", None):
                    tools.append(fc.name)
                if getattr(p, "text", None):
                    texts.append(p.text)
    return authors, tools, "\n".join(texts)


if __name__ == "__main__":
    main()
