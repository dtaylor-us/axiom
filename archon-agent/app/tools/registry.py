from __future__ import annotations

from app.llm.client import LLMClient
from app.memory.store import MemoryStore
from app.tools.adl_generator import ADLGeneratorV2Tool
from app.tools.architecture_generator import ArchitectureGeneratorTool
from app.tools.buy_vs_build_analyzer import BuyVsBuildAnalyzerTool
from app.tools.base import BaseTool
from app.tools.challenge_engine import RequirementChallengeEngineTool
from app.tools.characteristic_reasoner import CharacteristicReasoningEngineTool
from app.tools.conflict_analyzer import CharacteristicConflictAnalyzerTool
from app.tools.diagram_generator import DiagramGeneratorTool
from app.tools.fmea_analyzer import FMEAPlusTool
from app.tools.requirement_parser import RequirementParserTool
from app.tools.scenario_modeler import ScenarioModelerTool
from app.tools.tactics_advisor import TacticsAdvisorTool
from app.tools.trade_off_engine import TradeOffEngineTool
from app.tools.weakness_analyzer import WeaknessAnalyzerTool


def build_registry(
    llm_client: LLMClient,
    memory_store: MemoryStore,
) -> dict[str, BaseTool]:
    """Build and return the tool registry mapping tool names to instances.

    Args:
        llm_client: The shared LLM client instance.
        memory_store: The shared Qdrant-backed memory store.

    Returns:
        Dict mapping tool name strings to initialized tool instances.
    """
    return {
        "requirement_parser": RequirementParserTool(llm_client),
        "challenge_engine": RequirementChallengeEngineTool(llm_client),
        "scenario_modeler": ScenarioModelerTool(llm_client),
        "characteristic_reasoner": CharacteristicReasoningEngineTool(llm_client),
        "tactics_advisor": TacticsAdvisorTool(llm_client),
        "conflict_analyzer": CharacteristicConflictAnalyzerTool(llm_client),
        "architecture_generator": ArchitectureGeneratorTool(llm_client, memory_store),
        "buy_vs_build_analyzer": BuyVsBuildAnalyzerTool(llm_client),
        "diagram_generator": DiagramGeneratorTool(llm_client),
        "trade_off_engine": TradeOffEngineTool(llm_client),
        "adl_generator": ADLGeneratorV2Tool(llm_client),
        "weakness_analyzer": WeaknessAnalyzerTool(llm_client),
        "fmea_analyzer": FMEAPlusTool(llm_client),
    }
