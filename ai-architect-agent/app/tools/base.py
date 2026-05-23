from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from app.llm.client import LLMClient, LLMCallException, set_llm_context
from app.models import ArchitectureContext

logger = logging.getLogger(__name__)


class ToolExecutionException(Exception):
    """Raised when a pipeline tool fails during execution."""


class BaseTool(ABC):
    """Abstract base class for all pipeline tools."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    @abstractmethod
    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """Execute the tool against the given context.

        Args:
            context: The full pipeline context to read from and write to.

        Returns:
            The mutated ArchitectureContext with this tool's output fields populated.
        """
        ...

    async def execute(self, context: ArchitectureContext) -> ArchitectureContext:
        """Set LLM context vars for tracing/metrics, then delegate to run().

        All node functions should call execute() instead of run() directly
        so that llm_span and record_tokens record the correct tool name
        and conversation ID.
        """
        set_llm_context(self.name(), context.conversation_id)
        return await self.run(context)

    def name(self) -> str:
        """Return the class name in snake_case."""
        class_name = self.__class__.__name__
        # Remove trailing "Tool" if present for cleaner names
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    async def attempt_repair(
        self,
        original_prompt: str,
        failed_response: str,
        error_description: str,
        output_schema: dict | None = None,
        schema_name: str = "tool_output",
    ) -> str:
        """Make one targeted repair attempt after a validation failure.

        Constructs a repair prompt that includes the original task, the failed
        response (truncated to 500 chars), and the specific validation error.
        This is called at most once per stage per run — the name reflects that
        contract: one attempt, not a retry loop.

        Args:
            original_prompt: The prompt text that produced the bad response.
            failed_response: The raw LLM output that failed validation.
                Truncated to 500 chars when embedded in the repair prompt.
            error_description: The specific validation error message. Must
                contain the actual error, not a generic "something went wrong".
            output_schema: JSON schema for structured output enforcement on
                the repair call. Passed through to llm_client.complete().
            schema_name: Name for the json_schema object in the repair call.

        Returns:
            The repair response string. The caller is responsible for
            validating it — this method does not validate the output.

        Raises:
            ToolExecutionException: If the repair LLM call itself fails.
        """
        # Truncate the failed response to avoid bloating the repair prompt.
        # 500 chars is enough to show the structure problem without hitting
        # context limits on the repair call.
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
            )
        except LLMCallException as e:
            raise ToolExecutionException(
                f"Repair LLM call failed for {self.__class__.__name__}: {e}"
            ) from e
