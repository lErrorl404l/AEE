#!/usr/bin/env python3
"""Human-vision model: the ColorCorrections contract and the pure kernels.

The pure kernels run here from their real SQF through tools/tests/sqf_lite.py.
The engine-touching driver and the wiring are source-contracted.

The mandatory gap-closing suite pins the exact seven-element ColorCorrections
contract and the identity-at-default image.  Source: BIKI Post Process
Effects, Wayback capture 20240220225631.  The contract is
[brightness, contrast, offset, blend, colorize, weights, radial].  The
colorize alpha (slot 4, the fourth value) is the desaturation amount: 0 keeps
the original colour, 1 is black and white times the colorize colour.  A
wrong-length array or a colorize alpha of 1 is the black-and-white class that
drained normal vision to grey.

Every constant is traced to a published source or marked UNSOURCED beside the
value in the SQF header.  The per-constant register is in
.omo/plans/aee-vision-model.md.
"""

import ast
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OPTICS = ROOT / "addons" / "optics"
GRADE = OPTICS / "functions" / "grade"
PERCEPTION = OPTICS / "functions" / "perception"

BASE_KERNEL = GRADE / "fnc_baseGradeParams.sqf"
DRIVER = GRADE / "fnc_applyBaseGrade.sqf"
TEARDOWN = GRADE / "fnc_teardownBaseGrade.sqf"
INIT = GRADE / "fnc_initBaseGrade.sqf"
TONE_KERNEL = PERCEPTION / "fnc_perceptionToneResponse.sqf"
COMPOSE_KERNEL = PERCEPTION / "fnc_perceptionParams.sqf"

OPTICS_PREP = OPTICS / "XEH_PREP.hpp"
OPTICS_POSTINIT = OPTICS / "XEH_postInit.sqf"
OPTICS_SETTINGS = OPTICS / "initSettings.inc.sqf"
OPTICS_STRINGS = OPTICS / "stringtable.xml"

REC709_WEIGHTS = [0.2126, 0.7152, 0.0722, 0]
RADIAL_DEFAULT = [-1, -1, 0, 0, 0, 0, 0]

# The all-stages-neutral composed ColorCorrections array: tone identity, no
# white balance, photopic mesopic fraction.  The colorize alpha is 0, the
# identity (BIKI capture 20240220225631).  This is the fixture the perception
# composition kernel must reproduce at neutral inputs.
NEUTRAL_FIXTURE = [
    1,
    1,
    0,
    [0, 0, 0, 0],
    [1, 1, 1, 0],
    [0.2126, 0.7152, 0.0722, 0],
    [-1, -1, 0, 0, 0, 0, 0],
]

GRADE_FUNCTIONS = [
    "baseGradeParams",
    "applyBaseGrade",
    "initBaseGrade",
    "teardownBaseGrade",
]

PERCEPTION_FUNCTIONS = [
    "perceptionToneResponse",
    "perceptionParams",
]


def _code(path):
    """The SQF source with its leading block-comment header removed."""
    text = path.read_text(encoding="utf-8")
    return text[text.index("*/") + 2 :] if "*/" in text else text


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
    alpha = colorize[3]
    luma = sum(w * c for w, c in zip(weights[:3], pixel))
    grey = [channel * luma for channel in colorize[:3]]
    return [p * (1 - alpha) + g * alpha for p, g in zip(pixel, grey)]


class TestColorCorrectionsContract(unittest.TestCase):
    """Pin the BIKI seven-element ColorCorrections contract.

    Source: BIKI Post Process Effects, Wayback capture 20240220225631.
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
        self.assertEqual(cc[6], RADIAL_DEFAULT)

    def test_colorize_alpha_is_the_last_value(self):
        cc, _ = run_sqf(BASE_KERNEL, [1.15, 1.0, -0.02, 0.4])
        self.assertEqual(cc[4][3], 0.4)

    def test_weight_slot_fourth_value_is_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[5][3], 0)


class TestNeutralFixtureIdentity(unittest.TestCase):
    """The all-stages-neutral fixture is the identity image.

    The colorize alpha is the desaturation amount, so a non-zero fixture alpha
    drains normal vision to black and white and must fail the suite.
    """

    def test_fixture_has_seven_elements(self):
        self.assertEqual(len(NEUTRAL_FIXTURE), 7)

    def test_fixture_colorize_alpha_is_zero(self):
        self.assertEqual(
            NEUTRAL_FIXTURE[4][3], 0, "the neutral fixture desaturates: alpha is not 0"
        )

    def test_fixture_tone_is_identity(self):
        self.assertEqual(NEUTRAL_FIXTURE[0:3], [1, 1, 0])

    def test_fixture_blend_and_radial_are_neutral(self):
        self.assertEqual(NEUTRAL_FIXTURE[3], [0, 0, 0, 0])
        self.assertEqual(NEUTRAL_FIXTURE[6], RADIAL_DEFAULT)

    def test_fixture_weight_array_is_rec709_and_nonzero(self):
        self.assertEqual(NEUTRAL_FIXTURE[5], REC709_WEIGHTS)
        self.assertNotEqual(NEUTRAL_FIXTURE[5][:3], [0, 0, 0])

    def test_fixture_pixel_is_unchanged(self):
        patch = [0.8, 0.2, 0.1]
        for got, want in zip(cc_contract_pixel(patch, NEUTRAL_FIXTURE), patch):
            self.assertAlmostEqual(got, want, places=9)


class TestDefaultPathColorizeAlpha(unittest.TestCase):
    """With the model enabled and the photopic default the alpha is 0.

    This is the shipped-defect class: the legacy kernel default and the
    neutral fixture must both leave the colour stage at identity.
    """

    def test_default_kernel_colorize_alpha_is_zero(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[4][3], 0, "the default path desaturates")

    def test_neutral_fixture_matches_the_shipped_default(self):
        self.assertEqual(NEUTRAL_FIXTURE[4][3], 0)
        self.assertEqual(NEUTRAL_FIXTURE[5], REC709_WEIGHTS)


class TestIdentityDetectsDesaturation(unittest.TestCase):
    """cc_contract_pixel proves the test detects the black-and-white class."""

    def test_alpha_zero_keeps_a_red_patch(self):
        patch = [0.8, 0.2, 0.1]
        out = cc_contract_pixel(patch, NEUTRAL_FIXTURE)
        for got, want in zip(out, patch):
            self.assertAlmostEqual(got, want, places=9)

    def test_alpha_one_turns_a_red_patch_grey(self):
        desaturated = list(NEUTRAL_FIXTURE)
        desaturated[4] = [1, 1, 1, 1]
        out = cc_contract_pixel([0.8, 0.2, 0.1], desaturated)
        self.assertAlmostEqual(out[0], out[1], places=9)
        self.assertAlmostEqual(out[1], out[2], places=9)


class TestPerceptionToneResponse(unittest.TestCase):
    """fnc_perceptionToneResponse runs from the real SQF and clamps.

    Source register: Naka and Rushton 1966 (form), CIE 15:2004 and ISO
    11664-4 (L*), Stevens 1957; the exact exponent, sigma and calibration
    gain are UNSOURCED.
    """

    def test_strength_zero_is_the_identity(self):
        self.assertEqual(run_sqf(TONE_KERNEL, [1, 100, 0, 1]), [1, 1, 0])

    def test_negative_strength_is_the_identity(self):
        self.assertEqual(run_sqf(TONE_KERNEL, [1, 100, -1, 1]), [1, 1, 0])

    def test_reference_adaptation_is_the_identity(self):
        self.assertEqual(run_sqf(TONE_KERNEL, [100, 100, 1, 1]), [1, 1, 0])

    def test_contrast_and_offset_stay_in_range_across_the_sweep(self):
        for lum in [1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, 1000, 1e4, 1e5]:
            brightness, contrast, offset = run_sqf(TONE_KERNEL, [lum, 100, 1, 1])
            self.assertGreaterEqual(contrast, 0.8)
            self.assertLessEqual(contrast, 1.6)
            self.assertGreaterEqual(offset, -0.05)
            self.assertLessEqual(offset, 0.05)
            self.assertGreaterEqual(brightness, 0.7)
            self.assertLessEqual(brightness, 1.3)

    def test_contrast_rises_as_the_luminance_leaves_mid(self):
        _, mid, _ = run_sqf(TONE_KERNEL, [100, 100, 1, 1])
        _, dark, _ = run_sqf(TONE_KERNEL, [1e-4, 100, 1, 1])
        _, bright, _ = run_sqf(TONE_KERNEL, [1e5, 100, 1, 1])
        self.assertGreater(dark, mid, "dark adaptation did not raise contrast")
        self.assertGreater(bright, mid, "bright adaptation did not raise contrast")

    def test_out_of_range_inputs_are_clamped(self):
        brightness, contrast, offset = run_sqf(TONE_KERNEL, [1e12, 1e-12, 99, 99])
        self.assertGreaterEqual(contrast, 0.8)
        self.assertLessEqual(contrast, 1.6)
        self.assertGreaterEqual(offset, -0.05)
        self.assertLessEqual(offset, 0.05)
        self.assertGreaterEqual(brightness, 0.7)
        self.assertLessEqual(brightness, 1.3)


def compose(args):
    """Run fnc_perceptionParams with fnc_perceptionToneResponse bound."""
    globals_ = {
        "__FUNC__perceptionToneResponse": lambda *a: run_sqf(TONE_KERNEL, list(a)),
    }
    return run_sqf(COMPOSE_KERNEL, args, globals_)


class TestPerceptionComposition(unittest.TestCase):
    """fnc_perceptionParams composes the light slice from the real SQF.

    Slice 1: the tone stage only.  The colour stage is identity, so the
    colorize alpha is 0 (BIKI capture 20240220225631).  The weight array is
    the Rec.709 luma.
    """

    def test_array_has_seven_elements(self):
        cc, _ = compose([])
        self.assertEqual(len(cc), 7)

    def test_default_inputs_keep_the_colorize_alpha_zero(self):
        cc, _ = compose([])
        self.assertEqual(cc[4][3], 0, "the default composition desaturates")

    def test_strength_zero_is_the_identity_fixture(self):
        cc, _ = compose([1, 1, [1, 1, 1], True, False, 0, 1])
        self.assertEqual(cc, NEUTRAL_FIXTURE)

    def test_disabled_tone_is_the_identity_fixture(self):
        cc, _ = compose([1, 1, [1, 1, 1], False, False, 1, 1])
        self.assertEqual(cc, NEUTRAL_FIXTURE)

    def test_weight_array_is_rec709(self):
        cc, _ = compose([])
        self.assertEqual(cc[5], REC709_WEIGHTS)

    def test_filmgrain_has_six_elements(self):
        _, grain = compose([])
        self.assertEqual(len(grain), 6)


STAND_DOWN_RE = re.compile(
    r"\[1, 1, 0, \[0,0,0,0\], \[1,1,1,0\], \[0\.2126,0\.7152,0\.0722,0\], "
    r"\[-1,-1,0,0,0,0,0\]\]"
)


class TestPerceptionDriverContract(unittest.TestCase):
    """Source contract for the driver's perception branch.

    The driver subsumes the base grade in place: it reads the published eye
    state and the model switch, branches to the perception kernel, keeps the
    registry keys, and stands down to the contract identity on normal vision
    only.
    """

    def test_driver_calls_both_kernels(self):
        code = _code(DRIVER)
        self.assertIn("FUNC(perceptionParams)", code)
        self.assertIn("FUNC(baseGradeParams)", code)
        self.assertIn("visionModelEnabled", code)

    def test_driver_reads_the_published_eye_state(self):
        code = _code(DRIVER)
        self.assertIn("eyeAdaptedLux", code, "adapted luminance is not read")
        self.assertIn("eyeMesopic", code, "the mesopic fraction is not read")

    def test_driver_publishes_the_state(self):
        code = _code(DRIVER)
        for name in (
            "baseGradeActive",
            "baseGradeCC",
            "baseGradeGrain",
            "visionModelActive",
        ):
            self.assertIn(f"QGVAR({name})", code, f"state {name} is not published")

    def test_stand_down_neutral_is_the_contract_identity(self):
        code = _code(DRIVER)
        self.assertIn(
            "[1, 1, 0, [0,0,0,0], [1,1,1,0], [0.2126,0.7152,0.0722,0], "
            "[-1,-1,0,0,0,0,0]]",
            code,
            "the stand-down neutral is not the contract identity",
        )
        self.assertNotIn("[1,1,1,1]", code, "the stand-down still desaturates")

    def test_stand_down_fixture_is_the_identity_image(self):
        code = _code(DRIVER)
        match = STAND_DOWN_RE.search(code)
        self.assertIsNotNone(
            match, "the stand-down identity is not the contract identity"
        )
        cc = ast.literal_eval(match.group())
        self.assertEqual(cc, NEUTRAL_FIXTURE)
        patch = [0.8, 0.2, 0.1]
        for got, want in zip(cc_contract_pixel(patch, cc), patch):
            self.assertAlmostEqual(got, want, places=9)

    def test_driver_creates_no_new_effect(self):
        code = _code(DRIVER)
        self.assertIn("EFUNC(core,createPPEffect)", code)
        self.assertNotIn("= ppEffectCreate", code, "the driver bypasses the registry")

    def test_vision_mode_gate_precedes_the_first_adjust(self):
        code = _code(DRIVER)
        gate = code.index("currentVisionMode")
        self.assertLess(gate, code.index("ppEffectAdjust _ccParams"))


class TestPerceptionDebugHooks(unittest.TestCase):
    """Each vision hook is read, and none is registered as a CBA setting."""

    HOOKS = ["visionForce", "visionForceLux", "visionForceMesopic"]

    def test_each_hook_is_read(self):
        code = _code(DRIVER)
        for hook in self.HOOKS:
            self.assertIn(hook, code, f"debug hook {hook} is not read")

    def test_hooks_are_not_cba_settings(self):
        declared = OPTICS_SETTINGS.read_text(encoding="utf-8")
        for name in self.HOOKS:
            self.assertNotRegex(
                declared,
                rf"AEE_SETTING_\w+\(\s*{name}\s*,",
                f"{name} is registered as a CBA setting",
            )

    def test_logs_one_debug_line_per_tick(self):
        code = _code(DRIVER)
        self.assertIn("AEE_LOG_DEBUG(_visionLog)", code)
        self.assertIn("vision model active=", code)
        for value in ("_adaptedLux", "_mesopicW", "select 1"):
            self.assertIn(value, code, f"the debug line omits {value}")


if __name__ == "__main__":
    unittest.main()
