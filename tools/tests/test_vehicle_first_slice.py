#!/usr/bin/env python3
"""First sourced vehicle catalogue slice tests.

The first two real catalogue entries come from held tier-2 operator manuals:

- the Oshkosh M-ATV M1240, wheeled, from TM 9-2355-335-10;
- the M113A2 carrier, tracked, from TM 9-2350-261-10.

Both entries are incomplete leads. Each is not runtime-ready. Both emit a
runtime row, because each has a complete identity. No real source names an
AEE game class for either variant, so ``data/vehicle/class_map.json`` holds
one ``claimed`` engine class-table binding per entry. Every value cites a
held source id with a locator, a unit, a state and a grade.

Run: python3 -m unittest tools.tests.test_vehicle_first_slice -v
"""

from __future__ import annotations

import json
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

MATV_SOURCE = "tm_9_2355_335_10"
M113_SOURCE = "tm_9_2350_261_10"
MATV_CAPTURE = CATALOGUE / f"{MATV_SOURCE}.json"
M113_CAPTURE = CATALOGUE / f"{M113_SOURCE}.json"

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


def _entries(path: Path) -> list[JsonObject]:
    capture = _mapping(_load(path))
    raw = capture.get("entries")
    if not isinstance(raw, list):
        raise TypeError(f"{path.name}: entries must be an array")
    return [_mapping(item) for item in cast("list[object]", raw)]


def _one_entry(path: Path) -> JsonObject:
    entries = _entries(path)
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


class FirstSliceTest(unittest.TestCase):
    def test_captures_parse_and_name_the_held_manual(self) -> None:
        self.assertTrue(MATV_CAPTURE.is_file(), MATV_CAPTURE)
        self.assertTrue(M113_CAPTURE.is_file(), M113_CAPTURE)
        self.assertEqual("m_atv_m1240", _one_entry(MATV_CAPTURE)["catalogue_id"])
        self.assertEqual("m113a2", _one_entry(M113_CAPTURE)["catalogue_id"])

    def test_both_entries_are_wheeled_and_tracked_and_not_runtime(self) -> None:
        matv = _one_entry(MATV_CAPTURE)
        m113 = _one_entry(M113_CAPTURE)
        self.assertEqual("wheeled", matv["vehicle_type"])
        self.assertEqual("tracked", m113["vehicle_type"])
        self.assertIs(False, matv["runtime_ready"])
        self.assertIs(False, m113["runtime_ready"])

    def test_each_entry_binds_through_a_claimed_class_table_record(self) -> None:
        # No real-world source names an AEE class for either variant, so the
        # catalogue class_token stays empty and the class map holds one
        # claimed engine class-table binding per entry.
        self.assertEqual("", _one_entry(MATV_CAPTURE)["class_token"])
        self.assertEqual("", _one_entry(M113_CAPTURE)["class_token"])
        records = _load(CLASS_MAP)
        self.assertIsInstance(records, list)
        assert isinstance(records, list)
        bound = {
            str(item.get("catalogue_id")): item
            for item in cast("list[object]", records)
            if isinstance(item, dict)
        }
        for catalogue_id in ("m_atv_m1240", "m113a2"):
            self.assertIn(catalogue_id, bound)
            record = bound[catalogue_id]
            self.assertEqual("claimed", record["grade"])
            self.assertEqual(
                "class_table", record["identity_source"].replace("aee_", "")
            )
            self.assertIn(record["class_token"], record["identity_evidence"])

    def test_sources_exist_are_held_and_match_their_digest(self) -> None:
        by_id = {str(item.get("source_id")): item for item in _registry()}
        for source_id in (MATV_SOURCE, M113_SOURCE):
            self.assertIn(source_id, by_id)
            entry = by_id[source_id]
            self.assertIs(True, entry.get("primary_held"), source_id)
            self.assertEqual(2, entry.get("tier"), source_id)
            self.assertEqual("manual", entry.get("type"), source_id)
        self.assertEqual([], verify_sources(_registry(), DATA / "sources"))

    def test_matv_has_curb_and_gross_weight_but_no_operating_weight(self) -> None:
        values = _values(_one_entry(MATV_CAPTURE))
        self.assertIn("curb_weight_kg", values)
        self.assertIn("gross_weight_kg", values)
        self.assertNotIn("operating_weight_kg", values)
        self.assertEqual(11123, values["curb_weight_kg"]["value"])
        self.assertEqual(16798, values["gross_weight_kg"]["value"])
        self.assertEqual(370, values["published_power_hp"]["value"])
        self.assertNotIn("net_power_kw", values)
        self.assertEqual("automatic", values["transmission_type"]["value"])
        self.assertIn("tyre_size_text", values)

    def test_matv_has_no_unsourced_tyre_geometry_or_clearance(self) -> None:
        values = _values(_one_entry(MATV_CAPTURE))
        for absent in (
            "tyre_width_mm",
            "tyre_diameter_mm",
            "ground_clearance_mm",
        ):
            self.assertNotIn(absent, values)

    def test_m113_has_no_tyre_fields(self) -> None:
        values = _values(_one_entry(M113_CAPTURE))
        for absent in (
            "tyre_width_mm",
            "tyre_diameter_mm",
            "tyre_pressure_kpa",
            "tyre_size_text",
            "wheel_count",
            "axle_count",
        ):
            self.assertNotIn(absent, values)

    def test_m113_has_no_operating_weight_or_track_pitch(self) -> None:
        values = _values(_one_entry(M113_CAPTURE))
        self.assertIn("gross_weight_kg", values)
        self.assertNotIn("operating_weight_kg", values)
        self.assertNotIn("net_power_kw", values)
        self.assertNotIn("track_shoe_width_mm", values)
        self.assertNotIn("track_pitch_mm", values)
        self.assertEqual(11353, values["gross_weight_kg"]["value"])
        self.assertEqual(210, values["published_power_hp"]["value"])
        self.assertEqual(434.8, values["ground_clearance_mm"]["value"])
        self.assertEqual(1016, values["fording_depth_mm"]["value"])
        self.assertEqual("automatic", values["transmission_type"]["value"])
        self.assertEqual(63, values["track_shoe_count"]["value"])
        self.assertEqual("grousers", values["grousers_state"]["value"])

    def test_every_value_cites_a_held_tier_two_manual(self) -> None:
        held = {
            str(item.get("source_id"))
            for item in _registry()
            if item.get("primary_held") is True
        }
        for path in (MATV_CAPTURE, M113_CAPTURE):
            for field, entry in _values(_one_entry(path)).items():
                with self.subTest(capture=path.name, field=field):
                    self.assertIn(entry["source"], held)
                    self.assertEqual("documented", entry["grade"])

    def test_every_value_carries_unit_locator_state_and_grade(self) -> None:
        for path in (MATV_CAPTURE, M113_CAPTURE):
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

    def test_default_validator_accepts_the_whole_corpus(self) -> None:
        self.assertEqual([], v.run(DATA))


if __name__ == "__main__":
    unittest.main()
