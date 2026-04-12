"""Main orchestrator loop for hoi-yo.

Watches for new HOI4 save files, runs persona agents, writes strategy files,
and pushes updates to the dashboard.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from anthropic import AsyncAnthropic

from src.agents.runner import run_agents, cost_tracker
from src.board_state.builder import BoardStateBuilder
from src.config import HoiYoConfig
from src.dashboard.server import DashboardServer
from src.game.controller import GameController
from src.game.save_watcher import SaveWatcher
from src.interfaces import Persona
from src.parser.fast_parser import parse_save_fast as parse_save
from src.writer.strategy_writer import StrategyWriter

logger = logging.getLogger("hoi-yo")


class HoiYoOrchestrator:
    """Main orchestration loop: watch -> parse -> agents -> write -> reload."""

    def __init__(
        self,
        config: HoiYoConfig,
        personas: list[Persona],
        dashboard: DashboardServer,
        headless: bool = False,
        popcorn: bool = False,
        deep_dive: bool = False,
        player_tag: str | None = None,
    ):
        self.config = config
        self.personas = personas
        self.dashboard = dashboard
        self.headless = headless
        self.popcorn = popcorn
        self.deep_dive = deep_dive
        self.player_tag = player_tag

        self.client = AsyncAnthropic()
        self.board_builder = BoardStateBuilder()
        self.writer = StrategyWriter()
        self.game: GameController | None = None
        self.turn_number = 0
        self.log_dir = Path("logs")
        self._whisper_queue: dict[str, str] = {}  # tag -> message

    async def run(self):
        """Start the full agent loop."""
        self.log_dir.mkdir(exist_ok=True)

        # Launch game if headless
        if self.headless:
            self.game = GameController(self.config.game)
            if not self.game.launch():
                logger.error("Failed to launch HOI4. Is it installed?")
                return
            await asyncio.sleep(30)  # Wait for game to load
            self.game.enter_observer_mode()
            self.game.set_speed(self.config.game.initial_speed)

        # Set up save watcher
        watcher = SaveWatcher(self.config.game.save_dir)
        logger.info("Watching for saves in %s", self.config.game.save_dir)
        logger.info("Loaded %d personas: %s", len(self.personas),
                     ", ".join(f"{p.tag}={p.name}" for p in self.personas))

        # Write initial mod descriptor
        self.writer.write_descriptor(self.config.game.mod_dir, version="0.1.0")

        try:
            async for save_path in watcher.watch():
                await self._process_turn(save_path)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self.game:
                self.game.stop()

    def _poll_signal_files(self):
        """Check for whisper and swap signal files written by the CLI."""
        # Whispers: logs/whisper_TAG.txt
        for signal in self.log_dir.glob("whisper_*.txt"):
            tag = signal.stem.removeprefix("whisper_").upper()
            message = signal.read_text(encoding="utf-8").strip()
            if message:
                self.add_whisper(tag, message)
            signal.unlink()

        # Swaps: logs/swap_TAG.signal (contents = new persona path)
        for signal in self.log_dir.glob("swap_*.signal"):
            tag = signal.stem.removeprefix("swap_").upper()
            persona_path = Path(signal.read_text(encoding="utf-8").strip())
            signal.unlink()
            if not persona_path.is_absolute():
                persona_path = Path.cwd() / persona_path
            if not (persona_path / "SOUL.md").exists():
                logger.warning("Swap signal for %s: no SOUL.md at %s", tag, persona_path)
                continue
            from src.personas.loader import load_persona
            new_persona = load_persona(persona_path)
            self.swap_persona(tag, new_persona)

    async def _process_turn(self, save_path: Path):
        """Process a single game turn."""
        self.turn_number += 1
        logger.info("=== Turn %d | Processing %s ===", self.turn_number, save_path.name)

        # Check for whisper/swap signals from the CLI
        self._poll_signal_files()

        # 1. Parse the save file
        try:
            raw_state = parse_save(save_path)
            raw_state.turn_number = self.turn_number
        except Exception:
            logger.exception("Failed to parse save file: %s", save_path)
            return

        # 2. Build shared board state
        board_state = self.board_builder.build(raw_state)
        logger.info("Date: %s | World Tension: %.0f%% | Wars: %d",
                     board_state.date, board_state.world_tension, len(board_state.wars))

        # 3. Override api config for deep dive mode
        api_config = self.config.api
        if self.deep_dive:
            from src.config import ApiConfig
            api_config = ApiConfig(
                default_model="claude-opus-4-6",
                war_model="claude-opus-4-6",
                crisis_model="claude-opus-4-6",
                max_output_tokens=4000,
            )

        # 4. Inject whispers into personas temporarily
        augmented_personas = self._apply_whispers()

        # 4b. Filter out the player's country (play-alongside mode)
        if self.player_tag:
            augmented_personas = [p for p in augmented_personas if p.tag != self.player_tag]

        # 5. Run all agents in parallel
        try:
            decisions = await run_agents(
                personas=augmented_personas,
                board_state=board_state,
                turn=self.turn_number,
                client=self.client,
                api_config=api_config,
            )
        except Exception:
            logger.exception("Agent runner failed on turn %d", self.turn_number)
            return

        # 6. Write new strategy files (skip player's country)
        write_decisions = decisions
        if self.player_tag:
            write_decisions = [d for d in decisions if d.tag != self.player_tag]
        try:
            self.writer.write_all(write_decisions, self.config.game.mod_dir)
            logger.info("Wrote strategy files for %d agents", len(write_decisions))
        except Exception:
            logger.exception("Failed to write strategy files")
            return

        # 7. Tell game to reload
        if self.game:
            self.game.reload_files()

        # 8. Log decisions
        self._log_decisions(decisions, raw_state.date)

        # 9. Push to dashboard
        turn_data = {
            "turn": self.turn_number,
            "date": raw_state.date,
            "world_tension": raw_state.world_tension,
            "player_tag": self.player_tag,
            "decisions": {d.tag: d.to_dict() for d in decisions},
            "countries": {
                tag: {
                    "name": cs.name,
                    "mil_factories": cs.mil_factories,
                    "civ_factories": cs.civ_factories,
                    "dockyards": cs.dockyards,
                    "division_count": cs.division_count,
                    "at_war": cs.at_war,
                    "enemies": cs.enemies,
                    "surrender_progress": cs.surrender_progress,
                    "stability": cs.stability,
                    "war_support": cs.war_support,
                    "faction": cs.faction,
                }
                for tag, cs in raw_state.countries.items()
            },
            "wars": [
                {"name": w.name, "attackers": w.attackers, "defenders": w.defenders}
                for w in raw_state.wars
            ],
            "cost": cost_tracker.to_dict(),
        }
        await self.dashboard.broadcast(turn_data)

        # 10. Popcorn mode: pause for reading
        if self.popcorn:
            pause = self.config.dashboard.popcorn_mode_pause
            logger.info("Popcorn mode: pausing %ds for monologue reading", pause)
            if self.game:
                self.game.set_speed(0)
            await asyncio.sleep(pause)
            if self.game:
                self.game.set_speed(self.config.game.initial_speed)

        # Log monologue snippets
        for d in decisions:
            snippet = d.inner_monologue[:120].replace("\n", " ")
            logger.info("[%s/%s] %s: \"%s...\"", d.tag, d.mood, d.model_used, snippet)

    def _apply_whispers(self) -> list[Persona]:
        """Inject pending whisper messages into persona prompts."""
        if not self._whisper_queue:
            return self.personas

        augmented = []
        for p in self.personas:
            if p.tag in self._whisper_queue:
                msg = self._whisper_queue.pop(p.tag)
                augmented_soul = (
                    p.soul_prompt
                    + f"\n\n### URGENT MESSAGE FROM YOUR ADVISOR\n{msg}\n"
                    "(Consider this message in your next strategic decision.)\n"
                )
                augmented.append(Persona(
                    tag=p.tag,
                    name=p.name,
                    soul_prompt=augmented_soul,
                    base_strategies=p.base_strategies,
                ))
            else:
                augmented.append(p)
        return augmented

    def add_whisper(self, tag: str, message: str):
        """Queue a whisper message for the next turn."""
        self._whisper_queue[tag] = message
        logger.info("Queued whisper for %s: %s", tag, message[:80])

    def swap_persona(self, tag: str, new_persona: Persona):
        """Hot-swap a persona mid-game."""
        for i, p in enumerate(self.personas):
            if p.tag == tag:
                self.personas[i] = new_persona
                logger.info("Swapped %s persona: %s -> %s", tag, p.name, new_persona.name)
                return
        logger.warning("No persona found for tag %s", tag)

    def _log_decisions(self, decisions: list, date: str):
        """Save decision logs as JSON for replay."""
        game_dir = self.log_dir / f"game_{datetime.now().strftime('%Y-%m-%d')}"
        game_dir.mkdir(exist_ok=True)

        for d in decisions:
            log_path = game_dir / f"turn_{self.turn_number:03d}_{d.tag}.json"
            log_path.write_text(
                json.dumps(d.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Also write current state for `hoi-yo status`
        status_path = self.log_dir / "current_state.json"
        status_path.write_text(
            json.dumps({
                "turn": self.turn_number,
                "date": date,
                "personas": {p.tag: p.name for p in self.personas},
                "last_updated": datetime.now().isoformat(),
            }, indent=2),
            encoding="utf-8",
        )
