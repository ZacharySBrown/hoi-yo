"""Tests for the Clausewitz strategy writer and validators."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.interfaces import (
    AgentDecision,
    DiplomaticStrategy,
    MilitaryStrategy,
    ProductionStrategy,
)
from src.writer.strategy_writer import StrategyWriter
from src.validators.clausewitz import validate_brackets, validate_encoding, validate_file


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def sample_decision() -> AgentDecision:
    """A realistic AgentDecision for Germany."""
    return AgentDecision(
        tag="GER",
        turn_number=3,
        inner_monologue="Poland must fall before winter.",
        mood="aggressive",
        diplomatic_strategies=[
            DiplomaticStrategy(
                target="POL",
                strategy_type="conquer",
                value=200,
                reasoning="Danzig or war",
            ),
            DiplomaticStrategy(
                target="SOV",
                strategy_type="befriend",
                value=100,
                reasoning="Molotov-Ribbentrop",
            ),
        ],
        military_strategies=[
            MilitaryStrategy(
                strategy_type="front_control",
                id="POL",
                value=100,
                execution_type="careful",
                reasoning="Encircle and destroy",
            ),
            MilitaryStrategy(
                strategy_type="front_armor_score",
                id="POL",
                value=200,
                reasoning="Panzer push",
            ),
        ],
        production_strategies=[
            ProductionStrategy(
                strategy_type="equipment_production_factor",
                id="infantry_equipment",
                value=50,
                reasoning="Arm the troops",
            ),
            ProductionStrategy(
                strategy_type="build_army",
                value=80,
                reasoning="Expand divisions",
            ),
        ],
        research_priorities={
            "land_doctrine": 2.0,
            "infantry_weapons": 1.5,
            "armor": 1.8,
        },
        focus_preferences={
            "GER_rhineland": 100,
            "GER_anschluss": 80,
            "GER_demand_sudetenland": 60,
        },
    )


@pytest.fixture
def writer() -> StrategyWriter:
    return StrategyWriter()


# ── strategy file tests ──────────────────────────────────────────────


def test_write_strategy_creates_file(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    assert path.exists()
    assert path.name == "GER_hoi_yo.txt"
    assert path.parent.name == "ai_strategy"


def test_write_strategy_valid_clausewitz(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    # Brackets must match
    errors = validate_brackets(content)
    assert errors == [], f"Bracket errors: {errors}"


def test_write_strategy_contains_diplomatic_blocks(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "GER_hoi_yo_diplo_1" in content
    assert "GER_hoi_yo_diplo_2" in content
    assert 'type = conquer' in content
    assert 'id = "POL"' in content
    assert "value = 200" in content


def test_write_strategy_contains_military_blocks(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "GER_hoi_yo_mil_1" in content
    assert "GER_hoi_yo_mil_2" in content
    assert "type = front_control" in content
    assert "execution_type = careful" in content


def test_write_strategy_contains_production_blocks(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "GER_hoi_yo_prod_1" in content
    assert "GER_hoi_yo_prod_2" in content
    assert "type = equipment_production_factor" in content
    assert 'id = "infantry_equipment"' in content


def test_write_strategy_no_execution_type_when_none(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    """Military strategy without execution_type should not emit the key."""
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    # mil_2 has no execution_type -- check it doesn't appear in that block
    # Split by blocks and inspect mil_2
    blocks = content.split("GER_hoi_yo_mil_2")
    assert len(blocks) == 2
    mil2_block = blocks[1].split("GER_hoi_yo_")[0]  # up to next block or EOF
    assert "execution_type" not in mil2_block


def test_write_strategy_no_id_for_production_without_id(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    """Production strategy with empty id should not emit id line."""
    path = writer.write_strategy(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    blocks = content.split("GER_hoi_yo_prod_2")
    assert len(blocks) == 2
    prod2_block = blocks[1].split("GER_hoi_yo_")[0]
    assert 'id = ""' not in prod2_block


# ── strategy plan tests ──────────────────────────────────────────────


def test_write_strategy_plan_creates_file(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy_plan(sample_decision, tmp_path)
    assert path.exists()
    assert path.name == "GER_hoi_yo_plan.txt"
    assert path.parent.name == "ai_strategy_plans"


def test_write_strategy_plan_valid_clausewitz(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy_plan(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    errors = validate_brackets(content)
    assert errors == [], f"Bracket errors: {errors}"


def test_write_strategy_plan_contains_research(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy_plan(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "land_doctrine = 2.0" in content
    assert "infantry_weapons = 1.5" in content
    assert "armor = 1.8" in content


def test_write_strategy_plan_contains_focus_factors(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy_plan(sample_decision, tmp_path)
    content = path.read_text(encoding="utf-8")

    assert "GER_rhineland = 100" in content
    assert "GER_anschluss = 80" in content
    assert "GER_demand_sudetenland = 60" in content


# ── descriptor tests ─────────────────────────────────────────────────


def test_write_descriptor_creates_file(writer: StrategyWriter, tmp_path: Path):
    path = writer.write_descriptor(tmp_path, version="1.2.3")
    assert path.exists()
    assert path.name == "descriptor.mod"


def test_write_descriptor_content(writer: StrategyWriter, tmp_path: Path):
    path = writer.write_descriptor(tmp_path, version="1.2.3")
    content = path.read_text(encoding="utf-8")

    assert 'name="HOI-YO AI Personas"' in content
    assert 'tags={"AI" "Gameplay"}' in content
    assert 'supported_version="1.17.*"' in content
    assert 'version="1.2.3"' in content


# ── write_all test ───────────────────────────────────────────────────


def test_write_all(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    paths = writer.write_all([sample_decision], tmp_path)
    assert len(paths) == 2
    assert all(p.exists() for p in paths)


# ── encoding validation ─────────────────────────────────────────────


def test_encoding_no_bom(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    path = writer.write_strategy(sample_decision, tmp_path)
    errors = validate_encoding(path, expect_bom=False)
    assert errors == []


def test_encoding_rejects_bom(tmp_path: Path):
    bogus = tmp_path / "bom.txt"
    bogus.write_bytes(b"\xef\xbb\xbf" + b"hello")
    errors = validate_encoding(bogus, expect_bom=False)
    assert len(errors) == 1
    assert "BOM" in errors[0]


def test_encoding_expects_bom(tmp_path: Path):
    no_bom = tmp_path / "nobom.txt"
    no_bom.write_bytes(b"hello")
    errors = validate_encoding(no_bom, expect_bom=True)
    assert len(errors) == 1
    assert "BOM" in errors[0]


# ── bracket validation ───────────────────────────────────────────────


def test_validate_brackets_balanced():
    assert validate_brackets("a = { b = { c = 1 } }") == []


def test_validate_brackets_unclosed():
    errors = validate_brackets("a = { b = 1")
    assert len(errors) == 1
    assert "Unclosed" in errors[0]


def test_validate_brackets_extra_close():
    errors = validate_brackets("a = 1 }")
    assert len(errors) == 1
    assert "unexpected" in errors[0]


def test_validate_brackets_ignores_comments():
    assert validate_brackets("# a = {") == []


# ── full file validation ─────────────────────────────────────────────


def test_validate_file_passes_on_generated_output(writer: StrategyWriter, sample_decision: AgentDecision, tmp_path: Path):
    strategy_path = writer.write_strategy(sample_decision, tmp_path)
    plan_path = writer.write_strategy_plan(sample_decision, tmp_path)
    descriptor_path = writer.write_descriptor(tmp_path)

    for path in [strategy_path, plan_path, descriptor_path]:
        errors = validate_file(path)
        assert errors == [], f"Validation errors in {path.name}: {errors}"


def test_validate_file_missing_file(tmp_path: Path):
    errors = validate_file(tmp_path / "nope.txt")
    assert len(errors) == 1
    assert "does not exist" in errors[0]
