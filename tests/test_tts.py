"""Tests for the TTS module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.interfaces import AgentDecision
from src.tts.base import TTSProvider
from src.tts.generator import TTSGenerator, TTSCostTracker
from src.tts.voice_map import (
    DEFAULT_VOICE,
    PERSONA_VOICES,
    voice_for_persona,
)


# ── voice_map tests ────────────────────────────────────────────────────

class TestVoiceMap:
    def test_all_six_majors_have_voices(self):
        for tag in ["GER", "SOV", "USA", "ENG", "JAP", "ITA"]:
            assert tag in PERSONA_VOICES
            voice, speed = PERSONA_VOICES[tag]
            assert voice in {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
            assert 0.5 < speed < 1.5

    def test_voice_for_known_tag(self):
        voice, speed = voice_for_persona("GER")
        assert voice == "echo"

    def test_voice_for_unknown_tag(self):
        voice, speed = voice_for_persona("XXX")
        assert (voice, speed) == DEFAULT_VOICE

    def test_distinct_voices_or_speeds(self):
        # GER and ITA both use echo but at different speeds
        ger = PERSONA_VOICES["GER"]
        ita = PERSONA_VOICES["ITA"]
        assert ger != ita


# ── TTSCostTracker ─────────────────────────────────────────────────────

class TestCostTracker:
    def test_record_accumulates(self):
        t = TTSCostTracker()
        t.record("GER", 100, 0.0015)
        t.record("SOV", 200, 0.003)
        t.record("GER", 50, 0.00075)
        assert t.total_chars == 350
        assert abs(t.total_cost - 0.00525) < 1e-9
        assert t.by_tag == {"GER": 150, "SOV": 200}

    def test_to_dict(self):
        t = TTSCostTracker()
        t.record("GER", 100, 0.0015)
        d = t.to_dict()
        assert d["total_chars"] == 100
        assert d["total_cost"] == 0.0015
        assert d["by_tag"] == {"GER": 100}


# ── TTSGenerator ───────────────────────────────────────────────────────

class FakeProvider(TTSProvider):
    """Fake provider that just writes the text to disk as bytes."""

    name = "fake"

    def __init__(self, available=True, fail_tags: set[str] | None = None):
        self._available = available
        self._fail_tags = fail_tags or set()
        self.calls: list[tuple[str, str, Path, float]] = []

    @property
    def is_available(self) -> bool:
        return self._available

    async def synthesize(self, text, voice, output_path, speed=1.0):
        self.calls.append((text, voice, output_path, speed))
        # If this voice corresponds to a fail tag, raise
        for tag in self._fail_tags:
            if tag in str(output_path):
                raise RuntimeError("simulated failure")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"FAKE_MP3:" + text.encode())
        return output_path

    def estimate_cost(self, char_count):
        return char_count * 15.0 / 1_000_000


def _decision(tag: str, monologue: str) -> AgentDecision:
    return AgentDecision(
        tag=tag,
        turn_number=1,
        inner_monologue=monologue,
        mood="confident",
    )


@pytest.mark.asyncio
async def test_generator_disabled_when_provider_unavailable(tmp_path):
    provider = FakeProvider(available=False)
    gen = TTSGenerator(provider, tmp_path, campaign_id="test")
    assert not gen.is_enabled
    urls = await gen.synthesize_turn([_decision("GER", "Hello world.")], turn=1)
    assert urls == {}


@pytest.mark.asyncio
async def test_generator_synthesizes_each_decision(tmp_path):
    provider = FakeProvider()
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    decisions = [
        _decision("GER", "France grows weak."),
        _decision("SOV", "Moscow watches."),
        _decision("USA", "Build everything!"),
    ]
    urls = await gen.synthesize_turn(decisions, turn=4)
    assert set(urls.keys()) == {"GER", "SOV", "USA"}
    assert urls["GER"] == "/static/audio/abc/turn_004_GER.mp3"
    assert urls["SOV"] == "/static/audio/abc/turn_004_SOV.mp3"
    # Files exist
    assert (tmp_path / "abc" / "turn_004_GER.mp3").exists()
    assert (tmp_path / "abc" / "turn_004_SOV.mp3").exists()


@pytest.mark.asyncio
async def test_generator_uses_voice_map(tmp_path):
    provider = FakeProvider()
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    await gen.synthesize_turn([_decision("ENG", "We shall fight.")], turn=1)
    assert provider.calls[0][1] == "fable"  # ENG -> fable


@pytest.mark.asyncio
async def test_generator_skips_empty_monologue(tmp_path):
    provider = FakeProvider()
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    urls = await gen.synthesize_turn([_decision("GER", "")], turn=1)
    assert urls == {}
    assert provider.calls == []


@pytest.mark.asyncio
async def test_generator_dedupes_identical_monologue(tmp_path):
    provider = FakeProvider()
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    msg = "Build factories. Build more."
    await gen.synthesize_turn([_decision("GER", msg)], turn=1)
    assert len(provider.calls) == 1
    # Same text again -> should not call provider
    urls = await gen.synthesize_turn([_decision("GER", msg)], turn=2)
    assert urls == {}
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_generator_failure_is_isolated(tmp_path):
    provider = FakeProvider(fail_tags={"SOV"})
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    decisions = [
        _decision("GER", "Onward."),
        _decision("SOV", "This will fail."),
        _decision("USA", "Build!"),
    ]
    urls = await gen.synthesize_turn(decisions, turn=1)
    assert "GER" in urls
    assert "USA" in urls
    assert "SOV" not in urls


@pytest.mark.asyncio
async def test_generator_records_cost(tmp_path):
    provider = FakeProvider()
    gen = TTSGenerator(provider, tmp_path, campaign_id="abc")
    await gen.synthesize_turn(
        [_decision("GER", "x" * 100), _decision("SOV", "y" * 200)],
        turn=1,
    )
    assert gen.cost.total_chars == 300
    assert gen.cost.by_tag == {"GER": 100, "SOV": 200}
    assert gen.cost.total_cost > 0


# ── OpenAI provider availability test ─────────────────────────────────

class TestOpenAIProvider:
    def test_unavailable_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from src.tts.openai_tts import OpenAITTSProvider

        # If openai SDK isn't installed, is_available should still be False
        provider = OpenAITTSProvider(api_key=None)
        assert not provider.is_available

    def test_estimate_cost(self, monkeypatch):
        from src.tts.openai_tts import OpenAITTSProvider

        provider = OpenAITTSProvider(api_key="x")
        # 1M chars -> $15
        assert abs(provider.estimate_cost(1_000_000) - 15.0) < 0.001
        # 1000 chars -> $0.015
        assert abs(provider.estimate_cost(1000) - 0.015) < 0.001
