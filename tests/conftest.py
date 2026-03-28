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
