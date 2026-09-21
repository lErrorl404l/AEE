#!/usr/bin/env python3
"""Vehicle armour database tests (issue #168).

Locks the researched STANAG 4569 Ed 2 protection levels in
fnc_getVehicleArmour.sqf against the issue #168 vehicle armour table
(vehicle brochures, Janes, army manuals, the ABE ir_armor seed).  A
level that drifts from the real protection fails the gate.

STANAG 4569 Ed 2 ladder (the researched mapping):
  L1: 5.56/7.62 ball   L2: 7.62x39 API   L3: 7.62x54R AP (B32)
  L4: 14.5x114 AP      L5: 25mm APDS     L6: 30mm APFSDS

Run: python3 -m unittest tools/tests/test_armour_database.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (REPO / "addons/armour/functions/fnc_getVehicleArmour.sqf").read_text(
    encoding="utf-8"
)


class TestStanagLadder(unittest.TestCase):
    def test_ladder_documented(self):
        # The STANAG 4569 Ed 2 ladder must be in the function header.
        for anchor in (
            "Level 1",
            "Level 2",
            "Level 3",
            "Level 4",
            "Level 5",
            "Level 6",
        ):
            self.assertIn(anchor, FNC)
        for munition in (
            "5.56/7.62 ball",
            "7.62x39 API",
            "7.62x54R AP",
            "14.5x114 AP",
            "25mm APDS",
            "30mm APFSDS",
        ):
            self.assertIn(munition, FNC)

    def test_truck_unarmoured(self):
        # Soft-skin trucks: no protection (L0).
        self.assertIn('{ [0, 5, "7.62ball"] }', FNC)
        self.assertIn('_v find "truck" >= 0', FNC)

    def test_mrap_level2(self):
        # MRAP/JLTV: STANAG 4569 L2 (7.62x39 API).
        self.assertIn('{ [2, 20, "7.62API"] }', FNC)
        self.assertIn('_v find "mrap" >= 0', FNC)

    def test_wheeled_apc_level4(self):
        # Stryker/BTR-82A: L4 (14.5x114 AP).
        self.assertIn('{ [4, 60, "14.5mm"] }', FNC)
        self.assertIn('_v find "apc_wheeled" >= 0', FNC)

    def test_ifv_level5(self):
        # Bradley/BMP-3: L5 (25mm APDS).
        self.assertIn('{ [5, 120, "25mm"] }', FNC)
        self.assertIn('_v find "ifv" >= 0', FNC)

    def test_mbt_level6(self):
        # Abrams/Leopard 2: L6 (30mm APFSDS / KE).
        self.assertIn('{ [6, 650, "120mmKE"] }', FNC)
        self.assertIn('_v find "mbt" >= 0', FNC)

    def test_uses_cfgVehicles_classname(self):
        # Reads the vehicle's classname (the dynamic signal).
        self.assertIn("typeOf _vehicle", FNC)
        self.assertIn("toLower", FNC)

    def test_registered(self):
        prep = (REPO / "addons/armour/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("getVehicleArmour", prep)


if __name__ == "__main__":
    unittest.main()
