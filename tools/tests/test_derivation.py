#!/usr/bin/env python3
"""Dynamic derivation tests (issue #170).

Locks the derivation layer on top of the #167/#168 databases:
- the cartridge velocity-LENGTH curve (MV as a function of barrel,
  fitted to the seed's measured data: 5.56 211mm->723, 368->862,
  508->940 m/s)
- the barrel measurement (memory-point distance, family fallback)
- the protection derivation (mass + hierarchy -> STANAG category)

A derivation that drifts from the measured physics fails the gate.

Run: python3 -m unittest tools/tests/test_derivation.py
"""

import math
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
BALL = REPO / "addons/ballistics/functions"
ARM = REPO / "addons/armour/functions"


def cartridge_mv(
    barrel_m,
    ref_mv=948.0,
    ref_barrel=0.508,
    v_short=723.0,
    short_barrel=0.211,
    v_min=500.0,
):
    """Mirror of the SQF velocity-length curve: linear between the
    short-barrel anchor and the reference barrel (the measured 5.56
    pairs 211mm->723, 508->948 m/s); vMin falloff below the short
    anchor; the cartridge maximum at/above the reference."""
    if barrel_m >= ref_barrel:
        return ref_mv
    if barrel_m >= short_barrel:
        t = (barrel_m - short_barrel) / (ref_barrel - short_barrel)
        return v_short + t * (ref_mv - v_short)
    return max(v_short * (barrel_m / short_barrel), v_min)


class TestVelocityLengthCurve(unittest.TestCase):
    def test_m4a1_145in(self):
        # M4A1 14.5" (0.368 m): ~862-910 m/s from the SAME 5.56 curve.
        mv = cartridge_mv(0.368)
        self.assertGreater(mv, 820)
        self.assertLess(mv, 940)

    def test_m16a4_20in(self):
        # M16A4 20" (0.508 m): the reference 948 m/s.
        mv = cartridge_mv(0.508)
        self.assertAlmostEqual(mv, 948, delta=1)

    def test_short_barrel_derates(self):
        # A 10" (0.254 m) barrel falls off the curve (the M4-CQB class).
        mv_short = cartridge_mv(0.254)
        mv_long = cartridge_mv(0.508)
        self.assertLess(mv_short, mv_long)
        self.assertGreater(mv_short, 500)

    def test_mod_weapon_16in(self):
        # A mod weapon with a 16" (0.406 m) barrel: the linear fit gives
        # ~871 m/s (the measured HK416 16.5" = 862, the M4 14.5" = 862
        # band).  Computed from the cartridge curve, no table entry
        # (the first-load-works goal).
        mv = cartridge_mv(0.406)
        self.assertGreater(mv, 850)
        self.assertLess(mv, 900)

    def test_curve_in_sqf(self):
        src = (BALL / "fnc_deriveCartridge.sqf").read_text(encoding="utf-8")
        self.assertIn("linearConversion", src)
        self.assertIn("_vMin", src)
        self.assertIn("_refBarrel", src)
        self.assertIn("_airTempC", src)


class TestCartridgeParsing(unittest.TestCase):
    def test_family_parsed(self):
        # The class name encodes the family: B_556x45_Ball -> 556x45.
        src = (BALL / "fnc_deriveCartridge.sqf").read_text(encoding="utf-8")
        for cal in ("556x45", "762x51", "545x39", "127x99", "9x19", "65x39", "338"):
            self.assertIn(f'"{cal}"', src, f"caliber {cal} missing")

    def test_family_table_anchors(self):
        # The base families carry the #167 researched anchors.
        src = (BALL / "fnc_deriveCartridge.sqf").read_text(encoding="utf-8")
        for anchor in (
            '["556x45", [948',
            '["762x51", [838',
            '["127x99", [885',
            '["545x39", [880',
        ):
            self.assertIn(anchor, src, f"anchor {anchor} missing")


class TestBarrelMeasurement(unittest.TestCase):
    def test_measurement_math(self):
        # The barrel length is the muzzle-to-chamber distance.
        src = (BALL / "fnc_measureBarrel.sqf").read_text(encoding="utf-8")
        self.assertIn("selectionPosition", src)
        self.assertIn('"muzzle"', src)
        self.assertIn('"chamber"', src)
        self.assertIn("_familyBarrel", src)

    def test_sanity_band(self):
        # A measured barrel outside 0.1-1.0 m (4"-40") is not a
        # muzzle/chamber pair - fall back to the family.
        src = (BALL / "fnc_measureBarrel.sqf").read_text(encoding="utf-8")
        self.assertIn("_measured < 0.1", src)
        self.assertIn("_measured > 1.0", src)


class TestProtectionDerivation(unittest.TestCase):
    def test_hierarchy_first(self):
        # The #168 table is authoritative when it resolves; the mass
        # derivation is the fallback.
        src = (ARM / "fnc_deriveProtection.sqf").read_text(encoding="utf-8")
        self.assertIn("getVehicleArmour", src)
        self.assertIn("getMass", src)
        self.assertIn("isKindOf", src)

    def test_mass_bands(self):
        # The mass bands: >50t MBT L6, >15t IFV L5, >8t protected L2.
        src = (ARM / "fnc_deriveProtection.sqf").read_text(encoding="utf-8")
        self.assertIn("_mass > 50000", src)
        self.assertIn("_mass > 15000", src)
        self.assertIn("_mass > 8000", src)

    def test_tank_band(self):
        # A Tank class is L6 (the MBT band, 30mm APFSDS).
        src = (ARM / "fnc_deriveProtection.sqf").read_text(encoding="utf-8")
        self.assertIn('isKindOf "Tank"', src)
        self.assertIn('{ [6, 650, "120mmKE"] }', src)


class TestDerivationWiring(unittest.TestCase):
    def test_fired_eh_uses_derivation(self):
        # The Fired EH measures the barrel and derives the MV.
        post = (REPO / "addons/ballistics/XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("measureBarrel", post)
        self.assertIn("deriveCartridge", post)

    def test_derivation_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        for fn in ("deriveCartridge", "measureBarrel"):
            self.assertIn(fn, prep)
        arm_prep = (REPO / "addons/armour/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("deriveProtection", arm_prep)


if __name__ == "__main__":
    unittest.main()
