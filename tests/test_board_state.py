"""Tests for BoardStateBuilder producing valid prompts."""

from __future__ import annotations

from src.board_state.builder import BoardStateBuilder
from src.board_state.prompts import GAME_RULES_PROMPT
from src.interfaces import (
    BoardState,
    CountryState,
    MAJOR_POWERS,
    ParsedSaveData,
    WarData,
)


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_country(
    tag: str,
    name: str,
    *,
    at_war: bool = False,
    enemies: list[str] | None = None,
    faction: str | None = None,
    surrender_progress: float = 0.0,
) -> CountryState:
    return CountryState(
        tag=tag,
        name=name,
        ruling_ideology="fascism" if tag == "GER" else "democracy",
        stability=0.65,
        war_support=0.70,
        surrender_progress=surrender_progress,
        mil_factories=30,
        civ_factories=25,
        dockyards=5,
        manpower_available=500_000,
        division_count=40,
        at_war=at_war,
        enemies=enemies or [],
        faction=faction,
    )


def _make_parsed_state(
    *,
    with_wars: bool = False,
    world_tension: float = 25.0,
) -> ParsedSaveData:
    countries = {
        "GER": _make_country(
            "GER", "German Reich",
            at_war=with_wars,
            enemies=["SOV", "ENG"] if with_wars else [],
            faction="Axis",
        ),
        "SOV": _make_country(
            "SOV", "Soviet Union",
            at_war=with_wars,
            enemies=["GER"] if with_wars else [],
            faction="Comintern",
        ),
        "USA": _make_country("USA", "United States of America"),
        "ENG": _make_country(
            "ENG", "United Kingdom",
            at_war=with_wars,
            enemies=["GER"] if with_wars else [],
            faction="Allies",
        ),
        "JAP": _make_country(
            "JAP", "Empire of Japan",
            faction="Greater East Asia Co-Prosperity Sphere",
        ),
        "ITA": _make_country(
            "ITA", "Kingdom of Italy",
            faction="Axis",
        ),
    }

    wars = []
    if with_wars:
        wars.append(
            WarData(
                name="Second World War",
                attackers=["GER", "ITA"],
                defenders=["SOV", "ENG"],
                start_date="1941.6.22",
                front_summary="Eastern front stretching from Baltic to Black Sea",
            )
        )

    return ParsedSaveData(
        date="1941.7.1",
        turn_number=5,
        world_tension=world_tension,
        countries=countries,
        wars=wars,
        capitulated=["FRA"] if with_wars else [],
        nuclear_powers=[],
        nations_at_war_count=4 if with_wars else 0,
    )


# ── Tests ────────────────────────────────────────────────────────────


class TestGameRulesPrompt:
    """Verify the static game rules prompt is well-formed."""

    def test_prompt_is_nonempty(self) -> None:
        assert len(GAME_RULES_PROMPT) > 500

    def test_prompt_contains_key_sections(self) -> None:
        assert "WHAT YOU CONTROL" in GAME_RULES_PROMPT
        assert "HOW VALUES WORK" in GAME_RULES_PROMPT
        assert "STRATEGY TYPES AVAILABLE" in GAME_RULES_PROMPT
        assert "IMPORTANT CONSTRAINTS" in GAME_RULES_PROMPT
        assert "RESPONSE FORMAT" in GAME_RULES_PROMPT

    def test_prompt_mentions_strategy_types(self) -> None:
        for stype in ["conquer", "alliance", "role_ratio", "equipment_production_factor"]:
            assert stype in GAME_RULES_PROMPT, f"Missing strategy type: {stype}"


class TestBoardStateBuilder:
    """Verify BoardStateBuilder produces valid and comprehensive prompts."""

    def test_build_returns_board_state(self) -> None:
        builder = BoardStateBuilder()
        raw = _make_parsed_state()
        result = builder.build(raw)

        assert isinstance(result, BoardState)
        assert result.date == "1941.7.1"
        assert result.turn_number == 5
        assert result.world_tension == 25.0

    def test_summary_contains_header(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        assert "BOARD STATE -- 1941.7.1" in result.summary
        assert "Turn: 5" in result.summary
        assert "World Tension: 25.0%" in result.summary

    def test_summary_contains_all_major_powers(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        for tag in MAJOR_POWERS:
            assert tag in result.summary, f"Missing major power: {tag}"

    def test_summary_contains_country_details(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        assert "German Reich" in result.summary
        assert "Soviet Union" in result.summary
        assert "MIC" in result.summary
        assert "CIC" in result.summary
        assert "Stability" in result.summary

    def test_summary_contains_world_situation(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        assert "WORLD SITUATION" in result.summary
        assert "Active wars:" in result.summary
        assert "Nuclear weapons:" in result.summary

    def test_wartime_state_shows_wars(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(with_wars=True))

        assert "ACTIVE WARS" in result.summary
        assert "Second World War" in result.summary
        assert "GER, ITA vs SOV, ENG" in result.summary
        assert "1941.6.22" in result.summary

    def test_wartime_state_shows_capitulated(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(with_wars=True))

        assert "FRA" in result.summary

    def test_peacetime_no_wars(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(with_wars=False))

        assert "No active wars." in result.summary

    def test_faction_status_present(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        assert "FACTION STATUS" in result.summary
        assert "Axis" in result.summary

    def test_countries_preserved_in_board_state(self) -> None:
        builder = BoardStateBuilder()
        raw = _make_parsed_state()
        result = builder.build(raw)

        assert "GER" in result.countries
        assert result.countries["GER"].name == "German Reich"
        assert len(result.countries) == 6

    def test_wars_preserved_in_board_state(self) -> None:
        builder = BoardStateBuilder()
        raw = _make_parsed_state(with_wars=True)
        result = builder.build(raw)

        assert len(result.wars) == 1
        assert result.wars[0].name == "Second World War"

    def test_war_status_shown_for_belligerents(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(with_wars=True))

        assert "AT WAR" in result.summary

    def test_to_prompt_returns_summary(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        assert result.to_prompt() == result.summary

    def test_front_summary_included(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(with_wars=True))

        assert "Eastern front" in result.summary

    def test_high_world_tension(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state(world_tension=85.3))

        assert "85.3%" in result.summary

    def test_unaligned_powers_listed(self) -> None:
        builder = BoardStateBuilder()
        result = builder.build(_make_parsed_state())

        # USA has no faction in our test data
        assert "Unaligned" in result.summary
        assert "United States" in result.summary
