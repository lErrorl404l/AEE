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
CARTRIDGE = (REPO / "addons/ballistics/functions/fnc_deriveCartridge.sqf").read_text(
    encoding="utf-8"
)
PROJECTILE = (
    REPO / "addons/ballistics/functions/fnc_getProjectileData.sqf"
).read_text(encoding="utf-8")


def extract_cartridge(source, family):
    """Read one cartridge row from _AMMO_FAMILIES and return the numbers.
    The row format: [refMV, refBarrelM, vShort, shortBarrelM, vMin,
    bcG1, bcG7, caliberMm, massG, dragModel, twistM, pressureMPa]."""
    m = re.search(rf'\["{re.escape(family)}",\s*\[([^\]]+)\]\]', source)
    if not m:
        raise AssertionError(f"cartridge {family} not found")
    return [float(x) for x in re.findall(r"[0-9.]+", m.group(1))]


class TestCartridgeTwistPressure(unittest.TestCase):
    """Twist and chamber pressure are CARTRIDGE properties.

    The chambering fixes both, so they live in the cartridge table and
    resolve for a weapon of any mod. No weapon is listed anywhere, so
    the design supports any weapon without a per-weapon patch."""

    def test_556_twist_pressure(self):
        # STANAG 4172 (M855/SS109): 1:7 = 0.178 m per turn.
        # CIP MAP: 430 MPa.
        row = extract_cartridge(CARTRIDGE, "556x45")
        self.assertAlmostEqual(row[10], 0.178, delta=0.001, msg="5.56 twist")
        self.assertAlmostEqual(row[11], 430, delta=1, msg="5.56 pressure")

    def test_762_nato_twist_pressure(self):
        # The NATO standard twist is 1:12 = 305 mm and the NATO EPVAT
        # MAP is 415 MPa. The ABE seed splits 279/305 mm on row count,
        # so this value comes from the standard, not the row mode.
        row = extract_cartridge(CARTRIDGE, "762x51")
        self.assertAlmostEqual(row[10], 0.305, delta=0.001, msg="7.62 twist")
        self.assertAlmostEqual(row[11], 415, delta=1, msg="7.62 pressure")

    def test_545_twist(self):
        # AK-74: 200 mm, 4 right-hand grooves.
        row = extract_cartridge(CARTRIDGE, "545x39")
        self.assertAlmostEqual(row[10], 0.2, delta=0.001, msg="5.45 twist")

    def test_762x39_twist(self):
        # AKM: 240 mm, 4 right-hand grooves.
        row = extract_cartridge(CARTRIDGE, "762x39")
        self.assertAlmostEqual(row[10], 0.24, delta=0.001, msg="7.62x39 twist")

    def test_9mm_twist(self):
        # 9x19: 1:10 = 250 mm.
        row = extract_cartridge(CARTRIDGE, "9x19")
        self.assertAlmostEqual(row[10], 0.25, delta=0.001, msg="9mm twist")

    def test_shotgun_is_smoothbore(self):
        # A 12 gauge barrel has no rifling: twist 0.
        row = extract_cartridge(CARTRIDGE, "12gauge")
        self.assertAlmostEqual(row[10], 0.0, delta=0.001, msg="12 gauge twist")

    def test_no_mod_specific_entries(self):
        # The tables key on cartridge identity, never on a mod's
        # classnames. A mod weapon resolves from its ammunition and its
        # identity signals, so no mod needs its own entry.
        for prefix in ("MSS_", "MCC_", "MPP_", "MHS_", "RHS_", "CUP_"):
            self.assertNotIn(prefix, CARTRIDGE, f"{prefix} is a mod patch")
            self.assertNotIn(prefix, PROJECTILE, f"{prefix} is a mod patch")


class TestBallisticWiring(unittest.TestCase):
    def test_fired_eh_uses_real_mv(self):
        # The Fired EH must use the derived MV (issue #170: measure the
        # barrel, derive the MV from the cartridge curve), not the game
        # initSpeed.
        post = (REPO / "addons/ballistics/XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("measureBarrel", post)
        self.assertIn("resolveShot", post)

    def test_resolve_shot_uses_the_physics_fallbacks(self):
        # The single shot entry point must reach for the database first
        # and for physics when no source holds a value.
        shot = (REPO / "addons/ballistics/functions/fnc_resolveShot.sqf").read_text(
            encoding="utf-8"
        )
        for call in (
            "getCartridgeData",
            "getProjectileData",
            "getBulletShape",
            "calculateBallisticCoefficient",
            "deriveCartridge",
            "calculateInteriorBallistics",
            "calculateStability",
            "calculateBallisticDrag",
        ):
            self.assertIn(call, shot, f"resolveShot does not use {call}")

    def test_mv_correction_uses_initSpeed(self):
        # The MV correction normalises to the game's initSpeed (the
        # round's actual flight velocity) - the temperature ratio is
        # what matters, the database MV lives in the Fired EH.
        mv = (
            REPO
            / "addons/ballistics/functions/fnc_calculateMuzzleVelocityCorrection.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("initSpeed", mv)


if __name__ == "__main__":
    unittest.main()
