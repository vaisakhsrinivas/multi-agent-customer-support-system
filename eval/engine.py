"""Load YAML scenarios, run the support agent once per scenario, apply rule checks."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

_DEFAULT_APP_NAME = "mini_eval"


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _tool_names_from_event(event) -> list[str]:
    names: list[str] = []
    if not event.content or not event.content.parts:
        return names
    for p in event.content.parts:
        fc = getattr(p, "function_call", None)
        if fc is not None and getattr(fc, "name", None):
            names.append(fc.name)
    return names


def make_runner(agent, app_name: str = _DEFAULT_APP_NAME) -> Runner:
    return Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        auto_create_session=True,
    )


async def run_prompt(agent, prompt: str, *, app_name: str = _DEFAULT_APP_NAME) -> dict[str, Any]:
    runner = make_runner(agent, app_name=app_name)
    authors: list[str] = []
    tool_names: list[str] = []
    texts: list[str] = []
    session_id = f"eval-{uuid.uuid4().hex}"
    async for event in runner.run_async(
        user_id="mini-eval",
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


async def _return_a2a_card_url() -> str:
    card_url = os.environ.get("RETURN_A2A_CARD_URL", "").strip()
    if card_url:
        return card_url
    host = os.environ.get("RETURN_A2A_HOST", "127.0.0.1")
    port = os.environ.get("RETURN_A2A_PORT", "8001")
    protocol = os.environ.get("RETURN_A2A_PROTOCOL", "http")
    return f"{protocol}://{host}:{port}/.well-known/agent-card.json"


async def _agent_card_reachable(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            return r.status_code == 200
    except OSError:
        return False


def _authors_include(authors: list[str], names: list[str]) -> bool:
    blob = " ".join(authors)
    return all(n in blob for n in names)


def _tools_any(tool_names: list[str], needles: list[str]) -> bool:
    return any(t in tool_names for t in needles)


def _text_any(text: str, substrings: list[str], *, lower: bool) -> bool:
    hay = text.lower() if lower else text
    for s in substrings:
        cmp = s.lower() if lower else s
        if cmp in hay:
            return True
    return False


def _check_rule(rule: dict[str, Any], out: dict[str, Any]) -> str | None:
    rtype = rule.get("type")
    authors = out["authors"]
    tool_names = out["tool_names"]
    text = out["text"]

    if rtype == "authors_include":
        names = rule.get("names", [])
        if not _authors_include(authors, names):
            return f"authors_include failed: need all of {names!r} in authors={authors!r}"
        return None

    if rtype == "tools_any":
        needles = rule.get("names", [])
        if not _tools_any(tool_names, needles):
            return f"tools_any failed: need one of {needles!r} in tool_names={tool_names!r}"
        return None

    if rtype == "text_contains_any":
        subs = rule.get("substrings", [])
        lower = rule.get("case_insensitive", True)
        if not _text_any(text, subs, lower=lower):
            return (
                f"text_contains_any failed: need one of {subs!r} in text[:800]={text[:800]!r}"
            )
        return None

    if rtype == "text_min_length":
        n = int(rule.get("min", 0))
        if len(text.strip()) < n:
            return f"text_min_length failed: len={len(text.strip())} < {n}"
        return None

    if rtype == "tools_or_text":
        t_any = rule.get("tools_any", [])
        txt_any = rule.get("text_any", [])
        ok_tools = _tools_any(tool_names, t_any) if t_any else False
        ok_text = _text_any(text, txt_any, lower=True) if txt_any else False
        if ok_tools or ok_text:
            return None
        return (
            "tools_or_text failed: "
            f"tools_any={t_any!r} vs {tool_names!r}, text_any={txt_any!r} vs {text[:400]!r}"
        )

    return f"unknown rule type: {rtype!r}"


def _rule_weight(rule: dict[str, Any]) -> float:
    w = rule.get("weight", 1.0)
    try:
        w = float(w)
    except (TypeError, ValueError):
        return 1.0
    return max(w, 0.0)


@dataclass
class RuleOutcome:
    """One rule after evaluation: score is 0.0–1.0 (binary per rule)."""

    index: int
    rule_type: str
    score: float
    weight: float
    error: str | None = None


@dataclass
class ScenarioResult:
    scenario_id: str
    skipped: bool
    skip_reason: str = ""
    rule_outcomes: list[RuleOutcome] = field(default_factory=list)
    scenario_score: float = 0.0
    pass_threshold: float = 1.0
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if self.skipped:
            return False
        return self.scenario_score + 1e-9 >= self.pass_threshold


def _weighted_score(outcomes: list[RuleOutcome]) -> float:
    if not outcomes:
        return 1.0
    tw = sum(o.weight for o in outcomes)
    if tw <= 0:
        return 1.0
    return sum(o.score * o.weight for o in outcomes) / tw


def evaluate_rules(rules: list[dict[str, Any]], out: dict[str, Any]) -> list[RuleOutcome]:
    outcomes: list[RuleOutcome] = []
    for i, rule in enumerate(rules):
        rtype = str(rule.get("type", ""))
        w = _rule_weight(rule)
        msg = _check_rule(rule, out)
        if msg is None:
            outcomes.append(RuleOutcome(i, rtype, 1.0, w, None))
        else:
            outcomes.append(RuleOutcome(i, rtype, 0.0, w, msg))
    return outcomes


async def run_scenario(agent, scenario: dict[str, Any]) -> ScenarioResult:
    sid = scenario.get("id", "<missing id>")
    threshold_raw = scenario.get("pass_threshold", 1.0)
    try:
        pass_threshold = float(threshold_raw)
    except (TypeError, ValueError):
        pass_threshold = 1.0
    pass_threshold = min(max(pass_threshold, 0.0), 1.0)

    for env_key in scenario.get("skip_if_truthy_env", []) or []:
        if _truthy_env(str(env_key)):
            return ScenarioResult(
                sid,
                skipped=True,
                skip_reason=f"{env_key} is set",
                pass_threshold=pass_threshold,
            )

    if scenario.get("requires_return_a2a_server"):
        url = await _return_a2a_card_url()
        if not await _agent_card_reachable(url):
            return ScenarioResult(
                sid,
                skipped=True,
                skip_reason=f"Return A2A not reachable at {url}",
                pass_threshold=pass_threshold,
            )

    prompt = scenario.get("prompt", "")
    if not prompt.strip():
        return ScenarioResult(
            sid,
            skipped=False,
            scenario_score=0.0,
            pass_threshold=pass_threshold,
            errors=["empty prompt"],
        )

    out = await run_prompt(agent, prompt)
    rules = list(scenario.get("rules", []) or [])
    outcomes = evaluate_rules(rules, out)
    errors = [o.error for o in outcomes if o.error]
    scenario_score = _weighted_score(outcomes)

    return ScenarioResult(
        sid,
        skipped=False,
        rule_outcomes=outcomes,
        scenario_score=scenario_score,
        pass_threshold=pass_threshold,
        errors=errors,
    )


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scenarios file must be a mapping at top level")
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("scenarios file must contain a 'scenarios' list")
    return scenarios


def default_scenarios_path() -> Path:
    return Path(__file__).resolve().parent / "scenarios.yaml"


async def run_all(
    agent,
    scenarios_path: Path | None = None,
) -> list[ScenarioResult]:
    path = scenarios_path or default_scenarios_path()
    scenarios = load_scenarios(path)
    results: list[ScenarioResult] = []
    for sc in scenarios:
        results.append(await run_scenario(agent, sc))
    return results


def format_report(results: list[ScenarioResult]) -> str:
    lines: list[str] = []
    failed = 0
    skipped = 0
    ran_scores: list[float] = []
    for r in results:
        if r.skipped:
            skipped += 1
            lines.append(f"SKIP  {r.scenario_id}: {r.skip_reason}")
            continue
        ran_scores.append(r.scenario_score)
        status = "PASS" if r.passed else "FAIL"
        lines.append(
            f"{status}  {r.scenario_id}  score={r.scenario_score:.2f} "
            f"(threshold {r.pass_threshold:.2f})"
        )
        for o in r.rule_outcomes:
            rs = f"rule[{o.index}] {o.rule_type}={o.score:.2f} (w={o.weight:g})"
            lines.append(f"      {rs}")
            if o.error:
                lines.append(f"            {o.error}")
        if not r.passed:
            failed += 1
    n_ok = len(ran_scores) - failed
    mean_ran = sum(ran_scores) / len(ran_scores) if ran_scores else 0.0
    lines.append(
        f"\n{n_ok} passed, {failed} failed, {skipped} skipped "
        f"| mean score (non-skipped): {mean_ran:.2f}"
    )
    return "\n".join(lines)
