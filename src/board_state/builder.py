"""Builds the shared board state prompt from parsed save data.

The board state is a compact text document (~5000-8000 tokens) summarizing
the entire game situation. It is shared (and cached) across all 6 agent
calls each turn.
"""

from __future__ import annotations

from src.interfaces import (
    BoardState,
    CountryState,
    MAJOR_POWERS,
    ParsedSaveData,
    WarData,
)


class BoardStateBuilder:
    """Builds the shared board state prompt from parsed save data."""

    def build(self, raw_state: ParsedSaveData) -> BoardState:
        """Generate a BoardState from parsed save data.

        The summary text targets 5000-8000 tokens and is designed to be
        placed in the system prompt with a cache breakpoint so all 6
        parallel agent calls can reuse it.
        """
        sections = [
            self._header(raw_state),
            self._world_situation(raw_state),
            self._major_powers_summary(raw_state),
            self._active_wars(raw_state),
            self._faction_status(raw_state),
        ]
        summary = "\n\n".join(sections)

        return BoardState(
            date=raw_state.date,
            turn_number=raw_state.turn_number,
            world_tension=raw_state.world_tension,
            summary=summary,
            countries=raw_state.countries,
            wars=raw_state.wars,
        )

    # ── Section builders ─────────────────────────────────────────────

    def _header(self, state: ParsedSaveData) -> str:
        return (
            f"## BOARD STATE -- {state.date}\n"
            f"Turn: {state.turn_number} | World Tension: {state.world_tension:.1f}%"
        )

    def _world_situation(self, state: ParsedSaveData) -> str:
        capitulated = ", ".join(state.capitulated) if state.capitulated else "None"
        if state.nuclear_powers:
            nukes = "Researched by " + ", ".join(state.nuclear_powers)
        else:
            nukes = "Not yet available"

        return (
            "## WORLD SITUATION\n"
            f"- Active wars: {len(state.wars)}\n"
            f"- Nations at war: {state.nations_at_war_count}\n"
            f"- Nations capitulated: {capitulated}\n"
            f"- Nuclear weapons: {nukes}"
        )

    def _major_powers_summary(self, state: ParsedSaveData) -> str:
        """Compact summary of all 6 major powers."""
        lines = ["## MAJOR POWERS"]
        for tag in MAJOR_POWERS:
            country = state.countries.get(tag)
            if country is None:
                lines.append(f"\n### {tag} -- No data available")
                continue
            lines.append(self._country_block(country))
        return "\n".join(lines)

    def _country_block(self, c: CountryState) -> str:
        war_status = (
            f"AT WAR with {', '.join(c.enemies)}" if c.at_war else "At peace"
        )
        return (
            f"\n### {c.name} ({c.tag}) -- {war_status}\n"
            f"- Factories: {c.mil_factories} MIC / {c.civ_factories} CIC / {c.dockyards} NIC\n"
            f"- Divisions: {c.division_count} ({c.manpower_available:,} manpower available)\n"
            f"- Surrender: {c.surrender_progress:.0%} | "
            f"War Support: {c.war_support:.0%} | "
            f"Stability: {c.stability:.0%}\n"
            f"- Faction: {c.faction or 'None'} | Ideology: {c.ruling_ideology}\n"
            f"- Army: {c.army_summary or 'N/A'} | "
            f"Navy: {c.navy_summary or 'N/A'} | "
            f"Air: {c.air_summary or 'N/A'}"
        )

    def _active_wars(self, state: ParsedSaveData) -> str:
        lines = ["## ACTIVE WARS"]
        if not state.wars:
            lines.append("No active wars.")
            return "\n".join(lines)

        for war in state.wars:
            lines.append(
                f"- {war.name}: {war.attackers_str} vs {war.defenders_str} "
                f"(since {war.start_date})"
            )
            if war.front_summary:
                lines.append(f"  Front: {war.front_summary}")
        return "\n".join(lines)

    def _faction_status(self, state: ParsedSaveData) -> str:
        """Summarize faction membership for all major powers."""
        lines = ["## FACTION STATUS"]
        factions: dict[str, list[str]] = {}
        unaligned: list[str] = []

        for tag in MAJOR_POWERS:
            country = state.countries.get(tag)
            if country is None:
                continue
            if country.faction:
                factions.setdefault(country.faction, []).append(
                    f"{country.name} ({tag})"
                )
            else:
                unaligned.append(f"{country.name} ({tag})")

        for faction_name, members in factions.items():
            lines.append(f"- {faction_name}: {', '.join(members)}")

        if unaligned:
            lines.append(f"- Unaligned: {', '.join(unaligned)}")

        if len(lines) == 1:
            lines.append("No factions formed yet.")

        return "\n".join(lines)
