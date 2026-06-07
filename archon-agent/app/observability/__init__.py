"""
Observability package for the AI Architect Agent.

Provides OpenTelemetry tracing (spans) and custom metrics
(active runs, token counters, stage duration). Initialised
once at application startup before any other component.
"""

import logging

from .tracing import setup_tracing, get_tracer, pipeline_span, llm_span
from .metrics import (
    setup_metrics, get_meter, increment_active_runs, decrement_active_runs,
    record_tokens, record_stage_duration,
)

logger = logging.getLogger(__name__)


def configure_telemetry() -> None:
    """
    Configure tracing and metrics from environment.

    When OTEL_EXPORTER_OTLP_ENDPOINT is empty, both providers are initialized
    without exporters so local development does not emit repeated Jaeger errors.
    """
    setup_tracing()
    setup_metrics()
    logger.info("OpenTelemetry configured")


__all__ = [
    "configure_telemetry", "setup_tracing", "get_tracer", "pipeline_span", "llm_span",
    "setup_metrics", "get_meter", "increment_active_runs", "decrement_active_runs",
    "record_tokens", "record_stage_duration",
]
