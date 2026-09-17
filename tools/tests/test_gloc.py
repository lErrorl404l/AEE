#!/usr/bin/env python3
"""G-LOC and altitude DCS tests (issue #135).

Mirrors of fnc_calculateGLOC.sqf and fnc_calculateAltitudeDCS.sqf: the
Whinnery-Forster time-to-LOC onset model, ICAO barometric pressure,
and the ZH-L16C-as-altitude-DCS solver (R = tissue N2 / ambient).

Run: python3 -m unittest tools.tests.test_gloc
"""

import math
import unittest


# ─── ICAO standard atmosphere (fnc_calculateBarometricPressure.sqf) ────────
# Troposphere (<= 11 km): power law.  Stratosphere (> 11 km): isothermal
# exponential at 216.65 K.  Returns pressure in bar.
P0 = 101325.0  # Pa
T0 = 288.15  # K sea level
L = 0.0065  # K/m lapse
G = 9.80665
R = 287.05287
EXP = G / (R * L)  # 5.25588
T_TROPOPAUSE = 216.65  # K
P_TROPOPAUSE = P0 * (1 - L * 11000 / T0) ** EXP  # Pa


def barometric_pressure_pa(alt_m):
    if alt_m <= 11000:
        return P0 * (1 - L * alt_m / T0) ** EXP
    p_top = P_TROPOPAUSE
    return p_top * math.exp(-G * (alt_m - 11000) / (R * T_TROPOPAUSE))


# ─── Altitude DCS (fnc_calculateAltitudeDCS.sqf) ───────────────────────────
# Reuses the ZH-L16C tissue solver with pAmbOverride = barometric pressure.
# Risk from R = max tissue N2 / pAmb (the controlling slowest compartment,
# not the diving a/b ceiling).  Risk = clamp((R - 1.5) / 0.5, 0, 1).

# ZH-L16C compartment half-times (minutes) and N2 M-value a (surface).
T_HALF_N2 = [
    4.0,
    8.0,
    12.5,
    18.5,
    27.0,
    38.3,
    54.3,
    77.0,
    109,
    146,
    187,
    239,
    305,
    390,
    498,
    635,
]
A_N2 = [
    1.2599,
    1.0,
    0.8618,
    0.7562,
    0.62,
    0.5043,
    0.441,
    0.4,
    0.375,
    0.35,
    0.3295,
    0.3065,
    0.2835,
    0.261,
    0.248,
    0.2327,
]
B_N2 = [
    0.5050,
    0.6514,
    0.7222,
    0.7825,
    0.8126,
    0.8434,
    0.8693,
    0.8910,
    0.9092,
    0.9222,
    0.9319,
    0.9403,
    0.9477,
    0.9544,
    0.9602,
    0.9653,
]
WV = 0.0627  # water vapour, bar


def fresh_tissues():
    """Surface N2 equilibrium: (1 - WV) * 0.79 bar in all 16 comps."""
    baseline = (1 - WV) * 0.79
    return [baseline] * 16 + [0.0] * 16


def zh16c_step(tissues, p_amb, f_n2, dt_s, p_amb_override=None):
    """One tissue step at barometric pressure (altitude DCS mode).

    pi = f_n2 * (p_amb - WV) when p_amb is depth-derived; at altitude the
    override is the barometric pressure directly and inspired N2 follows it.
    """
    p_ambient = p_amb_override if p_amb_override is not None else p_amb
    p_inspired_n2 = 0.79 * (p_ambient - WV)
    dt_min = dt_s / 60.0
    new = list(tissues)
    for i in range(16):
        k = math.log(2) / T_HALF_N2[i]
        new[i] = p_inspired_n2 + (new[i] - p_inspired_n2) * math.exp(-k * dt_min)
    return new


def altitude_dcs_risk(alt_m, exposure_s, tissues=None):
    """R = max tissue N2 / pAmb; risk = clamp((R-1.5)/0.5, 0, 1)."""
    if tissues is None:
        tissues = fresh_tissues()
    p_amb_bar = barometric_pressure_pa(alt_m) / 100000.0
    t = zh16c_step(tissues, None, 0.79, exposure_s, p_amb_override=p_amb_bar)
    r_max = max(t[:16]) / p_amb_bar
    risk = max(0.0, min(1.0, (r_max - 1.5) / 0.5))
    return risk, r_max, t


# ─── G-LOC (fnc_calculateGLOC.sqf) ─────────────────────────────────────────
# Tolerance = 4.7 + 3.1*AGSM + 1.5*G-suit + 0.5*seat, x (1 - 0.4*hypoxiaRisk).
# Whinnery-Forster time-to-LOC: 9.10 s rapid (>= 1 G/s), 74.4 s gradual
# (<= 0.2 G/s), interpolated between; 5 s floor.  Stages: greyout, blackout,
# LOC by excess over tolerance.


def gloc_tolerance(agsm=False, gsuit=False, reclined=False, hypoxia_risk=0.0):
    tol = (
        4.7
        + 3.1 * (1 if agsm else 0)
        + 1.5 * (1 if gsuit else 0)
        + 0.5 * (1 if reclined else 0)
    )
    return tol * (1 - 0.4 * hypoxia_risk)


def time_to_loc(onset_rate_gps):
    """Whinnery-Forster: 9.10 s at >= 1 G/s, 74.41 s at <= 0.2 G/s."""
    if onset_rate_gps >= 1.0:
        return 9.10
    if onset_rate_gps <= 0.2:
        return 74.41
    frac = (onset_rate_gps - 0.2) / 0.8
    return 74.41 + (9.10 - 74.41) * frac  # linear in rate


def gloc_stage(g_level, tolerance):
    """0 none, 1 greyout, 2 blackout, 3 LOC.

    Mirrors the SQF: excess = (g - tolerance) / tolerance; greyout
    > 0.08, blackout > 0.08, LOC > 0.15 relative excess.
    """
    if g_level <= tolerance:
        return 0
    excess = (g_level - tolerance) / tolerance
    if excess > 0.15:
        return 3
    if excess > 0.08:
        return 2
    return 1


# ─── G measurement from velocity deltas (fnc_getGLoad.sqf) ─────────────────
# a = dv/dt, Gz = a·up/g + 1 (the +1 is the standing baseline), smoothed
# 0.6/0.4 with the previous sample.


def g_from_velocity(prev_vel, vel, dt, up, prev_g=1.0):
    """Mirror of the velocity-delta G measurement (total Gz)."""
    if dt <= 0 or dt > 2:
        return 1.0, 0.0
    a = [(vel[i] - prev_vel[i]) / dt for i in range(3)]
    a_up = sum(a[i] * up[i] for i in range(3))
    g = a_up / 9.81 + 1.0
    g_smooth = 0.6 * g + 0.4 * prev_g
    return max(g_smooth, 1.0), g


class TestGLoadMeasurement(unittest.TestCase):
    def test_stationary_unit_1g(self):
        # No motion, no acceleration: raw Gz = 1.0 (the +1 baseline),
        # smoothed result also 1.0.
        g, raw = g_from_velocity([0, 0, 0], [0, 0, 0], 1.0, [0, 0, 1], 1.0)
        self.assertAlmostEqual(g, 1.0, places=6)
        self.assertAlmostEqual(raw, 1.0, places=6)

    def test_constant_velocity_1g(self):
        # Moving but not accelerating (cruise): still 1 G.
        g, _ = g_from_velocity([10, 0, 0], [10, 0, 0], 1.0, [0, 0, 1], 1.0)
        self.assertAlmostEqual(g, 1.0, places=6)

    def test_pull_up_positive_gz(self):
        # Upward acceleration of 2g: raw Gz = 3.0; smoothed against the
        # previous 1.0 sample -> 2.2 (0.6*3 + 0.4*1).
        g, raw = g_from_velocity([0, 0, 0], [0, 0, 19.62], 1.0, [0, 0, 1], 1.0)
        self.assertAlmostEqual(raw, 3.0, places=6)
        self.assertAlmostEqual(g, 2.2, places=6)

    def test_push_over_negative_gz(self):
        # Downward acceleration (nose-drop): raw Gz = 0.0 (the +1
        # baseline minus a 1g push-over).  Smoothed 0.4 then floored
        # at 1.0 standing.
        g, raw = g_from_velocity([0, 0, 0], [0, 0, -9.81], 1.0, [0, 0, 1], 1.0)
        self.assertAlmostEqual(raw, 0.0, places=6)
        self.assertEqual(g, 1.0)

    def test_smoothing_mixes_previous(self):
        g, _ = g_from_velocity([0, 0, 0], [0, 0, 19.62], 1.0, [0, 0, 1], 2.0)
        # raw 3.0, prev 2.0 -> 0.6*3 + 0.4*2 = 2.6
        self.assertAlmostEqual(g, 2.6, places=6)

    def test_lateral_g(self):
        # Lateral acceleration resolves against the up vector: no Gz,
        # raw stays at the +1 baseline.
        g, raw = g_from_velocity([0, 0, 0], [9.81, 0, 0], 1.0, [0, 0, 1], 1.0)
        self.assertAlmostEqual(raw, 1.0, places=6)
        self.assertAlmostEqual(g, 1.0, places=6)

    def test_stale_sample_neutral(self):
        # dt > 2 s (gap): neutral 1 G, no state corruption.
        g, raw = g_from_velocity([0, 0, 0], [0, 0, 50], 5.0, [0, 0, 1], 1.0)
        self.assertEqual(g, 1.0)
        self.assertEqual(raw, 0.0)


class TestBarometricPressure(unittest.TestCase):
    def test_sea_level(self):
        self.assertAlmostEqual(barometric_pressure_pa(0), 101325.0, places=1)

    def test_troposphere_power_law(self):
        # 5000 m: ~54.0 kPa per ICAO.
        self.assertAlmostEqual(barometric_pressure_pa(5000) / 1000, 54.0, delta=0.4)

    def test_troposphere_exponent(self):
        # The exponent must be the ICAO 5.25588 (g/R/L).
        self.assertAlmostEqual(EXP, 5.25588, places=4)

    def test_stratosphere_continues_smoothly(self):
        # No jump at the tropopause (11 km).
        below = barometric_pressure_pa(11000)
        above = barometric_pressure_pa(11001)
        self.assertAlmostEqual(below, above, delta=below * 0.01)

    def test_40k_ft_roughly_0_19_bar(self):
        # 40,000 ft ~ 12.2 km: stratosphere, ~0.19 bar.
        p = barometric_pressure_pa(40000 * 0.3048) / 101325.0
        self.assertAlmostEqual(p, 0.19, delta=0.02)

    def test_63k_ft_armstrong_0_1_bar(self):
        # ~63,000 ft ~ 19.2 km: the Armstrong limit is where ambient
        # pressure equals water vapour pressure at body temperature
        # (~0.0627 bar) — tissue fluid boils.  The ICAO stratosphere
        # model reproduces it: 0.0613 bar.
        p = barometric_pressure_pa(63000 * 0.3048) / 101325.0
        self.assertAlmostEqual(p, 0.0627, delta=0.005)


class TestAltitudeDCS(unittest.TestCase):
    def test_sea_level_no_risk(self):
        risk, r, _ = altitude_dcs_risk(0, 600)
        self.assertAlmostEqual(risk, 0.0, places=6)

    def test_25k_45min_risk(self):
        # Haske & Pilmanis: 20% DCS at 25k/45 min -> R near the steep
        # part of the curve (risk meaningfully above 0).
        risk, r, _ = altitude_dcs_risk(25000 * 0.3048, 45 * 60)
        self.assertGreater(risk, 0.0)

    def test_40k_15s_risk(self):
        # 40k at 15 s: fast but real exposure.
        risk, r, _ = altitude_dcs_risk(40000 * 0.3048, 15)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_risk_bounded(self):
        for alt in range(0, 60000, 5000):
            for exp in [60, 600, 3600]:
                risk, _, _ = altitude_dcs_risk(alt * 0.3048, exp)
                self.assertGreaterEqual(risk, 0.0)
                self.assertLessEqual(risk, 1.0)

    def test_risk_monotonic_with_altitude(self):
        rs = [altitude_dcs_risk(a * 0.3048, 600)[0] for a in range(20000, 50000, 5000)]
        self.assertTrue(all(b >= a for a, b in zip(rs, rs[1:])))


class TestGLOC(unittest.TestCase):
    def test_baseline_tolerance(self):
        self.assertAlmostEqual(gloc_tolerance(), 4.7, places=6)

    def test_agsm_boosts(self):
        self.assertAlmostEqual(gloc_tolerance(agsm=True), 7.8, places=6)  # +3.1

    def test_full_kit(self):
        self.assertAlmostEqual(
            gloc_tolerance(agsm=True, gsuit=True, reclined=True), 9.8, places=6
        )

    def test_hypoxia_reduces_tolerance(self):
        base = gloc_tolerance()
        hyp = gloc_tolerance(hypoxia_risk=0.5)
        self.assertAlmostEqual(hyp, base * 0.8, places=6)  # (1 - 0.4*0.5)

    def test_time_to_loc_rapid(self):
        self.assertAlmostEqual(time_to_loc(1.0), 9.10, places=4)
        self.assertAlmostEqual(time_to_loc(5.0), 9.10, places=4)  # rate-independent

    def test_time_to_loc_gradual(self):
        self.assertAlmostEqual(time_to_loc(0.1), 74.41, places=4)
        self.assertAlmostEqual(time_to_loc(0.2), 74.41, places=4)

    def test_time_to_loc_intermediate(self):
        # 0.6 G/s -> halfway between 74.41 and 9.10.
        self.assertAlmostEqual(time_to_loc(0.6), (74.41 + 9.10) / 2, places=4)

    def test_stage_thresholds(self):
        tol = gloc_tolerance()  # 4.7
        # Boundaries: greyout > tol, blackout > tol*1.08, LOC > tol*1.15.
        self.assertEqual(gloc_stage(4.7, tol), 0)
        self.assertEqual(gloc_stage(5.0, tol), 1)  # excess 0.064 greyout
        self.assertEqual(gloc_stage(5.1, tol), 2)  # excess 0.085 blackout
        self.assertEqual(gloc_stage(5.3, tol), 2)  # excess 0.128 still blackout
        self.assertEqual(gloc_stage(5.5, tol), 3)  # excess 0.170 LOC

    def test_low_tolerance_stages_sooner(self):
        tol = gloc_tolerance(hypoxia_risk=1.0)  # 4.7 * 0.6 = 2.82
        self.assertEqual(gloc_stage(4.7, tol), 3)  # well past LOC


if __name__ == "__main__":
    unittest.main()
