"""ReturnAgent exposed as an A2A Starlette app (to_a2a). Used by SupportRouter via RemoteA2aAgent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

from .returns_logic import check_return_eligibility, initiate_return

return_agent = LlmAgent(
    name="ReturnAgent",
    model=os.environ.get("ADK_MODEL", "gemini-2.5-flash"),
    description=(
        "Product returns: checks eligibility (delivered, email match, return window) and "
        "registers return requests."
    ),
    instruction="""You handle returns only.

Always call check_return_eligibility before initiate_return.
If not eligible, explain why clearly.
If eligible and the customer confirms, call initiate_return with a short reason.
Never initiate without a successful eligibility check for the same order and email.""",
    tools=[
        FunctionTool(check_return_eligibility),
        FunctionTool(initiate_return),
    ],
)


def build_return_a2a_app():
    """Starlette ASGI app; Agent Card URL should match RETURN_A2A_* / how clients reach this host."""
    host = os.environ.get("RETURN_A2A_HOST", "127.0.0.1")
    port = int(os.environ.get("RETURN_A2A_PORT", "8001"))
    protocol = os.environ.get("RETURN_A2A_PROTOCOL", "http")
    return to_a2a(
        return_agent,
        host=host,
        port=port,
        protocol=protocol,
    )


app = build_return_a2a_app()

__all__ = ["app", "build_return_a2a_app", "return_agent", "to_a2a"]
