#!/usr/bin/env python3
"""Reference checks for the underwater light model (issue #14).

Runs the REAL SQF kernels in addons/maritime/functions through the sqf_lite
harness, so the test cannot drift from the source.  The anchors are the
issue's test vectors plus the cited ocean-optics values.

Run: python3 -m unittest tools.tests.test_underwater_light -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FUNCS = REPO / "addons" / "maritime" / "functions"

PURE = FUNCS / "fnc_pureWaterAbsorption.sqf"
WATER_TYPE = FUNCS / "fnc_waterTypeKd.sqf"
UNDERWATER = FUNCS / "fnc_calculateUnderwaterLight.sqf"
LIGHT_DEPTH = FUNCS / "fnc_calculateLightDepth.sqf"
SECCHI = FUNCS / "fnc_calculateSecchiKd.sqf"
SNELL = FUNCS / "fnc_calculateSnellWindow.sqf"
BIOLUM = FUNCS / "fnc_calculateBioluminescence.sqf"


def _pure(nm):
    return run_sqf(PURE, [nm])


class TestBeerLambert(unittest.TestCase):
    """I(z) = I0 exp(-Kd z), the issue test vectors."""

    def test_jerlov_i_ten_metres(self):
        # Issue: Jerlov I Kd=0.035, z=10 -> T=0.70.
        t = run_sqf(UNDERWATER, [10, 0.035, 0.035, 0.035])
        self.assertAlmostEqual(t[0], 0.70, places=2)

    def test_coastal_five_ten_metres(self):
        # Issue: coastal 5 Kd=0.42, z=10 -> T=0.015.
        t = run_sqf(UNDERWATER, [10, 0.42, 0.42, 0.42])
        self.assertAlmostEqual(t[0], 0.015, places=3)

    def test_red_band_five_metres(self):
        # Issue: Kd_R=0.45, z=5 -> T=0.105.
        t = run_sqf(UNDERWATER, [5, 0.45, 0.45, 0.45])
        self.assertAlmostEqual(t[0], 0.105, places=3)

    def test_blue_band_thirty_metres(self):
        # Issue: Kd_B=0.03, z=30 -> T=0.41.
        t = run_sqf(UNDERWATER, [30, 0.03, 0.03, 0.03])
        self.assertAlmostEqual(t[0], 0.41, places=2)

    def test_surface_is_full_transmission(self):
        t = run_sqf(UNDERWATER, [0, 0.4, 0.4, 0.4])
        self.assertEqual(t, [1.0, 1.0, 1.0])

    def test_negative_depth_clamps_to_surface(self):
        t = run_sqf(UNDERWATER, [-5, 0.4, 0.4, 0.4])
        self.assertEqual(t, [1.0, 1.0, 1.0])

    def test_red_decays_faster_than_blue(self):
        # Blue shift emerges from the three exponentials.
        t = run_sqf(UNDERWATER, [20, 0.40, 0.05, 0.03])
        self.assertLess(t[0], t[1])
        self.assertLess(t[1], t[2])


class TestSecchi(unittest.TestCase):
    """Kd from a Secchi depth: 1.7/Zsd clear, 1.44/Zsd turbid."""

    def test_open_ocean_thirty_metres(self):
        # Issue: Zsd=30 -> Kd=0.057.
        self.assertAlmostEqual(run_sqf(SECCHI, [30, False]), 0.057, places=3)

    def test_turbid_uses_holmes_factor(self):
        self.assertAlmostEqual(run_sqf(SECCHI, [10, True]), 0.144, places=3)

    def test_zero_depth_returns_zero(self):
        self.assertEqual(run_sqf(SECCHI, [0, False]), 0.0)


class TestLightDepth(unittest.TestCase):
    """1 percent light depth = ln(100)/Kd = 4.605/Kd."""

    def test_one_percent_depth(self):
        # Issue: Kd=0.04 -> 1 percent at 115 m.
        self.assertAlmostEqual(run_sqf(LIGHT_DEPTH, [0.04, 0.01]), 115.13, places=1)

    def test_ten_percent_depth(self):
        # ln(10)/0.1 = 23.03 m.
        self.assertAlmostEqual(run_sqf(LIGHT_DEPTH, [0.1, 0.1]), 23.03, places=1)

    def test_zero_kd_returns_zero(self):
        self.assertEqual(run_sqf(LIGHT_DEPTH, [0, 0.01]), 0.0)


class TestSnellWindow(unittest.TestCase):
    """sin(theta_c) = 1/n_water."""

    def test_pure_water_default(self):
        # Issue: n=1.333 -> theta_c=48.6, cone=97.2.
        s = run_sqf(SNELL, [])
        self.assertAlmostEqual(s[0], 48.6, places=1)
        self.assertAlmostEqual(s[1], 97.2, places=1)

    def test_seawater_index(self):
        # n=1.34 -> theta_c ~ 48.3.
        s = run_sqf(SNELL, [1.34])
        self.assertAlmostEqual(s[0], math.degrees(math.asin(1 / 1.34)), places=3)

    def test_cone_is_twice_the_critical_angle(self):
        s = run_sqf(SNELL, [1.333])
        self.assertAlmostEqual(s[1], s[0] * 2, places=6)


class TestPureWaterAbsorption(unittest.TestCase):
    """Pope and Fry (1997) anchors, omlc.org digitisation."""

    def test_anchors(self):
        self.assertAlmostEqual(_pure(418), 0.0044, places=4)
        self.assertAlmostEqual(_pure(475), 0.0114, places=4)
        self.assertAlmostEqual(_pure(530), 0.0434, places=4)
        self.assertAlmostEqual(_pure(600), 0.222, places=3)
        self.assertAlmostEqual(_pure(660), 0.410, places=3)
        self.assertAlmostEqual(_pure(700), 0.650, places=3)

    def test_interpolation_between_anchors(self):
        # 490 nm: 0.0114 + (15/55)*(0.0434-0.0114) = 0.02013.
        self.assertAlmostEqual(_pure(490), 0.02013, places=4)

    def test_below_range_holds_nearest_anchor(self):
        self.assertAlmostEqual(_pure(300), 0.0044, places=4)

    def test_above_range_holds_nearest_anchor(self):
        self.assertAlmostEqual(_pure(900), 0.650, places=3)


class TestWaterTypeKd(unittest.TestCase):
    """Jerlov water type to per-band Kd (660/530/475 nm)."""

    def _kd(self, idx):
        return run_sqf(WATER_TYPE, [idx], {"__FUNC__pureWaterAbsorption": _pure})

    def test_clear_water_peak_is_the_blue_band(self):
        # Jerlov I: Kd at the 475 nm peak is the tabulated 0.035.
        kd = self._kd(0)
        self.assertAlmostEqual(kd[2], 0.035, places=3)

    def test_clear_water_keeps_blue_longest(self):
        kd = self._kd(0)
        self.assertGreater(kd[0], kd[1])
        self.assertGreater(kd[1], kd[2])

    def test_turbid_water_loses_blue_first(self):
        # Jerlov 9: dissolved matter absorbs blue, so blue is the worst band.
        kd = self._kd(9)
        self.assertGreater(kd[2], kd[1])
        self.assertGreater(kd[1], kd[0])

    def test_index_clamps(self):
        self.assertEqual(self._kd(-3), self._kd(0))
        self.assertEqual(self._kd(99), self._kd(9))

    def test_bands_are_ordered_red_green_blue(self):
        # The output order is 660, 530, 475 nm, so Kd_R comes first.
        kd = self._kd(3)
        self.assertEqual(len(kd), 3)


class TestBioluminescence(unittest.TestCase):
    """Gate: darkness, clear water, disturbance."""

    def test_flash_in_dark_clear_stirred_water(self):
        visible, intensity = run_sqf(BIOLUM, [0.001, 0.05, 0.5, 0.17])
        self.assertTrue(visible)
        self.assertGreater(intensity, 0)

    def test_daylight_suppresses_the_flash(self):
        visible, intensity = run_sqf(BIOLUM, [1.0, 0.05, 0.5, 0.17])
        self.assertFalse(visible)
        self.assertEqual(intensity, 0)

    def test_turbid_water_hides_the_flash(self):
        visible, _ = run_sqf(BIOLUM, [0.001, 0.5, 0.5, 0.17])
        self.assertFalse(visible)

    def test_still_water_has_no_flash(self):
        visible, _ = run_sqf(BIOLUM, [0.001, 0.05, 0.0, 0.17])
        self.assertFalse(visible)

    def test_envelope_decays_after_the_peak(self):
        _, early = run_sqf(BIOLUM, [0.001, 0.05, 1.0, 0.17])
        _, late = run_sqf(BIOLUM, [0.001, 0.05, 1.0, 1.0])
        self.assertGreater(early, late)


if __name__ == "__main__":
    unittest.main()
