#!/usr/bin/env python3
"""NVG tube imperfections (issue #215).

The six pure kernels run from their real SQF through tools/tests/sqf_lite.py.
The parent wiring is locked by source contract because it needs the engine,
missionNamespace and CBA globals that sqf_lite does not provide.

The per-constant source register is in .omo/plans/aee-nvg-imperfections.md
and docs/wiki/research/nvg-imperfections-dossier.md.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NVG = ROOT / "addons" / "nightvision"
FUNCS = NVG / "functions"

TIER_INDEX = FUNCS / "fnc_nvgTierIndex.sqf"
BLEMISH = FUNCS / "fnc_nvgBlemishField.sqf"
BREATHING = FUNCS / "fnc_nvgAgcBreathing.sqf"
BLINDING = FUNCS / "fnc_nvgBlindingEnvelope.sqf"
SCINT = FUNCS / "fnc_nvgScintillation.sqf"
PINCUSHION = FUNCS / "fnc_nvgPincushion.sqf"
PARENT = FUNCS / "fnc_applyNVGTubeModel.sqf"
RSC = NVG / "RscTitles.hpp"
SETTINGS = NVG / "initSettings.inc.sqf"
STRINGS = NVG / "stringtable.xml"
PREP = NVG / "XEH_PREP.hpp"
ALLOWLIST = ROOT / "tools" / "validation" / "cba_settings_allowlist.txt"
ANNEX_C = ROOT / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"

KERNELS = {
    "nvgTierIndex": TIER_INDEX,
    "nvgBlemishField": BLEMISH,
    "nvgAgcBreathing": BREATHING,
    "nvgBlindingEnvelope": BLINDING,
    "nvgScintillation": SCINT,
    "nvgPincushion": PINCUSHION,
}

SETTING_NAMES = [
    "nvgImperfectionsEnabled",
    "nvgImperfectionStrength",
    "nvgBlemishStrength",
    "nvgReticulationStrength",
    "nvgAgcBreathing",
    "nvgBlindingStrength",
    "nvgScintillationStrength",
    "nvgEdgeDistortion",
    "nvgVeilingGlare",
]

FORCE_HOOKS = [
    "nvgForceImperfections",
    "nvgForceBlemishes",
    "nvgForceBreathing",
    "nvgForceBlowout",
    "nvgImperfectionDebug",
]


class TestTierIndex(unittest.TestCase):
    """fnc_nvgTierIndex runs from the real SQF."""

    def test_each_tier_maps_to_its_index(self):
        self.assertEqual(run_sqf(TIER_INDEX, ["GEN1"]), 0)
        self.assertEqual(run_sqf(TIER_INDEX, ["GEN2"]), 1)
        self.assertEqual(run_sqf(TIER_INDEX, ["GEN3"]), 2)
        self.assertEqual(run_sqf(TIER_INDEX, ["PVS31"]), 3)

    def test_unknown_tier_falls_back_to_gen1(self):
        self.assertEqual(run_sqf(TIER_INDEX, ["AUTO"]), 0)
        self.assertEqual(run_sqf(TIER_INDEX, [""]), 0)


class TestBlemishField(unittest.TestCase):
    """fnc_nvgBlemishField runs from the real SQF."""

    def test_zero_strength_is_transparent(self):
        for tier in range(4):
            self.assertEqual(run_sqf(BLEMISH, [tier, 0.5, 0]), 0)

    def test_monotone_decreasing_over_tier_at_full_strength(self):
        vals = [run_sqf(BLEMISH, [t, 1, 1]) for t in range(4)]
        for older, newer in zip(vals, vals[1:]):
            self.assertGreater(older, newer)

    def test_increases_with_strength(self):
        vals = [run_sqf(BLEMISH, [0, 0.5, s]) for s in (0, 0.25, 0.5, 0.75, 1)]
        for lo, hi in zip(vals, vals[1:]):
            self.assertGreater(hi, lo)

    def test_stays_in_bounds(self):
        for tier in range(4):
            for strength in (0, 0.5, 1, 2):
                v = run_sqf(BLEMISH, [tier, 0.7, strength])
                self.assertGreaterEqual(v, 0)
                self.assertLessEqual(v, 1)


class TestAgcBreathing(unittest.TestCase):
    """fnc_nvgAgcBreathing runs from the real SQF."""

    def test_zero_strength_is_zero(self):
        self.assertEqual(run_sqf(BREATHING, [0.5, 1, 3.0, 0]), 0)

    def test_no_gain_error_is_zero(self):
        self.assertEqual(run_sqf(BREATHING, [1.0, 1.0, 3.0, 1.0]), 0)

    def test_non_zero_and_bounded(self):
        self.assertNotEqual(run_sqf(BREATHING, [0.5, 1, 1.0, 1.0]), 0)
        for t in (i * 0.1 for i in range(200)):
            got = run_sqf(BREATHING, [0.5, 1, t, 1.0])
            self.assertLessEqual(abs(got), 0.15)


class TestBlindingEnvelope(unittest.TestCase):
    """fnc_nvgBlindingEnvelope runs from the real SQF."""

    def test_no_blowout_is_neutral(self):
        for tier in range(4):
            self.assertEqual(run_sqf(BLINDING, [0, tier, 1]), [1, 1])

    def test_ungated_whites_out(self):
        brightness, contrast = run_sqf(BLINDING, [1, 0, 1])
        self.assertGreater(brightness, 1)
        self.assertLess(contrast, 1)

    def test_gated_blacks_out(self):
        brightness, contrast = run_sqf(BLINDING, [1, 3, 1])
        self.assertLess(brightness, 1)
        self.assertLess(contrast, 1)

    def test_brightness_monotone_in_blowout(self):
        vals = [run_sqf(BLINDING, [x, 0, 1])[0] for x in (0, 0.25, 0.5, 0.75, 1)]
        for lo, hi in zip(vals, vals[1:]):
            self.assertGreater(hi, lo)

    def test_both_scales_bounded(self):
        for tier in range(4):
            brightness, contrast = run_sqf(BLINDING, [1, tier, 2])
            self.assertGreaterEqual(brightness, 0)
            self.assertLessEqual(brightness, 2)
            self.assertGreaterEqual(contrast, 0)
            self.assertLessEqual(contrast, 1)


class TestScintillation(unittest.TestCase):
    """fnc_nvgScintillation runs from the real SQF."""

    def test_returns_three_elements(self):
        self.assertEqual(len(run_sqf(SCINT, [0.001, 0.1, 0, 1])), 3)

    def test_dark_is_grainier_than_moonlit(self):
        dark = run_sqf(SCINT, [0.001, 0, 0, 1])[0]
        moon = run_sqf(SCINT, [0.25, 0, 0, 1])[0]
        self.assertGreater(dark, moon)

    def test_intensity_increases_with_strength(self):
        vals = [run_sqf(SCINT, [0.001, 0, 0, s])[0] for s in (0, 0.5, 1)]
        for lo, hi in zip(vals, vals[1:]):
            self.assertGreater(hi, lo)

    def test_intensity_bounded(self):
        v = run_sqf(SCINT, [0.001, 1, 1, 2])[0]
        self.assertGreaterEqual(v, 0)
        self.assertLessEqual(v, 1)

    def test_sharpness_band(self):
        for noise in (0, 0.5, 1):
            s = run_sqf(SCINT, [0.001, noise, 0, 1])[1]
            self.assertGreaterEqual(s, 1.0)
            self.assertLessEqual(s, 1.2)

    def test_grain_size_band(self):
        for noise in (0, 0.5, 1):
            g = run_sqf(SCINT, [0.001, noise, 0, 1])[2]
            self.assertGreaterEqual(g, 2.25)
            self.assertLessEqual(g, 2.70)


class TestPincushion(unittest.TestCase):
    """fnc_nvgPincushion runs from the real SQF."""

    def test_zero_strength_is_unity(self):
        self.assertEqual(run_sqf(PINCUSHION, [0, 0.004, 0]), 1.0)

    def test_power_stays_within_the_parent_guard(self):
        scale = run_sqf(PINCUSHION, [0, 0.004, 1])
        self.assertLessEqual(scale * 0.004, 0.01)

    def test_older_tier_has_the_stronger_edge(self):
        self.assertGreater(
            run_sqf(PINCUSHION, [0, 0.004, 1]),
            run_sqf(PINCUSHION, [3, 0.004, 1]),
        )

    def test_returns_a_number_not_an_array(self):
        self.assertIsInstance(run_sqf(PINCUSHION, [0, 0.004, 0.5]), float)


class TestImperfectionWiring(unittest.TestCase):
    """The kernels are registered, the parent is wired, the docs carry the state."""

    @classmethod
    def setUpClass(cls):
        cls.parent = PARENT.read_text(encoding="utf-8")
        cls.rsc = RSC.read_text(encoding="utf-8")
        cls.settings = SETTINGS.read_text(encoding="utf-8")
        cls.strings = STRINGS.read_text(encoding="utf-8")
        cls.prep = PREP.read_text(encoding="utf-8")
        cls.allow = ALLOWLIST.read_text(encoding="utf-8")
        cls.annex = ANNEX_C.read_text(encoding="utf-8")

    def test_every_kernel_is_prepped(self):
        for name in KERNELS:
            self.assertIn(f"PREP({name});", self.prep, f"{name} is not prepped")

    def test_parent_calls_every_kernel(self):
        for name in KERNELS:
            self.assertIn(f"FUNC({name})", self.parent, f"parent does not call {name}")

    def test_parent_uses_ctrlsetfade_and_the_layer(self):
        self.assertIn("ctrlSetFade", self.parent)
        self.assertIn("aee_nightvision_nvg_imperfections", self.parent)

    def test_parent_adds_no_new_pp_effect_handle(self):
        # Every ppEffect name that appears anywhere in the parent must be one
        # the tube model already owns.  A new handle adds a new name and fails.
        known_effects = {
            "RadialBlur",
            "ChromAberration",
            "WetDistortion",
            "ColorCorrections",
            "DynamicBlur",
            "FilmGrain",
            "ColorInversion",
            "SSAO",
            "Resolution",
            "DepthOfField",
        }
        present = set(re.findall(r'"(\w+)"', self.parent))
        self.assertEqual(
            present & known_effects,
            {
                "RadialBlur",
                "ChromAberration",
                "ColorCorrections",
                "DynamicBlur",
                "FilmGrain",
                "DepthOfField",
            },
        )

    def test_inline_erosion_switch_is_replaced_by_the_kernel(self):
        self.assertNotIn("private _erosionFactor = switch (_tier) do", self.parent)
        self.assertIn("call FUNC(nvgPincushion)", self.parent)

    def test_overlay_display_class_and_controls(self):
        for needle in (
            "class GVAR(nvgImperfections)",
            "idc = 1010",
            "idc = 1011",
            "nvg_blemishes.paa",
            "nvg_reticulation.paa",
            "class RscPicture",
        ):
            self.assertIn(needle, self.rsc)

    def test_settings_are_registered(self):
        for name in SETTING_NAMES:
            self.assertIn(name, self.settings, f"{name} is not registered")
        self.assertIn('"AEE Night Vision","Imperfections"', self.settings)

    def test_every_setting_has_a_name_and_a_description(self):
        for name in SETTING_NAMES:
            self.assertIn(f"STR_AEE_NightVision_{name}_Name", self.strings)
            self.assertIn(f"STR_AEE_NightVision_{name}_Description", self.strings)

    def test_force_hooks_are_read_and_allowlisted(self):
        for hook in FORCE_HOOKS:
            self.assertIn(hook, self.parent, f"hook {hook} is not read")
            self.assertIn(hook, self.allow, f"hook {hook} is not allowlisted")

    def test_entry_log_substring_present(self):
        self.assertIn("NVG imperfections:", self.parent)

    def test_new_published_state_is_in_annex_c(self):
        for state in (
            "aee_nightvision_nvgBreathing",
            "aee_nightvision_nvgImperfectionAlpha",
        ):
            self.assertIn(state, self.annex, f"{state} is not in Annex C")


if __name__ == "__main__":
    unittest.main()
