"""Model selection based on game situation complexity.

Routes each agent call to the appropriate Claude model tier:
- Haiku: peacetime routine, no active threats
- Sonnet: active war, moderate complexity
- Opus: crisis situations requiring deep reasoning

Target cost distribution: ~60% Haiku, ~30% Sonnet, ~10% Opus.
"""

from __future__ import annotations

from src.config import ApiConfig
from src.interfaces import CountryState, Persona


def select_model(
    persona: Persona,
    state: CountryState,
    api_config: ApiConfig,
) -> str:
    """Return the full model ID string based on crisis scoring.

    Scoring:
        at_war             +3
        surrender > 0.2    +4
        multi-front (>2)   +2
        recently_invaded   +5
        new_war_this_turn  +4
        ally_capitulated   +3
        focus_choices > 0  +1
        faction_invite     +2

    Thresholds:
        >= 7  -> opus   (crisis_model)
        >= 3  -> sonnet (war_model)
        <  3  -> haiku  (default_model)
    """
    crisis_score = _compute_crisis_score(state)

    if crisis_score >= 7:
        return api_config.crisis_model
    elif crisis_score >= 3:
        return api_config.war_model
    else:
        return api_config.default_model


def _compute_crisis_score(state: CountryState) -> int:
    """Compute a numeric crisis score from the country's situation."""
    score = 0

    # War status
    if state.at_war:
        score += 3
        if state.surrender_progress > 0.2:
            score += 4  # Losing badly
        if state.enemies_count > 2:
            score += 2  # Multi-front war

    # Major events
    if state.recently_invaded:
        score += 5
    if state.ally_capitulated_this_turn:
        score += 3
    if state.new_war_this_turn:
        score += 4

    # Key decision points
    if state.available_focus_choices > 0:
        score += 1
    if state.faction_invite_pending:
        score += 2

    return score
