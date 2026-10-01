#!/usr/bin/env python3
"""Engine mass override gate tests.

The approved calibration pairs each bound class with a held real mass and one
fitted scale. The generator turns the approved calibration into a CfgVehicles
mass override. These tests prove the committed header is fresh, that every
value is a calibrated scale of a held real mass and never a copy of an engine
mass, that each emitted class states its immediate real parent, that the two
keys share one CfgVehicles block, and that the generator fails closed on an
unapproved calibration, a missing held mass and a missing parent.

Run: python3 -m unittest tools.tests.test_mass_config -v
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_physics_config as gen  # noqa: E402

VEHICLE = REPO / "data" / "vehicle"
CALIBRATION = REPO / "data" / "physics" / "mass_calibration.json"
CLASS_BINDINGS = VEHICLE / "class_bindings.json"
PARENTS = VEHICLE / "class_parents.json"
PROJECTION = REPO / "data" / "physics" / "config_bindings.json"
GENERATED = REPO / "addons" / "mobility" / "generated" / "CfgVehicles.hpp"

# One emitted class body: `class X: Parent {` ... `};`.
BODY_RE = re.compile(r"^[ \t]+class (\w+): (\w+) \{\n(.*?)\n[ \t]+\};", re.M | re.S)
# One assignment inside a body.
ASSIGN_RE = re.compile(r"^[ \t]+(\w+) = ([0-9.]+);", re.M)
# A forward declaration `class X;` at class level.
FORWARD_RE = re.compile(r"^[ \t]+class (\w+);$", re.M)
# A bare class body `class X {` with no parent. None is allowed.
BARE_RE = re.compile(r"^[ \t]+class (\w+) \{\s*$", re.M)

FORBIDDEN_KEYS = ("htMin", "htMax", "afMax", "mfMax", "mFact", "tBody")


def _calibration_payload() -> dict[str, object]:
    return json.loads(CALIBRATION.read_text(encoding="utf-8"))


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class MassOverrideTest(unittest.TestCase):
    """The committed header carries one calibrated mass per bound class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.calibration = gen.load_mass_calibration(CALIBRATION)
        cls.bindings = gen.build_class_bindings(
            CLASS_BINDINGS, VEHICLE, PARENTS, CALIBRATION
        )
        cls.rendered = GENERATED.read_text(encoding="utf-8")
        cls.bodies: dict[str, dict[str, object]] = {}
        cls.assigned: dict[str, dict[str, str]] = {}
        for name, parent, body in BODY_RE.findall(cls.rendered):
            cls.bodies[name] = {"parent": parent, "body": body}
            cls.assigned[name] = dict(ASSIGN_RE.findall(body))
        cls.forwards = FORWARD_RE.findall(cls.rendered)

    def test_the_committed_header_is_fresh(self) -> None:
        self.assertEqual(
            gen.check_config(
                CLASS_BINDINGS, VEHICLE, PARENTS, GENERATED, PROJECTION, CALIBRATION
            ),
            0,
        )

    def test_the_committed_header_is_fresh_from_the_cli(self) -> None:
        self.assertEqual(gen.main(["--check"]), 0)

    def test_every_bound_class_carries_a_calibrated_mass(self) -> None:
        self.assertEqual(set(self.bodies), set(gen.bound_classes(CLASS_BINDINGS)))
        for name, assigned in self.assigned.items():
            with self.subTest(game_class=name):
                self.assertIn("mass", assigned)

    def test_every_mass_reproduces_from_the_calibration(self) -> None:
        for binding in self.bindings:
            with self.subTest(game_class=binding.game_class):
                self.assertIsNotNone(binding.mass)
                assigned = self.assigned[binding.game_class]["mass"]
                self.assertAlmostEqual(
                    float(assigned),
                    binding.mass,
                    places=self.calibration.round_to,
                )

    def test_no_mass_copies_a_recorded_engine_mass(self) -> None:
        # The engine mass is recorded in the calibration for the fit only. The
        # emitted mass must never equal it: it is a calibrated scale of a held
        # real mass, not a copied engine number.
        for row in _calibration_payload()["rows"]:
            assigned = float(self.assigned[row["game_class"]]["mass"])
            with self.subTest(game_class=row["game_class"]):
                self.assertNotEqual(assigned, float(row["engine_mass_config"]))
                self.assertNotEqual(assigned, float(row["engine_mass_live"]))

    def test_every_class_states_its_parent(self) -> None:
        for name, entry in self.bodies.items():
            with self.subTest(game_class=name):
                self.assertTrue(entry["parent"])
        self.assertEqual(BARE_RE.findall(self.rendered), [])

    def test_every_parent_is_forward_declared_once(self) -> None:
        for name, entry in self.bodies.items():
            with self.subTest(game_class=name):
                self.assertEqual(self.forwards.count(entry["parent"]), 1)

    def test_the_two_keys_share_one_cfgvehicles_block(self) -> None:
        # The engine lint rejects a second CfgVehicles block in the same
        # addon, so the file must open exactly one.
        self.assertEqual(self.rendered.count("class CfgVehicles"), 1)

    def test_only_admitted_keys_are_emitted(self) -> None:
        for assigned in self.assigned.values():
            with self.subTest(keys=sorted(assigned)):
                self.assertLessEqual(set(assigned), {"maxSpeed", "mass"})
                self.assertEqual(set(assigned) & set(FORBIDDEN_KEYS), set())

    def test_a_class_with_both_values_carries_both_keys(self) -> None:
        # Every class with a held maxSpeed also carries a calibrated mass.
        for binding in self.bindings:
            if binding.max_speed is not None:
                with self.subTest(game_class=binding.game_class):
                    self.assertIn("maxSpeed", self.assigned[binding.game_class])
                    self.assertIn("mass", self.assigned[binding.game_class])

    def test_a_missing_parent_fails_closed(self) -> None:
        drop = self.bindings[0].game_class
        records = [
            record
            for record in json.loads(PARENTS.read_text(encoding="utf-8"))
            if record["game_class"] != drop
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "class_parents.json"
            _write(path, records)
            with self.assertRaises(ValueError):
                gen.build_class_bindings(CLASS_BINDINGS, VEHICLE, path, CALIBRATION)

    def test_a_missing_held_mass_fails_closed(self) -> None:
        payload = _calibration_payload()
        drop = payload["rows"][0]["game_class"]
        payload["rows"] = [row for row in payload["rows"] if row["game_class"] != drop]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mass_calibration.json"
            _write(path, payload)
            with self.assertRaises(ValueError):
                gen.build_class_bindings(CLASS_BINDINGS, VEHICLE, PARENTS, path)

    def test_an_unapproved_calibration_fails_closed(self) -> None:
        payload = _calibration_payload()
        payload["approved"] = False
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mass_calibration.json"
            _write(path, payload)
            with self.assertRaises(ValueError):
                gen.build_class_bindings(CLASS_BINDINGS, VEHICLE, PARENTS, path)

    def test_a_non_positive_scale_fails_closed(self) -> None:
        payload = _calibration_payload()
        payload["fit"]["scale"] = 0.0
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mass_calibration.json"
            _write(path, payload)
            with self.assertRaises(ValueError):
                gen.load_mass_calibration(path)


if __name__ == "__main__":
    unittest.main()
