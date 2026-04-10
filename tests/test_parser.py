"""Tests for the Clausewitz parser and HOI4 save file parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.parser.clausewitz import parse_clausewitz
from src.parser.save_parser import parse_save


FIXTURES_DIR = Path(__file__).parent / "fixtures"


# =====================================================================
# Clausewitz parser unit tests
# =====================================================================

class TestClausewitzParser:
    """Tests for the generic Clausewitz format parser."""

    def test_simple_key_value(self):
        text = 'name="Germany" tag="GER"'
        result = parse_clausewitz(text)
        assert result["name"] == "Germany"
        assert result["tag"] == "GER"

    def test_integer_value(self):
        result = parse_clausewitz("manpower=8500000")
        assert result["manpower"] == 8500000
        assert isinstance(result["manpower"], int)

    def test_negative_integer(self):
        result = parse_clausewitz("modifier=-5")
        assert result["modifier"] == -5

    def test_float_value(self):
        result = parse_clausewitz("stability=0.65")
        assert result["stability"] == pytest.approx(0.65)
        assert isinstance(result["stability"], float)

    def test_negative_float(self):
        result = parse_clausewitz("modifier=-0.15")
        assert result["modifier"] == pytest.approx(-0.15)

    def test_date_value_not_float(self):
        result = parse_clausewitz('date="1939.9.1"')
        assert result["date"] == "1939.9.1"
        assert isinstance(result["date"], str)

    def test_bare_date_value(self):
        result = parse_clausewitz("start_date=1939.9.1")
        assert result["start_date"] == "1939.9.1"
        assert isinstance(result["start_date"], str)

    def test_boolean_yes(self):
        result = parse_clausewitz("is_active=yes")
        assert result["is_active"] is True

    def test_boolean_no(self):
        result = parse_clausewitz("is_active=no")
        assert result["is_active"] is False

    def test_nested_block(self):
        text = """
        country={
            tag="GER"
            stability=0.65
        }
        """
        result = parse_clausewitz(text)
        assert result["country"]["tag"] == "GER"
        assert result["country"]["stability"] == pytest.approx(0.65)

    def test_deeply_nested(self):
        text = """
        countries={
            GER={
                politics={
                    ruling_party="fascism"
                }
            }
        }
        """
        result = parse_clausewitz(text)
        assert result["countries"]["GER"]["politics"]["ruling_party"] == "fascism"

    def test_flat_list(self):
        text = "values={ 1 2 3 4 5 }"
        result = parse_clausewitz(text)
        assert result["values"] == [1, 2, 3, 4, 5]

    def test_string_list(self):
        text = 'tags={ GER SOV USA }'
        result = parse_clausewitz(text)
        assert result["tags"] == ["GER", "SOV", "USA"]

    def test_comments_stripped(self):
        text = """
        # This is a comment
        name="Test"  # inline comment
        value=42
        """
        result = parse_clausewitz(text)
        assert result["name"] == "Test"
        assert result["value"] == 42

    def test_empty_block(self):
        result = parse_clausewitz("data={}")
        assert result["data"] == {}

    def test_empty_string(self):
        result = parse_clausewitz("")
        assert result == {}

    def test_duplicate_keys_become_list(self):
        text = """
        war={
            name="War 1"
        }
        war={
            name="War 2"
        }
        """
        result = parse_clausewitz(text)
        assert isinstance(result["war"], list)
        assert len(result["war"]) == 2
        assert result["war"][0]["name"] == "War 1"
        assert result["war"][1]["name"] == "War 2"

    def test_mixed_types_in_block(self):
        text = """
        country={
            tag="GER"
            stability=0.65
            manpower=8500000
            at_war=yes
            capital=64
        }
        """
        result = parse_clausewitz(text)
        c = result["country"]
        assert c["tag"] == "GER"
        assert isinstance(c["stability"], float)
        assert isinstance(c["manpower"], int)
        assert c["at_war"] is True
        assert c["capital"] == 64

    def test_bare_identifier_value(self):
        result = parse_clausewitz("ruling_party=fascism")
        assert result["ruling_party"] == "fascism"

    def test_quoted_string_with_spaces(self):
        result = parse_clausewitz('name="German Reich"')
        assert result["name"] == "German Reich"

    def test_multiline_block(self):
        text = """research={
            infantry_weapons2=yes
            medium_armor=yes
        }"""
        result = parse_clausewitz(text)
        assert result["research"]["infantry_weapons2"] is True
        assert result["research"]["medium_armor"] is True

    def test_robustness_to_whitespace(self):
        text = "  \n\n  tag  =  GER  \n  value  =  42  \n\n"
        result = parse_clausewitz(text)
        assert result["tag"] == "GER"
        assert result["value"] == 42


# =====================================================================
# Save parser tests with sample fixture
# =====================================================================

class TestSaveParser:
    """Tests for the save_parser using the sample fixture."""

    @pytest.fixture()
    def parsed(self) -> "ParsedSaveData":
        return parse_save(FIXTURES_DIR / "sample_save.txt")

    def test_date_extracted(self, parsed):
        assert parsed.date == "1939.9.1"

    def test_world_tension(self, parsed):
        assert parsed.world_tension == pytest.approx(65.3)

    def test_turn_number(self, parsed):
        # 1939.9 => (1939-1936)*12 + (9-1) = 36 + 8 = 44
        assert parsed.turn_number == 44

    def test_all_major_powers_present(self, parsed):
        for tag in ["GER", "SOV", "USA", "ENG", "JAP", "ITA"]:
            assert tag in parsed.countries, f"{tag} missing from countries"

    def test_germany_basic_stats(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.tag == "GER"
        assert ger.name == "Germany"
        assert ger.ruling_ideology == "fascism"
        assert ger.stability == pytest.approx(0.65)
        assert ger.war_support == pytest.approx(0.82)
        assert ger.surrender_progress == pytest.approx(0.0)

    def test_germany_factories(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.mil_factories == 75
        assert ger.civ_factories == 48
        assert ger.dockyards == 12

    def test_germany_military(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.manpower_available == 8500000
        assert ger.division_count == 120

    def test_germany_faction(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.faction == "axis"

    def test_germany_research(self, parsed):
        ger = parsed.countries["GER"]
        assert "infantry_weapons2" in ger.researching
        assert "medium_armor" in ger.researching
        assert ger.research_slots == 4

    def test_germany_national_focus(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.national_focus == "danzig_or_war"

    def test_soviet_stats(self, parsed):
        sov = parsed.countries["SOV"]
        assert sov.manpower_available == 12000000
        assert sov.division_count == 180
        assert sov.ruling_ideology == "communism"
        assert sov.faction == "comintern"

    def test_usa_not_at_war(self, parsed):
        usa = parsed.countries["USA"]
        assert usa.at_war is False
        assert usa.enemies == []

    def test_usa_no_faction(self, parsed):
        usa = parsed.countries["USA"]
        assert usa.faction is None

    def test_england_at_war_via_wars(self, parsed):
        eng = parsed.countries["ENG"]
        assert eng.at_war is True
        assert "GER" in eng.enemies

    def test_germany_at_war(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.at_war is True
        assert "POL" in ger.enemies
        assert "ENG" in ger.enemies

    def test_japan_at_war(self, parsed):
        jap = parsed.countries["JAP"]
        assert jap.at_war is True
        assert "CHI" in jap.enemies

    def test_italy_at_war_as_attacker(self, parsed):
        ita = parsed.countries["ITA"]
        assert ita.at_war is True
        assert "POL" in ita.enemies

    def test_wars_parsed(self, parsed):
        assert len(parsed.wars) == 2
        war_names = {w.name for w in parsed.wars}
        assert "German-Polish War" in war_names
        assert "Second Sino-Japanese War" in war_names

    def test_war_participants(self, parsed):
        gp_war = next(w for w in parsed.wars if w.name == "German-Polish War")
        assert "GER" in gp_war.attackers
        assert "ITA" in gp_war.attackers
        assert "POL" in gp_war.defenders
        assert "ENG" in gp_war.defenders
        assert gp_war.start_date == "1939.9.1"

    def test_war_str_properties(self, parsed):
        gp_war = next(w for w in parsed.wars if w.name == "German-Polish War")
        assert "GER" in gp_war.attackers_str
        assert "POL" in gp_war.defenders_str

    def test_capitulated(self, parsed):
        # Poland has surrender_progress=1.0
        assert "POL" in parsed.capitulated

    def test_no_nuclear_powers(self, parsed):
        # Nobody has nukes in 1939
        assert parsed.nuclear_powers == []

    def test_nations_at_war_count(self, parsed):
        # GER, ENG, JAP, ITA are at war among the 6 majors
        assert parsed.nations_at_war_count == 4

    def test_country_crisis_detection(self, parsed):
        ger = parsed.countries["GER"]
        assert ger.is_at_war is True
        # GER has 2 enemies (POL, ENG) and surrender_progress=0.0,
        # so is_in_crisis requires >0.2 surrender or >2 enemies => False
        assert ger.is_in_crisis is False

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_save(Path("/tmp/nonexistent_save_file.hoi4"))


# =====================================================================
# Edge cases
# =====================================================================

class TestEdgeCases:
    """Test parser robustness with unusual inputs."""

    def test_clausewitz_malformed_input(self):
        text = """
        valid=42
        ===broken===
        another=100
        """
        result = parse_clausewitz(text)
        # Should still parse what it can
        assert result.get("valid") == 42 or result.get("another") == 100

    def test_empty_save_file(self, tmp_path):
        save_file = tmp_path / "empty.txt"
        save_file.write_text("")
        result = parse_save(save_file)
        assert result.date == "1936.1.1"
        assert result.world_tension == 0.0
        assert result.countries == {}

    def test_save_with_no_countries(self, tmp_path):
        save_file = tmp_path / "minimal.txt"
        save_file.write_text('date="1940.1.1"\nworld_tension=50.0\n')
        result = parse_save(save_file)
        assert result.date == "1940.1.1"
        assert result.world_tension == pytest.approx(50.0)
        assert len(result.countries) == 0

    def test_country_is_at_war_property(self):
        from src.interfaces import CountryState

        c = CountryState(
            tag="GER", name="Germany", ruling_ideology="fascism",
            stability=0.5, war_support=0.5, surrender_progress=0.0,
            mil_factories=50, civ_factories=30, dockyards=10,
            manpower_available=5000000, division_count=100,
            at_war=True, enemies=["SOV", "ENG", "USA"],
        )
        assert c.is_at_war is True
        assert c.is_in_crisis is True  # > 2 enemies
        assert c.enemies_count == 3
