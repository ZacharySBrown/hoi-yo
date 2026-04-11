"""Persona loader for hoi-yo.

Loads SOUL.md personality files and config.toml metadata from persona
directories, returning Persona objects ready for the agent loop.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from src.interfaces import Persona


def load_persona(persona_dir: Path) -> Persona:
    """Load a single persona from a directory containing SOUL.md and config.toml.

    Args:
        persona_dir: Path to a persona directory (e.g. personas/germany/).

    Returns:
        A Persona object with tag, name, soul_prompt, and base_strategies.

    Raises:
        FileNotFoundError: If SOUL.md or config.toml is missing.
        tomllib.TOMLDecodeError: If config.toml is malformed.
    """
    soul_path = persona_dir / "SOUL.md"
    config_path = persona_dir / "config.toml"

    soul_prompt = soul_path.read_text(encoding="utf-8")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    return Persona(
        tag=config["tag"],
        name=config["name"],
        soul_prompt=soul_prompt,
        base_strategies=config.get("base_strategies", {}),
    )


def load_all_personas(
    personas_dir: Path,
    mappings: dict[str, str] | None = None,
) -> list[Persona]:
    """Load all configured personas from the personas directory.

    If *mappings* is provided (tag -> directory name), only those personas
    are loaded. Otherwise every subdirectory that contains a SOUL.md is loaded.

    Args:
        personas_dir: Root personas/ directory.
        mappings: Optional dict mapping country tags to persona directory names
                  (e.g. {"GER": "personas/germany"}).

    Returns:
        List of Persona objects, sorted by tag.
    """
    personas: list[Persona] = []

    if mappings:
        for _tag, dir_name in mappings.items():
            persona_path = Path(dir_name)
            # If the mapping is a relative path, resolve against personas_dir parent
            if not persona_path.is_absolute():
                persona_path = personas_dir.parent / persona_path
            if persona_path.is_dir() and (persona_path / "SOUL.md").exists():
                personas.append(load_persona(persona_path))
    else:
        for subdir in sorted(personas_dir.iterdir()):
            if subdir.is_dir() and (subdir / "SOUL.md").exists():
                personas.append(load_persona(subdir))

    return sorted(personas, key=lambda p: p.tag)


def discover_personas(personas_dir: Path) -> dict[str, list[dict]]:
    """Scan personas directory and return all available personas grouped by tag.

    Returns a dict mapping country tags to lists of persona metadata::

        {"SOV": [
            {"path": "personas/soviet_union", "name": "Joseph Stalin", "tag": "SOV", "excerpt": "..."},
            {"path": "personas/soviet_union_alt_trotsky", "name": "Leon Trotsky", ...},
        ]}
    """
    result: dict[str, list[dict]] = {}

    for subdir in sorted(personas_dir.iterdir()):
        if not subdir.is_dir():
            continue
        soul_path = subdir / "SOUL.md"
        config_path = subdir / "config.toml"
        if not soul_path.exists() or not config_path.exists():
            continue

        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
            tag = config.get("tag", "")
            name = config.get("name", subdir.name)

            # Extract excerpt: first non-header, non-empty line(s) from SOUL.md
            soul_text = soul_path.read_text(encoding="utf-8")
            excerpt_lines = []
            for line in soul_text.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    if excerpt_lines:
                        break
                    continue
                excerpt_lines.append(stripped)
                if len(" ".join(excerpt_lines)) >= 150:
                    break
            excerpt = " ".join(excerpt_lines)[:200]

            entry = {
                "path": str(subdir),
                "name": name,
                "tag": tag,
                "excerpt": excerpt,
            }

            if tag not in result:
                result[tag] = []
            result[tag].append(entry)
        except Exception:
            continue

    return result
