"""
OpenTelemetry tracing setup for the AI Architect Agent.

Initialises a global TracerProvider that exports spans to an
OTLP endpoint (Jaeger locally, Azure Monitor in production).

Usage:
    from app.observability.tracing import get_tracer, pipeline_span

    tracer = get_tracer(__name__)

    async with pipeline_span("requirement_parsing", ctx.conversation_id):
        result = await tool.run(ctx)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None


def setup_tracing() -> None:
    """Initialise the global TracerProvider.

    Called once at application startup in the FastAPI lifespan.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    is_otel_disabled = os.getenv("OTEL_SDK_DISABLED", "").lower() == "true"
    service_name = os.getenv(
        "OTEL_SERVICE_NAME", "archon-agent"
    )

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

    logger.info(
        "OTel tracing initialised. endpoint=%s service=%s",
        otlp_endpoint, service_name,
    )


def get_tracer(name: str) -> trace.Tracer:
    """Return a named tracer.

    Call setup_tracing() first. Falls back to a no-op tracer if
    setup has not been called.
    """
    return trace.get_tracer(name)


@asynccontextmanager
async def pipeline_span(
    stage_name: str,
    conversation_id: str,
    iteration: int = 0,
) -> AsyncGenerator[trace.Span, None]:
    """Context manager that creates a span for a pipeline stage.

    Sets standard attributes: stage, conversation_id, iteration.

    Args:
        stage_name: Name of the pipeline stage.
        conversation_id: Conversation ID for correlation.
        iteration: Pipeline iteration number (0-based).

    Yields:
        The active OTel span.
    """
    tracer = get_tracer("ai_architect.pipeline")
    with tracer.start_as_current_span(f"pipeline.{stage_name}") as span:
        span.set_attribute("stage", stage_name)
        span.set_attribute("conversation_id", conversation_id)
        span.set_attribute("iteration", iteration)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise


@asynccontextmanager
async def llm_span(
    tool_name: str,
    conversation_id: str,
    model: str = "",
) -> AsyncGenerator[trace.Span, None]:
    """Context manager for an LLM call span.

    Records tool_name, conversation_id, and optional model as
    span attributes. Token counts should be set by the caller
    after the LLM response is received.

    Args:
        tool_name: Name of the tool making the LLM call.
        conversation_id: Conversation ID for correlation.
        model: Optional LLM model identifier.

    Yields:
        The active OTel span — caller sets llm.input_tokens
        and llm.output_tokens on it.
    """
    tracer = get_tracer("ai_architect.llm")
    with tracer.start_as_current_span(f"llm.{tool_name}") as span:
        span.set_attribute("tool_name", tool_name)
        span.set_attribute("conversation_id", conversation_id)
        if model:
            span.set_attribute("llm.model", model)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            raise
