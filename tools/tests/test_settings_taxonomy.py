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


if __name__ == "__main__":
    unittest.main()
