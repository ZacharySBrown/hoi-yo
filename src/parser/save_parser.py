"""HOI4 save file parser.

Reads a plaintext Clausewitz-format .hoi4 save and produces a
ParsedSaveData instance with structured game state for each major power.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.interfaces import (
    MAJOR_POWERS,
    CountryState,
    ParsedSaveData,
    WarData,
)
from src.parser.clausewitz import parse_clausewitz

logger = logging.getLogger(__name__)

# Human-readable country names
_COUNTRY_NAMES: dict[str, str] = {
    "GER": "Germany",
    "SOV": "Soviet Union",
    "USA": "United States",
    "ENG": "United Kingdom",
    "JAP": "Japan",
    "ITA": "Italy",
    "FRA": "France",
    "CHI": "China",
    "POL": "Poland",
}


def parse_save(save_path: Path) -> ParsedSaveData:
    """Parse an HOI4 plaintext save file into structured game state.

    Args:
        save_path: Path to the plaintext .hoi4 save file.

    Returns:
        ParsedSaveData with date, world tension, country states, wars, etc.

    Raises:
        FileNotFoundError: If save_path does not exist.
        ValueError: If the file cannot be parsed at all.
    """
    text = save_path.read_text(encoding="utf-8", errors="replace")
    data = parse_clausewitz(text)

    date = _extract_str(data, "date", "1936.1.1")
    turn_number = _estimate_turn(date)
    world_tension = _extract_float(data, "world_tension", 0.0)

    # --- Countries ---
    countries_raw = data.get("countries", {})
    if not isinstance(countries_raw, dict):
        countries_raw = {}

    countries: dict[str, CountryState] = {}
    for tag in MAJOR_POWERS:
        country_data = countries_raw.get(tag)
        if country_data is None:
            continue
        if not isinstance(country_data, dict):
            logger.warning("Country %s data is not a dict, skipping", tag)
            continue
        countries[tag] = _parse_country(tag, country_data)

    # --- Wars ---
    wars = _parse_wars(data)

    # Determine which countries are at war and set enemies from war data
    _apply_war_state(countries, wars)

    # --- Capitulated & nuclear ---
    capitulated = _parse_capitulated(data, countries_raw)
    nuclear_powers = _parse_nuclear_powers(data, countries_raw)
    nations_at_war = sum(1 for c in countries.values() if c.at_war)

    return ParsedSaveData(
        date=date,
        turn_number=turn_number,
        world_tension=world_tension,
        countries=countries,
        wars=wars,
        capitulated=capitulated,
        nuclear_powers=nuclear_powers,
        nations_at_war_count=nations_at_war,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_str(data: dict, key: str, default: str = "") -> str:
    val = data.get(key, default)
    return str(val) if val is not None else default


def _extract_float(data: dict, key: str, default: float = 0.0) -> float:
    val = data.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _extract_int(data: dict, key: str, default: int = 0) -> int:
    val = data.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _estimate_turn(date_str: str) -> int:
    """Estimate a turn number from the in-game date.

    Assumes monthly turns starting from 1936.1.1 (turn 0).
    """
    try:
        parts = date_str.split(".")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        return (year - 1936) * 12 + (month - 1)
    except (ValueError, IndexError):
        return 0


def _parse_country(tag: str, data: dict[str, Any]) -> CountryState:
    """Extract a CountryState from a country's raw parsed data."""
    name = _COUNTRY_NAMES.get(tag, tag)
    ruling_ideology = _extract_str(data, "ruling_party", "neutrality")
    stability = _extract_float(data, "stability", 0.5)
    war_support = _extract_float(data, "war_support", 0.5)
    surrender_progress = _extract_float(data, "surrender_progress", 0.0)
    manpower = _extract_int(data, "manpower", 0)

    # Factories
    mil_factories = _extract_int(data, "mil_factories", 0)
    civ_factories = _extract_int(data, "civ_factories", 0)
    dockyards = _extract_int(data, "dockyards", 0)

    # Divisions
    division_count = _count_divisions(data)

    # Faction
    faction = _extract_str(data, "faction", "") or None

    # Research
    research_raw = data.get("research", {})
    researching: list[str] = []
    if isinstance(research_raw, dict):
        researching = list(research_raw.keys())
    elif isinstance(research_raw, list):
        researching = [str(r) for r in research_raw]
    research_slots = _extract_int(data, "research_slots", 3)

    # National focus
    national_focus = _extract_str(data, "national_focus", "") or None

    return CountryState(
        tag=tag,
        name=name,
        ruling_ideology=ruling_ideology,
        stability=stability,
        war_support=war_support,
        surrender_progress=surrender_progress,
        mil_factories=mil_factories,
        civ_factories=civ_factories,
        dockyards=dockyards,
        manpower_available=manpower,
        division_count=division_count,
        at_war=False,  # set later by _apply_war_state
        enemies=[],
        faction=faction,
        research_slots=research_slots,
        researching=researching,
        national_focus=national_focus,
    )


def _count_divisions(data: dict[str, Any]) -> int:
    """Count divisions from various possible save structures."""
    # Direct count field
    count = _extract_int(data, "division_count", -1)
    if count >= 0:
        return count

    # Divisions as a list of sub-blocks
    divs = data.get("divisions", [])
    if isinstance(divs, list):
        return len(divs)
    if isinstance(divs, dict):
        return len(divs)
    return 0


def _parse_wars(data: dict[str, Any]) -> list[WarData]:
    """Extract active wars from the save data."""
    wars: list[WarData] = []

    # Wars can be under "active_wars" (a block containing "war" entries)
    # or directly as "war" at the top level.
    active_wars_block = data.get("active_wars")
    if isinstance(active_wars_block, dict):
        # active_wars={ war={...} war={...} } => dict with "war" key
        wars_raw = active_wars_block.get("war")
    else:
        # Fallback: "war" at top level
        wars_raw = data.get("war")

    if wars_raw is None:
        return wars

    # Normalize: single war dict -> list of one; list stays as-is
    if isinstance(wars_raw, dict):
        wars_raw = [wars_raw]
    elif not isinstance(wars_raw, list):
        return wars

    for war_data in wars_raw:
        if not isinstance(war_data, dict):
            continue
        war = _parse_single_war(war_data)
        if war:
            wars.append(war)

    return wars


def _parse_single_war(data: dict[str, Any]) -> WarData | None:
    """Parse a single war entry."""
    name = _extract_str(data, "name", "Unknown War")

    # Attackers and defenders
    attackers = _parse_war_participants(data.get("attackers"))
    defenders = _parse_war_participants(data.get("defenders"))

    if not attackers and not defenders:
        # Try alternative structure: original_attacker / original_defender
        attacker = _extract_str(data, "original_attacker", "")
        defender = _extract_str(data, "original_defender", "")
        if attacker:
            attackers = [attacker]
        if defender:
            defenders = [defender]

    start_date = _extract_str(data, "start_date", "")

    return WarData(
        name=name,
        attackers=attackers,
        defenders=defenders,
        start_date=start_date,
    )


def _parse_war_participants(raw: Any) -> list[str]:
    """Extract a list of country tags from a war participants field."""
    if raw is None:
        return []
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                tag = item.get("country") or item.get("tag", "")
                if tag:
                    result.append(str(tag))
        return result
    if isinstance(raw, dict):
        # Single participant as dict
        tag = raw.get("country") or raw.get("tag", "")
        return [str(tag)] if tag else []
    if isinstance(raw, str):
        return [raw]
    return []


def _apply_war_state(
    countries: dict[str, CountryState],
    wars: list[WarData],
) -> None:
    """Set at_war and enemies fields on countries based on parsed wars."""
    for war in wars:
        all_attackers = set(war.attackers)
        all_defenders = set(war.defenders)

        for tag, country in countries.items():
            if tag in all_attackers:
                country.at_war = True
                for enemy_tag in all_defenders:
                    if enemy_tag not in country.enemies:
                        country.enemies.append(enemy_tag)
            elif tag in all_defenders:
                country.at_war = True
                for enemy_tag in all_attackers:
                    if enemy_tag not in country.enemies:
                        country.enemies.append(enemy_tag)


def _parse_capitulated(
    data: dict[str, Any],
    countries_raw: dict[str, Any],
) -> list[str]:
    """Find nations that have capitulated (surrender_progress >= 1.0)."""
    # Check for explicit capitulated list
    cap_list = data.get("capitulated", [])
    if isinstance(cap_list, list) and cap_list:
        return [str(c) for c in cap_list]

    # Infer from surrender_progress
    result: list[str] = []
    for tag, cdata in countries_raw.items():
        if not isinstance(cdata, dict):
            continue
        sp = _extract_float(cdata, "surrender_progress", 0.0)
        if sp >= 1.0:
            result.append(tag)
    return result


def _parse_nuclear_powers(
    data: dict[str, Any],
    countries_raw: dict[str, Any],
) -> list[str]:
    """Find nations that have nuclear capability."""
    # Check for explicit list
    nuke_list = data.get("nuclear_powers", [])
    if isinstance(nuke_list, list) and nuke_list:
        return [str(c) for c in nuke_list]

    # Infer from country data
    result: list[str] = []
    for tag, cdata in countries_raw.items():
        if not isinstance(cdata, dict):
            continue
        nukes = _extract_int(cdata, "nukes", 0)
        has_bomb = cdata.get("has_nuclear_bomb", False)
        if nukes > 0 or has_bomb is True:
            result.append(tag)
    return result
