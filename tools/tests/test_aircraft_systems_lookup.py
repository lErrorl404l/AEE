#!/usr/bin/env python3
"""Aircraft systems lookup generator tests (task 8).

The systems lookup is generated from the validated aircraft catalogue by
``tools/validation/gen_aircraft_systems.py``. Every catalogue entry with a
complete identity emits a row. A value that is not held is a labelled absent
zero, not a reason to refuse the record. These tests hold the three-column row
contract, the fixed systems field order, the labelled absent zero, the
generated marker, the ordered field-name tuple and the caller wiring.

The complete records live only in this test file. They hold sentinel values,
name no real aircraft and are never written to the corpus.

Run: python3 -m unittest tools.tests.test_aircraft_systems_lookup -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_aircraft_systems as gen  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

SYSTEMS_PATH = REPO / "addons" / "mobility" / "functions" / "fnc_getAircraftSystems.sqf"
PREP_PATH = REPO / "addons" / "mobility" / "XEH_PREP.hpp"
SYSTEMS = SYSTEMS_PATH.read_text(encoding="utf-8")

# The plan's authoritative ordered field tuple. The generator must match it.
PLAN_NUMERIC = (
    "fuel_capacity",
    "fuel_consumption_rate",
    "fuel_density_kg_l",
    "sfc_kg_kwh",
    "fuel_cg_arm_m",
    "engine_idle_ng",
    "engine_max_ng",
    "engine_max_np",
    "engine_max_torque_nm",
    "engine_max_tgt_c",
    "engine_oil_pressure_min_kpa",
    "engine_oil_pressure_max_kpa",
    "transmission_torque_limit_nm",
    "hydraulic_pressure_kpa",
    "generator_power_kw",
    "bus_voltage_v",
    "battery_capacity_ah",
    "cabin_pressure_max_kpa",
)
PLAN_ENUM = ("fuel_type", "engine_oil_type", "oxygen_system")
ROW_LENGTH = len(PLAN_NUMERIC) + len(PLAN_ENUM)


def value(field: str, raw: object) -> dict[str, object]:
    """A complete value object. The source is a test fixture, not a document."""
    return {
        "value": raw,
        "unit": catalogue.SYSTEMS_FIELD_UNITS[field],
        "source": "fixture_source",
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": "documented",
    }


def ready_record(
    vehicle_type: str = "rotary_wing",
    catalogue_id: str = "fixture_aircraft",
    variant_id: str = "fixture_variant",
    values: dict[str, object] | None = None,
) -> dict[str, object]:
    """A runtime-ready catalogue entry. Fixture only, one sentinel per field."""
    return {
        "catalogue_id": catalogue_id,
        "variant_id": variant_id,
        "vehicle_type": vehicle_type,
        "class_token": "Helicopter",
        "runtime_ready": True,
        "values": {} if values is None else values,
    }


def full_values() -> dict[str, object]:
    """One distinct sentinel per row position, in the fixed order."""
    fields = gen.SYSTEMS_ROW_FIELDS
    return {field: value(field, index + 1) for index, field in enumerate(fields)}


class TestGeneratedSystemsFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self) -> None:
        self.assertIn("GENERATED", SYSTEMS)
        self.assertIn("gen_aircraft_systems.py", SYSTEMS)
        self.assertIn("aee_mobility_fnc_getAircraftSystems", SYSTEMS)

    def test_the_header_states_the_ordered_field_tuple(self) -> None:
        header = SYSTEMS.split("*/", 1)[0]
        for field in PLAN_NUMERIC:
            self.assertIn(field, header, f"the header does not state {field}")
        for field in PLAN_ENUM:
            self.assertIn(field, header, f"the header does not state {field}")

    def test_the_lookup_consumes_the_matcher(self) -> None:
        self.assertIn("FUNC(getAircraftMatch)", SYSTEMS)
        self.assertIn("_match select 0", SYSTEMS)
        self.assertIn("_match select 1", SYSTEMS)

    def test_reads_no_source_registry_and_no_config_value(self) -> None:
        self.assertNotIn("sources.json", SYSTEMS)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, SYSTEMS, f"the lookup reads {command}")

    def test_the_unknown_class_returns_empty(self) -> None:
        self.assertIn('if (_className == "") exitWith { [] };', SYSTEMS)
        self.assertTrue(SYSTEMS.rstrip().endswith("(_row select 0) select 2"))


class TestFieldOrder(unittest.TestCase):
    def test_the_numeric_tuple_matches_the_plan(self) -> None:
        self.assertEqual(gen.SYSTEMS_FIELDS, PLAN_NUMERIC)

    def test_the_enum_tuple_matches_the_plan(self) -> None:
        self.assertEqual(gen.SYSTEMS_ENUM_FIELDS, PLAN_ENUM)


class TestGeneratorRows(unittest.TestCase):
    def test_a_ready_record_makes_a_three_column_row(self) -> None:
        row = gen.build_row(ready_record())
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(len(row), 3)

    def test_the_row_order_is_fixed(self) -> None:
        row = gen.build_row(ready_record(values=full_values()))
        assert row is not None
        values = row[2]
        assert isinstance(values, list)
        self.assertEqual(values, list(range(1, ROW_LENGTH + 1)))

    def test_the_identity_columns_follow_the_contract(self) -> None:
        row = gen.build_row(ready_record())
        assert row is not None
        self.assertEqual(row[0], "fixture_aircraft")
        self.assertEqual(row[1], "fixture_variant")

    def test_a_missing_value_resolves_to_a_labelled_zero(self) -> None:
        row = gen.build_row(ready_record())
        assert row is not None
        values = row[2]
        assert isinstance(values, list)
        self.assertEqual(values, [0] * ROW_LENGTH)

    def test_an_identity_incomplete_record_makes_no_row(self) -> None:
        self.assertIsNone(gen.build_row(ready_record(catalogue_id="")))
        self.assertIsNone(gen.build_row(ready_record(vehicle_type="wheeled")))

    def test_rows_are_stable_and_sorted(self) -> None:
        first = ready_record(catalogue_id="b_aircraft")
        second = ready_record(catalogue_id="a_aircraft")
        rows = gen.build_rows([first, second])
        self.assertEqual([row[0] for row in rows], ["a_aircraft", "b_aircraft"])

    def test_a_synthetic_row_renders_into_the_file(self) -> None:
        row = gen.build_row(ready_record(values=full_values()))
        assert row is not None
        text = gen.render_systems([row])
        self.assertIn('"fixture_aircraft", "fixture_variant"', text)
        self.assertIn(
            "1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21",
            text,
        )


class TestWiring(unittest.TestCase):
    def test_get_aircraft_systems_is_registered_once(self) -> None:
        prep = PREP_PATH.read_text(encoding="utf-8")
        hits = [line for line in prep.splitlines() if "getAircraftSystems" in line]
        self.assertEqual(len(hits), 1, hits)
        self.assertEqual(hits[0], "PREP(getAircraftSystems);")


if __name__ == "__main__":
    unittest.main()
