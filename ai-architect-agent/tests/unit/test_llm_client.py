from __future__ import annotations

import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.client import LLMClient, LLMCallException


class TestLLMClientComplete:
    """Tests for LLMClient.complete()."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Patch env to avoid needing a real API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "LLM_PROVIDER": "openai"}):
            with patch("app.llm.client.ChatOpenAI") as mock_cls:
                self.mock_chat = MagicMock()
                # _invoke calls self._llm.bind(...) then ainvoke() on the result.
                # Make bind() return the same mock so ainvoke is always self.mock_chat.ainvoke.
                self.mock_chat.bind.return_value = self.mock_chat
                mock_cls.return_value = self.mock_chat
                self.client = LLMClient()
                yield

    async def test_complete_appends_json_instruction(self):
        """complete() appends JSON instruction when response_format='json'."""
        mock_response = MagicMock()
        mock_response.content = '{"result": "ok"}'
        mock_response.usage_metadata = {"input_tokens": 10, "output_tokens": 5}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        result = await self.client.complete("test prompt", response_format="json")

        assert result == '{"result": "ok"}'
        call_args = self.mock_chat.ainvoke.call_args[0][0]
        # The prompt should have had the JSON instruction appended
        assert "Return valid JSON only" in call_args[0].content

    async def test_complete_no_json_instruction_for_text(self):
        """complete() does not append JSON instruction when response_format='text'."""
        mock_response = MagicMock()
        mock_response.content = "plain text"
        mock_response.usage_metadata = {}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        result = await self.client.complete("test prompt", response_format="text")

        assert result == "plain text"
        call_args = self.mock_chat.ainvoke.call_args[0][0]
        assert "Return valid JSON only" not in call_args[0].content

    async def test_complete_raises_llm_call_exception_after_retries(self):
        """complete() raises LLMCallException when LLM fails after all retries."""
        self.mock_chat.ainvoke = AsyncMock(side_effect=TimeoutError("timeout"))

        with pytest.raises(LLMCallException, match="LLM call failed"):
            await self.client.complete("failing prompt")

    async def test_complete_logs_token_counts_at_debug(self, caplog):
        """complete() logs token counts at DEBUG level."""
        mock_response = MagicMock()
        mock_response.content = '{"data": 1}'
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        with caplog.at_level(logging.DEBUG, logger="app.llm.client"):
            await self.client.complete("test prompt")

        assert any("input" in r.message.lower() or "token" in r.message.lower() for r in caplog.records)

    async def test_complete_strips_markdown_fences_from_json(self):
        """complete() strips ```json ... ``` fences when response_format='json'."""
        mock_response = MagicMock()
        mock_response.content = '```json\n{"result": "ok"}\n```'
        mock_response.usage_metadata = {}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        result = await self.client.complete("test prompt", response_format="json")
        assert result == '{"result": "ok"}'

    async def test_complete_strips_plain_fences_from_json(self):
        """complete() strips ``` ... ``` fences (without json tag) when response_format='json'."""
        mock_response = MagicMock()
        mock_response.content = '```\n{"data": 1}\n```'
        mock_response.usage_metadata = {}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        result = await self.client.complete("test prompt", response_format="json")
        assert result == '{"data": 1}'

    async def test_complete_does_not_strip_fences_for_text_format(self):
        """complete() leaves markdown fences intact when response_format='text'."""
        mock_response = MagicMock()
        mock_response.content = '```json\n{"data": 1}\n```'
        mock_response.usage_metadata = {}
        self.mock_chat.ainvoke = AsyncMock(return_value=mock_response)

        result = await self.client.complete("test prompt", response_format="text")
        assert result == '```json\n{"data": 1}\n```'
