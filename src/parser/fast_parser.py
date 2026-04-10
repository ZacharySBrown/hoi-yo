"""Fast targeted extractor for real HOI4 save files.

Instead of parsing the entire 50MB+ save into a dict, this module
scans the file line-by-line and extracts only the data we need for
the board state. Much faster and more robust than full Clausewitz parsing.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.interfaces import CountryState, ParsedSaveData, WarData, MAJOR_POWERS


def parse_save_fast(save_path: Path) -> ParsedSaveData:
    """Fast extraction of game state from a real HOI4 plaintext save."""
    text = save_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Top-level fields
    date = _extract_quoted(lines, "date", "1936.1.1")
    world_tension_line = _find_value(lines, "world_tension", limit=2000)
    world_tension = float(world_tension_line) if world_tension_line else 0.0

    # Count factories from states (they're per-state, not per-country)
    factory_counts = _count_factories_by_owner(lines)

    # Find the countries block
    countries = {}
    for tag in MAJOR_POWERS:
        country = _extract_country(lines, tag)
        if country:
            fc = factory_counts.get(tag, {})
            country.mil_factories = fc.get("arms_factory", 0)
            country.civ_factories = fc.get("industrial_complex", 0)
            country.dockyards = fc.get("dockyard", 0)
            countries[tag] = country

    # Extract wars
    wars = _extract_wars(lines)

    # Cross-reference wars to set at_war/enemies
    for war in wars:
        for tag in war.attackers:
            if tag in countries:
                countries[tag].at_war = True
                countries[tag].enemies.extend(
                    [t for t in war.defenders if t in MAJOR_POWERS and t != tag]
                )
        for tag in war.defenders:
            if tag in countries:
                countries[tag].at_war = True
                countries[tag].enemies.extend(
                    [t for t in war.attackers if t in MAJOR_POWERS and t != tag]
                )

    # Deduplicate enemies
    for c in countries.values():
        c.enemies = list(set(c.enemies))

    capitulated = [tag for tag, c in countries.items() if c.surrender_progress >= 1.0]
    nations_at_war = sum(1 for c in countries.values() if c.at_war)

    return ParsedSaveData(
        date=date,
        turn_number=0,
        world_tension=world_tension,
        countries=countries,
        wars=wars,
        capitulated=capitulated,
        nuclear_powers=[],
        nations_at_war_count=nations_at_war,
    )


def _extract_quoted(lines: list[str], key: str, default: str = "") -> str:
    """Find key="value" in the first N lines."""
    pattern = re.compile(rf'^\s*{key}\s*=\s*"([^"]*)"', re.IGNORECASE)
    for line in lines[:3000]:
        m = pattern.match(line)
        if m:
            return m.group(1)
    return default


def _find_value(lines: list[str], key: str, limit: int = 5000) -> str | None:
    """Find key=value (unquoted) in first N lines."""
    pattern = re.compile(rf'^\s*{key}\s*=\s*(.+)', re.IGNORECASE)
    for line in lines[:limit]:
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return None


def _extract_country(lines: list[str], tag: str) -> CountryState | None:
    """Extract a country's data by finding its block in the countries section.

    Strategy: find the line with `\t{TAG}={` inside the countries block,
    then scan forward extracting key fields until we hit the closing brace
    at the same depth.
    """
    # Find the countries block start
    countries_start = None
    for i, line in enumerate(lines):
        if line.strip() == "countries={":
            countries_start = i
            break

    if countries_start is None:
        return None

    # Find the country tag within countries block
    tag_pattern = re.compile(rf'^\t{tag}=\{{')
    country_start = None
    for i in range(countries_start, len(lines)):
        if tag_pattern.match(lines[i]):
            country_start = i
            break

    if country_start is None:
        return None

    # Extract fields by scanning forward from country_start
    # We track brace depth to know when the country block ends
    depth = 0
    stability = 0.0
    war_support = 0.0
    surrender = 0.0
    manpower = 0
    mil_factories = 0
    civ_factories = 0
    dockyards = 0
    division_count = 0
    ideology = "neutrality"
    faction_name = None
    national_focus = None
    researching = []

    # Count divisions by looking for division blocks
    in_active_mission = False

    for i in range(country_start, min(country_start + 50000, len(lines))):
        line = lines[i]
        stripped = line.strip()

        # Track depth
        depth += stripped.count("{") - stripped.count("}")
        if depth <= 0 and i > country_start:
            break  # End of country block

        # Extract key=value pairs at shallow depth (within first 2-3 levels)
        if depth <= 3:
            if stripped.startswith("stability="):
                try:
                    stability = float(stripped.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("war_support="):
                try:
                    war_support = float(stripped.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("surrender_progress="):
                try:
                    surrender = float(stripped.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("manpower=") and depth <= 2:
                try:
                    val = int(float(stripped.split("=", 1)[1]))
                    if val > manpower:  # Take the largest manpower value
                        manpower = val
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("ruling_party="):
                ideology = stripped.split("=", 1)[1].strip().strip('"')
            elif stripped.startswith("num_of_military_factories="):
                try:
                    mil_factories = int(float(stripped.split("=", 1)[1]))
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("num_of_civilian_factories="):
                try:
                    civ_factories = int(float(stripped.split("=", 1)[1]))
                except (ValueError, IndexError):
                    pass
            elif stripped.startswith("num_of_naval_factories="):
                try:
                    dockyards = int(float(stripped.split("=", 1)[1]))
                except (ValueError, IndexError):
                    pass

        # Count divisions (they appear as division={ blocks within the country)
        if stripped.startswith("division={"):
            division_count += 1

        # Faction
        if stripped.startswith("faction={") and depth <= 3:
            # Look ahead for faction name
            for j in range(i, min(i + 10, len(lines))):
                fline = lines[j].strip()
                if fline.startswith("name="):
                    faction_name = fline.split("=", 1)[1].strip().strip('"')
                    break

        # National focus
        if stripped.startswith("focus={") and depth <= 3:
            for j in range(i, min(i + 5, len(lines))):
                fline = lines[j].strip()
                if fline.startswith("id="):
                    national_focus = fline.split("=", 1)[1].strip().strip('"')
                    break

    # Country name mapping
    NAMES = {
        "GER": "Germany", "SOV": "Soviet Union", "USA": "United States",
        "ENG": "United Kingdom", "JAP": "Japan", "ITA": "Italy",
    }

    return CountryState(
        tag=tag,
        name=NAMES.get(tag, tag),
        ruling_ideology=ideology,
        stability=stability,
        war_support=war_support,
        surrender_progress=surrender,
        mil_factories=mil_factories,
        civ_factories=civ_factories,
        dockyards=dockyards,
        manpower_available=manpower,
        division_count=division_count,
        faction=faction_name,
        national_focus=national_focus,
        researching=researching,
    )


def _count_factories_by_owner(lines: list[str]) -> dict[str, dict[str, int]]:
    """Count factories per owner by scanning the states section.

    States contain buildings like arms_factory, industrial_complex, dockyard
    with level=N, and an owner="TAG" field. We aggregate by owner.
    """
    result: dict[str, dict[str, int]] = {}

    # Find the states block
    states_start = None
    for i, line in enumerate(lines):
        if line.strip() == "states={":
            states_start = i
            break

    if states_start is None:
        return result

    # Scan states -- each state has owner="TAG" and building blocks
    # We look for owner and factory levels within each state
    FACTORY_TYPES = {"arms_factory", "industrial_complex", "dockyard"}
    current_owner = None
    depth = 0
    state_depth = 0
    in_state = False

    for i in range(states_start, len(lines)):
        line = lines[i]
        stripped = line.strip()

        depth += stripped.count("{") - stripped.count("}")

        # Detect end of states block
        if depth <= 0 and i > states_start:
            break

        # Track state boundaries (depth 1 = inside states, depth 2 = inside a state)
        if stripped.startswith("owner="):
            current_owner = stripped.split("=", 1)[1].strip().strip('"')

        # Look for factory level lines
        for ftype in FACTORY_TYPES:
            if stripped.startswith(f"{ftype}="):
                # Inline: arms_factory=3 or block: arms_factory={
                val = stripped.split("=", 1)[1].strip().strip("{}")
                if val:
                    try:
                        level = int(float(val))
                        if current_owner and level > 0:
                            if current_owner not in result:
                                result[current_owner] = {}
                            result[current_owner][ftype] = result[current_owner].get(ftype, 0) + level
                    except ValueError:
                        pass
            elif stripped == f"level=" or stripped.startswith("level="):
                # Check if we're inside a factory block -- look back a few lines
                for back in range(max(0, i - 5), i):
                    back_stripped = lines[back].strip()
                    for ft in FACTORY_TYPES:
                        if back_stripped.startswith(f"{ft}="):
                            try:
                                level = int(float(stripped.split("=", 1)[1]))
                                if current_owner and level > 0:
                                    if current_owner not in result:
                                        result[current_owner] = {}
                                    result[current_owner][ft] = result[current_owner].get(ft, 0) + level
                            except (ValueError, IndexError):
                                pass
                            break
                    else:
                        continue
                    break

    return result


def _extract_wars(lines: list[str]) -> list[WarData]:
    """Extract active wars from the save file."""
    wars = []

    # Find active_wars or previous_wars blocks
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("active_war={") or (stripped == "active_war={"):
            war = _parse_war_block(lines, i)
            if war:
                wars.append(war)
        i += 1

    return wars


def _parse_war_block(lines: list[str], start: int) -> WarData | None:
    """Parse a single war block."""
    depth = 0
    name = "Unknown War"
    attackers = []
    defenders = []
    start_date = ""
    in_attackers = False
    in_defenders = False

    for i in range(start, min(start + 500, len(lines))):
        line = lines[i].strip()
        depth += line.count("{") - line.count("}")

        if depth <= 0 and i > start:
            break

        if line.startswith("name="):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("start_date="):
            start_date = line.split("=", 1)[1].strip().strip('"')
        elif "attacker={" in line:
            in_attackers = True
            in_defenders = False
        elif "defender={" in line:
            in_defenders = True
            in_attackers = False
        elif line.startswith("country="):
            country = line.split("=", 1)[1].strip().strip('"')
            if in_attackers:
                attackers.append(country)
            elif in_defenders:
                defenders.append(country)

    if not attackers and not defenders:
        return None

    return WarData(
        name=name,
        attackers=attackers,
        defenders=defenders,
        start_date=start_date,
    )
