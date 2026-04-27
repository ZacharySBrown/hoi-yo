"""Text-to-speech module for voicing persona monologues."""
from src.tts.base import TTSProvider
from src.tts.generator import TTSGenerator
from src.tts.voice_map import voice_for_persona, PERSONA_VOICES

__all__ = ["TTSProvider", "TTSGenerator", "voice_for_persona", "PERSONA_VOICES"]
