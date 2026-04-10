"""Configuration loading for hoi-yo."""

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
    """Maps country tags to persona directory paths."""
    mappings: dict[str, str] = field(default_factory=dict)

    def get_path(self, tag: str) -> Path:
        return Path(self.mappings[tag])


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
    personas = PersonaMapping(mappings=personas_raw)

    api_raw = raw.get("api", {})
    api = ApiConfig(**{k: v for k, v in api_raw.items()})

    dash_raw = raw.get("dashboard", {})
    dashboard = DashboardConfig(**{k: v for k, v in dash_raw.items()})

    cloud_raw = raw.get("cloud", {})
    cloud = CloudConfig(**{k: v for k, v in cloud_raw.items()})

    return HoiYoConfig(game=game, personas=personas, api=api, dashboard=dashboard, cloud=cloud)
