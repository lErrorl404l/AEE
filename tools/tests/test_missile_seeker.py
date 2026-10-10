#!/usr/bin/env python3
"""Missile seeker physics verification (issue #131).

Executes the ACTUAL shipped SQF kernels through tools/tests/sqf_lite.py.
A hand-transcribed mirror is NOT used: the SQF file itself is the subject
under test, so a change to a kernel changes what this suite runs.

The kernels and their sources:
  fnc_calculateIRSeekerRange   R = sqrt(J*tau/(NEFD*SNR_min))  Holst, SPIE 2017
  fnc_calculateRadarRange      R = (Pt*G^2*lambda^2*sigma/((4pi)^3*Pmin))^(1/4)
                               Skolnik, Radar Handbook 3rd ed.
  fnc_calculateRadarNoiseFloor Pmin = k*T0*B*Fn*SNR_min        Skolnik
  fnc_calculateChaffCrossSection sigma = N*0.17*lambda^2       Van Vleck 1947
  fnc_calculateFlareIntensity  J(t) = J0*exp(-t/tau)           shape UNSOURCED
  fnc_calculateProportionalNavigation a = N'*Vc*lambda_dot     Zarchan
  fnc_calculateLosRate         acos(u1.u2)/dt
  fnc_calculateNoEscapeZone    min(Rk, Rs)*margin              margin UNSOURCED
  fnc_calculateSeekerTrack     hysteresis gate                 half factor UNSOURCED
  fnc_calculateCountermeasureEffectiveness  seduction gate     bases UNSOURCED
  fnc_calculateSeekerState     state machine

Run: python3 -m unittest tools.tests.test_missile_seeker
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf

REPO = Path(__file__).resolve().parents[2]

IR_RANGE = REPO / "addons/thermal/functions/sensor/fnc_calculateIRSeekerRange.sqf"
FLARE = REPO / "addons/thermal/functions/sensor/fnc_calculateFlareIntensity.sqf"
NOISE = REPO / "addons/radio/functions/fnc_calculateRadarNoiseFloor.sqf"
RADAR = REPO / "addons/radio/functions/fnc_calculateRadarRange.sqf"
# The seeker-facing radar kernels delegate to the canonical #104 kernels
# (addons/radio/functions/radar/).  The harness resolves FUNC(x) through the
# bound globals, so wire the delegation targets here.
CANON_RANGE = REPO / "addons/radio/functions/radar/fnc_radarRangeEquation.sqf"
CANON_NOISE = REPO / "addons/radio/functions/radar/fnc_radarNoiseFloor.sqf"


def run_radar(args):
    """Run the seeker radar-range wrapper, wiring FUNC to the canonical kernel."""
    return run_sqf(
        RADAR,
        args,
        globals_={
            "__FUNC__radarRangeEquation": lambda *a: run_sqf(CANON_RANGE, list(a))
        },
    )


def run_noise(args):
    """Run the seeker noise-floor wrapper, wiring FUNC to the canonical kernel."""
    return run_sqf(
        NOISE,
        args,
        globals_={"__FUNC__radarNoiseFloor": lambda *a: run_sqf(CANON_NOISE, list(a))},
    )


CHAFF = REPO / "addons/radio/functions/fnc_calculateChaffCrossSection.sqf"
PN = REPO / "addons/ballistics/functions/fnc_calculateProportionalNavigation.sqf"
TRACK = REPO / "addons/ballistics/functions/fnc_calculateSeekerTrack.sqf"
CM = REPO / "addons/ballistics/functions/fnc_calculateCountermeasureEffectiveness.sqf"
LOSRATE = REPO / "addons/ballistics/functions/fnc_calculateLosRate.sqf"
NEZ = REPO / "addons/ballistics/functions/fnc_calculateNoEscapeZone.sqf"
STATE = REPO / "addons/ballistics/functions/fnc_calculateSeekerState.sqf"


class TestRadarRange(unittest.TestCase):
    def test_issue_vector_46km(self):
        # 1 MW, G=1000, lambda=0.03 m, sigma=1 m2, Pmin=1e-13 W -> 46.1 km.
        r = run_radar([1e6, 1000, 0.03, 1, 1e-13])
        self.assertAlmostEqual(r, 46150, delta=150)

    def test_sigma_quarter_law(self):
        # 100x RCS multiplies the range by 100^(1/4) = 3.162.
        r1 = run_radar([1e6, 1000, 0.03, 1, 1e-13])
        r100 = run_radar([1e6, 1000, 0.03, 100, 1e-13])
        self.assertAlmostEqual(r100 / r1, 100**0.25, places=6)

    def test_power_quarter_law(self):
        # Doubling the power multiplies the range by 2^(1/4).
        r1 = run_radar([1e6, 1000, 0.03, 1, 1e-13])
        r2 = run_radar([2e6, 1000, 0.03, 1, 1e-13])
        self.assertAlmostEqual(r2 / r1, 2**0.25, places=6)

    def test_zero_argument_refused(self):
        self.assertEqual(run_radar([0, 1000, 0.03, 1, 1e-13]), 0)


class TestRadarNoiseFloor(unittest.TestCase):
    def test_reference_value(self):
        # k*T0*B*Fn*SNR = 1.38e-23 * 290 * 1e6 * 3 * 20 (the canonical #104
        # noise-floor kernel's Boltzmann constant).
        p = run_noise([1e6, 3, 20])
        self.assertAlmostEqual(p, 1.38e-23 * 290 * 1e6 * 3 * 20, places=28)

    def test_scales_with_bandwidth(self):
        p1 = run_noise([1e6, 3, 20])
        p2 = run_noise([2e6, 3, 20])
        self.assertAlmostEqual(p2 / p1, 2.0, places=6)

    def test_zero_bandwidth_refused(self):
        self.assertEqual(run_noise([0, 3, 20]), 0)


class TestChaffCrossSection(unittest.TestCase):
    def test_one_dipole_x_band(self):
        # lambda = 0.03 m -> 0.17 * 9e-4 = 1.53e-4 m2.
        s = run_sqf(CHAFF, [1, 0.03])
        self.assertAlmostEqual(s, 1.53e-4, places=9)

    def test_fighter_return_needs_39000_dipoles(self):
        # A 6 m2 return from 0.17*lambda^2 dipoles needs ~39,000.
        s = run_sqf(CHAFF, [39000, 0.03])
        self.assertAlmostEqual(s, 6.0, delta=0.1)

    def test_dipole_count_for_rr188(self):
        # RR-188 = 835 m2 -> N = 835 / 1.53e-4 = 5.46e6 dipoles.
        s = run_sqf(CHAFF, [835 / (0.17 * 0.03 * 0.03), 0.03])
        self.assertAlmostEqual(s, 835, delta=1)

    def test_zero_count_refused(self):
        self.assertEqual(run_sqf(CHAFF, [0, 0.03]), 0)


class TestIRSeekerRange(unittest.TestCase):
    def test_point_source_range(self):
        # J=100 W/sr, tau=0.8, NEFD=1e-9 W/m2, SNR=5 -> sqrt(80/5e-9).
        r = run_sqf(IR_RANGE, [100, 0.8, 1e-9, 5])
        self.assertAlmostEqual(r, (100 * 0.8 / (1e-9 * 5)) ** 0.5, places=3)

    def test_range_scales_as_sqrt_j(self):
        r1 = run_sqf(IR_RANGE, [100, 1, 1e-9, 5])
        r4 = run_sqf(IR_RANGE, [400, 1, 1e-9, 5])
        self.assertAlmostEqual(r4 / r1, 2.0, places=6)

    def test_zero_contrast_refused(self):
        self.assertEqual(run_sqf(IR_RANGE, [0, 1, 1e-9, 5]), 0)

    def test_zero_nefd_refused(self):
        self.assertEqual(run_sqf(IR_RANGE, [100, 1, 0, 5]), 0)


class TestFlareIntensity(unittest.TestCase):
    def test_peak_at_ignition(self):
        self.assertAlmostEqual(run_sqf(FLARE, [1000, 2, 0]), 1000, places=6)

    def test_one_time_constant(self):
        # J(2) = 1000 * exp(-1) = 367.879.
        j = run_sqf(FLARE, [1000, 2, 2])
        self.assertAlmostEqual(j, 1000 * 2.718281828459045**-1, places=3)

    def test_decays_monotonically(self):
        j1 = run_sqf(FLARE, [1000, 2, 1])
        j2 = run_sqf(FLARE, [1000, 2, 5])
        self.assertGreater(j1, j2)

    def test_zero_tau_refused(self):
        self.assertEqual(run_sqf(FLARE, [1000, 0, 1]), 0)


class TestProportionalNavigation(unittest.TestCase):
    def test_command_value(self):
        # a = N' * Vc * lambda_dot = 4 * 1000 * 0.05 = 200.
        self.assertAlmostEqual(run_sqf(PN, [4, 1000, 0.05, 0]), 200, places=6)

    def test_minimum_nav_constant(self):
        # N' = 3 is the theoretical minimum.
        self.assertAlmostEqual(run_sqf(PN, [3, 1000, 0.05, 0]), 150, places=6)

    def test_clamped_to_max_accel(self):
        self.assertAlmostEqual(run_sqf(PN, [4, 1000, 1, 100]), 100, places=6)

    def test_negative_clamped(self):
        self.assertAlmostEqual(run_sqf(PN, [4, 1000, -1, 100]), -100, places=6)


class TestLosRate(unittest.TestCase):
    def test_quarter_turn_over_half_second(self):
        # 90 deg over 0.5 s = (pi/2)/0.5 rad/s.
        r = run_sqf(LOSRATE, [[1, 0, 0], [0, 1, 0], 0.5])
        self.assertAlmostEqual(r, 3.141592653589793, places=6)

    def test_no_rotation_zero_rate(self):
        self.assertAlmostEqual(
            run_sqf(LOSRATE, [[1, 0, 0], [1, 0, 0], 0.1]), 0, places=9
        )

    def test_zero_dt_refused(self):
        self.assertEqual(run_sqf(LOSRATE, [[1, 0, 0], [0, 1, 0], 0]), 0)


class TestNoEscapeZone(unittest.TestCase):
    def test_smaller_range_scaled(self):
        # min(10000, 8000) * 0.8 = 6400.
        self.assertAlmostEqual(run_sqf(NEZ, [10000, 8000, 0.8]), 6400, places=6)

    def test_zero_range_no_zone(self):
        self.assertEqual(run_sqf(NEZ, [10000, 0, 0.8]), 0)


class TestSeekerTrack(unittest.TestCase):
    def test_acquire_at_threshold(self):
        self.assertTrue(run_sqf(TRACK, [1.0, 1.0, True, 0, 0, False]))

    def test_below_threshold_not_acquired(self):
        self.assertFalse(run_sqf(TRACK, [0.9, 1.0, True, 0, 0, False]))

    def test_hysteresis_holds_at_half(self):
        # Already tracking: 0.5 holds, just below does not.
        self.assertTrue(run_sqf(TRACK, [0.5, 1.0, True, 0, 0, True]))
        self.assertFalse(run_sqf(TRACK, [0.49, 1.0, True, 0, 0, True]))

    def test_out_of_fov_not_tracked(self):
        self.assertFalse(run_sqf(TRACK, [10, 1.0, False, 0, 0, True]))

    def test_rate_limit_breaks_track(self):
        self.assertFalse(run_sqf(TRACK, [10, 1.0, True, 2.0, 1.0, True]))


class TestCountermeasureEffectiveness(unittest.TestCase):
    def test_stronger_decoy_seduces(self):
        self.assertAlmostEqual(run_sqf(CM, [10, 5, 0.7]), 0.7, places=6)

    def test_weaker_decoy_no_seduction(self):
        self.assertEqual(run_sqf(CM, [4, 5, 0.7]), 0)

    def test_equal_signature_no_seduction(self):
        self.assertEqual(run_sqf(CM, [5, 5, 0.7]), 0)

    def test_probability_clamped(self):
        self.assertEqual(run_sqf(CM, [10, 5, 5]), 1)


class TestSeekerState(unittest.TestCase):
    def test_pre_launch_stays(self):
        self.assertEqual(run_sqf(STATE, [0, 1000, True, 0, 2, 3000, 50]), 0)

    def test_boost_to_midcourse(self):
        self.assertEqual(run_sqf(STATE, [1, 5000, True, 3, 2, 3000, 50]), 2)
        self.assertEqual(run_sqf(STATE, [1, 5000, True, 1, 2, 3000, 50]), 1)

    def test_midcourse_to_terminal(self):
        self.assertEqual(run_sqf(STATE, [2, 2000, True, 0, 2, 3000, 50]), 3)

    def test_midcourse_lock_loss_ballistic(self):
        self.assertEqual(run_sqf(STATE, [2, 5000, False, 0, 2, 3000, 50]), 5)

    def test_terminal_lock_loss_lost(self):
        self.assertEqual(run_sqf(STATE, [3, 5000, False, 0, 2, 3000, 50]), 6)

    def test_impact_wins(self):
        self.assertEqual(run_sqf(STATE, [3, 40, True, 0, 2, 3000, 50]), 4)
        self.assertEqual(run_sqf(STATE, [2, 40, True, 0, 2, 3000, 50]), 4)

    def test_terminal_stays_while_tracked(self):
        self.assertEqual(run_sqf(STATE, [3, 2000, True, 0, 2, 3000, 50]), 3)

    def test_absorbing_states(self):
        for s in (4, 5, 6):
            self.assertEqual(run_sqf(STATE, [s, 100, True, 0, 2, 3000, 50]), s)


if __name__ == "__main__":
    unittest.main()
