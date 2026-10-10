#!/usr/bin/env python3
"""Reference checks for the internal-wave and thermocline model (issue #17).

Runs the REAL SQF kernels through the sqf_lite harness (issue #204): the
two-layer internal-wave phase speed, the linear seawater equation of state,
the tanh thermocline profile, and the internal-tide displacement.

Run: python3 -m unittest tools.tests.test_internal_waves -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ADDON = Path(__file__).resolve().parents[2] / "addons" / "maritime" / "functions"

DENSITY = ADDON / "fnc_calculateSeawaterDensity.sqf"
SPEED = ADDON / "fnc_calculateInternalWaveSpeed.sqf"
PROFILE = ADDON / "fnc_calculateThermoclineTemperature.sqf"
TIDE = ADDON / "fnc_calculateInternalTide.sqf"


def density(temp, sal=35.0, rho0=1027.8, alpha=1.7e-4, beta=7.6e-4, t0=4.0, s0=35.0):
    return run_sqf(DENSITY, [temp, sal, rho0, alpha, beta, t0, s0])


def wave_speed(rho1, rho2, h1, h2, g=9.80665):
    return run_sqf(SPEED, [rho1, rho2, h1, h2, g])


def profile(depth, t_surf=15.0, t_deep=4.0, z_tc=50.0, width=30.0):
    return run_sqf(PROFILE, [depth, t_surf, t_deep, z_tc, width])


def internal_tide(amp, period, time, speed, h1, h2):
    return run_sqf(TIDE, [amp, period, time, speed, h1, h2])


class TestSeawaterDensity(unittest.TestCase):
    def test_reference_state(self):
        # At the reference (4 degC, 35 psu) the density is rho0.
        self.assertAlmostEqual(density(4.0), 1027.8, places=6)

    def test_warmer_is_lighter(self):
        self.assertLess(density(20.0), density(4.0))

    def test_linear_in_temperature(self):
        # rho falls by rho0 * alpha per degC (Gill 1982 linear EOS).
        drop = density(4.0) - density(5.0)
        self.assertAlmostEqual(drop, 1027.8 * 1.7e-4, places=9)


class TestInternalWaveSpeed(unittest.TestCase):
    def test_matches_the_two_layer_formula(self):
        rho1, rho2, h1, h2, g = 1025.0, 1027.8, 50.0, 1000.0, 9.80665
        c, gp = wave_speed(rho1, rho2, h1, h2, g)
        want_gp = g * (rho2 - rho1) / rho2
        want_c = math.sqrt(want_gp * h1 * h2 / (h1 + h2))
        self.assertAlmostEqual(gp, want_gp, places=9)
        self.assertAlmostEqual(c, want_c, places=9)

    def test_speed_is_in_the_observed_range(self):
        # 0.5 to 1.5 m/s at mid-latitude (issue #17).
        c, _ = wave_speed(1025.0, 1027.8, 50.0, 1000.0, 9.80665)
        self.assertGreater(c, 0.5)
        self.assertLess(c, 1.5)

    def test_deep_limit_tends_to_the_upper_layer(self):
        # h2 much greater than h1: c tends to sqrt(g' * h1).
        c, gp = wave_speed(1025.0, 1027.8, 50.0, 1.0e9, 9.80665)
        self.assertAlmostEqual(c, math.sqrt(gp * 50.0), places=3)

    def test_no_wave_when_the_column_is_unstable(self):
        # rho2 <= rho1: no internal wave, so the speed is 0.
        c, gp = wave_speed(1028.0, 1025.0, 50.0, 1000.0, 9.80665)
        self.assertEqual(c, 0.0)
        self.assertLessEqual(gp, 0.0)


class TestThermoclineProfile(unittest.TestCase):
    def test_midpoint_at_the_thermocline(self):
        # At z = z_tc the temperature is the mean of the two layers.
        self.assertAlmostEqual(profile(50.0), (15.0 + 4.0) / 2, places=6)

    def test_surface_and_deep_limits(self):
        self.assertGreater(profile(0.0), 14.0)  # near the mixed layer
        self.assertLess(profile(0.0), 15.0)
        self.assertAlmostEqual(profile(400.0), 4.0, places=3)

    def test_monotonic_decreasing(self):
        prev = profile(0.0)
        for z in range(0, 401, 10):
            t = profile(float(z))
            self.assertLessEqual(t, prev + 1e-9)
            prev = t

    def test_smaller_width_is_sharper(self):
        # The gradient at z_tc is steeper for a smaller width.
        dz = 1.0
        sharp = (profile(50.0 - dz, width=10.0) - profile(50.0 + dz, width=10.0)) / (
            2 * dz
        )
        soft = (profile(50.0 - dz, width=40.0) - profile(50.0 + dz, width=40.0)) / (
            2 * dz
        )
        self.assertGreater(sharp, soft)


class TestInternalTide(unittest.TestCase):
    def test_displacement_is_a_sine_of_the_phase(self):
        amp, period = 20.0, 44714.0
        self.assertAlmostEqual(
            internal_tide(amp, period, 0.0, 1.0, 50.0, 1000.0)[0], 0.0, places=6
        )
        self.assertAlmostEqual(
            internal_tide(amp, period, period / 4, 1.0, 50.0, 1000.0)[0], amp, places=6
        )
        self.assertAlmostEqual(
            internal_tide(amp, period, period / 2, 1.0, 50.0, 1000.0)[0], 0.0, places=6
        )
        self.assertAlmostEqual(
            internal_tide(amp, period, 3 * period / 4, 1.0, 50.0, 1000.0)[0],
            -amp,
            places=6,
        )

    def test_layer_currents_follow_continuity(self):
        # Gill 1982, section 6.2: u1 = c * eta / h1, u2 = -c * eta / h2.
        amp, period, c = 20.0, 44714.0, 1.2
        h1, h2 = 50.0, 1000.0
        eta, u1, u2 = internal_tide(amp, period, period / 4, c, h1, h2)
        self.assertAlmostEqual(u1, c * eta / h1, places=9)
        self.assertAlmostEqual(u2, -c * eta / h2, places=9)
        # The thinner layer carries the larger current.
        self.assertGreater(abs(u1), abs(u2))


if __name__ == "__main__":
    unittest.main()
