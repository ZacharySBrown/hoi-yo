"""Orchestrates parallel TTS synthesis for a turn's worth of agent decisions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.interfaces import AgentDecision
from src.tts.base import TTSProvider
from src.tts.voice_map import voice_for_persona

logger = logging.getLogger(__name__)


@dataclass
class TTSCostTracker:
    """Tracks cumulative TTS character spend."""

    total_chars: int = 0
    total_cost: float = 0.0
    by_tag: dict[str, int] = field(default_factory=dict)

    def record(self, tag: str, char_count: int, cost: float) -> None:
        self.total_chars += char_count
        self.total_cost += cost
        self.by_tag[tag] = self.by_tag.get(tag, 0) + char_count

    def to_dict(self) -> dict:
        return {
            "total_chars": self.total_chars,
            "total_cost": round(self.total_cost, 4),
            "by_tag": dict(self.by_tag),
        }


class TTSGenerator:
    """Generates per-agent audio clips for each turn.

    Audio files are written under ``output_dir/{campaign_id}/turn_{N}_{TAG}.mp3``.
    Returns a dict mapping country tag -> public URL path (relative to /static).
    """

    def __init__(
        self,
        provider: TTSProvider,
        output_dir: Path,
        campaign_id: str = "default",
    ):
        self._provider = provider
        self._output_dir = output_dir / campaign_id
        self._campaign_id = campaign_id
        self._last_text: dict[str, str] = {}
        self.cost = TTSCostTracker()
        if provider.is_available:
            self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_enabled(self) -> bool:
        return self._provider.is_available

    async def synthesize_turn(
        self,
        decisions: list[AgentDecision],
        turn: int,
    ) -> dict[str, str]:
        """Synthesize audio for each decision in parallel.

        Returns a dict ``{tag: audio_url}`` where ``audio_url`` is the public
        path that the dashboard can fetch (e.g. ``/static/audio/<id>/turn_8_GER.mp3``).
        """
        if not self.is_enabled:
            return {}

        targets: list[AgentDecision] = []
        for d in decisions:
            text = (d.inner_monologue or "").strip()
            if not text:
                continue
            if self._last_text.get(d.tag) == text:
                # Reuse previous file -- monologue identical (rare)
                continue
            targets.append(d)

        if not targets:
            return {}

        tasks = [self._synth_one(d, turn) for d in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        urls: dict[str, str] = {}
        for d, result in zip(targets, results):
            if isinstance(result, Exception):
                logger.warning("TTS failed for %s: %s", d.tag, result)
                continue
            if result is None:
                continue
            urls[d.tag] = result
            self._last_text[d.tag] = d.inner_monologue.strip()
        return urls

    async def _synth_one(self, decision: AgentDecision, turn: int) -> str | None:
        text = (decision.inner_monologue or "").strip()
        voice, speed = voice_for_persona(decision.tag)

        filename = f"turn_{turn:03d}_{decision.tag}.mp3"
        output_path = self._output_dir / filename

        try:
            await self._provider.synthesize(text, voice, output_path, speed=speed)
        except Exception:
            logger.exception("TTS synth failed for %s turn %d", decision.tag, turn)
            raise

        cost = self._provider.estimate_cost(len(text))
        self.cost.record(decision.tag, len(text), cost)

        # Public URL the dashboard fetches
        return f"/static/audio/{self._campaign_id}/{filename}"
