#!/usr/bin/env python3
"""Perception deviation kernel (task 11).

fnc_perceptionDetectDeviation compares the model's expected grade against the
grade that reached the render and reports discolouration, blindness, a grade
mismatch and a stuck adaptation.  It is pure and runs from its real SQF
through tools/tests/sqf_lite.py.

Fixtures: a clean view raises no flag; an offset grade raises discolouration;
a pinned aperture with a clamped pupil and an extreme lux raises blindness.

Run: python3 -m unittest tools.tests.test_perception_deviation -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEVIATION = (
    REPO
    / "addons"
    / "optics"
    / "functions"
    / "perception"
    / "fnc_perceptionDetectDeviation.sqf"
)

IDENTITY = [1.0, 1.0, 0.0, 0.0]

# The source clamp ends: aperture 8..50 (fnc_eyeAperture), pupil 1.9..8.0 mm
# (fnc_eyePupilSteady).
CLAMPS = dict(
    aperture=20.0,
    pupil=4.9,
    aperture_min=8.0,
    aperture_max=50.0,
    pupil_min=1.9,
    pupil_max=8.0,
)


def deviation(
    expected,
    applied,
    adapted=None,
    aperture=None,
    pupil=None,
    scene_lux=100.0,
    adapted_lux=50.0,
    prev_time=-1.0,
):
    if aperture is None:
        aperture = CLAMPS["aperture"]
    if pupil is None:
        pupil = CLAMPS["pupil"]
    adapted = [0.0, 0.0, 0.0, 0.0] if adapted is None else adapted
    return run_sqf(
        DEVIATION,
        [
            expected,
            applied,
            adapted,
            aperture,
            pupil,
            CLAMPS["aperture_min"],
            CLAMPS["aperture_max"],
            CLAMPS["pupil_min"],
            CLAMPS["pupil_max"],
            scene_lux,
            adapted_lux,
            prev_time,
        ],
    )


class TestClean(unittest.TestCase):
    def test_clean_view_raises_no_flag(self):
        discolouration, blindness, grade_mismatch, stuck, detail = deviation(
            IDENTITY, IDENTITY
        )
        self.assertFalse(discolouration)
        self.assertFalse(blindness)
        self.assertFalse(grade_mismatch)
        self.assertFalse(stuck)
        self.assertEqual(detail, "")


class TestDiscolouration(unittest.TestCase):
    def test_offset_grade_raises_discolouration(self):
        result = deviation(IDENTITY, [1.2, 1.0, 0.0, 0.0])
        self.assertTrue(result[0])
        self.assertEqual(result[4], "discolouration")

    def test_alpha_offset_raises_discolouration(self):
        result = deviation(IDENTITY, [1.0, 1.0, 0.0, 0.08])
        self.assertTrue(result[0])

    def test_grade_inside_tolerance_is_clean(self):
        result = deviation(IDENTITY, [1.01, 0.99, 0.01, 0.01])
        self.assertFalse(result[0])


class TestBlindness(unittest.TestCase):
    def test_pinned_aperture_raises_blindness(self):
        result = deviation(
            IDENTITY,
            IDENTITY,
            aperture=8.0,
            pupil=1.9,
            scene_lux=0.001,
            adapted_lux=0.001,
        )
        self.assertTrue(result[1])
        self.assertEqual(result[4], "blindness")

    def test_pinned_aperture_alone_is_not_blindness(self):
        # A normal scene lux with a pinned aperture is not a blindness.
        result = deviation(
            IDENTITY,
            IDENTITY,
            aperture=8.0,
            pupil=1.9,
            scene_lux=100.0,
            adapted_lux=50.0,
        )
        self.assertFalse(result[1])


class TestOtherFlags(unittest.TestCase):
    def test_absent_grade_is_a_mismatch(self):
        result = deviation(IDENTITY, [])
        self.assertTrue(result[2])

    def test_stuck_adaptation(self):
        result = deviation(
            IDENTITY, IDENTITY, adapted=[0.0, 0.0, 1.0, 5.0], prev_time=5.0
        )
        self.assertTrue(result[3])

    def test_adaptation_that_moved_is_not_stuck(self):
        result = deviation(
            IDENTITY, IDENTITY, adapted=[0.0, 0.0, 1.0, 2.0], prev_time=5.0
        )
        self.assertFalse(result[3])


if __name__ == "__main__":
    unittest.main()
