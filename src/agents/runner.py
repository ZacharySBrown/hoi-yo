"""Parallel agent runner that calls Claude API for each persona.

Each turn, all 6 persona agents are called concurrently via
``asyncio.gather``.  The system prompt is structured for efficient
prompt caching:

    [CACHED -- written once, read 6x per turn]
    +-- Game Rules Prompt (~3000 tokens)    -- static, 1-hour cache
    +-- Board State (~5000-8000 tokens)     -- changes each turn, 5-min cache
    [NOT CACHED -- unique per agent]
    +-- SOUL.md persona (~1500 tokens)
    +-- Country-specific detail (~500 tokens)
    +-- User message with turn context (~300 tokens)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from src.agents.model_router import select_model
from src.agents.schema import SUBMIT_STRATEGY_TOOL
from src.board_state.prompts import GAME_RULES_PROMPT
from src.config import ApiConfig
from src.interfaces import (
    AgentDecision,
    BoardState,
    CountryState,
    Persona,
)

logger = logging.getLogger(__name__)


async def run_agents(
    personas: list[Persona],
    board_state: BoardState,
    turn: int,
    client: AsyncAnthropic,
    api_config: ApiConfig,
) -> list[AgentDecision]:
    """Run all persona agents in parallel, sharing cached board state.

    Returns one ``AgentDecision`` per persona, in the same order as the
    input ``personas`` list.
    """
    # Build the shared system prompt prefix (cached across all agents)
    shared_system = _build_shared_system(board_state, api_config)

    # Fan out to all agents concurrently
    tasks = [
        _call_agent(persona, shared_system, board_state, turn, client, api_config)
        for persona in personas
    ]
    return list(await asyncio.gather(*tasks))


def _build_shared_system(
    board_state: BoardState,
    api_config: ApiConfig,
) -> list[dict[str, Any]]:
    """Build the cached portion of the system prompt.

    Two cache breakpoints:
    1. Game rules -- static, 1-hour TTL
    2. Board state -- changes each turn, 5-minute TTL (default ephemeral)
    """
    return [
        {
            "type": "text",
            "text": GAME_RULES_PROMPT,
            "cache_control": {"type": "ephemeral", "ttl": api_config.cache_ttl_static},
        },
        {
            "type": "text",
            "text": board_state.to_prompt(),
            "cache_control": {"type": "ephemeral"},
        },
    ]


async def _call_agent(
    persona: Persona,
    shared_system: list[dict[str, Any]],
    board_state: BoardState,
    turn: int,
    client: AsyncAnthropic,
    api_config: ApiConfig,
) -> AgentDecision:
    """Call a single persona agent and parse the result."""

    # Persona-specific system block (NOT cached -- varies per agent)
    persona_block = {
        "type": "text",
        "text": persona.soul_prompt,
    }

    system_blocks = shared_system + [persona_block]

    # Country-specific user message
    country_state = board_state.get_country_detail(persona.tag)
    user_msg = _build_user_message(board_state, country_state, persona.tag, turn)

    # Model routing per agent
    model = select_model(persona, country_state, api_config) if country_state else api_config.default_model

    logger.info("Agent %s: calling %s", persona.tag, model)

    response = await client.messages.create(
        model=model,
        max_tokens=api_config.max_output_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_msg}],
        tools=[SUBMIT_STRATEGY_TOOL],
        tool_choice={"type": "tool", "name": "submit_strategy"},
    )

    # Extract the tool use block from the response
    data = _extract_tool_input(response)

    decision = AgentDecision.from_json(
        tag=persona.tag,
        turn=turn,
        data=data,
        model=model,
    )

    logger.info(
        "Agent %s: mood=%s, %d diplomatic, %d military, %d production strategies",
        persona.tag,
        decision.mood,
        len(decision.diplomatic_strategies),
        len(decision.military_strategies),
        len(decision.production_strategies),
    )

    return decision


def _build_user_message(
    board_state: BoardState,
    country_state: CountryState | None,
    tag: str,
    turn: int,
) -> str:
    """Build the per-agent user message with country-specific context."""
    if country_state is None:
        country_detail = "No detailed country data available."
    else:
        country_detail = (
            f"Tag: {country_state.tag}\n"
            f"Ideology: {country_state.ruling_ideology}\n"
            f"Stability: {country_state.stability:.0%} | "
            f"War Support: {country_state.war_support:.0%}\n"
            f"Factories: {country_state.mil_factories} MIC / "
            f"{country_state.civ_factories} CIC / {country_state.dockyards} NIC\n"
            f"Divisions: {country_state.division_count} "
            f"({country_state.manpower_available:,} manpower)\n"
            f"Research slots: {country_state.research_slots}\n"
            f"Researching: {', '.join(country_state.researching) or 'None'}\n"
            f"National focus: {country_state.national_focus or 'None'}"
        )

    recent_events = board_state.recent_events_for(tag)

    return (
        f"TURN {turn} | Date: {board_state.date}\n\n"
        f"YOUR COUNTRY STATE:\n{country_detail}\n\n"
        f"RECENT EVENTS:\n{recent_events}\n\n"
        "Respond with your strategic decisions by calling the submit_strategy tool. "
        "Include a brief inner_monologue written in-character explaining your reasoning."
    )


def _extract_tool_input(response: Any) -> dict:
    """Extract the submit_strategy tool input from a Claude response.

    The response uses forced tool_use, so exactly one tool_use content
    block is expected.
    """
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_strategy":
            return block.input

    # Fallback: try to parse text content as JSON
    for block in response.content:
        if block.type == "text" and block.text.strip():
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                pass

    raise ValueError(
        f"No submit_strategy tool call found in response. "
        f"Content blocks: {[b.type for b in response.content]}"
    )
