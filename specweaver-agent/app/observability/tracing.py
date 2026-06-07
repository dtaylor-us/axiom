"""OpenTelemetry tracing setup for the SpecWeaver agent."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.observability.metrics import setup_metrics

logger = logging.getLogger(__name__)
_tracer_provider: TracerProvider | None = None


def configure_telemetry() -> None:
    """
    Initialise tracing and metrics with the same OTLP guard as archon-agent.

    Export is disabled when OTEL_SDK_DISABLED=true or no endpoint is set.
    """
    setup_tracing()
    setup_metrics()


def setup_tracing() -> None:
    """Initialise the global tracer provider once."""
    global _tracer_provider
    if _tracer_provider is not None:
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    is_otel_disabled = os.getenv("OTEL_SDK_DISABLED", "").lower() == "true"
    service_name = os.getenv("OTEL_SERVICE_NAME", "specweaver-agent")

    resource = Resource.create({SERVICE_NAME: service_name})
    _tracer_provider = TracerProvider(resource=resource)

    if is_otel_disabled or not otlp_endpoint:
        trace.set_tracer_provider(_tracer_provider)
        logger.info(
            "OTel tracing using no-op provider. Set "
            "OTEL_EXPORTER_OTLP_ENDPOINT to enable trace export."
        )
        return

    try:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception as exc:
        logger.warning(
            "OTel tracing exporter setup failed. endpoint=%s error=%s. "
            "Falling back to no-op provider.",
            otlp_endpoint,
            str(exc),
        )
        trace.set_tracer_provider(_tracer_provider)
        return

    trace.set_tracer_provider(_tracer_provider)
    logger.info("OTel tracing initialised. endpoint=%s service=%s", otlp_endpoint, service_name)


@asynccontextmanager
async def llm_span(
    tool_name: str,
    session_id: str,
    model: str = "",
) -> AsyncGenerator[trace.Span, None]:
    """
    Create a tracing span around a single LLM call.

    Args:
        tool_name: Pipeline tool issuing the call.
        session_id: SpecWeaver session identifier.
        model: Provider model name.

    Yields:
        Active OpenTelemetry span.
    """
    tracer = trace.get_tracer("specweaver.llm")
    with tracer.start_as_current_span(f"llm.{tool_name}") as span:
        span.set_attribute("tool_name", tool_name)
        span.set_attribute("session_id", session_id)
        if model:
            span.set_attribute("llm.model", model)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
