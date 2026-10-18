#!/usr/bin/env python3
"""Aircraft systems config gate tests (tasks 6 and 20).

The aircraft keys are projected into the one ``CfgVehicles`` block by
``tools/validation/gen_physics_config.py``. The build-time predicate admits a
HELD key only when the class identity grade AND the held value grade are both
``documented``. The ``fuelConsumptionRate`` structural zero is not a held key:
no grade gates it, and it ships for exactly the classes the fuel driver burns,
identified by the two guards ``fnc_updateFuelSystem`` applies (a positive
systems-row ``fuel_capacity`` and ``fuel_density_kg_l``).

These tests prove:

  * POSITIVE: a sentinel class with a ``documented`` identity and a
    ``documented`` held ``fuel_capacity`` emits ``fuelCapacity`` beside the
    land keys in the same block, and the value equals the catalogue value.
  * POSITIVE: the same class emits ``mass`` from the held
    ``operating_weight_kg`` as the PhysX mass and ``centerOfMass`` from the
    held ``cg_empty_m``.
  * POSITIVE: a driver-covered class at grade ``claimed`` emits no held key and
    still emits the structural zero, because the zero has no held value for a
    grade to gate.
  * NEGATIVE: a class the fuel driver does not burn emits no structural zero,
    so the engine's own burn stays on for a class the script does not burn.
  * NEGATIVE: no moment-of-inertia key is emitted, because the engine has no
    runtime inertia hook.
  * NEGATIVE: a class the driver does not burn at grade ``claimed`` emits no
    key at all and is recorded as a lead.
  * NON-REGRESSION: the shipped ``addons/vehicles/generated/CfgVehicles.hpp``
    still carries one block, one land body per bound class and the keys
    ``maxSpeed``, ``mass`` and the structural zero, and no held aircraft key.

Run: python3 -m unittest tools.tests.test_aircraft_systems -v
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
from tools.validation import validate_physics_config as v  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

GENERATED = REPO / "addons" / "vehicles" / "generated" / "CfgVehicles.hpp"
VEHICLE = REPO / "data" / "vehicle"
AIRCRAFT = REPO / "data" / "aircraft"

# One `class CfgVehicles {` opener at column zero.
BLOCK_RE = re.compile(r"^class CfgVehicles \{$", re.M)

# One emitted child body `class X: Parent {` and its parent.
BODY_RE = re.compile(r"^[ \t]+class (\w+): (\w+) \{$", re.M)

# One emitted key assignment `        key = value;`.
KEY_RE = re.compile(r"^[ \t]+(\w+) = ", re.M)

# The sentinel fixture. It is not a real aircraft and must never ship.
SENTINEL_CLASS = "FIXTURE_SENTINEL_F"
SENTINEL_PARENT = "Heli_Base"
SENTINEL_VALUE = 1234
SENTINEL_MASS_KG = 2345
SENTINEL_CG_M = 1.25
SENTINEL_ID = "fixture_sentinel"
SENTINEL_FUEL_TYPE = "jet_a"

# The land corpus is un-gated. The shipped file carries one body per bound
# class; the grandfathered 18 are the floor and their bodies stay byte-identical
# (tools/tests/test_mass_config.py pins them).
LAND_BODY_COUNT = 18
LAND_KEYS = {"maxSpeed", "mass"}


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sentinel_corpus(
    root: Path, grade: str, *, covered: bool = True
) -> tuple[Path, Path]:
    """Build a temp aircraft corpus with one sentinel binding.

    The binding identity grade is ``grade`` and the held value grades are the
    same, so ``grade`` drives both sides of the build-time predicate. The
    corpus holds no real aircraft value and no held document.

    ``covered`` selects whether the fuel driver burns the sentinel. The driver
    refuses a class unless the runtime systems row carries a positive
    ``fuel_capacity`` AND a positive ``fuel_density_kg_l``. The capacity is
    always held here; the density is a named derivation over the held
    ``fuel_type``, so omitting ``fuel_type`` removes the second guard and the
    driver refuses the class.
    """
    _write(
        root / "sources.json",
        [
            {
                "source_id": "fixture_manual",
                "tier": 2,
                "type": "manual",
                "title": "FIXTURE ONLY tier-2 manual, not a held document",
                "identifier": "FIXTURE-SENTINEL",
                "locator": "fixture only, no real locator",
                "published": "2026",
                "retrieved": "2026-10-09",
                "url": "",
                "licence": "fixture only",
                "primary_held": False,
                "sha256": "",
                "note": "FIXTURE ONLY, not a held document",
            }
        ],
    )
    _write(root / "class_map.json", [])
    _write(
        root / "class_bindings.json",
        [
            {
                "game_class": SENTINEL_CLASS,
                "class_token": "Helicopter",
                "catalogue_id": SENTINEL_ID,
                "identity_source": "fixture_manual",
                "identity_evidence": "FIXTURE ONLY, no real identity",
                "grade": grade,
            }
        ],
    )
    entry = {
        "catalogue_id": SENTINEL_ID,
        "canonical_name": "FIXTURE",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "variant_id": "fixture_sentinel_variant",
        "vehicle_type": "rotary_wing",
        "propulsion": "turboshaft",
        "role": "transport",
        "class_token": "Helicopter",
        "country": "NONE",
        "era": "none",
        "aliases": [],
        "keywords": [],
        "runtime_ready": False,
        "values": {
            "fuel_capacity": {
                "value": SENTINEL_VALUE,
                "unit": "L",
                "source": "fixture_manual",
                "locator": "fixture only, no real locator",
                "state": "fixture only, no real configuration",
                "grade": grade,
            },
            "operating_weight_kg": {
                "value": SENTINEL_MASS_KG,
                "unit": "kg",
                "source": "fixture_manual",
                "locator": "fixture only, no real locator",
                "state": "fixture only, no real configuration",
                "grade": grade,
            },
            "cg_empty_m": {
                "value": SENTINEL_CG_M,
                "unit": "m",
                "source": "fixture_manual",
                "locator": "fixture only, no real locator",
                "state": "fixture only, no real configuration",
                "grade": grade,
            },
        },
    }
    if covered:
        # The systems row derives fuel_density_kg_l from the held fuel type, so
        # the sentinel carries one of the repo's own standard fuel tokens. No
        # physical figure is invented: the profile derives the density.
        entry["values"]["fuel_type"] = {
            "value": SENTINEL_FUEL_TYPE,
            "unit": "enum",
            "source": "fixture_manual",
            "locator": "fixture only, no real locator",
            "state": "fixture only, no real configuration",
            "grade": grade,
        }
    _write(
        root / "catalogue" / f"{SENTINEL_ID}.json",
        {
            "retrieved": "2026-10-09",
            "note": "FIXTURE ONLY, no real aircraft value",
            "sources": [],
            "entries": [entry],
        },
    )
    parents = root / "class_parents.json"
    _write(
        parents,
        [
            {
                "game_class": SENTINEL_CLASS,
                "parent_class": SENTINEL_PARENT,
                "source_kind": "fixture",
                "source_locator": "fixture only, no real locator",
            }
        ],
    )
    return root / "class_bindings.json", parents


def _generate(root: Path, class_bindings: Path, parents: Path) -> str:
    """Run the generator to a temp out file and return its text."""
    out = root / "out" / "CfgVehicles.hpp"
    projection = root / "out" / "config_bindings.json"
    code = gen.main(
        [
            "--aircraft-class-bindings",
            str(class_bindings),
            "--aircraft-dir",
            str(root),
            "--aircraft-parents",
            str(parents),
            "--out",
            str(out),
            "--projection",
            str(projection),
        ]
    )
    if code != 0:
        raise AssertionError(f"the generator returned {code}")
    return out.read_text(encoding="utf-8")


class AircraftFuelEmissionTest(unittest.TestCase):
    """The build-time gate admits the aircraft fuel key by grade."""

    def test_a_documented_sentinel_emits_the_fuel_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "documented")
            text = _generate(root, class_bindings, parents)
        self.assertEqual(len(BLOCK_RE.findall(text)), 1)
        self.assertIn((SENTINEL_CLASS, SENTINEL_PARENT), BODY_RE.findall(text))
        body = re.search(
            rf"class {SENTINEL_CLASS}: {SENTINEL_PARENT} \{{(.*?)\n    \}};",
            text,
            re.S,
        )
        self.assertIsNotNone(body)
        assert body is not None
        self.assertIn(f"fuelCapacity = {SENTINEL_VALUE};", body.group(1))
        # The zero burn disables the engine's own burn, so the scripted burn
        # from the sourced systems row is authoritative and never double-counts.
        self.assertIn("fuelConsumptionRate = 0;", body.group(1))

    def test_a_documented_sentinel_value_equals_the_catalogue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "documented")
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
        self.assertEqual(
            [emission.game_class for emission in emissions], [SENTINEL_CLASS]
        )
        self.assertEqual(emissions[0].value, SENTINEL_VALUE)
        self.assertEqual(emissions[0].parent_class, SENTINEL_PARENT)
        self.assertEqual(emissions[0].unit, "L")
        self.assertEqual(emissions[0].mass, SENTINEL_MASS_KG)
        self.assertEqual(emissions[0].cg, SENTINEL_CG_M)
        self.assertEqual(leads, [])

    def test_a_documented_sentinel_emits_the_mass_and_cg_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "documented")
            text = _generate(root, class_bindings, parents)
        body = re.search(
            rf"class {SENTINEL_CLASS}: {SENTINEL_PARENT} \{{(.*?)\n    \}};",
            text,
            re.S,
        )
        self.assertIsNotNone(body)
        assert body is not None
        # CfgVehicles mass is the PhysX mass from the sourced operating
        # weight, and the centre of gravity is the sourced empty CG.
        self.assertIn(f"mass = {SENTINEL_MASS_KG};", body.group(1))
        self.assertIn(f"centerOfMass = {SENTINEL_CG_M};", body.group(1))

    def test_no_inertia_key_is_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "documented")
            text = _generate(root, class_bindings, parents)
        # The engine has no runtime inertia hook, so no moment-of-inertia key
        # is emitted. The header names the ceiling in prose, so test the
        # emitted assignment form, not the raw string.
        self.assertIsNone(re.search(r"^\s+inertia", text, re.M | re.I))

    def test_a_claimed_covered_sentinel_emits_only_the_structural_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "claimed")
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
            text = _generate(root, class_bindings, parents)
        # The held keys are gated on the grade, so a claimed class emits none
        # of them. The zero is not a held key: the driver burns this class, so
        # the zero ships and the scripted burn is the only burn.
        self.assertEqual(leads, [])
        self.assertEqual(
            [emission.game_class for emission in emissions], [SENTINEL_CLASS]
        )
        self.assertIsNone(emissions[0].value)
        self.assertTrue(emissions[0].burn)
        body = re.search(
            rf"class {SENTINEL_CLASS}: {SENTINEL_PARENT} \{{(.*?)\n    \}};",
            text,
            re.S,
        )
        self.assertIsNotNone(body)
        assert body is not None
        self.assertIn("fuelConsumptionRate = 0;", body.group(1))
        self.assertNotIn(f"{gen.AIRCRAFT_KEY} = ", body.group(1))
        self.assertNotIn(f"{gen.AIRCRAFT_MASS_KEY} = ", body.group(1))
        self.assertNotIn(f"{gen.AIRCRAFT_CG_KEY} = ", body.group(1))
        self.assertIsNone(re.search(r"^\s+fuelCapacity = ", text, re.M))

    def test_a_claimed_covered_sentinel_projects_only_the_structural_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "claimed")
            emissions, _leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
            records = gen.aircraft_projection_records(emissions)
            catalogue_ids = v.catalogue_by_id(VEHICLE)
            catalogue_ids.update(
                v.catalogue_by_id(root, profile=v.catalogue.AIRCRAFT_PROFILE)
            )
            class_map = v.class_binding_map(VEHICLE)
            class_map.update(v.class_binding_map(root))
            sources = v.sources_by_id(VEHICLE)
            sources.update(v.sources_by_id(root))
            errors = v.validate_bindings(records, catalogue_ids, class_map, sources)
        # The zero has no held value, so it traces to the held fuel_capacity
        # that qualifies the class and it carries the derived grade.
        self.assertEqual([record["key"] for record in records], ["fuelConsumptionRate"])
        burn = records[0]
        self.assertEqual(burn["value"], 0)
        self.assertEqual(burn["unit"], "unitless")
        self.assertEqual(burn["conversion"], "structural_zero")
        self.assertEqual(burn["grade"], "derived")
        self.assertEqual(burn["value_source"]["field"], "fuel_capacity")
        self.assertEqual(errors, [])

    def test_a_class_the_driver_does_not_burn_emits_no_structural_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(
                root, "documented", covered=False
            )
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
            text = _generate(root, class_bindings, parents)
        # The driver refuses a class with no positive fuel density, so the
        # scripted burn never runs and the engine's own burn must stay on. The
        # held capacity is documented, so fuelCapacity still ships.
        self.assertEqual(leads, [])
        self.assertFalse(emissions[0].burn)
        body = re.search(
            rf"class {SENTINEL_CLASS}: {SENTINEL_PARENT} \{{(.*?)\n    \}};",
            text,
            re.S,
        )
        self.assertIsNotNone(body)
        assert body is not None
        self.assertIn(f"fuelCapacity = {SENTINEL_VALUE};", body.group(1))
        self.assertNotIn(f"{gen.AIRCRAFT_BURN_KEY} = ", body.group(1))
        self.assertIsNone(re.search(r"^\s+fuelConsumptionRate = ", text, re.M))

    def test_a_claimed_uncovered_sentinel_emits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "claimed", covered=False)
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
            text = _generate(root, class_bindings, parents)
        self.assertEqual(emissions, [])
        self.assertEqual(leads, [SENTINEL_CLASS])
        self.assertNotIn(SENTINEL_CLASS, text)
        # No emitted assignment for any aircraft key. The header comment names
        # the keys, so test the emitted assignment form, not the string.
        self.assertIsNone(re.search(r"^\s+fuelCapacity = ", text, re.M))
        self.assertIsNone(re.search(r"^\s+fuelConsumptionRate = ", text, re.M))
        self.assertIsNone(re.search(r"^\s+centerOfMass = ", text, re.M))

    def test_a_documented_sentinel_projects_the_aircraft_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _sentinel_corpus(root, "documented")
            emissions, _leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
            records = gen.aircraft_projection_records(emissions)
            catalogue_ids = v.catalogue_by_id(VEHICLE)
            catalogue_ids.update(
                v.catalogue_by_id(root, profile=v.catalogue.AIRCRAFT_PROFILE)
            )
            class_map = v.class_binding_map(VEHICLE)
            class_map.update(v.class_binding_map(root))
            sources = v.sources_by_id(VEHICLE)
            sources.update(v.sources_by_id(root))
            errors = v.validate_bindings(records, catalogue_ids, class_map, sources)
        keys = {record["key"] for record in records}
        self.assertEqual(
            keys, {"fuelCapacity", "fuelConsumptionRate", "mass", "centerOfMass"}
        )
        burn = next(r for r in records if r["key"] == "fuelConsumptionRate")
        self.assertEqual(burn["value"], 0)
        self.assertEqual(burn["unit"], "unitless")
        self.assertEqual(burn["conversion"], "structural_zero")
        mass = next(r for r in records if r["key"] == "mass")
        self.assertEqual(mass["value"], SENTINEL_MASS_KG)
        self.assertEqual(mass["unit"], "kg")
        self.assertEqual(mass["conversion"], "identity")
        cg = next(r for r in records if r["key"] == "centerOfMass")
        self.assertEqual(cg["value"], SENTINEL_CG_M)
        self.assertEqual(cg["unit"], "m")
        self.assertEqual(errors, [])

    def test_the_predicate_admits_both_documented_only(self) -> None:
        self.assertTrue(gen.emit_key("documented", "documented"))
        self.assertFalse(gen.emit_key("claimed", "documented"))
        self.assertFalse(gen.emit_key("documented", "claimed"))
        self.assertFalse(gen.emit_key(None, "documented"))
        self.assertFalse(gen.emit_key("documented", None))


class ShippedConfigRegressionTest(unittest.TestCase):
    """The shipped override carries the land bodies and the structural zero.

    Every aircraft identity is ``claimed``, so no held aircraft key ships. The
    structural zero is not a held key: it ships for exactly the classes the
    fuel driver burns and a resolved parent can reopen.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = GENERATED.read_text(encoding="utf-8")
        cls.emissions, cls.leads = gen.build_aircraft_emissions(
            AIRCRAFT / "class_bindings.json",
            AIRCRAFT,
            AIRCRAFT / "class_parents.json",
        )
        cls.aircraft_bodies = {emission.game_class for emission in cls.emissions}

    def test_one_cfgvehicles_block(self) -> None:
        self.assertEqual(len(BLOCK_RE.findall(self.text)), 1)

    def test_class_bodies(self) -> None:
        # One land body per bound class plus one body per driver-covered
        # aircraft class. The count grows with the land-coverage binding set;
        # the grandfathered bodies stay byte-identical.
        bindings = json.loads(
            (VEHICLE / "class_bindings.json").read_text(encoding="utf-8")
        )
        bodies = BODY_RE.findall(self.text)
        self.assertGreaterEqual(len(bodies), LAND_BODY_COUNT)
        self.assertEqual(len(bodies), len(bindings) + len(self.aircraft_bodies))

    def test_the_key_set_is_the_land_pair_and_the_structural_zero(self) -> None:
        self.assertEqual(
            set(KEY_RE.findall(self.text)), LAND_KEYS | {gen.AIRCRAFT_BURN_KEY}
        )

    def test_no_held_aircraft_key_is_shipped(self) -> None:
        # Every aircraft identity is claimed, so the grade gate emits no held
        # aircraft key. The structural zero is not a held key. The header
        # comment names the keys, so test the emitted assignment form.
        self.assertIsNone(re.search(r"^\s+fuelCapacity = ", self.text, re.M))
        self.assertIsNone(re.search(r"^\s+centerOfMass = ", self.text, re.M))
        self.assertIsNone(re.search(r"^\s+emptyMass = ", self.text, re.M))
        self.assertNotIn("fuelCapacity =", self.text)

    def test_the_structural_zero_ships_for_every_covered_emittable_class(
        self,
    ) -> None:
        # The covered set is the classes the fuel driver burns; a resolved
        # parent is required to reopen one. The two sets must agree exactly, so
        # a covered class either carries the zero or is recorded as a lead.
        covered = {emission.game_class for emission in self.emissions if emission.burn}
        self.assertEqual(covered, self.aircraft_bodies)
        for game_class in sorted(covered):
            with self.subTest(game_class=game_class):
                body = re.search(
                    rf"class {game_class}: \w+ \{{(.*?)\n    \}};", self.text, re.S
                )
                self.assertIsNotNone(body)
                assert body is not None
                self.assertIn(f"{gen.AIRCRAFT_BURN_KEY} = 0;", body.group(1))

    def test_a_covered_class_with_no_parent_keeps_the_double_count(self) -> None:
        # The covered set is a corpus fact, not a gate pass. A covered class
        # with no resolved parent cannot be reopened, so it emits nothing and
        # is recorded as a lead rather than failing the build.
        parents = gen.load_aircraft_parents(AIRCRAFT / "class_parents.json")
        entries = {
            entry.catalogue_id: entry
            for entry in catalogue.load(
                AIRCRAFT, profile=catalogue.AIRCRAFT_PROFILE
            ).entries
        }
        covered_without_parent = []
        for record in gen.load_class_bindings(AIRCRAFT / "class_bindings.json"):
            game_class = str(record.get("game_class"))
            entry = entries.get(str(record.get("catalogue_id")))
            if game_class in parents:
                continue
            capacity = gen._gated_value(
                entry, gen.AIRCRAFT_VALUE_FIELD, gen.AIRCRAFT_KEY_UNIT, game_class
            )
            if gen._driver_covers(entry, capacity):
                covered_without_parent.append(game_class)
        self.assertTrue(covered_without_parent)
        for game_class in covered_without_parent:
            with self.subTest(game_class=game_class):
                self.assertIn(game_class, self.leads)
                self.assertNotIn(f"class {game_class}:", self.text)


if __name__ == "__main__":
    unittest.main()
