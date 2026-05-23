"""
Architectural implication synthesiser for the Quality Attribute Workshop.

Derives architectural constraints from quality attribute scenarios,
particularly from architectural drivers identified in the utility tree.
Each implication traces to a specific scenario and states requirements
rather than mechanisms.
"""

import json
import logging

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import ArchitectureImplication, WorkshopContext

logger = logging.getLogger(__name__)

# Maximum number of implications to accept per synthesis call.
# More than this is likely hallucination padding rather than real constraints.
MAX_IMPLICATIONS = 20

PROHIBITED_MECHANISM_TERMS = {
    "async worker pool",
    "consensus protocol",
    "circuit breaker",
    "fallback handler",
    "local state store",
    "event sourcing",
    "saga pattern",
    "cqrs",
    "outbox pattern",
    "distributed lock",
    "message queue",
    "message broker",
    "load balancer",
    "api gateway",
    "service mesh",
    "kafka",
    "redis",
    "rabbitmq",
    "postgresql",
    "kubernetes",
    "docker",
}


class ImplicationSynthesiser:
    """
    Derives architectural implications from driver scenarios in the utility tree.

    Architectural implications are requirements that the architecture must
    satisfy, derived from specific scenarios. They avoid mechanism names so
    that the downstream reasoning engine can evaluate solution options.

    Synthesis is skipped when no utility tree has been generated yet — the
    utility tree identifies which scenarios are architectural drivers, and
    driver traceability is required for each implication.
    """

    def __init__(self, llm: LLMClient) -> None:
        """
        Args:
            llm: LLM client used to call the synthesise_implications prompt.
        """
        self._llm = llm

    async def synthesise(
        self, context: WorkshopContext
    ) -> list[ArchitectureImplication]:
        """
        Synthesise architectural implications from the current session state.

        Returns an empty list when no utility tree exists yet.  Returns the
        existing implications list unchanged when generation fails so that
        partial state is preserved rather than discarded.

        Args:
            context: WorkshopContext after utility tree generation.

        Returns:
            List of ArchitectureImplication instances, or the existing list
            on failure, or an empty list when no tree is available.
        """
        if context.utility_tree is None:
            logger.info(
                "Implication synthesis skipped — no utility tree yet. session=%s",
                context.session_id,
            )
            return context.architecture_implications

        # Extract driver scenarios — those listed as architectural drivers in the tree.
        driver_ids = set(context.utility_tree.architectural_drivers)
        driver_scenarios = [
            s for s in context.deduplicated_scenarios
            if s.scenario_id in driver_ids
        ]

        if not driver_scenarios:
            logger.info(
                "No driver scenarios identified in utility tree. session=%s",
                context.session_id,
            )
            return context.architecture_implications

        prompt = load_prompt(
            "workshop/synthesise_implications",
            system_name=context.system_name,
            driver_scenarios=[s.model_dump() for s in driver_scenarios],
            all_scenarios=[s.model_dump() for s in context.deduplicated_scenarios],
            attributes=[a.model_dump() for a in context.attributes],
        )

        try:
            raw = await self._llm.complete(prompt, response_format="json")
            parsed = json.loads(raw)
        except Exception:
            logger.error(
                "Implication synthesis LLM call failed. session=%s turn=%d",
                context.session_id,
                context.current_turn,
                exc_info=True,
            )
            # Preserve existing implications on failure.
            return context.architecture_implications

        raw_implications = parsed.get("implications", [])[:MAX_IMPLICATIONS]
        implications = [
            ArchitectureImplication(**imp) for imp in raw_implications
        ]

        for implication in implications:
            warning = self._validate_implication(implication)
            if warning:
                logger.warning(
                    "IMPLICATION_MECHANISM_VIOLATION: %s session=%s",
                    warning,
                    context.session_id,
                )

        logger.info(
            "Implication synthesis complete. session=%s turn=%d count=%d",
            context.session_id,
            context.current_turn,
            len(implications),
        )
        return implications

    def _validate_implication(
        self, implication: ArchitectureImplication
    ) -> str | None:
        """
        Return a warning when an implication contains mechanism terms.

        The implication is not rejected because preserving visible workshop
        output is better than dropping all generated requirements. The warning
        gives the next prompt iteration a concrete failure to correct.

        Args:
            implication: Architecture implication returned by the LLM.

        Returns:
            Warning text when prohibited mechanism terms are present, otherwise
            None.
        """
        text = implication.implication.lower()
        found = [
            term for term in PROHIBITED_MECHANISM_TERMS
            if term in text
        ]
        if found:
            return (
                f"Implication {implication.implication_id} "
                f"contains mechanism terms: {found}. "
                f"Rephrase as a requirement, not a solution."
            )
        return None
