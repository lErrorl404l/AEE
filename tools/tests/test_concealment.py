#!/usr/bin/env python3
"""Seasonal vegetation concealment tests (issue #137).

The chain vegetationState -> concealment -> camo -> detection did not
exist: foliage and crop density were computed ("for concealment" in their
comments) but nothing consumed them.  fnc_calculateConcealment now
produces the concealment factor per position from surface class,
foliage/crop density, stance, and snow.  These tests mirror the SQF and
lock the physics.

Run: python3 -m unittest tools.tests.test_concealment
"""

import unittest

FOLIAGE_TEMPERATE = [0.2, 0.2, 0.3, 0.5, 0.8, 1.0, 1.0, 1.0, 0.9, 0.6, 0.4, 0.2]
CROP_TEMPERATE = [0.1, 0.1, 0.2, 0.4, 0.7, 1.0, 1.0, 0.9, 0.7, 0.3, 0.1, 0.1]


def concealment(surface, foliage, crop, snow, stance="STAND"):
    """Mirror of fnc_calculateConcealment.sqf.

    Returns (factor, snow_penalty, concealment) matching the SQF.
    """
    prone = stance == "PRONE"
    crouched = stance == "CROUCH"
    factor = 0.05
    cls = "bare"

    if any(
        k in surface
        for k in [
            "#gdtforest",
            "#gdtconiferous",
            "#gdtjungle",
            "#gdtrainforest",
            "#gdtorchard",
        ]
    ):
        factor = foliage
        cls = "forest"
    elif any(k in surface for k in ["#gdtcrop", "#gdtvineyard"]):
        factor = crop
        cls = "crop"
    elif any(
        k in surface
        for k in ["#gdtgrass", "#gdtgrassland", "#gdtprairie", "#gdttundra"]
    ):
        factor = 0.5 if prone else (0.2 if crouched else 0.05)
        cls = "grass"
    elif any(k in surface for k in ["#gdtmarsh", "#gdtswamp"]):
        factor = 0.3 + 0.7 * foliage
        cls = "marsh"
    elif any(k in surface for k in ["#gdtsnow", "#gdtglacier", "#gdtice"]):
        factor = -0.3 * (0.1 + snow)
        cls = "snow"
    else:
        cls = "bare"

    snow_penalty = 0.0
    if snow > 0 and cls != "snow":
        snow_penalty = 0.2 * min(snow, 0.5)

    concealment = max(0.0, min(1.0, factor - snow_penalty))
    return factor, snow_penalty, concealment


class TestConcealmentForest(unittest.TestCase):
    def test_summer_full_concealment(self):
        # July temperate: foliage 1.0 -> forest concealment 1.0.
        _, _, c = concealment("#gdtforest", 1.0, 0.0, 0.0)
        self.assertEqual(c, 1.0)

    def test_winter_leaf_off(self):
        # January temperate: foliage 0.2 -> much reduced concealment.
        _, _, c = concealment("#gdtforest", 0.2, 0.0, 0.0)
        self.assertEqual(c, 0.2)

    def test_winter_detection_increases(self):
        # Leaf-on vs leaf-off: detection range roughly 2-3x when
        # concealment drops from 1.0 to 0.2.
        _, _, summer = concealment("#gdtforest", 1.0, 0.0, 0.0)
        _, _, winter = concealment("#gdtforest", 0.2, 0.0, 0.0)
        self.assertAlmostEqual(summer / winter, 5.0, places=4)

    def test_leaf_on_monotonic(self):
        for m in range(12):
            _, _, c = concealment("#gdtforest", FOLIAGE_TEMPERATE[m], 0.0, 0.0)
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)


class TestConcealmentCrop(unittest.TestCase):
    def test_standing_corn_hides(self):
        # Crop 1.0 (standing corn ~2 m) hides a standing person.
        _, _, c = concealment("#gdtcrop", 0.0, 1.0, 0.0)
        self.assertEqual(c, 1.0)

    def test_bare_field_no_concealment(self):
        # Crop 0.0 (harvested stubble) -> none.
        _, _, c = concealment("#gdtcrop", 0.0, 0.0, 0.0)
        self.assertEqual(c, 0.0)

    def test_growing_crop_scales(self):
        _, _, c = concealment("#gdtcrop", 0.0, 0.7, 0.0)
        self.assertAlmostEqual(c, 0.7, places=4)


class TestConcealmentGrass(unittest.TestCase):
    def test_prone_hidden_crouched_partial_standing_visible(self):
        # Tall grass: prone 0.5, crouched 0.2, standing 0.05.
        f_prone, _, _ = concealment("#gdtgrass", 0.0, 0.0, 0.0, "PRONE")
        f_crouch, _, _ = concealment("#gdtgrass", 0.0, 0.0, 0.0, "CROUCH")
        f_stand, _, _ = concealment("#gdtgrass", 0.0, 0.0, 0.0, "STAND")
        self.assertEqual(f_prone, 0.5)
        self.assertEqual(f_crouch, 0.2)
        self.assertEqual(f_stand, 0.05)


class TestConcealmentSnow(unittest.TestCase):
    def test_snow_penalizes_vegetation(self):
        # A khaki soldier on snow is MORE visible (negative factor).
        _, _, c = concealment("#gdtsnow", 0.0, 0.0, 0.3)
        self.assertEqual(c, 0.0)  # negative clamped to 0
        f, _, _ = concealment("#gdtsnow", 0.0, 0.0, 0.3)
        self.assertLess(f, 0.0)

    def test_snow_reduces_forest_concealment(self):
        # Snow-covered forest: structure remains but white ground reduces
        # the khaki soldier's concealment.
        _, _, no_snow = concealment("#gdtforest", 1.0, 0.0, 0.0)
        _, _, with_snow = concealment("#gdtforest", 1.0, 0.0, 0.5)
        self.assertLess(with_snow, no_snow)
        # 0.5 m snow -> penalty 0.1 -> concealment 0.9.
        self.assertAlmostEqual(with_snow, 0.9, places=4)

    def test_snow_penalty_capped(self):
        _, _, c1 = concealment("#gdtforest", 1.0, 0.0, 0.5)
        _, _, c2 = concealment("#gdtforest", 1.0, 0.0, 2.0)
        self.assertEqual(c1, c2)  # snow penalty capped at 0.5 m


class TestConcealmentBare(unittest.TestCase):
    def test_bare_floor(self):
        # Desert/sand/rock: near-zero concealment floor.
        for s in ["#gdtdesert", "#gdtsand", "#gdtrock", "#gdtmountain"]:
            _, _, c = concealment(s, 0.0, 0.0, 0.0)
            self.assertEqual(c, 0.05, s)


class TestConcealmentMarsh(unittest.TestCase):
    def test_marsh_uses_foliage(self):
        _, _, c = concealment("#gdtmarsh", 0.8, 0.0, 0.0)
        self.assertAlmostEqual(c, 0.3 + 0.7 * 0.8, places=4)


class TestSQFSync(unittest.TestCase):
    """Drift-lock: the SQF must keep the concealment chain."""

    def test_sqf_wires_consumers(self):
        from pathlib import Path

        update = Path("addons/core/functions/fnc_updateEnvironment.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("calculateConcealment", update)

        sqf = Path(
            "addons/environmental/functions/terrain/fnc_calculateConcealment.sqf"
        ).read_text(encoding="utf-8")
        # Must read the existing density state.
        self.assertIn("currentFoliageDensity", sqf)
        self.assertIn("currentCropDensity", sqf)
        self.assertIn("snowDepth_m", sqf)
        # Must publish the camo coefficient for future consumers.
        self.assertIn("concealmentFactor", sqf)
        self.assertIn("surfaceType", sqf)


if __name__ == "__main__":
    unittest.main()
