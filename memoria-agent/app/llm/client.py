"""LLM and embedding client for memoria-agent."""
import json
import os
from typing import Any

import openai

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

CHAT_MODEL = "gpt-4o-mini"


class LLMClient:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def complete(
        self,
        prompt: str,
        response_format: str = "text",
    ) -> str:
        """Call the chat completions API and return the response text.

        Args:
            prompt: The user prompt to send.
            response_format: ``"json"`` requests ``json_object`` response format;
                any other value uses plain text.

        Returns:
            The model's response content as a string.
        """
        kwargs: dict[str, Any] = {
            "model": CHAT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def get_llm_client() -> LLMClient:
    return LLMClient()


async def embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSION,
    )
    return response.data[0].embedding
