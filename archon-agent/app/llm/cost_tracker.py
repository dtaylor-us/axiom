"""Per-pipeline LLM cost tracking.

Accumulates token usage across all stages and review nodes within
a single pipeline run. Thread-safe via contextvars — each async task
gets its own tracker instance.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Approximate pricing per 1 K tokens (USD) — update when models change.
# These are conservative estimates used for relative cost comparison only.
_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.0100},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}
_DEFAULT_COST = {"input": 0.003, "output": 0.015}


@dataclass
class StageTokenUsage:
    """Token counts for a single stage or review node."""

    stage: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        rates = _COST_PER_1K.get(self.model, _DEFAULT_COST)
        return (
            (self.input_tokens / 1_000) * rates["input"]
            + (self.output_tokens / 1_000) * rates["output"]
        )

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class PipelineTokenUsage:
    """Aggregate token usage for an entire pipeline run."""

    stages: dict[str, StageTokenUsage] = field(default_factory=dict)

    def record(
        self,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Accumulate tokens for *stage*. Multiple calls per stage are summed."""
        if stage not in self.stages:
            self.stages[stage] = StageTokenUsage(stage=stage, model=model)
        entry = self.stages[stage]
        entry.input_tokens += input_tokens
        entry.output_tokens += output_tokens
        # Keep the most recent model name if it changes mid-stage
        if model:
            entry.model = model

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.stages.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.stages.values())

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def estimated_total_cost_usd(self) -> float:
        return sum(s.estimated_cost_usd for s in self.stages.values())

    def to_dict(self) -> dict:
        return {
            "stages": {
                name: s.to_dict() for name, s in self.stages.items()
            },
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_total_cost_usd": round(
                self.estimated_total_cost_usd, 6
            ),
        }


# ── Context var for per-pipeline tracking ────────────────────────

_current_usage: ContextVar[PipelineTokenUsage | None] = ContextVar(
    "_current_usage", default=None
)


def start_tracking() -> PipelineTokenUsage:
    """Create a fresh tracker for a new pipeline run and bind it to contextvars."""
    tracker = PipelineTokenUsage()
    _current_usage.set(tracker)
    return tracker


def get_tracker() -> PipelineTokenUsage | None:
    """Return the tracker for the current task (None when not inside a pipeline)."""
    return _current_usage.get()


def track_tokens(
    stage: str, model: str, input_tokens: int, output_tokens: int
) -> None:
    """Record tokens into the current run's tracker (no-op if no tracker is active)."""
    tracker = _current_usage.get()
    if tracker is not None:
        tracker.record(stage, model, input_tokens, output_tokens)
