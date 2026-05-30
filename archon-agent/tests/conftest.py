from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models import ArchitectureContext, PipelineMode


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Return an AsyncMock of LLMClient."""
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{"stub": true}')
    return llm


@pytest.fixture
def sample_requirements() -> str:
    """Return a multi-sentence requirements string suitable for all three tools."""
    return (
        "Build a real-time payment processing platform that handles 10,000 TPS. "
        "The system must integrate with Stripe and PayPal for payment gateways. "
        "It needs a fraud detection engine with sub-100ms latency. "
        "All transactions must comply with PCI-DSS Level 1 requirements. "
        "The platform should support multi-currency conversion with live exchange rates. "
        "There must be a merchant dashboard for analytics and settlement tracking. "
        "The system needs a webhook notification system for payment status updates. "
        "Disaster recovery with RPO < 1 minute and RTO < 5 minutes is required."
    )


@pytest.fixture
def base_context(sample_requirements: str) -> ArchitectureContext:
    """Return an ArchitectureContext populated with sample_requirements."""
    return ArchitectureContext(
        conversation_id="test-conv-123",
        raw_requirements=sample_requirements,
        mode=PipelineMode.AUTO,
    )
