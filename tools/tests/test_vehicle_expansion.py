#!/usr/bin/env python3
"""Sourced vehicle catalogue expansion tests.

Two real catalogue entries extend the corpus beyond the first military slice:

- a civilian car, the 6th generation Honda Civic 4 door Sedan, wheeled, from
  the held tier-2 Honda Civic Factory Service Manual (96-00);
- a military truck, the M923A2, wheeled, from the held tier-2 operator manual
  TM 9-2320-272-10 / Air Force TO 36A12-1C-441.

Both entries are incomplete leads. Each is not runtime-ready. Both emit a
runtime row, because each has a complete identity. No real source names an
AEE game class for either variant, so ``data/vehicle/class_map.json`` holds
one ``claimed`` engine class-table binding per entry. Every value cites a
held source id with a locator, a unit, a state and a grade. Neither entry
holds an operating weight, a net power, a tyre width or a tyre diameter.

Run: python3 -m unittest tools.tests.test_vehicle_expansion -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_vehicle_data as v  # noqa: E402
from tools.validation.fetch_vehicle_sources import verify_sources  # noqa: E402

DATA = REPO / "data" / "vehicle"
CATALOGUE = DATA / "catalogue"
CLASS_MAP = DATA / "class_map.json"
SOURCES = DATA / "sources.json"
GEN_COVERAGE = REPO / "tools" / "validation" / "gen_vehicle_coverage.py"

HONDA_SOURCE = "honda_civic_factory_service_manual_96_00"
TRUCK_SOURCE = "tm_9_2320_272_10"
HONDA_CAPTURE = CATALOGUE / "honda_civic_96_00.json"
TRUCK_CAPTURE = CATALOGUE / "m923a2.json"

VALUE_KEYS = ("value", "unit", "source", "locator", "state", "grade")

JsonObject = dict[str, object]


def _load(path: Path) -> object:
    return cast("object", json.loads(path.read_text(encoding="utf-8")))


def _mapping(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError(f"expected an object, got {type(value).__name__}")
    result: JsonObject = {}
    for key, item in cast("dict[object, object]", value).items():
        result[str(key)] = item
    return result


def _one_entry(path: Path) -> JsonObject:
    capture = _mapping(_load(path))
    raw = capture.get("entries")
    if not isinstance(raw, list):
        raise TypeError(f"{path.name}: entries must be an array")
    entries = [_mapping(item) for item in cast("list[object]", raw)]
    if len(entries) != 1:
        raise AssertionError(f"{path.name}: expected one entry, got {len(entries)}")
    return entries[0]


def _values(entry: JsonObject) -> dict[str, JsonObject]:
    raw = entry.get("values")
    if not isinstance(raw, dict):
        raise TypeError("entry values must be an object")
    return {
        str(key): _mapping(item)
        for key, item in cast("dict[object, object]", raw).items()
    }


def _registry() -> list[JsonObject]:
    raw = _load(SOURCES)
    if not isinstance(raw, list):
        raise TypeError("sources.json must be an array")
    return [_mapping(item) for item in cast("list[object]", raw)]


class VehicleExpansionTest(unittest.TestCase):
    def test_captures_parse_and_name_the_new_entries(self) -> None:
        self.assertTrue(HONDA_CAPTURE.is_file(), HONDA_CAPTURE)
        self.assertTrue(TRUCK_CAPTURE.is_file(), TRUCK_CAPTURE)
        self.assertEqual(
            "honda_civic_6gen_sedan", _one_entry(HONDA_CAPTURE)["catalogue_id"]
        )
        self.assertEqual("m923a2", _one_entry(TRUCK_CAPTURE)["catalogue_id"])

    def test_both_new_entries_are_wheeled_and_not_runtime(self) -> None:
        honda = _one_entry(HONDA_CAPTURE)
        truck = _one_entry(TRUCK_CAPTURE)
        self.assertEqual("wheeled", honda["vehicle_type"])
        self.assertEqual("wheeled", truck["vehicle_type"])
        self.assertIs(False, honda["runtime_ready"])
        self.assertIs(False, truck["runtime_ready"])

    def test_each_entry_binds_through_a_claimed_class_table_record(self) -> None:
        # No real-world source names an AEE class for either variant, so the
        # catalogue class_token stays empty and the class map holds one
        # claimed engine class-table binding per entry.
        self.assertEqual("", _one_entry(HONDA_CAPTURE)["class_token"])
        self.assertEqual("", _one_entry(TRUCK_CAPTURE)["class_token"])
        records = _load(CLASS_MAP)
        self.assertIsInstance(records, list)
        bound = (
            {str(item.get("catalogue_id")): item for item in records}
            if isinstance(records, list)
            else {}
        )
        for catalogue_id in ("honda_civic_6gen_sedan", "m923a2"):
            self.assertIn(catalogue_id, bound)
            record = bound[catalogue_id]
            self.assertEqual("claimed", record["grade"])
            self.assertEqual(
                "class_table", record["identity_source"].replace("aee_", "")
            )
            self.assertIn(record["class_token"], record["identity_evidence"])

    def test_new_sources_exist_are_held_and_match_their_digest(self) -> None:
        by_id = {str(item.get("source_id")): item for item in _registry()}
        for source_id in (HONDA_SOURCE, TRUCK_SOURCE):
            self.assertIn(source_id, by_id)
            entry = by_id[source_id]
            self.assertIs(True, entry.get("primary_held"), source_id)
            self.assertEqual(2, entry.get("tier"), source_id)
            self.assertEqual("manual", entry.get("type"), source_id)
            digest = entry.get("sha256")
            self.assertIsInstance(digest, str)
            self.assertEqual(64, len(cast("str", digest)), source_id)
        self.assertEqual([], verify_sources(_registry(), DATA / "sources"))

    def test_pinned_digests_match_the_task_contract(self) -> None:
        by_id = {str(item.get("source_id")): item for item in _registry()}
        self.assertEqual(
            "31afe30bc1d1064482c8c510b6264fbcf884afd862306bd57815ab14b409bec3",
            by_id[HONDA_SOURCE]["sha256"],
        )
        self.assertEqual(
            "7407b35b7a876a87c7af9a549a173121b8220ab218e8d4a29c074e849e616ed4",
            by_id[TRUCK_SOURCE]["sha256"],
        )

    def test_every_value_carries_unit_locator_state_and_grade(self) -> None:
        for path in (HONDA_CAPTURE, TRUCK_CAPTURE):
            for field, entry in _values(_one_entry(path)).items():
                with self.subTest(capture=path.name, field=field):
                    self.assertEqual(set(VALUE_KEYS), set(entry))
                    self.assertIn(field, v.FIELD_UNITS)
                    self.assertEqual(v.FIELD_UNITS[field], entry["unit"])
                    for key in ("locator", "state", "grade"):
                        text = entry[key]
                        self.assertIsInstance(text, str)
                        self.assertNotEqual("", cast("str", text).strip())
                    raw = entry["value"]
                    self.assertIsInstance(raw, (int, float, str))
                    if v.FIELD_UNITS[field] in v.NON_NUMERIC_UNITS:
                        self.assertIsInstance(raw, str)
                    else:
                        self.assertIsInstance(raw, (int, float))

    def test_every_value_cites_a_held_tier_two_manual(self) -> None:
        held = {
            str(item.get("source_id"))
            for item in _registry()
            if item.get("primary_held") is True
        }
        for path in (HONDA_CAPTURE, TRUCK_CAPTURE):
            for field, entry in _values(_one_entry(path)).items():
                with self.subTest(capture=path.name, field=field):
                    self.assertIn(entry["source"], held)
                    self.assertEqual("documented", entry["grade"])

    def test_both_entries_claim_no_operating_weight_net_power_or_tyre_size(
        self,
    ) -> None:
        for path in (HONDA_CAPTURE, TRUCK_CAPTURE):
            values = _values(_one_entry(path))
            for absent in (
                "operating_weight_kg",
                "net_power_kw",
                "tyre_width_mm",
                "tyre_diameter_mm",
            ):
                with self.subTest(capture=path.name, field=absent):
                    self.assertNotIn(absent, values)

    def test_honda_is_a_civilian_car_with_no_tyre_fields(self) -> None:
        entry = _one_entry(HONDA_CAPTURE)
        self.assertEqual("Honda", entry["maker"])
        self.assertEqual("Civic", entry["model"])
        values = _values(entry)
        for absent in (
            "tyre_size_text",
            "tyre_pressure_kpa",
            "wheel_count",
            "axle_count",
        ):
            self.assertNotIn(absent, values)

    def test_honda_values_are_source_backed(self) -> None:
        values = _values(_one_entry(HONDA_CAPTURE))
        self.assertEqual(4450, values["length_mm"]["value"])
        self.assertEqual(1705, values["width_mm"]["value"])
        self.assertEqual(1390, values["height_mm"]["value"])
        self.assertEqual(2620, values["wheelbase_mm"]["value"])
        self.assertEqual(1475, values["track_mm"]["value"])
        self.assertEqual(150, values["ground_clearance_mm"]["value"])
        self.assertEqual(1540, values["gross_weight_kg"]["value"])
        self.assertEqual("automatic", values["transmission_type"]["value"])
        self.assertEqual(4, values["gears"]["value"])
        self.assertEqual("Honda D16Y8", values["engine_model"]["value"])
        self.assertEqual(1.59, values["engine_displacement_l"]["value"])

    def test_honda_track_records_the_printed_value_not_the_ocr_digit(self) -> None:
        # The page image prints 1,475/1,475 mm and 58.1/58.1 in. The PDF text
        # layer misreads the rear as 1,415 mm, which must not enter the corpus.
        track = _values(_one_entry(HONDA_CAPTURE))["track_mm"]
        self.assertEqual(1475, track["value"])
        state = cast("str", track["state"])
        self.assertIn("1,475/1,475", state)
        self.assertIn("1,415", state)

    def test_truck_is_a_cargo_wheeled_truck_with_a_tyre_size_code_only(self) -> None:
        entry = _one_entry(TRUCK_CAPTURE)
        self.assertEqual("unknown", entry["maker"])
        self.assertEqual("M939A2", entry["model"])
        values = _values(entry)
        self.assertEqual("14:00 x R20", values["tyre_size_text"]["value"])
        for absent in ("wheel_count", "axle_count"):
            self.assertNotIn(absent, values)

    def test_truck_values_are_source_backed(self) -> None:
        values = _values(_one_entry(TRUCK_CAPTURE))
        self.assertEqual(7887, values["length_mm"]["value"])
        self.assertEqual(2474, values["width_mm"]["value"])
        self.assertEqual(3073, values["height_mm"]["value"])
        self.assertEqual(4547, values["wheelbase_mm"]["value"])
        self.assertEqual(353, values["ground_clearance_mm"]["value"])
        self.assertEqual(9502, values["curb_weight_kg"]["value"])
        self.assertEqual(4540, values["payload_kg"]["value"])
        self.assertEqual(6810, values["towing_capacity_kg"]["value"])
        self.assertEqual(12.4, values["turning_radius_m"]["value"])
        self.assertEqual(46, values["approach_angle_deg"]["value"])
        self.assertEqual(38, values["departure_angle_deg"]["value"])
        self.assertEqual(760, values["fording_depth_mm"]["value"])
        self.assertEqual(1980, values["wading_depth_mm"]["value"])
        self.assertEqual(240, values["published_power_hp"]["value"])
        self.assertEqual("Cummins 6CTA8.3", values["engine_model"]["value"])
        self.assertEqual("automatic", values["transmission_type"]["value"])
        self.assertEqual(5, values["gears"]["value"])
        self.assertEqual(483, values["tyre_pressure_kpa"]["value"])
        self.assertEqual(88, values["max_speed_kmh"]["value"])

    def test_captures_keep_the_retired_sources_array_empty(self) -> None:
        for path in (HONDA_CAPTURE, TRUCK_CAPTURE):
            capture = _mapping(_load(path))
            self.assertEqual([], capture["sources"], path.name)

    def test_default_validator_accepts_the_whole_corpus(self) -> None:
        self.assertEqual([], v.run(DATA))

    def test_coverage_generator_check_is_fresh(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GEN_COVERAGE), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_new_leads_appear_in_the_generated_gap_report(self) -> None:
        report = (DATA / "SOURCE_GAPS.md").read_text(encoding="utf-8")
        self.assertIn("honda_civic_6gen_sedan", report)
        self.assertIn("m923a2", report)
        self.assertIn("- Catalogue entries: 4", report)


if __name__ == "__main__":
    unittest.main()
