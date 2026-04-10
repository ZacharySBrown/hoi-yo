"""Shared types used across all hoi-yo components.

This module defines the contracts between components. All agents/modules
import from here to ensure type compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Country Tags ───────────────────────────────────────────────────

MAJOR_POWERS = ["GER", "SOV", "USA", "ENG", "JAP", "ITA"]


# ─── Parsed Game State ──────────────────────────────────────────────

@dataclass
class CountryState:
    tag: str
    name: str
    ruling_ideology: str
    stability: float
    war_support: float
    surrender_progress: float
    mil_factories: int
    civ_factories: int
    dockyards: int
    manpower_available: int
    division_count: int
    equipment_stockpile: dict[str, int] = field(default_factory=dict)
    at_war: bool = False
    enemies: list[str] = field(default_factory=list)
    faction: str | None = None
    research_slots: int = 3
    researching: list[str] = field(default_factory=list)
    national_focus: str | None = None
    army_summary: str = ""
    navy_summary: str = ""
    air_summary: str = ""

    @property
    def is_at_war(self) -> bool:
        return self.at_war

    @property
    def is_in_crisis(self) -> bool:
        return self.at_war and (
            self.surrender_progress > 0.2
            or len(self.enemies) > 2
        )

    @property
    def recently_invaded(self) -> bool:
        return False  # Set by parser when detecting territory loss

    @property
    def ally_capitulated_this_turn(self) -> bool:
        return False  # Set by parser

    @property
    def new_war_this_turn(self) -> bool:
        return False  # Set by parser

    @property
    def enemies_count(self) -> int:
        return len(self.enemies)

    @property
    def available_focus_choices(self) -> int:
        return 0  # Set by parser

    @property
    def faction_invite_pending(self) -> bool:
        return False  # Set by parser


@dataclass
class WarData:
    name: str
    attackers: list[str]
    defenders: list[str]
    start_date: str
    front_summary: str = ""

    @property
    def attackers_str(self) -> str:
        return ", ".join(self.attackers)

    @property
    def defenders_str(self) -> str:
        return ", ".join(self.defenders)


@dataclass
class ParsedSaveData:
    date: str
    turn_number: int
    world_tension: float
    countries: dict[str, CountryState] = field(default_factory=dict)
    wars: list[WarData] = field(default_factory=list)
    capitulated: list[str] = field(default_factory=list)
    nuclear_powers: list[str] = field(default_factory=list)
    nations_at_war_count: int = 0


# ─── Board State (Prompt Representation) ────────────────────────────

@dataclass
class BoardState:
    date: str
    turn_number: int
    world_tension: float
    summary: str  # The full board state prompt text
    countries: dict[str, CountryState] = field(default_factory=dict)
    wars: list[WarData] = field(default_factory=list)

    def to_prompt(self) -> str:
        return self.summary

    def get_country_detail(self, tag: str) -> CountryState | None:
        return self.countries.get(tag)

    def recent_events_for(self, tag: str) -> str:
        """Get country-specific recent events summary."""
        country = self.countries.get(tag)
        if not country:
            return "No data available."
        events = []
        if country.at_war:
            events.append(f"Currently at war with: {', '.join(country.enemies)}")
            events.append(f"Surrender progress: {country.surrender_progress:.0%}")
        if country.national_focus:
            events.append(f"Current focus: {country.national_focus}")
        return "\n".join(events) if events else "No significant recent events."


# ─── Persona ────────────────────────────────────────────────────────

@dataclass
class Persona:
    tag: str
    name: str
    soul_prompt: str  # Full SOUL.md content
    base_strategies: dict[str, Any] = field(default_factory=dict)


# ─── Agent Decision (Output) ────────────────────────────────────────

class Mood(str, Enum):
    CONFIDENT = "confident"
    ANXIOUS = "anxious"
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    SCHEMING = "scheming"
    PANICKING = "panicking"
    TRIUMPHANT = "triumphant"
    BROODING = "brooding"


@dataclass
class DiplomaticStrategy:
    target: str
    strategy_type: str
    value: int
    reasoning: str = ""


@dataclass
class MilitaryStrategy:
    strategy_type: str
    id: str
    value: float
    execution_type: str | None = None
    reasoning: str = ""


@dataclass
class ProductionStrategy:
    strategy_type: str
    id: str = ""
    value: float = 0
    reasoning: str = ""


@dataclass
class LendLeaseOrder:
    target: str
    equipment_type: str
    amount: int
    reasoning: str = ""


@dataclass
class AgentDecision:
    tag: str
    turn_number: int
    inner_monologue: str
    mood: str
    diplomatic_strategies: list[DiplomaticStrategy] = field(default_factory=list)
    military_strategies: list[MilitaryStrategy] = field(default_factory=list)
    production_strategies: list[ProductionStrategy] = field(default_factory=list)
    research_priorities: dict[str, float] = field(default_factory=dict)
    focus_preferences: dict[str, float] = field(default_factory=dict)
    lend_lease_orders: list[LendLeaseOrder] = field(default_factory=list)
    threat_assessment: dict[str, int] = field(default_factory=dict)
    model_used: str = ""

    @property
    def all_strategies(self) -> list:
        return (
            [vars(s) for s in self.diplomatic_strategies]
            + [vars(s) for s in self.military_strategies]
            + [vars(s) for s in self.production_strategies]
        )

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "turn": self.turn_number,
            "inner_monologue": self.inner_monologue,
            "mood": self.mood,
            "diplomatic": [vars(s) for s in self.diplomatic_strategies],
            "military": [vars(s) for s in self.military_strategies],
            "production": [vars(s) for s in self.production_strategies],
            "research": self.research_priorities,
            "focus": self.focus_preferences,
            "lend_lease": [vars(o) for o in self.lend_lease_orders],
            "threats": self.threat_assessment,
            "model": self.model_used,
        }

    @classmethod
    def from_json(cls, tag: str, turn: int, data: dict, model: str = "") -> "AgentDecision":
        """Create an AgentDecision from parsed JSON response."""
        return cls(
            tag=tag,
            turn_number=turn,
            inner_monologue=data.get("inner_monologue", ""),
            mood=data.get("mood", "confident"),
            diplomatic_strategies=[
                DiplomaticStrategy(**s) for s in data.get("diplomatic_strategies", [])
            ],
            military_strategies=[
                MilitaryStrategy(**s) for s in data.get("military_strategies", [])
            ],
            production_strategies=[
                ProductionStrategy(**s) for s in data.get("production_strategies", [])
            ],
            research_priorities=data.get("research_priorities", {}),
            focus_preferences=data.get("focus_preferences", {}),
            lend_lease_orders=[
                LendLeaseOrder(**o) for o in data.get("lend_lease_orders", [])
            ],
            threat_assessment=data.get("threat_assessment", {}),
            model_used=model,
        )
