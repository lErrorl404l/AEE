#!/usr/bin/env python3
"""ECOTI environment HUD tests (port of FPANO ECOTI).

Executes the REAL pure formatters through sqf_lite:

  addons/optics/functions/hud/fnc_hudFormatHeading.sqf
  addons/optics/functions/hud/fnc_hudFormatGrid.sqf
  addons/optics/functions/hud/fnc_hudFormatRange.sqf

The engine-reading functions fnc_hudBuild, fnc_hudUpdate, fnc_hudRangefinder
and fnc_hudMarkers cannot run without an engine, so their source contract is
locked here instead: the RscTitles HUD class exists, the update function
reads the aee environment state, the setting and PREP entries and the
postInit wiring exist, no .paa or .ogg is referenced, and no editor or
radioBridge code was ported.

Run: python3 -m unittest tools.tests.test_hud -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

OPTICS = REPO / "addons" / "optics"
HUD = OPTICS / "functions" / "hud"
HEADING_KERNEL = HUD / "fnc_hudFormatHeading.sqf"
GRID_KERNEL = HUD / "fnc_hudFormatGrid.sqf"
GRID_DISPLAY_KERNEL = HUD / "fnc_formatGridDisplay.sqf"
RANGE_KERNEL = HUD / "fnc_hudFormatRange.sqf"

HUD_FILE = OPTICS / "RscTitles.hpp"
BUILD_SRC = (HUD / "fnc_hudBuild.sqf").read_text(encoding="utf-8")
UPDATE_SRC = (HUD / "fnc_hudUpdate.sqf").read_text(encoding="utf-8")
RANGE_SRC = (HUD / "fnc_hudRangefinder.sqf").read_text(encoding="utf-8")
MARKERS_SRC = (HUD / "fnc_hudMarkers.sqf").read_text(encoding="utf-8")
FORMAT_DISPLAY_SRC = (HUD / "fnc_formatGridDisplay.sqf").read_text(encoding="utf-8")
HUD_CLASS_SRC = HUD_FILE.read_text(encoding="utf-8")
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (OPTICS / "initSettings.inc.sqf").read_text(encoding="utf-8")
STRINGTABLE_SRC = (OPTICS / "stringtable.xml").read_text(encoding="utf-8")
POSTINIT_SRC = (OPTICS / "XEH_postInit.sqf").read_text(encoding="utf-8")
CONFIG_SRC = (OPTICS / "config.cpp").read_text(encoding="utf-8")
ALL_HUD_SRC = "\n".join(
    [
        HUD_CLASS_SRC,
        BUILD_SRC,
        UPDATE_SRC,
        RANGE_SRC,
        MARKERS_SRC,
        FORMAT_DISPLAY_SRC,
    ]
)

FORBIDDEN_PROVENANCE = (
    "Agent:",
    "opencode",
    "claude",
    "anthropic",
    "openai",
    "deepseek",
    "hephaestus",
)


def heading(direction):
    return run_sqf(HEADING_KERNEL, [direction], {})


def grid(raw):
    return run_sqf(GRID_KERNEL, [raw], {})


def rng(distance):
    return run_sqf(RANGE_KERNEL, [distance], {})


def grid_display(position, anchor, precision, grid_raw, enabled, mgrs):
    """Run the real selector with the real legacy formatter and a stub worldToMgrs."""
    globals_ = {
        "__EFUNC__core_worldToMgrs": lambda _p, _a, _prec: [
            mgrs,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
        ],
        "__FUNC__hudFormatGrid": lambda raw: run_sqf(GRID_KERNEL, [raw], {}),
    }
    return run_sqf(
        GRID_DISPLAY_KERNEL, [position, anchor, precision, grid_raw, enabled], globals_
    )


class TestHudHeading(unittest.TestCase):
    """fnc_hudFormatHeading, executed: bearing -> cardinal and padded degrees."""

    def test_the_cardinals_land_in_their_sectors(self):
        for direction, cardinal in (
            (0, "N"),
            (45, "NE"),
            (90, "E"),
            (135, "SE"),
            (180, "S"),
            (225, "SW"),
            (270, "W"),
            (315, "NW"),
        ):
            with self.subTest(direction=direction):
                self.assertEqual(heading(direction)[0], cardinal)

    def test_the_north_sector_wraps_past_338(self):
        self.assertEqual(heading(338)[0], "N")
        self.assertEqual(heading(337)[0], "NW")

    def test_the_ne_sector_starts_at_23(self):
        self.assertEqual(heading(22)[0], "N")
        self.assertEqual(heading(23)[0], "NE")

    def test_the_degrees_are_zero_padded_to_three(self):
        self.assertEqual(heading(0)[1], "000")
        self.assertEqual(heading(5)[1], "005")
        self.assertEqual(heading(45)[1], "045")
        self.assertEqual(heading(359)[1], "359")

    def test_a_full_turn_wraps_to_zero(self):
        self.assertEqual(heading(360), ["N", "000"])

    def test_a_negative_bearing_wraps_clockwise(self):
        self.assertEqual(heading(-90), ["W", "270"])

    def test_rounding_at_the_top_edge_wraps_to_north(self):
        self.assertEqual(heading(359.6), ["N", "000"])

    def test_rounding_below_the_edge_keeps_the_bearing(self):
        self.assertEqual(heading(359.4)[1], "359")


class TestHudGrid(unittest.TestCase):
    """fnc_hudFormatGrid, executed: grid reference -> readable pair."""

    def test_ten_figures_split_into_four_and_four(self):
        self.assertEqual(grid("12345678"), "1234 - 5678")

    def test_longer_than_eight_drops_the_tail(self):
        self.assertEqual(grid("1234567890"), "1234 - 5678")

    def test_eight_figures_split_into_four_and_four(self):
        self.assertEqual(grid("98765432"), "9876 - 5432")

    def test_six_figures_get_a_leading_zero_per_half(self):
        self.assertEqual(grid("123456"), "0123 - 0456")

    def test_seven_figures_use_the_six_figure_branch(self):
        self.assertEqual(grid("1234567"), "0123 - 0456")

    def test_five_figures_pass_through(self):
        self.assertEqual(grid("12345"), "12345")

    def test_an_empty_grid_passes_through(self):
        self.assertEqual(grid(""), "")


class TestHudRange(unittest.TestCase):
    """fnc_hudFormatRange, executed: metres below 1 km, km at and above."""

    def test_metres_below_one_kilometre(self):
        self.assertEqual(rng(500), "500m")
        self.assertEqual(rng(999), "999m")
        self.assertEqual(rng(0), "0m")

    def test_one_kilometre_switches_to_km(self):
        self.assertEqual(rng(1000), "1.0km")

    def test_kilometres_carry_one_decimal(self):
        self.assertEqual(rng(1234), "1.2km")
        self.assertEqual(rng(1500), "1.5km")
        self.assertEqual(rng(2500), "2.5km")

    def test_a_fractional_metre_rounds(self):
        self.assertEqual(rng(999.4), "999m")


class TestHudGridDisplay(unittest.TestCase):
    """fnc_formatGridDisplay, executed: MGRS when on, the legacy grid when off."""

    def test_mgrs_is_returned_when_the_setting_is_on(self):
        self.assertEqual(
            grid_display([0, 0, 0], [0] * 9, 10, "12345678", True, "35SLE5013418852"),
            "35SLE5013418852",
        )

    def test_the_legacy_grid_is_returned_when_the_setting_is_off(self):
        self.assertEqual(
            grid_display([0, 0, 0], [0] * 9, 10, "12345678", False, "35SLE5013418852"),
            "1234 - 5678",
        )

    def test_it_falls_back_to_the_legacy_grid_when_mgrs_is_empty(self):
        self.assertEqual(
            grid_display([0, 0, 0], [0] * 9, 10, "123456", True, ""),
            "0123 - 0456",
        )


class TestHudSourceContract(unittest.TestCase):
    """The engine readers carry the source's mechanisms."""

    def test_the_mgrs_control_uses_a_free_idc(self):
        self.assertIn("idc = 9015;", HUD_CLASS_SRC)

    def test_the_update_calls_the_grid_selector(self):
        self.assertIn("call FUNC(formatGridDisplay)", UPDATE_SRC)

    def test_the_update_supplies_the_position_and_the_anchor(self):
        self.assertIn("getPosASL _player", UPDATE_SRC)
        self.assertIn("EFUNC(core,getGeoAnchor)", UPDATE_SRC)

    def test_the_hud_class_exists(self):
        self.assertIn("class GVAR(hud)", HUD_CLASS_SRC)

    def test_the_config_includes_the_hud_class(self):
        self.assertIn('#include "RscTitles.hpp"', CONFIG_SRC)

    def test_the_update_reads_the_aee_temperature(self):
        self.assertIn("currentTemperature", UPDATE_SRC)

    def test_the_update_reads_the_aee_humidity(self):
        self.assertIn("currentHumidity", UPDATE_SRC)

    def test_the_update_reads_the_aee_wind(self):
        self.assertIn("currentWindStr", UPDATE_SRC)
        self.assertIn("currentWindDir", UPDATE_SRC)

    def test_the_update_uses_the_aee_eye_state(self):
        self.assertIn("EFUNC(core,getEyeState)", UPDATE_SRC)

    def test_the_update_builds_the_hud(self):
        self.assertIn("FUNC(hudBuild)", UPDATE_SRC)

    def test_the_rangefinder_casts_real_geometry(self):
        self.assertIn("lineIntersectsSurfaces", RANGE_SRC)

    def test_the_rangefinder_uses_3d_text_without_an_icon(self):
        self.assertIn("drawIcon3D", RANGE_SRC)
        self.assertIn('"",', RANGE_SRC)

    def test_the_markers_are_read_only(self):
        self.assertIn("allMapMarkers", MARKERS_SRC)
        for writer in ("createMarker", "setMarkerPos", "setMarkerText", "deleteMarker"):
            self.assertNotIn(writer, MARKERS_SRC, writer)

    def test_no_source_references_a_paa_asset(self):
        self.assertNotIn(".paa", ALL_HUD_SRC)

    def test_no_source_references_an_ogg_asset(self):
        self.assertNotIn(".ogg", ALL_HUD_SRC)

    def test_no_editor_code_was_ported(self):
        self.assertNotIn("createEditorLayer", ALL_HUD_SRC)
        self.assertNotIn("FPANO_fnc_editor", ALL_HUD_SRC)

    def test_no_radio_bridge_code_was_ported(self):
        self.assertNotIn("radioBridge", ALL_HUD_SRC)
        self.assertNotIn("FPANO_ECOTI_Comms", ALL_HUD_SRC)

    def test_no_provenance_leaked(self):
        for token in FORBIDDEN_PROVENANCE:
            self.assertNotIn(token, ALL_HUD_SRC, token)


class TestHudWiring(unittest.TestCase):
    """The setting, PREP entries and postInit wiring exist."""

    def test_prep_registers_every_hud_function(self):
        for name in (
            "formatGridDisplay",
            "hudBuild",
            "hudFormatGrid",
            "hudFormatHeading",
            "hudFormatRange",
            "hudMarkers",
            "hudRangefinder",
            "hudUpdate",
        ):
            self.assertIn(f"PREPS(hud,{name});", PREP_SRC, name)

    def test_the_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(hudEnabled,"AEE HUD","Displays",false)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in ("hudEnabled_Name", "hudEnabled_Description"):
            self.assertIn(f"STR_AEE_Optics_{key}", STRINGTABLE_SRC)

    def test_the_mgrs_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(mgrsEnabled,"AEE HUD","Displays",true)',
            SETTINGS_SRC,
        )

    def test_the_mgrs_precision_setting_is_a_list_default_ten(self):
        self.assertIn("QGVAR(mgrsPrecision),", SETTINGS_SRC)
        self.assertIn('"LIST",', SETTINGS_SRC)
        self.assertIn("[[4, 6, 8, 10]", SETTINGS_SRC)
        self.assertIn('"10 (1 m)"', SETTINGS_SRC)

    def test_the_mgrs_stringtable_keys_exist(self):
        for key in (
            "mgrsEnabled_Name",
            "mgrsEnabled_Description",
            "mgrsPrecision_Name",
            "mgrsPrecision_Description",
        ):
            self.assertIn(f"STR_AEE_Optics_{key}", STRINGTABLE_SRC)

    def test_the_postinit_has_the_module_guard(self):
        self.assertIn("AEE_MODULE_POST_INIT", POSTINIT_SRC)

    def test_the_postinit_starts_the_hud_workers(self):
        self.assertIn("FUNC(hudRangefinder)", POSTINIT_SRC)
        self.assertIn("FUNC(hudMarkers)", POSTINIT_SRC)
        self.assertIn("FUNC(hudUpdate)", POSTINIT_SRC)

    def test_the_postinit_hud_is_client_side(self):
        self.assertIn("hasInterface", POSTINIT_SRC)


class TestHudLogging(unittest.TestCase):
    """The HUD is visible in a log (the no-logging defect)."""

    def test_the_build_logs_raise_and_clear(self):
        self.assertIn('"environment HUD: display raised"', BUILD_SRC)
        self.assertIn('"environment HUD: display cleared"', BUILD_SRC)

    def test_the_update_has_a_windowed_log(self):
        self.assertIn("environment HUD update:", UPDATE_SRC)
        self.assertIn("AEE_LOG_DEBUG", UPDATE_SRC)


if __name__ == "__main__":
    unittest.main()
