#!/usr/bin/env python3
"""CBA settings taxonomy contract.

The category is display metadata: CBA stores a setting by its name, so a
category move keeps every stored value and every runtime behaviour.  This
suite locks the taxonomy so it cannot drift again.

Run: python3 -m unittest tools.tests.test_settings_taxonomy -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_config_docs as gen  # noqa: E402


def taxonomy_groups(prefixes):
    """Group settings under the given category prefixes.

    Returns {(category, subcategory): {setting names}}.
    """
    groups = {}
    for setting in gen.collect_settings():
        if any(setting.category.startswith(prefix) for prefix in prefixes):
            key = (setting.category, setting.subcategory)
            groups.setdefault(key, set()).add(setting.name)
    return groups


EXPECTED_HUD = {
    "aee_thermal_fusionHud",
    "aee_optics_hudEnabled",
    "aee_physiology_HUDWarningThreshold",
    "aee_nightvision_ltmEnabled",
    "aee_nightvision_ltmDaylightFade",
}


class TestSettingsTaxonomy(unittest.TestCase):
    """AEE HUD holds exactly the four on-screen displays."""

    def test_hud_group_is_exact(self):
        groups = taxonomy_groups({"AEE HUD"})
        self.assertEqual(groups.get(("AEE HUD", "Displays")), EXPECTED_HUD)

    def test_no_unknown_setting_uses_a_taxonomy_category(self):
        for setting in gen.collect_settings():
            if setting.category == "AEE HUD":
                self.assertIn(setting.name, EXPECTED_HUD)


EXPECTED_EXPERIMENTAL_FUSION = {
    "aee_thermal_fusionAlwaysOn",
    "aee_thermal_fusionFovFrame",
    "aee_thermal_fusionOutline",
    "aee_thermal_fusionSolidFill",
}

EXPECTED_EXPERIMENTAL_VISION = {
    "aee_optics_visionAdaptationDegree",
    "aee_optics_visionMesopicDesaturation",
    "aee_optics_visionPurkinjeStrength",
}

# Every AEE Experimental name, across all subcategories.  The unknown-setting
# guard reads this union; the per-group exact tests read the two sets above, so
# the Fusion exact group stays unchanged.
EXPECTED_EXPERIMENTAL = EXPECTED_EXPERIMENTAL_FUSION | EXPECTED_EXPERIMENTAL_VISION


class TestExperimentalTaxonomy(unittest.TestCase):
    """AEE Experimental holds the fusion and the vision-calibration knobs."""

    def test_experimental_group_is_exact(self):
        groups = taxonomy_groups({"AEE Experimental"})
        self.assertEqual(
            groups.get(("AEE Experimental", "Fusion")), EXPECTED_EXPERIMENTAL_FUSION
        )
        self.assertEqual(
            groups.get(("AEE Experimental", "Vision")), EXPECTED_EXPERIMENTAL_VISION
        )

    def test_no_unknown_setting_uses_a_taxonomy_category(self):
        for setting in gen.collect_settings():
            if setting.category == "AEE Experimental":
                self.assertIn(setting.name, EXPECTED_EXPERIMENTAL)


EXPECTED_OPTICS_VISION = {
    "aee_optics_visionContrastScale",
    "aee_optics_visionModelEnabled",
    "aee_optics_visionToneEnabled",
    "aee_optics_visionToneStrength",
    "aee_optics_visionWhiteBalance",
}


class TestOpticsVisionTaxonomy(unittest.TestCase):
    """AEE Optics > Vision holds exactly the five human-vision settings."""

    def test_optics_vision_group_is_exact(self):
        groups = taxonomy_groups({"AEE Optics"})
        self.assertEqual(groups.get(("AEE Optics", "Vision")), EXPECTED_OPTICS_VISION)


EXPECTED_WILDLIFE_GENERAL = {
    "aee_wildlife_enabled",
    "aee_wildlife_tickInterval",
}

EXPECTED_WILDLIFE_FAUNA = {
    "aee_wildlife_animalsEnabled",
    "aee_wildlife_density",
    "aee_wildlife_maxAnimals",
    "aee_wildlife_spawnRadius",
    "aee_wildlife_despawnRadius",
}

EXPECTED_WILDLIFE = {
    ("AEE Wildlife", "General"): EXPECTED_WILDLIFE_GENERAL,
    ("AEE Wildlife", "Ambient Sound"): {"aee_wildlife_ambientEnabled"},
    ("AEE Wildlife", "Fauna"): EXPECTED_WILDLIFE_FAUNA,
    ("AEE Wildlife", "Behaviour"): {
        "aee_wildlife_spookSensitivity",
        "aee_wildlife_silenceDecay",
        "aee_wildlife_hungerRate",
        "aee_wildlife_thirstRate",
        "aee_wildlife_herdSize",
    },
}


class TestWildlifeTaxonomy(unittest.TestCase):
    """AEE Wildlife holds exactly the slice-one ecology settings."""

    def test_wildlife_groups_are_exact(self):
        groups = taxonomy_groups({"AEE Wildlife"})
        self.assertEqual(groups, EXPECTED_WILDLIFE)

    def test_fauna_group_is_exact(self):
        groups = taxonomy_groups({"AEE Wildlife"})
        self.assertEqual(groups.get(("AEE Wildlife", "Fauna")), EXPECTED_WILDLIFE_FAUNA)

    def test_no_unknown_setting_uses_the_wildlife_category(self):
        known = {name for names in EXPECTED_WILDLIFE.values() for name in names}
        for setting in gen.collect_settings():
            if setting.category == "AEE Wildlife":
                self.assertIn(setting.name, known)


EXPECTED_DEBUG = {
    ("AEE Debug", "AI"): {"aee_ai_logDebug"},
    ("AEE Debug", "Wildlife"): {"aee_wildlife_logDebug"},
    ("AEE Debug", "Core"): {"aee_core_diagnostic", "aee_core_logDebug"},
    ("AEE Debug", "FX"): {"aee_core_collisionDebug", "aee_fx_logDebug"},
    ("AEE Debug", "Environmental"): {"aee_environmental_logDebug"},
    ("AEE Debug", "Thermal"): {"aee_thermal_thermalDebug", "aee_thermal_logDebug"},
    ("AEE Debug", "Physiology"): {"aee_physiology_logDebug"},
    ("AEE Debug", "Ballistics"): {"aee_ballistics_logDebug"},
    ("AEE Debug", "Armour"): {"aee_armour_penetrationDebug", "aee_armour_logDebug"},
    ("AEE Debug", "Optics"): {"aee_optics_logDebug"},
    ("AEE Debug", "Perception"): {
        "aee_optics_perceptionHud",
        "aee_optics_perceptionInterval",
        "aee_optics_perceptionMonitor",
    },
    ("AEE Debug", "Night Vision"): {"aee_nightvision_logDebug"},
    ("AEE Debug", "Mobility"): {"aee_mobility_logDebug"},
    ("AEE Debug", "Maritime"): {"aee_maritime_logDebug"},
    ("AEE Debug", "Radio"): {"aee_radio_logDebug"},
    ("AEE Debug", "Atmos"): {"aee_atmos_logDebug"},
    ("AEE Debug", "Compat - ACE3"): {"aee_compat_ace3_logDebug"},
    ("AEE Debug", "Compat - ACM"): {"aee_compat_acm_logDebug"},
    ("AEE Debug", "Compat - ACRE2"): {"aee_compat_acre2_logDebug"},
    ("AEE Debug", "Compat - KAT"): {"aee_compat_kat_logDebug"},
    ("AEE Debug", "Compat - Real Weather"): {"aee_compat_realweather_logDebug"},
    ("AEE Debug", "Compat - TFAR"): {"aee_compat_tfar_logDebug"},
    ("AEE Debug", "Actions"): {"aee_actions_logDebug"},
    ("AEE Debug", "Material"): {"aee_material_logDebug"},
}


class TestDebugTaxonomy(unittest.TestCase):
    """AEE Debug holds exactly the diagnostic switches, by component."""

    def test_debug_groups_are_exact(self):
        groups = taxonomy_groups({"AEE Debug"})
        self.assertEqual(groups, EXPECTED_DEBUG)

    def test_no_unknown_setting_uses_a_taxonomy_category(self):
        known = {name for names in EXPECTED_DEBUG.values() for name in names}
        for setting in gen.collect_settings():
            if setting.category == "AEE Debug":
                self.assertIn(setting.name, known)


# The 7th SLIDER argument is CBA's _trailingDecimals, not a step.  A fractional
# value is floored by toFixed, CBA_fnc_formatNumber's "." search then fails, and
# the leading-zero padding loop prints the literal string "000" or "001" on the
# slider.  These two maps lock the corrected values so the defect cannot return.
EXPECTED_SLIDER_DECIMALS = {
    "aee_ballistics_ammoHeatPerShotJ": 4,  # was 6
    "aee_fx_exhaustShimmerAlpha": 2,  # was 0
    "aee_mobility_bedSlope": 4,  # was 5
    "aee_nightvision_fogGrainMax": 2,  # was 0
    "aee_nightvision_nightGrainMax": 1,  # was 0
    "aee_nightvision_nvgAgcBreathing": 2,  # was 0.05
    "aee_nightvision_nvgBlemishStrength": 2,  # was 0.05
    "aee_nightvision_nvgBlindingStrength": 2,  # was 0.05
    "aee_nightvision_nvgEdgeDistortion": 2,  # was 0.05
    "aee_nightvision_nvgImperfectionStrength": 2,  # was 0.05
    "aee_nightvision_nvgReticulationStrength": 2,  # was 0.05
    "aee_nightvision_nvgScintillationStrength": 2,  # was 0.05
    "aee_nightvision_nvgVeilingGlare": 4,  # was 0.001
    "aee_nightvision_rainGrainMax": 1,  # was 0
    "aee_optics_baseGradeBlackPoint": 3,  # was 0.005
    "aee_optics_baseGradeBrightness": 2,  # was 0.05
    "aee_optics_baseGradeContrast": 2,  # was 0.05
    "aee_optics_baseGradeGrain": 3,  # was 0.001
    "aee_optics_baseGradeSaturation": 2,  # was 0.05
    "aee_optics_chromaCap": 2,  # was 0
    "aee_optics_dewAccumRate": 2,  # was 0
    "aee_optics_dewBlurMax": 1,  # was 0
    "aee_optics_dewDecayRate": 2,  # was 0
    "aee_optics_eyeAmbientLuxScale": 3,  # was 0
    "aee_optics_eyeFastBlend": 2,  # was 0
    "aee_optics_eyeLocalLuxScale": 3,  # was 0
    "aee_optics_eyeMesopicHigh": 1,  # was 0
    "aee_optics_eyeMesopicLow": 3,  # was 0
    "aee_optics_eyePupilTauConstrict": 2,  # was 0
    "aee_optics_eyePupilTauDilate": 3,  # was 0
    "aee_optics_eyeReflectance": 2,  # was 0
    "aee_optics_eyeTauLight": 1,  # was 0
    "aee_optics_glareBlurMax": 1,  # was 0
    "aee_optics_heatShimmerIntensity": 2,  # was 0
    "aee_optics_mirageDensity": 2,  # was 0
    "aee_optics_rainAccumRate": 2,  # was 0
    "aee_optics_rainBlurScale": 1,  # was 0
    "aee_optics_rainDecayRate": 2,  # was 0
    "aee_optics_seeingFXIntensity": 2,  # was 0
    "aee_optics_smokePersistenceScale": 1,  # was 0
    "aee_optics_snowBlindnessBase": 1,  # was 0
    "aee_optics_snowVisibilityPenalty": 1,  # was 0
    "aee_optics_vehicleShimmerBase": 1,  # was 0
    "aee_optics_visionAdaptationDegree": 2,  # was 0.05
    "aee_optics_visionContrastScale": 2,  # was 0.05
    "aee_optics_visionMesopicDesaturation": 2,  # was 0.05
    "aee_optics_visionPurkinjeStrength": 2,  # was 0.05
    "aee_optics_visionToneStrength": 2,  # was 0.05
    "aee_thermal_thermalAgcHunt": 3,  # was 0.005
    "aee_thermal_thermalHotBloom": 2,  # was 0.01
    "aee_thermal_thermalManualMaxC": 0,  # was 5
    "aee_thermal_thermalNucDrift": 2,  # was 0.05
    "aee_thermal_thermalTemporalNoise": 1,  # was 0.1
    "aee_wildlife_density": 2,  # was 0.05
    "aee_wildlife_despawnRadius": 0,  # was 10
    "aee_wildlife_hungerRate": 3,  # was 0.001
    "aee_wildlife_silenceDecay": 3,  # was 0.005
    "aee_wildlife_spawnRadius": 0,  # was 10
    "aee_wildlife_spookSensitivity": 2,  # was 0.05
    "aee_wildlife_thirstRate": 3,  # was 0.001
    "aee_wildlife_tickInterval": 1,  # was 0.1
}

_SLIDER_MACRO = re.compile(r"AEE_SETTING_SLIDER\s*\((?P<args>[^)]*)\)")
_ADD_SETTING = re.compile(r"call CBA_fnc_addSetting")
_QGVAR = re.compile(r"QGVAR\((\w+)\)")


def _iter_sliders():
    """(name, default, trailing_decimals_text) for every SLIDER, both forms.

    The macro valueInfo is [min, max, default, trailingDecimals]; the explicit
    block keeps the same order.  Names are aee_<addon>_<key>.
    """
    for init_path in sorted(gen.ADDONS.rglob("initSettings.inc.sqf")):
        addon = init_path.parent.name
        text = gen.strip_comments(init_path.read_text(encoding="utf-8"))
        for match in _SLIDER_MACRO.finditer(text):
            args = gen.split_top_level(match.group("args"))
            if len(args) != 7:
                continue
            yield f"aee_{addon}_{args[0]}", float(args[5]), args[6]
        for match in _ADD_SETTING.finditer(text):
            body = gen.bracket_before(text, match.start())
            if body is None:
                continue
            parts = gen.split_top_level(body)
            if len(parts) < 6 or gen.unquote(parts[1]) != "SLIDER":
                continue
            name_match = _QGVAR.search(parts[0])
            if name_match is None:
                continue
            info = gen.split_top_level(parts[4].strip().strip("[]"))
            if len(info) < 3:
                continue
            decimals = info[3].strip() if len(info) >= 4 else "2"
            yield f"aee_{addon}_{name_match.group(1)}", float(info[2]), decimals


class TestSliderTrailingDecimals(unittest.TestCase):
    """Every slider passes an integer trailingDecimals CBA can render."""

    def test_trailing_decimals_is_a_non_negative_integer(self):
        bad = {
            name: dec
            for name, _default, dec in _iter_sliders()
            if re.fullmatch(r"\d+", dec) is None
        }
        self.assertEqual(bad, {}, f"fractional trailingDecimals: {bad}")

    def test_default_is_representable_in_its_decimals(self):
        # The rendered default must equal the default exactly; a default that
        # needs more places than it declares prints a rounded or padded number.
        unrepresentable = {
            name: (default, dec)
            for name, default, dec in _iter_sliders()
            if abs(round(default, int(dec)) - default) > 1e-9
        }
        self.assertEqual(
            unrepresentable, {}, f"default needs more decimals: {unrepresentable}"
        )

    def test_corrected_values_are_pinned(self):
        actual = {name: dec for name, _default, dec in _iter_sliders()}
        for name, expected in EXPECTED_SLIDER_DECIMALS.items():
            self.assertIn(name, actual, f"{name} disappeared")
            self.assertEqual(
                int(actual[name]), expected, f"{name} regressed to {actual[name]}"
            )


if __name__ == "__main__":
    unittest.main()
