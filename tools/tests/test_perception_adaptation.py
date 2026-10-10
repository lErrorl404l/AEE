#!/usr/bin/env python3
"""Eye adaptation temporal state (task 10).

fnc_perceptionAdaptState folds the published eye-adaptation state into the
four fields the perception schema carries for eyeAdaptationState.  It is pure
and runs from its real SQF through tools/tests/sqf_lite.py.

The fixtures pin the direction rule: a level below the target adapts upward
(+1) and a level above the target adapts downward (-1).  The time to adapt is
tau * ln(20) when the caller supplies no measured value, and the published
direction and time win when they are present.

Run: python3 -m unittest tools.tests.test_perception_adaptation -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ADAPT = (
    REPO
    / "addons" / "vision" / "functions" / "perception"
    / "fnc_perceptionAdaptState.sqf"
)

TAU_95 = math.log(20)


def adapt(state, target_lux, mesopic=1.0, direction=0.0, tau=0.0, time=0.0, rho=0.18):
    return run_sqf(ADAPT, [state, target_lux, mesopic, direction, tau, time, rho])


def target_lux_for_level(level, rho=0.18):
    """The scene lux whose rho * E / pi luminance log equals the level."""
    return (10.0**level) * math.pi / rho


class TestDirection(unittest.TestCase):
    def test_level_below_target_gives_plus_one(self):
        # level -2 (log10), target 100 lx (log10 2): the eye must adapt up.
        result = adapt([-2.0, -2.0], 100.0, tau=2.0)
        self.assertEqual(result[2], 1)

    def test_level_below_target_has_positive_time(self):
        result = adapt([-2.0, -2.0], 100.0, tau=2.0)
        self.assertGreater(result[3], 0.0)
        self.assertAlmostEqual(result[3], 2.0 * TAU_95, places=9)

    def test_level_above_target_gives_minus_one(self):
        # level 2 (log10), target 1 lx (log10 0): the eye must adapt down.
        result = adapt([2.0, 2.0], 1.0, tau=2.0)
        self.assertEqual(result[2], -1)

    def test_level_above_target_has_positive_time(self):
        result = adapt([2.0, 2.0], 1.0, tau=2.0)
        self.assertGreater(result[3], 0.0)


class TestLevel(unittest.TestCase):
    def test_mesopic_blend_is_weighted_log(self):
        # mesopic 0.5 blends cone -2 and rod 0 to a level of -1.
        result = adapt([-2.0, 0.0], 100.0, mesopic=0.5)
        self.assertEqual(result[0], -1.0)
        self.assertEqual(result[2], 1)

    def test_photopic_level_is_the_cone_pool(self):
        result = adapt([-3.0, 4.0], 1.0, mesopic=1.0)
        self.assertEqual(result[0], -3.0)


class TestPublishedWins(unittest.TestCase):
    def test_published_direction_is_authoritative(self):
        result = adapt([-2.0, -2.0], 100.0, direction=-1.0, tau=2.0)
        self.assertEqual(result[2], -1)

    def test_published_time_is_authoritative(self):
        result = adapt([-2.0, -2.0], 100.0, direction=1.0, tau=2.0, time=3.5)
        self.assertEqual(result[3], 3.5)

    def test_settled_level_reports_no_direction(self):
        # The level (log10 cd/m2) equals the target's luminance log, so the
        # fallback stays settled.  The target arrives in lux, so it is the
        # luminance-equivalent lux, not the raw lux log.
        result = adapt([0.0, 0.0], target_lux_for_level(0.0))
        self.assertEqual(result[2], 0)

    def test_settled_uses_the_luminance_conversion_not_the_raw_lux(self):
        # Regression for the false stuckAdaptation flag.  The level is log10
        # cd/m2; a raw log of the target lux sits log10(pi / rho) high, about
        # 1.24, which always read as "brighter" and forced direction +1 on a
        # settled eye.  A settled level must stay settled when the target's
        # luminance log matches it, and the same raw lux must NOT read settled.
        settled = adapt([0.0, 0.0], target_lux_for_level(0.0))
        self.assertEqual(settled[2], 0)
        # 1 lux is luminance 0.0573 cd/m2 (log -1.24), well below a level of 0.
        raw = adapt([0.0, 0.0], 1.0)
        self.assertEqual(raw[2], -1)

    def test_fallback_gap_is_taken_in_the_luminance_unit(self):
        # Level -1 (log10 cd/m2); the luminance-equivalent target is level 0,
        # one log unit brighter, so the fallback reports +1.
        result = adapt([-1.0, -1.0], target_lux_for_level(0.0))
        self.assertEqual(result[2], 1)

    def test_fallback_honours_a_custom_reflectance(self):
        # A different rho shifts the luminance conversion; the settled target
        # follows it.
        result = adapt([0.0, 0.0], target_lux_for_level(0.0, rho=0.5), rho=0.5)
        self.assertEqual(result[2], 0)

    def test_target_is_returned_unchanged(self):
        result = adapt([-1.0, -1.0], 42.0, direction=1.0, time=1.0)
        self.assertEqual(result[1], 42.0)


if __name__ == "__main__":
    unittest.main()
