#!/usr/bin/env python3
"""CBA settings taxonomy contract.

The category is display metadata: CBA stores a setting by its name, so a
category move keeps every stored value and every runtime behaviour.  This
suite locks the taxonomy so it cannot drift again.

Run: python3 -m unittest tools.tests.test_settings_taxonomy -v
"""

from __future__ import annotations

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


EXPECTED_DEBUG = {
    ("AEE Debug", "Core"): {"aee_core_diagnostic", "aee_core_logDebug"},
    ("AEE Debug", "FX"): {"aee_core_collisionDebug", "aee_fx_logDebug"},
    ("AEE Debug", "Environmental"): {"aee_environmental_logDebug"},
    ("AEE Debug", "Thermal"): {"aee_thermal_thermalDebug", "aee_thermal_logDebug"},
    ("AEE Debug", "Physiology"): {"aee_physiology_logDebug"},
    ("AEE Debug", "Ballistics"): {"aee_ballistics_logDebug"},
    ("AEE Debug", "Armour"): {"aee_armour_penetrationDebug", "aee_armour_logDebug"},
    ("AEE Debug", "Optics"): {"aee_optics_logDebug"},
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
}


class TestDebugTaxonomy(unittest.TestCase):
    """AEE Debug holds exactly the 23 diagnostic switches, by component."""

    def test_debug_groups_are_exact(self):
        groups = taxonomy_groups({"AEE Debug"})
        self.assertEqual(groups, EXPECTED_DEBUG)

    def test_no_unknown_setting_uses_a_taxonomy_category(self):
        known = {name for names in EXPECTED_DEBUG.values() for name in names}
        for setting in gen.collect_settings():
            if setting.category == "AEE Debug":
                self.assertIn(setting.name, known)


if __name__ == "__main__":
    unittest.main()
