"""Test for the PhysX mass-surface ceiling document (Task 5).

The document must name the three out-of-reach surfaces (character, terrain,
flight model) and cite a file:line for every reachable surface.
"""

from __future__ import annotations

import unittest
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "wiki" / "research" / "physx-mass-surface.md"


class TestPhysxMassSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DOC.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()

    def test_names_the_character_controller(self) -> None:
        self.assertIn("character controller", self.lower)

    def test_names_terrain(self) -> None:
        self.assertIn("terrain", self.lower)

    def test_names_the_flight_model(self) -> None:
        self.assertIn("flight model", self.lower)

    def test_each_reachable_surface_cites_a_file_line(self) -> None:
        for surface, citation in (
            ("CfgMagazines >> mass", "fnc_calculateUnitLoadoutThermal.sqf:70"),
            ("CfgVehicles >> mass", "fnc_applyRollover.sqf:144"),
            ("ItemInfo", "fnc_calculateUnitLoadoutThermal.sqf:48"),
            ("WeaponSlotsInfo", "fnc_calculateUnitLoadoutThermal.sqf:90"),
            ("carx", "gen_physics_config.py:184"),
        ):
            self.assertIn(surface, self.text, f"{surface} not named")
            self.assertIn(citation, self.text, f"{surface} cites no {citation}")

    def test_the_gated_surface_cites_the_gate(self) -> None:
        self.assertIn("gen_physics_config.py:399", self.text)
        self.assertIn("documented", self.lower)

    def test_out_of_reach_cites_a_source(self) -> None:
        self.assertIn("ADR-017-flight-physics-ceiling.md:15", self.text)
        self.assertIn("ADR-017-flight-physics-ceiling.md:29", self.text)

    def test_every_reachable_row_has_a_line_citation(self) -> None:
        rows = [
            line
            for line in self.text.splitlines()
            if line.startswith("|")
            and ">>" in line
            or line.startswith("| `CfgVehicles")
        ]
        self.assertTrue(rows, "no reachable surface rows found")
        for row in rows:
            self.assertRegex(row, r"\w[\w./-]*:\d+")


if __name__ == "__main__":
    unittest.main()
