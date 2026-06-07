"""Base tool abstractions for SpecWeaver pipeline stages."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from app.llm.client import LLMCallException, LLMClient, set_llm_context
from app.pipeline.context import SpecWeaverContext

logger = logging.getLogger(__name__)


class ToolExecutionException(Exception):
    """Raised when a pipeline tool fails during execution."""


class BaseTool(ABC):
    """Abstract base class for SpecWeaver pipeline tools."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    @abstractmethod
    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Execute the tool against the given context."""
        ...

    async def execute(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Set LLM tracing context, then delegate to run()."""
        set_llm_context(self.name(), context.session_id)
        return await self.run(context)

    def name(self) -> str:
        """Return the class name in snake_case."""
        class_name = self.__class__.__name__
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    async def attempt_repair(
        self,
        original_prompt: str,
        failed_response: str,
        error_description: str,
        output_schema: dict | None = None,
        schema_name: str = "tool_output",
        stage_name: str | None = None,
    ) -> str:
        """Make one targeted repair attempt after a validation failure."""
        truncated_response = failed_response[:500]
        if len(failed_response) > 500:
            truncated_response += f"... [truncated, total={len(failed_response)} chars]"

        repair_prompt = (
            f"The previous response failed validation with this error:\n"
            f"{error_description}\n\n"
            f"The failed response was:\n"
            f"{truncated_response}\n\n"
            f"Return a corrected version that fixes only the identified "
            f"error. Do not change any other part of the output. "
            f"Return valid JSON only with no markdown fences.\n\n"
            f"Original task:\n{original_prompt}"
        )

        logger.info(
            "Attempting repair. tool=%s error=%s",
            self.__class__.__name__,
            error_description[:100],
        )

        try:
            return await self.llm_client.complete(
                repair_prompt,
                response_format="json",
                output_schema=output_schema,
                schema_name=schema_name,
                stage_name=stage_name or schema_name,
            )
        except LLMCallException as exc:
            raise ToolExecutionException(
                f"Repair LLM call failed for {self.__class__.__name__}: {exc}"
            ) from exc
