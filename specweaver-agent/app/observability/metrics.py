"""OpenTelemetry metrics setup for the SpecWeaver agent."""

from __future__ import annotations

import logging
import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

logger = logging.getLogger(__name__)
_meter_provider: MeterProvider | None = None
_token_counter = None


def setup_metrics() -> None:
    """Initialise the global meter provider once."""
    global _meter_provider, _token_counter
    if _meter_provider is not None:
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    is_otel_disabled = os.getenv("OTEL_SDK_DISABLED", "").lower() == "true"
    metric_readers = []

    if is_otel_disabled or not otlp_endpoint:
        logger.info(
            "OTel metrics using no-op provider. Set "
            "OTEL_EXPORTER_OTLP_ENDPOINT to enable metric export."
        )
    else:
        try:
            exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
            metric_readers.append(
                PeriodicExportingMetricReader(exporter, export_interval_millis=15_000)
            )
        except Exception as exc:
            logger.warning(
                "OTel metrics exporter setup failed. endpoint=%s error=%s. "
                "Falling back to no-op provider.",
                otlp_endpoint,
                str(exc),
            )

    _meter_provider = MeterProvider(metric_readers=metric_readers)
    metrics.set_meter_provider(_meter_provider)
    meter = metrics.get_meter("specweaver.agent")
    _token_counter = meter.create_counter(
        name="llm_tokens_total",
        description="Total LLM tokens consumed",
        unit="tokens",
    )


def record_tokens(
    stage: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """
    Record token counts for a single LLM call.

    Args:
        stage: Pipeline stage.
        model: Provider model.
        input_tokens: Input token count.
        output_tokens: Output token count.
    """
    if _token_counter:
        _token_counter.add(input_tokens, {"stage": stage, "model": model, "direction": "input"})
        _token_counter.add(output_tokens, {"stage": stage, "model": model, "direction": "output"})
