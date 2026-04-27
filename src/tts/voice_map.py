"""Maps personas (by country tag) to OpenAI TTS voices and speeds."""

from __future__ import annotations

# OpenAI TTS-1 voices: alloy, echo, fable, onyx, nova, shimmer
PERSONA_VOICES: dict[str, tuple[str, float]] = {
    "GER": ("echo",  1.00),   # Bismarck: cold, measured
    "SOV": ("onyx",  1.00),   # Stalin: deep, dark, authoritative
    "USA": ("nova",  1.05),   # Roosevelt: bright, energetic
    "ENG": ("fable", 1.00),   # Churchill: British orator
    "JAP": ("onyx",  1.10),   # Nobunaga: commanding, sharper
    "ITA": ("echo",  0.90),   # Machiavelli: scheming, slower
}

DEFAULT_VOICE = ("alloy", 1.0)


def voice_for_persona(tag: str, persona_name: str = "") -> tuple[str, float]:
    """Look up voice + speed for a country tag.

    ``persona_name`` is reserved for future per-persona overrides
    (e.g. swapping Stalin -> Khrushchev voice). Currently the tag
    determines the voice; alternate Soviet personas all use ``onyx``.
    """
    return PERSONA_VOICES.get(tag, DEFAULT_VOICE)
