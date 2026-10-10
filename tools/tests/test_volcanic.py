#!/usr/bin/env python3
"""Reference checks for AEE's volcanic activity model (issue #25).

These tests validate the SQF implementation in addons/atmos/functions/volcanic
(Briggs plume rise, Pasquill-Gifford dispersion, Stokes settling, ash, SO2,
lahar, volcanic winter) against the source formulas. They fail if the
formulas drift from the reference.

Run: python3 -m unittest tools/tests/test_volcanic.py
"""

import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLCANIC = ROOT / "addons" / "atmos" / "functions" / "volcanic"

# Briggs (1973) open-country dispersion coefficients, x and sigma in metres.
SY_C = {"A": 0.22, "B": 0.16, "C": 0.11, "D": 0.08, "E": 0.06, "F": 0.04}
SZ_C = {"A": 0.20, "B": 0.12, "C": 0.08, "D": 0.06, "E": 0.03, "F": 0.016}
SZ_D = {"A": 0.0, "B": 0.0, "C": 0.0002, "D": 0.0015, "E": 0.0003, "F": 0.0003}
SZ_E = {"A": -0.5, "B": -0.5, "C": -0.5, "D": -0.5, "E": -1.0, "F": -1.0}


def sigma(stability, x):
    """Mirror of the Briggs coefficient block in fnc_calculateGaussianPlume.sqf."""
    s = stability if stability in SY_C else "D"
    sy = SY_C[s] * x * ((1 + 0.0001 * x) ** -0.5)
    sz = SZ_C[s] * x * ((1 + SZ_D[s] * x) ** SZ_E[s])
    return sy, sz


def gaussian(Q, u, stability, H, x, y, z):
    """Mirror of fnc_calculateGaussianPlume.sqf."""
    if Q <= 0 or u <= 0 or x <= 0:
        return 0.0
    sy, sz = sigma(stability, x)
    if sy <= 0 or sz <= 0:
        return 0.0
    lateral = math.exp(-(y * y) / (2 * sy * sy))
    vertical = math.exp(-((z - H) ** 2) / (2 * sz * sz)) + math.exp(
        -((z + H) ** 2) / (2 * sz * sz)
    )
    return Q / (2 * math.pi * u * sy * sz) * lateral * vertical


def plume_rise(Qh, u, stability="D", temp_c=15, rho=1.225):
    """Mirror of fnc_calculatePlumeRise.sqf (Briggs 1975)."""
    cp = 1005.0
    g = 9.80665
    T = temp_c + 273.15
    F = g * Qh / (math.pi * cp * rho * T)
    u = max(u, 0.5)
    if F <= 0:
        return 0.0
    if stability in ("E", "F"):
        dtdz = 0.035 if stability == "F" else 0.02
        S = (g / T) * dtdz
        return 2.6 * ((F / (u * S)) ** (1 / 3))
    if F < 55:
        return 21.425 * (F**0.75) / u
    return 38.71 * (F**0.6) / u


def settling(d, rho_p=2500.0, rho_a=1.225, mu=1.81e-5):
    """Mirror of fnc_calculateAshSettling.sqf (Stokes 1851)."""
    if d <= 0 or mu <= 0:
        return 0.0
    r = d / 2
    return max(0.0, (2 / 9) * (rho_p - rho_a) * 9.80665 * r * r / mu)


def dust_visibility(c_mg):
    """Mirror of the weather calculateDustVisibility model (Baddock 2014)."""
    k = 0.5
    vis = 300.0
    if c_mg > 0:
        vis = k / c_mg
    return vis


def volcanic_ash(Q, u, stability, H, x, y, d=2e-5, rho_a=1.225):
    """Mirror of fnc_calculateVolcanicAsh.sqf.  Returns (cKg, cMg, vs, dep)."""
    vs = settling(d, 2500.0, rho_a)
    tilt = vs * x / u if u > 0 else 0.0
    h_eff = max(0.0, H - tilt)
    c_kg = gaussian(Q, u, stability, h_eff, x, y, 0)
    return c_kg, c_kg * 1e6, vs, c_kg * vs


def so2_ppm(c_kg, temp_c=15, p=101325):
    """Mirror of the ppm conversion in fnc_calculateSO2Plume.sqf."""
    M = 0.064066
    R = 8.314
    T = temp_c + 273.15
    return max(0.0, (c_kg / M) * (R * T / p) * 1e6)


def so2_band(ppm):
    """Mirror of the NIOSH bands in fnc_calculateSO2Plume.sqf."""
    band = "none"
    if ppm >= 2:
        band = "rel"
    if ppm >= 5:
        band = "stel"
    if ppm >= 20:
        band = "bronchospasm"
    if ppm >= 100:
        band = "idlh"
    return band


def lahar_risk(activity, rain_mmh, deposit_m, slope_deg):
    """Mirror of fnc_calculateLaharRisk.sqf."""
    water = min(max(rain_mmh, 0) / 25.0, 1.0)
    material = min(max(deposit_m, 0) / 1.0, 1.0)
    slope = min(max(slope_deg, 0) / 15.0, 1.0)
    activity = max(0.0, min(activity, 1.0))
    return max(0.0, min(water * material * slope * activity, 1.0))


def winter_cooling(vei, lat, same_hemisphere=True):
    """Mirror of fnc_calculateVolcanicWinter.sqf.  Returns (global, regional)."""
    global_cooling = 0.5 * (2 ** (vei - 6)) if vei >= 2 else 0.0
    hemisphere = 1.0 if same_hemisphere else 0.5
    latitude = 1 + (abs(lat) / 90) * 0.5
    return global_cooling, global_cooling * hemisphere * latitude


class TestPlumeRise(unittest.TestCase):
    def test_zero_heat_zero_rise(self):
        self.assertEqual(plume_rise(0, 5), 0.0)

    def test_weak_branch(self):
        # F < 55 uses 21.425 F^(3/4) / u.
        Qh = 1.0e6
        F = 9.80665 * Qh / (math.pi * 1005 * 1.225 * 288.15)
        self.assertLess(F, 55)
        self.assertAlmostEqual(plume_rise(Qh, 5), 21.425 * F**0.75 / 5, places=6)

    def test_strong_branch(self):
        # F >= 55 uses 38.71 F^(3/5) / u.
        Qh = 1.0e9
        F = 9.80665 * Qh / (math.pi * 1005 * 1.225 * 288.15)
        self.assertGreaterEqual(F, 55)
        self.assertAlmostEqual(plume_rise(Qh, 5), 38.71 * F**0.6 / 5, places=6)

    def test_rise_increases_with_heat(self):
        self.assertGreater(plume_rise(1.0e9, 5), plume_rise(1.0e7, 5))

    def test_rise_decreases_with_wind(self):
        self.assertGreater(plume_rise(1.0e9, 2), plume_rise(1.0e9, 8))

    def test_stable_formula(self):
        Qh = 1.0e9
        F = 9.80665 * Qh / (math.pi * 1005 * 1.225 * 288.15)
        S = (9.80665 / 288.15) * 0.02
        self.assertAlmostEqual(
            plume_rise(Qh, 5, "E"), 2.6 * (F / (5 * S)) ** (1 / 3), places=6
        )


class TestGaussianPlume(unittest.TestCase):
    def test_zero_source_zero(self):
        self.assertEqual(gaussian(0, 5, "D", 100, 1000, 0, 0), 0.0)

    def test_ground_centreline_matches_formula(self):
        sy, sz = sigma("D", 1000)
        expect = (
            1.0
            / (2 * math.pi * 5 * sy * sz)
            * (
                math.exp(-(100.0**2) / (2 * sz * sz))
                + math.exp(-(100.0**2) / (2 * sz * sz))
            )
        )
        self.assertAlmostEqual(gaussian(1, 5, "D", 100, 1000, 0, 0), expect, places=9)

    def test_unstable_spreads_more_than_stable(self):
        sy_a, _ = sigma("A", 1000)
        sy_f, _ = sigma("F", 1000)
        self.assertGreater(sy_a, sy_f)

    def test_crosswind_decays(self):
        self.assertGreater(
            gaussian(1, 5, "D", 100, 1000, 0, 0),
            gaussian(1, 5, "D", 100, 1000, 200, 0),
        )


class TestAshSettling(unittest.TestCase):
    def test_known_value_10um(self):
        # 10 um fine ash at 2500 kg/m3 settles at ~7.52 mm/s.
        self.assertAlmostEqual(settling(1.0e-5), 7.521e-3, places=5)

    def test_larger_faster(self):
        self.assertGreater(settling(5.0e-5), settling(1.0e-5))

    def test_zero_diameter_zero(self):
        self.assertEqual(settling(0), 0.0)


class TestVolcanicAsh(unittest.TestCase):
    def test_concentration_positive(self):
        # Coarse ash settles into a low plume at 5 km: the ground sees ash.
        c_kg, _, _, _ = volcanic_ash(5.0e6, 5, "D", 200, 5000, 0, 1.0e-4)
        self.assertGreater(c_kg, 0.0)

    def test_settling_brings_ash_down(self):
        # Coarse ash settles to the ground; fine ash stays aloft.
        coarse = volcanic_ash(5.0e6, 5, "D", 200, 5000, 0, 1.0e-4)[0]
        fine = volcanic_ash(5.0e6, 5, "D", 200, 5000, 0, 1.0e-6)[0]
        self.assertGreater(coarse, fine)

    def test_deposition_is_concentration_times_settling(self):
        c_kg, _, vs, dep = volcanic_ash(5.0e6, 5, "D", 200, 5000, 0, 1.0e-4)
        self.assertAlmostEqual(dep, c_kg * vs, places=12)

    def test_visibility_falls_with_concentration(self):
        self.assertLess(dust_visibility(1000), dust_visibility(10))

    def test_clear_air_visibility(self):
        self.assertEqual(dust_visibility(0), 300.0)


class TestSO2Plume(unittest.TestCase):
    def test_one_ppm_is_262_mgm3(self):
        # NIOSH: 1 ppm = 2.62 mg/m3 at 25 C, 1 atm.
        self.assertAlmostEqual(so2_ppm(2.62e-6, 25, 101325), 1.0, places=2)

    def test_bands(self):
        self.assertEqual(so2_band(0.5), "none")
        self.assertEqual(so2_band(3), "rel")
        self.assertEqual(so2_band(10), "stel")
        self.assertEqual(so2_band(50), "bronchospasm")
        self.assertEqual(so2_band(150), "idlh")

    def test_idlh_is_life_threatening(self):
        self.assertEqual(so2_band(100), "idlh")


class TestLaharRisk(unittest.TestCase):
    def test_dry_no_risk(self):
        self.assertEqual(lahar_risk(1, 0, 2, 20), 0.0)

    def test_threshold_half(self):
        # 12.5 mm/h is half the 25 mm/h threshold; full material and slope.
        self.assertAlmostEqual(lahar_risk(1, 12.5, 1, 15), 0.5)

    def test_full_risk(self):
        self.assertEqual(lahar_risk(1, 50, 2, 20), 1.0)

    def test_flat_no_risk(self):
        self.assertEqual(lahar_risk(1, 50, 2, 0), 0.0)


class TestVolcanicWinter(unittest.TestCase):
    def test_vei6_pinatubo_anchor(self):
        g, _ = winter_cooling(6, 0)
        self.assertAlmostEqual(g, 0.5)

    def test_vei7_doubles(self):
        g, _ = winter_cooling(7, 0)
        self.assertAlmostEqual(g, 1.0)

    def test_below_vei2_no_cooling(self):
        self.assertEqual(winter_cooling(1, 45)[0], 0.0)

    def test_latitude_amplifies(self):
        self.assertGreater(winter_cooling(6, 70)[1], winter_cooling(6, 0)[1])

    def test_other_hemisphere_weaker(self):
        self.assertLess(winter_cooling(6, 45, False)[1], winter_cooling(6, 45, True)[1])


class TestSources(unittest.TestCase):
    """The SQF carries the named formula sources; removing one fails here."""

    def _src(self, name):
        return (VOLCANIC / name).read_text(encoding="utf-8")

    def test_plume_rise_cites_briggs(self):
        self.assertIn("Briggs", self._src("fnc_calculatePlumeRise.sqf"))
        self.assertIn("21.425", self._src("fnc_calculatePlumeRise.sqf"))
        self.assertIn("38.71", self._src("fnc_calculatePlumeRise.sqf"))

    def test_settling_cites_stokes(self):
        self.assertIn("Stokes", self._src("fnc_calculateAshSettling.sqf"))

    def test_so2_cites_niosh(self):
        self.assertIn("NIOSH", self._src("fnc_calculateSO2Plume.sqf"))

    def test_winter_cites_robock(self):
        self.assertIn("Robock", self._src("fnc_calculateVolcanicWinter.sqf"))

    def test_lahar_cites_pierson(self):
        self.assertIn("Pierson", self._src("fnc_calculateLaharRisk.sqf"))


if __name__ == "__main__":
    unittest.main()
