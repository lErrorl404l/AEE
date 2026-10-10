#!/usr/bin/env python3
"""The AEE dynamic variation selector display (aee_symbology).

Parses config_variation_ui.hpp and pins the fixed controls.  The option rows
are NOT in the .hpp: they are built at run time from fnc_variationOptions, so a
new option value appears with no UI change.  The runtime control count is the
fixed controls plus one label per option plus one button per value.

Run: python3 -m unittest tools.tests.test_variation_ui -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

SYMBOLOGY = REPO / "addons" / "symbology"
SYM = SYMBOLOGY / "functions" / "symbology"
UI_HPP = (SYMBOLOGY / "config_variation_ui.hpp").read_text(encoding="utf-8")
CONFIG_SRC = (SYMBOLOGY / "config.cpp").read_text(encoding="utf-8")
REFRESH_SRC = (SYM / "fnc_variationDialogRefresh.sqf").read_text(encoding="utf-8")
SELECT_SRC = (SYM / "fnc_variationDialogSelect.sqf").read_text(encoding="utf-8")
OPEN_SRC = (SYM / "fnc_variationDialogOpen.sqf").read_text(encoding="utf-8")

# The fixed controls: the background, the title, the options group and the
# close button.  The option rows are built at run time, not declared here.
FIXED_CONTROLS = (
    "AEEVariationBackground",
    "AEEVariationTitle",
    "AEEVariationOptions",
    "AEEVariationClose",
)
# The option ids that must NOT appear in the .hpp, so the list is not hard-coded.
OPTION_IDS = ("affiliation", "dimension", "function", "echelon", "palette")


class TestVariationDialog(unittest.TestCase):
    def test_the_display_is_a_real_engine_dialog(self):
        self.assertIn("class RscDisplayAEEVariation {", UI_HPP)
        self.assertIn("idd = 10790;", UI_HPP)
        self.assertIn("onLoad =", UI_HPP)
        self.assertIn("onUnload =", UI_HPP)

    def test_the_display_is_included_from_the_config(self):
        self.assertIn('#include "config_variation_ui.hpp"', CONFIG_SRC)

    def test_the_dialog_declares_exactly_the_fixed_controls(self):
        controls = re.findall(
            r"class (\w+): (?:RscText|RscButton|RscControlsGroup) \{", UI_HPP
        )
        self.assertEqual(len(controls), len(FIXED_CONTROLS))
        self.assertEqual(set(controls), set(FIXED_CONTROLS))

    def test_every_fixed_control_uses_a_real_engine_control_type(self):
        for control in FIXED_CONTROLS:
            with self.subTest(control=control):
                self.assertIn(f"class {control}:", UI_HPP)
        parents = re.findall(r"class \w+: (\w+) \{", UI_HPP)
        for parent in parents:
            self.assertIn(parent, ("RscText", "RscButton", "RscControlsGroup"))

    def test_the_option_list_is_not_hard_coded(self):
        for option_id in OPTION_IDS:
            with self.subTest(option=option_id):
                self.assertNotIn(f'"{option_id}"', UI_HPP)

    def test_the_rows_are_built_from_the_model(self):
        self.assertIn("FUNC(variationOptions)", REFRESH_SRC)
        self.assertIn("ctrlCreate", REFRESH_SRC)
        self.assertIn("ctrlDelete", REFRESH_SRC)

    def test_the_button_handler_defers_the_refresh(self):
        # The button handler calls variationDialogSelect; select defers the
        # refresh (which ctrlDeletes) through CBA_fnc_waitAndExecute, so
        # ctrlDelete never runs inside the control's own event handler.
        self.assertIn("aee_symbology_fnc_variationDialogSelect", REFRESH_SRC)
        self.assertIn("CBA_fnc_waitAndExecute", SELECT_SRC)
        self.assertIn("FUNC(variationDialogRefresh)", SELECT_SRC)

    def test_the_open_no_ops_without_the_map(self):
        self.assertIn("findDisplay 12", OPEN_SRC)
        self.assertIn("createDialog", OPEN_SRC)


if __name__ == "__main__":
    unittest.main()
