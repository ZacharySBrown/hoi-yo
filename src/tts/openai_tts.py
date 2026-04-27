"""OpenAI TTS-1 provider implementation."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class OpenAITTSProvider(TTSProvider):
    """Calls OpenAI's tts-1 endpoint to synthesize mp3 audio.

    Pricing (April 2026): $15 per 1M chars for tts-1.
    """

    name = "openai"
    PRICE_PER_MILLION_CHARS = 15.0  # USD, tts-1
    MODEL = "tts-1"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        if self._api_key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                logger.warning("openai SDK not installed -- TTS disabled")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        speed: float = 1.0,
    ) -> Path:
        if not self._client:
            raise RuntimeError("OpenAI TTS provider not configured (missing API key)")

        # Safety net: cap text length
        if len(text) > 800:
            text = text[:797] + "..."

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # OpenAI speed range is 0.25-4.0
        speed = max(0.25, min(4.0, speed))

        response = await self._client.audio.speech.create(
            model=self.MODEL,
            voice=voice,
            input=text,
            speed=speed,
        )

        # Stream to disk
        content = await response.aread()
        output_path.write_bytes(content)
        return output_path

    def estimate_cost(self, char_count: int) -> float:
        return char_count * self.PRICE_PER_MILLION_CHARS / 1_000_000
