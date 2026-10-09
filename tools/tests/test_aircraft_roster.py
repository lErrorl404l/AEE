#!/usr/bin/env python3
"""Aircraft class roster guard tests (aircraft systems, wave 2 task 9).

The roster logic lives in the production generator
``tools/validation/gen_aircraft_roster.py``. This module imports it.

The guard flags a roster class that is absent from the committed
``data/aircraft/class_inventory.json``, so the roster never names a class
the config read did not see. The committed roster and report must match a
fresh headless build, so a stale artefact fails the gate.

Run: python3 -m unittest tools.tests.test_aircraft_roster -v
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_aircraft_roster as g  # noqa: E402
from tools.validation import vehicle_catalogue as vc  # noqa: E402

DATA = REPO / "data" / "aircraft"
INVENTORY = DATA / g.INVENTORY_OUT
ROSTER = DATA / g.ROSTER_OUT
REPORT = DATA / g.ROSTER_REPORT


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _classes(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise TypeError("inventory must be an object")
    records = payload.get("classes")
    if not isinstance(records, list):
        raise TypeError("classes must be a list")
    out: list[dict[str, object]] = []
    for item in records:
        if not isinstance(item, dict):
            raise TypeError("class row must be an object")
        out.append(item)
    return out


class RosterDerivationTest(unittest.TestCase):
    def test_the_roster_derives_from_the_inventory(self) -> None:
        inventory = _load(INVENTORY)
        rows = g.build_roster(inventory)  # a dict satisfies the JsonObject shape
        self.assertTrue(rows)
        self.assertEqual(rows, _load(ROSTER))

    def test_every_roster_row_carries_a_game_class(self) -> None:
        rows = _load(ROSTER)
        self.assertIsInstance(rows, list)
        for row in rows:
            self.assertTrue(row.get("game_class"))

    def test_the_roster_has_at_least_45_rows(self) -> None:
        rows = _load(ROSTER)
        self.assertGreaterEqual(len(rows), 45)

    def test_every_roster_token_is_a_closed_air_token(self) -> None:
        for row in _load(ROSTER):
            self.assertIn(row.get("class_token"), g.AIR_TOKENS, row.get("game_class"))

    def test_a_derivation_is_deterministic(self) -> None:
        inventory = _load(INVENTORY)
        first = json.dumps(g.build_roster(inventory), sort_keys=True)
        second = json.dumps(g.build_roster(inventory), sort_keys=True)
        self.assertEqual(first, second)

    def test_the_inventory_holds_every_bound_class(self) -> None:
        # A bound class that the config read missed is a gap, not a silent drop.
        known = {row["class"] for row in _classes(_load(INVENTORY))}
        bindings = _load(DATA / "class_bindings.json")
        self.assertIsInstance(bindings, list)
        for binding in bindings:
            self.assertIn(binding["game_class"], known)


class RosterGuardTest(unittest.TestCase):
    def test_a_clean_roster_has_no_errors(self) -> None:
        inventory = _load(INVENTORY)
        rows = g.build_roster(inventory)
        self.assertEqual([], g.roster_errors(inventory, rows))

    def test_a_roster_class_absent_from_the_inventory_is_flagged(self) -> None:
        inventory = _load(INVENTORY)
        rows = g.build_roster(inventory)
        rows.append(
            {
                "game_class": "FIXTURE_Not_In_The_Inventory_F",
                "class_token": "Plane",
                "base_class": "FIXTURE",
                "variant_family": "FIXTURE",
                "role": "variant",
                "is_variant": True,
            }
        )
        errors = g.roster_errors(inventory, rows)
        self.assertTrue(
            any(
                "FIXTURE_Not_In_The_Inventory_F" in error
                and "absent from the committed inventory" in error
                for error in errors
            ),
            errors,
        )

    def test_a_non_air_inventory_class_is_flagged(self) -> None:
        inventory = _load(INVENTORY)
        self.assertIsInstance(inventory, dict)
        classes = inventory["classes"]
        self.assertIsInstance(classes, list)
        classes.append({"class": "FIXTURE_Car_F", "class_token": "Car", "scope": 2})
        errors = g.roster_errors(inventory, [])
        self.assertTrue(any("not an air class" in error for error in errors), errors)


class CommittedArtefactsTest(unittest.TestCase):
    def test_the_committed_report_matches_a_fresh_build(self) -> None:
        inventory = _load(INVENTORY)
        rows = g.build_roster(inventory)
        self.assertEqual(
            REPORT.read_text(encoding="utf-8"), g.build_roster_report(inventory, rows)
        )

    def test_check_is_fresh_on_the_committed_artefacts(self) -> None:
        self.assertEqual(0, g.check_all(DATA))

    def test_check_fails_when_the_roster_names_an_unknown_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(INVENTORY, root / g.INVENTORY_OUT)
            rows = json.loads(ROSTER.read_text(encoding="utf-8"))
            rows.append({"game_class": "FIXTURE_Unknown_F", "class_token": "Plane"})
            (root / g.ROSTER_OUT).write_text(json.dumps(rows), encoding="utf-8")
            (root / g.ROSTER_REPORT).write_text("stale\n", encoding="utf-8")
            self.assertEqual(1, g.check_all(root))

    def test_check_fails_on_a_stale_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(INVENTORY, root / g.INVENTORY_OUT)
            shutil.copy(ROSTER, root / g.ROSTER_OUT)
            (root / g.ROSTER_REPORT).write_text("stale\n", encoding="utf-8")
            self.assertEqual(1, g.check_all(root))


class ResolutionGuardTest(unittest.TestCase):
    """Every roster class is bound or carries a no_source reason (task 10)."""

    def _bindings(self) -> list[object]:
        payload = _load(DATA / "class_bindings.json")
        self.assertIsInstance(payload, list)
        return list(payload)

    def test_every_roster_class_is_bound_or_no_source(self) -> None:
        errors = g.resolution_errors(_load(ROSTER), self._bindings())
        self.assertEqual([], errors)

    def test_a_no_source_family_carries_a_reason(self) -> None:
        rows = [row for row in _load(ROSTER) if row.get("no_source_reason")]
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row.get("no_source_reason"))

    def test_a_class_that_is_neither_bound_nor_no_source_is_reported(self) -> None:
        roster = _load(ROSTER)
        for row in roster:
            row.pop("no_source_reason", None)
        bindings = [
            b for b in self._bindings() if b["game_class"] != "B_Heli_Attack_01_F"
        ]
        errors = g.resolution_errors(roster, bindings)
        self.assertTrue(
            any(
                "B_Heli_Attack_01_F" in error and "neither" in error for error in errors
            ),
            errors,
        )

    def test_an_invented_analogue_is_rejected_by_the_validator(self) -> None:
        # A binding to a fictional analogue names a catalogue id the corpus
        # does not hold, so the loader reports an unknown catalogue_id.
        bindings = self._bindings()
        invented = dict(bindings[0])
        invented["catalogue_id"] = "fixture_invented_analogue"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(DATA / "catalogue", root / "catalogue")
            shutil.copy(DATA / "sources.json", root / "sources.json")
            (root / "class_bindings.json").write_text(
                json.dumps([invented]), encoding="utf-8"
            )
            loaded = vc.load(root, profile=vc.AIRCRAFT_PROFILE)
        self.assertEqual([], loaded.bindings)
        self.assertTrue(
            any("unknown catalogue_id" in error for error in loaded.errors),
            loaded.errors,
        )


if __name__ == "__main__":
    unittest.main()
