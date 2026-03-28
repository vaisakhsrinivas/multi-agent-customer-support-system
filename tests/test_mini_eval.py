"""YAML-driven mini eval: same live deps as integration tests (MCP, optional A2A).

  export RUN_MINI_EVAL=1
  export GOOGLE_API_KEY=...
  export SUPABASE_ACCESS_TOKEN=... SUPABASE_PROJECT_REF=...
  pytest tests/test_mini_eval.py -v

CLI: python -m eval
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    load_dotenv(_ROOT / ".env")


@pytest.fixture(scope="module")
def support_root_agent():
    _load_env()
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set")
    if not os.environ.get("SUPABASE_ACCESS_TOKEN") or not os.environ.get(
        "SUPABASE_PROJECT_REF"
    ):
        pytest.skip("SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF required for import")
    if "customer_support.agent" in sys.modules:
        del sys.modules["customer_support.agent"]
    from customer_support import agent as agent_mod

    return agent_mod.root_agent


def _scenario_ids() -> list[str]:
    from eval.engine import default_scenarios_path, load_scenarios

    return [s["id"] for s in load_scenarios(default_scenarios_path())]


@pytest.mark.mini_eval
@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_id", _scenario_ids())
async def test_mini_eval_scenario(support_root_agent, scenario_id: str):
    from eval.engine import default_scenarios_path, load_scenarios, run_scenario

    scenarios = {s["id"]: s for s in load_scenarios(default_scenarios_path())}
    scenario = scenarios[scenario_id]
    result = await run_scenario(support_root_agent, scenario)
    if result.skipped:
        pytest.skip(result.skip_reason)
    assert result.passed, (
        f"score {result.scenario_score:.2f} < threshold {result.pass_threshold:.2f}; "
        + "; ".join(result.errors)
    )
