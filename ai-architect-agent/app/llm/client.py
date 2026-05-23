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
    async def _invoke(
        self,
        prompt: str,
        response_format_param: dict | None = None,
    ) -> object:
        """Invoke the LLM with retry logic.

        Args:
            prompt: The prompt to send.
            response_format_param: Optional response_format dict to bind to
                the LLM before invoking. When None the LLM is invoked as-is.
        """
        if response_format_param is not None:
            llm = self._llm.bind(response_format=response_format_param)
        else:
            llm = self._llm
        return await llm.ainvoke([HumanMessage(content=prompt)])

    async def complete(
        self,
        prompt: str,
        response_format: str = "json",
        output_schema: dict | None = None,
        schema_name: str = "tool_output",
    ) -> str:
        """Call the LLM with the given prompt and return the raw string content.

        Wraps the call in an OTel llm_span for distributed tracing and
        records token usage to the metrics subsystem.

        Args:
            prompt: The full rendered prompt string.
            response_format: "json" or "text". When "json" and output_schema
                is None, uses the legacy json_object hint for backward compat.
            output_schema: JSON schema dict derived from a Pydantic model via
                model.model_json_schema(). When provided, attempts provider-
                native structured output (OpenAI json_schema type, strict=True).
                Falls back to json_object mode if the provider rejects the schema.
            schema_name: Name field for the json_schema object. Used in error
                messages and provider logs.

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

        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        tool_name = _current_tool_name.get()
        conversation_id = _current_conversation_id.get()

        # Determine the response_format parameter to pass to the API.
        # Layer 1: provider-native structured output when a schema is available.
        # Layer 0: legacy json_object hint when no schema is provided.
        schema_enforcement_active = False
        if output_schema is not None and response_format == "json":
            if provider == "ollama":
                # Ollama does not universally support the json_schema type.
                # The schema is used as a prompt hint only; enforce via Layer 2.
                logger.debug(
                    "Ollama provider: output_schema for '%s' is used as "
                    "a prompt hint only — provider schema enforcement skipped.",
                    schema_name,
                )
                response_format_param: dict | None = {"type": "json_object"}
            else:
                response_format_param = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": output_schema,
                    },
                }
                schema_enforcement_active = True
        elif response_format == "json":
            # Legacy fallback — used by tool calls not yet migrated to schemas.
            response_format_param = {"type": "json_object"}
        else:
            response_format_param = None

        async with llm_span(
            tool_name, conversation_id, model=self.model_name
        ) as span:
            try:
                response = await self._invoke(prompt, response_format_param)
            except Exception as e:
                if schema_enforcement_active and _is_schema_rejection(e):
                    # The provider refused the strict schema constraint.
                    # Fall back to json_object mode so the pipeline can continue.
                    logger.warning(
                        "Provider rejected strict schema for '%s': %s. "
                        "Falling back to json_object mode. "
                        "schema_enforcement_fallback=True",
                        schema_name, str(e)[:200],
                    )
                    span.set_attribute("schema_enforcement_fallback", True)
                    try:
                        response = await self._invoke(prompt, {"type": "json_object"})
                    except Exception as e2:
                        logger.error(
                            "LLM call failed after schema fallback: %s", str(e2)
                        )
                        raise LLMCallException(f"LLM call failed: {str(e2)}") from e2
                else:
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


def _is_schema_rejection(exc: Exception) -> bool:
    """Return True when the exception indicates a provider-side schema rejection.

    This is heuristic: OpenAI returns HTTP 400 / BadRequestError with messages
    mentioning schema, json_schema, or strict when it cannot satisfy a structured
    output constraint. We match on the exception message rather than importing
    openai directly, keeping this module provider-agnostic.

    Args:
        exc: The exception raised by _invoke().

    Returns:
        True if the exception looks like a schema enforcement rejection.
    """
    msg = str(exc).lower()
    schema_keywords = ("json_schema", "strict", "schema", "invalid_schema")
    return any(kw in msg for kw in schema_keywords)
