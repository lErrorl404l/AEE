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
VISION_ADDON = ROOT / "addons" / "vision"
THERMAL = ROOT / "addons" / "thermal"

GRADE = VISION_ADDON / "functions" / "grade"
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

    def test_color_weight_is_zero_at_the_engine_neutral(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        weights = cc[5]
        self.assertEqual(weights, [0, 0, 0, 0])
        self.assertEqual(weights[:3], [0, 0, 0])

    def test_default_colorize_is_the_engine_neutral(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[4][3], 1)

    def test_saturation_flows_into_the_colorize_alpha(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0.4])
        # The engine neutral alpha is 1; a desaturation of 0.4 maps to 1 - 0.4.
        self.assertAlmostEqual(cc[4][3], 0.6, places=9)

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


def cc_contract_pixel(pixel, cc):
    """Model the BIKI ColorCorrections colour stage for one pixel.

    Source: BIKI Post Process Effects, Wayback capture 20240220225631.  The
    array is [brightness, contrast, offset, blend, colorize, weights, radial].
    The colorize alpha (slot 4) is the desaturation amount: 0 keeps the
    original colour, 1 is black and white times the colorize colour.  The
    weight array (slot 5) supplies the luma.  Only the colour stage is
    modelled: the order of the affine, blend and colorize stages is not
    documented, so this is used only for the order-independent property that
    alpha 0 preserves colour and alpha 1 is the grey class.
    """
    _brightness, _contrast, _offset, _blend, colorize, weights, _radial = cc
    if sum(weights[:3]) == 0 or colorize[3] >= 1:
        return list(pixel)
    amount = 1 - colorize[3]
    luma = sum(w * c for w, c in zip(weights[:3], pixel))
    grey = [channel * luma for channel in colorize[:3]]
    return [p * (1 - amount) + g * amount for p, g in zip(pixel, grey)]


class TestColorCorrectionsContract(unittest.TestCase):
    """Pin the BIKI seven-element ColorCorrections contract.

    A wrong-length array or a moved slot must fail here.  Source: BIKI Post
    Process Effects, Wayback capture 20240220225631.
    """

    def test_array_has_seven_elements(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(len(cc), 7)

    def test_blend_colorize_and_weights_are_four_vectors(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        for slot in (3, 4, 5):
            self.assertIsInstance(cc[slot], list, f"slot {slot} is not an array")
            self.assertEqual(len(cc[slot]), 4, f"slot {slot} is not [r,g,b,a]")

    def test_radial_slot_is_the_documented_default(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[6], [-1, -1, 0, 0, 0, 0, 0])

    def test_colorize_alpha_is_the_last_value(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0.4])
        self.assertEqual(cc[4][3], 0.6)

    def test_weight_slot_fourth_value_is_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[5][3], 0)


class TestBaseGradeIdentityAtDefault(unittest.TestCase):
    """At the shipped defaults the colour stage leaves the image unchanged.

    This is the gap-closing test.  The default colorize alpha is the
    desaturation amount, so a non-zero default drains normal vision to black
    and white and must fail the suite.
    """

    def test_default_colorize_is_the_engine_neutral(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[4][3], 1, "the default desaturates: alpha is not 1")

    def test_default_weights_are_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[5][:3], [0, 0, 0])

    def test_default_pixel_is_unchanged(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        patch = [0.8, 0.2, 0.1]
        for got, want in zip(cc_contract_pixel(patch, cc), patch):
            self.assertAlmostEqual(got, want, places=9)

    def test_detects_the_black_and_white_class(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        desaturated = list(cc)
        desaturated[4] = [1, 1, 1, 0]
        desaturated[5] = [0.2126, 0.7152, 0.0722, 0]
        out = cc_contract_pixel([0.8, 0.2, 0.1], desaturated)
        self.assertAlmostEqual(out[0], out[1], places=9)
        self.assertAlmostEqual(out[1], out[2], places=9)


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


def _code(path):
    """The SQF source with its leading block-comment header removed."""
    text = path.read_text(encoding="utf-8")
    return text[text.index("*/") + 2 :] if "*/" in text else text


DRIVER = GRADE / "fnc_applyBaseGrade.sqf"
INIT = GRADE / "fnc_initBaseGrade.sqf"
TEARDOWN = GRADE / "fnc_teardownBaseGrade.sqf"
THERMAL_DISPLAY = THERMAL / "functions" / "display" / "fnc_applyThermalVision.sqf"
# The create table moved off the per-entry path into its own function.
THERMAL_CREATE = THERMAL / "functions" / "display" / "fnc_createThermalPPEffects.sqf"
VISION_PREP = VISION_ADDON / "XEH_PREP.hpp"
VISION_POSTINIT = VISION_ADDON / "XEH_postInit.sqf"
VISION_SETTINGS = VISION_ADDON / "initSettings.inc.sqf"
VISION_STRINGS = VISION_ADDON / "stringtable.xml"
THERMAL_SETTINGS = THERMAL / "initSettings.inc.sqf"
THERMAL_STRINGS = THERMAL / "stringtable.xml"

BASE_GRADE_SETTINGS = [
    "baseGradeEnabled",
    "baseGradeContrast",
    "baseGradeBrightness",
    "baseGradeBlackPoint",
    "baseGradeSaturation",
    "baseGradeSharpness",
    "baseGradeGrain",
    "baseGradeAcuityEnabled",
]

THERMAL_SETTINGS_NAMES = [
    "thermalTemporalNoise",
    "thermalAgcHunt",
    "thermalAgcHuntPeriod",
    "thermalNucDrift",
    "thermalHotBloom",
    "thermalImperfectionsEnabled",
]

GRADE_FUNCTIONS = [
    "baseGradeParams",
    "applyBaseGrade",
    "initBaseGrade",
    "teardownBaseGrade",
]


class TestBaseGradeDriverContract(unittest.TestCase):
    """Source contract for the registry-owned base grade and acuity driver."""

    def test_recreation_goes_through_the_registry(self):
        code = _code(DRIVER)
        self.assertIn("EFUNC(lib,createPPEffect)", code)
        self.assertNotIn("= ppEffectCreate", code, "the driver bypasses the registry")

    def test_owns_the_two_named_keys_at_the_registry_priorities(self):
        code = _code(DRIVER)
        self.assertIn('"BaseGrade"', code)
        self.assertIn('"BaseAcuity"', code)
        self.assertIn("ColorCorrections", code)
        self.assertIn("FilmGrain", code)
        self.assertIn("1505", code)
        self.assertIn("2505", code)

    def test_vision_mode_gate_precedes_the_live_grade_adjust(self):
        code = _code(DRIVER)
        gate = code.index("currentVisionMode")
        self.assertLess(gate, code.index("ppEffectAdjust _ccParams"))
        self.assertLess(gate, code.index("ppEffectAdjust _grainParams"))

    def test_every_adjust_has_a_handle_guard(self):
        code = _code(DRIVER)
        adjusts = list(re.finditer(r"(\w+)\s+ppEffectAdjust", code))
        self.assertGreaterEqual(len(adjusts), 3, "expected the grade and grain adjusts")
        for match in adjusts:
            var = match.group(1)
            self.assertRegex(
                code[: match.start()],
                rf"if\s*\({var}\s*>=\s*0\)\s*then",
                f"adjust on {var} has no >= 0 guard before it",
            )

    def test_stand_down_neutral_is_the_contract_identity(self):
        code = _code(DRIVER)
        self.assertIn(
            "[1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]]",
            code,
            "the stand-down neutral is not the contract identity",
        )
        self.assertNotIn(
            "[0.2126,0.7152,0.0722,0]", code, "the stand-down still desaturates"
        )

    def test_teardown_neutral_is_the_contract_identity(self):
        code = _code(TEARDOWN)
        self.assertIn(
            "[1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]]",
            code,
            "the teardown neutral is not the contract identity",
        )
        self.assertNotIn(
            "[0.2126,0.7152,0.0722,0]", code, "the teardown still desaturates"
        )

    def test_reads_the_eight_image_settings(self):
        code = _code(DRIVER)
        for name in BASE_GRADE_SETTINGS:
            self.assertIn(name, code, f"setting {name} is not read")

    def test_publishes_the_state(self):
        code = _code(DRIVER)
        for name in ("baseGradeActive", "baseGradeCC", "baseGradeGrain"):
            self.assertIn(f"QGVAR({name})", code, f"state {name} is not published")

    def test_branches_onto_the_perception_model(self):
        code = _code(DRIVER)
        self.assertIn("FUNC(perceptionParams)", code, "the perception branch is absent")
        self.assertIn("FUNC(baseGradeParams)", code, "the legacy fallback is absent")
        self.assertIn("visionModelEnabled", code, "the model switch is not read")


class TestThermalIntegrationContract(unittest.TestCase):
    """The imperfection terms fold into the existing chain, no new effect."""

    def test_adds_no_new_pp_effect(self):
        # The display already owns a recreate loop; the integration must add
        # no new effect, so every create must draw its name from the table.
        # The table now lives in fnc_createThermalPPEffects; scan both files.
        code = _code(THERMAL_DISPLAY) + _code(THERMAL_CREATE)
        creates = list(re.finditer(r"ppEffectCreate\s*\[([^\]]*)\]", code))
        self.assertGreaterEqual(len(creates), 1)
        for match in creates:
            self.assertIn(
                "_name", match.group(1), f"a new effect is created: {match.group(0)}"
            )

    def test_calls_the_imperfection_kernel(self):
        code = _code(THERMAL_DISPLAY)
        self.assertIn("FUNC(thermalImperfectionParams)", code)

    def test_reads_the_four_force_hooks(self):
        code = _code(THERMAL_DISPLAY)
        for hook in ("bloomForce", "agcHuntForce", "nucForce", "temporalNoiseForce"):
            self.assertIn(hook, code, f"force hook {hook} is not read")

    def test_publishes_the_four_artefacts(self):
        code = _code(THERMAL_DISPLAY)
        for name in ("bloom", "agcHunt", "nucDrift", "temporalNoise"):
            self.assertIn(f"QGVAR({name})", code, f"state {name} is not published")


class TestImageRealismWiring(unittest.TestCase):
    """Functions are prepped, started, wired, and documented."""

    def test_every_grade_function_is_prepped(self):
        text = VISION_PREP.read_text(encoding="utf-8")
        for name in GRADE_FUNCTIONS:
            self.assertIn(f"PREPS(grade,{name});", text, f"{name} is not prepped")

    def test_postinit_starts_the_module_after_eye_adaptation(self):
        # initEyeAdaptation lives in aee_eye and initBaseGrade in aee_vision;
        # the grade starts after the eye module because vision lists aee_eye
        # in requiredAddons.
        text = VISION_POSTINIT.read_text(encoding="utf-8")
        self.assertIn("FUNC(initBaseGrade)", text)
        eye_post = (ROOT / "addons" / "eye" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("FUNC(initEyeAdaptation)", eye_post)
        cfg = (ROOT / "addons" / "vision" / "config.cpp").read_text(encoding="utf-8")
        self.assertIn('"aee_eye"', cfg)

    def test_vision_mode_branch_applies_the_grade(self):
        text = VISION_POSTINIT.read_text(encoding="utf-8")
        self.assertIn("FUNC(applyBaseGrade)", text)
        self.assertLess(
            text.index("FUNC(managePostProcess)"),
            text.index("FUNC(applyBaseGrade)"),
        )

    def test_teardown_releases_through_the_registry(self):
        code = _code(TEARDOWN)
        self.assertIn("EFUNC(lib,destroyPPEffect)", code)
        self.assertIn("QGVAR(baseGradePFH)", code)

    def test_settings_are_registered(self):
        optics = VISION_SETTINGS.read_text(encoding="utf-8")
        for name in BASE_GRADE_SETTINGS:
            self.assertIn(name, optics, f"setting {name} is not registered")
        self.assertIn('"AEE Vision","Image"', optics)
        thermal = THERMAL_SETTINGS.read_text(encoding="utf-8")
        for name in THERMAL_SETTINGS_NAMES:
            self.assertIn(name, thermal, f"setting {name} is not registered")
        self.assertIn('"AEE Thermal","Sensor"', thermal)

    def test_every_setting_has_name_and_description(self):
        optics = VISION_STRINGS.read_text(encoding="utf-8")
        for name in BASE_GRADE_SETTINGS:
            self.assertIn(f"STR_AEE_Vision_{name}_Name", optics)
            self.assertIn(f"STR_AEE_Vision_{name}_Description", optics)
        thermal = THERMAL_STRINGS.read_text(encoding="utf-8")
        for name in THERMAL_SETTINGS_NAMES:
            self.assertIn(f"STR_AEE_Thermal_{name}_Name", thermal)
            self.assertIn(f"STR_AEE_Thermal_{name}_Description", thermal)

    def test_stringtable_keys_are_sorted(self):
        optics = re.findall(
            r'<Key ID="(STR_AEE_Vision_\w+)"',
            VISION_STRINGS.read_text(encoding="utf-8"),
        )
        self.assertEqual(optics, sorted(optics), "optics keys are not sorted")
        thermal = re.findall(
            r'<Key ID="(STR_AEE_Thermal_\w+)"',
            THERMAL_STRINGS.read_text(encoding="utf-8"),
        )
        self.assertEqual(thermal, sorted(thermal), "thermal keys are not sorted")


class TestImageRealismDebugHooks(unittest.TestCase):
    """Every force hook is read, and none is registered as a CBA setting."""

    OPTICS_HOOKS = [
        "baseGradeForce",
        "baseGradeContrast",
        "baseGradeSharpness",
        "baseGradeGrain",
    ]
    THERMAL_HOOKS = [
        "bloomForce",
        "agcHuntForce",
        "nucForce",
        "temporalNoiseForce",
    ]

    def test_each_optics_hook_is_read(self):
        code = _code(DRIVER)
        for hook in self.OPTICS_HOOKS:
            self.assertIn(hook, code, f"debug hook {hook} is not read")

    def test_each_thermal_hook_is_read(self):
        code = _code(THERMAL_DISPLAY)
        for hook in self.THERMAL_HOOKS:
            self.assertIn(hook, code, f"debug hook {hook} is not read")

    def test_hooks_are_not_cba_settings(self):
        declared = VISION_SETTINGS.read_text(
            encoding="utf-8"
        ) + THERMAL_SETTINGS.read_text(encoding="utf-8")
        for name in ["baseGradeForce", *self.THERMAL_HOOKS]:
            self.assertNotRegex(
                declared,
                rf"AEE_SETTING_\w+\(\s*{name}\s*,",
                f"{name} is registered as a CBA setting",
            )


class TestBaseGradeRegistryOwnership(unittest.TestCase):
    """Only the grade driver names the registry keys; the teardown releases them."""

    def test_only_the_grade_driver_names_the_keys(self):
        stray = []
        for path in (ROOT / "addons").rglob("*.sqf"):
            text = path.read_text(encoding="utf-8")
            if '"BaseGrade"' in text or '"BaseAcuity"' in text:
                if GRADE not in path.parents:
                    stray.append(str(path.relative_to(ROOT)))
        self.assertEqual(stray, [])

    def test_teardown_releases_both_keys(self):
        code = (GRADE / "fnc_teardownBaseGrade.sqf").read_text(encoding="utf-8")
        self.assertIn('["optics", "BaseGrade"] call EFUNC(lib,destroyPPEffect)', code)
        self.assertIn('["optics", "BaseAcuity"] call EFUNC(lib,destroyPPEffect)', code)

    def test_grade_priorities_are_at_their_declared_slots(self):
        code = (GRADE / "fnc_applyBaseGrade.sqf").read_text(encoding="utf-8")
        self.assertRegex(
            code,
            r'\[\s*"optics"\s*,\s*"BaseGrade"\s*,\s*"ColorCorrections"\s*,\s*1505\s*,',
        )
        self.assertRegex(
            code,
            r'\[\s*"optics"\s*,\s*"BaseAcuity"\s*,\s*"FilmGrain"\s*,\s*2505\s*,',
        )


class TestBaseGradeHandleLifecycle(unittest.TestCase):
    """The driver reads the core registry owner record, not the unused mirror.

    The registry writes aee_core_ppHandle_optics_<key> on create and resets it
    to -1 on destroy.  The addon's own QGVAR(ppHandle_BaseGrade) mirror is
    never written, so reading it pinned the handle at -1 and recreated a live
    effect every tick.  These assertions pin the owner-record read and the
    missing-handle guard.
    """

    def setUp(self):
        self.driver = _code(DRIVER)
        self.teardown = _code(TEARDOWN)

    def test_driver_reads_both_owner_records(self):
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseGrade), -1]",
            self.driver,
        )
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseAcuity), -1]",
            self.driver,
        )

    def test_driver_does_not_read_the_legacy_mirror_as_the_handle(self):
        self.assertNotIn("getVariable [QGVAR(ppHandle_BaseGrade)", self.driver)
        self.assertNotIn("getVariable [QGVAR(ppHandle_BaseAcuity)", self.driver)

    def test_teardown_reads_both_owner_records(self):
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseGrade), -1]",
            self.teardown,
        )
        self.assertIn(
            "missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseAcuity), -1]",
            self.teardown,
        )

    def test_recreate_sits_inside_the_missing_handle_guard(self):
        self.assertRegex(
            self.driver,
            r"if\s*\(_hCC\s*<\s*0\)\s*then\s*\{[^}]*"
            r'\["optics",\s*"BaseGrade"\]\s*call\s*EFUNC\(lib,destroyPPEffect\)'
            r"[^}]*EFUNC\(lib,createPPEffect\)[^}]*\}",
        )
        self.assertRegex(
            self.driver,
            r"if\s*\(_hAcuity\s*<\s*0\)\s*then\s*\{[^}]*"
            r'\["optics",\s*"BaseAcuity"\]\s*call\s*EFUNC\(lib,destroyPPEffect\)'
            r"[^}]*EFUNC\(lib,createPPEffect\)[^}]*\}",
        )

    def test_registry_lifecycle_feeds_the_owner_record(self):
        create = (
            ROOT / "addons" / "lib" / "functions" / "fnc_createPPEffect.sqf"
        ).read_text(encoding="utf-8")
        destroy = (
            ROOT / "addons" / "lib" / "functions" / "fnc_destroyPPEffect.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "missionNamespace setVariable "
            "[format [QEGVAR(core,ppHandle_%1_%2), _scope, _key], _handle]",
            create,
        )
        self.assertIn(
            "missionNamespace setVariable "
            "[format [QEGVAR(core,ppHandle_%1_%2), _parts select 0, _parts select 1], -1]",
            destroy,
        )


if __name__ == "__main__":
    unittest.main()
