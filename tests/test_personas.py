"""Tests for persona loading and validation."""

from pathlib import Path

import pytest

from src.interfaces import MAJOR_POWERS, Persona
from src.personas.loader import load_all_personas, load_persona

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = PROJECT_ROOT / "personas"

# All expected persona directories
EXPECTED_DIRS = [
    "germany",
    "italy",
    "japan",
    "modern_germany",
    "modern_italy",
    "modern_japan",
    "modern_russia",
    "modern_uk",
    "modern_usa",
    "soviet_union",
    "soviet_union_alt_khrushchev",
    "soviet_union_alt_rasputin",
    "soviet_union_alt_trotsky",
    "united_kingdom",
    "usa",
]


# ── File structure tests ────────────────────────────────────────────


class TestPersonaDirectoryStructure:
    """Verify that all 9 persona directories have the required files."""

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_soul_md_exists(self, dirname: str) -> None:
        soul_path = PERSONAS_DIR / dirname / "SOUL.md"
        assert soul_path.exists(), f"Missing SOUL.md in personas/{dirname}/"

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_config_toml_exists(self, dirname: str) -> None:
        config_path = PERSONAS_DIR / dirname / "config.toml"
        assert config_path.exists(), f"Missing config.toml in personas/{dirname}/"


# ── Loader tests ────────────────────────────────────────────────────


class TestLoadPersona:
    """Test that loader correctly parses each individual persona."""

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_load_returns_persona(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert isinstance(persona, Persona)

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_persona_has_nonempty_soul_prompt(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert persona.soul_prompt.strip(), (
            f"Persona {dirname} has an empty soul_prompt"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_persona_has_nonempty_name(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert persona.name.strip(), f"Persona {dirname} has an empty name"

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_persona_tag_is_valid_major_power(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert persona.tag in MAJOR_POWERS, (
            f"Persona {dirname} has tag '{persona.tag}' which is not in "
            f"MAJOR_POWERS {MAJOR_POWERS}"
        )


# ── Specific persona content tests ─────────────────────────────────


EXPECTED_PERSONAS = {
    "germany": ("GER", "Otto von Bismarck"),
    "soviet_union": ("SOV", "Joseph Stalin"),
    "usa": ("USA", "Theodore Roosevelt"),
    "united_kingdom": ("ENG", "Winston Churchill"),
    "japan": ("JAP", "Oda Nobunaga"),
    "italy": ("ITA", "Niccolo Machiavelli"),
    "soviet_union_alt_khrushchev": ("SOV", "Nikita Khrushchev"),
    "soviet_union_alt_rasputin": ("SOV", "Grigory Rasputin"),
    "soviet_union_alt_trotsky": ("SOV", "Leon Trotsky"),
    "modern_germany": ("GER", "The Iron Accountant"),
    "modern_russia": ("SOV", "The Grandmaster"),
    "modern_usa": ("USA", "The Commander-in-Tweet"),
    "modern_uk": ("ENG", "The Rt. Hon. Chaos Coordinator"),
    "modern_japan": ("JAP", "The CEO-Premier"),
    "modern_italy": ("ITA", "Il Magnifico"),
}


class TestPersonaContent:
    """Verify that each persona has the expected tag and name."""

    @pytest.mark.parametrize(
        "dirname,expected_tag,expected_name",
        [(d, t, n) for d, (t, n) in EXPECTED_PERSONAS.items()],
        ids=list(EXPECTED_PERSONAS.keys()),
    )
    def test_persona_tag_and_name(
        self, dirname: str, expected_tag: str, expected_name: str
    ) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert persona.tag == expected_tag
        assert persona.name == expected_name

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_soul_prompt_contains_heading(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert persona.soul_prompt.startswith("# "), (
            f"SOUL.md for {dirname} should start with a markdown heading"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_soul_prompt_has_personality_section(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert "### Your Personality" in persona.soul_prompt, (
            f"SOUL.md for {dirname} is missing '### Your Personality' section"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_soul_prompt_has_voice_section(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert "### Your Voice" in persona.soul_prompt, (
            f"SOUL.md for {dirname} is missing '### Your Voice' section"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_soul_prompt_has_never_do_section(self, dirname: str) -> None:
        persona = load_persona(PERSONAS_DIR / dirname)
        assert "### What You Would NEVER Do" in persona.soul_prompt, (
            f"SOUL.md for {dirname} is missing '### What You Would NEVER Do' section"
        )


# ── Bulk loading tests ──────────────────────────────────────────────


class TestLoadAllPersonas:
    """Test bulk loading of all personas."""

    def test_load_all_finds_all_personas(self) -> None:
        personas = load_all_personas(PERSONAS_DIR)
        assert len(personas) == 15

    def test_load_all_returns_sorted_by_tag(self) -> None:
        personas = load_all_personas(PERSONAS_DIR)
        tags = [p.tag for p in personas]
        assert tags == sorted(tags)

    def test_load_all_with_mappings(self) -> None:
        mappings = {
            "GER": "personas/germany",
            "SOV": "personas/soviet_union",
            "USA": "personas/usa",
            "ENG": "personas/united_kingdom",
            "JAP": "personas/japan",
            "ITA": "personas/italy",
        }
        personas = load_all_personas(PERSONAS_DIR, mappings=mappings)
        assert len(personas) == 6
        loaded_tags = {p.tag for p in personas}
        assert loaded_tags == {"GER", "SOV", "USA", "ENG", "JAP", "ITA"}

    def test_all_tags_are_major_powers(self) -> None:
        personas = load_all_personas(PERSONAS_DIR)
        for persona in personas:
            assert persona.tag in MAJOR_POWERS, (
                f"{persona.name} has invalid tag '{persona.tag}'"
            )
