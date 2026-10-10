#!/usr/bin/env python3
"""PhysX gated-surface proof and the production non-regression (Task 7).

The gated CfgVehicles surface is emitted at BUILD TIME only when the class
identity grade AND the held value grade are both ``documented``. Two families
use that one predicate:

  * the land carx/tankx/shipx surface from ``data/vehicle/class_bindings.json``
    and the held catalogue fields in ``LAND_SURFACE_FIELDS``;
  * the aircraft keys from ``data/aircraft/class_bindings.json``.

These tests prove three things:

  * POSITIVE: a documented land fixture emits every emittable carx/tankx/shipx
    key, including the shipx ``mass`` from the held ``displacement_kg``, and the
    projection validates.
  * POSITIVE: a documented aircraft fixture emits ``fuelCapacity``,
    ``fuelConsumptionRate``, ``mass`` and ``centerOfMass``, and the projection
    validates.
  * NON-REGRESSION: the production corpus carries zero documented identity, so
    the shipped ``CfgVehicles.hpp`` carries no gated key. It declares only the
    pre-existing ``maxSpeed`` and ``mass``.

Run: python3 -m unittest tools.tests.test_physx_gated_surface -v
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

VEHICLE = REPO / "data" / "vehicle"
AIRCRAFT = REPO / "data" / "aircraft"
GENERATED = REPO / "addons" / "vehicles" / "generated" / "CfgVehicles.hpp"
LEAD_DOC = REPO / "docs" / "wiki" / "research" / "class-identity-sources.md"

# One key assignment `        key = value;` inside a body.
KEY_RE = re.compile(r"^[ \t]+(\w+) = ", re.M)

# The keys the land gate can emit today: every LAND_SURFACE_FIELDS entry that
# names a held catalogue field. The text-unit keys are excluded because the
# projection validator admits a numeric held value only.
NUMERIC_LAND_FIELDS = {
    key: field
    for key, (field, unit) in gen.LAND_SURFACE_FIELDS.items()
    if field is not None and unit != "text"
}

# The four aircraft keys the gate can emit.
AIRCRAFT_KEYS = frozenset(
    {
        gen.AIRCRAFT_KEY,
        gen.AIRCRAFT_BURN_KEY,
        gen.AIRCRAFT_MASS_KEY,
        gen.AIRCRAFT_CG_KEY,
    }
)

# The pre-existing land keys. Neither is gated.
LAND_KEYS = frozenset({gen.KEY, gen.MASS_KEY})


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture_source() -> dict[str, object]:
    return {
        "source_id": "fixture_manual",
        "tier": 2,
        "type": "manual",
        "title": "FIXTURE ONLY tier-2 manual, not a held document",
        "identifier": "FIXTURE-GATED",
        "locator": "fixture only, no real locator",
        "published": "2026",
        "retrieved": "2026-10-10",
        "url": "",
        "licence": "fixture only",
        "primary_held": False,
        "sha256": "",
        "note": "FIXTURE ONLY, not a held document",
    }


def _land_corpus(root: Path, grade: str) -> Path:
    """Build a temp land corpus holding every numeric carx/tankx/shipx field.

    The fixture is not a real vehicle and traces to no held document. It drives
    the SAME build-time predicate and the SAME land surface mapping the
    production corpus uses.
    """
    _write(root / "class_map.json", [])
    _write(root / "sources.json", [_fixture_source()])
    values = {
        field: {
            "value": index + 1,
            "unit": gen.LAND_SURFACE_FIELDS[key][1],
            "source": "fixture_manual",
            "locator": "fixture only, no real locator",
            "state": "fixture only, no real configuration",
            "grade": grade,
        }
        for index, (key, field) in enumerate(sorted(NUMERIC_LAND_FIELDS.items()))
    }
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
                    "values": values,
                }
            ],
        },
    )
    path = root / "class_bindings.json"
    _write(
        path,
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
    return path


def _aircraft_corpus(root: Path, grade: str) -> tuple[Path, Path]:
    """Build a temp aircraft corpus with one documented sentinel binding."""
    _write(root / "class_map.json", [])
    _write(root / "sources.json", [_fixture_source()])
    _write(
        root / "class_bindings.json",
        [
            {
                "game_class": "FIXTURE_SENTINEL_F",
                "class_token": "Helicopter",
                "catalogue_id": "fixture_sentinel",
                "identity_source": "fixture_manual",
                "identity_evidence": "FIXTURE ONLY, no real identity",
                "grade": grade,
            }
        ],
    )
    _write(
        root / "catalogue" / "fixture_sentinel.json",
        {
            "retrieved": "2026-10-10",
            "note": "FIXTURE ONLY, no real aircraft value",
            "sources": [],
            "entries": [
                {
                    "catalogue_id": "fixture_sentinel",
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
                        gen.AIRCRAFT_VALUE_FIELD: {
                            "value": 1234,
                            "unit": gen.AIRCRAFT_KEY_UNIT,
                            "source": "fixture_manual",
                            "locator": "fixture only, no real locator",
                            "state": "fixture only, no real configuration",
                            "grade": grade,
                        },
                        gen.AIRCRAFT_MASS_VALUE_FIELD: {
                            "value": 2345,
                            "unit": gen.AIRCRAFT_MASS_UNIT,
                            "source": "fixture_manual",
                            "locator": "fixture only, no real locator",
                            "state": "fixture only, no real configuration",
                            "grade": grade,
                        },
                        gen.AIRCRAFT_CG_VALUE_FIELD: {
                            "value": 1.25,
                            "unit": gen.AIRCRAFT_CG_UNIT,
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
    parents = root / "class_parents.json"
    _write(
        parents,
        [
            {
                "game_class": "FIXTURE_SENTINEL_F",
                "parent_class": "Heli_Base",
                "source_kind": "fixture",
                "source_locator": "fixture only, no real locator",
            }
        ],
    )
    return root / "class_bindings.json", parents


class LandGatedSurfaceTest(unittest.TestCase):
    """The land carx/tankx/shipx keys emit under documented grades only."""

    def test_a_documented_fixture_emits_every_numeric_land_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = _land_corpus(root, "documented")
            surface = gen.build_land_surface(class_bindings, root)
        emitted = {emission.key for group in surface.values() for emission in group}
        self.assertEqual(emitted, set(NUMERIC_LAND_FIELDS))
        # The shipx mass key is admitted from the held displacement_kg.
        self.assertIn("mass", emitted)
        self.assertLessEqual(emitted, v.CONFIG_KEYS)

    def test_a_claimed_fixture_emits_no_land_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = _land_corpus(root, "claimed")
            surface = gen.build_land_surface(class_bindings, root)
        self.assertEqual(surface, {})

    def test_a_documented_fixture_projection_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings = _land_corpus(root, "documented")
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


class AircraftGatedSurfaceTest(unittest.TestCase):
    """The four aircraft keys emit under documented grades only."""

    def test_a_documented_fixture_emits_the_aircraft_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _aircraft_corpus(root, "documented")
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
        self.assertEqual(leads, [])
        self.assertEqual(len(emissions), 1)
        emitted = gen.aircraft_projection_records(emissions)
        keys = {record["key"] for record in emitted}
        self.assertEqual(keys, set(AIRCRAFT_KEYS))
        burn = next(r for r in emitted if r["key"] == gen.AIRCRAFT_BURN_KEY)
        self.assertEqual(burn["value"], gen.AIRCRAFT_BURN_VALUE)

    def test_a_claimed_fixture_emits_no_aircraft_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _aircraft_corpus(root, "claimed")
            emissions, leads = gen.build_aircraft_emissions(
                class_bindings, root, parents
            )
        self.assertEqual(emissions, [])
        self.assertEqual(leads, ["FIXTURE_SENTINEL_F"])

    def test_a_documented_fixture_projection_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            class_bindings, parents = _aircraft_corpus(root, "documented")
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
        self.assertEqual(
            v.validate_bindings(records, catalogue_ids, class_map, sources), []
        )


class ProductionShipsNoGatedKeyTest(unittest.TestCase):
    """Non-regression: production carries zero documented identity.

    While every class identity stays ``claimed``, the build-time gate emits no
    gated key. The shipped override declares only the pre-existing ``maxSpeed``
    and ``mass``.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.land = gen.load_class_bindings(VEHICLE / "class_bindings.json")
        cls.aircraft = gen.load_class_bindings(AIRCRAFT / "class_bindings.json")
        cls.text = GENERATED.read_text(encoding="utf-8")

    def test_every_land_identity_is_claimed(self) -> None:
        grades = {record.get("grade") for record in self.land}
        self.assertEqual(grades, {"claimed"})

    def test_every_aircraft_identity_is_claimed(self) -> None:
        grades = {record.get("grade") for record in self.aircraft}
        self.assertEqual(grades, {"claimed"})

    def test_the_production_land_surface_is_empty(self) -> None:
        self.assertEqual(
            gen.build_land_surface(VEHICLE / "class_bindings.json", VEHICLE), {}
        )

    def test_the_production_aircraft_emissions_are_empty(self) -> None:
        emissions, leads = gen.build_aircraft_emissions(
            AIRCRAFT / "class_bindings.json",
            AIRCRAFT,
            AIRCRAFT / "class_parents.json",
        )
        self.assertEqual(emissions, [])
        self.assertTrue(leads)

    def test_the_shipped_override_declares_no_gated_key(self) -> None:
        assigned = set(KEY_RE.findall(self.text))
        # The grandfathered land pair only. ``mass`` is the pre-existing land
        # key, so it ships; the gated land shipx mass reuses the same key name
        # and cannot be told apart by name, so it is proven through the empty
        # land-surface projection above.
        self.assertEqual(assigned, set(LAND_KEYS))
        gated = (set(AIRCRAFT_KEYS) | set(NUMERIC_LAND_FIELDS)) - set(LAND_KEYS)
        self.assertEqual(assigned & gated, set())


class IdentityLeadDocTest(unittest.TestCase):
    """The identity lead doc records why every class link stays claimed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = LEAD_DOC.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()

    def test_the_doc_names_the_lead(self) -> None:
        self.assertIn("lead", self.lower)

    def test_the_doc_states_the_class_link_is_claimed(self) -> None:
        self.assertIn("claimed", self.lower)

    def test_the_doc_names_the_engine_class_table_source(self) -> None:
        self.assertIn("aee_class_table", self.lower)

    def test_the_doc_names_every_ground_token(self) -> None:
        for token in ("Car", "Truck", "Tracked_APC", "MRAP", "Tank", "Wheeled_APC"):
            with self.subTest(token=token):
                self.assertIn(token.lower(), self.lower)


if __name__ == "__main__":
    unittest.main()
