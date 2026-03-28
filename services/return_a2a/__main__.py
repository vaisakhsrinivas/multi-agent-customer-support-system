"""Run: python -m services.return_a2a (from repository root)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("RETURN_A2A_HOST", "127.0.0.1")
    port = int(os.environ.get("RETURN_A2A_PORT", "8001"))
    from .app import build_return_a2a_app

    uvicorn.run(build_return_a2a_app(), host=host, port=port)


if __name__ == "__main__":
    main()
