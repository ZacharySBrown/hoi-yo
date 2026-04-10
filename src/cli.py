"""hoi-yo -- CLI for the live multi-agent Hearts of Iron IV system.

Usage examples::

    hoi-yo run --local --speed 4
    hoi-yo run --headless --persona GER=personas/germany_alt
    hoi-yo dashboard --port 9090
    hoi-yo status
    hoi-yo swap SOV personas/soviet_union_alt_trotsky
    hoi-yo whisper GER "Attack Poland now."
    hoi-yo replay --game-log logs/game_20260408.jsonl
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import click

from src.config import HoiYoConfig, load_config

logger = logging.getLogger("hoi-yo")

# ── Defaults ─────────────────────────────────────────────────────────

DEFAULT_CONFIG_PATH = "config.toml"
DEFAULT_DASHBOARD_PORT = 8080

BANNER = r"""
  _           _
 | |__   ___ (_)      _   _  ___
 | '_ \ / _ \| |_____| | | |/ _ \
 | | | | (_) | |_____| |_| | (_) |
 |_| |_|\___/|_|      \__, |\___/
                       |___/
  Live AI Persona Agents for Hearts of Iron IV
"""


def _load_env() -> None:
    """Load ANTHROPIC_API_KEY from .env if it exists."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def _setup_logging(verbose: bool = False) -> None:
    """Configure root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _resolve_config(ctx: click.Context) -> HoiYoConfig:
    """Load and return config from the path stored in the Click context."""
    config_path = Path(ctx.obj["config"])
    if not config_path.exists():
        click.echo(f"Error: config file not found: {config_path}", err=True)
        ctx.exit(1)
    return load_config(config_path)


# ── CLI Group ────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    envvar="HOIYO_CONFIG",
    type=click.Path(),
    help="Path to config.toml.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, config: str, verbose: bool) -> None:
    """hoi-yo -- live AI persona agents for Hearts of Iron IV."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose
    _load_env()
    _setup_logging(verbose)


# ── run ──────────────────────────────────────────────────────────────

@cli.command()
@click.option("--local", "mode", flag_value="local", help="Local mode (game launched manually). [default]")
@click.option("--headless", "mode", flag_value="headless", default="local", help="Headless mode (launch game via Xvfb).")
@click.option("--speed", type=click.IntRange(1, 5), default=None, help="Game speed (1-5).")
@click.option(
    "--persona",
    multiple=True,
    metavar="TAG=PATH",
    help="Override a persona mapping, e.g. --persona SOV=personas/alt_soviet.",
)
@click.option("--popcorn", is_flag=True, help="Enable Popcorn Mode (pause between turns for viewing).")
@click.option("--deep-dive", is_flag=True, help="Enable Deep Dive Mode (extra-long think on every turn).")
@click.pass_context
def run(
    ctx: click.Context,
    mode: str,
    speed: int | None,
    persona: tuple[str, ...],
    popcorn: bool,
    deep_dive: bool,
) -> None:
    """Start the full game loop.

    In --local mode the game must be launched manually.  In --headless mode
    the controller will launch HOI4 inside a virtual framebuffer.
    """
    config = _resolve_config(ctx)

    # Apply CLI overrides
    if speed is not None:
        config.game.initial_speed = speed

    if mode == "headless":
        config.game.use_xvfb = True

    # Persona overrides: --persona GER=personas/germany_alt
    for mapping in persona:
        if "=" not in mapping:
            click.echo(f"Error: invalid persona format '{mapping}' -- expected TAG=PATH", err=True)
            ctx.exit(1)
        tag, _, path = mapping.partition("=")
        tag = tag.strip().upper()
        path = path.strip()
        config.personas.mappings[tag] = path
        logger.info("Persona override: %s -> %s", tag, path)

    # Startup banner
    click.echo(BANNER)
    click.echo(f"  Mode:      {mode}")
    click.echo(f"  Speed:     {config.game.initial_speed}")
    click.echo(f"  Popcorn:   {'ON' if popcorn else 'OFF'}")
    click.echo(f"  Deep Dive: {'ON' if deep_dive else 'OFF'}")
    click.echo()
    click.echo("  Personas:")
    for tag, path in sorted(config.personas.mappings.items()):
        click.echo(f"    {tag:>4} -> {path}")
    click.echo()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        click.echo(
            "Warning: ANTHROPIC_API_KEY not set. Set it in .env or your environment.",
            err=True,
        )

    # Launch game controller if headless
    if mode == "headless":
        from src.game.controller import GameController

        controller = GameController(config.game.hoi4_executable, use_xvfb=True)
        launched = controller.launch()
        if not launched:
            click.echo("Warning: Could not auto-launch HOI4. Continuing -- launch the game manually.")

    click.echo("Starting orchestrator loop...")

    # Stub: the orchestrator module doesn't exist yet.
    # When it does, this will be:
    #   from src.orchestrator import Orchestrator
    #   orchestrator = Orchestrator(config, popcorn=popcorn, deep_dive=deep_dive)
    #   asyncio.run(orchestrator.run())
    try:
        from src.orchestrator import Orchestrator  # type: ignore[import-not-found]

        orchestrator = Orchestrator(config, popcorn=popcorn, deep_dive=deep_dive)
        asyncio.run(orchestrator.run())
    except ImportError:
        click.echo(
            "Orchestrator not yet implemented.  The game controller and save "
            "watcher are ready -- build src/orchestrator.py next.",
        )


# ── dashboard ────────────────────────────────────────────────────────

@cli.command()
@click.option("--port", type=int, default=None, help="Port for the dashboard server.")
@click.pass_context
def dashboard(ctx: click.Context, port: int | None) -> None:
    """Start the web dashboard server only (no game loop)."""
    config = _resolve_config(ctx)
    actual_port = port if port is not None else config.dashboard.port
    click.echo(f"Starting dashboard on port {actual_port}...")

    try:
        from src.dashboard import app  # type: ignore[import-not-found]
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=actual_port)
    except ImportError:
        click.echo(
            "Dashboard not yet implemented.  Build src/dashboard/app.py next."
        )


# ── swap ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("tag")
@click.argument("soul_path", type=click.Path(exists=True))
@click.pass_context
def swap(ctx: click.Context, tag: str, soul_path: str) -> None:
    """Hot-swap a persona mid-game.

    TAG is the country code (e.g. GER, SOV).  SOUL_PATH is the path to
    the new persona directory containing SOUL.md.
    """
    tag = tag.upper()
    click.echo(f"Swapping persona for {tag} to {soul_path}...")

    # This will communicate with the running orchestrator via a signal file
    # or IPC mechanism once the orchestrator is implemented.
    swap_signal = Path("logs") / f"swap_{tag}.signal"
    swap_signal.parent.mkdir(parents=True, exist_ok=True)
    swap_signal.write_text(soul_path)
    click.echo(f"Swap signal written. {tag} will pick up the new persona on the next turn.")


# ── whisper ──────────────────────────────────────────────────────────

@cli.command()
@click.argument("tag")
@click.argument("message")
@click.pass_context
def whisper(ctx: click.Context, tag: str, message: str) -> None:
    """Send a message to an agent as a system-level hint.

    TAG is the country code.  MESSAGE is free-form text that will be
    injected into the agent's next prompt as an operator whisper.
    """
    tag = tag.upper()
    whisper_file = Path("logs") / f"whisper_{tag}.txt"
    whisper_file.parent.mkdir(parents=True, exist_ok=True)
    whisper_file.write_text(message)
    click.echo(f"Whisper queued for {tag}: \"{message}\"")


# ── replay ───────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--game-log",
    type=click.Path(exists=True),
    required=True,
    help="Path to a completed game log (JSONL).",
)
@click.pass_context
def replay(ctx: click.Context, game_log: str) -> None:
    """Replay a completed game from its log file.

    Reads the JSONL game log and streams turn-by-turn decisions to the
    dashboard for review.
    """
    click.echo(f"Replaying game from {game_log}...")
    click.echo("Replay mode not yet implemented.")


# ── status ───────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current game status.

    Reads the latest state files to display turn number, active personas,
    and game speed.
    """
    click.echo("Game Status")
    click.echo("-" * 40)

    # Check for a running game by looking for state files
    state_file = Path("logs") / "current_state.json"
    if state_file.exists():
        import json

        try:
            state = json.loads(state_file.read_text())
            click.echo(f"  Turn:    {state.get('turn', '?')}")
            click.echo(f"  Date:    {state.get('date', '?')}")
            click.echo(f"  Speed:   {state.get('speed', '?')}")
            click.echo(f"  Agents:  {', '.join(state.get('agents', []))}")
        except (json.JSONDecodeError, KeyError):
            click.echo("  Could not parse state file.")
    else:
        click.echo("  No active game found.")
        click.echo("  Start one with: hoi-yo run --local")


# ── deploy ───────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def deploy(ctx: click.Context) -> None:
    """Deploy hoi-yo to AWS (placeholder).

    Will use Terraform configs in terraform/ to provision an EC2 instance
    with Xvfb, install HOI4 via SteamCMD, and start the headless game loop.
    """
    click.echo("Deploy is not yet implemented.")
    click.echo("See terraform/ for infrastructure-as-code templates.")


# ── Entry point ──────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the hoi-yo CLI."""
    cli()


if __name__ == "__main__":
    main()
