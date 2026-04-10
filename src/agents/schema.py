"""StrategyUpdate JSON schema for Claude structured output.

This schema defines the tool input that Claude must conform to when
producing strategic decisions. It is used with the tool_use pattern
(defining a ``submit_strategy`` tool and forcing its use) to guarantee
well-formed JSON output from every agent call.
"""

from __future__ import annotations

# ── Enum values matching real HOI4 Clausewitz strategy types ─────────

DIPLOMATIC_STRATEGY_TYPES = [
    "conquer",
    "alliance",
    "antagonize",
    "befriend",
    "contain",
    "support",
    "protect",
    "declare_war",
    "prepare_for_war",
]

MILITARY_STRATEGY_TYPES = [
    "role_ratio",
    "build_army",
    "garrison",
    "front_control",
    "area_priority",
    "invade",
    "build_ship",
    "build_airplane",
]

PRODUCTION_STRATEGY_TYPES = [
    "equipment_production_factor",
    "added_military_to_civilian_factory_ratio",
    "dockyard_to_military_factory_ratio",
    "wanted_divisions",
]

EXECUTION_TYPES = ["aggressive", "balanced", "careful", "none"]

MOOD_TYPES = [
    "confident",
    "anxious",
    "aggressive",
    "defensive",
    "scheming",
    "panicking",
    "triumphant",
    "brooding",
]


# ── The schema dict used by the submit_strategy tool ─────────────────

STRATEGY_UPDATE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "inner_monologue": {
            "type": "string",
            "description": (
                "In-character reasoning about the current situation. "
                "Written in the voice of the persona. Displayed on the dashboard."
            ),
        },
        "mood": {
            "type": "string",
            "enum": MOOD_TYPES,
            "description": "Current emotional state affecting decision-making.",
        },
        "diplomatic_strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Country tag (GER, SOV, USA, ENG, JAP, ITA, etc.)",
                    },
                    "strategy_type": {
                        "type": "string",
                        "enum": DIPLOMATIC_STRATEGY_TYPES,
                    },
                    "value": {
                        "type": "integer",
                        "description": "Strategy weight from -500 to +500.",
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["target", "strategy_type", "value"],
            },
        },
        "military_strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "strategy_type": {
                        "type": "string",
                        "enum": MILITARY_STRATEGY_TYPES,
                    },
                    "id": {"type": "string"},
                    "value": {"type": "number"},
                    "execution_type": {
                        "type": "string",
                        "enum": EXECUTION_TYPES,
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["strategy_type", "id", "value"],
            },
        },
        "production_strategies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "strategy_type": {
                        "type": "string",
                        "enum": PRODUCTION_STRATEGY_TYPES,
                    },
                    "id": {"type": "string"},
                    "value": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["strategy_type", "value"],
            },
        },
        "research_priorities": {
            "type": "object",
            "description": "Tech category -> multiplier (0.1 to 5.0). 1.0 = normal.",
            "additionalProperties": {"type": "number"},
        },
        "focus_preferences": {
            "type": "object",
            "description": "Focus ID -> weight multiplier. 0 = skip, 5 = strongly prefer.",
            "additionalProperties": {"type": "number"},
        },
        "lend_lease_orders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "equipment_type": {"type": "string"},
                    "amount": {"type": "integer"},
                    "reasoning": {"type": "string"},
                },
                "required": ["target", "equipment_type", "amount"],
            },
        },
        "threat_assessment": {
            "type": "object",
            "description": "Country tag -> threat level (0-100).",
            "additionalProperties": {"type": "integer"},
        },
    },
    "required": [
        "inner_monologue",
        "mood",
        "diplomatic_strategies",
        "military_strategies",
        "production_strategies",
    ],
}


# ── Tool definition for the tool_use pattern ─────────────────────────

SUBMIT_STRATEGY_TOOL: dict = {
    "name": "submit_strategy",
    "description": (
        "Submit your strategic decisions for this turn. "
        "You MUST call this tool exactly once with your complete strategy update."
    ),
    "input_schema": STRATEGY_UPDATE_SCHEMA,
}
