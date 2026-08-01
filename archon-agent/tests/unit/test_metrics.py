"""Tests for app.observability.metrics module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.observability.metrics import (
    decrement_active_runs,
    increment_active_runs,
    record_stage_duration,
    record_tokens,
    setup_metrics,
)


class TestSetupMetrics:
    """Tests for the setup_metrics() initialiser."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        """Reset module-level state between tests."""
        import app.observability.metrics as mod
        original_mp = mod._meter_provider
        original_gauge = mod._active_runs_gauge
        original_counter = mod._token_counter
        original_hist = mod._stage_duration
        mod._meter_provider = None
        mod._active_runs_gauge = None
        mod._token_counter = None
        mod._stage_duration = None
        yield
        mod._meter_provider = original_mp
        mod._active_runs_gauge = original_gauge
        mod._token_counter = original_counter
        mod._stage_duration = original_hist

    @patch("app.observability.metrics.metrics")
    def test_setup_creates_meter_provider(self, mock_metrics):
        """setup_metrics() creates a MeterProvider and registers instruments."""
        mock_meter = MagicMock()
        mock_metrics.get_meter.return_value = mock_meter
        mock_meter.create_up_down_counter.return_value = MagicMock()
        mock_meter.create_counter.return_value = MagicMock()
        mock_meter.create_histogram.return_value = MagicMock()

        setup_metrics()

        mock_metrics.set_meter_provider.assert_called_once()
        mock_meter.create_up_down_counter.assert_called_once()
        mock_meter.create_counter.assert_called_once()
        mock_meter.create_histogram.assert_called_once()

    @patch("app.observability.metrics.metrics")
    def test_setup_is_idempotent(self, mock_metrics):
        """Calling setup_metrics() twice creates instruments only once."""
        mock_meter = MagicMock()
        mock_metrics.get_meter.return_value = mock_meter
        mock_meter.create_up_down_counter.return_value = MagicMock()
        mock_meter.create_counter.return_value = MagicMock()
        mock_meter.create_histogram.return_value = MagicMock()

        setup_metrics()
        setup_metrics()

        mock_metrics.set_meter_provider.assert_called_once()


class TestActiveRuns:
    """Tests for increment/decrement active runs helpers."""

    def test_increment_calls_add_with_positive(self):
        """increment_active_runs() calls add(1) on the gauge."""
        import app.observability.metrics as mod
        mock_gauge = MagicMock()
        mod._active_runs_gauge = mock_gauge
        try:
            increment_active_runs()
            mock_gauge.add.assert_called_once_with(1)
        finally:
            mod._active_runs_gauge = None

    def test_decrement_calls_add_with_negative(self):
        """decrement_active_runs() calls add(-1) on the gauge."""
        import app.observability.metrics as mod
        mock_gauge = MagicMock()
        mod._active_runs_gauge = mock_gauge
        try:
            decrement_active_runs()
            mock_gauge.add.assert_called_once_with(-1)
        finally:
            mod._active_runs_gauge = None

    def test_increment_is_noop_when_not_setup(self):
        """increment_active_runs() does nothing when metrics not initialised."""
        # Should not raise — just a no-op
        increment_active_runs()

    def test_decrement_is_noop_when_not_setup(self):
        """decrement_active_runs() does nothing when metrics not initialised."""
        decrement_active_runs()


class TestRecordTokens:
    """Tests for the record_tokens() helper."""

    def test_records_input_and_output_with_labels(self):
        """record_tokens() calls add() twice with correct stage/model/direction."""
        import app.observability.metrics as mod
        mock_counter = MagicMock()
        mod._token_counter = mock_counter
        try:
            record_tokens("req_parsing", "gpt-4o", 100, 50)

            assert mock_counter.add.call_count == 2
            # First call — input tokens
            args_in = mock_counter.add.call_args_list[0]
            assert args_in[0][0] == 100
            assert args_in[0][1]["direction"] == "input"
            assert args_in[0][1]["stage"] == "req_parsing"
            assert args_in[0][1]["model"] == "gpt-4o"

            # Second call — output tokens
            args_out = mock_counter.add.call_args_list[1]
            assert args_out[0][0] == 50
            assert args_out[0][1]["direction"] == "output"
        finally:
            mod._token_counter = None

    def test_noop_when_not_setup(self):
        """record_tokens() does nothing when metrics not initialised."""
        record_tokens("req_parsing", "gpt-4o", 100, 50)


class TestRecordStageDuration:
    """Tests for the record_stage_duration() helper."""

    def test_records_duration_with_stage_label(self):
        """record_stage_duration() calls record() on the histogram."""
        import app.observability.metrics as mod
        mock_hist = MagicMock()
        mod._stage_duration = mock_hist
        try:
            record_stage_duration("diagram_generation", 3.14)
            mock_hist.record.assert_called_once_with(
                3.14, {"stage": "diagram_generation"}
            )
        finally:
            mod._stage_duration = None

    def test_noop_when_not_setup(self):
        """record_stage_duration() does nothing when metrics not initialised."""
        record_stage_duration("some_stage", 1.0)
