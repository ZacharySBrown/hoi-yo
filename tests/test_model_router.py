"""Tests for model routing based on crisis level."""

from __future__ import annotations

from src.agents.model_router import select_model, _compute_crisis_score
from src.config import ApiConfig
from src.interfaces import CountryState, Persona


# ── Fixtures ─────────────────────────────────────────────────────────


def _default_api_config() -> ApiConfig:
    return ApiConfig(
        default_model="claude-haiku-4-5",
        war_model="claude-sonnet-4-6",
        crisis_model="claude-opus-4-6",
    )


def _make_persona(tag: str = "GER") -> Persona:
    return Persona(tag=tag, name="Test Persona", soul_prompt="You are a test.")


def _make_country(
    tag: str = "GER",
    *,
    at_war: bool = False,
    enemies: list[str] | None = None,
    surrender_progress: float = 0.0,
) -> CountryState:
    return CountryState(
        tag=tag,
        name="Test Country",
        ruling_ideology="fascism",
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
    )


# ── Tests: Crisis Score Computation ──────────────────────────────────


class TestCrisisScore:
    """Verify crisis score computation for various scenarios."""

    def test_peacetime_score_is_zero(self) -> None:
        state = _make_country(at_war=False)
        assert _compute_crisis_score(state) == 0

    def test_at_war_gives_base_3(self) -> None:
        state = _make_country(at_war=True, enemies=["SOV"])
        assert _compute_crisis_score(state) == 3

    def test_losing_war_adds_4(self) -> None:
        state = _make_country(
            at_war=True,
            enemies=["SOV"],
            surrender_progress=0.3,
        )
        # at_war(3) + surrender>0.2(4) = 7
        assert _compute_crisis_score(state) == 7

    def test_multi_front_adds_2(self) -> None:
        state = _make_country(
            at_war=True,
            enemies=["SOV", "ENG", "USA"],
        )
        # at_war(3) + multi-front(2) = 5
        assert _compute_crisis_score(state) == 5

    def test_losing_multi_front_crisis(self) -> None:
        state = _make_country(
            at_war=True,
            enemies=["SOV", "ENG", "USA"],
            surrender_progress=0.5,
        )
        # at_war(3) + surrender(4) + multi-front(2) = 9
        assert _compute_crisis_score(state) == 9

    def test_not_at_war_surrender_ignored(self) -> None:
        """Surrender progress only matters when at war."""
        state = _make_country(at_war=False, surrender_progress=0.5)
        assert _compute_crisis_score(state) == 0

    def test_at_war_boundary_surrender(self) -> None:
        """Surrender at exactly 0.2 should NOT trigger the +4."""
        state = _make_country(
            at_war=True,
            enemies=["SOV"],
            surrender_progress=0.2,
        )
        # at_war(3) only -- 0.2 is not > 0.2
        assert _compute_crisis_score(state) == 3

    def test_enemies_exactly_two_no_multifront(self) -> None:
        """Two enemies is NOT multi-front (need > 2)."""
        state = _make_country(
            at_war=True,
            enemies=["SOV", "ENG"],
        )
        # at_war(3) only
        assert _compute_crisis_score(state) == 3


# ── Tests: Model Selection ───────────────────────────────────────────


class TestModelSelection:
    """Verify model selection maps crisis scores to correct model tiers."""

    def test_peacetime_selects_haiku(self) -> None:
        persona = _make_persona()
        state = _make_country(at_war=False)
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-haiku-4-5"

    def test_at_war_selects_sonnet(self) -> None:
        persona = _make_persona()
        state = _make_country(at_war=True, enemies=["SOV"])
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-sonnet-4-6"

    def test_crisis_selects_opus(self) -> None:
        persona = _make_persona()
        state = _make_country(
            at_war=True,
            enemies=["SOV"],
            surrender_progress=0.3,
        )
        # Score = 7 (at_war + losing) -> opus
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-opus-4-6"

    def test_severe_crisis_selects_opus(self) -> None:
        persona = _make_persona()
        state = _make_country(
            at_war=True,
            enemies=["SOV", "ENG", "USA"],
            surrender_progress=0.5,
        )
        # Score = 9 -> opus
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-opus-4-6"

    def test_multi_front_without_losing_selects_sonnet(self) -> None:
        persona = _make_persona()
        state = _make_country(
            at_war=True,
            enemies=["SOV", "ENG", "USA"],
        )
        # Score = 5 -> sonnet
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-sonnet-4-6"

    def test_custom_api_config_model_names(self) -> None:
        """Model names come from ApiConfig, not hardcoded."""
        config = ApiConfig(
            default_model="custom-haiku",
            war_model="custom-sonnet",
            crisis_model="custom-opus",
        )
        persona = _make_persona()

        # Peacetime
        state_peace = _make_country(at_war=False)
        assert select_model(persona, state_peace, config) == "custom-haiku"

        # War
        state_war = _make_country(at_war=True, enemies=["SOV"])
        assert select_model(persona, state_war, config) == "custom-sonnet"

        # Crisis
        state_crisis = _make_country(
            at_war=True,
            enemies=["SOV"],
            surrender_progress=0.3,
        )
        assert select_model(persona, state_crisis, config) == "custom-opus"

    def test_threshold_boundary_score_3(self) -> None:
        """Score exactly 3 should select sonnet."""
        persona = _make_persona()
        state = _make_country(at_war=True, enemies=["SOV"])
        # Score is exactly 3
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-sonnet-4-6"

    def test_threshold_boundary_score_7(self) -> None:
        """Score exactly 7 should select opus."""
        persona = _make_persona()
        state = _make_country(
            at_war=True,
            enemies=["SOV"],
            surrender_progress=0.3,
        )
        # at_war(3) + surrender(4) = exactly 7
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-opus-4-6"

    def test_score_below_3_selects_haiku(self) -> None:
        """Score of 0, 1, or 2 should all select haiku."""
        persona = _make_persona()
        state = _make_country(at_war=False)
        model = select_model(persona, state, _default_api_config())
        assert model == "claude-haiku-4-5"
