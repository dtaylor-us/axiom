"""Unit tests for QualityAttributeWorkshopAgent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workshop.agent import QualityAttributeWorkshopAgent
from app.workshop.context import WorkshopContext, InformationGap, WorkshopTurn


async def _echo_phase(state_in: WorkshopContext, **_k: object) -> WorkshopContext:
    return state_in.model_copy(update={"workshop_phase": "business_context"})


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.complete = AsyncMock(return_value='{"facts": [], "system_name": ""}')
    return client


@pytest.fixture
def agent(mock_llm_client):
    return QualityAttributeWorkshopAgent(llm_client=mock_llm_client)


class TestProcessTurnStructure:
    @pytest.mark.asyncio
    async def test_increments_turn_number(self, agent):
        ctx = WorkshopContext(session_id="s1", user_id="u1", system_name="TestSys")
        assert ctx.current_turn == 0

        with patch.object(agent, "_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(side_effect=_echo_phase)

            updated, _ = await agent.process_turn(ctx, "hello")

        assert updated.current_turn == 1

    @pytest.mark.asyncio
    async def test_appends_input_to_raw_inputs(self, agent):
        ctx = WorkshopContext(session_id="s1", user_id="u1", system_name="TestSys")
        ctx.raw_inputs = ["first message"]

        with patch.object(agent, "_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(side_effect=_echo_phase)

            updated, _ = await agent.process_turn(ctx, "second message")

        assert updated.raw_inputs[-1] == "second message"

    def test_build_turn_response_shape(self, agent):
        ctx = WorkshopContext(session_id="s1", user_id="u1", system_name="TestSys")
        ctx.current_turn = 3
        ctx.workshop_phase = "risk_priority"
        ctx.turns = [
            WorkshopTurn(
                turn_number=3,
                user_input="hi",
                agent_response="Question here",
            ),
        ]

        response = agent._build_turn_response(ctx)

        assert "session_id" in response
        assert "agent_message" in response
        assert "workshop_phase" in response
        assert "turn_number" in response
        assert "gap_summary" in response
        assert "has_sufficient_attributes" in response
        assert response["agent_message"] == "Question here"
        assert response["turn_number"] == 3

    def test_build_turn_response_gap_summary_structure(self, agent):
        ctx = WorkshopContext(session_id="s1", user_id="u1", system_name="TestSys")
        ctx.gaps = [
            InformationGap(
                gap_id="g1",
                category="business_context",
                description="What does it do?",
                filled=False,
                priority="critical",
            ),
        ]

        response = agent._build_turn_response(ctx)
        gap_summary = response["gap_summary"]

        assert gap_summary["total"] == 1
        assert gap_summary["filled"] == 0
        assert gap_summary["completion_pct"] == 0
        assert len(gap_summary["open_gaps"]) == 1
        assert gap_summary["open_gaps"][0]["gap_id"] == "g1"


class TestProduceSummary:
    @pytest.mark.asyncio
    async def test_calls_llm_with_session_id(self, agent, mock_llm_client):
        mock_llm_client.complete = AsyncMock(
            return_value=(
                '{"session_id": "s1", "attributes": [], '
                '"completeness_score": 0.0, "workshop_summary": "", '
                '"recommended_next_steps": ""}'
            )
        )
        ctx = WorkshopContext(session_id="s1", user_id="u1", system_name="TestSys")

        result = await agent.produce_summary(ctx)

        assert result is not None
