#!/usr/bin/env python3
"""Physics config-binding gate tests.

The config-binding corpus binds one engine config key on one concrete game
class to one held catalogue value through a named conversion. The validator
is the gate. These tests prove a clean corpus passes, an invented value fails
and an unknown conversion fails. The good records come from the committed
corpus. The bad records are copies held in this test only.

Run: python3 -m unittest tools.tests.test_physics_config -v
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_physics_config as v  # noqa: E402

DATA = REPO / "data" / "physics"
VEHICLE = REPO / "data" / "vehicle"
BINDINGS = DATA / "config_bindings.json"


def _run_with(records: list[object]) -> int:
    """Write a corpus to a temporary data dir and run the validator CLI."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / v.BINDINGS_NAME
        path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return v.main(["--data-dir", tmp, "--vehicle-dir", str(VEHICLE)])


class PhysicsConfigTest(unittest.TestCase):
    """The committed corpus is valid and the gate rejects a broken corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.records = v.load_bindings(BINDINGS)
        cls.catalogue_ids = v.catalogue_by_id(VEHICLE)
        cls.class_bindings = v.class_binding_map(VEHICLE)
        cls.sources = v.sources_by_id(VEHICLE)

    def _errors(self, records: list[object]) -> list[str]:
        return v.validate_bindings(
            records, self.catalogue_ids, self.class_bindings, self.sources
        )

    def test_the_committed_file_is_clean(self) -> None:
        self.assertEqual(self._errors(self.records), [])

    def test_the_cli_passes(self) -> None:
        self.assertEqual(v.main([]), 0)

    def test_an_invented_value_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["value"] = records[0]["value"] + 7
        self.assertTrue(
            any("does not reproduce" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_an_invented_value_fails_the_cli(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["value"] = records[0]["value"] + 7
        self.assertEqual(_run_with(records), 1)

    def test_an_unknown_conversion_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["conversion"] = "warp_speed"
        self.assertTrue(
            any("unknown conversion" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_an_unknown_conversion_fails_the_cli(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["conversion"] = "warp_speed"
        self.assertEqual(_run_with(records), 1)

    def test_an_unknown_game_class_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["game_class"] = "B_No_Such_Class_F"
        self.assertTrue(
            any("unknown game_class" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_an_unknown_source_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["value_source"]["source_id"] = "no_such_source"
        self.assertTrue(
            any("unknown source_id" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_a_mismatched_source_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["value_source"]["source_id"] = "aee_class_table"
        self.assertTrue(
            any("does not own" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_a_class_with_no_held_field_fails(self) -> None:
        records = copy.deepcopy(self.records)
        # The Civic hatchback is bound, but its catalogue entry holds no
        # max_speed_kmh. A recorded binding for it is an error.
        records[0]["game_class"] = "C_Hatchback_01_F"
        self.assertTrue(
            any("holds no value for field" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_an_undocumented_key_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["key"] = "maxHealth"
        self.assertEqual(_run_with(records), 1)

    def test_an_empty_required_field_fails(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["unit"] = ""
        self.assertTrue(
            any("required field is empty" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_identity_keeps_the_held_grade(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["grade"] = "claimed"
        self.assertTrue(
            any("keeps the held grade" in e for e in self._errors(records)),
            self._errors(records),
        )

    def test_every_binding_resolves_to_a_held_field(self) -> None:
        for record in self.records:
            with self.subTest(game_class=record["game_class"]):
                catalogue_id = self.class_bindings[record["game_class"]]
                entry = self.catalogue_ids[catalogue_id]
                field = record["value_source"]["field"]
                self.assertIsNotNone(v.catalogue.held_value(entry.values, field))

    def test_a_class_with_no_held_field_is_omitted(self) -> None:
        bound = {record["game_class"] for record in self.records}
        self.assertNotIn("C_Hatchback_01_F", bound)

    def test_a_non_array_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / v.BINDINGS_NAME
            path.write_text(json.dumps({"game_class": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                v.load_bindings(path)


if __name__ == "__main__":
    unittest.main()
