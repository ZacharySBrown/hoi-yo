"""Configuration loading and platform detection for hoi-yo."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class GameConfig:
    hoi4_executable: Path
    save_dir: Path
    mod_dir: Path
    config_dir: Path
    use_xvfb: bool = False
    autosave_interval: str = "MONTHLY"
    initial_speed: int = 3
    use_plaintext_saves: bool = True


@dataclass
class PersonaMapping:
    """Maps country tags to persona directory paths, with mode support."""
    mappings: dict[str, str] = field(default_factory=dict)
    modes: dict[str, dict[str, str]] = field(default_factory=dict)
    default_mode: str = "classic"

    def get_path(self, tag: str) -> Path:
        return Path(self.mappings[tag])

    def select_mode(self, mode: str) -> None:
        """Switch active mappings to the given mode."""
        if mode in self.modes:
            self.mappings = dict(self.modes[mode])
        else:
            available = ", ".join(sorted(self.modes.keys()))
            raise ValueError(f"Unknown persona mode '{mode}'. Available: {available}")

    @property
    def available_modes(self) -> list[str]:
        return sorted(self.modes.keys())


@dataclass
class ApiConfig:
    default_model: str = "claude-haiku-4-5"
    war_model: str = "claude-sonnet-4-6"
    crisis_model: str = "claude-opus-4-6"
    cache_ttl_static: str = "1h"
    cache_ttl_board: str = "5m"
    max_output_tokens: int = 2000


@dataclass
class DashboardConfig:
    port: int = 8080
    enable_vnc: bool = True
    vnc_port: int = 6080
    popcorn_mode_pause: int = 5


@dataclass
class CloudConfig:
    enabled: bool = False
    database_path: str = "data/hoi-yo.db"
    auto_shutdown_minutes: int = 30


@dataclass
class HoiYoConfig:
    game: GameConfig
    personas: PersonaMapping
    api: ApiConfig
    dashboard: DashboardConfig
    cloud: CloudConfig = None

    def __post_init__(self):
        if self.cloud is None:
            self.cloud = CloudConfig()


def load_config(config_path: Path) -> HoiYoConfig:
    """Load configuration from a TOML file."""
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    game_raw = raw.get("game", {})
    game = GameConfig(
        hoi4_executable=Path(game_raw.get("hoi4_executable", "")).expanduser(),
        save_dir=Path(game_raw.get("save_dir", "")).expanduser(),
        mod_dir=Path(game_raw.get("mod_dir", "")).expanduser(),
        config_dir=Path(game_raw.get("config_dir", "")).expanduser(),
        use_xvfb=game_raw.get("use_xvfb", False),
        autosave_interval=game_raw.get("autosave_interval", "MONTHLY"),
        initial_speed=game_raw.get("initial_speed", 3),
        use_plaintext_saves=game_raw.get("use_plaintext_saves", True),
    )

    personas_raw = raw.get("personas", {})
    default_mode = personas_raw.pop("default_mode", "classic")
    # Separate mode sub-tables (dicts) from flat tag mappings (strings)
    modes: dict[str, dict[str, str]] = {}
    flat_mappings: dict[str, str] = {}
    for key, value in personas_raw.items():
        if isinstance(value, dict):
            modes[key] = value
        else:
            flat_mappings[key] = value
    # If no mode sub-tables found, treat flat mappings as "classic"
    if not modes and flat_mappings:
        modes["classic"] = flat_mappings
    active = modes.get(default_mode, next(iter(modes.values()), {}))
    personas = PersonaMapping(mappings=dict(active), modes=modes, default_mode=default_mode)

    api_raw = raw.get("api", {})
    api = ApiConfig(**{k: v for k, v in api_raw.items()})

    dash_raw = raw.get("dashboard", {})
    dashboard = DashboardConfig(**{k: v for k, v in dash_raw.items()})

    cloud_raw = raw.get("cloud", {})
    cloud = CloudConfig(**{k: v for k, v in cloud_raw.items()})

    return HoiYoConfig(game=game, personas=personas, api=api, dashboard=dashboard, cloud=cloud)


# ── Platform Detection ───────────────────────────────────────────────


def _find_steam_libraries_windows() -> list[Path]:
    """Parse Steam's libraryfolders.vdf to find all library paths."""
    vdf_path = Path(r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf")
    libraries = [Path(r"C:\Program Files (x86)\Steam")]
    if not vdf_path.exists():
        return libraries
    try:
        text = vdf_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip().strip('"')
            if line.startswith("path"):
                parts = line.split('"')
                if len(parts) >= 4:
                    libraries.append(Path(parts[3].replace("\\\\", "\\")))
    except Exception:
        pass
    return libraries


def detect_hoi4_paths() -> dict[str, Path | None]:
    """Auto-detect HOI4 installation paths for the current platform.

    Returns a dict with keys: hoi4_executable, save_dir, mod_dir, config_dir.
    Values may be ``None`` if the path cannot be found.
    """
    exe: Path | None = None
    docs_base: Path | None = None

    if sys.platform == "win32":
        # Check default + all Steam library folders
        libraries = _find_steam_libraries_windows()
        for lib in libraries:
            candidate = lib / "steamapps" / "common" / "Hearts of Iron IV" / "hoi4.exe"
            if candidate.exists():
                exe = candidate
                break
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"

    elif sys.platform == "darwin":
        candidates = [
            Path.home() / "Library" / "Application Support" / "Steam"
            / "steamapps" / "common" / "Hearts of Iron IV" / "hoi4.app",
        ]
        for c in candidates:
            if c.exists():
                exe = c
                break
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"

    else:  # Linux
        candidates = [
            Path.home() / ".steam" / "steamapps" / "common" / "Hearts of Iron IV" / "hoi4",
            Path.home() / ".local" / "share" / "Steam"
            / "steamapps" / "common" / "Hearts of Iron IV" / "hoi4",
            Path("/opt/hoi4/hoi4"),
        ]
        for c in candidates:
            if c.exists():
                exe = c
                break
        docs_base = Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV"

    return {
        "hoi4_executable": exe,
        "save_dir": (docs_base / "save games") if docs_base else None,
        "mod_dir": (docs_base / "mod" / "hoi_yo_bots") if docs_base else None,
        "config_dir": docs_base,
    }


def get_app_data_dir() -> Path:
    """Return the platform-appropriate app data directory for hoi-yo config."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "hoi-yo"


def find_config() -> Path | None:
    """Search for config.toml in standard locations.

    Search order: CWD → app data dir → None.
    """
    cwd_config = Path("config.toml")
    if cwd_config.exists():
        return cwd_config

    app_config = get_app_data_dir() / "config.toml"
    if app_config.exists():
        return app_config

    return None


def write_config(path: Path, paths: dict, persona_mappings: dict[str, str] | None = None) -> None:
    """Generate a config.toml file from detected paths and settings."""
    path.parent.mkdir(parents=True, exist_ok=True)

    personas = persona_mappings or {
        "GER": "personas/germany",
        "SOV": "personas/soviet_union",
        "USA": "personas/usa",
        "ENG": "personas/united_kingdom",
        "JAP": "personas/japan",
        "ITA": "personas/italy",
    }
    persona_lines = "\n".join(f'{k} = "{v}"' for k, v in sorted(personas.items()))

    content = f"""\
[game]
hoi4_executable = "{paths.get('hoi4_executable', '')}"
save_dir = "{paths.get('save_dir', '')}"
mod_dir = "{paths.get('mod_dir', '')}"
config_dir = "{paths.get('config_dir', '')}"
autosave_interval = "MONTHLY"
initial_speed = 3
use_plaintext_saves = true

[personas]
{persona_lines}

[api]
default_model = "claude-haiku-4-5"
war_model = "claude-sonnet-4-6"
crisis_model = "claude-opus-4-6"
max_output_tokens = 2000

[dashboard]
port = 8080
"""
    path.write_text(content, encoding="utf-8")
