"""Provider-abstracted LLM client for SpecWeaver pipeline inference."""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from enum import Enum
from typing import Any

import httpx

from app.llm.budget import output_budget_for_stage
from app.observability import llm_span, record_tokens

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_CONTEXT_WINDOW = 128000
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_OPENAI_TEMPERATURE = 0.2
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_OLLAMA_TEMPERATURE = 0.1
MAX_STRUCTURED_OUTPUT_TEMPERATURE = 0.3
OPENAI_TIMEOUT_SECONDS = 120
OLLAMA_STANDARD_TIMEOUT_SECONDS = 300
OLLAMA_REASONING_TIMEOUT_SECONDS = 300

TIER_DEFAULTS = {
    "1": {
        "primary_model": "qwen3:8b",
        "fast_model": "qwen3:8b",
        "primary_context": 8192,
        "fast_context": 8192,
    },
    "2": {
        "primary_model": "qwen3:14b",
        "fast_model": "qwen3:8b",
        "primary_context": 16384,
        "fast_context": 8192,
    },
    "3": {
        "primary_model": "qwen3:32b",
        "fast_model": "qwen3:14b",
        "primary_context": 32768,
        "fast_context": 16384,
    },
    "cpu": {
        "primary_model": "qwen3:8b",
        "fast_model": "qwen3:8b",
        "primary_context": 4096,
        "fast_context": 4096,
    },
}

FAST_MODEL_STAGES = {"output_formatting"}
REASONING_STAGES = {"extraction", "classification"}
LARGE_OUTPUT_STAGES = {"extraction", "classification"}

_current_tool_name: ContextVar[str] = ContextVar("_current_tool_name", default="unknown")
_current_session_id: ContextVar[str] = ContextVar("_current_session_id", default="unknown")


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"


class ModelTier(str, Enum):
    """Ollama model tiers used for stage-based routing."""

    PRIMARY = "primary"
    FAST = "fast"


class LLMCallException(Exception):
    """Raised when an LLM provider call fails."""


def set_llm_context(tool_name: str, session_id: str) -> None:
    """
    Set tracing context for the current LLM call.

    Args:
        tool_name: Pipeline tool name.
        session_id: SpecWeaver session identifier.
    """
    _current_tool_name.set(tool_name)
    _current_session_id.set(session_id)


class LLMClient:
    """Provider-abstracted LLM client with Ollama and OpenAI support."""

    def __init__(self) -> None:
        provider_name = os.getenv("LLM_PROVIDER", LLMProvider.OLLAMA.value).lower()
        self._provider = LLMProvider(provider_name)
        self._setup_provider()

    def _setup_provider(self) -> None:
        """Load provider-specific configuration from environment variables."""
        if self._provider == LLMProvider.OLLAMA:
            tier_name = os.getenv("OLLAMA_HARDWARE_TIER", "2").lower()
            tier_defaults = TIER_DEFAULTS.get(tier_name, TIER_DEFAULTS["2"])
            self._base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
            self._primary_model = os.getenv(
                "OLLAMA_PRIMARY_MODEL", str(tier_defaults["primary_model"])
            )
            self._fast_model = os.getenv(
                "OLLAMA_FAST_MODEL", str(tier_defaults["fast_model"])
            )
            self._num_ctx_primary = int(
                os.getenv("OLLAMA_NUM_CTX_PRIMARY", str(tier_defaults["primary_context"]))
            )
            self._num_ctx_fast = int(
                os.getenv("OLLAMA_NUM_CTX_FAST", str(tier_defaults["fast_context"]))
            )
            self._temperature = min(
                float(os.getenv("OLLAMA_TEMPERATURE", str(DEFAULT_OLLAMA_TEMPERATURE))),
                MAX_STRUCTURED_OUTPUT_TEMPERATURE,
            )
            self.model_name = self._primary_model
            logger.info(
                "LLMClient: provider=ollama tier=%s base_url=%s primary=%s "
                "fast=%s ctx_primary=%d ctx_fast=%d",
                tier_name,
                self._base_url,
                self._primary_model,
                self._fast_model,
                self._num_ctx_primary,
                self._num_ctx_fast,
            )
            return

        import openai

        self._openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._openai_model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self._temperature = float(os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_OPENAI_TEMPERATURE)))
        self.model_name = self._openai_model
        logger.info("LLMClient: provider=openai model=%s", self._openai_model)

    def _select_model(self, stage_name: str) -> tuple[str, int]:
        """
        Return the provider model and context window for a stage.

        Args:
            stage_name: Pipeline stage name.

        Returns:
            Tuple of model name and context window.
        """
        if self._provider == LLMProvider.OPENAI:
            return self._openai_model, DEFAULT_OPENAI_CONTEXT_WINDOW
        if stage_name in FAST_MODEL_STAGES:
            return self._fast_model, self._num_ctx_fast
        return self._primary_model, self._num_ctx_primary

    async def check_connectivity(self) -> None:
        """Verify Ollama connectivity and log missing model guidance."""
        if self._provider != LLMProvider.OLLAMA:
            return

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.error(
                "OLLAMA_STARTUP: cannot reach Ollama at %s. error=%s.",
                self._base_url,
                str(exc),
            )
            return

        models = [model["name"] for model in data.get("models", [])]
        primary_available = any(
            _ollama_model_matches(self._primary_model, model) for model in models
        )
        fast_available = any(
            _ollama_model_matches(self._fast_model, model) for model in models
        )
        if not primary_available:
            logger.error(
                "OLLAMA_STARTUP: primary model '%s' not found. Available: %s. "
                "Run: ollama pull %s",
                self._primary_model,
                models,
                self._primary_model,
            )
        if not fast_available:
            logger.warning(
                "OLLAMA_STARTUP: fast model '%s' not found. Available: %s. "
                "Run: ollama pull %s",
                self._fast_model,
                models,
                self._fast_model,
            )

    async def complete(
        self,
        prompt: str,
        response_format: str = "json",
        output_schema: dict | None = None,
        schema_name: str = "tool_output",
        stage_name: str = "",
    ) -> str:
        """
        Call the configured LLM and return raw response content.

        Args:
            prompt: Rendered prompt.
            response_format: json or text.
            output_schema: Optional JSON schema.
            schema_name: Schema name for provider logs.
            stage_name: Pipeline stage name.

        Returns:
            Raw response text.

        Raises:
            LLMCallException: If the provider call fails.
        """
        if response_format == "json":
            prompt = _append_json_instruction(prompt)

        start = time.monotonic()
        tool_name = _current_tool_name.get()
        session_id = _current_session_id.get()
        model, _ = self._select_model(stage_name)

        async with llm_span(tool_name, session_id, model=model) as span:
            try:
                if self._provider == LLMProvider.OLLAMA:
                    result = await self._complete_ollama(
                        prompt, response_format, output_schema, stage_name
                    )
                else:
                    result = await self._complete_openai(
                        prompt, response_format, output_schema, schema_name
                    )
            except Exception as exc:
                logger.error(
                    "LLM call failed. provider=%s stage=%s schema=%s error=%s",
                    self._provider.value,
                    stage_name or "unknown",
                    schema_name,
                    str(exc)[:300],
                )
                raise LLMCallException(f"LLM call failed: {exc}") from exc

            if response_format == "json":
                result = self._strip_markdown_fences(result)

            duration = time.monotonic() - start
            span.set_attribute("llm.provider", self._provider.value)
            span.set_attribute("llm.stage", stage_name or "unknown")
            self._record_usage(model, result)
            logger.info(
                "LLMClient.complete: provider=%s stage=%s schema=%s "
                "duration_ms=%d response_len=%d",
                self._provider.value,
                stage_name or "unknown",
                schema_name,
                int(duration * 1000),
                len(result),
            )
            return result

    async def _complete_ollama(
        self,
        prompt: str,
        response_format: str,
        output_schema: dict | None,
        stage_name: str,
    ) -> str:
        """
        Call Ollama's /api/generate endpoint.

        Args:
            prompt: Prompt text.
            response_format: json or text.
            output_schema: Optional JSON schema.
            stage_name: Pipeline stage name.

        Returns:
            Ollama response content.
        """
        model, num_ctx = self._select_model(stage_name)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": self._temperature,
                "num_ctx": num_ctx,
                "num_predict": self._max_tokens_for_stage(stage_name, num_ctx),
            },
        }
        if output_schema is not None and response_format == "json":
            payload["format"] = output_schema
        elif response_format == "json":
            payload["format"] = "json"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_for_stage(stage_name))
        ) as client:
            response = await client.post(f"{self._base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            content = str(data.get("response", ""))
            if not content or not content.strip():
                logger.error(
                    "Ollama returned empty response. stage=%s model=%s "
                    "num_ctx=%d prompt_len_chars=%d.",
                    stage_name,
                    model,
                    num_ctx,
                    len(prompt),
                )
                raise ValueError(f"Ollama returned empty response for stage={stage_name}.")
            return content

    async def _complete_openai(
        self,
        prompt: str,
        response_format: str,
        output_schema: dict | None,
        schema_name: str,
    ) -> str:
        """
        Call OpenAI Chat Completions with structured output.

        Args:
            prompt: Prompt text.
            response_format: json or text.
            output_schema: Optional schema.
            schema_name: Schema name.

        Returns:
            OpenAI response content.
        """
        response_format_param = None
        if response_format == "json" and output_schema is not None:
            response_format_param = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": output_schema,
                },
            }
        elif response_format == "json":
            response_format_param = {"type": "json_object"}

        try:
            response = await self._openai_client.chat.completions.create(
                model=self._openai_model,
                temperature=self._temperature,
                response_format=response_format_param,
                messages=[{"role": "user", "content": prompt}],
                timeout=self._timeout_for_stage(""),
            )
        except Exception as exc:
            should_retry_without_schema = (
                response_format == "json"
                and output_schema is not None
                and "Invalid schema for response_format" in str(exc)
            )
            if not should_retry_without_schema:
                raise

            logger.warning(
                "OpenAI rejected json_schema for %s; retrying with json_object. error=%s",
                schema_name,
                str(exc)[:300],
            )
            response = await self._openai_client.chat.completions.create(
                model=self._openai_model,
                temperature=self._temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
                timeout=self._timeout_for_stage(""),
            )
        return response.choices[0].message.content or ""

    def _max_tokens_for_stage(self, stage_name: str, num_ctx: int) -> int:
        """
        Return maximum output tokens for a stage.

        Args:
            stage_name: Pipeline stage name.
            num_ctx: Selected context window.

        Returns:
            Output token budget.
        """
        fallback = min(4096, int(num_ctx * 0.4)) if stage_name in LARGE_OUTPUT_STAGES else min(2048, int(num_ctx * 0.25))
        return output_budget_for_stage(stage_name, fallback)

    def _timeout_for_stage(self, stage_name: str) -> int:
        """
        Return provider timeout in seconds for a stage.

        Args:
            stage_name: Pipeline stage name.

        Returns:
            Timeout in seconds.
        """
        if self._provider == LLMProvider.OPENAI:
            return OPENAI_TIMEOUT_SECONDS
        if stage_name in REASONING_STAGES:
            return OLLAMA_REASONING_TIMEOUT_SECONDS
        return OLLAMA_STANDARD_TIMEOUT_SECONDS

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """
        Remove Markdown code fences from JSON responses.

        Args:
            text: Raw model response.

        Returns:
            Response without outer Markdown fences.
        """
        stripped = text.strip()
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            if first_newline == -1:
                return stripped.strip("`")
            stripped = stripped[first_newline + 1 :]
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
        return stripped

    def _record_usage(self, model: str, response: str) -> None:
        """
        Record best-effort token metrics.

        Args:
            model: Model used for the request.
            response: Response text used for approximation.
        """
        output_tokens = max(1, len(response) // 4) if response else 0
        record_tokens(
            stage=_current_tool_name.get(),
            model=model,
            input_tokens=0,
            output_tokens=output_tokens,
        )


def _append_json_instruction(prompt: str) -> str:
    """
    Add a defensive JSON-only instruction to a prompt.

    Args:
        prompt: Rendered prompt body.

    Returns:
        Prompt with a JSON-only suffix.
    """
    return (
        prompt
        + "\n\nIMPORTANT: Return valid JSON only. "
        "No markdown fences, no preamble, no explanation. "
        "Just the raw JSON object."
    )


def _ollama_model_matches(expected_model: str, available_model: str) -> bool:
    """
    Return whether an available Ollama model satisfies the expected model.

    Args:
        expected_model: Configured model name.
        available_model: Model name returned by Ollama.

    Returns:
        True when names match.
    """
    if ":" in expected_model:
        return available_model == expected_model
    return available_model.split(":")[0] == expected_model


def get_llm_client() -> LLMClient:
    """
    Return the process-wide LLM client singleton.

    Returns:
        Shared LLMClient instance.
    """
    return _llm_client_instance


_llm_client_instance = LLMClient()
