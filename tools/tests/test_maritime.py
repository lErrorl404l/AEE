#!/usr/bin/env python3
"""Reference checks for AEE's maritime models.

Checks of the SQF implementations in addons/maritime: harmonic tidal
prediction (eight constituents, validated against NOAA) and WMO Beaufort
sea state.  Compass declination is covered by test_wmm.py.

Run: python3 -m unittest tools/tests/test_maritime.py
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

MAGNETIC = (
    Path(__file__).resolve().parents[2]
    / "addons"
    / "magnetism"
    / "functions"
    / "fnc_calculateMagneticAnomaly.sqf"
)

_MARITIME = Path(__file__).resolve().parents[2] / "addons" / "maritime" / "functions"


def dipole_flux_density_nt(moment, r, cos_theta):
    """SI dipole flux density in nT: B = (mu0/4pi) M/r^3 sqrt(1+3cos^2)."""
    return (1e-7 * moment / r**3) * math.sqrt(1 + 3 * cos_theta**2) * 1e9


def tidal_alignment(jd_ut):
    """cos of the M2-S2 equilibrium phase difference (twice the elongation)."""
    from tools import gen_tide_constituents as tides
    args = tides.arguments(jd_ut)
    return math.cos(math.radians(args["M2"][0] - args["S2"][0]))


def sea_state_beaufort(wind_ms):
    """Mirror of fnc_calculateSeaState.sqf — WMO Beaufort B = (v/0.836)^(2/3)."""
    return max(0, min(12, round((wind_ms / 0.836) ** (2 / 3))))


def wave_height(wind_ms):
    """Mirror of the Pierson-Moskowitz significant wave height 0.0246 v^2."""
    return min(0.0246 * wind_ms**2, 15)


def ekman_transport(u10, lat_deg):
    """Mirror of fnc_ekmanTransport.sqf (Ekman 1905; Stewart 2008).

    f = 2 Omega sin(phi); M = tau/(rho_w f); D_e = sqrt(2 K_v/|f|);
    V0 = tau/sqrt(rho_w^2 |f| K_v).  |f| is clamped at the value at 0.5 deg.
    """
    omega = 7.2921e-5
    rho_air, cd, rho_w, kv = 1.2, 1.2e-3, 1025.0, 0.1
    f = 2 * omega * math.sin(math.radians(lat_deg))
    f_min = 2 * omega * math.sin(math.radians(0.5))
    if abs(f) < f_min:
        f = f_min * (1 if f >= 0 else -1)
    tau = rho_air * cd * u10 * u10
    transport = tau / (rho_w * f)
    depth = math.sqrt(2 * kv / abs(f))
    surface = tau / math.sqrt(rho_w * rho_w * abs(f) * kv)
    return [transport, depth, surface]


def tidal_current_speed(eta, depth):
    """Mirror of fnc_tidalCurrentSpeed.sqf: u = |eta| sqrt(g/H)."""
    return abs(eta) * math.sqrt(9.80665 / max(depth, 1.0))


def ocean_current_vector(
    u10,
    wind_az_deg,
    lat_deg,
    fraction,
    deflection_deg,
    tide,
    depth,
    ebb,
    flood_bearing_deg,
):
    """Mirror of the vector composition in fnc_calculateOceanCurrent.sqf.

    The wind-driven part is deflected right of the wind in the north and left
    in the south; the tidal part runs along the flood axis and reverses on the
    ebb.  Returns [total [east, north], speed, tidal speed].
    """
    wind_speed = fraction * u10
    sign = 1 if lat_deg >= 0 else -1
    waz = math.radians(wind_az_deg + sign * deflection_deg)
    wx, wy = wind_speed * math.sin(waz), wind_speed * math.cos(waz)
    tidal_speed = abs(tide) * math.sqrt(9.80665 / max(depth, 1.0))
    tb = math.radians(flood_bearing_deg + (180 if ebb else 0))
    tx, ty = tidal_speed * math.sin(tb), tidal_speed * math.cos(tb)
    total = [wx + tx, wy + ty]
    return total, math.hypot(total[0], total[1]), tidal_speed


class TestTidalHarmonics(unittest.TestCase):
    def test_constituent_periods(self):
        # M2 period = 360/28.9841 = 12.42 h; S2 = 360/30 = 12 h.
        self.assertAlmostEqual(360 / 28.9841, 12.42, places=1)
        self.assertAlmostEqual(360 / 30.0000, 12.00, places=2)

    def test_beat_period_spring_neap(self):
        # M2-S2 beat = 360/1.0159 = 354.4 h = 14.77 days.
        beat_h = 360 / (30.0000 - 28.9841)
        self.assertAlmostEqual(beat_h / 24, 14.77, places=1)

    def test_spring_tide_at_new_and_full_moon(self):
        # New moon 2024-01-11 11:57 UT, full moon 2024-01-25 17:54 UT, first
        # quarter 2024-01-18 03:52 UT (USNO phases of the moon).
        self.assertGreater(tidal_alignment(2460320.998), 0.95)
        self.assertGreater(tidal_alignment(2460335.246), 0.95)
        self.assertLess(tidal_alignment(2460327.661), -0.95)

    def test_formula_reproduces_noaa(self):
        from tools import gen_tide_constituents as tides
        self.assertLess(tides.noaa_rms(), 0.06)

    def test_generated_table_is_fresh(self):
        from tools import gen_tide_constituents as tides
        self.assertEqual(tides.main(["--check"]), 0)

    def test_real_gauges(self):
        # TICON-4: Samothraki (North Aegean) is microtidal, Lautoka (Fiji)
        # mesotidal.  Brest M2 205.1 cm confirms the source unit is cm.
        import json
        data = json.loads((Path(__file__).resolve().parents[2] / "data" / "maritime"
                           / "tide_constituents.json").read_text(encoding="utf-8"))
        sam = data["gauges"]["samothraki"]["constituents"]
        lau = data["gauges"]["lautoka"]["constituents"]
        self.assertLess(sum(c["amp_m"] for c in sam.values()), 0.25)
        self.assertAlmostEqual(lau["M2"]["amp_m"], 0.629, places=2)
        self.assertEqual(data["world_bindings"]["Enoch"]["gauge"], "")

    def test_the_sqf_uses_the_validated_arguments(self):
        src = (Path(__file__).resolve().parents[2] / "addons" / "maritime" / "functions"
               / "fnc_calculateTidalPrediction.sqf").read_text(encoding="utf-8")
        for token in ("[_tau + _h - 90, _fK1, _uK1]", "[_tau - 2 * _s + _h + 90, _fO1, _uO1]",
                      "gameClockToUT", "getTideConstituents"):
            self.assertIn(token, src)
        self.assertNotIn("max -_amp min _amp", src)


class TestSeaState(unittest.TestCase):
    def test_wmo_beaufort_reference(self):
        # WMO: B=12 starts at ~32.7 m/s (64 kt); B=5 ~9.8 m/s.
        self.assertEqual(sea_state_beaufort(32.7), 12)
        self.assertEqual(sea_state_beaufort(9.8), 5)

    def test_calm_is_zero(self):
        self.assertEqual(sea_state_beaufort(0), 0)

    def test_monotonic(self):
        prev = sea_state_beaufort(0)
        for v in range(0, 4001, 100):
            b = sea_state_beaufort(v / 100)
            self.assertGreaterEqual(b, prev)
            prev = b

    def test_clamped_12(self):
        self.assertEqual(sea_state_beaufort(100), 12)

    def test_wave_height_grows_quadratically(self):
        # H_s = 0.0246 v^2: 10 m/s -> 2.46 m, 20 m/s -> 9.84 m (4x).
        self.assertAlmostEqual(wave_height(10), 2.46, places=2)
        self.assertAlmostEqual(wave_height(20) / wave_height(10), 4.0, places=1)

    def test_wave_height_capped(self):
        self.assertLessEqual(wave_height(100), 15)


class TestCompassAnomalyScale(unittest.TestCase):
    """The dipole kernel returns SI flux density in nT, not field strength.

    fnc_calculateMagneticAnomaly omitted the vacuum permeability mu0, so it
    returned the magnetic field strength H (A/m) instead of the flux density B
    (tesla): ~795775x too large.  The operator RPT of 2026-10-08 logged an
    anomaly of 8.22e7 nT (about 1700x Earth's 50000 nT field) and pinned the
    compass deviation at the +10 deg clamp.  This suite runs the REAL SQF
    kernel and asserts a physically bounded flux density.
    """

    def test_vehicle_at_50_m_is_a_few_nanotesla(self):
        # Given a vehicle-scale dipole (1000 A m^2) 50 m above the sensor.
        # When the real kernel runs.
        got = run_sqf(MAGNETIC, [[0, 0, 50], [0, 0, 0], 1000, 0])
        # Then the flux density is bounded (a few nT), not 1e8.
        want = dipole_flux_density_nt(1000, 50, 1.0)
        self.assertAlmostEqual(got, want, places=6)
        self.assertLess(got, 10.0)

    def test_matches_the_si_flux_density_not_field_strength(self):
        # The pre-fix formula (missing mu0) is 1/(4pi*1e-7) = 795775x.
        r = 10.0
        got = run_sqf(MAGNETIC, [[0, 0, r], [0, 0, 0], 1000, 0])
        field_strength_nt = (1000 / (4 * math.pi * r**3)) * 2 * 1e9
        self.assertAlmostEqual(
            field_strength_nt / got, 1 / (4 * math.pi * 1e-7), places=0
        )

    def test_deviation_never_reaches_the_clamp_at_50_m(self):
        # deviation = anomaly/50000 * 57.2957795, clamped +/-10 deg.
        anomaly_nt = run_sqf(MAGNETIC, [[0, 0, 50], [0, 0, 0], 1000, 0])
        dev_deg = (anomaly_nt / 50000.0) * 57.2957795
        self.assertLess(abs(dev_deg), 1.0)

    def test_inverse_cube_falloff_holds(self):
        b10 = run_sqf(MAGNETIC, [[0, 0, 10], [0, 0, 0], 1000, 0])
        b20 = run_sqf(MAGNETIC, [[0, 0, 20], [0, 0, 0], 1000, 0])
        self.assertAlmostEqual(b20, b10 / 8, places=6)


class TestEkmanTransport(unittest.TestCase):
    """The Ekman transport kernel (issue #28), executed as shipped SQF."""

    def setUp(self):
        self.kernel = _MARITIME / "fnc_ekmanTransport.sqf"

    def test_matches_the_ekman_reference_at_45n(self):
        # f = 2*7.2921e-5*sin(45) = 1.0312e-4; tau = 1.2*1.2e-3*10^2 = 0.144;
        # M = tau/(1025 f) = 1.362 m^2/s; D_e = sqrt(2*0.1/f) = 44.0 m.
        got = run_sqf(self.kernel, [10, 45])
        want = ekman_transport(10, 45)
        self.assertAlmostEqual(got[0], want[0], places=9)
        self.assertAlmostEqual(got[0], 1.362, places=3)
        self.assertAlmostEqual(got[1], 44.038, places=3)
        self.assertAlmostEqual(got[2], want[2], places=9)

    def test_issue_vector_one_m2s_per_tenth_n_per_m2(self):
        # The issue's stated vector: tau = 0.1 N/m^2 at 45 N gives M = 0.95.
        # tau = 0.00144 U10^2, so U10 = sqrt(0.1/0.00144) = 8.333 m/s.
        got = run_sqf(self.kernel, [math.sqrt(0.1 / 0.00144), 45])
        self.assertAlmostEqual(got[0], 0.95, places=2)

    def test_equator_is_clamped_and_finite(self):
        # f -> 0 at the equator would divide by zero; the kernel clamps |f| to
        # the value at 0.5 degrees and stays finite.
        got = run_sqf(self.kernel, [10, 0])
        self.assertTrue(math.isfinite(got[0]))
        self.assertTrue(math.isfinite(got[1]))
        self.assertGreater(got[0], 0)


class TestTidalCurrentSpeed(unittest.TestCase):
    """The tidal current kernel (issue #28), executed as shipped SQF."""

    def setUp(self):
        self.kernel = _MARITIME / "fnc_tidalCurrentSpeed.sqf"

    def test_shallow_and_deep_reference(self):
        # u = eta sqrt(g/H): 1 m in 10 m -> 0.99 m/s; in 50 m -> 0.44 m/s.
        self.assertAlmostEqual(run_sqf(self.kernel, [1, 10]), 0.990, places=3)
        self.assertAlmostEqual(run_sqf(self.kernel, [1, 50]), 0.443, places=3)

    def test_zero_tide_is_zero_current(self):
        self.assertEqual(run_sqf(self.kernel, [0, 10]), 0)

    def test_sign_of_the_tide_does_not_matter(self):
        # The speed is the magnitude; the direction is set by the flood/ebb.
        self.assertAlmostEqual(
            run_sqf(self.kernel, [-1, 10]), run_sqf(self.kernel, [1, 10]), places=9
        )

    def test_zero_depth_is_finite(self):
        self.assertTrue(math.isfinite(run_sqf(self.kernel, [1, 0])))


class TestOceanCurrentDriver(unittest.TestCase):
    """The driver that composes the wind-driven and tidal currents."""

    def setUp(self):
        self.driver = (_MARITIME / "fnc_calculateOceanCurrent.sqf").read_text(
            encoding="utf-8"
        )

    def test_driver_reuses_the_state_it_must(self):
        # It reuses the wind vector, the harmonic tide height, the map latitude
        # and the two pure kernels; it does not model its own tide or wind.
        self.assertIn("EGVAR(core,currentWind)", self.driver)
        self.assertIn("EGVAR(core,currentTideOffset_m)", self.driver)
        self.assertIn("EFUNC(lib,getWorldLocation)", self.driver)
        self.assertIn("FUNC(ekmanTransport)", self.driver)
        self.assertIn("FUNC(tidalCurrentSpeed)", self.driver)

    def test_driver_publishes_the_current(self):
        self.assertIn("QGVAR(oceanCurrent)", self.driver)
        self.assertIn("QGVAR(oceanCurrentSpeed)", self.driver)
        self.assertIn("QGVAR(ekmanTransport_m2s)", self.driver)

    def test_vector_sum_of_the_two_parts(self):
        # Wind blowing north (azimuth 0) at 10 m/s, 45 N, 3%, 30 deg right,
        # a 1 m flood tide in 10 m of water on the north axis.
        total, speed, tidal_speed = ocean_current_vector(
            10, 0, 45, 0.03, 30, 1, 10, False, 0
        )
        self.assertAlmostEqual(total[0], 0.15, places=3)  # east: 0.3 sin30
        self.assertAlmostEqual(total[1], 0.15 * 1.732 + 0.990, places=2)
        self.assertAlmostEqual(tidal_speed, 0.990, places=3)
        self.assertAlmostEqual(speed, math.hypot(*total), places=9)

    def test_southern_hemisphere_deflects_left(self):
        # The same wind in the south deflects the current left of the wind, so
        # the east component flips sign.
        north, _, _ = ocean_current_vector(10, 0, 45, 0.03, 30, 0, 10, False, 0)
        south, _, _ = ocean_current_vector(10, 0, -45, 0.03, 30, 0, 10, False, 0)
        self.assertGreater(north[0], 0)
        self.assertLess(south[0], 0)

    def test_ebb_reverses_the_tidal_part(self):
        flood, _, _ = ocean_current_vector(0, 0, 45, 0.03, 30, 1, 10, False, 0)
        ebb, _, _ = ocean_current_vector(0, 0, 45, 0.03, 30, 1, 10, True, 0)
        self.assertAlmostEqual(flood[1], -ebb[1], places=6)


class TestOceanCurrentWiring(unittest.TestCase):
    """The current is wired into the environment tick and prep'd."""

    def test_core_tick_calls_the_current(self):
        core = (
            Path(__file__).resolve().parents[2]
            / "addons"
            / "core"
            / "functions"
            / "fnc_updateEnvironment.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("EFUNC(maritime,calculateOceanCurrent)", core)

    def test_prep_registers_the_functions(self):
        prep = (_MARITIME.parent / "XEH_PREP.hpp").read_text(encoding="utf-8")
        for name in (
            "PREP(calculateOceanCurrent)",
            "PREP(ekmanTransport)",
            "PREP(tidalCurrentSpeed)",
        ):
            self.assertIn(name, prep)


if __name__ == "__main__":
    unittest.main()
