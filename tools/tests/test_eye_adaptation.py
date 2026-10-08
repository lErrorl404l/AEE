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
AMBIENT = EYE / "fnc_eyeAmbientLux.sqf"
LOCAL = EYE / "fnc_eyeLocalLux.sqf"
ADAPT_INIT = EYE / "fnc_eyeAdaptInit.sqf"
ADAPT_STATE = EYE / "fnc_eyeAdaptState.sqf"
TIME_SKIP = EYE / "fnc_eyeTimeSkip.sqf"
LIMITS = EYE / "fnc_eyeLimits.sqf"
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


EYE_RHO = 0.18  # the driver eyeReflectance default


def aperture(lux):
    """Mirror of fnc_eyeAperture: log-lux -> aperture.

    The aperture value is LIGHT INTAKE: a lower value is a wider aperture and
    a brighter image, so the map ascends from the wide night anchor (8) to the
    narrow daylight anchor (50).  Anchors: BI wiki setApertureNew night
    example [2, 8, 14], and the BI wiki setAperture Namikaze calibration
    (50 = daylight outdoor, 30 = indoor, below 20 = very bright, closer to 0
    lets in more light).
    """
    d = pupil_steady(EYE_RHO * max(1e-9, lux) / math.pi)
    d = max(1.9, min(8.0, d))
    t = max(0.0, min(1.0, (d - 1.9) / (8.0 - 1.9)))
    return 50 + t * (8 - 50)


class TestEyeAperture(unittest.TestCase):
    """fnc_eyeAperture runs from the real SQF and matches the wiki anchors."""

    def test_starlight_is_near_the_night_end(self):
        v = run_sqf(APERTURE, [0.001])
        self.assertGreater(v, 8.0)
        self.assertLess(v, 12.0)

    def test_full_sun_is_near_the_day_end(self):
        # Regression: at full sun the aperture is the daylight outdoor value
        # (50), not the scenario-less setApertureNew Example 1 value 0.2.  A
        # 0.2 anchor pinned a near-maximum light intake at noon and
        # over-exposed normal vision (the daytime blowout report).
        v = run_sqf(APERTURE, [100000])
        self.assertGreater(v, 47.0)
        self.assertLess(v, 50.5)

    def test_map_ascends_from_night_to_day(self):
        # A lower value is more light, so a brighter scene must map to a
        # HIGHER (narrower) value.  This fails if the anchors are inverted.
        self.assertGreater(run_sqf(APERTURE, [100000]), run_sqf(APERTURE, [0.001]))

    def test_monotonic_increasing(self):
        prev = None
        for lux in [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000]:
            got = run_sqf(APERTURE, [lux])
            if prev is not None:
                self.assertGreaterEqual(got, prev)
            prev = got

    def test_clamps_outside_the_domain(self):
        self.assertLess(run_sqf(APERTURE, [1e-9]), 9.0)
        self.assertGreater(run_sqf(APERTURE, [1e9]), 49.5)

    def test_day_anchor_is_a_daylight_value(self):
        # Source contract: the day anchor must sit above the BI wiki "very
        # bright" ceiling (20), or it over-exposes a daylit scene.
        text = APERTURE.read_text(encoding="utf-8")
        match = re.search(r"_dayStandard\s*=\s*([0-9.]+)", text)
        self.assertIsNotNone(match, "no _dayStandard found in fnc_eyeAperture")
        self.assertGreater(float(match.group(1)), 20)

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

    def test_driver_steps_on_the_real_clock(self):
        # Regression: diag_deltaTime is the FRAME delta, smaller than the 0.1 s
        # PFH tick, so the eye ran ~8x slower than its taus.
        code = self._code(DRIVER)
        self.assertIn("diag_tickTime", code)
        self.assertIn("eyeLastTick", code)

    def test_driver_detects_a_time_skip_and_re_seeds(self):
        # A skip jumps the world clock; the eye must arrive adapted, not chase.
        code = self._code(DRIVER)
        self.assertIn("dayTime", code)
        self.assertIn("FUNC(eyeTimeSkip)", code)
        self.assertIn("eyeLastHour", code)
        self.assertIn("if (_skipped) then", code)


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
        "eyeTimeSkip",
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


class TestEyeAmbientLux(unittest.TestCase):
    """The night ambient comes from the physical sky, not the engine.

    Regression for the operator report (night too dim, local lights
    imperceptible).  The engine ambient brightness is a render artifact at an
    indoor scale at night (~51 lx in the report), two orders of magnitude
    above the real night sky.  It must not override the physical
    starlight/moon/twilight model at or below the horizon.
    """

    def test_night_uses_the_physical_sky(self):
        # Physical moonlit sky 0.25 lx; engine ambient 51 (indoor scale).
        self.assertAlmostEqual(run_sqf(AMBIENT, [0.25, 51, 1, -10]), 0.25, places=6)

    def test_starlight_floor_is_kept(self):
        self.assertAlmostEqual(run_sqf(AMBIENT, [0.001, 51, 1, -40]), 0.001, places=6)

    def test_twilight_uses_the_physical_glow(self):
        self.assertAlmostEqual(run_sqf(AMBIENT, [6.3, 51, 1, -6]), 6.3, places=6)

    def test_day_uses_the_engine_ambient(self):
        # The physical model has no daylight term; the engine supplies it.
        self.assertAlmostEqual(run_sqf(AMBIENT, [0.001, 84987, 1, 30]), 84987, places=3)

    def test_horizon_hands_over_to_the_engine(self):
        self.assertAlmostEqual(run_sqf(AMBIENT, [398, 5000, 1, 0.5]), 5000, places=3)


class TestEyeLocalLux(unittest.TestCase):
    """The night local light is the physical scan, not the engine.

    Regression for the operator report.  The engine getLightingAt dynamic term
    reads an indoor-scale value at night (~46 lx in the RPT) with no physical
    meaning, and it moves with the camera, so any movement moved the aperture
    target.  The gate discards it at or below the horizon, exactly as
    fnc_eyeAmbientLux discards the engine ambient.
    """

    def test_night_uses_the_physical_local(self):
        # Physical local 0 lx (no lamp); engine dynamic 46.45 (RPT night value).
        self.assertAlmostEqual(
            run_sqf(LOCAL, [0, 46.4537, 1, 0, 0, -31.35]), 0, places=9
        )

    def test_night_keeps_a_real_local_light(self):
        # A physical lamp (aee_core_dynamicLux) is not gated.
        self.assertAlmostEqual(
            run_sqf(LOCAL, [50, 46.4537, 1, 0, 0, -31.35]), 50, places=6
        )

    def test_starlight_floor_is_kept(self):
        self.assertAlmostEqual(run_sqf(LOCAL, [0.01, 51, 1, 0, 0, -40]), 0.01, places=6)

    def test_day_uses_the_engine_local(self):
        self.assertAlmostEqual(run_sqf(LOCAL, [0, 300, 1, 0, 0, 30]), 300, places=3)

    def test_horizon_hands_over_to_the_engine(self):
        self.assertAlmostEqual(run_sqf(LOCAL, [0.2, 300, 1, 0, 0, 0.5]), 300, places=3)

    def test_blinding_is_gated_with_the_engine_term(self):
        # The blinding term rides the same gate; a zero scale keeps it out.
        self.assertAlmostEqual(run_sqf(LOCAL, [0, 0, 1, 900, 0, -20]), 0, places=9)
        # Above the horizon it adds at its scale.
        self.assertAlmostEqual(run_sqf(LOCAL, [0, 0, 1, 900, 0.01, 30]), 9, places=3)


class TestEyeSceneComposition(unittest.TestCase):
    """The gated scene composition: a movement flicker cannot move it at night.

    The RPT night scene read 46.45 lx against a physical ambient of 0.143 lx,
    so the eye sat at an indoor aperture (32.8).  With the engine local term
    gated, the night scene is the physical sky, and the movement swing in the
    engine value no longer moves the target.
    """

    def _scene(self, phys_ambient, eng_ambient, phys_local, eng_local, sun_elev, sky):
        ambient = run_sqf(AMBIENT, [phys_ambient, eng_ambient, 1, sun_elev])
        local = run_sqf(LOCAL, [phys_local, eng_local, 1, 0, 0, sun_elev])
        return run_sqf(SCENE_LUX, [ambient, local, sky])

    def test_night_scene_is_the_physical_sky(self):
        # RPT values: ambient 0.142886 lx, engine ambient 51, engine local
        # 46.4537, sun -31.35 deg, open sky.
        scene = self._scene(0.142886, 51, 0, 46.4537, -31.35, 1)
        self.assertAlmostEqual(scene, 0.142886, places=5)

    def test_night_aperture_opens(self):
        # The night aperture moves from the indoor RPT value (32.8) to the
        # physical-sky value, wide open.  A lower aperture is more light.
        scene = self._scene(0.142886, 51, 0, 46.4537, -31.35, 1)
        v = run_sqf(APERTURE, [scene])
        self.assertLess(v, 20)
        self.assertGreater(run_sqf(APERTURE, [46.4537]), v)

    def test_movement_flicker_does_not_move_the_night_scene(self):
        # The engine local value swings with the camera in the RPT (11.6 to
        # 189.6).  Both ends give the same physical night scene.
        low = self._scene(0.142886, 51, 0, 11.58, -31.35, 1)
        high = self._scene(0.142886, 51, 0, 189.55, -31.35, 1)
        self.assertAlmostEqual(low, high, places=9)
        self.assertAlmostEqual(low, 0.142886, places=5)

    def test_a_real_night_light_still_raises_the_scene(self):
        lit = self._scene(0.142886, 51, 50, 46.4537, -31.35, 1)
        self.assertAlmostEqual(lit, 50.142886, places=4)


class TestEyeNightAndDayAperture(unittest.TestCase):
    """The aperture the eye pins at a real night and at noon."""

    def test_moonlit_night_is_wide(self):
        # 0.25 lx moonlit night -> a wide aperture, not the indoor value (~33).
        v = run_sqf(APERTURE, [0.25])
        self.assertGreater(v, 12)
        self.assertLess(v, 20)

    def test_starlight_is_wide(self):
        self.assertLess(run_sqf(APERTURE, [0.001]), 12)

    def test_noon_is_the_daylight_anchor(self):
        # RPT day adaptedLux 68036 -> near the BIKI daylight outdoor point.
        v = run_sqf(APERTURE, [68036])
        self.assertGreater(v, 46.0)
        self.assertLess(v, 50.5)

    def test_a_local_light_raises_the_adapted_aperture(self):
        # A 50 lx lamp on a 0.25 lx night must visibly raise the adaptation.
        dark = run_sqf(SCENE_LUX, [0.25, 0, 0.8])
        lit = run_sqf(SCENE_LUX, [0.25, 50, 0.8])
        self.assertLess(dark, lit)
        self.assertGreater(run_sqf(APERTURE, [lit]), run_sqf(APERTURE, [dark]) + 5)


# ─── Driver default settings, mirrored for the transient simulation ─────────
RHO = 0.18
TAU_LIGHT = 2.0
TAU_DARK_CONE = 120.0
TAU_DARK_ROD = 400.0
LN20 = math.log(20.0)


def scene_target(scene_lux, rho=RHO):
    """The driver's target log-luminance for a scene illuminance, lx."""
    return math.log10(max(rho * scene_lux / math.pi, 1e-9))


def pool_step(state, target, dt):
    cone, rod = state
    tau_c = TAU_LIGHT if target >= cone else TAU_DARK_CONE
    tau_r = TAU_LIGHT if target >= rod else TAU_DARK_ROD
    return [
        cone + (target - cone) * (1 - math.exp(-dt / tau_c)),
        rod + (target - rod) * (1 - math.exp(-dt / tau_r)),
    ]


def adapted_aperture(state, scene_lux, rho=RHO):
    """The aperture the driver pins for a pool state and the current scene."""
    lum = rho * scene_lux / math.pi
    w = mesopic_weight(lum)
    x = w * state[0] + (1 - w) * state[1]
    return aperture((math.pi / rho) * (10**x))


def pupil_implied_loglum(d):
    """Mirror of the driver's inversion of the pupil fit to a log-luminance."""
    u = max(-0.999, min(0.999, (4.9 - d) / 3.0))
    log_b = (0.5 * math.log((1 + u) / (1 - u))) / 0.4 - 0.5
    return math.log10(3.183 * (10**log_b))


class TestEyeAdaptInit(unittest.TestCase):
    """A night start is already dark-adapted, a day start light-adapted."""

    def test_night_start_is_dark_adapted(self):
        x = scene_target(0.1)  # a dark night
        got = run_sqf(ADAPT_INIT, [x])
        self.assertAlmostEqual(got[0], x, places=6)
        self.assertAlmostEqual(got[1], x, places=6)

    def test_day_start_is_light_adapted(self):
        x = scene_target(10000.0)
        got = run_sqf(ADAPT_INIT, [x])
        self.assertAlmostEqual(got[0], x, places=6)
        self.assertAlmostEqual(got[1], x, places=6)

    def test_day_init_is_far_above_night_init(self):
        night = run_sqf(ADAPT_INIT, [scene_target(0.1)])[0]
        day = run_sqf(ADAPT_INIT, [scene_target(10000.0)])[0]
        self.assertGreater(day, night + 3.0)


class TestEyeAdaptState(unittest.TestCase):
    """The published direction, effective tau and time to adapt."""

    def test_settled_reports_nothing_pending(self):
        # A settled eye has no adaptation pending: direction 0, tau 0, time 0.
        d, tau, t = run_sqf(ADAPT_STATE, [[0, 0], 0, 1, 2, 120, 400])
        self.assertEqual(d, 0)
        self.assertEqual(tau, 0)
        self.assertEqual(t, 0)

    def test_settled_pool_a_hair_above_target_still_reports_nothing(self):
        # Regression for the RPT defect: a settled eye whose rod pool sits a
        # floating-point hair above the target flipped the tau comparison to
        # the 400 s rod dark branch and reported a ~20 minute time to adapt
        # (adapt=[-1.54151,0.501617,0,1198.29]).  The settled guard must win.
        target = -1.54151
        d, tau, t = run_sqf(
            ADAPT_STATE, [[target, target + 1e-9], target, 1, 2, 120, 400]
        )
        self.assertEqual(d, 0)
        self.assertEqual(tau, 0)
        self.assertEqual(t, 0)

    def test_light_adapting_uses_the_light_tau(self):
        d, tau, t = run_sqf(ADAPT_STATE, [[-2, -2], 2, 1, 2, 120, 400])
        self.assertEqual(d, 1)
        self.assertAlmostEqual(tau, 2.0, places=6)
        # delta is 4 log10; the time is tau * ln(delta / settled).
        self.assertAlmostEqual(t, 2.0 * math.log(4.0 / 0.05), places=4)

    def test_dark_adapting_uses_the_rod_tau(self):
        d, tau, t = run_sqf(ADAPT_STATE, [[2, 2], -2, 1, 2, 120, 400])
        self.assertEqual(d, -1)
        self.assertAlmostEqual(tau, 400.0, places=6)
        self.assertAlmostEqual(t, 400.0 * math.log(4.0 / 0.05), places=3)

    def test_mesopic_level_weights_the_pools(self):
        # Level = 0.5*(-4) + 0.5*(0) = -2, target +2 -> light-adapting.
        d, _tau, _t = run_sqf(ADAPT_STATE, [[-4, 0], 2, 0.5, 2, 120, 400])
        self.assertEqual(d, 1)

    def test_time_to_adapt_falls_as_the_eye_approaches(self):
        # Regression for the false stuckAdaptation flag: the reported time must
        # shrink as the remaining gap shrinks, or the monitor's "time did not
        # fall" test fires on every adapting window.  Same pools, smaller gap.
        _d, _tau, near = run_sqf(ADAPT_STATE, [[-2, -2], 0, 1, 2, 120, 400])
        _d, _tau, far = run_sqf(ADAPT_STATE, [[-2, -2], 2, 1, 2, 120, 400])
        self.assertLess(near, far)
        self.assertGreater(near, 0)


class TestEyeAdaptationTransient(unittest.TestCase):
    """The eye overshoots then settles.

    Dark to bright is a brief over-brightness (the aperture is still wide), and
    bright to dark is a brief under-brightness (the aperture is still narrow).
    Simulated through the real pool kernel and the aperture mirror.
    """

    DARK = 0.1
    BRIGHT = 10000.0
    DT = 0.05

    def _settle(self, scene_lux, seconds=4000.0):
        state = run_sqf(ADAPT_INIT, [scene_target(scene_lux)])
        for _ in range(int(seconds / self.DT)):
            state = pool_step(state, scene_target(scene_lux), self.DT)
        return state

    def test_dark_to_bright_overshoots_bright_then_settles(self):
        dark = self._settle(self.DARK)
        transient = adapted_aperture(dark, self.BRIGHT)
        settle = adapted_aperture(self._settle(self.BRIGHT), self.BRIGHT)
        # The transient aperture is wider (less light intake) -> over-bright.
        self.assertLess(transient, settle)
        state = dark
        for _ in range(int((10 * TAU_LIGHT) / self.DT)):
            state = pool_step(state, scene_target(self.BRIGHT), self.DT)
        self.assertAlmostEqual(adapted_aperture(state, self.BRIGHT), settle, delta=1.5)

    def test_bright_to_dark_undershoots_dark_then_recovers(self):
        bright = self._settle(self.BRIGHT)
        transient = adapted_aperture(bright, self.DARK)
        settle = adapted_aperture(self._settle(self.DARK), self.DARK)
        # The transient aperture is narrower (more light intake) -> under-bright.
        self.assertGreater(transient, settle)
        # Dark adaptation is slow: after 30 s it is still clearly under-bright.
        state = bright
        for _ in range(int(30.0 / self.DT)):
            state = pool_step(state, scene_target(self.DARK), self.DT)
        self.assertGreater(adapted_aperture(state, self.DARK), settle + 1.0)


class TestEyeApertureResponse(unittest.TestCase):
    """The closing response to a whole-scene step is not instant.

    Regression for the operator report: the aperture "closed very quickly when
    moving".  The aperture must follow the neural light adaptation (seconds),
    not the 0.25 s pupil reflex alone.  The opening side (dark adaptation) is
    minutes and must stay that way.  Simulated through the real pupil, pool and
    aperture kernels, with the driver's fast/slow blend.
    """

    DT = 0.25
    DARK = 0.1
    BRIGHT = 1000.0
    KP = 0.35  # the driver eyeFastBlend default

    def _step(self, pools, pupil, scene_lux):
        lum = RHO * scene_lux / math.pi
        d_steady = run_sqf(PUPIL_STEADY, [lum])
        pupil = run_sqf(PUPIL_STEP, [pupil, d_steady, self.DT, 0.25, 0.475])
        pools = run_sqf(
            ADAPT_STEP,
            [
                pools,
                scene_target(scene_lux),
                self.DT,
                TAU_LIGHT,
                TAU_DARK_CONE,
                TAU_DARK_ROD,
                0,
            ],
        )
        return pools, pupil

    def _settle(self, scene_lux, seconds=200.0):
        pools = run_sqf(ADAPT_INIT, [scene_target(scene_lux)])
        pupil = run_sqf(PUPIL_STEADY, [RHO * scene_lux / math.pi])
        for _ in range(int(seconds / self.DT)):
            pools, pupil = self._step(pools, pupil, scene_lux)
        return pools, pupil

    def _aperture(self, pools, pupil, scene_lux):
        lum = RHO * scene_lux / math.pi
        w = mesopic_weight(lum)
        x_slow = w * pools[0] + (1 - w) * pools[1]
        x = (1 - self.KP) * x_slow + self.KP * pupil_implied_loglum(pupil)
        return run_sqf(APERTURE, [(math.pi / RHO) * (10**x)])

    def _run(self, pools, pupil, scene_lux, seconds):
        for _ in range(int(seconds / self.DT)):
            pools, pupil = self._step(pools, pupil, scene_lux)
        return pools, pupil

    def test_closing_step_is_not_instant(self):
        pools, pupil = self._settle(self.DARK)
        start = self._aperture(pools, pupil, self.BRIGHT)
        settled = self._aperture(*self._settle(self.BRIGHT), self.BRIGHT)
        pools, pupil = self._step(pools, pupil, self.BRIGHT)
        after_one_tick = self._aperture(pools, pupil, self.BRIGHT)
        # One 0.25 s tick moves the aperture, but well short of the settled
        # value: the pupil reflex alone must not snap it shut.
        self.assertGreater(after_one_tick, start)
        self.assertLess(after_one_tick - start, 0.5 * (settled - start))

    def test_closing_reaches_the_settled_value_in_seconds(self):
        pools, pupil = self._settle(self.DARK)
        settled = self._aperture(*self._settle(self.BRIGHT), self.BRIGHT)
        pools, pupil = self._run(pools, pupil, self.BRIGHT, 6.0)
        self.assertAlmostEqual(
            self._aperture(pools, pupil, self.BRIGHT), settled, delta=2.0
        )

    def test_opening_side_is_unchanged(self):
        # Bright to dark: the rod pool is minutes, so after 30 s the aperture
        # is still far from the settled dark value.
        pools, pupil = self._settle(self.BRIGHT)
        settled = self._aperture(*self._settle(self.DARK), self.DARK)
        pools, pupil = self._run(pools, pupil, self.DARK, 30.0)
        self.assertGreater(self._aperture(pools, pupil, self.DARK), settled + 1.0)

    def test_closing_is_faster_than_opening(self):
        # The physiological asymmetry is kept: a whole-scene brightening
        # settles in seconds, a darkening in minutes.
        close_start_state = self._settle(self.DARK)
        close_start = self._aperture(*close_start_state, self.BRIGHT)
        close_settled = self._aperture(*self._settle(self.BRIGHT), self.BRIGHT)
        c = self._run(*close_start_state, self.BRIGHT, 6.0)
        close_frac = (self._aperture(*c, self.BRIGHT) - close_start) / (
            close_settled - close_start
        )

        open_start_state = self._settle(self.BRIGHT)
        open_start = self._aperture(*open_start_state, self.DARK)
        open_settled = self._aperture(*self._settle(self.DARK), self.DARK)
        o = self._run(*open_start_state, self.DARK, 6.0)
        open_frac = (open_start - self._aperture(*o, self.DARK)) / (
            open_start - open_settled
        )

        self.assertGreater(close_frac, open_frac)


class TestEyeLimits(unittest.TestCase):
    """Human limits: scotopic acuity, colour loss, dark noise, scattered glare.

    The glare term is angular scatter, not an on-axis-or-nothing cone: a source
    off to the side is dimmer by angle but never zero, and fog adds in-scatter.
    """

    def test_photopic_is_unimpaired(self):
        a, c, n, g = run_sqf(LIMITS, [100, 1, 0, 0, 0])
        self.assertAlmostEqual(a, 1.0, places=6)
        self.assertAlmostEqual(c, 0.0, places=6)
        self.assertAlmostEqual(n, 0.0, places=6)
        self.assertAlmostEqual(g, 0.0, places=6)

    def test_scotopic_acuity_has_a_floor(self):
        a, _c, _n, _g = run_sqf(LIMITS, [0.001, 0, 0, 0, 0])
        self.assertAlmostEqual(a, 0.15, places=6)

    def test_scotopic_is_achromatic(self):
        _a, c, _n, _g = run_sqf(LIMITS, [0.001, 0, 0, 0, 0])
        self.assertAlmostEqual(c, 1.0, places=6)

    def test_dark_noise_rises_as_the_light_falls(self):
        _a, _c, dim, _g = run_sqf(LIMITS, [0.01, 0, 0, 0, 0])
        _a, _c, bright, _g = run_sqf(LIMITS, [10, 0, 0, 0, 0])
        self.assertGreater(dim, bright)

    def test_on_axis_source_scatters(self):
        _a, _c, _n, g = run_sqf(LIMITS, [1, 1, 100, 0, 0])
        self.assertGreater(g, 0.5)

    def test_off_axis_source_is_not_zero(self):
        # A headlight off to the side is dimmer but still visible.
        _a, _c, _n, g = run_sqf(LIMITS, [1, 1, 100, 85, 0])
        self.assertGreater(g, 0.0)

    def test_scatter_decays_with_angle_but_never_reaches_zero(self):
        _a, _c, _n, on = run_sqf(LIMITS, [1, 1, 100, 0, 0])
        _a, _c, _n, far = run_sqf(LIMITS, [1, 1, 100, 179, 0])
        self.assertGreater(on, far)
        self.assertGreater(far, 0.0)

    def test_fog_adds_in_scatter(self):
        _a, _c, _n, clear = run_sqf(LIMITS, [1, 1, 100, 85, 0])
        _a, _c, _n, foggy = run_sqf(LIMITS, [1, 1, 100, 85, 1])
        self.assertGreater(foggy, clear)


class TestEyeTimeSkip(unittest.TestCase):
    """fnc_eyeTimeSkip runs from the real SQF.

    A skipTime jumps the world clock so the eye can arrive adapted (ADR-007).
    The threshold sits above the largest clock advance one tick can produce
    under time acceleration, and below the smallest useful skip.
    """

    def test_first_sample_is_not_a_skip(self):
        self.assertFalse(run_sqf(TIME_SKIP, [-1, 6.0]))

    def test_a_normal_tick_is_not_a_skip(self):
        # 0.1 s at 100x acceleration is 10 s of world time, about 0.0028 h.
        self.assertFalse(run_sqf(TIME_SKIP, [6.0, 6.00278, 0.05]))

    def test_a_forward_skip_is_detected(self):
        self.assertTrue(run_sqf(TIME_SKIP, [0.0, 12.0, 0.05]))

    def test_a_backward_skip_is_detected(self):
        self.assertTrue(run_sqf(TIME_SKIP, [12.0, 0.0, 0.05]))

    def test_the_midnight_wrap_is_the_short_way(self):
        # 23.99 -> 0.01 is 0.02 h forward, not 23.98 h back.
        self.assertFalse(run_sqf(TIME_SKIP, [23.99, 0.01, 0.05]))

    def test_a_small_move_stays_below_the_threshold(self):
        # 0.01 h is under the 0.05 h threshold; 0.06 h is over it.
        self.assertFalse(run_sqf(TIME_SKIP, [1.0, 1.01, 0.05]))
        self.assertTrue(run_sqf(TIME_SKIP, [1.0, 1.06, 0.05]))

    def test_the_threshold_param_is_honoured(self):
        self.assertTrue(run_sqf(TIME_SKIP, [0.0, 1.0, 0.05]))
        self.assertFalse(run_sqf(TIME_SKIP, [0.0, 1.0, 2.0]))


if __name__ == "__main__":
    unittest.main()
