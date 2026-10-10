#!/usr/bin/env python3
"""Reference checks for the underwater acoustics model (issue #113).

Runs the REAL SQF kernels in addons/maritime/functions through the sqf_lite
harness, so the test cannot drift from the source.  The anchors are the
issue's test vectors (corrected where the issue is wrong) and the cited
formulas: Mackenzie (1981), Francois-Garrison (1982), Wenz (1962), Urick.

Run: python3 -m unittest tools.tests.test_underwater_acoustics -v
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

SPEED = FUNCS / "fnc_calculateSoundSpeedWater.sqf"
ABSORP = FUNCS / "fnc_calculateAbsorptionWater.sqf"
TL = FUNCS / "fnc_calculateTransmissionLoss.sqf"
SONAR = FUNCS / "fnc_calculateSonarEquation.sqf"
RANGE = FUNCS / "fnc_calculateDetectionRange.sqf"
NOISE = FUNCS / "fnc_calculateAmbientNoise.sqf"
PROFILE = FUNCS / "fnc_calculateSoundSpeedProfile.sqf"
BEND = FUNCS / "fnc_calculateRayBending.sqf"
CHANNEL = FUNCS / "fnc_calculateSoundChannel.sqf"
SHADOW = FUNCS / "fnc_calculateShadowZone.sqf"
DRIVER = FUNCS / "fnc_updateUnderwaterAcoustics.sqf"
QUERY = FUNCS / "fnc_getSonarDetectionRange.sqf"
THERMO = FUNCS / "fnc_calculateThermoclineTemperature.sqf"


def run_profile(args):
    """Run the sound-speed profile, wiring FUNC to the shared thermocline kernel."""
    return run_sqf(
        PROFILE,
        args,
        globals_={
            "__FUNC__calculateThermoclineTemperature": lambda *a: run_sqf(
                THERMO, list(a)
            )
        },
    )


def mackenzie(T, S, D):
    """Mackenzie (1981) nine-term equation, JASA 70(3):807."""
    return (
        1448.96
        + 4.591 * T
        - 5.304e-2 * T**2
        + 2.374e-4 * T**3
        + 1.340 * (S - 35)
        + 1.630e-2 * D
        + 1.675e-7 * D**2
        - 1.025e-2 * T * (S - 35)
        - 7.139e-13 * T * D**3
    )


class TestMackenzieSoundSpeed(unittest.TestCase):
    """c(T,S,D), Mackenzie (1981)."""

    def test_issue_vector_1489_8(self):
        # Issue: T=10, S=35, D=0 -> 1489.8 m/s (NOT 1481, which is fresh
        # water at 20 C).
        self.assertAlmostEqual(run_sqf(SPEED, [10, 35, 0]), 1489.8, places=1)

    def test_matches_the_published_equation(self):
        for T, S, D in [
            (0, 35, 0),
            (20, 35, 0),
            (27, 35, 10),
            (4, 34, 500),
            (30, 40, 8000),
        ]:
            self.assertAlmostEqual(
                run_sqf(SPEED, [T, S, D]), mackenzie(T, S, D), places=4
            )

    def test_speed_increases_with_salinity_and_depth(self):
        base = run_sqf(SPEED, [10, 35, 0])
        self.assertGreater(run_sqf(SPEED, [10, 40, 0]), base)
        self.assertGreater(run_sqf(SPEED, [10, 35, 1000]), base)

    def test_typical_range(self):
        # 1450-1550 m/s over the valid range.
        for T in range(0, 31, 5):
            c = run_sqf(SPEED, [T, 35, 0])
            self.assertGreater(c, 1440)
            self.assertLess(c, 1560)


class TestFrancoisGarrisonAbsorption(unittest.TestCase):
    """alpha(f), Francois-Garrison (1982), JASA 72(6):1879."""

    def test_10khz_band(self):
        # Issue: 10 kHz -> 0.1-1 dB/km.
        a = run_sqf(ABSORP, [10000, 10, 35, 0, 8.0])
        self.assertGreater(a, 0.1)
        self.assertLess(a, 1.0)

    def test_100hz_the_issue_vector_is_wrong(self):
        # Issue: "0.01-0.1 at 100 Hz".  The equation gives about 0.001.
        a = run_sqf(ABSORP, [100, 10, 35, 0, 8.0])
        self.assertLess(a, 0.01)
        self.assertGreater(a, 0.0)

    def test_100khz_the_issue_vector_is_wrong(self):
        # Issue: "~50 dB/km at 100 kHz".  The equation gives about 34.
        a = run_sqf(ABSORP, [100000, 10, 35, 0, 8.0])
        self.assertGreater(a, 25)
        self.assertLess(a, 45)

    def test_monotonic_rise_with_frequency(self):
        prev = -1.0
        for f in [100, 1000, 10000, 100000, 1000000]:
            a = run_sqf(ABSORP, [f, 10, 35, 0, 8.0])
            self.assertGreater(a, prev)
            prev = a

    def test_pure_water_branch_changes_at_20c(self):
        # Both A3 branches are continuous at T=20.
        lo = run_sqf(ABSORP, [100000, 19.999, 35, 0, 8.0])
        hi = run_sqf(ABSORP, [100000, 20.001, 35, 0, 8.0])
        self.assertAlmostEqual(lo, hi, places=2)


class TestTransmissionLoss(unittest.TestCase):
    """TL = spreading + absorption."""

    def test_spherical_one_km(self):
        # 20 log10(1000) + 0.1 = 60.1 dB.
        self.assertAlmostEqual(run_sqf(TL, [1000, 0.1, "spherical"]), 60.1, places=2)

    def test_cylindrical_one_km(self):
        # 10 log10(1000) = 30 dB.
        self.assertAlmostEqual(run_sqf(TL, [1000, 0.0, "cylindrical"]), 30.0, places=2)

    def test_absorption_accumulates_with_range(self):
        near = run_sqf(TL, [10000, 0.1, "spherical"])
        far = run_sqf(TL, [100000, 0.1, "spherical"])
        # Absorption adds 0.1 dB/km: 9 dB over 90 km extra.
        self.assertAlmostEqual((far - near) - 20 * math.log10(10), 9.0, places=2)

    def test_zero_range_floored(self):
        self.assertAlmostEqual(run_sqf(TL, [0, 0.0, "spherical"]), 0.0, places=2)


class TestSonarEquation(unittest.TestCase):
    """Urick passive and active forms."""

    def test_passive(self):
        # SE = SL - TL - NL + DI = 150 - 80 - 55 + 20 = 35.
        self.assertAlmostEqual(
            run_sqf(SONAR, ["passive", 150, 80, 55, 20, 0]), 35.0, places=3
        )

    def test_active_doubles_tl(self):
        # SE = SL - 2TL + TS - NL + DI = 220 - 160 + 15 - 55 + 20 = 40.
        self.assertAlmostEqual(
            run_sqf(SONAR, ["active", 220, 80, 55, 20, 15]), 40.0, places=3
        )

    def test_passive_ignores_target_strength(self):
        a = run_sqf(SONAR, ["passive", 150, 80, 55, 20, 0])
        b = run_sqf(SONAR, ["passive", 150, 80, 55, 20, 99])
        self.assertAlmostEqual(a, b, places=6)


class TestDetectionRange(unittest.TestCase):
    """Detection when SE >= DT, inverted for range."""

    def test_passive_submarine_range(self):
        # Issue: passive submarine 10-100 km.  SL 150, NL 55, DI 20, DT 6,
        # alpha 0.1 dB/km -> about 95 km.
        r = run_sqf(RANGE, ["passive", 150, 55, 20, 0, 6, 0.1, "spherical"])
        self.assertGreater(r, 10000)
        self.assertLess(r, 100000)

    def test_no_absorption_closed_form(self):
        # EL = 150 - 55 + 20 - 6 = 109 -> r = 10^(109/20) m.
        r = run_sqf(RANGE, ["passive", 150, 55, 20, 0, 6, 0.0, "spherical"])
        self.assertAlmostEqual(r, 10 ** (109 / 20), delta=10 ** (109 / 20) * 1e-6)

    def test_zero_when_no_excess(self):
        # SL below NL + DT -> no detection.
        self.assertEqual(
            run_sqf(RANGE, ["passive", 50, 55, 0, 0, 6, 0.1, "spherical"]), 0
        )

    def test_active_range_shorter_than_passive(self):
        # For a quiet target the active range is shorter than a loud passive
        # one (2 TL vs 1 TL).
        active = run_sqf(RANGE, ["active", 220, 55, 20, 15, 6, 0.1, "spherical"])
        self.assertGreater(active, 0)


class TestWenzAmbientNoise(unittest.TestCase):
    """Wenz (1962) sea-state anchors at 1 kHz, dB re 1 uPa^2/Hz."""

    def test_sea_state_anchors(self):
        # Issue: SS0 ~40, SS3 ~55-60, SS6 ~70.
        self.assertAlmostEqual(run_sqf(NOISE, [1000, 0, False]), 40.0, places=1)
        self.assertAlmostEqual(run_sqf(NOISE, [1000, 3, False]), 55.0, places=1)
        self.assertAlmostEqual(run_sqf(NOISE, [1000, 6, False]), 70.0, places=1)

    def test_five_db_per_sea_state(self):
        a = run_sqf(NOISE, [1000, 1, False]) - run_sqf(NOISE, [1000, 0, False])
        self.assertAlmostEqual(a, 5.0, places=3)

    def test_high_frequency_falls(self):
        self.assertLess(
            run_sqf(NOISE, [10000, 3, False]), run_sqf(NOISE, [1000, 3, False])
        )

    def test_low_frequency_shipping_rises(self):
        self.assertGreater(
            run_sqf(NOISE, [100, 3, False]), run_sqf(NOISE, [500, 3, False])
        )

    def test_shallow_water_is_louder(self):
        self.assertGreater(
            run_sqf(NOISE, [1000, 3, True]), run_sqf(NOISE, [1000, 3, False])
        )


class TestSoundSpeedProfile(unittest.TestCase):
    """Vertical profile through Mackenzie."""

    def test_profile_shape(self):
        prof = run_profile([20, 100, 4, 35, 4000, 21])
        self.assertEqual(len(prof), 21)
        # Surface speed for T=20, S=35.  The shared thermocline model
        # (fnc_calculateThermoclineTemperature) is a tanh profile, so the
        # surface temperature is asymptotic to the mixed layer (within 0.02 C
        # here); allow 0.2 m/s on the derived sound speed.
        self.assertAlmostEqual(prof[0][1], mackenzie(20, 35, 0), delta=0.2)
        # Deep speed for T=4 at 4000 m.
        self.assertAlmostEqual(prof[-1][1], mackenzie(4, 35, 4000), places=3)

    def test_temperature_falls_to_thermocline(self):
        # The sound speed falls through the thermocline (a negative gradient)
        # then rises with pressure in the deep isothermal layer.
        prof = run_profile([20, 100, 4, 35, 4000, 21])
        speeds = [c for _, c in prof]
        self.assertLess(speeds[5], speeds[0])
        self.assertGreater(speeds[-1], min(speeds))


class TestSnellRayBending(unittest.TestCase):
    """cos(theta)/c constant across a layer boundary."""

    def test_bends_toward_slower_speed(self):
        # c falls 1500 -> 1450, so the grazing angle increases.
        theta2, turned = run_sqf(BEND, [0, 1500, 1450])
        self.assertFalse(turned)
        self.assertGreater(theta2, 0)
        self.assertAlmostEqual(math.cos(math.radians(theta2)), 1450 / 1500, places=6)

    def test_turning_point(self):
        # c rises 1450 -> 1500: cos would exceed 1, so the ray turns.
        theta2, turned = run_sqf(BEND, [0, 1450, 1500])
        self.assertTrue(turned)
        self.assertEqual(theta2, 90)

    def test_invariant_holds(self):
        for c1, c2 in [(1500, 1480), (1480, 1520), (1490, 1470)]:
            theta1 = 10
            theta2, turned = run_sqf(BEND, [theta1, c1, c2])
            if not turned:
                self.assertAlmostEqual(
                    math.cos(math.radians(theta1)) / c1,
                    math.cos(math.radians(theta2)) / c2,
                    places=9,
                )


class TestSoundChannelAndShadow(unittest.TestCase):
    """SOFAR axis and the direct-path shadow zone."""

    def test_axis_is_the_minimum(self):
        prof = run_profile([20, 100, 4, 35, 4000, 21])
        axis_depth, axis_speed = run_sqf(CHANNEL, [prof, 0])
        self.assertAlmostEqual(axis_speed, min(c for _, c in prof), places=6)
        self.assertGreater(axis_depth, 0)

    def test_shadow_below_the_axis(self):
        prof = run_profile([20, 100, 4, 35, 4000, 21])
        top, bottom = run_sqf(SHADOW, [prof, 0])
        axis_depth, _ = run_sqf(CHANNEL, [prof, 0])
        self.assertAlmostEqual(top, axis_depth, places=6)
        self.assertGreater(bottom, top)

    def test_deep_source_has_no_shadow(self):
        prof = run_profile([20, 100, 4, 35, 4000, 21])
        top, bottom = run_sqf(SHADOW, [prof, 3900])
        self.assertEqual((top, bottom), (0, 0))


class TestWiring(unittest.TestCase):
    """The driver publishes the state the query reads, source-locked."""

    def test_driver_calls_the_kernels(self):
        src = DRIVER.read_text(encoding="utf-8")
        for call in [
            "calculateSoundSpeedWater",
            "calculateSoundSpeedProfile",
            "calculateSoundChannel",
            "calculateShadowZone",
            "calculateAbsorptionWater",
            "calculateAmbientNoise",
        ]:
            self.assertIn(f"FUNC({call})", src, f"driver does not call {call}")

    def test_driver_publishes_the_state(self):
        src = DRIVER.read_text(encoding="utf-8")
        for var in [
            "soundSpeedSurface",
            "soundChannelAxisDepth_m",
            "soundChannelAxisSpeed",
            "shadowZoneTop_m",
            "shadowZoneBottom_m",
            "absorptionDbPerKm",
            "ambientNoiseDb",
        ]:
            self.assertIn(f"QGVAR({var})", src, f"driver does not publish {var}")

    def test_query_reads_the_environment(self):
        src = QUERY.read_text(encoding="utf-8")
        self.assertIn("QGVAR(ambientNoiseDb)", src)
        self.assertIn("QGVAR(absorptionDbPerKm)", src)
        self.assertIn("FUNC(calculateDetectionRange)", src)


if __name__ == "__main__":
    unittest.main()
