#!/usr/bin/env python3
"""Ship mass field and source-plan contract (Task 8).

The schema must name the two ship displacement states, each in kg. The
source plan must name the exact documents that publish a ship displacement
and their licence. The generator must hold the ship mass binding, gated so
it emits nothing while every identity is claimed.

Run: python3 -m unittest tools.tests.test_ship_mass_schema -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_physics_config as gen  # noqa: E402

SCHEMA = REPO / "data" / "vehicle" / "SCHEMA.md"
PLAN = REPO / "docs" / "wiki" / "research" / "ship-mass-source-plan.md"

# The documents the plan must name, and the licence it must state for each.
REQUIRED_DOCS = (
    "naval vessel register",
    "maritime administration",
    "technical manual",
    "wikipedia",
)
REQUIRED_LICENCES = (
    "public domain",
    "cc by-sa",
)


def _shipx_block(text: str) -> str:
    """Return the ShipX subsection up to the next heading."""
    start = text.find("### ShipX")
    if start == -1:
        return ""
    body = text[start:]
    end = body.find("\n###", len("### ShipX"))
    return body if end == -1 else body[:end]


class ShipMassSchemaTest(unittest.TestCase):
    """The schema names the ship mass states and the plan names the sources."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = SCHEMA.read_text(encoding="utf-8")
        cls.plan = PLAN.read_text(encoding="utf-8")
        cls.shipx = _shipx_block(cls.schema)

    def test_the_shipx_block_exists(self) -> None:
        self.assertTrue(self.shipx, "no ShipX block found in the schema")

    def test_the_schema_gains_the_light_ship_field(self) -> None:
        self.assertIn("`displacement_kg`", self.shipx)

    def test_the_schema_gains_the_full_load_field(self) -> None:
        self.assertIn("`full_load_displacement_kg`", self.shipx)

    def test_each_ship_field_names_the_unit_kg(self) -> None:
        for field in ("`displacement_kg`", "`full_load_displacement_kg`"):
            with self.subTest(field=field):
                row = next(
                    (
                        line
                        for line in self.shipx.splitlines()
                        if line.strip().startswith(f"| {field}")
                    ),
                    None,
                )
                self.assertIsNotNone(row, f"no row for {field}")
                self.assertIn("unit kg", row)

    def test_the_schema_names_the_two_states(self) -> None:
        self.assertIn("light ship", self.shipx.lower())
        self.assertIn("full load", self.shipx.lower())

    def test_the_generator_holds_the_ship_mass_key(self) -> None:
        self.assertEqual(gen.LAND_SURFACE_FIELDS.get("mass"), ("displacement_kg", "kg"))

    def test_the_generator_check_passes(self) -> None:
        self.assertEqual(gen.main(["--check"]), 0)

    def test_the_plan_names_the_documents(self) -> None:
        lowered = self.plan.lower()
        for doc in REQUIRED_DOCS:
            with self.subTest(document=doc):
                self.assertIn(doc, lowered)

    def test_the_plan_names_the_licences(self) -> None:
        lowered = self.plan.lower()
        for licence in REQUIRED_LICENCES:
            with self.subTest(licence=licence):
                self.assertIn(licence, lowered)

    def test_the_plan_states_no_displacement_is_held(self) -> None:
        lowered = self.plan.lower()
        self.assertIn("no displacement is held", lowered)

    def test_the_plan_records_the_lead(self) -> None:
        self.assertIn("lead", self.plan.lower())


if __name__ == "__main__":
    unittest.main()
