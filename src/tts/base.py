"""Abstract TTS provider interface.

Concrete providers implement ``synthesize`` to produce an mp3 file
from text + voice config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract TTS provider."""

    name: str = "base"

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        speed: float = 1.0,
    ) -> Path:
        """Generate audio for ``text`` using ``voice`` and write to ``output_path``.

        Returns the output path on success, raises on failure.
        """

    @abstractmethod
    def estimate_cost(self, char_count: int) -> float:
        """Return USD cost estimate for synthesizing this many characters."""

    @property
    def is_available(self) -> bool:
        """Whether this provider is properly configured (e.g. has API key)."""
        return True
