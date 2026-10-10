#!/usr/bin/env python3
"""Radar detection model tests (issue #104).

The pure kernels under addons/radio/functions/radar are executed for real
through tools/tests/sqf_lite.py.  Each kernel is checked against the
issue's test vectors and against the published reference formula it
mirrors.  The engine-reading query (fnc_calculateRadarDetection) is
checked structurally: it reads the atmosphere and maritime state, calls
every kernel, and publishes nothing.

Run: python3 -m unittest tools.tests.test_radar -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.tests.sqf_lite import run_sqf  # noqa: E402

RADAR = ROOT / "addons" / "radio" / "functions" / "radar"


def _kernel(name: str):
    return RADAR / name


def _code(name: str) -> str:
    return _kernel(name).read_text(encoding="utf-8")


class TestRadarRangeEquation(unittest.TestCase):
    def test_issue_vector_461_km(self):
        # 1 MW, G = 1000, lambda = 0.03 m, sigma = 1 m^2, P_min = 1e-13 W.
        rmax = run_sqf(
            _kernel("fnc_radarRangeEquation.sqf"),
            [1e6, 1000, 0.03, 1, 1e-13, 4],
        )
        self.assertAlmostEqual(rmax / 1000, 46.1, places=1)

    def test_reference_formula(self):
        pt, g, lam, sigma, pmin = 1e6, 1000.0, 0.03, 1.0, 1e-13
        expected = (pt * g**2 * lam**2 * sigma / ((4 * math.pi) ** 3 * pmin)) ** 0.25
        got = run_sqf(
            _kernel("fnc_radarRangeEquation.sqf"), [pt, g, lam, sigma, pmin, 4]
        )
        self.assertAlmostEqual(got, expected, places=6)

    def test_duct_exponent_extends_range(self):
        free = run_sqf(
            _kernel("fnc_radarRangeEquation.sqf"), [1e6, 1000, 0.03, 1, 1e-13, 4]
        )
        duct = run_sqf(
            _kernel("fnc_radarRangeEquation.sqf"), [1e6, 1000, 0.03, 1, 1e-13, 2]
        )
        self.assertGreater(duct, free)

    def test_guards_return_zero(self):
        self.assertEqual(
            run_sqf(_kernel("fnc_radarRangeEquation.sqf"), [1e6, 1000, 0.03, 1, 0, 4]),
            0,
        )


class TestRadarNoiseFloor(unittest.TestCase):
    def test_reference_formula(self):
        b, fn, snr = 1e6, 2.0, 20.0
        expected = 1.38e-23 * 290 * b * fn * snr
        got = run_sqf(_kernel("fnc_radarNoiseFloor.sqf"), [b, fn, snr])
        self.assertAlmostEqual(got, expected, places=12)

    def test_scales_with_bandwidth(self):
        low = run_sqf(_kernel("fnc_radarNoiseFloor.sqf"), [1e6, 2.0, 20.0])
        high = run_sqf(_kernel("fnc_radarNoiseFloor.sqf"), [2e6, 2.0, 20.0])
        self.assertAlmostEqual(high / low, 2.0, places=6)


class TestRadarHorizon(unittest.TestCase):
    def test_issue_vector_35_6_km(self):
        dmax = run_sqf(_kernel("fnc_radarHorizon.sqf"), [30, 10])
        self.assertAlmostEqual(dmax, 35.6, places=1)

    def test_reference_formula(self):
        ha, ht = 30.0, 10.0
        expected = (math.sqrt(2 * (4 / 3) * 6371000) / 1000) * (
            math.sqrt(ha) + math.sqrt(ht)
        )
        got = run_sqf(_kernel("fnc_radarHorizon.sqf"), [ha, ht])
        self.assertAlmostEqual(got, expected, places=6)

    def test_higher_antenna_sees_further(self):
        low = run_sqf(_kernel("fnc_radarHorizon.sqf"), [10, 10])
        high = run_sqf(_kernel("fnc_radarHorizon.sqf"), [100, 10])
        self.assertGreater(high, low)


class TestRadarSeaClutter(unittest.TestCase):
    def test_issue_vector_41_2_db(self):
        # VV, 10 GHz, sea state 3, grazing 1 degree.
        sigma0 = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [1, 10, 3, "VV"])
        self.assertAlmostEqual(sigma0, -41.2, places=1)

    def test_reference_formula_vv(self):
        psi, f, ss = 1.0, 10.0, 3.0
        cc1, cc2, cc3, cc4, cc5 = -50.796, 25.93, 0.7093, 21.588, 0.00211
        expected = (
            cc1
            + cc2 * math.log10(math.sin(math.radians(psi)))
            + (27.5 + cc3 * psi) * math.log10(f) / (1 + 0.95 * psi)
            + cc4 * (ss + 1) ** (1 / (2 + 0.085 * psi + 0.033 * ss))
            + cc5 * psi**2
        )
        got = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [psi, f, ss, "VV"])
        self.assertAlmostEqual(got, expected, places=6)

    def test_hh_differs_from_vv(self):
        vv = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [1, 10, 3, "VV"])
        hh = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [1, 10, 3, "HH"])
        self.assertNotAlmostEqual(vv, hh, places=3)

    def test_higher_sea_state_higher_clutter(self):
        low = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [1, 10, 1, "VV"])
        high = run_sqf(_kernel("fnc_radarSeaClutter.sqf"), [1, 10, 6, "VV"])
        self.assertGreater(high, low)


class TestRadarClutterRange(unittest.TestCase):
    def test_issue_vector_3_3_km(self):
        rmax = run_sqf(
            _kernel("fnc_radarClutterRange.sqf"),
            [10, -40, 0.02, 1e-6, 0, 10],
        )
        self.assertAlmostEqual(rmax / 1000, 3.3, places=1)

    def test_reference_formula(self):
        sigma_t, sigma0_db, theta, tau, psi, tcr = 10.0, -40.0, 0.02, 1e-6, 0.0, 10.0
        sigma0 = 10 ** (sigma0_db / 10)
        expected = sigma_t / (
            sigma0 * theta * (3e8 * tau / 2) / math.cos(math.radians(psi)) * tcr
        )
        got = run_sqf(
            _kernel("fnc_radarClutterRange.sqf"),
            [sigma_t, sigma0_db, theta, tau, psi, tcr],
        )
        self.assertAlmostEqual(got, expected, places=3)

    def test_bigger_target_seen_further(self):
        small = run_sqf(
            _kernel("fnc_radarClutterRange.sqf"), [1, -40, 0.02, 1e-6, 0, 10]
        )
        big = run_sqf(
            _kernel("fnc_radarClutterRange.sqf"), [10, -40, 0.02, 1e-6, 0, 10]
        )
        self.assertGreater(big, small)


class TestRadarRcs(unittest.TestCase):
    def test_class_values(self):
        self.assertAlmostEqual(
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["fighter"]), 3.0, places=6
        )
        self.assertAlmostEqual(
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["helicopter"]), 3.0, places=6
        )
        self.assertAlmostEqual(
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["vehicle"]), 10.0, places=6
        )
        self.assertAlmostEqual(
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["ship"]), 1000.0, places=6
        )

    def test_case_insensitive(self):
        self.assertEqual(
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["FIGHTER"]),
            run_sqf(_kernel("fnc_radarRcs.sqf"), ["fighter"]),
        )

    def test_unknown_class_is_zero(self):
        self.assertEqual(run_sqf(_kernel("fnc_radarRcs.sqf"), ["banana"]), 0)

    def test_stealth_less_than_fighter(self):
        stealth = run_sqf(_kernel("fnc_radarRcs.sqf"), ["stealth"])
        fighter = run_sqf(_kernel("fnc_radarRcs.sqf"), ["fighter"])
        self.assertLess(stealth, fighter)


class TestRadarDuctRange(unittest.TestCase):
    def test_trapped_x_band_returns_two(self):
        # X-band 10 GHz, duct delta 15 m.  A surface duct needs
        # dN/dz < -157 N/km (so dM/dz = dN/dz + 157 < 0).
        exponent = run_sqf(_kernel("fnc_radarDuctRange.sqf"), [15, 1e10, -200, 10, 5])
        self.assertEqual(exponent, 2)

    def test_no_duct_when_gradient_not_trapping(self):
        # dN/dz = -60 N/km -> dM/dz = 97 N/km >= 0: no trapping.
        exponent = run_sqf(_kernel("fnc_radarDuctRange.sqf"), [15, 1e10, -60, 10, 5])
        self.assertEqual(exponent, 4)

    def test_endpoint_above_duct_not_trapped(self):
        exponent = run_sqf(_kernel("fnc_radarDuctRange.sqf"), [15, 1e10, -200, 100, 5])
        self.assertEqual(exponent, 4)

    def test_below_cutoff_not_trapped(self):
        # 10 MHz is far below the duct cutoff (~61 MHz at delta 15 m).
        exponent = run_sqf(_kernel("fnc_radarDuctRange.sqf"), [15, 1e7, -200, 10, 5])
        self.assertEqual(exponent, 4)


class TestRadarDetectionRange(unittest.TestCase):
    def test_horizon_limits_when_not_ducted(self):
        rdet, limiting = run_sqf(
            _kernel("fnc_radarDetectionRange.sqf"), [50000, 40000, 35000, False]
        )
        self.assertEqual(rdet, 35000)
        self.assertEqual(limiting, "horizon")

    def test_clutter_limits_when_smallest(self):
        rdet, limiting = run_sqf(
            _kernel("fnc_radarDetectionRange.sqf"), [50000, 3000, 35000, False]
        )
        self.assertEqual(rdet, 3000)
        self.assertEqual(limiting, "clutter")

    def test_noise_limits_when_smallest(self):
        rdet, limiting = run_sqf(
            _kernel("fnc_radarDetectionRange.sqf"), [2000, 40000, 35000, False]
        )
        self.assertEqual(rdet, 2000)
        self.assertEqual(limiting, "noise")

    def test_duct_removes_the_horizon_limit(self):
        ducted, _ = run_sqf(
            _kernel("fnc_radarDetectionRange.sqf"), [50000, 40000, 35000, True]
        )
        self.assertEqual(ducted, 40000)


class TestCalculateRadarDetectionContract(unittest.TestCase):
    """The engine query: structure, not behaviour (it reads engine state)."""

    SRC = _code("fnc_calculateRadarDetection.sqf")

    def test_reads_the_atmosphere_and_maritime_state(self):
        self.assertIn("EGVAR(atmos,refractivityGradient)", self.SRC)
        self.assertIn("EGVAR(core,currentTemperature)", self.SRC)
        self.assertIn("EGVAR(maritime,seaSurfaceTemperature)", self.SRC)
        self.assertIn("EGVAR(core,seaStateBeaufort)", self.SRC)

    def test_calls_every_kernel(self):
        for name in (
            "radarDuctRange",
            "radarNoiseFloor",
            "radarRcs",
            "radarRangeEquation",
            "radarSeaClutter",
            "radarClutterRange",
            "radarHorizon",
            "radarDetectionRange",
        ):
            self.assertIn(f"FUNC({name})", self.SRC)

    def test_gated_on_the_setting(self):
        self.assertIn("QGVAR(radarDetection)", self.SRC)

    def test_publishes_nothing(self):
        self.assertNotIn("setVariable", self.SRC)

    def test_returns_the_three_element_shape(self):
        self.assertIn("[_rdet, _limiting, _detected]", self.SRC)


if __name__ == "__main__":
    unittest.main()
