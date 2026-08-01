"""
Provider-abstracted LLM client for pipeline and workshop inference.

The local development provider is Ollama, which uses native JSON schema
enforcement through the ``format`` parameter. The production provider is
OpenAI, which uses Chat Completions ``json_schema`` response formats.
Pipeline tools call ``LLMClient.complete()`` without knowing which provider
is active.
"""

from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from enum import Enum
from typing import Any

import httpx

from app.llm.cost_tracker import track_tokens
from app.observability import llm_span, record_tokens

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_CONTEXT_WINDOW = 128000
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_OPENAI_TEMPERATURE = 0.2
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_OLLAMA_TEMPERATURE = 0.1
MAX_STRUCTURED_OUTPUT_TEMPERATURE = 0.3
OPENAI_TIMEOUT_SECONDS = 120
# Allow up to 5 minutes for standard stages; cold native model loads can exceed
# the previous 120 s limit on first use.
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

FAST_MODEL_STAGES = {
    "identify_gaps",
    "analyze_input",
    "reconcile_gaps",
    "elicit_scenarios",
    "resolve_questions",
    "consolidate",
    "check_transition",
}

REASONING_STAGES = {
    "architecture_generation",
    "fmea_analysis",
    "adl_generation",
    "trade_off_analysis",
    "architecture_review",
    "generate_utility_tree",
    "synthesise_implications",
    "weakness_analysis",
}

LARGE_OUTPUT_STAGES = {
    "architecture_generation",
    "fmea_analysis",
    "adl_generation",
    "trade_off_analysis",
    "generate_utility_tree",
    "synthesise_implications",
    # requirement_parsing produces a fully structured JSON document encoding
    # every parsed requirement; complex inputs routinely exceed the 2048-token
    # default budget, truncating the output mid-string.
    "requirement_parsing",
}

_current_tool_name: ContextVar[str] = ContextVar(
    "_current_tool_name", default="unknown"
)
_current_conversation_id: ContextVar[str] = ContextVar(
    "_current_conversation_id", default="unknown"
)


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


def set_llm_context(tool_name: str, conversation_id: str) -> None:
    """
    Set tracing context for the current LLM call.

    Args:
        tool_name: Pipeline tool or node name issuing the call.
        conversation_id: Conversation identifier for trace correlation.
    """
    _current_tool_name.set(tool_name)
    _current_conversation_id.set(conversation_id)


class LLMClient:
    """
    Provider-abstracted LLM client.

    The provider is selected by ``LLM_PROVIDER``. Ollama additionally routes
    short structured stages to a fast model and reasoning-heavy stages to the
    primary model.
    """

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
                os.getenv(
                    "OLLAMA_NUM_CTX_PRIMARY",
                    str(tier_defaults["primary_context"]),
                )
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

        self._openai_client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self._openai_model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self._temperature = float(
            os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_OPENAI_TEMPERATURE))
        )
        self.model_name = self._openai_model
        logger.info("LLMClient: provider=openai model=%s", self._openai_model)

    def _select_model(self, stage_name: str) -> tuple[str, int]:
        """
        Return the provider model and context window for a stage.

        Args:
            stage_name: Pipeline or workshop stage name.

        Returns:
            Tuple of model name and maximum context window.
        """
        if self._provider == LLMProvider.OPENAI:
            return self._openai_model, DEFAULT_OPENAI_CONTEXT_WINDOW

        if stage_name in FAST_MODEL_STAGES:
            return self._fast_model, self._num_ctx_fast
        return self._primary_model, self._num_ctx_primary

    async def check_connectivity(self) -> None:
        """
        Verify that the configured LLM provider is reachable.

        For Ollama, the check also warns when the base URL points at the
        removed Docker service name, because that topology is CPU-only on
        macOS Docker Desktop and causes the empty structured-output failures
        seen under memory pressure.
        """
        if self._provider != LLMProvider.OLLAMA:
            return

        if "ollama:11434" in self._base_url:
            logger.warning(
                "OLLAMA_WARNING: base_url=%s points to a Docker service name. "
                "On macOS this means CPU-only inference because Docker Desktop "
                "cannot access the Apple Silicon GPU (Metal). Use "
                "OLLAMA_BASE_URL=http://host.docker.internal:11434 and install "
                "Ollama natively via: brew install ollama && "
                "brew services start ollama",
                self._base_url,
            )

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.error(
                "OLLAMA_STARTUP: cannot reach Ollama at %s. error=%s. "
                "On macOS: brew install ollama && brew services start ollama",
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
        if primary_available and fast_available:
            logger.info(
                "OLLAMA_STARTUP: connected. base_url=%s primary=%s fast=%s "
                "available_models=%s",
                self._base_url,
                self._primary_model,
                self._fast_model,
                models,
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
            prompt: Fully rendered prompt string.
            response_format: ``json`` or ``text``.
            output_schema: JSON schema dict from a Pydantic model.
            schema_name: Schema name used for provider logs and OpenAI.
            stage_name: Pipeline stage name for model tier selection.

        Returns:
            Raw model response text.

        Raises:
            LLMCallException: If the provider call fails.
        """
        if response_format == "json":
            prompt = _append_json_instruction(prompt)

        start = time.monotonic()
        tool_name = _current_tool_name.get()
        conversation_id = _current_conversation_id.get()
        model, _ = self._select_model(stage_name)

        async with llm_span(tool_name, conversation_id, model=model) as span:
            try:
                if self._provider == LLMProvider.OLLAMA:
                    result = await self._complete_ollama(
                        prompt, response_format, output_schema, stage_name
                    )
                else:
                    result = await self._complete_openai(
                        prompt, response_format, output_schema, schema_name
                    )
            except (httpx.HTTPError, TimeoutError, Exception) as exc:
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
        Call Ollama's ``/api/generate`` endpoint.

        Args:
            prompt: Prompt text to send.
            response_format: ``json`` or ``text``.
            output_schema: Optional JSON schema for native constrained output.
            stage_name: Stage name used for model and timeout selection.

        Returns:
            Ollama response content.
        """
        model, num_ctx = self._select_model(stage_name)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            # Disable chain-of-thought tokens (qwen3 <think>...</think>) so the
            # output is valid JSON when Ollama's format constraint is active.
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
                    "num_ctx=%d prompt_len_chars=%d. This typically means "
                    "the context window was exceeded or the JSON schema could "
                    "not be satisfied under current memory pressure. If "
                    "running on macOS, ensure Ollama is installed natively via "
                    "Homebrew, not in Docker.",
                    stage_name,
                    model,
                    num_ctx,
                    len(prompt),
                )
                raise ValueError(
                    f"Ollama returned empty response for stage={stage_name}. "
                    f"Model={model} num_ctx={num_ctx}. Reduce context window "
                    "or input size."
                )

            return content

    async def _complete_openai(
        self,
        prompt: str,
        response_format: str,
        output_schema: dict | None,
        schema_name: str,
    ) -> str:
        """
        Call OpenAI Chat Completions with provider-native structured output.

        Args:
            prompt: Prompt text to send.
            response_format: ``json`` or ``text``.
            output_schema: Optional JSON schema for strict response format.
            schema_name: Schema name for OpenAI json_schema.

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

        response = await self._openai_client.chat.completions.create(
            model=self._openai_model,
            temperature=self._temperature,
            response_format=response_format_param,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._timeout_for_stage(""),
        )
        return response.choices[0].message.content or ""

    def _max_tokens_for_stage(self, stage_name: str, num_ctx: int) -> int:
        """
        Return maximum output tokens for a stage.

        Args:
            stage_name: Pipeline or workshop stage name.
            num_ctx: Context window for the selected model.

        Returns:
            Output token budget.
        """
        if stage_name in LARGE_OUTPUT_STAGES:
            return min(4096, int(num_ctx * 0.4))
        return min(2048, int(num_ctx * 0.25))

    def _timeout_for_stage(self, stage_name: str) -> int:
        """
        Return provider timeout in seconds for a stage.

        Args:
            stage_name: Pipeline or workshop stage name.

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
        Record best-effort token metrics when providers do not return usage.

        Args:
            model: Model used for the request.
            response: Response text used for output token approximation.
        """
        output_tokens = max(1, len(response) // 4) if response else 0
        tool_name = _current_tool_name.get()
        record_tokens(
            stage=tool_name,
            model=model,
            input_tokens=0,
            output_tokens=output_tokens,
        )
        track_tokens(
            stage=tool_name,
            model=model,
            input_tokens=0,
            output_tokens=output_tokens,
        )


def _append_json_instruction(prompt: str) -> str:
    """
    Add the existing defensive JSON-only instruction to a prompt.

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
        expected_model: Configured model name, optionally with a tag.
        available_model: Model name returned by Ollama.

    Returns:
        True when the names match exactly, or when the expected model has no
        tag and matches the available model family.
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


def _is_schema_rejection(exc: Exception) -> bool:
    """
    Return whether an exception looks like an OpenAI schema rejection.

    Args:
        exc: Exception raised by a provider.

    Returns:
        True when the message points at schema validation rejection.
    """
    message = str(exc).lower()
    return any(
        keyword in message
        for keyword in ("json_schema", "strict", "schema", "invalid_schema")
    )


_llm_client_instance = LLMClient()
