"""Provider-abstracted LLM client for Lens review pipeline inference.

Mirrors the specweaver-agent LLM client pattern. Supports OpenAI and Ollama.
All pipeline tools must call complete() through this module — never import
openai directly.

Includes retry logic with exponential backoff for transient failures.
Long prompts (rich evidence + CRITICAL RULES) can occasionally trigger
timeouts or rate limits; retrying recovers most of these.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_OPENAI_TEMPERATURE = 0.2
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_TEMPERATURE = 0.1

# OpenAI timeout per attempt. Total wall time with retries is
# OPENAI_TIMEOUT_SECONDS * MAX_RETRIES + backoff time.
OPENAI_TIMEOUT_SECONDS = 120
OLLAMA_TIMEOUT_SECONDS = 300

# Retry configuration for transient LLM failures (timeouts, 429, 5xx).
# 3 attempts with exponential backoff: 2s, 4s, 8s.
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2.0

# Error substrings that are transient and worth retrying.
_RETRYABLE_ERRORS = (
    "timeout",
    "timed out",
    "rate limit",
    "429",
    "500",
    "502",
    "503",
    "connection",
    "read error",
)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"


class LLMCallException(Exception):
    """Raised when an LLM provider call fails after all retries."""


class LLMClient:
    """
    Provider-abstracted LLM client for the Lens agent.

    Supports OpenAI and Ollama. All tools call complete() through this
    class — never import openai or httpx directly in tool modules.

    Includes retry with exponential backoff for transient failures.
    """

    def __init__(self) -> None:
        provider_name = os.getenv("LLM_PROVIDER", LLMProvider.OPENAI.value).lower()
        self._provider = LLMProvider(provider_name)
        self._setup_provider()

    def _setup_provider(self) -> None:
        """Load provider-specific configuration from environment variables."""
        if self._provider == LLMProvider.OLLAMA:
            self._base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
            self._model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
            self._temperature = float(
                os.getenv("OLLAMA_TEMPERATURE", str(DEFAULT_OLLAMA_TEMPERATURE))
            )
            self.model_name = self._model
            logger.info(
                "LLMClient: provider=ollama model=%s base_url=%s",
                self._model,
                self._base_url,
            )
            return

        self._openai_client = None
        self._model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self._temperature = float(
            os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_OPENAI_TEMPERATURE))
        )
        self.model_name = self._model
        logger.info("LLMClient: provider=openai model=%s", self._model)

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

        Retries up to MAX_RETRIES times with exponential backoff on
        transient failures (timeouts, rate limits, 5xx errors).

        Args:
            prompt: Rendered prompt text.
            response_format: 'json' or 'text'.
            output_schema: Optional JSON schema for structured output.
            schema_name: Schema name used in provider logs.
            stage_name: Pipeline stage name for logging.

        Returns:
            Raw response text from the model.

        Raises:
            LLMCallException: If the provider call fails after all retries.
        """
        if response_format == "json":
            prompt = (
                prompt
                + "\n\nIMPORTANT: Return valid JSON only. "
                "No markdown fences, no preamble, no explanation. "
                "Just the raw JSON object."
            )

        start = time.monotonic()
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if self._provider == LLMProvider.OLLAMA:
                    result = await self._complete_ollama(
                        prompt, response_format, output_schema
                    )
                else:
                    result = await self._complete_openai(
                        prompt, response_format, output_schema, schema_name
                    )

                if response_format == "json":
                    result = self._strip_markdown_fences(result)

                duration = time.monotonic() - start
                logger.info(
                    "LLMClient.complete: provider=%s stage=%s attempt=%d "
                    "duration_ms=%d response_len=%d",
                    self._provider.value,
                    stage_name or "unknown",
                    attempt,
                    int(duration * 1000),
                    len(result),
                )
                return result

            except Exception as exc:
                last_exc = exc
                error_str = str(exc).lower()
                is_retryable = any(e in error_str for e in _RETRYABLE_ERRORS)

                if not is_retryable or attempt == MAX_RETRIES:
                    logger.error(
                        "LLM call failed permanently. provider=%s stage=%s "
                        "attempt=%d error=%s",
                        self._provider.value,
                        stage_name or "unknown",
                        attempt,
                        str(exc)[:300],
                    )
                    raise LLMCallException(f"LLM call failed: {exc}") from exc

                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "LLM call failed, retrying. provider=%s stage=%s "
                    "attempt=%d/%d delay=%.1fs error=%s",
                    self._provider.value,
                    stage_name or "unknown",
                    attempt,
                    MAX_RETRIES,
                    delay,
                    str(exc)[:200],
                )
                await asyncio.sleep(delay)

        # Should not reach here but satisfies type checker
        raise LLMCallException(f"LLM call failed after {MAX_RETRIES} attempts") from last_exc

    async def _complete_ollama(
        self,
        prompt: str,
        response_format: str,
        output_schema: dict | None,
    ) -> str:
        """Call Ollama's /api/generate endpoint."""
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": self._temperature},
        }
        if output_schema is not None and response_format == "json":
            payload["format"] = output_schema
        elif response_format == "json":
            payload["format"] = "json"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(OLLAMA_TIMEOUT_SECONDS)
        ) as client:
            response = await client.post(
                f"{self._base_url}/api/generate", json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = str(data.get("response", ""))
            if not content.strip():
                raise ValueError(
                    f"Ollama returned empty response for stage={self._model}"
                )
            return content

    async def _complete_openai(
        self,
        prompt: str,
        response_format: str,
        output_schema: dict | None,
        schema_name: str,
    ) -> str:
        """Call OpenAI Chat Completions with optional structured output."""
        if self._openai_client is None:
            import openai

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LLMCallException("OPENAI_API_KEY is required for the openai provider")
            self._openai_client = openai.AsyncOpenAI(api_key=api_key)

        response_format_param: Any = None
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
                model=self._model,
                temperature=self._temperature,
                response_format=response_format_param,
                messages=[{"role": "user", "content": prompt}],
                timeout=OPENAI_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            # Retry without strict schema if OpenAI rejects it as invalid
            if output_schema is not None and "Invalid schema" in str(exc):
                logger.warning(
                    "OpenAI rejected json_schema for %s; retrying with "
                    "json_object. error=%s",
                    schema_name,
                    str(exc)[:300],
                )
                response = await self._openai_client.chat.completions.create(
                    model=self._model,
                    temperature=self._temperature,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}],
                    timeout=OPENAI_TIMEOUT_SECONDS,
                )
            else:
                raise
        return response.choices[0].message.content or ""

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove Markdown code fences from JSON responses."""
        stripped = text.strip()
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            if first_newline == -1:
                return stripped.strip("`")
            stripped = stripped[first_newline + 1 :]
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
        return stripped


def get_llm_client() -> LLMClient:
    """
    Return the process-wide LLM client singleton.

    Returns:
        Shared LLMClient instance.
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance


_llm_client_instance: LLMClient | None = None
