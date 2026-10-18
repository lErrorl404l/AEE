#!/usr/bin/env python3
"""G-LOC and altitude DCS tests (issue #135).

Mirrors of fnc_calculateGLOC.sqf and fnc_calculateAltitudeDCS.sqf: the
Whinnery-Forster time-to-LOC onset model, ICAO barometric pressure,
and the ZH-L16C-as-altitude-DCS solver (R = tissue N2 / ambient).

Run: python3 -m unittest tools.tests.test_gloc
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402


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
# The risk is the exposure-integrated hazard, not the instantaneous ratio
# (issue #280):
#   severity = max(0, (R - 1.5) / 0.5)   R = max tissue N2 / pAmb
#   hazard   = severity ** HAZARD_EXP     per second, at full severity
#   risk     = 1 - exp(-sum(hazard * dt) / CALIB_SEC)
# The exponent and the time constant are fitted to the two Haske &
# Pilmanis 2002 anchors: 20% at 25,000 ft / 45 min and 20% at
# 22,000 ft / 200 min.  The interval is walked in sub-steps of at most
# SUBSTEP_S seconds (bounded by MAX_SUBSTEPS), so the mirror matches the
# SQF quadrature.

# ZH-L16C compartment half-times (minutes) and N2 M-value a (surface).
HAZARD_EXP = 1.2
CALIB_SEC = 10352.0
SUBSTEP_S = 30.0
MAX_SUBSTEPS = 120
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
    """Exposure-integrated DCS risk over exposure_s seconds."""
    if tissues is None:
        tissues = fresh_tissues()
    p_amb_bar = barometric_pressure_pa(alt_m) / 100000.0
    step_s = max(exposure_s, 0.0)
    n_sub = min(MAX_SUBSTEPS, math.ceil(step_s / SUBSTEP_S))
    sub_s = step_s / n_sub if n_sub > 0 else 0.0
    dose = 0.0
    for _ in range(n_sub):
        r = max(tissues[:16]) / p_amb_bar if p_amb_bar > 0 else 0.0
        severity = (r - 1.5) / 0.5
        if severity > 0:
            dose += (severity**HAZARD_EXP) * sub_s
        tissues = zh16c_step(tissues, None, 0.79, sub_s, p_amb_override=p_amb_bar)
    r_max = max(tissues[:16]) / p_amb_bar if p_amb_bar > 0 else 0.0
    risk = max(0.0, min(1.0, 1.0 - math.exp(-dose / CALIB_SEC)))
    return risk, r_max, tissues


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


def gloc_next_exposure(g_level, tolerance, exposure_s, dt_s):
    """The exposure at the end of a step: held above tolerance, else reset."""
    if g_level > tolerance:
        return exposure_s + dt_s
    return 0.0


def gloc_stage(g_level, tolerance, exposure_s=0.0, time_to_loc_s=9.10):
    """0 none, 1 greyout, 2 blackout, 3 LOC.

    Mirrors the SQF: the instantaneous excess sets the visual warning
    (greyout above 0.08 relative excess, blackout above that), and LOC is
    reached only once the exposure held above tolerance passes timeToLoc.
    (issue #290: LOC used to fire on the first tick above tolerance, so the
    warning window was zero.)
    """
    if g_level <= tolerance:
        return 0
    excess = (g_level - tolerance) / tolerance
    if exposure_s >= time_to_loc_s:
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

    def test_25k_1s_step_is_low_risk(self):
        # One tick at 25,000 ft. The exposure is one second, so the risk is
        # far below the 45-minute anchor and not the 0.94 the instantaneous
        # supersaturation ratio reported (#280).
        risk, _, _ = altitude_dcs_risk(25000 * 0.3048, 1)
        self.assertLess(risk, 0.05)

    def test_25k_2700s_approaches_the_anchor(self):
        # Haske & Pilmanis 2002: 20% DCS at 25,000 ft for 45 min (2700 s).
        risk, _, _ = altitude_dcs_risk(25000 * 0.3048, 2700)
        self.assertAlmostEqual(risk, 0.20, delta=0.02)

    def test_22k_12000s_approaches_the_anchor(self):
        # The second cited anchor: 22,000 ft for 200 min (12,000 s).
        risk, _, _ = altitude_dcs_risk(22000 * 0.3048, 12000)
        self.assertAlmostEqual(risk, 0.20, delta=0.02)

    def test_exposure_composes_across_ticks(self):
        # The engine calls the kernel once per second, so 2700 one-second
        # steps must accumulate the exposure of one 2700 s step.
        tissues = fresh_tissues()
        compounded = 0.0
        for _ in range(2700):
            risk, _, tissues = altitude_dcs_risk(25000 * 0.3048, 1, tissues)
            compounded = 1.0 - (1.0 - compounded) * (1.0 - risk)
        single, _, _ = altitude_dcs_risk(25000 * 0.3048, 2700)
        self.assertAlmostEqual(compounded, single, delta=0.01)

    def test_no_step_at_the_gate(self):
        # The caller gates at ~21,000 ft (6400 m). One tick there is a small
        # risk, not the 0.32 the ratio gave (#280).
        for alt_ft in (21000, 21200, 25000):
            risk, _, _ = altitude_dcs_risk(alt_ft * 0.3048, 1)
            self.assertLess(risk, 0.001)

    def test_risk_keeps_rising_above_the_curve_shoulder(self):
        # Severity reaches 1.0 at R = 2.0, but the hazard keeps growing with
        # altitude: the dose is the excess supersaturation, not a clamp.
        low, _, _ = altitude_dcs_risk(30000 * 0.3048, 2700)
        high, _, _ = altitude_dcs_risk(35000 * 0.3048, 2700)
        self.assertGreater(high, low)

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
        # Below tolerance there is no stage; above it the instantaneous excess
        # sets greyout, then blackout.
        self.assertEqual(gloc_stage(4.7, tol), 0)
        self.assertEqual(gloc_stage(5.0, tol), 1)  # excess 0.064 greyout
        self.assertEqual(gloc_stage(5.1, tol), 2)  # excess 0.085 blackout
        self.assertEqual(gloc_stage(5.3, tol), 2)  # excess 0.128 still blackout
        # LOC is a time-to-event, not an instantaneous threshold (issue #290).
        self.assertEqual(gloc_stage(5.5, tol), 2)  # excess 0.170, no exposure
        self.assertEqual(gloc_stage(5.5, tol, exposure_s=9.10), 3)

    def test_loc_needs_the_exposure_to_accumulate(self):
        tol = gloc_tolerance()
        exposure = 0.0
        # Ten one-second steps just above tolerance never reach LOC...
        for _ in range(9):
            exposure = gloc_next_exposure(5.5, tol, exposure, 1.0)
            self.assertLess(gloc_stage(5.5, tol, exposure), 3)
        # ... and the tenth does (rapid onset, time to LOC 9.10 s).
        exposure = gloc_next_exposure(5.5, tol, exposure, 1.0)
        self.assertEqual(gloc_stage(5.5, tol, exposure), 3)

    def test_below_tolerance_resets_the_exposure(self):
        tol = gloc_tolerance()
        exposure = gloc_next_exposure(5.5, tol, 8.0, 1.0)
        self.assertAlmostEqual(exposure, 9.0, places=6)
        self.assertAlmostEqual(gloc_next_exposure(4.0, tol, exposure, 1.0), 0.0)

    def test_low_tolerance_lowers_the_stage_threshold(self):
        tol = gloc_tolerance(hypoxia_risk=1.0)  # 4.7 * 0.6 = 2.82
        self.assertEqual(gloc_stage(4.7, tol), 2)  # well past tolerance, no exposure
        self.assertEqual(
            gloc_stage(4.7, tol, exposure_s=9.10), 3
        )  # LOC after the latency


if __name__ == "__main__":
    unittest.main()


class TestAltitudeDcsCallSite(unittest.TestCase):
    """The caller must pass [altitude, tissues, dt] in the kernel's order.

    Passed as [alt, 1, tissues], the params type check discarded the tissue
    array, so the nitrogen state reset to the surface baseline every second
    and the exposure had no memory.
    """

    def test_call_matches_the_params_order(self):
        from pathlib import Path
        import re

        addons = Path(__file__).resolve().parents[2] / "addons" / "altitude"
        kernel = next(addons.rglob("fnc_calculateAltitudeDCS.sqf")).read_text(
            encoding="utf-8"
        )
        params = re.search(r"params \[(.*?)\];", kernel, re.S).group(1)
        names = re.findall(r'\["(_\w+)"', params)
        self.assertEqual(names[:3], ["_altM", "_tissues", "_dtSec"])
        caller = (addons / "XEH_postInit.sqf").read_text(encoding="utf-8")
        # The step is the measured interval, not a hardcoded 1 s (issue #292).
        self.assertIn(
            "[_altM, _tissues, _dtSec] call FUNC(calculateAltitudeDCS)", caller
        )
        self.assertNotIn("[_altM, _tissues, 1] call FUNC(calculateAltitudeDCS)", caller)


class TestGlocKernelExecutes(unittest.TestCase):
    """fnc_calculateGLOC runs from the real SQF (issue #290).

    The kernel integrates the exposure held above tolerance and reaches LOC
    only after timeToLoc.  Before the fix the stage jumped to LOC on the first
    tick above 1.15 x tolerance, so the warning window was zero.
    """

    KERNEL = (
        Path(__file__).resolve().parents[2]
        / "addons"
        / "altitude"
        / "functions"
        / "altitude"
        / "fnc_calculateGLOC.sqf"
    )

    def _call(self, g, exposure=0.0, dt=0.0):
        return run_sqf(self.KERNEL, [g, 3, 0, 0, 0, 0, exposure, dt])

    def test_params_carry_the_exposure_and_step(self):
        params = re.search(
            r"params \[(.*?)\];", self.KERNEL.read_text(encoding="utf-8"), re.S
        ).group(1)
        names = re.findall(r'\["(_\w+)"', params)
        self.assertEqual(names[-2:], ["_exposureSec", "_dtSec"])

    def test_high_g_does_not_lose_consciousness_at_once(self):
        stage, t_loc, tol, exposure = self._call(5.6, 0.0, 1.0)
        self.assertEqual(stage, 2)  # blackout, not LOC
        self.assertAlmostEqual(t_loc, 9.10, places=4)
        self.assertAlmostEqual(tol, 4.7, places=4)
        self.assertAlmostEqual(exposure, 1.0, places=6)

    def test_loc_after_the_whinnery_forster_time(self):
        stage, _, _, exposure = self._call(5.6, 9.0, 1.0)
        self.assertAlmostEqual(exposure, 10.0, places=6)
        self.assertEqual(stage, 3)

    def test_exposure_resets_below_tolerance(self):
        stage, _, _, exposure = self._call(2.0, 30.0, 1.0)
        self.assertEqual(exposure, 0)
        self.assertEqual(stage, 0)

    def test_the_step_scales_the_exposure(self):
        _, _, _, one = self._call(5.6, 0.0, 1.0)
        _, _, _, two = self._call(5.6, 0.0, 2.0)
        self.assertAlmostEqual(two, 2.0 * one, places=6)


class TestLoopUsesTheRealInterval(unittest.TestCase):
    """The physiology loop integrates over the real elapsed time (issue #292).

    CBA's per-frame handler passes [_args, _handle] and no delta, so the loop
    measures the wall-clock gap instead of assuming a 1 s cadence.
    """

    def setUp(self):
        self.caller = (
            Path(__file__).resolve().parents[2]
            / "addons"
            / "altitude"
            / "XEH_postInit.sqf"
        ).read_text(encoding="utf-8")

    def test_the_interval_is_measured(self):
        self.assertIn("diag_tickTime", self.caller)
        self.assertIn("_dtSec = _now -", self.caller)

    def test_the_measured_interval_reaches_both_integrators(self):
        self.assertIn("_exposurePrev, _dtSec] call FUNC(calculateGLOC)", self.caller)
        self.assertIn(
            "[_altM, _tissues, _dtSec] call FUNC(calculateAltitudeDCS)", self.caller
        )


class TestGlocVisualConsumer(unittest.TestCase):
    """The published G-LOC stage has a consumer (issue #293).

    Before the fix the stage was written and never read except by the
    diagnostic dump, so the whole feature was inert.
    """

    ALTITUDE = Path(__file__).resolve().parents[2] / "addons" / "altitude"

    def test_the_loop_applies_the_stage(self):
        caller = (self.ALTITUDE / "XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("[] call FUNC(applyGLOCEffects)", caller)

    def test_the_consumer_reads_the_stage_and_owns_a_radial_blur(self):
        src = (
            self.ALTITUDE / "functions" / "altitude" / "fnc_applyGLOCEffects.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("getVariable [QGVAR(gLocStage), 0]", src)
        self.assertIn('"RadialBlur"', src)
        # The optics arbiter owns these four; the consumer must not create a
        # second owner of any of them.  Comments may name them, so test code.
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        code = "\n".join(line.split("//", 1)[0] for line in code.splitlines())
        for owned in (
            "ColorCorrections",
            "DynamicBlur",
            "ChromAberration",
            "FilmGrain",
        ):
            self.assertNotIn(owned, code)

    def test_the_consumer_is_prepped(self):
        prep = (self.ALTITUDE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREPS(altitude,applyGLOCEffects)", prep)


class TestDiveStateSplice(unittest.TestCase):
    """The altitude DCS tick keeps the FULL dive state (issue #289).

    _entry was reassigned to the 32-element tissue result before the splice
    loop, so the loop copied the result onto itself and the 38-element dive
    state was truncated, losing fN2/fHe/fO2, the last depth, the DCS
    accumulator and the ascent-violation count.
    """

    ROOT = Path(__file__).resolve().parents[2]

    def test_the_dive_state_is_38_slots(self):
        src = next(
            (self.ROOT / "addons" / "dive").rglob("fnc_getDiveState.sqf")
        ).read_text(encoding="utf-8")
        self.assertIn("0..15", src)  # 16 N2 compartments
        self.assertIn("16..31", src)  # 16 He compartments
        self.assertIn("37", src)  # the last of the 38 slots

    def test_the_splice_does_not_reassign_the_entry(self):
        caller = (self.ROOT / "addons" / "altitude" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'for "_i" from 0 to 31 do { _entry set [_i, _res select 2 select _i]; };',
            caller,
        )
        self.assertNotIn("_entry = _res select 2;", caller)
