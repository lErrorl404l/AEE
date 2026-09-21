#!/usr/bin/env python3
"""Ammunition database tests (issue #167).

Locks the researched real-world ballistic values in
fnc_getAmmoProperties.sqf against the issue #167 ammunition table
(NATO EPVAT / STANAG 4172/2310, MIL-C-50/MIL-DTL-10190E, Soviet
ballistics, Applied Ballistics ABDOC) and the ABE real-weapons seed.
A value that drifts from research fails the gate.

Run: python3 -m unittest tools/tests/test_ammo_database.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
AMMO = (REPO / "addons/ballistics/functions/fnc_getAmmoProperties.sqf").read_text(
    encoding="utf-8"
)
WEAPON = (REPO / "addons/ballistics/functions/fnc_getWeaponProperties.sqf").read_text(
    encoding="utf-8"
)


def extract_family(source, key):
    """Find the switch case for the family and return the numbers.
    Bracket-aware: counts { } depth so nested if/else variants (AP,
    SLAP) are captured whole.  The ammo file uses `_a find`, the
    weapon file `_w find`."""
    m = re.search(rf'case \([_\w]+ find "{key}" >= 0[^)]*\):\s*\{{', source)
    if not m:
        raise AssertionError(f"family {key} not found")
    i = m.end()
    depth, j = 1, i
    while depth > 0 and j < len(source):
        if source[j] == "{":
            depth += 1
        elif source[j] == "}":
            depth -= 1
        j += 1
    body = source[i:j]
    # Strip any inner `find "x" >= 0` conditions: take only the numbers
    # after the first `{` that opens the actual tier array.
    first_arr = body.find("{")
    if first_arr >= 0:
        body = body[first_arr:]
    tier = re.findall(r"[0-9.]+", body)
    return [float(x) for x in tier]


class TestAmmoDatabase(unittest.TestCase):
    def test_556_mv_bc(self):
        # M855A1 EPR: 961 m/s @ 20", G1 0.308 (the AP branch; the ball
        # M855 948 m/s / 0.307 is the else branch).
        tier = extract_family(AMMO, "556x45")
        self.assertAlmostEqual(tier[0], 961, delta=1, msg="M855A1 MV")
        self.assertAlmostEqual(tier[1], 0.308, delta=0.001, msg="M855A1 G1 BC")

    def test_762_nato_mv_bc(self):
        # M993 AP: 930 m/s, G1 0.430 (the AP branch; M80 ball 838/0.393
        # is the else branch).
        tier = extract_family(AMMO, "762x51")
        self.assertAlmostEqual(tier[0], 930, delta=1, msg="M993 AP MV")
        self.assertAlmostEqual(tier[1], 0.430, delta=0.001, msg="M993 G1 BC")

    def test_762_soviet_mv(self):
        # M67: 710-733 m/s (Soviet; 733 at 25 m in the Yugo spec).
        tier = extract_family(AMMO, "762x39")
        self.assertAlmostEqual(tier[0], 710, delta=1, msg="M67 MV")
        self.assertAlmostEqual(tier[1], 0.279, delta=0.001, msg="M67 G1 BC")

    def test_545_mv(self):
        # 7N6: 880 m/s @ 16.3", G7 0.168 (BRL measured).
        tier = extract_family(AMMO, "545x39")
        self.assertAlmostEqual(tier[0], 880, delta=1, msg="7N6 MV")
        self.assertAlmostEqual(tier[2], 0.168, delta=0.001, msg="7N6 G7 BC")

    def test_50bmg_mv_bc(self):
        # M903 SLAP: 1219 m/s, G1 0.670 (the SLAP branch; M33 ball
        # 885 m/s is the else branch).
        tier = extract_family(AMMO, "127x99")
        self.assertAlmostEqual(tier[0], 1219, delta=1, msg="SLAP MV")
        self.assertAlmostEqual(tier[1], 0.670, delta=0.001, msg="SLAP G1 BC")

    def test_127_soviet(self):
        # B-32 API: 818 m/s @ 40", G7 0.340 (Soviet; seed 0.34).
        tier = extract_family(AMMO, "127x108")
        self.assertAlmostEqual(tier[0], 818, delta=1, msg="B-32 MV")
        self.assertAlmostEqual(tier[2], 0.340, delta=0.001, msg="B-32 G7 BC")

    def test_9mm(self):
        # 124gr FMJ: 351 m/s @ 4", G1 0.149 (CIP 235 MPa).
        tier = extract_family(AMMO, "9x21")
        self.assertAlmostEqual(tier[0], 351, delta=1, msg="9mm MV")
        self.assertAlmostEqual(tier[1], 0.149, delta=0.001, msg="9mm G1 BC")

    def test_65_caseless_analogue(self):
        # 6.5 Grendel (the real analogue): 790 m/s, G1 0.500.
        tier = extract_family(AMMO, "65x39")
        self.assertAlmostEqual(tier[0], 790, delta=1, msg="6.5 Grendel MV")
        self.assertAlmostEqual(tier[1], 0.500, delta=0.001, msg="6.5 G1 BC")

    def test_338(self):
        # .338 LM 250gr: 899 m/s @ 24", G1 0.756 (ABDOC116).
        tier = extract_family(AMMO, "338")
        self.assertAlmostEqual(tier[0], 899, delta=1, msg=".338 MV")
        self.assertAlmostEqual(tier[1], 0.756, delta=0.001, msg=".338 G1 BC")


class TestWeaponDatabase(unittest.TestCase):
    def test_m4_family(self):
        # M4A1: 368 mm barrel, 1:7 twist (0.178 m), 430 MPa, 862 m/s.
        tier = extract_family(WEAPON, "arifle_mx")
        self.assertAlmostEqual(tier[0], 0.368, delta=0.001, msg="M4 barrel m")
        self.assertAlmostEqual(tier[1], 0.178, delta=0.001, msg="M4 twist m")
        self.assertAlmostEqual(tier[2], 430, delta=1, msg="M4 pressure MPa")
        self.assertAlmostEqual(tier[6], 862, delta=1, msg="M4 MV m/s")

    def test_m16_family(self):
        # M16A4: 508 mm, 1:7, 940 m/s.
        tier = extract_family(WEAPON, "arifle_mx_gl")
        self.assertAlmostEqual(tier[0], 0.508, delta=0.001, msg="M16 barrel m")
        self.assertAlmostEqual(tier[6], 940, delta=1, msg="M16 MV m/s")

    def test_m249(self):
        # M249 SAW: 465 mm, 1:7, 915 m/s.
        tier = extract_family(WEAPON, "lmga_mk200")
        self.assertAlmostEqual(tier[0], 0.465, delta=0.001, msg="M249 barrel")
        self.assertAlmostEqual(tier[6], 915, delta=1, msg="M249 MV")

    def test_m240(self):
        # M240: 630 mm, 1:12 (0.305 m), 857 m/s.
        tier = extract_family(WEAPON, "lmga_navid")
        self.assertAlmostEqual(tier[0], 0.630, delta=0.001, msg="M240 barrel")
        self.assertAlmostEqual(tier[1], 0.305, delta=0.001, msg="M240 twist")
        self.assertAlmostEqual(tier[6], 857, delta=1, msg="M240 MV")

    def test_pkm(self):
        # PKM: 650 mm, 1:9.45 (0.240 m), 355 MPa, 825 m/s.
        tier = extract_family(WEAPON, "lmga_zafir")
        self.assertAlmostEqual(tier[0], 0.650, delta=0.001, msg="PKM barrel")
        self.assertAlmostEqual(tier[2], 355, delta=1, msg="PKM pressure")
        self.assertAlmostEqual(tier[6], 825, delta=1, msg="PKM MV")


class TestBallisticWiring(unittest.TestCase):
    def test_fired_eh_uses_real_mv(self):
        # The Fired EH must use the derived MV (issue #170: measure the
        # barrel, derive the MV from the cartridge curve), not the game
        # initSpeed.
        post = (REPO / "addons/ballistics/XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("measureBarrel", post)
        self.assertIn("deriveCartridge", post)

    def test_mv_correction_uses_real_mv(self):
        # The MV correction reads the ammo database real MV.
        mv = (
            REPO
            / "addons/ballistics/functions/fnc_calculateMuzzleVelocityCorrection.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getAmmoProperties", mv)


if __name__ == "__main__":
    unittest.main()
