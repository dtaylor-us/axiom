"""Tests for app.observability.tracing module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.observability.tracing import (
    get_tracer,
    llm_span,
    pipeline_span,
    setup_tracing,
)


class TestSetupTracing:
    """Tests for the setup_tracing() initialiser."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        """Reset the module-level provider between tests."""
        import app.observability.tracing as mod
        original = mod._tracer_provider
        mod._tracer_provider = None
        yield
        mod._tracer_provider = original

    @patch("app.observability.tracing.trace")
    def test_setup_creates_provider(self, mock_trace):
        """setup_tracing() creates a TracerProvider and sets it globally."""
        setup_tracing()
        mock_trace.set_tracer_provider.assert_called_once()

    @patch("app.observability.tracing.trace")
    def test_setup_is_idempotent(self, mock_trace):
        """Calling setup_tracing() twice does not re-create the provider."""
        setup_tracing()
        setup_tracing()
        # Only called once despite two setup_tracing() calls
        mock_trace.set_tracer_provider.assert_called_once()

    @patch("app.observability.tracing.OTLPSpanExporter")
    @patch("app.observability.tracing.trace")
    def test_setup_uses_no_exporter_when_env_is_unset(self, mock_trace, mock_exp):
        """setup_tracing() does not export when endpoint is unset."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            setup_tracing()
        mock_exp.assert_not_called()


class TestGetTracer:
    """Tests for the get_tracer() helper."""

    def test_returns_tracer_object(self):
        """get_tracer() returns an OTel tracer (possibly no-op)."""
        tracer = get_tracer("test_module")
        assert tracer is not None


class TestPipelineSpan:
    """Tests for the pipeline_span() async context manager."""

    async def test_creates_span_with_attributes(self):
        """pipeline_span() sets stage, conversation_id, and iteration."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = lambda s: mock_span
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.observability.tracing.get_tracer", return_value=mock_tracer):
            async with pipeline_span("req_parsing", "conv-1", iteration=1) as span:
                pass

        mock_tracer.start_as_current_span.assert_called_once_with("pipeline.req_parsing")
        mock_span.set_attribute.assert_any_call("stage", "req_parsing")
        mock_span.set_attribute.assert_any_call("conversation_id", "conv-1")
        mock_span.set_attribute.assert_any_call("iteration", 1)

    async def test_records_exception_on_error(self):
        """pipeline_span() calls record_exception and sets ERROR status on failure."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = lambda s: mock_span
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.observability.tracing.get_tracer", return_value=mock_tracer):
            with pytest.raises(ValueError, match="boom"):
                async with pipeline_span("failing_stage", "conv-2") as span:
                    raise ValueError("boom")

        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()


class TestLlmSpan:
    """Tests for the llm_span() async context manager."""

    async def test_creates_span_with_tool_and_model(self):
        """llm_span() sets tool_name, conversation_id, and model."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = lambda s: mock_span
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.observability.tracing.get_tracer", return_value=mock_tracer):
            async with llm_span("requirement_parser", "conv-3", model="gpt-4o") as span:
                pass

        mock_tracer.start_as_current_span.assert_called_once_with("llm.requirement_parser")
        mock_span.set_attribute.assert_any_call("tool_name", "requirement_parser")
        mock_span.set_attribute.assert_any_call("conversation_id", "conv-3")
        mock_span.set_attribute.assert_any_call("llm.model", "gpt-4o")

    async def test_omits_model_when_empty(self):
        """llm_span() does not set llm.model when model is empty string."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = lambda s: mock_span
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.observability.tracing.get_tracer", return_value=mock_tracer):
            async with llm_span("some_tool", "conv-4") as span:
                pass

        set_attrs = {call.args[0] for call in mock_span.set_attribute.call_args_list}
        assert "llm.model" not in set_attrs

    async def test_records_exception_on_error(self):
        """llm_span() records exception and sets ERROR status on failure."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = lambda s: mock_span
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.observability.tracing.get_tracer", return_value=mock_tracer):
            with pytest.raises(RuntimeError, match="fail"):
                async with llm_span("broken_tool", "conv-5") as span:
                    raise RuntimeError("fail")

        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()
