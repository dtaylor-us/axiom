"""Tests for guarded OpenTelemetry configuration."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from app.observability import configure_telemetry
from app.observability.metrics import get_meter
from app.observability.tracing import get_tracer


def test_configure_telemetry_uses_noop_providers_when_endpoint_is_empty() -> None:
    """configure_telemetry does not create OTLP exporters when endpoint is empty."""
    _reset_observability_state()

    with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": ""}, clear=False):
        with patch("app.observability.tracing.OTLPSpanExporter") as span_exporter:
            with patch("app.observability.metrics.OTLPMetricExporter") as metric_exporter:
                configure_telemetry()

    span_exporter.assert_not_called()
    metric_exporter.assert_not_called()


def test_configure_telemetry_uses_noop_providers_when_sdk_disabled() -> None:
    """configure_telemetry does not create exporters when OTEL_SDK_DISABLED=true."""
    _reset_observability_state()

    with patch.dict(
        os.environ,
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://jaeger:4317",
            "OTEL_SDK_DISABLED": "true",
        },
        clear=False,
    ):
        with patch("app.observability.tracing.OTLPSpanExporter") as span_exporter:
            with patch("app.observability.metrics.OTLPMetricExporter") as metric_exporter:
                configure_telemetry()

    span_exporter.assert_not_called()
    metric_exporter.assert_not_called()


def test_configure_telemetry_configures_otlp_when_endpoint_is_set() -> None:
    """configure_telemetry creates trace and metric exporters for an endpoint."""
    _reset_observability_state()

    with patch.dict(
        os.environ,
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://jaeger:4317",
            "OTEL_SDK_DISABLED": "false",
        },
        clear=False,
    ):
        with patch("app.observability.tracing.OTLPSpanExporter") as span_exporter:
            with patch("app.observability.metrics.OTLPMetricExporter") as metric_exporter:
                configure_telemetry()

    span_exporter.assert_called_once()
    metric_exporter.assert_called_once()


def test_configure_telemetry_falls_back_to_noop_on_otlp_config_error() -> None:
    """configure_telemetry handles exporter setup errors without raising."""
    _reset_observability_state()

    with patch.dict(
        os.environ,
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://jaeger:4317",
            "OTEL_SDK_DISABLED": "false",
        },
        clear=False,
    ):
        with patch(
            "app.observability.tracing.OTLPSpanExporter",
            side_effect=RuntimeError("trace failed"),
        ):
            with patch(
                "app.observability.metrics.OTLPMetricExporter",
                side_effect=RuntimeError("metric failed"),
            ):
                configure_telemetry()

    assert get_tracer("test") is not None


def test_get_tracer_returns_tracer_regardless_of_configuration() -> None:
    """get_tracer returns a tracer even when no exporter is configured."""
    _reset_observability_state()

    tracer = get_tracer("test")

    assert tracer is not None


def test_get_meter_returns_meter_regardless_of_configuration() -> None:
    """get_meter returns a meter even when no exporter is configured."""
    _reset_observability_state()

    meter = get_meter("test")

    assert meter is not None


def _reset_observability_state() -> None:
    """Reset observability module globals for isolated setup tests."""
    import app.observability.metrics as metrics_module
    import app.observability.tracing as tracing_module

    tracing_module._tracer_provider = None
    metrics_module._meter_provider = None
    metrics_module._active_runs_gauge = None
    metrics_module._token_counter = None
    metrics_module._stage_duration = None
