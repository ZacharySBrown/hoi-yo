"""Clausewitz strategy writer -- converts AgentDecision objects into HOI4 mod files.

Produces valid .txt files that HOI4 can load from common/ai_strategy/ and
common/ai_strategy_plans/, plus a descriptor.mod for the mod root.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import asdict

from jinja2 import Environment, FileSystemLoader

from src.interfaces import AgentDecision

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_env() -> Environment:
    """Create a Jinja2 environment pointed at the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


class StrategyWriter:
    """Renders AgentDecision objects into Clausewitz-compatible .txt files."""

    def __init__(self) -> None:
        self.env = _build_env()

    # ── public API ───────────────────────────────────────────────────

    def write_all(
        self,
        decisions: list[AgentDecision],
        output_dir: Path,
    ) -> list[Path]:
        """Write strategy files for every decision. Returns paths written."""
        written: list[Path] = []
        for decision in decisions:
            written.append(self.write_strategy(decision, output_dir))
            written.append(self.write_strategy_plan(decision, output_dir))
        return written

    def write_strategy(self, decision: AgentDecision, output_dir: Path) -> Path:
        """Write common/ai_strategy/{TAG}_hoi_yo.txt."""
        template = self.env.get_template("ai_strategy.txt.j2")
        context = _strategy_context(decision)
        content = template.render(**context)
        dest = output_dir / "common" / "ai_strategy" / f"{decision.tag}_hoi_yo.txt"
        _write_utf8(dest, content)
        return dest

    def write_strategy_plan(self, decision: AgentDecision, output_dir: Path) -> Path:
        """Write common/ai_strategy_plans/{TAG}_hoi_yo_plan.txt."""
        template = self.env.get_template("ai_strategy_plan.txt.j2")
        context = {
            "tag": decision.tag,
            "turn_number": decision.turn_number,
            "research": decision.research_priorities,
            "focus_prefs": decision.focus_preferences,
        }
        content = template.render(**context)
        dest = output_dir / "common" / "ai_strategy_plans" / f"{decision.tag}_hoi_yo_plan.txt"
        _write_utf8(dest, content)
        return dest

    def write_descriptor(self, output_dir: Path, version: str = "0.1.0") -> Path:
        """Write descriptor.mod at the mod root."""
        template = self.env.get_template("descriptor.mod.j2")
        content = template.render(version=version)
        dest = output_dir / "descriptor.mod"
        _write_utf8(dest, content)
        return dest


# ── helpers ──────────────────────────────────────────────────────────

def _strategy_context(decision: AgentDecision) -> dict:
    """Build the template context dict from an AgentDecision."""
    return {
        "tag": decision.tag,
        "turn_number": decision.turn_number,
        "mood": decision.mood,
        "diplomatic_strategies": [asdict(s) for s in decision.diplomatic_strategies],
        "military_strategies": [asdict(s) for s in decision.military_strategies],
        "production_strategies": [asdict(s) for s in decision.production_strategies],
    }


def _write_utf8(path: Path, content: str) -> None:
    """Write content as UTF-8 *without* BOM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
