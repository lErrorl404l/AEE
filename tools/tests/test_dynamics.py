#!/usr/bin/env python3
"""Dynamic (sweep) tests for the continuous physiology models.

Single-point tests verify the maths at one input.  These tests sweep each
model across its full operational range and assert the structural
properties a continuous physical model must hold: monotonicity,
smoothness at piecewise breakpoints, clamp integrity across the whole
domain, periodicity, and physical boundedness.

Method: parameter sweeps across the operational envelope, per the US
Army Research Institute of Environmental Medicine methodology and NATO
STANAG 4370 boundary-condition testing.

Run: python3 -m unittest tools.tests.test_dynamics
"""

import math
import unittest

import numpy as np

from tools.tests.test_sleep_model import (
    AMP,
    FLOOR,
    S_MAX,
    S_MIN,
    WAKEFULNESS_THRESHOLD,
    fatigue_factor,
    sleep_pressure,
)
from tools.tests.test_shooter_stability import (
    cold_factor,
    fatigue_factor_hours,
    heat_factor,
    stability,
)
from tools.tests.test_physiology import TUC_TABLE, cross_sensitivity, hypoxia_risk, tuc
from tools.tests.test_propellant_temp import (
    INIT_SPEED,
    REF_TEMP_C,
    muzzle_velocity_correction,
)


class TestProcessSSweep(unittest.TestCase):
    """Process S (homeostatic sleep pressure) across 0-96 h."""

    def test_rises_monotonically_while_awake(self):
        hours = np.linspace(0, 96, 961)
        s = np.array([sleep_pressure(h, 0, 12, False)[0] for h in hours])
        self.assertTrue(np.all(np.diff(s) > 0), "Process S fell while awake")

    def test_decays_monotonically_while_sleeping(self):
        sleeps = np.linspace(0, 24, 241)
        s = np.array([sleep_pressure(0, sh, 12, True)[0] for sh in sleeps])
        self.assertTrue(np.all(np.diff(s) < 0), "Process S rose while sleeping")

    def test_bounded_across_whole_domain(self):
        for h in np.linspace(0, 96, 97):
            for sh in np.linspace(0, 24, 25):
                s, c, _ = sleep_pressure(h, sh, 12, sh > 0)
                self.assertGreaterEqual(s, S_MIN)
                self.assertLessEqual(s, S_MAX)

    def test_smooth_rise(self):
        # The exponential rise is concave: the slope never increases.
        hours = np.linspace(0, 96, 961)
        s = np.array([sleep_pressure(h, 0, 12, False)[0] for h in hours])
        d = np.diff(s) / np.diff(hours)
        self.assertTrue(np.all(np.diff(d) <= 1e-12), "Process S rise accelerated")


class TestProcessCSweep(unittest.TestCase):
    """Process C (circadian) across 0-23 h."""

    def test_periodic_24h(self):
        c0 = np.array(
            [sleep_pressure(0, 0, h, False)[1] for h in np.linspace(0, 24, 241)]
        )
        c1 = np.array(
            [sleep_pressure(0, 0, h + 24, False)[1] for h in np.linspace(0, 24, 241)]
        )
        np.testing.assert_allclose(c0, c1, atol=1e-12, err_msg="day 1 != day 2")

    def test_bounded_by_amplitude(self):
        for h in np.linspace(0, 23, 230):
            _, c, _ = sleep_pressure(0, 0, h, False)
            self.assertLessEqual(abs(c), AMP + 1e-9)

    def test_peaks_at_18h(self):
        # Sinusoid peaks where (h - PHI)/24 = 0.25 -> h = PHI + 6 = 18.
        vals = [sleep_pressure(0, 0, h, False)[1] for h in range(24)]
        self.assertEqual(vals.index(max(vals)), 18)


class TestFatigueFactorSweep(unittest.TestCase):
    """Fatigue factor across 0-96 h awake (fixed circadian phase)."""

    def test_monotonic_degradation(self):
        hours = np.linspace(0, 96, 961)
        # Fixed local hour -> constant circadian modulation, so the awake
        # trend is purely the linear impairment ramp.
        f = np.array([fatigue_factor(0, 0, 0, h) for h in hours])
        self.assertTrue(np.all(np.diff(f) <= 1e-12), "fatigue rose while awake")

    def test_floor_holds_across_domain(self):
        for h in np.linspace(0, 96, 97):
            f = fatigue_factor(0, 0, 0, h)
            self.assertGreaterEqual(f, FLOOR)
            self.assertLessEqual(f, 1.0)

    def test_floor_is_general_fatigue_floor(self):
        # The general fatigue model (fnc_calculateFatigueFactor) floors at
        # 0.30; the shooter-stability fatigue curve floors at 0.35 (issue
        # #63).  Two models, two floors - both asserted here.
        self.assertEqual(FLOOR, 0.30)
        self.assertEqual(fatigue_factor_hours(96), 0.35)

    def test_circadian_swing_bounded(self):
        # Modulating process C must not push past the floor/ceiling.
        for h in np.linspace(0, 96, 97):
            for phase in np.linspace(0, 24, 25):
                c = sleep_pressure(0, 0, phase, False)[1]
                f = fatigue_factor(0, 0, c, h)
                self.assertGreaterEqual(f, FLOOR)
                self.assertLessEqual(f, 1.0)


class TestColdFactorSweep(unittest.TestCase):
    """Cold dexterity curve across -40 to 50 C."""

    def test_monotonic(self):
        # As it gets warmer, dexterity improves monotonically (never dips).
        temps = np.linspace(-40, 50, 901)
        c = np.array([cold_factor(t) for t in temps])
        self.assertTrue(np.all(np.diff(c) >= -1e-12), "cold factor dipped on warming")

    def test_no_penalty_above_15(self):
        for t in np.linspace(15, 50, 36):
            self.assertEqual(cold_factor(t), 1.0)

    def test_full_penalty_at_minus_20(self):
        self.assertEqual(cold_factor(-20), 0.3)

    def test_bounded(self):
        for t in np.linspace(-40, 50, 91):
            c = cold_factor(t)
            self.assertGreaterEqual(c, 0.3)
            self.assertLessEqual(c, 1.0)


class TestHeatFactorSweep(unittest.TestCase):
    """Heat vigilance curve across WBGT 0-59."""

    def test_monotonic(self):
        wbgts = np.linspace(0, 59, 591)
        h = np.array([heat_factor(w) for w in wbgts])
        self.assertTrue(np.all(np.diff(h) <= 1e-12), "heat factor rose with WBGT")

    def test_no_penalty_below_29(self):
        for w in np.linspace(0, 29, 30):
            self.assertEqual(heat_factor(w), 1.0)

    def test_floor_at_42(self):
        for w in np.linspace(42, 59, 18):
            self.assertEqual(heat_factor(w), 0.6)

    def test_bounded(self):
        for w in np.linspace(0, 59, 60):
            h = heat_factor(w)
            self.assertGreaterEqual(h, 0.6)
            self.assertLessEqual(h, 1.0)


class TestStabilitySweep(unittest.TestCase):
    """Shooter stability geometric mean over the joint domain."""

    def test_bounded_whole_domain(self):
        for c in np.linspace(-40, 50, 10):
            for w in np.linspace(0, 59, 10):
                for h in np.linspace(0, 96, 10):
                    s = stability(c, w, h)
                    self.assertGreaterEqual(s, 0.2)
                    self.assertLessEqual(s, 1.0)

    def test_monotonic_in_each_factor(self):
        # Holding two factors fixed, stability must improve as each factor
        # improves: rises as it warms, falls as WBGT rises, falls with
        # hours awake.
        cs = [stability(c, 20, 8) for c in np.linspace(-40, 50, 91)]
        self.assertTrue(np.all(np.diff(cs) >= -1e-12), "stability dipped on warming")
        hs = [stability(20, w, 8) for w in np.linspace(0, 59, 60)]
        self.assertTrue(np.all(np.diff(hs) <= 1e-12), "stability rose with WBGT")
        fs = [stability(20, 20, h) for h in np.linspace(0, 96, 97)]
        self.assertTrue(np.all(np.diff(fs) <= 1e-12), "stability rose with hours awake")

    def test_ideal_conditions_are_optimal(self):
        self.assertAlmostEqual(stability(25, 20, 8), 1.0, places=4)


class TestHypoxiaSweep(unittest.TestCase):
    """Hypoxia risk across altitude 0-12000 m, exposure 0-3600 s."""

    def test_risk_bounded_whole_domain(self):
        for alt in np.linspace(0, 12000, 25):
            for exp in np.linspace(0, 3600, 25):
                r = hypoxia_risk(alt, exp)
                self.assertGreaterEqual(r, 0.0)
                self.assertLessEqual(r, 1.0)

    def test_risk_rises_with_exposure(self):
        for alt in [6000, 8000, 10000]:
            rs = [hypoxia_risk(alt, e) for e in np.linspace(0, 3600, 61)]
            self.assertTrue(
                np.all(np.diff(rs) >= 0), f"risk fell with exposure at {alt} m"
            )

    def test_risk_rises_with_altitude(self):
        for exp in [300, 600, 1200]:
            rs = [hypoxia_risk(a, exp) for a in np.linspace(5000, 11000, 61)]
            self.assertTrue(
                np.all(np.diff(rs) >= 0), f"risk fell with altitude at {exp} s"
            )

    def test_tuc_continuous_at_breakpoints(self):
        # No value jump at any table row: interpolating to exactly a row
        # altitude must equal that row's TUC (piecewise-linear continuity).
        for alt, expected in TUC_TABLE:
            self.assertAlmostEqual(
                tuc(alt), expected, places=6, msg=f"TUC jumps at {alt} m"
            )

    def test_tuc_table_slope_consistent(self):
        # Steepness decreases monotonically upward: the sharpest onset is
        # just above the safe floor, flattening toward the 15 s cap.
        # A re-entrant bend (steep-shallow-steep) would be unphysical.
        slopes = []
        for i in range(len(TUC_TABLE) - 1):
            lo = TUC_TABLE[i]
            hi = TUC_TABLE[i + 1]
            slopes.append((hi[1] - lo[1]) / (hi[0] - lo[0]))
        for a, b in zip(slopes, slopes[1:]):
            self.assertLess(abs(b), abs(a), "TUC steepness bends back on itself")


class TestCrossSensitivitySweep(unittest.TestCase):
    """Cross-sensitivity over the (dehydration, hypoxia) 0-1 grid."""

    def test_bounded_whole_grid(self):
        for d in np.linspace(0, 1, 21):
            for h in np.linspace(0, 1, 21):
                eff_d, eff_h = cross_sensitivity(d, h)
                self.assertGreaterEqual(eff_d, 0.0)
                self.assertLessEqual(eff_d, 1.0)
                self.assertGreaterEqual(eff_h, 0.0)
                self.assertLessEqual(eff_h, 1.0)

    def test_amplifies_both_directions(self):
        for d in np.linspace(0, 1, 11):
            for h in np.linspace(0, 1, 11):
                eff_d, eff_h = cross_sensitivity(d, h)
                self.assertGreaterEqual(
                    eff_h, h, "hypoxia not amplified by dehydration"
                )
                self.assertGreaterEqual(
                    eff_d, d, "dehydration not amplified by hypoxia"
                )

    def test_scale_zero_passthrough(self):
        for d in np.linspace(0, 1, 11):
            for h in np.linspace(0, 1, 11):
                eff_d, eff_h = cross_sensitivity(d, h, scale=0)
                self.assertAlmostEqual(eff_d, d)
                self.assertAlmostEqual(eff_h, h)

    def test_clamps_at_1(self):
        eff_d, eff_h = cross_sensitivity(1.0, 1.0)
        self.assertEqual(eff_d, 1.0)
        self.assertEqual(eff_h, 1.0)


class TestPropellantSweep(unittest.TestCase):
    """Muzzle velocity correction across -40 to 50 C."""

    def test_bounded_whole_domain(self):
        for ammo, speed in INIT_SPEED.items():
            for t in np.linspace(-40, 50, 91):
                corr, _ = muzzle_velocity_correction(ammo, speed, t)
                self.assertGreaterEqual(corr, 0.85)
                self.assertLessEqual(corr, 1.15)

    def test_zero_crossing_at_21c(self):
        # At the EPVAT conditioning temperature the correction is 1.0.
        for ammo, speed in INIT_SPEED.items():
            corr, _ = muzzle_velocity_correction(ammo, speed, REF_TEMP_C)
            self.assertAlmostEqual(corr, 1.0, places=6)

    def test_monotonic_with_temperature(self):
        for ammo, speed in INIT_SPEED.items():
            corrs = [
                muzzle_velocity_correction(ammo, speed, t)[0]
                for t in np.linspace(-40, 50, 91)
            ]
            # Corrections rise with temperature once past the clamp tail.
            self.assertTrue(np.all(np.diff(corrs) >= -1e-9), f"{ammo} non-monotonic")


if __name__ == "__main__":
    unittest.main()
