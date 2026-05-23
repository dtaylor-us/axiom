from __future__ import annotations

import logging
import os
from contextvars import ContextVar

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.messages import HumanMessage
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from app.observability import llm_span, record_tokens
from app.llm.cost_tracker import track_tokens

logger = logging.getLogger(__name__)

# Context vars for thread-safe per-request state — set by each tool
# before calling complete() so span attributes are accurate.
_current_tool_name: ContextVar[str] = ContextVar(
    "_current_tool_name", default="unknown"
)
_current_conversation_id: ContextVar[str] = ContextVar(
    "_current_conversation_id", default="unknown"
)


def set_llm_context(tool_name: str, conversation_id: str) -> None:
    """Set contextvar state for the current LLM call.

    Called by each tool's run() method before invoking
    llm_client.complete() so that spans and metrics carry
    the correct tool name and conversation ID.
    """
    _current_tool_name.set(tool_name)
    _current_conversation_id.set(conversation_id)


class LLMCallException(Exception):
    """Raised when the LLM call fails after all retries are exhausted."""


class LLMClient:
    """Unified LLM client supporting OpenAI and Azure OpenAI providers."""

    def __init__(self) -> None:
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "azure":
            self._llm = AzureChatOpenAI(
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                api_version="2024-06-01",
                temperature=0.2,
            )
            self.model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            logger.info("LLMClient initialized with Azure OpenAI provider")
        else:
            self._llm = ChatOpenAI(
                model="gpt-4o",
                api_key=os.environ.get("OPENAI_API_KEY"),
                temperature=0.2,
            )
            self.model_name = "gpt-4o"
            logger.info("LLMClient initialized with OpenAI provider")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(min=1, max=30),
        retry=retry_if_exception_type((TimeoutError, Exception)),
        reraise=True,
    )
    async def _invoke(self, prompt: str) -> object:
        """Invoke the LLM with retry logic."""
        return await self._llm.ainvoke([HumanMessage(content=prompt)])

    async def complete(self, prompt: str, response_format: str = "json") -> str:
        """Call the LLM with the given prompt and return the raw string content.

        Wraps the call in an OTel llm_span for distributed tracing and
        records token usage to the metrics subsystem.

        Args:
            prompt: The prompt to send to the LLM.
            response_format: If "json", appends instruction to return valid JSON only.

        Returns:
            The raw string content of the LLM response.

        Raises:
            LLMCallException: If the call fails after all retries.
        """
        if response_format == "json":
            prompt = (
                prompt
                + "\n\nIMPORTANT: Return valid JSON only. "
                "No markdown fences, no preamble, no explanation. "
                "Just the raw JSON object."
            )

        tool_name = _current_tool_name.get()
        conversation_id = _current_conversation_id.get()

        async with llm_span(
            tool_name, conversation_id, model=self.model_name
        ) as span:
            try:
                response = await self._invoke(prompt)
            except Exception as e:
                logger.error("LLM call failed after retries: %s", str(e))
                raise LLMCallException(f"LLM call failed: {str(e)}") from e

            content = response.content

            # Strip markdown fences that LLMs sometimes add despite instructions
            if response_format == "json":
                content = self._strip_markdown_fences(content)

            # Extract token counts from response metadata
            usage_meta = getattr(response, "usage_metadata", {})
            if isinstance(usage_meta, dict):
                input_tokens = usage_meta.get("input_tokens", 0)
                output_tokens = usage_meta.get("output_tokens", 0)
                span.set_attribute("llm.input_tokens", input_tokens)
                span.set_attribute("llm.output_tokens", output_tokens)
                record_tokens(
                    stage=tool_name,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                track_tokens(
                    stage=tool_name,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                logger.debug(
                    "LLM tokens — input: %s, output: %s",
                    input_tokens, output_tokens,
                )
            else:
                logger.debug("LLM response received (token counts unavailable)")

            return content

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove ```json ... ``` or ``` ... ``` wrappers from LLM output."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = stripped.index("\n")
            stripped = stripped[first_newline + 1 :]
            # Remove closing fence
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
        return stripped
