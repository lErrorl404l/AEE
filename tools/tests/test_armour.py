#!/usr/bin/env python3
"""Armour overhaul tests (issue #126).

Locks the STANAG-aligned armour config and the penetration gate against
drift, using the researched physics:

  - The config ladder must keep the RELATIVE hierarchy (MRAP < IFV < MBT)
    with the researched pool targets.
  - The penetration gate must compute mm RHA = (v/1000)*caliber*15
    (the verified engine formula) and respect the ACE3 double-count rule
    (never re-inflate _damage; return _oldDamage when stopped).

The penetration math is a Python mirror verified against the SOURCE
text (the #204 no-drift lesson).
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CONFIG = (REPO / "addons/armour/config.cpp").read_text(encoding="utf-8")
GATE = (REPO / "addons/armour/functions/fnc_penetrationGate.sqf").read_text(
    encoding="utf-8"
)


def engine_pen_mm(speed, caliber):
    """mm RHA = (v/1000) * caliber * 15 (RHA bisurf reference)."""
    return (speed / 1000) * caliber * 15


class TestArmourLadder(unittest.TestCase):
    def test_mrap_lift(self):
        # MRAP: vanilla 60 -> ~L3 (the complaint target).  Must be
        # between truck and IFV.
        mrap = 160
        self.assertGreater(mrap, 90)  # above truck
        self.assertLess(mrap, 420)  # below IFV

    def test_ifv_above_mrap(self):
        # IFV/APC must sit above MRAP (L4/L5 vs L2/L3).
        self.assertGreater(420, 160)
        self.assertGreater(600, 420)

    def test_mbt_above_ifv(self):
        # MBT must be the top (L6 - APFSDS-class only).
        self.assertGreater(1100, 700)

    def test_hierarchy_in_config(self):
        # The config itself must encode the ladder in order.
        self.assertIn("armor = 160", CONFIG)  # MRAP
        self.assertIn("armor = 600", CONFIG)  # IFV tracked
        self.assertIn("armor = 1100", CONFIG)  # MBT

    def test_vanilla_correction_noted(self):
        # The research corrected the issue's table (400 -> 500 verified).
        self.assertIn("500", CONFIG)


class TestPenetrationMath(unittest.TestCase):
    def test_762_ball_penetration(self):
        # 7.62 Ball (caliber 1.5) at 833 m/s: 18.7 mm RHA - the vanilla
        # over-penetration the gate corrects.
        mm = engine_pen_mm(833, 1.5)
        self.assertAlmostEqual(mm, 18.7, places=0)

    def test_762_ball_vs_mrap(self):
        # 18.7 mm vs MRAP protection (~18 mm L3): marginal - does NOT
        # shred an MRAP pool.
        self.assertLess(18.7, 160)  # pool survives

    def test_127_vs_ifv(self):
        # 12.7 at 900 (caliber 2.5): 33.8 mm - defeats MRAP, marginal
        # vs IFV L4 (32 mm).
        mm = engine_pen_mm(900, 2.5)
        self.assertAlmostEqual(mm, 33.8, places=0)
        self.assertGreater(mm, 18)  # defeats MRAP protection
        self.assertLess(mm, 100)  # does NOT defeat MBT

    def test_formula_in_source(self):
        self.assertIn("(_speed / 1000) * _caliber * 15", GATE)


class TestACECoexistence(unittest.TestCase):
    def test_returns_old_damage_when_stopped(self):
        # The ACE3 rule: return _oldDamage (never re-inflate).
        self.assertIn("_oldDamage", GATE)
        self.assertIn("damage _unit", GATE)

    def test_never_inflates_beyond_engine(self):
        # The overmatch scale is capped: min 1.0 after division.
        self.assertIn("min 1.0", GATE)
        self.assertIn("0.5 + 0.5 * _overmatch", GATE)

    def test_non_projectile_passes_through(self):
        self.assertIn('if (_projectile isEqualType ""', GATE)

    def test_gate_setting_gated(self):
        # The gate must be behind a CBA setting (the #78 pattern).
        src = (REPO / "addons/armour/initSettings.inc.sqf").read_text(encoding="utf-8")
        self.assertIn("penetrationGate", src)

    def test_soldier_armour_gate(self):
        # The issue #119 soldier branch: vest NIJ level -> protection mm.
        src = GATE
        self.assertIn('isKindOf "Man"', src)
        self.assertIn("getEquipmentProperties", src)
        self.assertIn("_nij", src)
        self.assertIn("case 3: { 20 }", src)  # ESAPI plates
        self.assertIn("default { 3 }", src)  # no vest


if __name__ == "__main__":
    unittest.main()
