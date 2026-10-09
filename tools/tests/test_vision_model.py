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
VISION_ADDON = ROOT / "addons" / "vision"
GRADE = VISION_ADDON / "functions" / "grade"
PERCEPTION = VISION_ADDON / "functions" / "perception"

BASE_KERNEL = GRADE / "fnc_baseGradeParams.sqf"
DRIVER = GRADE / "fnc_applyBaseGrade.sqf"
TEARDOWN = GRADE / "fnc_teardownBaseGrade.sqf"
INIT = GRADE / "fnc_initBaseGrade.sqf"
TONE_KERNEL = PERCEPTION / "fnc_perceptionToneResponse.sqf"
COMPOSE_KERNEL = PERCEPTION / "fnc_perceptionParams.sqf"
ILLUMINANT_KERNEL = PERCEPTION / "fnc_perceptionIlluminant.sqf"
CHROMA_KERNEL = PERCEPTION / "fnc_perceptionChromaticAdaptation.sqf"
MESOPIC_KERNEL = PERCEPTION / "fnc_perceptionMesopicColor.sqf"
BASE_ANCHOR_KERNEL = PERCEPTION / "fnc_perceptionBaseGrade.sqf"

VISION_PREP = VISION_ADDON / "XEH_PREP.hpp"
VISION_POSTINIT = VISION_ADDON / "XEH_postInit.sqf"
VISION_SETTINGS = VISION_ADDON / "initSettings.inc.sqf"
VISION_STRINGS = VISION_ADDON / "stringtable.xml"

REC709_WEIGHTS = [0.2126, 0.7152, 0.0722, 0]
RADIAL_DEFAULT = [-1, -1, 0, 0, 0, 0, 0]

# The all-stages-neutral composed ColorCorrections array: tone identity, no
# white balance, photopic mesopic fraction.  The identity is the engine's own
# neutral post-process (CfgPostProcessTemplates >> Default >> colorCorrections =
# {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}}): colorize alpha 1 and zero weights.
# This is the fixture the perception composition kernel must reproduce.
NEUTRAL_FIXTURE = [
    1,
    1,
    0,
    [0, 0, 0, 0],
    [1, 1, 1, 1],
    [0, 0, 0, 0],
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
    "perceptionIlluminant",
    "perceptionChromaticAdaptation",
    "perceptionMesopicColor",
    "perceptionBaseGrade",
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
    # The engine neutral is colorize alpha 1 with zero desaturation weights
    # (CfgPostProcessTemplates >> Default >> colorCorrections).  Zero weights
    # means the engine applies no desaturation, and colorize alpha 1 preserves
    # the original colour.  A lower alpha blends toward the desaturation target.
    if sum(weights[:3]) == 0 or colorize[3] >= 1:
        return list(pixel)
    amount = 1 - colorize[3]
    luma = sum(w * c for w, c in zip(weights[:3], pixel))
    grey = [channel * luma for channel in colorize[:3]]
    return [p * (1 - amount) + g * amount for p, g in zip(pixel, grey)]


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
        # The engine neutral alpha is 1; a desaturation of 0.4 maps to 1 - 0.4.
        self.assertEqual(cc[4][3], 0.6)

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

    def test_fixture_colorize_alpha_is_the_engine_neutral(self):
        self.assertEqual(
            NEUTRAL_FIXTURE[4][3], 1, "the neutral fixture desaturates: alpha is not 1"
        )

    def test_fixture_tone_is_identity(self):
        self.assertEqual(NEUTRAL_FIXTURE[0:3], [1, 1, 0])

    def test_fixture_blend_and_radial_are_neutral(self):
        self.assertEqual(NEUTRAL_FIXTURE[3], [0, 0, 0, 0])
        self.assertEqual(NEUTRAL_FIXTURE[6], RADIAL_DEFAULT)

    def test_fixture_weight_array_is_zero(self):
        self.assertEqual(NEUTRAL_FIXTURE[5], [0, 0, 0, 0])
        self.assertEqual(NEUTRAL_FIXTURE[5][:3], [0, 0, 0])

    def test_fixture_pixel_is_unchanged(self):
        patch = [0.8, 0.2, 0.1]
        for got, want in zip(cc_contract_pixel(patch, NEUTRAL_FIXTURE), patch):
            self.assertAlmostEqual(got, want, places=9)


class TestDefaultPathColorizeAlpha(unittest.TestCase):
    """With the model enabled and the photopic default the alpha is 0.

    This is the shipped-defect class: the legacy kernel default and the
    neutral fixture must both leave the colour stage at identity.
    """

    def test_default_kernel_colorize_is_the_engine_neutral(self):
        cc, _ = run_sqf(BASE_KERNEL, [])
        self.assertEqual(cc[4][3], 1, "the default path desaturates")
        self.assertEqual(cc[5], [0, 0, 0, 0], "the default path has desaturation weights")

    def test_base_grade_acuity_grain_is_colour_not_monochrome(self):
        # BIKI capture 20240220225631: the Arma 3 FilmGrain monochromatic
        # parameter is 0 monochrome, any other value colour.  0 drains normal
        # vision to grey while the base grade is enabled.
        _, grain = run_sqf(BASE_KERNEL, [])
        self.assertEqual(len(grain), 6)
        self.assertNotEqual(grain[5], 0, "the acuity grain is monochrome")

    def test_default_perception_compose_keeps_the_mesopic_colour_identity(self):
        # The live driver passes desatMax 0, Purkinje 0 and desatAlpha 0; the
        # eye model publishes a mesopic fraction below 1 at dusk (RPT 0.983).
        # The colour stage must stay the identity on that branch.
        cc, _ = compose(
            [50, 0.98, [1, 1, 1], True, False, 0.25, 1, 0.9, 0, 0, [1, 1, 0], 0]
        )
        self.assertEqual(cc[4], [1, 1, 1, 1], "the default mesopic path desaturates")

    def test_perception_acuity_grain_is_colour_not_monochrome(self):
        _, grain = compose([])
        self.assertEqual(len(grain), 6)
        self.assertNotEqual(grain[5], 0, "the acuity grain is monochrome")

    def test_neutral_fixture_matches_the_shipped_default(self):
        self.assertEqual(NEUTRAL_FIXTURE[4][3], 1)
        self.assertEqual(NEUTRAL_FIXTURE[5], [0, 0, 0, 0])


class TestIdentityDetectsDesaturation(unittest.TestCase):
    """cc_contract_pixel proves the test detects the black-and-white class."""

    def test_alpha_zero_keeps_a_red_patch(self):
        patch = [0.8, 0.2, 0.1]
        out = cc_contract_pixel(patch, NEUTRAL_FIXTURE)
        for got, want in zip(out, patch):
            self.assertAlmostEqual(got, want, places=9)

    def test_a_desaturating_array_turns_a_red_patch_grey(self):
        desaturated = list(NEUTRAL_FIXTURE)
        desaturated[4] = [1, 1, 1, 0]
        desaturated[5] = REC709_WEIGHTS
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


class TestPerceptionIlluminant(unittest.TestCase):
    """fnc_perceptionIlluminant normalises the ambient colour to unit luma.

    Source register: Rec.709 luma weights (ITU-R BT.709-6).  The luma floor and
    the 0.5 to 2 channel clamp are UNSOURCED.
    """

    def test_black_input_asks_for_no_adaptation(self):
        self.assertEqual(run_sqf(ILLUMINANT_KERNEL, [[0, 0, 0]]), [1, 1, 1])

    def test_grey_input_is_neutral(self):
        self.assertEqual(run_sqf(ILLUMINANT_KERNEL, [[0.5, 0.5, 0.5]]), [1, 1, 1])

    def test_warm_input_lifts_green_to_one_and_lowers_blue(self):
        r, g, b = run_sqf(ILLUMINANT_KERNEL, [[1.0, 0.9, 0.6]])
        self.assertAlmostEqual(g, 1.0, places=2)
        self.assertLess(b, 1.0)
        self.assertGreater(r, 1.0)

    def test_blue_input_lowers_red_and_lifts_blue(self):
        r, g, b = run_sqf(ILLUMINANT_KERNEL, [[0.6, 0.9, 1.0]])
        self.assertLess(r, 1.0)
        self.assertGreater(b, 1.0)

    def test_every_channel_stays_in_range(self):
        for color in ([1e6, 1e-6, 1e-6], [0.001, 5, 0.001], [2.0, 1.0, 0.5]):
            for channel in run_sqf(ILLUMINANT_KERNEL, [color]):
                self.assertGreaterEqual(channel, 0.5)
                self.assertLessEqual(channel, 2)

    def test_malformed_and_near_black_inputs_fall_back(self):
        self.assertEqual(run_sqf(ILLUMINANT_KERNEL, ["not a colour"]), [1, 1, 1])
        self.assertEqual(run_sqf(ILLUMINANT_KERNEL, [[1, 2]]), [1, 1, 1])
        self.assertEqual(
            run_sqf(ILLUMINANT_KERNEL, [[0.00001, 0.00001, 0.00001]]), [1, 1, 1]
        )


class TestPerceptionChromaticAdaptation(unittest.TestCase):
    """fnc_perceptionChromaticAdaptation derives the ColorCorrections blend slot.

    Source register: von Kries 1902 and CAT16 (Li et al. 2017); the degree D is
    CIECAM02 (CIE 159:2004); the display-RGB diagonal and the cap are
    UNSOURCED.  The engine cannot express the cone matrix, so the blend slot
    carries the complementary tint in the display domain.
    """

    def test_degree_zero_is_the_identity(self):
        self.assertEqual(run_sqf(CHROMA_KERNEL, [[1.3, 1.0, 0.7], 0]), [1, 1, 1, 0])

    def test_neutral_illuminant_is_the_identity(self):
        self.assertEqual(run_sqf(CHROMA_KERNEL, [[1, 1, 1]]), [1, 1, 1, 0])

    def test_a_warm_illuminant_cools_the_blend(self):
        r, _g, _b, alpha = run_sqf(CHROMA_KERNEL, [[1.3, 1.0, 0.7]])
        self.assertGreater(alpha, 0)
        self.assertLess(r, 1.0, "a warm illuminant did not cool the blend")

    def test_a_blue_illuminant_warms_the_blend(self):
        r, _g, b, alpha = run_sqf(CHROMA_KERNEL, [[0.7, 1.0, 1.3]])
        self.assertGreater(alpha, 0)
        self.assertGreater(r, b, "a blue cast was not warmed")

    def test_degree_is_clamped_to_one(self):
        self.assertEqual(
            run_sqf(CHROMA_KERNEL, [[1.3, 1.0, 0.7], 2]),
            run_sqf(CHROMA_KERNEL, [[1.3, 1.0, 0.7], 1]),
        )

    def test_alpha_never_exceeds_the_cap(self):
        for cap in (0.0, 0.05, 0.25, 0.9):
            alpha = run_sqf(CHROMA_KERNEL, [[1.5, 1.0, 0.5], 1, cap])[3]
            self.assertGreaterEqual(alpha, 0)
            self.assertLessEqual(alpha, min(cap, 0.25))

    def test_malformed_illuminant_is_the_identity(self):
        self.assertEqual(run_sqf(CHROMA_KERNEL, ["x"]), [1, 1, 1, 0])
        self.assertEqual(run_sqf(CHROMA_KERNEL, [[1, 2]]), [1, 1, 1, 0])


class TestPerceptionMesopicColor(unittest.TestCase):
    """fnc_perceptionMesopicColor derives the ColorCorrections colorize slot.

    Source register: photopic fraction m (CIE 191:2010); scotopic peak 507 nm
    (CIE 1951 and CIE 018:2019).  The desaturation amplitude and the tint
    amplitude are UNSOURCED.  The colorize alpha is the engine desaturation
    amount (BIKI capture 20240220225631).
    """

    def test_photopic_is_the_identity(self):
        self.assertEqual(run_sqf(MESOPIC_KERNEL, [1]), [1, 1, 1, 0])

    def test_kernel_defaults_are_the_identity(self):
        # The latent parameter defaults must not desaturate a bare caller.
        # With the old defaults 0.3 / 0.5 this returns alpha 0.15.
        self.assertEqual(run_sqf(MESOPIC_KERNEL, [0.5]), [1, 1, 1, 0])

    def test_scotopic_raises_the_alpha_to_the_maximum(self):
        _r, _g, _b, alpha = run_sqf(MESOPIC_KERNEL, [0, 0.3, 0.5])
        self.assertAlmostEqual(alpha, 0.3, places=9)

    def test_scotopic_blue_exceeds_red(self):
        r, _g, b, _alpha = run_sqf(MESOPIC_KERNEL, [0, 0.3, 0.5])
        self.assertGreater(b, r, "the Purkinje shift did not move toward blue")

    def test_alpha_never_exceeds_half(self):
        for desat in (0.0, 0.3, 0.5, 0.9):
            alpha = run_sqf(MESOPIC_KERNEL, [0, desat, 0.5])[3]
            self.assertGreaterEqual(alpha, 0)
            self.assertLessEqual(alpha, 0.5)

    def test_negative_mesopic_is_clamped_to_scotopic(self):
        self.assertEqual(
            run_sqf(MESOPIC_KERNEL, [-1, 0.3, 0.5]),
            run_sqf(MESOPIC_KERNEL, [0, 0.3, 0.5]),
        )

    def test_out_of_range_inputs_are_clamped(self):
        self.assertEqual(run_sqf(MESOPIC_KERNEL, [2]), [1, 1, 1, 0])
        _r, _g, _b, alpha = run_sqf(MESOPIC_KERNEL, [0, 0.9, 2])
        self.assertLessEqual(alpha, 0.5)


class TestPerceptionBaseAnchor(unittest.TestCase):
    """fnc_perceptionBaseGrade bounds the composed grade to the vanilla anchor.

    The base game ships the neutral default grade brightness 1, contrast 1,
    offset 0 (a3\\functions_f\\config.cpp line 3553 of functions_f.pbo, build
    2025-08-11).  The kernel allows only a small bounded deviation: brightness
    within 0.03 either side of the anchor, contrast 0.00 to 0.08 above it,
    offset -0.02 to 0.00 from it, and a desaturation alpha 0 to 0.10.
    """

    def test_identity_inputs_return_the_anchor_and_zero_alpha(self):
        self.assertEqual(
            run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1, 1, 0], 1, 0]),
            [1, 1, 0, 0],
        )

    def test_contrast_clamps_to_the_upper_bound(self):
        # dc = (cT - 1) * s = 0.08 at cT 1.08, s 1.
        _b, c, _o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1.08, 0], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(c, 1.08, places=9)

    def test_contrast_cannot_fall_below_the_anchor(self):
        _b, c, _o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 0.8, 0], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(c, 1.0, places=9)

    def test_offset_clamps_to_the_lower_bound(self):
        # do = oT * s = -0.02 at oT -0.02, s 1.
        _b, _c, o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, -0.02], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(o, -0.02, places=9)

    def test_offset_cannot_rise_above_the_anchor(self):
        _b, _c, o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0.05], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(o, 0.0, places=9)

    def test_brightness_clamps_to_each_bound(self):
        b_hi, _c, _o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1.03, 1, 0], [1, 1, 0], 1, 0])
        b_lo, _c, _o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[0.97, 1, 0], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(b_hi, 1.03, places=9)
        self.assertAlmostEqual(b_lo, 0.97, places=9)

    def test_brightness_lower_bound_holds_beyond_the_boundary(self):
        # db = (0.5 - 1) * 1 = -0.5, far below the -0.03 bound.  Only the lower
        # clamp keeps the result at the bound; removing it returns 0.5 here.
        _b, _c, _o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[0.5, 1, 0], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(_b, 0.97, places=9)

    def test_offset_lower_bound_holds_beyond_the_boundary(self):
        # do = -0.5 * 1 = -0.5, far below the -0.02 bound.  Only the lower
        # clamp keeps the result at the bound; removing it returns -0.5 here.
        _b, _c, o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, -0.5], [1, 1, 0], 1, 0])
        self.assertAlmostEqual(o, -0.02, places=9)

    def test_alpha_clamps_to_the_upper_bound(self):
        _b, _c, _o, a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1, 1, 0], 1, 0.10])
        _b, _c, _o, a_over = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1, 1, 0], 1, 0.5])
        self.assertAlmostEqual(a, 0.10, places=9)
        self.assertAlmostEqual(a_over, 0.10, places=9)

    def test_alpha_cannot_go_negative(self):
        _b, _c, _o, a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1, 1, 0], 1, -1])
        self.assertAlmostEqual(a, 0.0, places=9)

    def test_out_of_range_input_still_returns_in_bound(self):
        b, c, o, a = run_sqf(
            BASE_ANCHOR_KERNEL, [[1e12, 1e12, 1e12], [1, 1, 0], 99, 99]
        )
        self.assertGreaterEqual(b, 0.97)
        self.assertLessEqual(b, 1.03)
        self.assertGreaterEqual(c, 1.0)
        self.assertLessEqual(c, 1.08)
        self.assertGreaterEqual(o, -0.02)
        self.assertLessEqual(o, 0.0)
        self.assertGreaterEqual(a, 0)
        self.assertLessEqual(a, 0.10)

    def test_malformed_tone_and_anchor_fall_back(self):
        self.assertEqual(
            run_sqf(BASE_ANCHOR_KERNEL, ["x", [1, 2], 1, 0]),
            [1, 1, 0, 0],
        )

    def test_absent_anchor_keeps_the_neutral_default(self):
        # One argument: the tone only.  The anchor parameter default is the
        # neutral triple, so the result is the identity grade.
        self.assertEqual(run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0]]), [1, 1, 0, 0])

    def test_non_numeric_anchor_falls_back(self):
        self.assertEqual(
            run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], ["x", 1, 0], 1, 0]),
            [1, 1, 0, 0],
        )

    def test_short_anchor_falls_back(self):
        self.assertEqual(
            run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1, 2], 1, 0]),
            [1, 1, 0, 0],
        )

    def test_driver_normalises_the_anchor_range(self):
        # The kernel guards the anchor type and length.  The driver owns the
        # numeric range: an out-of-range raw scalar falls back to the neutral
        # triple at run time.  This is the out-of-range half of the anchor
        # normalise contract; the absent half is the kernel fallback above.
        code = _code(DRIVER)
        self.assertIn("(_b >= 0) && (_b <= 4)", code)
        self.assertIn("(_c >= 0) && (_c <= 4)", code)
        self.assertIn("(_o >= -1) && (_o <= 1)", code)
        self.assertIn("_anchor = [1, 1, 0]", code)

    def test_a_non_neutral_anchor_shifts_the_bounds(self):
        b, c, o, _a = run_sqf(BASE_ANCHOR_KERNEL, [[1, 1, 0], [1.1, 1.2, -0.05], 1, 0])
        self.assertAlmostEqual(b, 1.1, places=9)
        self.assertAlmostEqual(c, 1.2, places=9)
        self.assertAlmostEqual(o, -0.05, places=9)


def compose(args):
    """Run fnc_perceptionParams with its sub-kernels bound."""
    globals_ = {
        "__FUNC__perceptionToneResponse": lambda *a: run_sqf(TONE_KERNEL, list(a)),
        "__FUNC__perceptionIlluminant": lambda *a: run_sqf(ILLUMINANT_KERNEL, list(a)),
        "__FUNC__perceptionChromaticAdaptation": lambda *a: run_sqf(
            CHROMA_KERNEL, list(a)
        ),
        "__FUNC__perceptionMesopicColor": lambda *a: run_sqf(MESOPIC_KERNEL, list(a)),
        "__FUNC__perceptionBaseGrade": lambda *a: run_sqf(BASE_ANCHOR_KERNEL, list(a)),
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

    def test_default_inputs_use_the_engine_neutral(self):
        cc, _ = compose([])
        self.assertEqual(cc[4][3], 1, "the default composition desaturates")
        self.assertEqual(cc[5], [0, 0, 0, 0], "the default composition has weights")

    def test_strength_zero_is_the_identity_fixture(self):
        cc, _ = compose([1, 1, [1, 1, 1], True, False, 0, 1])
        self.assertEqual(cc, NEUTRAL_FIXTURE)

    def test_disabled_tone_is_the_identity_fixture(self):
        cc, _ = compose([1, 1, [1, 1, 1], False, False, 1, 1])
        self.assertEqual(cc, NEUTRAL_FIXTURE)

    def test_default_weight_array_is_zero(self):
        cc, _ = compose([])
        self.assertEqual(cc[5], [0, 0, 0, 0])

    def test_filmgrain_has_six_elements(self):
        _, grain = compose([])
        self.assertEqual(len(grain), 6)

    def test_colour_slots_stay_neutral_when_the_colour_path_is_off(self):
        cc, _ = compose([1, 1, [1.0, 0.9, 0.6], True, False, 1, 1])
        self.assertEqual(cc[3], [0, 0, 0, 0])
        self.assertEqual(cc[4], [1, 1, 1, 1])


class TestPerceptionColourComposition(unittest.TestCase):
    """fnc_perceptionParams composes the colour stage from the real SQF.

    The colour stage is off when white balance is off and the scene is
    photopic, so the array is the identity.  A tinted illuminant with white
    balance on raises the blend alpha; a mesopic scene raises the colorize
    alpha (BIKI capture 20240220225631).
    """

    def test_colour_paths_off_is_the_identity_fixture(self):
        cc, _ = compose([1, 1, [1.0, 0.9, 0.6], True, False, 0, 1])
        self.assertEqual(cc, NEUTRAL_FIXTURE)

    def test_scotopic_raises_the_colorize_alpha(self):
        # desatAlpha 0.08 drives the bounded colorize alpha; the anchor is
        # appended before it.  The colorize RGB is the mesopic kernel output, so
        # it must be non-neutral and blue-shifted.  A neutral RGB would prove
        # the mesopic branch did not run.
        cc, _ = compose(
            [1, 0, [1, 1, 1], True, False, 1, 1, 0.9, 0.3, 0.5, [1, 1, 0], 0.08]
        )
        self.assertGreater(cc[4][3], 0)
        self.assertGreaterEqual(cc[4][3], 0.5)
        self.assertAlmostEqual(cc[4][3], 0.92, places=9)
        self.assertNotEqual(cc[4][:3], [1, 1, 1], "the mesopic kernel did not run")
        self.assertGreater(cc[4][2], cc[4][0], "the colorize is not blue-shifted")

    def test_warm_illuminant_with_white_balance_raises_the_blend_alpha(self):
        cc, _ = compose([1, 1, [1.0, 0.9, 0.6], True, True, 1, 1])
        self.assertGreater(cc[3][3], 0)

    def test_blue_illuminant_warms_the_blend(self):
        cc, _ = compose([1, 1, [0.6, 0.9, 1.0], True, True, 1, 1])
        self.assertGreater(cc[3][0], cc[3][2])

    def test_neutral_illuminant_keeps_the_blend_alpha_zero(self):
        cc, _ = compose([1, 1, [1, 1, 1], True, True, 1, 1])
        self.assertEqual(cc[3][3], 0)


STAND_DOWN_RE = re.compile(
    r"\[1, 1, 0, \[0,0,0,0\], \[1,1,1,1\], \[0,0,0,0\], "
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

    def test_driver_reads_the_ambient_colour_once(self):
        code = _code(DRIVER)
        self.assertEqual(
            code.count("getLightingAt"), 1, "the ambient colour is read more than once"
        )
        self.assertIn("select 0", code, "the ambient light colour element is not used")

    def test_driver_reads_the_force_illuminant_hook(self):
        self.assertIn("visionForceIlluminant", _code(DRIVER))

    def test_driver_caches_the_anchor_above_the_first_adjust(self):
        code = _code(DRIVER)
        # The anchor is read from the loaded config exactly once per session and
        # cached.  A second read, or a read below the first adjust, fails.
        self.assertEqual(code.count("getArray"), 1, "the anchor is read more than once")
        self.assertIn(
            "isNil QGVAR(visionBaseAnchor)", code, "the cache guard is missing"
        )
        self.assertIn(
            "setVariable [QGVAR(visionBaseAnchor)", code, "the anchor is not cached"
        )
        self.assertLess(
            code.index("getArray"),
            code.index("ppEffectAdjust"),
            "the anchor read is not above the first post-process adjust",
        )

    def test_driver_passes_the_colour_calibration_settings(self):
        code = _code(DRIVER)
        for name in (
            "visionAdaptationDegree",
            "visionMesopicDesaturation",
            "visionPurkinjeStrength",
        ):
            self.assertIn(name, code, f"setting {name} is not read")

    def test_driver_does_not_write_the_aperture(self):
        self.assertNotIn("setAperture", _code(DRIVER))

    def test_driver_publishes_the_state(self):
        code = _code(DRIVER)
        for name in (
            "baseGradeActive",
            "baseGradeCC",
            "baseGradeGrain",
            "visionModelActive",
            "visionBaseResolved",
        ):
            self.assertIn(f"QGVAR({name})", code, f"state {name} is not published")

    def test_stand_down_neutral_is_the_contract_identity(self):
        code = _code(DRIVER)
        self.assertIn(
            "[1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], "
            "[-1,-1,0,0,0,0,0]]",
            code,
            "the stand-down neutral is not the contract identity",
        )
        self.assertNotIn("[1,1,1,0]", code, "the stand-down still desaturates")

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
        self.assertIn("EFUNC(lib,createPPEffect)", code)
        self.assertNotIn("= ppEffectCreate", code, "the driver bypasses the registry")

    def test_vision_mode_gate_precedes_the_first_adjust(self):
        code = _code(DRIVER)
        gate = code.index("currentVisionMode")
        self.assertLess(gate, code.index("ppEffectAdjust _ccParams"))


class TestPerceptionColourContracts(unittest.TestCase):
    """Source and behaviour contracts for the colour stage.

    The composition kernel calls the three colour kernels and sets the blend
    and colorize slots; the driver calls the composition kernel.  No new
    post-process effect is created.  The stand-down neutral keeps the colorize
    alpha 0.  A warm illuminant with white balance off is the identity; with
    white balance on it raises the blend alpha.  The engine's unstated pipeline
    order is not asserted.
    """

    def test_composition_calls_each_colour_kernel(self):
        code = _code(COMPOSE_KERNEL)
        for name in (
            "perceptionBaseGrade",
            "perceptionIlluminant",
            "perceptionChromaticAdaptation",
            "perceptionMesopicColor",
        ):
            self.assertIn(f"FUNC({name})", code, f"the composition omits {name}")

    def test_composition_calls_the_anchor_clamp(self):
        # The composition must route the tone triple through the anchor clamp.
        # The behavioural proof is in TestPerceptionSmallBound: bypassing this
        # call returns the raw tone contrast, which reaches 1.6.
        self.assertIn(
            "call FUNC(perceptionBaseGrade)",
            _code(COMPOSE_KERNEL),
            "the composition does not clamp the grade to the anchor",
        )

    def test_composition_sets_the_blend_and_colorize_slots(self):
        code = _code(COMPOSE_KERNEL)
        self.assertIn("_blend", code, "the blend slot is not set")
        self.assertIn("_colorize", code, "the colorize slot is not set")

    def test_driver_calls_the_composition_kernel(self):
        self.assertIn("FUNC(perceptionParams)", _code(DRIVER))

    def test_no_new_post_process_effect(self):
        code = _code(DRIVER) + _code(COMPOSE_KERNEL)
        self.assertNotIn("ppEffectCreate", code, "a new effect is created")

    def test_stand_down_neutral_keeps_the_colorize_alpha_zero(self):
        code = _code(DRIVER)
        match = STAND_DOWN_RE.search(code)
        self.assertIsNotNone(match, "the stand-down identity is missing")
        cc = ast.literal_eval(match.group())
        self.assertEqual(cc[4][3], 1, "the stand-down desaturates")

    def test_warm_illuminant_with_white_balance_off_keeps_the_blend_alpha_zero(self):
        cc, _ = compose([1, 1, [1.0, 0.9, 0.6], True, False, 1, 1])
        self.assertEqual(cc[3][3], 0)

    def test_warm_illuminant_with_white_balance_on_raises_the_blend_alpha(self):
        cc, _ = compose([1, 1, [1.0, 0.9, 0.6], True, True, 1, 1])
        self.assertGreater(cc[3][3], 0)

    def test_neutral_illuminant_is_the_identity_image(self):
        cc, _ = compose([1, 1, [1, 1, 1], True, True, 0, 1])
        self.assertEqual(cc[3][3], 0, "a neutral illuminant blended the image")
        self.assertEqual(cc[4][3], 1)
        patch = [0.8, 0.2, 0.1]
        for got, want in zip(cc_contract_pixel(patch, cc), patch):
            self.assertAlmostEqual(got, want, places=9)


class TestPerceptionSmallBound(unittest.TestCase):
    """The composed grade never leaves the small bound around the anchor.

    The default tone strength 0.25 folds the tone kernel into a bounded
    deviation from the vanilla anchor.  Over a luminance sweep the grade must
    stay inside contrast +0.00..+0.08, offset -0.02..0.00, brightness +/-0.03
    and a desaturation alpha 0..0.10.  The sweep also proves the composition
    calls the anchor clamp: bypassing FUNC(perceptionBaseGrade) returns the raw
    tone triple, whose contrast reaches 1.6 at the sweep ends.
    """

    LUM_SWEEP = [1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, 1000, 1e4, 1e5]
    ANCHOR = [1, 1, 0]

    def _compose_at(self, lum, desat_alpha=0.0):
        return compose(
            [
                lum,
                1,
                [1, 1, 1],
                True,
                False,
                0.25,
                1,
                0.9,
                0,
                0,
                self.ANCHOR,
                desat_alpha,
            ]
        )[0]

    def test_composed_grade_stays_within_the_small_bound_over_the_sweep(self):
        b0, c0, o0 = self.ANCHOR
        for lum in self.LUM_SWEEP:
            cc = self._compose_at(lum)
            self.assertGreaterEqual(
                cc[0], b0 - 0.03, f"brightness below bound at {lum}"
            )
            self.assertLessEqual(cc[0], b0 + 0.03, f"brightness above bound at {lum}")
            self.assertGreaterEqual(cc[1], c0, f"contrast below the anchor at {lum}")
            self.assertLessEqual(cc[1], c0 + 0.08, f"contrast above bound at {lum}")
            self.assertGreaterEqual(cc[2], o0 - 0.02, f"offset below bound at {lum}")
            self.assertLessEqual(cc[2], o0, f"offset above the anchor at {lum}")
            self.assertGreaterEqual(cc[4][3], 0.90, f"alpha below bound at {lum}")
            self.assertLessEqual(cc[4][3], 1, f"alpha above bound at {lum}")

    def test_composed_alpha_clamps_to_the_upper_bound(self):
        for lum in self.LUM_SWEEP:
            alpha = self._compose_at(lum, desat_alpha=0.5)[4][3]
            self.assertGreaterEqual(alpha, 0.90)
            self.assertLessEqual(alpha, 1)

    def test_kernel_grade_stays_within_the_small_bound_over_the_sweep(self):
        for lum in self.LUM_SWEEP:
            tone = run_sqf(TONE_KERNEL, [lum, 100, 0.25, 1])
            b, c, o, _a = run_sqf(BASE_ANCHOR_KERNEL, [tone, self.ANCHOR, 0.25, 0])
            self.assertGreaterEqual(b, 0.97)
            self.assertLessEqual(b, 1.03)
            self.assertGreaterEqual(c, 1.0)
            self.assertLessEqual(c, 1.08)
            self.assertGreaterEqual(o, -0.02)
            self.assertLessEqual(o, 0.0)


class TestPerceptionDebugHooks(unittest.TestCase):
    """Each vision hook is read, and none is registered as a CBA setting."""

    HOOKS = [
        "visionForce",
        "visionForceLux",
        "visionForceMesopic",
        "visionForceIlluminant",
        "visionForceBase",
    ]

    def test_each_hook_is_read(self):
        code = _code(DRIVER)
        for hook in self.HOOKS:
            self.assertIn(hook, code, f"debug hook {hook} is not read")

    def test_hooks_are_not_cba_settings(self):
        declared = VISION_SETTINGS.read_text(encoding="utf-8")
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


class TestPerceptionWiring(unittest.TestCase):
    """The slice-1 functions are prepped, started, registered and grouped."""

    def test_every_perception_function_is_prepped(self):
        text = VISION_PREP.read_text(encoding="utf-8")
        for name in PERCEPTION_FUNCTIONS:
            self.assertIn(f"PREPS(perception,{name});", text, f"{name} is not prepped")

    def test_init_starts_the_one_second_pfh(self):
        text = INIT.read_text(encoding="utf-8")
        self.assertIn(
            "[FUNC(applyBaseGrade), 1.0] call CBA_fnc_addPerFrameHandler",
            text,
            "the 1.0 s base-grade PFH is missing",
        )

    def test_vision_mode_event_applies_the_grade(self):
        text = VISION_POSTINIT.read_text(encoding="utf-8")
        self.assertIn("FUNC(applyBaseGrade)", text)

    def test_settings_are_registered(self):
        optics = VISION_SETTINGS.read_text(encoding="utf-8")
        for name in (
            "visionModelEnabled",
            "visionToneEnabled",
            "visionToneStrength",
            "visionContrastScale",
            "visionWhiteBalance",
        ):
            self.assertIn(name, optics, f"setting {name} is not registered")
        self.assertIn('"AEE Vision","Vision"', optics)

    def test_stringtable_keys_exist(self):
        strings = VISION_STRINGS.read_text(encoding="utf-8")
        for name in (
            "visionModelEnabled",
            "visionToneEnabled",
            "visionToneStrength",
            "visionContrastScale",
            "visionWhiteBalance",
        ):
            self.assertIn(f"STR_AEE_Vision_{name}_Name", strings)
            self.assertIn(f"STR_AEE_Vision_{name}_Description", strings)

    def test_taxonomy_group_exists(self):
        sys.path.insert(0, str(ROOT))
        from tools.validation import gen_config_docs as gen

        names = {
            setting.name
            for setting in gen.collect_settings()
            if setting.category == "AEE Vision" and setting.subcategory == "Vision"
        }
        self.assertEqual(
            names,
            {
                "aee_vision_visionModelEnabled",
                "aee_vision_visionToneEnabled",
                "aee_vision_visionToneStrength",
                "aee_vision_visionContrastScale",
                "aee_vision_visionWhiteBalance",
            },
        )


class TestPerceptionCost(unittest.TestCase):
    """The perception path adds at most one engine read per tick, no effect.

    The model runs in the existing 1.0 s client PFH.  It makes one ambient
    engine read for the white balance and does no engine filtering.  It must
    not add a second read or create a post-process effect.
    """

    def test_one_engine_read_per_tick(self):
        code = _code(DRIVER)
        self.assertEqual(
            code.count("getLightingAt"),
            1,
            "the driver adds more than one engine read per tick",
        )

    def test_no_post_process_effect_is_created(self):
        self.assertNotIn(
            "ppEffectCreate",
            _code(DRIVER),
            "the driver creates a post-process effect outside the registry",
        )


class TestPerceptionNoTintAtDefaults(unittest.TestCase):
    """At the plan defaults the colour stage is the identity.

    With mesopic desaturation 0 and Purkinje strength 0 the mesopic kernel
    returns [1, 1, 1, 0] for every mesopic fraction, and with white balance
    off the blend stays [0, 0, 0, 0].  This is the headline: no green cast.
    """

    # The composition arguments at the registered defaults:
    # [adaptedLux, mesopicW, illuminant, toneEnabled, whiteBalance, strength,
    #  contrastScale, adaptDegree, desatMax, purkinje, anchor, desatAlpha].
    DEFAULTS = [1, 1, [1, 1, 1], True, False, 0.25, 1, 0.9, 0, 0, [1, 1, 0], 0]

    def _compose_at(self, mesopic_w):
        args = list(self.DEFAULTS)
        args[1] = mesopic_w
        return compose(args)[0]

    def test_colorize_is_the_identity_at_the_defaults(self):
        for mesopic_w in (0, 0.25, 0.5, 0.75, 1):
            cc = self._compose_at(mesopic_w)
            self.assertEqual(cc[4], [1, 1, 1, 1], f"tint at mesopic {mesopic_w}")
            self.assertEqual(cc[3], [0, 0, 0, 0], f"blend at mesopic {mesopic_w}")

    def test_mesopic_kernel_is_the_identity_for_every_fraction(self):
        for mesopic_w in (0, 0.25, 0.5, 0.75, 1):
            self.assertEqual(run_sqf(MESOPIC_KERNEL, [mesopic_w, 0, 0]), [1, 1, 1, 0])

    def test_zero_desaturation_stays_neutral_at_the_old_purkinje_default(self):
        # The old Purkinje default is 0.5.  Zero desaturation must dominate:
        # the composition gates the colour on the mesopic alpha, so a
        # zero-alpha grade keeps the neutral colorize even at a full Purkinje
        # strength.  Removing that guard (the pre-change composition) tints
        # the RGB toward [0.75, 1, 1] and fails here.
        args = list(self.DEFAULTS)
        args[1] = 0  # scotopic, so the mesopic path runs
        args[9] = 0.5  # the old default Purkinje strength
        cc = compose(args)[0]
        self.assertEqual(
            cc[4],
            [1, 1, 1, 1],
            "a full Purkinje strength tinted a zero-desaturation grade",
        )

    def test_no_Green_cast_at_the_defaults(self):
        # The capital G keeps this test selectable by `-k Green`.
        for mesopic_w in (0, 0.25, 0.5, 0.75, 1):
            r, g, b, alpha = self._compose_at(mesopic_w)[4]
            self.assertAlmostEqual(g, r, places=9, msg="a green cast at defaults")
            self.assertAlmostEqual(b, r, places=9, msg="a blue cast at defaults")
            self.assertEqual(alpha, 1, "the default path desaturates")


class TestPerceptionDriverFallbacks(unittest.TestCase):
    """The driver's absent-setting fallbacks are the plan defaults.

    CBA registers the setting names in a later commit; a tick before that, or
    a missionNamespace that is not yet set, makes getVariable return the
    fallback.  The fallback must equal the registered default, or the old
    green-cast value returns for a tick.  Defaults: tone 0.25, mesopic
    desaturation 0, Purkinje 0.
    """

    FALLBACKS = {
        "visionToneStrength": "0.25",
        "visionMesopicDesaturation": "0",
        "visionPurkinjeStrength": "0",
    }

    def test_absent_setting_fallbacks_are_the_plan_defaults(self):
        code = _code(DRIVER)
        for name, literal in self.FALLBACKS.items():
            pattern = (
                r"getVariable\s*\[\s*QGVAR\("
                + re.escape(name)
                + r"\)\s*,\s*"
                + re.escape(literal)
                + r"\s*\]"
            )
            self.assertRegex(
                code,
                pattern,
                f"the absent-setting fallback for {name} is not {literal}",
            )


if __name__ == "__main__":
    unittest.main()
