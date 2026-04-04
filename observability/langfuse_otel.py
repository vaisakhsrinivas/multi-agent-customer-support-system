"""Optional OpenTelemetry export to Langfuse for ADK / google.genai spans.

Install: pip install -r requirements-observability.txt

Enable with LANGFUSE_ENABLED=1 plus LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (and
optional LANGFUSE_HOST), or set OTEL_EXPORTER_OTLP_* yourself. See agents/README.md.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ran_configure: bool = False
_openinference_instrumented: bool = False


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _tracing_requested() -> bool:
    if _truthy("LANGFUSE_ENABLED"):
        return True
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return True
    if os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip():
        return True
    return False


def _parse_otlp_headers(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        out[key.strip()] = value.strip()
    return out


def _resolve_exporter_config() -> tuple[str | None, dict[str, str] | None]:
    traces_ep = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    base_ep = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    endpoint = traces_ep or base_ep

    headers_raw = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "").strip()
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    sk = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()

    if not endpoint:
        if pk and sk:
            host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").strip().rstrip(
                "/"
            )
            endpoint = f"{host}/api/public/otel/v1/traces"
        else:
            return None, None

    if headers_raw:
        headers = _parse_otlp_headers(headers_raw)
    elif pk and sk:
        token = base64.b64encode(f"{pk}:{sk}".encode()).decode("ascii")
        headers = {
            "Authorization": f"Basic {token}",
            "x-langfuse-ingestion-version": "4",
        }
    else:
        headers = {}

    return endpoint, headers


def _maybe_instrument_openinference() -> None:
    global _openinference_instrumented
    if _openinference_instrumented:
        return
    if not _truthy("LANGFUSE_OPENINFERENCE"):
        return
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    except ImportError:
        logger.warning(
            "LANGFUSE_OPENINFERENCE=1 but openinference-instrumentation-google-genai "
            "is not installed (pip install -r requirements-observability.txt)."
        )
        return
    try:
        GoogleGenAIInstrumentor().instrument()
        _openinference_instrumented = True
    except Exception:
        logger.exception("OpenInference Google GenAI instrumentation failed")


def configure_tracing(*, service_name: str = "customer_support") -> None:
    """Configure OTLP HTTP export to Langfuse (or any OTLP backend). Safe to call once per process."""
    global _ran_configure
    if _ran_configure:
        return
    _ran_configure = True

    if not _tracing_requested():
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "Langfuse/OTel tracing requested but opentelemetry-sdk or OTLP exporter "
            "is missing. Install: pip install -r requirements-observability.txt"
        )
        return

    endpoint, headers = _resolve_exporter_config()
    if not endpoint:
        logger.warning(
            "Tracing requested (LANGFUSE_ENABLED or OTEL_EXPORTER_OTLP_*) but no OTLP "
            "endpoint could be resolved. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
            "or OTEL_EXPORTER_OTLP_TRACES_ENDPOINT / OTEL_EXPORTER_OTLP_ENDPOINT."
        )
        return

    resource = Resource.create(
        {
            "service.name": service_name,
        }
    )
    exporter_kwargs: dict[str, Any] = {"endpoint": endpoint}
    if headers:
        exporter_kwargs["headers"] = headers

    try:
        exporter = OTLPSpanExporter(**exporter_kwargs)
    except Exception:
        logger.exception("Failed to create OTLPSpanExporter for endpoint %s", endpoint)
        return

    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        current.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("Added OTLP span processor to existing TracerProvider (%s).", service_name)
    else:
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry TracerProvider configured for Langfuse/OTLP (%s).", service_name)

    _maybe_instrument_openinference()
