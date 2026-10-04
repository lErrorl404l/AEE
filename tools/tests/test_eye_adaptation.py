#!/usr/bin/env python3
"""Eye adaptation kernels (issue #141).

AEE owns the camera aperture and therefore owns the eye adaptation rate.
The model runs in base-10 log-luminance space.  A fast pupil branch lags a
slow cone and rod pair.  The CIE 191:2010 mesopic photopic fraction blends
the cone pool against the rod pool.

The pure kernels are executed here from their real SQF through
tools/tests/sqf_lite.py.  The engine-touching sampler, driver and wiring are
source-contracted (the wiring classes live in this file and in
test_engine_bridges.py).

Constants are traced to a published source or marked UNSOURCED beside the
value in the SQF header.  The per-constant register is in
.omo/plans/aee-eye-adaptation.md.
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EYE = ROOT / "addons" / "optics" / "functions" / "eye"

MESOPIC = EYE / "fnc_eyeMesopicWeight.sqf"
PUPIL_STEADY = EYE / "fnc_eyePupilSteady.sqf"
PUPIL_STEP = EYE / "fnc_eyePupilStep.sqf"
ADAPT_STEP = EYE / "fnc_eyeAdaptStep.sqf"
SCENE_LUX = EYE / "fnc_eyeSceneLux.sqf"
SKY_FRACTION = EYE / "fnc_eyeSkyFraction.sqf"
SKY_CAST = EYE / "fnc_eyeSkyCast.sqf"
APERTURE = EYE / "fnc_eyeAperture.sqf"
SAMPLE = EYE / "fnc_eyeSampleScene.sqf"
DRIVER = EYE / "fnc_updateEyeAdaptation.sqf"
INIT = EYE / "fnc_initEyeAdaptation.sqf"
FLASH = EYE / "fnc_eyeFlash.sqf"


def mesopic_weight(lum):
    """Mirror of fnc_eyeMesopicWeight: CIE 191:2010 photopic fraction."""
    lo, hi = 0.005, 5.0
    if lum <= lo:
        return 0.0
    if lum >= hi:
        return 1.0
    t = (math.log10(lum) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    return t * t * (3 - 2 * t)


def pupil_steady(lum):
    """Mirror of fnc_eyePupilSteady: de Groot and Gebhard 1952 diameter."""
    b = lum / 3.183
    x = 0.4 * (math.log10(b) + 0.5)
    d = 4.9 - 3.0 * math.tanh(x)
    return max(1.9, min(8.0, d))


def pupil_step(d, d_target, dt, tau_constrict=0.25, tau_dilate=0.475):
    """Mirror of fnc_eyePupilStep: asymmetric first-order lag."""
    tau = tau_constrict if d_target < d else tau_dilate
    return d + (d_target - d) * (1 - math.exp(-dt / tau))


class TestEyeMesopicWeight(unittest.TestCase):
    """fnc_eyeMesopicWeight runs from the real SQF and matches the mirror."""

    def test_scotopic_endpoint_is_zero(self):
        self.assertEqual(run_sqf(MESOPIC, [0.005]), 0)

    def test_photopic_endpoint_is_one(self):
        self.assertEqual(run_sqf(MESOPIC, [5]), 1)

    def test_below_band_is_scotopic(self):
        self.assertEqual(run_sqf(MESOPIC, [0.001]), 0)

    def test_above_band_is_photopic(self):
        self.assertEqual(run_sqf(MESOPIC, [100]), 1)

    def test_monotonic_on_the_band(self):
        sweep = [0.005 * (5 / 0.005) ** (i / 20) for i in range(21)]
        prev = -1.0
        for lum in sweep:
            got = run_sqf(MESOPIC, [lum])
            self.assertGreaterEqual(got, prev)
            self.assertLessEqual(got, 1.0)
            prev = got

    def test_matches_the_mirror_in_the_band(self):
        for lum in [0.01, 0.05, 0.2, 1.0, 2.5]:
            self.assertAlmostEqual(
                run_sqf(MESOPIC, [lum]), mesopic_weight(lum), places=6
            )


class TestEyePupilSteady(unittest.TestCase):
    """fnc_eyePupilSteady runs from the real SQF and matches the mirror."""

    def test_bright_scene_constricts(self):
        self.assertLess(run_sqf(PUPIL_STEADY, [10000]), 2.5)

    def test_dark_scene_dilates(self):
        self.assertGreater(run_sqf(PUPIL_STEADY, [0.001]), 7.0)

    def test_monotonic_decreasing_in_lum(self):
        prev = None
        for lum in [1e-4, 1e-2, 1e-1, 1, 10, 1000, 1e5]:
            got = run_sqf(PUPIL_STEADY, [lum])
            if prev is not None:
                self.assertLessEqual(got, prev)
            prev = got

    def test_stays_inside_the_clamps(self):
        for lum in [1e-9, 1e-3, 1, 1e3, 1e9]:
            got = run_sqf(PUPIL_STEADY, [lum])
            self.assertGreaterEqual(got, 1.9)
            self.assertLessEqual(got, 8.0)

    def test_matches_the_mirror(self):
        for lum in [0.001, 0.1, 3.183, 100, 10000]:
            self.assertAlmostEqual(
                run_sqf(PUPIL_STEADY, [lum]), pupil_steady(lum), places=6
            )


class TestEyePupilStep(unittest.TestCase):
    """fnc_eyePupilStep runs from the real SQF and matches the mirror."""

    def test_zero_step_does_not_move(self):
        self.assertAlmostEqual(
            run_sqf(PUPIL_STEP, [4.0, 6.0, 0.0, 0.25, 0.475]), 4.0, places=9
        )

    def test_large_step_reaches_target(self):
        got = run_sqf(PUPIL_STEP, [4.0, 6.0, 100.0, 0.25, 0.475])
        self.assertAlmostEqual(got, 6.0, places=6)

    def test_constriction_is_faster_than_redilation(self):
        # Equal 3 mm steps over the same dt: the constriction moves further.
        constricted = run_sqf(PUPIL_STEP, [6.0, 3.0, 0.2, 0.25, 0.475])
        dilated = run_sqf(PUPIL_STEP, [3.0, 6.0, 0.2, 0.25, 0.475])
        moved_constrict = 6.0 - constricted
        moved_dilate = dilated - 3.0
        self.assertGreater(moved_constrict, moved_dilate)

    def test_matches_the_mirror(self):
        for d, target, dt in [(5.0, 2.0, 0.1), (2.0, 7.0, 0.4), (4.0, 4.5, 0.2)]:
            self.assertAlmostEqual(
                run_sqf(PUPIL_STEP, [d, target, dt, 0.25, 0.475]),
                pupil_step(d, target, dt),
                places=6,
            )


class TestEyeAdaptStep(unittest.TestCase):
    """fnc_eyeAdaptStep runs from the real SQF; the taus are asymmetric."""

    def test_light_step_advances_faster_than_dark_step(self):
        # Same dt, same |target - state|: the light branch (tau 2) moves more.
        to_light = run_sqf(ADAPT_STEP, [[0.0, 0.0], 1.0, 1.0, 2.0, 120.0, 400.0, 0.5])
        to_dark = run_sqf(ADAPT_STEP, [[0.0, 0.0], -1.0, 1.0, 2.0, 120.0, 400.0, 0.5])
        self.assertGreater(to_light[1], abs(to_dark[1]))

    def test_rod_pool_is_slower_than_cone_pool_in_the_dark(self):
        got = run_sqf(ADAPT_STEP, [[0.0, 0.0], -1.0, 1.0, 2.0, 120.0, 400.0, 0.5])
        cone, rod = got
        self.assertLess(cone, rod)  # cone travelled further into the dark

    def test_no_change_when_target_equals_state(self):
        got = run_sqf(ADAPT_STEP, [[1.0, 1.0], 1.0, 1.0, 2.0, 120.0, 400.0, 0.5])
        self.assertAlmostEqual(got[0], 1.0, places=9)
        self.assertAlmostEqual(got[1], 1.0, places=9)

    def test_matches_the_first_order_lag(self):
        # Brightening: both pools use the light tau.
        cone, rod = run_sqf(ADAPT_STEP, [[0.0, 0.0], 2.0, 0.5, 2.0, 120.0, 400.0, 0.5])
        self.assertAlmostEqual(cone, 2.0 * (1 - math.exp(-0.25)), places=9)
        self.assertAlmostEqual(rod, 2.0 * (1 - math.exp(-0.25)), places=9)
        # Darkening: each pool uses its own dark tau.
        cone, rod = run_sqf(ADAPT_STEP, [[0.0, 0.0], -2.0, 0.5, 2.0, 120.0, 400.0, 0.5])
        self.assertAlmostEqual(cone, -2.0 * (1 - math.exp(-0.5 / 120)), places=9)
        self.assertAlmostEqual(rod, -2.0 * (1 - math.exp(-0.5 / 400)), places=9)


class TestEyeSceneLux(unittest.TestCase):
    """fnc_eyeSceneLux runs from the real SQF; local light ignores sky."""

    def test_sky_only_scales_with_the_fraction(self):
        self.assertAlmostEqual(run_sqf(SCENE_LUX, [1.0, 0.0, 0.5]), 0.5, places=9)

    def test_no_sky_and_no_local_is_dark(self):
        self.assertEqual(run_sqf(SCENE_LUX, [1.0, 0.0, 0.0]), 0.0)

    def test_local_light_is_not_scaled_by_the_sky(self):
        # A torch works indoors, where the sky fraction is 0.
        self.assertAlmostEqual(run_sqf(SCENE_LUX, [1.0, 0.5, 0.0]), 0.5, places=9)

    def test_ambient_and_local_add(self):
        self.assertAlmostEqual(run_sqf(SCENE_LUX, [1.0, 0.5, 0.5]), 1.0, places=9)


class TestEyeSkyFraction(unittest.TestCase):
    """fnc_eyeSkyFraction runs from the real SQF."""

    def test_partial_sky(self):
        self.assertAlmostEqual(
            run_sqf(SKY_FRACTION, [[True, False, False]]), 1 / 3, places=6
        )

    def test_empty_sample_is_open_sky(self):
        self.assertEqual(run_sqf(SKY_FRACTION, [[]]), 1)

    def test_all_clear_is_one(self):
        self.assertEqual(run_sqf(SKY_FRACTION, [[True, True, True, True]]), 1)

    def test_all_blocked_is_zero(self):
        self.assertEqual(run_sqf(SKY_FRACTION, [[False, False]]), 0)


def aperture(lux):
    """Mirror of fnc_eyeAperture: log-lux -> aperture (higher is wider)."""
    lux = max(0.001, min(100000.0, lux))
    ev = math.log10(lux)
    t = max(0.0, min(1.0, (ev - (-3)) / (5 - (-3))))
    return 8 + t * (0.2 - 8)


class TestEyeAperture(unittest.TestCase):
    """fnc_eyeAperture runs from the real SQF and matches the wiki anchors."""

    def test_night_anchor(self):
        self.assertAlmostEqual(run_sqf(APERTURE, [0.001]), 8, places=6)

    def test_day_anchor(self):
        self.assertAlmostEqual(run_sqf(APERTURE, [100000]), 0.2, places=6)

    def test_monotonic_decreasing(self):
        prev = None
        for lux in [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000]:
            got = run_sqf(APERTURE, [lux])
            if prev is not None:
                self.assertLessEqual(got, prev)
            prev = got

    def test_clamps_outside_the_domain(self):
        self.assertAlmostEqual(run_sqf(APERTURE, [1e-9]), 8, places=6)
        self.assertAlmostEqual(run_sqf(APERTURE, [1e9]), 0.2, places=6)

    def test_matches_the_mirror(self):
        for lux in [0.005, 0.5, 50, 5000]:
            self.assertAlmostEqual(run_sqf(APERTURE, [lux]), aperture(lux), places=6)


class TestEyeDriverContract(unittest.TestCase):
    """Source contract for the engine-touching sampler, driver and starter."""

    @staticmethod
    def _code(path):
        text = path.read_text(encoding="utf-8")
        return text[text.index("*/") + 2 :] if "*/" in text else text

    def test_driver_gates_on_vision_mode_before_the_write(self):
        code = self._code(DRIVER)
        gate = re.search(r"if\s*\([^)]*currentVisionMode[^)]*\)\s*exitWith", code)
        self.assertIsNotNone(gate, "no live vision-mode gate found")
        write = re.search(r"^\s*setApertureNew\s*\[", code, re.M)
        self.assertIsNotNone(write, "no setApertureNew call found")
        self.assertLess(gate.start(), write.start(), "the gate is after the write")

    def test_pin_uses_the_four_element_form(self):
        match = re.search(r"setApertureNew\s*\[([^\]]+)\]", self._code(DRIVER))
        self.assertIsNotNone(match, "no setApertureNew call found")
        elements = [part for part in match.group(1).split(",") if part.strip()]
        self.assertEqual(len(elements), 4, f"expected 4 elements, got {len(elements)}")

    def test_driver_hands_the_camera_back(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("setAperture -1", text)

    def test_starter_is_client_gated_and_idempotent(self):
        text = INIT.read_text(encoding="utf-8")
        self.assertIn("hasInterface", text)
        self.assertIn("eyePFH", text)
        self.assertIn("addPerFrameHandler", text)

    def test_sampler_reads_the_engine_lighting(self):
        text = SAMPLE.read_text(encoding="utf-8")
        self.assertIn("getLightingAt", text)
        self.assertIn("hasInterface", text)

    def test_engine_notes_carry_forward(self):
        aperture_text = APERTURE.read_text(encoding="utf-8")
        driver_text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("HDR", aperture_text)
        self.assertIn("mission start", aperture_text)
        self.assertIn("HDR", driver_text)
        self.assertIn("mission start", driver_text)

    def test_debug_hooks_are_read(self):
        text = DRIVER.read_text(encoding="utf-8")
        for hook in ["eyeForceLux", "eyeFreeze", "eyeForceMode"]:
            self.assertIn(hook, text, f"debug hook {hook} not read")


OPTICS = ROOT / "addons" / "optics"
PREP = OPTICS / "XEH_PREP.hpp"
POSTINIT = OPTICS / "XEH_postInit.sqf"
SETTINGS = OPTICS / "initSettings.inc.sqf"
STRINGS = OPTICS / "stringtable.xml"


class TestEyeWiring(unittest.TestCase):
    """The module is registered, started, and documented."""

    EYE_FUNCTIONS = [
        "eyeMesopicWeight",
        "eyePupilSteady",
        "eyePupilStep",
        "eyeAdaptStep",
        "eyeSceneLux",
        "eyeSkyFraction",
        "eyeSkyCast",
        "eyeAperture",
        "eyeSampleScene",
        "eyeFlash",
        "updateEyeAdaptation",
        "initEyeAdaptation",
    ]

    EYE_SETTINGS = [
        "eyeAdaptationEnabled",
        "eyeReflectance",
        "eyeTauLight",
        "eyeTauDarkCone",
        "eyeTauDarkRod",
        "eyePupilTauConstrict",
        "eyePupilTauDilate",
        "eyeMesopicLow",
        "eyeMesopicHigh",
        "eyeFastBlend",
        "eyeAmbientLuxScale",
        "eyeLocalLuxScale",
        "eyeBlindingLuxScale",
    ]

    def test_every_function_is_prepped(self):
        text = PREP.read_text(encoding="utf-8")
        for name in self.EYE_FUNCTIONS:
            self.assertIn(f"PREPS(eye,{name});", text, f"{name} is not prepped")

    def test_postinit_starts_the_module(self):
        text = POSTINIT.read_text(encoding="utf-8")
        self.assertIn("FUNC(initEyeAdaptation)", text)

    def test_settings_are_registered(self):
        text = SETTINGS.read_text(encoding="utf-8")
        for name in self.EYE_SETTINGS:
            self.assertIn(name, text, f"setting {name} is not registered")
        self.assertIn('"AEE Optics","Eye Adaptation"', text)

    def test_stringtable_keys_are_sorted(self):
        keys = re.findall(
            r'<Key ID="(STR_AEE_Optics_\w+)"', STRINGS.read_text(encoding="utf-8")
        )
        self.assertEqual(keys, sorted(keys), "stringtable keys are not sorted")

    def test_every_setting_has_name_and_description(self):
        text = STRINGS.read_text(encoding="utf-8")
        for name in self.EYE_SETTINGS:
            self.assertIn(f"STR_AEE_Optics_{name}_Name", text)
            self.assertIn(f"STR_AEE_Optics_{name}_Description", text)


class TestEyeFlash(unittest.TestCase):
    """fnc_eyeFlash runs from the real SQF; the handler stamps the window."""

    def test_no_flash_is_dark(self):
        self.assertEqual(run_sqf(FLASH, [0, False]), 0)

    def test_a_flash_is_positive(self):
        self.assertGreater(run_sqf(FLASH, [2, False]), 0)

    def test_suppressed_is_dimmer(self):
        loud = run_sqf(FLASH, [5, False])
        quiet = run_sqf(FLASH, [5, True])
        self.assertGreater(loud, quiet)
        self.assertGreater(quiet, 0)

    def test_handler_stamps_the_flash_window(self):
        text = POSTINIT.read_text(encoding="utf-8")
        self.assertIn("FUNC(eyeFlash)", text)
        self.assertIn("eyeFlashLux", text)
        self.assertIn("eyeFlashUntil", text)

    def test_driver_reads_the_flash_window(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("eyeFlashLux", text)
        self.assertIn("eyeFlashUntil", text)

    def test_driver_does_not_double_count_with_the_engine_term(self):
        # The flash is a separate additive term on the scene lux, not folded
        # into the engine dynamic term.
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("_sceneLux + _flashLux", text)


if __name__ == "__main__":
    unittest.main()
