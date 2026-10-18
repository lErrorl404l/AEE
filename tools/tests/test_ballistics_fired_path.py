#!/usr/bin/env python3
"""Fired-path tests for the ballistics addon (issues #245, #246).

The Fired event is a hot path: it runs once per shot, on every shooter.  Two
defects lived there.

  #245  The round mass was `getNumber (configFile >> "CfgAmmo" >> _ammo >> "hit")
        * 0.5`.  `hit` is a DAMAGE number, not a mass, so the mass for kinetic
        energy and free recoil was wrong, worst for a large calibre (a .50 M33
        is 42 g against the 15 g proxy).

  #246  The ammo-to-initSpeed lookup enumerated every CfgMagazines class in
        every loaded mod, uncached, on every shot.

The mass lock parses the generated projectile table and holds it to the
published bullet weights (grains to grams), because the Fired handler now
consumes that table.

Run: python3 -m unittest tools.tests.test_ballistics_fired_path
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
XEH_POSTINIT = (REPO / "addons/ballistics/XEH_postInit.sqf").read_text(encoding="utf-8")
PROJECTILES_SQF = (
    REPO / "addons/ballistics/functions/fnc_getProjectileData.sqf"
).read_text(encoding="utf-8")
MV_CORRECTION = (
    REPO / "addons/ballistics/functions/fnc_calculateMuzzleVelocityCorrection.sqf"
).read_text(encoding="utf-8")

GRAIN_G = 0.06479891


def projectile_rows():
    """[id, aliases, mass g, diameter mm, coefficients, length mm] rows."""
    m = re.search(r"private _TABLE = \[(.*?)\n\];", PROJECTILES_SQF, re.S)
    assert m is not None
    return {
        row[0]: float(row[2])
        for row in re.findall(
            r'\["([^"]+)", "([^"]*)", ([0-9.]+), ([0-9.]+), "([^"]*)", ([0-9.]+)\]',
            m.group(1),
        )
    }


class TestRoundMass(unittest.TestCase):
    """Issue #245: the round mass is the bullet mass, in kilograms."""

    def setUp(self):
        self.rows = projectile_rows()

    def test_the_fired_handler_reads_the_projectile_database(self):
        self.assertIn("getProjectileData", XEH_POSTINIT)
        self.assertIn("_massG / 1000", XEH_POSTINIT)

    def test_the_damage_value_is_only_a_fallback(self):
        # `hit` stays as the fallback for an ammo the corpus does not hold,
        # and it is converted to kilograms so the units cannot drift again.
        self.assertIn('"CfgAmmo" >> _ammo >> "hit"', XEH_POSTINIT)
        self.assertIn(") * 0.5) / 1000", XEH_POSTINIT)

    def test_the_published_bullet_masses_are_held(self):
        # M193 55 gr, M80 149 gr, M33 650 gr, held in grams.
        for pid, grains, issue_grams in (
            ("apg_m193", 55.0, 4.0),
            ("apg_m80", 149.0, 9.5),
            ("apg_m33", 650.0, 42.0),
        ):
            with self.subTest(projectile=pid):
                self.assertIn(pid, self.rows)
                self.assertAlmostEqual(self.rows[pid], grains * GRAIN_G, places=4)
                # The issue's real masses, which the old proxy missed badly.
                self.assertAlmostEqual(self.rows[pid], issue_grams, delta=0.5)

    def test_the_old_proxy_would_miss_these_masses(self):
        # The proxy was hit * 0.5 grams: 9/11.6/30 -> 4.5/5.8/15 g.
        for pid, proxy_g, held_g in (
            ("apg_m193", 4.5, 3.5639),
            ("apg_m80", 5.8, 9.655),
            ("apg_m33", 15.0, 42.1193),
        ):
            with self.subTest(projectile=pid):
                self.assertNotAlmostEqual(proxy_g, self.rows[pid], places=1)
                self.assertNotAlmostEqual(held_g, proxy_g, places=1)


class TestInitSpeedCache(unittest.TestCase):
    """Issue #246: the initSpeed lookup must be cached per ammo class."""

    def test_the_lookup_is_memoised(self):
        self.assertIn("initSpeedCache", MV_CORRECTION)

    def test_the_config_scan_is_inside_the_cache_miss(self):
        # The CfgMagazines enumeration may not run once the value is held.
        # The scan marker is the CALL, not the header comment that also names
        # the function.
        cache_at = MV_CORRECTION.index("initSpeedCache")
        scan_at = MV_CORRECTION.index("call BIS_fnc_returnChildren")
        self.assertLess(cache_at, scan_at)
        miss = MV_CORRECTION[cache_at:scan_at]
        self.assertIn("_initSpeed < 0", miss)
        # The value is written back, or the cache never fills.
        self.assertGreater(MV_CORRECTION.count("_cache set [_ammo, _initSpeed]"), 0)

    def test_the_cache_holds_a_zero_as_a_zero(self):
        # A zero means "no magazine fires this ammo", which is stable for the
        # session: caching it avoids a rescan per shot for such an ammo.  The
        # -1 sentinel is what marks "not yet resolved".
        self.assertIn("getOrDefault [_ammo, -1]", MV_CORRECTION)


if __name__ == "__main__":
    unittest.main()
