#!/usr/bin/env python3
"""Image realism kernels (normal-vision grade and thermal imperfections).

The pure kernels run here from their real SQF through tools/tests/sqf_lite.py.
The engine-touching drivers and wiring are source-contracted.  Every constant
is traced to a published source or marked UNSOURCED beside the value in the
SQF header; the per-constant register is in
.omo/plans/aee-image-realism.md.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OPTICS = ROOT / "addons" / "optics"
THERMAL = ROOT / "addons" / "thermal"

GRADE = OPTICS / "functions" / "grade"
BASE_KERNEL = GRADE / "fnc_baseGradeParams.sqf"
THERMAL_KERNEL = THERMAL / "functions" / "display" / "fnc_thermalImperfectionParams.sqf"


class TestBaseGradeParams(unittest.TestCase):
    """fnc_baseGradeParams runs from the real SQF and clamps every input."""

    def test_colorcorrections_array_has_seven_elements(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(len(cc), 7)

    def test_brightness_is_element_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.15, 0.9])
        self.assertAlmostEqual(cc[0], 0.9, places=9)

    def test_contrast_is_element_one(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.3, 1.0])
        self.assertAlmostEqual(cc[1], 1.3, places=9)

    def test_color_weight_is_rec709_and_not_all_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        weights = cc[5]
        self.assertEqual(weights, [0.2126, 0.7152, 0.0722, 0])
        self.assertNotEqual(weights[:3], [0, 0, 0])

    def test_saturation_defaults_to_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[4][3], 0)

    def test_saturation_flows_into_the_colorize_alpha(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0.4])
        self.assertAlmostEqual(cc[4][3], 0.4, places=9)

    def test_blend_alpha_keeps_the_original_colour(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[3], [0, 0, 0, 0])

    def test_filmgrain_array_has_six_elements(self):
        _, grain = run_sqf(BASE_KERNEL, [])
        self.assertEqual(len(grain), 6)

    def test_sharpness_is_element_one_in_range(self):
        _, grain = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0, 12.0])
        self.assertAlmostEqual(grain[1], 12.0, places=9)
        self.assertGreaterEqual(grain[1], 1)
        self.assertLessEqual(grain[1], 20)

    def test_grain_intensity_is_element_zero(self):
        _, grain = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0, 4.0, 0.01])
        self.assertAlmostEqual(grain[0], 0.01, places=9)

    def test_default_contrast_is_1_15(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertAlmostEqual(cc[1], 1.15, places=9)

    def test_default_black_point_offsets_negative(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertAlmostEqual(cc[2], -0.02, places=9)

    def test_contrast_is_clamped(self):
        cc, _ = run_sqf(BASE_KERNEL, [99.0, 1.0])
        self.assertAlmostEqual(cc[1], 1.6, places=9)
        cc, _ = run_sqf(BASE_KERNEL, [0.1, 1.0])
        self.assertAlmostEqual(cc[1], 0.8, places=9)

    def test_brightness_is_clamped(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.0, 99.0])
        self.assertAlmostEqual(cc[0], 1.3, places=9)
        cc, _ = run_sqf(BASE_KERNEL, [1.0, -99.0])
        self.assertAlmostEqual(cc[0], 0.7, places=9)

    def test_offset_is_clamped(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.0, 1.0, 99.0])
        self.assertAlmostEqual(cc[2], 0.1, places=9)
        cc, _ = run_sqf(BASE_KERNEL, [1.0, 1.0, -99.0])
        self.assertAlmostEqual(cc[2], -0.1, places=9)

    def test_saturation_is_clamped(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.0, 1.0, 0.0, 99.0])
        self.assertAlmostEqual(cc[4][3], 0.5, places=9)

    def test_sharpness_is_clamped(self):
        _, grain = run_sqf(BASE_KERNEL, [1.0, 1.0, 0.0, 0.0, 99.0])
        self.assertAlmostEqual(grain[1], 20.0, places=9)

    def test_grain_is_clamped(self):
        _, grain = run_sqf(BASE_KERNEL, [1.0, 1.0, 0.0, 0.0, 4.0, 99.0])
        self.assertAlmostEqual(grain[0], 0.05, places=9)


class TestThermalImperfectionParams(unittest.TestCase):
    """fnc_thermalImperfectionParams runs from the real SQF."""

    def test_agc_hunt_is_zero_at_entry(self):
        _, hunt, _, _ = run_sqf(THERMAL_KERNEL, [1, 0, 0.05, 4.0, 0.15, 0.08, 0, 1])
        self.assertAlmostEqual(hunt, 0, places=9)

    def test_agc_hunt_is_negative_at_half_the_period(self):
        _, hunt, _, _ = run_sqf(THERMAL_KERNEL, [1, 2.0, 0.05, 4.0, 0.15, 0.08, 0, 1])
        self.assertLess(hunt, 0)

    def test_bloom_is_zero_with_no_hot_source(self):
        bloom, _, _, _ = run_sqf(THERMAL_KERNEL, [1, 0, 0.05, 4.0, 0.15, 0.08, 0, 1])
        self.assertEqual(bloom, 0)

    def test_bloom_equals_base_at_full_hot(self):
        bloom, _, _, _ = run_sqf(THERMAL_KERNEL, [1, 0, 0.05, 4.0, 0.15, 0.08, 1, 1])
        self.assertAlmostEqual(bloom, 0.08, places=9)

    def test_bloom_scales_with_the_settle_factor(self):
        bloom, _, _, _ = run_sqf(THERMAL_KERNEL, [1, 0, 0.05, 4.0, 0.15, 0.08, 1, 0.5])
        self.assertAlmostEqual(bloom, 0.04, places=9)

    def test_nuc_and_hunt_are_phase_distinct(self):
        _, hunt, nuc, _ = run_sqf(THERMAL_KERNEL, [1, 2.0, 0.05, 4.0, 0.15, 0.08, 0, 1])
        self.assertGreater(abs(hunt - nuc), 1e-3)

    def test_temporal_noise_is_bounded(self):
        for t in [0, 0.1, 0.37, 1.0, 3.7, 11.3]:
            _, _, _, noise = run_sqf(
                THERMAL_KERNEL, [1, t, 0.05, 4.0, 0.15, 0.08, 0, 1]
            )
            self.assertGreaterEqual(noise, 0)
            self.assertLessEqual(noise, 1)

    def test_every_output_is_within_its_range(self):
        for t in [0, 0.5, 1.0, 2.0, 3.0, 4.0, 9.0, 37.0, 100.0]:
            bloom, hunt, nuc, noise = run_sqf(
                THERMAL_KERNEL, [1, t, 0.05, 4.0, 0.15, 0.08, 1, 1]
            )
            self.assertGreaterEqual(bloom, 0)
            self.assertLessEqual(bloom, 0.15)
            self.assertGreaterEqual(hunt, -0.1)
            self.assertLessEqual(hunt, 0.1)
            self.assertGreaterEqual(nuc, -0.3)
            self.assertLessEqual(nuc, 0.3)
            self.assertGreaterEqual(noise, 0)
            self.assertLessEqual(noise, 1)

    def test_out_of_range_inputs_are_clamped(self):
        bloom, hunt, nuc, _ = run_sqf(
            THERMAL_KERNEL, [1, 2.0, 99.0, 4.0, 99.0, 99.0, 99.0, 99.0]
        )
        self.assertLessEqual(bloom, 0.15)
        self.assertLessEqual(hunt, 0.1)
        self.assertGreaterEqual(hunt, -0.1)
        self.assertLessEqual(nuc, 0.3)
        self.assertGreaterEqual(nuc, -0.3)

    def test_period_is_floored_to_avoid_division_by_zero(self):
        # A zero period must not raise; the sine argument stays finite.
        result = run_sqf(THERMAL_KERNEL, [1, 1.0, 0.05, 0, 0.15, 0.08, 0, 1])
        self.assertEqual(len(result), 4)


if __name__ == "__main__":
    unittest.main()
