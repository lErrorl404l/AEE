#!/usr/bin/env python3
"""Seismic kernels (issue #27).

Executes the shipped SQF kernels through the sqf_lite interpreter, so the test
runs the real source rather than a Python mirror.  The kernels are pure: they
read only their parameters and the built-in math commands.

Sources (see each kernel header):
  Boore and Atkinson (2008) GMPE, Earthquake Spectra 24(1):99-138,
    DOI 10.1193/1.2830434.
  Worden et al. (2012) MMI from PGA, BSSA 102(1):204-221,
    DOI 10.1785/0120110156.
  Seed and Idriss (1971) liquefaction; Youd et al. (2001) NCEER, DOI
    10.1061/(ASCE)1090-0241(2001)127:4(297).
  Newmark (1965) Geotechnique 15(2):139-160, DOI 10.1680/geot.1965.15.2.139;
    Ambraseys and Menu (1988) regression, DOI 10.1002/eqe.4290160704.
  Wells and Coppersmith (1994) rupture length, DOI 10.1785/BSSA0840040974.

Run: python3 -m unittest tools.tests.test_seismic -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

SEISMIC = REPO / "addons" / "persistence" / "functions" / "seismic"


def gm(mag, rjb):
    return run_sqf(SEISMIC / "fnc_seismicGroundMotion.sqf", [mag, rjb])


def lq(pga, depth, n160, mag, wt):
    return run_sqf(SEISMIC / "fnc_seismicLiquefaction.sqf", [pga, depth, n160, mag, wt])


def ls(slope, pga, fs):
    return run_sqf(SEISMIC / "fnc_seismicLandslide.sqf", [slope, pga, fs])


def dmg(mmi):
    return run_sqf(SEISMIC / "fnc_seismicDamage.sqf", [mmi])


def shake(pga, mag):
    return run_sqf(SEISMIC / "fnc_seismicShake.sqf", [pga, mag])


def points(centre, radius, delta, step):
    return run_sqf(
        SEISMIC / "fnc_seismicTerrainPoints.sqf", [centre, radius, delta, step]
    )


class TestGroundMotion(unittest.TestCase):
    def test_ba08_reference_values(self):
        # BA08 Table 6, rock (Vs30 = 760), normal fault, Rjb = 10 km.
        pga, pgv, mmi = gm(6.5, 10)
        self.assertAlmostEqual(pga, 0.14791, places=4)
        self.assertAlmostEqual(pgv, 8.6311, places=3)
        self.assertAlmostEqual(mmi, 6.3976, places=3)

    def test_pga_in_g_is_plausible(self):
        # A unit error (g vs cm/s^2) would put this near 145, not 0.15.
        pga, _, _ = gm(6.5, 10)
        self.assertGreater(pga, 0.02)
        self.assertLess(pga, 1.0)

    def test_magnitude_increases_motion(self):
        self.assertGreater(gm(7.5, 10)[0], gm(6.5, 10)[0])
        self.assertGreater(gm(6.5, 10)[0], gm(5.5, 10)[0])

    def test_distance_decreases_motion(self):
        self.assertGreater(gm(6.5, 10)[0], gm(6.5, 100)[0])

    def test_mmi_bands_match_shakemap(self):
        # 0.115 g -> VI, 0.215 g -> VII, 0.401 g -> VIII (USGS ShakeMap).
        self.assertAlmostEqual(gm(6.5, 10)[2], 6.3976, places=3)
        self.assertGreater(gm(6.5, 10)[2], 6.0)
        self.assertLess(gm(6.5, 10)[2], 7.0)

    def test_mmi_clamped(self):
        self.assertGreaterEqual(gm(0.1, 500)[2], 1.0)
        self.assertLessEqual(gm(9.0, 1)[2], 12.0)

    def test_bad_input(self):
        self.assertEqual(gm(6.5, -5), [0, 0, 1])


class TestLiquefaction(unittest.TestCase):
    def test_liquefies_under_strong_shaking(self):
        fs, liq = lq(0.3, 5, 15, 7.0, 1.5)
        self.assertLess(fs, 1.0)
        self.assertTrue(liq)

    def test_no_liquefaction_under_weak_shaking(self):
        fs, liq = lq(0.1, 5, 25, 6.0, 2.0)
        self.assertGreater(fs, 1.0)
        self.assertFalse(liq)

    def test_fs_falls_with_pga(self):
        self.assertGreater(lq(0.1, 5, 15, 7.0, 1.5)[0], lq(0.4, 5, 15, 7.0, 1.5)[0])

    def test_clean_sand_is_not_liquefiable(self):
        self.assertEqual(lq(0.5, 5, 35, 7.0, 1.5)[0], 99)

    def test_surface_layer_has_no_safety_concern(self):
        self.assertEqual(lq(0.5, 0, 15, 7.0, 1.5)[0], 99)


class TestLandslide(unittest.TestCase):
    def test_critical_acceleration(self):
        # a_c = (FS-1)*sin(slope); FS 1.5, slope 20 deg -> 0.1710 g.
        ac, _, _ = ls(20, 0.3, 1.5)
        self.assertAlmostEqual(ac, 0.17101, places=4)

    def test_displacement_positive_when_shaking_exceeds_ac(self):
        _, dn, trig = ls(20, 0.3, 1.5)
        self.assertAlmostEqual(dn, 0.017324, places=5)
        self.assertTrue(trig)

    def test_no_movement_below_critical(self):
        _, dn, trig = ls(20, 0.1, 1.5)
        self.assertEqual(dn, 0)
        self.assertFalse(trig)

    def test_steeper_slope_has_higher_critical_acceleration(self):
        # a_c = (FS-1)*sin(slope): a steeper slope needs stronger shaking to
        # move, so at a fixed static factor of safety it moves less.
        self.assertGreater(ls(30, 0.5, 1.2)[0], ls(20, 0.5, 1.2)[0])
        self.assertLess(ls(30, 0.5, 1.2)[1], ls(20, 0.5, 1.2)[1])

    def test_lower_static_fs_moves_more(self):
        self.assertGreater(ls(20, 0.5, 1.1)[1], ls(20, 0.5, 1.8)[1])


class TestDamage(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(dmg(5.0), [0, False])
        self.assertEqual(dmg(7.0), [1, False])
        self.assertEqual(dmg(9.0), [2, False])
        self.assertEqual(dmg(10.0), [3, True])

    def test_monotonic(self):
        self.assertLessEqual(dmg(6.0)[0], dmg(8.0)[0])
        self.assertLessEqual(dmg(8.0)[0], dmg(10.0)[0])


class TestShake(unittest.TestCase):
    def test_power_scales_with_pga(self):
        self.assertEqual(shake(0.5, 6.5)[0], 20.0)
        self.assertLess(shake(0.1, 6.5)[0], shake(0.3, 6.5)[0])

    def test_power_capped(self):
        self.assertLessEqual(shake(1.0, 8.0)[0], 20.0)

    def test_duration_grows_with_magnitude(self):
        # Wells and Coppersmith rupture length / 2.8 km/s.
        self.assertAlmostEqual(shake(0.3, 7.0)[1], 17.4921, places=3)
        self.assertGreater(shake(0.3, 7.0)[1], shake(0.3, 6.0)[1])


class TestTerrainPoints(unittest.TestCase):
    def test_subsidence_grid(self):
        pts = points([100, 200, 50], 10, -0.2, 5)
        self.assertGreater(len(pts), 0)
        # Centre point is lowered by the full delta.
        centre = [p for p in pts if p[0] == 100 and p[1] == 200][0]
        self.assertAlmostEqual(centre[2], 49.8, places=4)
        # Every point is at or below the base height for a negative delta.
        self.assertTrue(all(p[2] <= 50.0 for p in pts))

    def test_deposit_grid_raises(self):
        pts = points([0, 0, 10], 8, 0.3, 4)
        self.assertTrue(all(p[2] >= 10.0 for p in pts))

    def test_bad_input_is_empty(self):
        self.assertEqual(points([0, 0, 0], 0, 0.2, 5), [])
        self.assertEqual(points([0, 0, 0], 10, 0, 5), [])


if __name__ == "__main__":
    unittest.main()
