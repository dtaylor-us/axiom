"""
Custom OpenTelemetry metrics for the AI Architect Agent.

Exposes three metrics:
    active_pipeline_runs  — gauge: pipelines currently running
                            (used by AKS HPA for agent autoscaling)
    llm_tokens_total      — counter: cumulative tokens by stage and model
    stage_duration_seconds — histogram: time per pipeline stage

All metrics are labelled with service_name from OTEL_SERVICE_NAME.
"""

from __future__ import annotations

import logging
import os

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)

logger = logging.getLogger(__name__)

_meter_provider: MeterProvider | None = None
_active_runs_gauge = None
_token_counter = None
_stage_duration = None


def setup_metrics() -> None:
    """Initialise the global MeterProvider.

    Called once at application startup alongside setup_tracing().
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _meter_provider, _active_runs_gauge
    global _token_counter, _stage_duration

    if _meter_provider is not None:
        return

    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )

    exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
    # Export every 15 seconds — fast enough for local dev,
    # not so fast that it overwhelms a production collector.
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=15_000
    )
    _meter_provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(_meter_provider)

    meter = metrics.get_meter("ai_architect.agent")

    _active_runs_gauge = meter.create_up_down_counter(
        name="active_pipeline_runs",
        description="Number of pipeline runs currently executing",
        unit="1",
    )
    _token_counter = meter.create_counter(
        name="llm_tokens_total",
        description="Total LLM tokens consumed",
        unit="tokens",
    )
    _stage_duration = meter.create_histogram(
        name="stage_duration_seconds",
        description="Time taken per pipeline stage",
        unit="s",
    )

    logger.info("OTel metrics initialised. endpoint=%s", otlp_endpoint)


def increment_active_runs() -> None:
    """Increment the active pipeline runs gauge by one."""
    if _active_runs_gauge:
        _active_runs_gauge.add(1)


def decrement_active_runs() -> None:
    """Decrement the active pipeline runs gauge by one."""
    if _active_runs_gauge:
        _active_runs_gauge.add(-1)


def record_tokens(
    stage: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Record input and output token counts for a single LLM call."""
    if _token_counter:
        _token_counter.add(
            input_tokens,
            {"stage": stage, "model": model, "direction": "input"},
        )
        _token_counter.add(
            output_tokens,
            {"stage": stage, "model": model, "direction": "output"},
        )


def record_stage_duration(stage: str, duration_seconds: float) -> None:
    """Record the wall-clock duration of a pipeline stage."""
    if _stage_duration:
        _stage_duration.record(duration_seconds, {"stage": stage})
