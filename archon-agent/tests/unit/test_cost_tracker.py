"""Tests for app.llm.cost_tracker module."""

from __future__ import annotations

import pytest

from app.llm.cost_tracker import (
    PipelineTokenUsage,
    StageTokenUsage,
    get_tracker,
    start_tracking,
    track_tokens,
)


class TestStageTokenUsage:
    """Tests for the StageTokenUsage dataclass."""

    def test_total_tokens(self):
        """total_tokens is sum of input and output."""
        usage = StageTokenUsage(
            stage="req_parsing", model="gpt-4o",
            input_tokens=100, output_tokens=50,
        )
        assert usage.total_tokens == 150

    def test_estimated_cost_gpt4o(self):
        """Cost estimate uses gpt-4o pricing ($0.0025/1K in, $0.01/1K out)."""
        usage = StageTokenUsage(
            stage="req_parsing", model="gpt-4o",
            input_tokens=1000, output_tokens=1000,
        )
        # 1K * 0.0025 + 1K * 0.01 = 0.0125
        assert abs(usage.estimated_cost_usd - 0.0125) < 1e-6

    def test_estimated_cost_gpt4o_mini(self):
        """Cost estimate uses gpt-4o-mini pricing."""
        usage = StageTokenUsage(
            stage="req_parsing", model="gpt-4o-mini",
            input_tokens=1000, output_tokens=1000,
        )
        # 1K * 0.00015 + 1K * 0.0006 = 0.00075
        assert abs(usage.estimated_cost_usd - 0.00075) < 1e-6

    def test_estimated_cost_unknown_model_uses_default(self):
        """Unknown models fall back to default pricing."""
        usage = StageTokenUsage(
            stage="req_parsing", model="some-future-model",
            input_tokens=1000, output_tokens=1000,
        )
        # Default: 1K * 0.003 + 1K * 0.015 = 0.018
        assert abs(usage.estimated_cost_usd - 0.018) < 1e-6

    def test_to_dict_structure(self):
        """to_dict() returns all expected keys."""
        usage = StageTokenUsage(
            stage="diagram", model="gpt-4o",
            input_tokens=200, output_tokens=100,
        )
        d = usage.to_dict()
        assert d["stage"] == "diagram"
        assert d["model"] == "gpt-4o"
        assert d["input_tokens"] == 200
        assert d["output_tokens"] == 100
        assert d["total_tokens"] == 300
        assert "estimated_cost_usd" in d

    def test_zero_tokens_gives_zero_cost(self):
        """No tokens consumed means zero cost."""
        usage = StageTokenUsage(stage="empty", model="gpt-4o")
        assert usage.total_tokens == 0
        assert usage.estimated_cost_usd == 0.0


class TestPipelineTokenUsage:
    """Tests for the PipelineTokenUsage aggregate dataclass."""

    def test_record_creates_new_stage(self):
        """record() creates a new StageTokenUsage entry."""
        tracker = PipelineTokenUsage()
        tracker.record("req_parsing", "gpt-4o", 100, 50)

        assert "req_parsing" in tracker.stages
        assert tracker.stages["req_parsing"].input_tokens == 100
        assert tracker.stages["req_parsing"].output_tokens == 50

    def test_record_accumulates_on_same_stage(self):
        """Multiple record() calls for the same stage sum tokens."""
        tracker = PipelineTokenUsage()
        tracker.record("req_parsing", "gpt-4o", 100, 50)
        tracker.record("req_parsing", "gpt-4o", 200, 100)

        assert tracker.stages["req_parsing"].input_tokens == 300
        assert tracker.stages["req_parsing"].output_tokens == 150

    def test_total_input_tokens_aggregates(self):
        """total_input_tokens sums across all stages."""
        tracker = PipelineTokenUsage()
        tracker.record("stage_a", "gpt-4o", 100, 50)
        tracker.record("stage_b", "gpt-4o", 200, 75)

        assert tracker.total_input_tokens == 300

    def test_total_output_tokens_aggregates(self):
        """total_output_tokens sums across all stages."""
        tracker = PipelineTokenUsage()
        tracker.record("stage_a", "gpt-4o", 100, 50)
        tracker.record("stage_b", "gpt-4o", 200, 75)

        assert tracker.total_output_tokens == 125

    def test_total_tokens_property(self):
        """total_tokens is sum of all input + output."""
        tracker = PipelineTokenUsage()
        tracker.record("s1", "gpt-4o", 100, 50)
        tracker.record("s2", "gpt-4o-mini", 200, 100)

        assert tracker.total_tokens == 450

    def test_estimated_total_cost(self):
        """estimated_total_cost_usd sums across stages."""
        tracker = PipelineTokenUsage()
        tracker.record("s1", "gpt-4o", 1000, 1000)
        tracker.record("s2", "gpt-4o-mini", 1000, 1000)

        expected = 0.0125 + 0.00075  # gpt-4o + gpt-4o-mini
        assert abs(tracker.estimated_total_cost_usd - expected) < 1e-6

    def test_to_dict_format(self):
        """to_dict() includes stages dict and all totals."""
        tracker = PipelineTokenUsage()
        tracker.record("s1", "gpt-4o", 100, 50)

        d = tracker.to_dict()
        assert "stages" in d
        assert "s1" in d["stages"]
        assert d["total_input_tokens"] == 100
        assert d["total_output_tokens"] == 50
        assert d["total_tokens"] == 150
        assert "estimated_total_cost_usd" in d

    def test_empty_tracker_has_zero_totals(self):
        """Empty tracker returns zero for all aggregates."""
        tracker = PipelineTokenUsage()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_tokens == 0
        assert tracker.estimated_total_cost_usd == 0.0


class TestContextVarTracking:
    """Tests for contextvars-based tracking functions."""

    def test_start_tracking_returns_fresh_tracker(self):
        """start_tracking() creates and binds a new PipelineTokenUsage."""
        tracker = start_tracking()
        assert isinstance(tracker, PipelineTokenUsage)
        assert len(tracker.stages) == 0

    def test_get_tracker_returns_active_tracker(self):
        """get_tracker() returns the same tracker that start_tracking() created."""
        tracker = start_tracking()
        assert get_tracker() is tracker

    def test_track_tokens_records_into_active_tracker(self):
        """track_tokens() delegates to the active tracker."""
        tracker = start_tracking()
        track_tokens("req_parsing", "gpt-4o", 100, 50)

        assert tracker.total_input_tokens == 100
        assert tracker.total_output_tokens == 50
        assert "req_parsing" in tracker.stages

    def test_track_tokens_noop_without_active_tracker(self):
        """track_tokens() is a no-op when no tracker is active."""
        # Reset the contextvar to ensure no tracker
        from app.llm.cost_tracker import _current_usage
        token = _current_usage.set(None)
        try:
            track_tokens("some_stage", "gpt-4o", 100, 50)
            # Should not raise
        finally:
            _current_usage.reset(token)

    def test_get_tracker_returns_none_when_inactive(self):
        """get_tracker() returns None when no pipeline run is active."""
        from app.llm.cost_tracker import _current_usage
        token = _current_usage.set(None)
        try:
            assert get_tracker() is None
        finally:
            _current_usage.reset(token)
