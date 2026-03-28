"""Pytest configuration: repo root on path, optional integration gate."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "agents"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: needs GOOGLE_API_KEY, network, and live dependencies"
    )
    config.addinivalue_line(
        "markers",
        "mini_eval: YAML scenario eval; set RUN_MINI_EVAL=1 (see eval/scenarios.yaml)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list | None) -> None:
    if not items:
        return
    if os.environ.get("RUN_INTEGRATION_TESTS", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        skip_int = pytest.mark.skip(
            reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests",
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_int)

    if os.environ.get("RUN_MINI_EVAL", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        skip_me = pytest.mark.skip(
            reason="Set RUN_MINI_EVAL=1 to run mini eval tests",
        )
        for item in items:
            if "mini_eval" in item.keywords:
                item.add_marker(skip_me)
