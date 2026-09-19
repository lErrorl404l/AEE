#!/usr/bin/env python3
"""Reference checks for AEE's atmospheric refraction model.

These tests validate the SQF implementation in addons/atmos
(fnc_calculateRefraction.sqf) against the source formulas. They mirror
the exact formulas in the SQF source so that any drift breaks the tests.

Covers:
  - Buck vapour pressure
  - ITU-R P.453 radio refractivity
  - Surface refractivity gradient
  - k-factor (refraction coefficient)
  - Ducting / super-refraction / standard / sub-refraction condition

Run: python3 -m unittest tools.tests.test_atmospheric_refraction -v
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ATMOS = _REPO_ROOT / "addons" / "atmos" / "functions"


def _read_recursive(base, name):
    """Read an SQF function file, resolving categorised subfolders (issue
    #203).  The function NAME is flat (aee_<mod>_fnc_<name>)."""
    if (base / name).exists():
        return (base / name).read_text(encoding="utf-8")
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


def _read_sqf(name):
    """Read an SQF function file. The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced."""
    return _read_recursive(_ATMOS, name)


def vapor_pressure_buck(temp_c, rh_pct):
    """Mirror of the Buck equation in fnc_calculateRefraction.sqf.

    e = RH/100 * 6.105 * exp(17.27*T / (237.7 + T)) hPa.
    """
    return (rh_pct / 100) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))


def refractivity_itu(temp_c, rh_pct, pressure_hpa):
    """Mirror of the ITU-R P.453 refractivity in fnc_calculateRefraction.sqf.

    N = 77.6 * P/T + 3.73e5 * e/T^2, T in Kelvin.
    """
    temp_k = temp_c + 273.15
    e = vapor_pressure_buck(temp_c, rh_pct)
    return 77.6 * pressure_hpa / temp_k + 3.73e5 * e / (temp_k**2)


def refractivity_gradient(temp_c):
    """Mirror of the surface gradient in fnc_calculateRefraction.sqf.

    The standard atmosphere has a surface gradient of -39 N/km. The
    simulation scales this by the temperature deviation from 15 C.
    """
    return -39 * (1 + 0.00366 * (temp_c - 15))


def k_factor(dndh):
    """Mirror of the k-factor in fnc_calculateRefraction.sqf.

    k = 1 / (1 + a * dn/dh) with a = 6371 km. The gradient is in N/km,
    so the product carries a 1e-6 scale. Ducting drives the denominator
    to zero; the clamp keeps k finite.
    """
    denom = 1 + 6371 * dndh * 1e-6
    return 1 / max(denom, 0.001)


def refraction_condition(dndh):
    """Mirror of the condition switch in fnc_calculateRefraction.sqf."""
    if dndh <= -157:
        return "Ducting"
    if dndh < -39:
        return "Super-refraction"
    if dndh > -39:
        return "Sub-refraction"
    return "Standard"


class TestVapourPressure(unittest.TestCase):
    def test_standard(self):
        # 15 C, 50 % RH -> e ~ 8.5 hPa.
        self.assertAlmostEqual(vapor_pressure_buck(15, 50), 8.51, delta=0.1)

    def test_saturation(self):
        # 100 % RH at 25 C -> e ~ 31.7 hPa (saturation vapour pressure).
        self.assertAlmostEqual(vapor_pressure_buck(25, 100), 31.7, delta=0.5)

    def test_dry_zero(self):
        self.assertEqual(vapor_pressure_buck(15, 0), 0.0)

    def test_humidity_scales(self):
        self.assertAlmostEqual(
            vapor_pressure_buck(20, 50) * 2, vapor_pressure_buck(20, 100), delta=0.01
        )


class TestRefractivity(unittest.TestCase):
    def test_standard_atmosphere(self):
        # 15 C, 1013 hPa, 50 % RH -> N ~ 311 (task reference ~315).
        n = refractivity_itu(15, 50, 1013)
        self.assertAlmostEqual(n, 315, delta=10)

    def test_extreme_humidity(self):
        # 25 C, 95 % RH, 1010 hPa -> N > 350.
        self.assertGreater(refractivity_itu(25, 95, 1010), 350)

    def test_typical_range(self):
        # Earth atmosphere N is typically 250-400.
        for t, rh, p in [(15, 50, 1013), (25, 95, 1010), (-10, 30, 1030)]:
            self.assertTrue(250 < refractivity_itu(t, rh, p) < 400)

    def test_dry_air(self):
        # Dry air at 0 C: N = 77.6 * P / T only.
        self.assertAlmostEqual(
            refractivity_itu(0, 0, 1013), 77.6 * 1013 / 273.15, delta=0.1
        )


class TestGradient(unittest.TestCase):
    def test_standard(self):
        self.assertAlmostEqual(refractivity_gradient(15), -39, delta=0.01)

    def test_cold_sub_refraction(self):
        self.assertGreater(refractivity_gradient(-10), -39)

    def test_warm_super_refraction(self):
        self.assertLess(refractivity_gradient(25), -39)


class TestKFactor(unittest.TestCase):
    def test_standard(self):
        self.assertAlmostEqual(k_factor(-39), 1.33, delta=0.05)

    def test_ducting(self):
        # dN/dh = -157 drives the denominator to zero: k -> infinity.
        self.assertGreater(k_factor(-157), 100)

    def test_sub_refraction(self):
        self.assertLess(k_factor(-20), 1.33)

    def test_super_refraction(self):
        self.assertGreater(k_factor(-100), 1.33)


class TestCondition(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(refraction_condition(-39), "Standard")

    def test_ducting(self):
        self.assertEqual(refraction_condition(-200), "Ducting")

    def test_super_refraction(self):
        self.assertEqual(refraction_condition(-100), "Super-refraction")

    def test_sub_refraction(self):
        self.assertEqual(refraction_condition(-20), "Sub-refraction")

    def test_boundary_157(self):
        self.assertEqual(refraction_condition(-157), "Ducting")


class TestSQFSync(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, fragments, context):
        text = _read_sqf("fnc_calculateRefraction.sqf")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"fnc_calculateRefraction.sqf: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_atmospheric_refraction.py.",
        )

    def test_buck_constants(self):
        self._assert_in_sqf(["6.105", "17.27", "237.7"], "Buck equation constants")

    def test_itu_constants(self):
        self._assert_in_sqf(["77.6", "3.73e5", "273.15"], "ITU-R P.453 constants")

    def test_gradient_constants(self):
        self._assert_in_sqf(["-39", "0.00366", "15"], "surface gradient calibration")

    def test_k_factor_constants(self):
        self._assert_in_sqf(["6371", "1e-6", "0.001"], "k-factor constants")

    def test_condition_thresholds(self):
        self._assert_in_sqf(
            [
                "-157",
                "-39",
                "Ducting",
                "Super-refraction",
                "Sub-refraction",
                "Standard",
            ],
            "condition thresholds",
        )

    def test_mirage_types(self):
        self._assert_in_sqf(
            ["Towering", "Inferior", "Looming", "Superior", "None"],
            "mirage type strings",
        )


if __name__ == "__main__":
    unittest.main()
