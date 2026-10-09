#!/usr/bin/env python3
"""Physics config-binding gate tests.

The config-binding corpus binds one engine config key on one concrete game
class to one held catalogue value through a named conversion. The validator
is the gate. These tests prove a clean corpus passes, an invented value fails
and an unknown conversion fails. The good records come from the committed
corpus. The bad records are copies held in this test only.

The generator turns the class-binding corpus and the catalogue into a
CfgVehicles override and a validator projection. Each emitted class must
state its immediate real parent, the parent must be forward-declared once,
and no class may be reopened bare.

Run: python3 -m unittest tools.tests.test_physics_config -v
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_physics_config as gen  # noqa: E402
from tools.validation import validate_physics_config as v  # noqa: E402

DATA = REPO / "data" / "physics"
VEHICLE = REPO / "data" / "vehicle"
BINDINGS = DATA / "config_bindings.json"
CLASS_BINDINGS = VEHICLE / "class_bindings.json"
PARENTS = VEHICLE / "class_parents.json"
GENERATED = REPO / "addons" / "mobility" / "generated" / "CfgVehicles.hpp"


def _write(path: Path, payload: object) -> None:
    """Write one JSON artefact for the fixture corpus."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# One emitted child body: `class X: Parent {` and its maxSpeed value.
CHILD_RE = re.compile(
    r"^[ \t]+class (\w+): (\w+) \{\n[ \t]+maxSpeed = ([0-9.]+);", re.M
)

# A forward declaration `class X;` at class level.
FORWARD_RE = re.compile(r"^[ \t]+class (\w+);$", re.M)

# A bare class body `class X {` with no parent. None is allowed.
BARE_RE = re.compile(r"^[ \t]+class (\w+) \{\s*$", re.M)

# Keys thermal and optics already own. This addon loads last, so emitting any
# of them would silently win. The generator must never write one.
FORBIDDEN_KEYS = ("htMin", "htMax", "afMax", "mfMax", "mFact", "tBody")


def _corpus_set() -> dict[str, str]:
    """Return the corpus-driven class set with its value literals."""
    emissions = gen.build(CLASS_BINDINGS, VEHICLE, PARENTS)
    return {e.game_class: gen._render_value(e.value) for e in emissions}


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


class PhysicsConfigGeneratorTest(unittest.TestCase):
    """The generator emits the parent form, and only the corpus bindings."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = _corpus_set()
        cls.emissions = gen.build(CLASS_BINDINGS, VEHICLE, PARENTS)
        cls.rendered = GENERATED.read_text(encoding="utf-8")
        cls.children = dict(
            (name, value) for name, _parent, value in CHILD_RE.findall(cls.rendered)
        )
        cls.parent_of = {
            name: parent for name, parent, _value in CHILD_RE.findall(cls.rendered)
        }
        cls.forwards = FORWARD_RE.findall(cls.rendered)

    def test_the_committed_header_is_fresh(self) -> None:
        self.assertEqual(
            gen.check_config(CLASS_BINDINGS, VEHICLE, PARENTS, GENERATED, BINDINGS),
            0,
        )

    def test_the_committed_header_is_fresh_from_the_cli(self) -> None:
        self.assertEqual(gen.main(["--check"]), 0)

    def test_every_emitted_class_states_its_parent_and_value(self) -> None:
        self.assertEqual(self.children, self.corpus)

    def test_the_emitted_class_set_equals_the_corpus_set(self) -> None:
        self.assertEqual(set(self.children), set(self.corpus))
        self.assertEqual({e.game_class for e in self.emissions}, set(self.corpus))

    def test_every_parent_is_forward_declared_once(self) -> None:
        for name, parent in self.parent_of.items():
            with self.subTest(game_class=name):
                self.assertEqual(self.forwards.count(parent), 1)

    def test_no_bare_class_exists(self) -> None:
        # A body `class X { ... };` with no parent shadows the vanilla class
        # at run time. Every emitted body must state its parent.
        self.assertEqual(BARE_RE.findall(self.rendered), [])

    def test_only_admitted_keys_are_emitted(self) -> None:
        # The generator owns maxSpeed and mass. It must never emit a key that
        # thermal or optics own, because this addon loads last and a
        # redeclaration here would silently win.
        assignments = re.findall(r"^\s+(\w+) = ", self.rendered, re.M)
        self.assertEqual(set(assignments), {"maxSpeed", "mass"})
        self.assertEqual(set(assignments) & set(FORBIDDEN_KEYS), set())

    def test_the_projection_is_fresh(self) -> None:
        committed = BINDINGS.read_text(encoding="utf-8")
        self.assertEqual(committed, gen.render_projection(self.emissions))

    def test_the_projection_matches_the_emitted_set(self) -> None:
        records = json.loads(BINDINGS.read_text(encoding="utf-8"))
        self.assertEqual({record["game_class"] for record in records}, set(self.corpus))
        for record in records:
            self.assertIn(record["game_class"], self.children)

    def test_the_parents_cache_covers_every_bound_class(self) -> None:
        parents = gen.load_parents(PARENTS)
        self.assertEqual(set(parents), set(gen.bound_classes(CLASS_BINDINGS)))

    def test_a_missing_parent_fails_closed(self) -> None:
        # An emitted class with no resolved parent must stop the build rather
        # than emit a bare class.
        drop = self.emissions[0].game_class
        records = [
            record
            for record in json.loads(PARENTS.read_text(encoding="utf-8"))
            if record["game_class"] != drop
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "class_parents.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            with self.assertRaises(ValueError):
                gen.build(CLASS_BINDINGS, VEHICLE, path)

    def test_a_stale_header_fails_the_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "CfgVehicles.hpp"
            stale.write_text("class CfgVehicles {};\n", encoding="utf-8")
            self.assertEqual(
                gen.check_config(CLASS_BINDINGS, VEHICLE, PARENTS, stale, BINDINGS),
                1,
            )

    def test_a_missing_header_fails_the_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                gen.check_config(
                    CLASS_BINDINGS,
                    VEHICLE,
                    PARENTS,
                    Path(tmp) / "CfgVehicles.hpp",
                    BINDINGS,
                ),
                1,
            )

    def test_a_stale_projection_fails_the_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "config_bindings.json"
            stale.write_text("[]\n", encoding="utf-8")
            self.assertEqual(
                gen.check_config(CLASS_BINDINGS, VEHICLE, PARENTS, GENERATED, stale),
                1,
            )

    def test_a_non_array_class_binding_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "class_bindings.json"
            path.write_text(json.dumps({"game_class": "x"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                gen.load_class_bindings(path)


class LandSurfaceGateTest(unittest.TestCase):
    """The land surface key is admitted only on a documented binding.

    A fixture corpus drives the SAME build-time predicate the aircraft keys
    use. The fixture is not a real vehicle and must never ship.
    """

    def _fixture(self, root: Path, grade: str) -> Path:
        _write(
            root / "class_map.json",
            [],
        )
        _write(
            root / "sources.json",
            [
                {
                    "source_id": "fixture_manual",
                    "tier": 2,
                    "type": "manual",
                    "title": "FIXTURE ONLY tier-2 manual, not a held document",
                    "identifier": "FIXTURE-LAND",
                    "locator": "fixture only, no real locator",
                    "published": "2026",
                    "retrieved": "2026-10-10",
                    "url": "",
                    "licence": "fixture only",
                    "primary_held": False,
                    "sha256": "",
                    "note": "FIXTURE ONLY, not a held document",
                }
            ],
        )
        class_bindings = root / "class_bindings.json"
        _write(
            class_bindings,
            [
                {
                    "game_class": "FIXTURE_LAND_F",
                    "class_token": "Tank",
                    "catalogue_id": "fixture_land",
                    "identity_source": "fixture_manual",
                    "identity_evidence": "FIXTURE ONLY, no real identity",
                    "grade": grade,
                }
            ],
        )
        _write(
            root / "catalogue" / "fixture_land.json",
            {
                "retrieved": "2026-10-10",
                "note": "FIXTURE ONLY, no real vehicle value",
                "sources": [],
                "entries": [
                    {
                        "catalogue_id": "fixture_land",
                        "canonical_name": "FIXTURE",
                        "maker": "FIXTURE",
                        "model": "FIXTURE",
                        "variant": "FIXTURE",
                        "variant_id": "fixture_land_variant",
                        "vehicle_type": "tracked",
                        "class_token": "Tank",
                        "country": "NONE",
                        "era": "none",
                        "aliases": [],
                        "keywords": [],
                        "runtime_ready": False,
                        "values": {
                            "max_brake_torque_nm": {
                                "value": 54000,
                                "unit": "N m",
                                "source": "fixture_manual",
                                "locator": "fixture only, no real locator",
                                "state": "fixture only, no real configuration",
                                "grade": grade,
                            },
                            "max_hand_brake_torque_nm": {
                                "value": 12000,
                                "unit": "N m",
                                "source": "fixture_manual",
                                "locator": "fixture only, no real locator",
                                "state": "fixture only, no real configuration",
                                "grade": grade,
                            },
                        },
                    }
                ],
            },
        )
        return class_bindings

    def test_every_land_surface_key_is_admitted(self) -> None:
        self.assertEqual(set(gen.LAND_SURFACE_FIELDS) - v.CONFIG_KEYS, set())

    def test_every_land_surface_unit_matches_the_validator(self) -> None:
        for key, (_field, unit) in gen.LAND_SURFACE_FIELDS.items():
            with self.subTest(key=key):
                self.assertEqual(v.KEY_UNITS.get(key), unit)

    def test_a_documented_fixture_emits_admitted_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = self._fixture(root, "documented")
            surface = gen.build_land_surface(class_bindings, root)
        emitted = {emission.key for group in surface.values() for emission in group}
        self.assertTrue(emitted, "a documented fixture must emit a land key")
        self.assertLessEqual(emitted, v.CONFIG_KEYS)

    def test_a_claimed_fixture_emits_no_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = self._fixture(root, "claimed")
            surface = gen.build_land_surface(class_bindings, root)
        self.assertEqual(surface, {})

    def test_a_documented_fixture_projection_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = self._fixture(root, "documented")
            surface = gen.build_land_surface(class_bindings, root)
            records = gen.land_surface_projection_records(surface)
            self.assertTrue(records)
            catalogue_ids = v.catalogue_by_id(root)
            class_binding_map = v.class_binding_map(root)
            sources = v.sources_by_id(root)
        self.assertEqual(
            v.validate_bindings(records, catalogue_ids, class_binding_map, sources),
            [],
        )


if __name__ == "__main__":
    unittest.main()
