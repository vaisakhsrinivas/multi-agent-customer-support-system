"""CLI: python -m eval [path/to/scenarios.yaml]"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


async def _main() -> int:
    load_dotenv(_root() / ".env")
    if not os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY not set", file=sys.stderr)
        return 2
    if not os.environ.get("SUPABASE_ACCESS_TOKEN") or not os.environ.get(
        "SUPABASE_PROJECT_REF"
    ):
        print(
            "SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF required (agent import)",
            file=sys.stderr,
        )
        return 2

    agents_dir = _root() / "agents"
    sys.path.insert(0, str(agents_dir))

    from customer_support.agent import root_agent

    from eval.engine import default_scenarios_path, format_report, load_scenarios, run_scenario

    scenarios_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_scenarios_path()
    scenarios = load_scenarios(scenarios_path)
    results = []
    for sc in scenarios:
        results.append(await run_scenario(root_agent, sc))
    print(format_report(results))
    failed = sum(1 for r in results if not r.skipped and not r.passed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
