#!/usr/bin/env python3
"""Runtime aircraft matcher and lookup tests (aircraft corpus, wave 4 task 14).

The matcher and the lookup are generated from the validated aircraft
catalogue by tools/validation/gen_aircraft_data.py. Every catalogue entry
with a complete identity emits a row. A value that is not held is a
labelled absent zero, not a reason to refuse the record. These tests hold
the nine-column row contract, the four-value row order, the graded
resolution, the four named derivations, the five-layer ladder, the
fail-closed result, the generated marker and the caller wiring.

The complete records live only in this test file. They hold sentinel values,
name no real aircraft and are never written to the corpus.

Run: python3 -m unittest tools.tests.test_runtime_aircraft -v
"""

from __future__ import annotations

import math
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_aircraft_data as gen  # noqa: E402

MATCH_PATH = REPO / "addons" / "flight" / "functions" / "fnc_getAircraftMatch.sqf"
DATA_PATH = REPO / "addons" / "flight" / "functions" / "fnc_getAircraftData.sqf"
PREP_PATH = REPO / "addons" / "flight" / "XEH_PREP.hpp"
CALLER_PATH = (
    REPO / "addons" / "weatherfx" / "functions" / "weather" / "fnc_applyExhaustShimmer.sqf"
)
MATCH = MATCH_PATH.read_text(encoding="utf-8")
DATA = DATA_PATH.read_text(encoding="utf-8")
CALLER = CALLER_PATH.read_text(encoding="utf-8")

# The nine columns the matcher row carries.
COL_CATALOGUE = 0
COL_VARIANT = 1
COL_TYPE = 2
COL_CLASS_TOKEN = 3
COL_CLASSES = 4
COL_ALIASES = 5
COL_KEYWORDS = 6
COL_SOURCE = 7
COL_VALUES = 8
ROW_COLUMNS = 9
VALUE_COLUMNS = 4

# Distinct sentinels so the four-value order is provable. No real value.
SENTINEL = {
    "operating_weight_kg": 11,
    "rated_power_w": 22,
    "drag_area_m2": 33,
    "rotor_disc_area_m2": 44,
}
UNITS = {
    "operating_weight_kg": "kg",
    "rated_power_w": "W",
    "drag_area_m2": "m^2",
    "rotor_disc_area_m2": "m^2",
    "empty_weight_kg": "kg",
    "max_takeoff_weight_kg": "kg",
    "thrust_kn": "kN",
    "reference_speed_ms": "m/s",
    "net_power_kw": "kW",
    "published_power_hp": "hp",
    "rotor_diameter_m": "m",
    "drag_coefficient": "ratio",
    "wing_area_m2": "m^2",
}

# A robust subset of the first-slice catalogue ids. The corpus may grow, so
# the tests assert presence, never an exact count.
FIRST_SLICE = (
    "a10a_thunderbolt_ii",
    "su25_frogfoot",
    "l159_alca",
    "cessna_172_skyhawk",
    "jas39c_gripen",
    "md500",
    "md530_defender",
    "uh60a_black_hawk",
    "ch47_chinook",
)


def value(field: str, raw: object, source: str = "fixture_source") -> dict[str, object]:
    """A complete value object. The source is a test fixture, not a document."""
    return {
        "value": raw,
        "unit": UNITS[field],
        "source": source,
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": "documented",
    }


def ready_record(
    vehicle_type: str = "fixed_wing",
    catalogue_id: str = "fixture_aircraft",
    variant_id: str = "fixture_variant",
    class_token: str = "Plane",
    aliases: tuple[str, ...] = ("fixture", "fx"),
    keywords: tuple[str, ...] = ("probe",),
    values: dict[str, object] | None = None,
) -> dict[str, object]:
    """A runtime-ready catalogue entry. Fixture only, one sentinel per field."""
    return {
        "catalogue_id": catalogue_id,
        "variant_id": variant_id,
        "vehicle_type": vehicle_type,
        "class_token": class_token,
        "aliases": list(aliases),
        "keywords": list(keywords),
        "runtime_ready": True,
        "values": {} if values is None else values,
    }


def full_values() -> dict[str, object]:
    """One distinct sentinel per value column, in the projection order."""
    return {field: value(field, SENTINEL[field]) for field in gen.VALUE_FIELDS}


def value_row(row: list[object]) -> list[object]:
    """Return the value_row column, narrowed for the type checker."""
    values = row[COL_VALUES]
    assert isinstance(values, list)
    return values


def row_fields(record: dict[str, object]) -> dict[str, object]:
    """Return the resolved fields of a record, keyed by name."""
    fields = gen.resolve_row(record)
    assert fields is not None
    return {field.name: field for field in fields}


def table_body(text: str = MATCH) -> str:
    match = re.search(r"private _table = \[(.*?)\n\];", text, re.S)
    if match is None:
        raise AssertionError("the generated table is missing")
    return match.group(1)


class TestGeneratedMatchFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", MATCH)
        self.assertIn("gen_aircraft_data.py", MATCH)
        self.assertIn("aee_flight_fnc_getAircraftMatch", MATCH)

    def test_the_header_states_the_nine_column_row(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "catalogue_id",
            "variant_id",
            "vehicle_type",
            "class_token",
            "mapped_classes",
            "aliases",
            "keywords",
            "source_record_id",
            "value_row",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_header_states_the_result_contract(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "confidence",
            "matched_by",
            "exact_class",
            "alias",
            "keyword",
            "inheritance",
            "closest",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_header_states_the_four_value_order(self):
        header = MATCH.split("*/", 1)[0]
        self.assertIn(
            "value_row  [operating_weight_kg, rated_power_w, drag_area_m2,", header
        )
        self.assertIn("rotor_disc_area_m2]", header)

    def test_the_generated_table_holds_at_least_the_first_slice(self):
        body = table_body()
        rows = re.findall(r"^\s{4}\[", body, re.M)
        self.assertGreaterEqual(len(rows), 5)
        for sentinel in FIRST_SLICE:
            self.assertIn(f'"{sentinel}"', body, f"the table drops {sentinel}")

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", MATCH)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, MATCH, f"the matcher reads {command}")

    def test_uses_class_identity_only(self):
        self.assertIn("isKindOf", MATCH)
        self.assertIn("displayName", MATCH)
        self.assertIn("getText (configFile", MATCH)


class TestMatcherLayers(unittest.TestCase):
    """The five layers, ordered, each with a strict tie rule."""

    def test_the_exact_class_layer_runs_first_with_confidence_one(self):
        self.assertIn('"exact_class"', MATCH)
        self.assertIn(', 1, "exact_class"', MATCH)
        self.assertIn('(_classes splitString "|") find _key', MATCH)

    def test_the_alias_layer_runs_second_with_confidence_two(self):
        self.assertIn(', 2, "alias"', MATCH)
        self.assertIn("_x in _tokens", MATCH)

    def test_the_keyword_layer_runs_third_with_confidence_three(self):
        self.assertIn(', 3, "keyword"', MATCH)
        self.assertIn("_query find _x", MATCH)

    def test_the_inheritance_layer_runs_fourth_with_confidence_four(self):
        self.assertIn(', 4, "inheritance"', MATCH)
        self.assertIn("_className isKindOf _token", MATCH)

    def test_the_closest_layer_runs_fifth_with_confidence_five(self):
        self.assertIn(', 5, "closest"', MATCH)
        self.assertIn("_bestScore > _runnerUp", MATCH)
        self.assertIn(str(gen.SCAN_MIN), MATCH)

    def test_a_tie_at_a_layer_returns_empty(self):
        # Every layer that finds more than one candidate returns [].
        self.assertEqual(
            MATCH.count("if ((count _candidates) > 1) exitWith { [] };"), 4
        )
        self.assertIn("_tie = true", MATCH)

    def test_no_match_returns_empty(self):
        self.assertIn('if (_className == "") exitWith { [] };', MATCH)
        self.assertTrue(MATCH.rstrip().endswith("[]"))

    def test_the_result_is_the_documented_seven_element_array(self):
        self.assertIn(
            "[_row select 0, _row select 1, _row select 2, _confidence, _layer,",
            MATCH,
        )
        self.assertIn("_row select 7, _row select 8]", MATCH)


class TestGeneratedDataFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", DATA)
        self.assertIn("gen_aircraft_data.py", DATA)
        self.assertIn("aee_flight_fnc_getAircraftData", DATA)

    def test_the_lookup_consumes_the_matcher(self):
        self.assertIn("FUNC(getAircraftMatch)", DATA)
        self.assertIn("_match select 6", DATA)

    def test_the_lookup_holds_no_table(self):
        self.assertNotIn("private _table", DATA)

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", DATA)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, DATA, f"the lookup reads {command}")

    def test_a_variant_selector_is_supported(self):
        self.assertIn("_variantId", DATA)
        self.assertIn("_variantKey", DATA)


class TestWiring(unittest.TestCase):
    def test_both_functions_are_registered(self):
        prep = PREP_PATH.read_text(encoding="utf-8")
        self.assertIn("PREP(getAircraftMatch);", prep)
        self.assertIn("PREP(getAircraftData);", prep)

    def test_get_aircraft_match_is_registered_once(self):
        prep = PREP_PATH.read_text(encoding="utf-8")
        hits = [line for line in prep.splitlines() if "getAircraftMatch" in line]
        self.assertEqual(len(hits), 1, hits)


class TestGeneratorRows(unittest.TestCase):
    def test_a_ready_record_makes_a_nine_column_row(self):
        row = gen.build_row(ready_record(), ("FIXTURE_CLASS",))
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(len(row), ROW_COLUMNS)
        self.assertEqual(len(value_row(row)), VALUE_COLUMNS)

    def test_the_value_row_order_is_fixed(self):
        # Four distinct sentinels prove the fixed order:
        # [operating_weight_kg, rated_power_w, drag_area_m2, rotor_disc_area_m2].
        row = gen.build_row(ready_record(values=full_values()))
        assert row is not None
        self.assertEqual(value_row(row), [11, 22, 33, 44])

    def test_the_fixed_wing_row_leaves_the_rotor_disc_absent(self):
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 11),
                "rated_power_w": value("rated_power_w", 22),
            }
        )
        row = gen.build_row(record)
        assert row is not None
        self.assertEqual(value_row(row), [11, 22, 0, 0])

    def test_the_rotary_wing_row_carries_the_rotor_disc(self):
        record = ready_record(
            vehicle_type="rotary_wing",
            class_token="Helicopter",
            values={
                "operating_weight_kg": value("operating_weight_kg", 11),
                "rated_power_w": value("rated_power_w", 22),
                "rotor_disc_area_m2": value("rotor_disc_area_m2", 44),
            },
        )
        row = gen.build_row(record)
        assert row is not None
        self.assertEqual(value_row(row), [11, 22, 0, 44])

    def test_the_identity_columns_follow_the_contract(self):
        row = gen.build_row(ready_record(), ())
        assert row is not None
        self.assertEqual(row[COL_CATALOGUE], "fixture_aircraft")
        self.assertEqual(row[COL_VARIANT], "fixture_variant")
        self.assertEqual(row[COL_TYPE], "fixed_wing")
        self.assertEqual(row[COL_CLASS_TOKEN], "Plane")

    def test_the_mapped_class_blob_is_normalised(self):
        row = gen.build_row(ready_record(), ("B_Plane_CAS_01_F", "Plane"))
        assert row is not None
        self.assertEqual(row[COL_CLASSES], "bplanecas01f|plane")

    def test_the_alias_and_keyword_blobs_are_normalised(self):
        record = ready_record(
            aliases=("A-10", "a10", "Wipeout"), keywords=("CAS", "Close Air Support")
        )
        row = gen.build_row(record, ())
        assert row is not None
        self.assertEqual(row[COL_ALIASES], "a10|wipeout")
        self.assertEqual(row[COL_KEYWORDS], "cas|closeairsupport")

    def test_the_source_record_id_is_the_held_source(self):
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 11, "src_fixture")
            }
        )
        row = gen.build_row(record, ())
        assert row is not None
        self.assertEqual(row[COL_SOURCE], "src_fixture")

    def test_a_missing_value_resolves_to_a_labelled_zero(self):
        row = gen.build_row(ready_record())
        assert row is not None
        self.assertEqual(value_row(row), [0, 0, 0, 0])

    def test_an_identity_incomplete_record_makes_no_row(self):
        record = ready_record(catalogue_id="")
        self.assertIsNone(gen.build_row(record))

    def test_rows_are_stable_and_sorted(self):
        first = ready_record(catalogue_id="b_aircraft")
        second = ready_record(catalogue_id="a_aircraft")
        rows = gen.build_rows([first, second])
        self.assertEqual(
            [row[COL_CATALOGUE] for row in rows],
            ["a_aircraft", "b_aircraft"],
        )

    def test_a_synthetic_row_renders_into_the_match_file(self):
        row = gen.build_row(ready_record(), ("B_Plane_CAS_01_F",))
        assert row is not None
        text = gen.render_match([row])
        self.assertIn('"fixture_aircraft", "fixture_variant", "fixed_wing"', text)
        self.assertIn('"bplanecas01f"', text)


class TestGradedResolution(unittest.TestCase):
    """The four named derivations, graded, against temp fixtures."""

    def test_rated_power_derives_from_thrust(self) -> None:
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 1000),
                "thrust_kn": value("thrust_kn", 76.0),
                "reference_speed_ms": value("reference_speed_ms", 250.0),
            }
        )
        rated = row_fields(record)["rated_power_w"]
        self.assertEqual("derived", rated.grade)
        self.assertEqual(76.0 * 1000.0 * 250.0, rated.value)
        self.assertIn(
            "rated_power_w = thrust_kn * 1000 * reference_speed_ms", rated.state
        )

    def test_rated_power_derives_from_net_power_kw(self) -> None:
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 1000),
                "net_power_kw": value("net_power_kw", 500.0),
            }
        )
        rated = row_fields(record)["rated_power_w"]
        self.assertEqual("derived", rated.grade)
        self.assertEqual(500000.0, rated.value)

    def test_rated_power_derives_from_published_power_hp(self) -> None:
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 1000),
                "published_power_hp": value("published_power_hp", 200.0),
            }
        )
        rated = row_fields(record)["rated_power_w"]
        self.assertEqual("derived", rated.grade)
        self.assertAlmostEqual(200.0 * 745.699872, rated.value, places=6)

    def test_rotor_disc_derives_from_diameter(self) -> None:
        record = ready_record(
            vehicle_type="rotary_wing",
            class_token="Helicopter",
            values={
                "operating_weight_kg": value("operating_weight_kg", 1000),
                "net_power_kw": value("net_power_kw", 500.0),
                "rotor_diameter_m": value("rotor_diameter_m", 10.0),
            },
        )
        disc = row_fields(record)["rotor_disc_area_m2"]
        self.assertEqual("derived", disc.grade)
        self.assertAlmostEqual(math.pi * (10.0 / 2.0) ** 2, disc.value, places=6)

    def test_drag_area_derives_from_coefficient_and_wing_area(self) -> None:
        record = ready_record(
            values={
                "operating_weight_kg": value("operating_weight_kg", 1000),
                "thrust_kn": value("thrust_kn", 50.0),
                "reference_speed_ms": value("reference_speed_ms", 200.0),
                "drag_coefficient": value("drag_coefficient", 0.02),
                "wing_area_m2": value("wing_area_m2", 30.0),
            }
        )
        drag = row_fields(record)["drag_area_m2"]
        self.assertEqual("derived", drag.grade)
        self.assertAlmostEqual(0.6, drag.value, places=6)
        self.assertIn("drag_area_m2 = drag_coefficient * wing_area_m2", drag.state)

    def test_operating_weight_derives_from_empty_weight(self) -> None:
        record = ready_record(
            values={
                "empty_weight_kg": value("empty_weight_kg", 5000),
                "thrust_kn": value("thrust_kn", 50.0),
                "reference_speed_ms": value("reference_speed_ms", 200.0),
            }
        )
        mass = row_fields(record)["operating_weight_kg"]
        self.assertEqual("derived", mass.grade)
        self.assertEqual(5000, mass.value)

    def test_an_empty_record_resolves_every_value_absent(self) -> None:
        fields = row_fields(ready_record())
        for field in gen.VALUE_FIELDS:
            self.assertEqual("absent", fields[field].grade, field)
            self.assertEqual(0, fields[field].value, field)


class TestRealCorpus(unittest.TestCase):
    def test_the_first_slice_sentinels_are_present(self):
        rows = gen.load_rows(gen.DEFAULT_DATA)
        ids = {row[COL_CATALOGUE] for row in rows}
        for sentinel in FIRST_SLICE:
            self.assertIn(sentinel, ids)

    def test_every_live_row_has_nine_columns_and_four_values(self):
        rows = gen.load_rows(gen.DEFAULT_DATA)
        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            self.assertEqual(len(row), ROW_COLUMNS)
            self.assertEqual(len(value_row(row)), VALUE_COLUMNS)

    def test_a_ready_entry_carries_a_nonzero_mass_and_power(self):
        rows = {row[COL_CATALOGUE]: row for row in gen.load_rows(gen.DEFAULT_DATA)}
        for sentinel in ("md500", "cessna_172_skyhawk"):
            self.assertGreater(value_row(rows[sentinel])[0], 0, sentinel)
            self.assertGreater(value_row(rows[sentinel])[1], 0, sentinel)


class TestCallerContract(unittest.TestCase):
    """The exhaust-shimmer caller reads the generated lookup."""

    def test_the_caller_reads_the_generated_lookup(self):
        self.assertIn("EFUNC(flight,getAircraftData)", CALLER)

    def test_the_caller_keeps_the_declared_fallbacks(self):
        self.assertIn("_rated = 150000;", CALLER)
        self.assertIn("_dragArea = 0.7;", CALLER)
        self.assertIn("_discArea = 50;", CALLER)

    def test_the_caller_reads_the_four_value_row(self):
        self.assertIn("count _row == 4", CALLER)
        for index in range(VALUE_COLUMNS):
            self.assertIn(f"_row select {index}", CALLER)


if __name__ == "__main__":
    unittest.main()
