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
MGRS_MAP_KERNEL = HUD / "fnc_mgrsMapDraw.sqf"
MGRS_MARKER_KERNEL = HUD / "fnc_mgrsMarkerText.sqf"
GPS_BUILD_KERNEL = HUD / "fnc_gpsBuild.sqf"
GPS_UPDATE_KERNEL = HUD / "fnc_gpsUpdate.sqf"
TRACKER_UPDATE_KERNEL = HUD / "fnc_trackerUpdate.sqf"
TRACKER_DRAW_KERNEL = HUD / "fnc_trackerDraw.sqf"
TRACKER_PROJECT_KERNEL = HUD / "fnc_trackerProject.sqf"
GRID_LINES_KERNEL = HUD / "fnc_mgrsGridLines.sqf"
CURSOR_TEXT_KERNEL = HUD / "fnc_mgrsCursorText.sqf"
CORE_GEO = REPO / "addons" / "core" / "functions" / "geo"
CORE_LATLON = CORE_GEO / "fnc_latLonToUtm.sqf"
CORE_UTM2LL = CORE_GEO / "fnc_utmToLatLon.sqf"
CORE_UTM2WORLD = CORE_GEO / "fnc_utmToWorld.sqf"
CORE_FORMAT = CORE_GEO / "fnc_formatMgrs.sqf"
CORE_W2M = CORE_GEO / "fnc_worldToMgrs.sqf"
CORE_TABLES = REPO / "addons" / "core" / "data" / "mgrs_tables.sqf"

HUD_FILE = OPTICS / "RscTitles.hpp"
BUILD_SRC = (HUD / "fnc_hudBuild.sqf").read_text(encoding="utf-8")
UPDATE_SRC = (HUD / "fnc_hudUpdate.sqf").read_text(encoding="utf-8")
RANGE_SRC = (HUD / "fnc_hudRangefinder.sqf").read_text(encoding="utf-8")
MARKERS_SRC = (HUD / "fnc_hudMarkers.sqf").read_text(encoding="utf-8")
FORMAT_DISPLAY_SRC = (HUD / "fnc_formatGridDisplay.sqf").read_text(encoding="utf-8")
MGRS_MAP_SRC = MGRS_MAP_KERNEL.read_text(encoding="utf-8")
MGRS_MARKER_SRC = MGRS_MARKER_KERNEL.read_text(encoding="utf-8")
GRID_LINES_SRC = GRID_LINES_KERNEL.read_text(encoding="utf-8")
CURSOR_TEXT_SRC = CURSOR_TEXT_KERNEL.read_text(encoding="utf-8")
GPS_BUILD_SRC = GPS_BUILD_KERNEL.read_text(encoding="utf-8")
GPS_UPDATE_SRC = GPS_UPDATE_KERNEL.read_text(encoding="utf-8")
TRACKER_UPDATE_SRC = TRACKER_UPDATE_KERNEL.read_text(encoding="utf-8")
TRACKER_DRAW_SRC = TRACKER_DRAW_KERNEL.read_text(encoding="utf-8")
TRACKER_PROJECT_SRC = TRACKER_PROJECT_KERNEL.read_text(encoding="utf-8")
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
        MGRS_MAP_SRC,
        MGRS_MARKER_SRC,
        GRID_LINES_SRC,
        CURSOR_TEXT_SRC,
        GPS_BUILD_SRC,
        GPS_UPDATE_SRC,
        TRACKER_UPDATE_SRC,
        TRACKER_DRAW_SRC,
        TRACKER_PROJECT_SRC,
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


def mgrs_marker_text(label, position, anchor, precision, mgrs):
    """Run the real marker-text kernel with a stub worldToMgrs."""
    globals_ = {
        "__EFUNC__core_worldToMgrs": lambda _p, _a, _prec: [
            mgrs,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
        ],
    }
    return run_sqf(MGRS_MARKER_KERNEL, [label, position, anchor, precision], globals_)


ALTIS_ANCHOR = [
    39.906515,
    25.246742,
    35,
    30720,
    25.011957,
    39.718452,
    25.481527,
    40.094578,
    "mapArea",
]


def _core_globals():
    """The real core geo kernels, for the optics grid kernel to call."""
    g = {"aee_core_mgrsTables": run_sqf(CORE_TABLES, [])}
    g["__FUNC__latLonToUtm"] = lambda lat, lon: run_sqf(CORE_LATLON, [lat, lon])
    g["__FUNC__utmToLatLon"] = lambda e, n, z, h: run_sqf(CORE_UTM2LL, [e, n, z, h])
    g["__FUNC__utmToWorld"] = lambda e, n, z, h, a: run_sqf(
        CORE_UTM2WORLD, [e, n, z, h, a], _core_globals()
    )
    g["__FUNC__formatMgrs"] = lambda e, n, z, p, lat: run_sqf(
        CORE_FORMAT, [e, n, z, p, lat], _core_globals()
    )
    g["__FUNC__worldToMgrs"] = lambda p, a, prec: run_sqf(
        CORE_W2M, [p, a, prec], _core_globals()
    )
    return g


def grid_lines(anchor, rect):
    """Run the real grid kernel against the real core conversions."""
    g = _core_globals()
    g["__EFUNC__core_worldToMgrs"] = lambda p, a, prec: run_sqf(
        CORE_W2M, [p, a, prec], _core_globals()
    )
    g["__EFUNC__core_utmToWorld"] = lambda e, n, z, h, a: run_sqf(
        CORE_UTM2WORLD, [e, n, z, h, a], _core_globals()
    )
    g["__EFUNC__core_formatMgrs"] = lambda e, n, z, p, lat: run_sqf(
        CORE_FORMAT, [e, n, z, p, lat], _core_globals()
    )
    return run_sqf(GRID_LINES_KERNEL, [anchor, rect], g)


def cursor_text(mgrs, elevation):
    """Run the real cursor-readout kernel."""
    return run_sqf(CURSOR_TEXT_KERNEL, [mgrs, elevation], {})


def tracker_project(position, ellipse, fix, link, seed):
    """Run the real pure tracker projector."""
    return run_sqf(TRACKER_PROJECT_KERNEL, [position, ellipse, fix, link, seed], {})


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


class TestHudMgrsMarkerText(unittest.TestCase):
    """fnc_mgrsMarkerText, executed: a marker position as an MGRS label."""

    def test_a_label_is_prefixed_to_the_mgrs(self):
        self.assertEqual(
            mgrs_marker_text("Alpha", [0, 0, 0], [0] * 9, 10, "35SLE5013418852"),
            "Alpha 35SLE5013418852",
        )

    def test_an_empty_label_returns_the_mgrs_alone(self):
        self.assertEqual(
            mgrs_marker_text("", [0, 0, 0], [0] * 9, 10, "35SLE5013418852"),
            "35SLE5013418852",
        )

    def test_an_empty_mgrs_returns_the_label_alone(self):
        self.assertEqual(
            mgrs_marker_text("Alpha", [0, 0, 0], [0] * 9, 10, ""),
            "Alpha",
        )


class TestHudGpsReadout(unittest.TestCase):
    """The GVAR(gps) display, its idcs and the ItemGPS gate."""

    def test_the_gps_display_exists_with_a_free_idd(self):
        self.assertIn("class GVAR(gps)", HUD_CLASS_SRC)
        self.assertIn("idd = 10783;", HUD_CLASS_SRC)

    def test_the_gps_fields_have_free_idcs(self):
        for idc in (9020, 9021, 9022, 9023):
            self.assertIn(f"idc = {idc};", HUD_CLASS_SRC, idc)

    def test_the_update_gates_on_holding_an_itemgps(self):
        self.assertIn("ItemGPS", GPS_UPDATE_SRC)
        self.assertIn("assignedItems", GPS_UPDATE_SRC)

    def test_the_update_gates_on_the_mgrs_setting(self):
        self.assertIn("QGVAR(mgrsEnabled)", GPS_UPDATE_SRC)


class TestHudSourceContract(unittest.TestCase):
    """The engine readers carry the source's mechanisms."""

    def test_the_map_handler_draws_icons(self):
        self.assertIn("_map drawIcon", MGRS_MAP_SRC)

    def test_the_map_handler_cross_checks_the_engine_grid(self):
        self.assertIn("mapGridPosition _player", MGRS_MAP_SRC)

    def test_the_map_handler_attaches_a_draw_handler(self):
        self.assertIn('ctrlAddEventHandler ["Draw"', MGRS_MAP_SRC)

    def test_the_map_handler_creates_no_marker(self):
        for writer in ("createMarker", "setMarkerPos", "setMarkerText", "deleteMarker"):
            self.assertNotIn(writer, MGRS_MAP_SRC, writer)

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


class TestHudMapGridContract(unittest.TestCase):
    """The map draw path carries the grid overlay and the cursor readout."""

    def test_the_map_handler_draws_grid_lines(self):
        self.assertIn("_map drawLine", MGRS_MAP_SRC)

    def test_the_map_handler_calls_the_grid_kernel(self):
        self.assertIn("call FUNC(mgrsGridLines)", MGRS_MAP_SRC)

    def test_the_map_handler_converts_the_control_rect(self):
        self.assertIn("ctrlMapScreenToWorld", MGRS_MAP_SRC)
        self.assertIn("ctrlPosition _map", MGRS_MAP_SRC)

    def test_the_map_handler_reads_the_cursor(self):
        self.assertIn("getMousePosition", MGRS_MAP_SRC)

    def test_the_map_handler_hides_the_engine_readout(self):
        # The engine readout is the map display's RscMapControlTooltip
        # control (idc 2350).  The overlay hides it so the map shows one
        # readout, the aee MGRS one.
        self.assertIn("displayCtrl 2350", MGRS_MAP_SRC)
        self.assertIn("ctrlShow false", MGRS_MAP_SRC)

    def test_the_map_handler_reads_the_engine_readout_rect(self):
        # The engine moves the tooltip to the cursor, so its rectangle is
        # where the aee readout is drawn.
        self.assertIn("ctrlPosition _engineReadout", MGRS_MAP_SRC)
        self.assertIn("_readoutPos", MGRS_MAP_SRC)

    def test_the_map_handler_calls_the_cursor_kernel(self):
        self.assertIn("call FUNC(mgrsCursorText)", MGRS_MAP_SRC)

    def test_the_map_handler_reads_the_terrain_height(self):
        self.assertIn("getTerrainHeightASL", MGRS_MAP_SRC)

    def test_the_map_handler_gates_the_grid_and_cursor(self):
        self.assertIn("QGVAR(mgrsMapGrid)", MGRS_MAP_SRC)
        self.assertIn("QGVAR(mgrsCursorReadout)", MGRS_MAP_SRC)

    def test_the_grid_plan_is_cached_on_the_visible_rectangle(self):
        self.assertIn("QGVAR(mgrsGridCache)", MGRS_MAP_SRC)

    def test_the_grid_kernel_creates_no_marker(self):
        for writer in ("createMarker", "setMarkerPos", "setMarkerText", "deleteMarker"):
            self.assertNotIn(writer, GRID_LINES_SRC, writer)

    def test_the_grid_kernel_reuses_the_core_kernels(self):
        self.assertIn("EFUNC(core,worldToMgrs)", GRID_LINES_SRC)
        self.assertIn("EFUNC(core,utmToWorld)", GRID_LINES_SRC)
        self.assertIn("EFUNC(core,formatMgrs)", GRID_LINES_SRC)


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
            "mgrsCursorText",
            "mgrsGridLines",
            "mgrsMapDraw",
            "mgrsMarkerText",
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

    def test_the_mgrs_map_grid_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(mgrsMapGrid,"AEE HUD","Displays",true)',
            SETTINGS_SRC,
        )

    def test_the_mgrs_cursor_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(mgrsCursorReadout,"AEE HUD","Displays",true)',
            SETTINGS_SRC,
        )

    def test_the_map_grid_stringtable_keys_exist(self):
        for key in (
            "mgrsMapGrid_Name",
            "mgrsMapGrid_Description",
            "mgrsCursorReadout_Name",
            "mgrsCursorReadout_Description",
        ):
            self.assertIn(f"STR_AEE_Optics_{key}", STRINGTABLE_SRC)

    def test_the_postinit_has_the_module_guard(self):
        self.assertIn("AEE_MODULE_POST_INIT", POSTINIT_SRC)

    def test_the_postinit_starts_the_hud_workers(self):
        self.assertIn("FUNC(hudRangefinder)", POSTINIT_SRC)
        self.assertIn("FUNC(hudMarkers)", POSTINIT_SRC)
        self.assertIn("FUNC(hudUpdate)", POSTINIT_SRC)

    def test_the_postinit_starts_the_mgrs_map_overlay(self):
        self.assertIn("FUNC(mgrsMapDraw)", POSTINIT_SRC)

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


class TestHudTrackerProject(unittest.TestCase):
    """fnc_trackerProject, executed: the exact position plus the modelled error."""

    def test_a_zero_error_keeps_the_exact_position(self):
        shown = tracker_project(
            [100, 200, 5],
            [0, 0, 0, 0, 0, 0, 0, 0],
            ["ok", 0, 1, 0, 0],
            ["received", 1, 0, 0],
            0.5,
        )
        self.assertEqual(shown[0], [100, 200, 5])
        self.assertEqual(shown[5], 0.0)

    def test_a_nonzero_error_displaces_the_displayed_position(self):
        shown = tracker_project(
            [100, 200, 5],
            [3.6, 3.6, 5.85, 3.6, 3.6, 0, 4.2, 7.2],
            ["degraded", 0, 0.5, 20, 0.25],
            ["received", 1, 0, 0],
            0.5,
        )
        self.assertNotEqual(shown[0], [100, 200, 5])
        # The displacement magnitude is R95 7.2 + added 0 + lag 20.
        self.assertAlmostEqual(shown[5], 27.2, places=6)

    def test_the_ellipse_and_the_track_age_pass_through(self):
        shown = tracker_project(
            [0, 0, 0],
            [3.6, 3.6, 5.85, 3.6, 2.0, 90, 4.2, 7.2],
            ["ok", 0, 1, 0, 0],
            ["received", 1, 12.5, 0],
            0.0,
        )
        self.assertAlmostEqual(shown[1], 3.6, places=6)
        self.assertAlmostEqual(shown[2], 2.0, places=6)
        self.assertAlmostEqual(shown[3], 90, places=6)
        self.assertAlmostEqual(shown[4], 12.5, places=6)

    def test_the_lag_alone_displaces(self):
        shown = tracker_project(
            [0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            ["degraded", 0, 0.5, 40, 0.25],
            ["lost", 0, 0, 0],
            0.0,
        )
        self.assertAlmostEqual(shown[5], 40.0, places=6)
        self.assertNotEqual(shown[0], [0, 0, 0])


class TestHudTrackerContract(unittest.TestCase):
    """The driver calls the three kernels and applies the offset."""

    def test_the_driver_calls_the_error_kernel(self):
        self.assertIn("call EFUNC(core,gnssErrorEllipse)", TRACKER_UPDATE_SRC)

    def test_the_driver_calls_the_fix_kernel(self):
        self.assertIn("call EFUNC(core,gnssFixState)", TRACKER_UPDATE_SRC)

    def test_the_driver_calls_the_datalink_kernel(self):
        self.assertIn("call EFUNC(core,datalinkState)", TRACKER_UPDATE_SRC)

    def test_the_driver_applies_the_offset(self):
        self.assertIn("call FUNC(trackerProject)", TRACKER_UPDATE_SRC)

    def test_the_projector_displaces_by_the_total_error(self):
        self.assertIn("(sin _rad) * _totalError", TRACKER_PROJECT_SRC)
        self.assertIn("(cos _rad) * _totalError", TRACKER_PROJECT_SRC)

    def test_the_driver_reads_the_local_group_exact_positions(self):
        self.assertIn("units (group _player)", TRACKER_UPDATE_SRC)
        self.assertIn("getPosASL _unit", TRACKER_UPDATE_SRC)

    def test_the_driver_publishes_the_track_state(self):
        self.assertIn("setVariable [QGVAR(trackerTracks)", TRACKER_UPDATE_SRC)
        self.assertIn("setVariable [QGVAR(trackerR95)", TRACKER_UPDATE_SRC)
        self.assertIn("setVariable [QGVAR(trackerFix)", TRACKER_UPDATE_SRC)

    def test_the_driver_never_public_variables(self):
        self.assertNotIn("publicVariable", TRACKER_UPDATE_SRC)
        self.assertNotIn("publicVariable", TRACKER_DRAW_SRC)

    def test_the_suppression_uses_the_allowed_command(self):
        self.assertIn(
            "disableMapIndicators [true, false, false, false]", TRACKER_UPDATE_SRC
        )

    def test_the_source_records_the_suppression_ceiling(self):
        self.assertIn("setGroupIconsVisible", TRACKER_UPDATE_SRC)
        self.assertIn("extended map content", TRACKER_UPDATE_SRC)

    def test_the_draw_renders_the_ellipse_and_the_label(self):
        self.assertIn("drawEllipse", TRACKER_DRAW_SRC)
        self.assertIn("_map drawIcon", TRACKER_DRAW_SRC)
        self.assertIn("drawIcon3D", TRACKER_DRAW_SRC)

    def test_the_draw_creates_no_marker(self):
        for writer in ("createMarker", "setMarkerPos", "setMarkerText", "deleteMarker"):
            self.assertNotIn(writer, TRACKER_DRAW_SRC, writer)

    def test_the_gps_readout_consumes_the_tracker_state(self):
        self.assertIn("QGVAR(trackerFix)", GPS_UPDATE_SRC)
        self.assertIn("QGVAR(trackerR95)", GPS_UPDATE_SRC)


class TestHudTrackerWiring(unittest.TestCase):
    """The tracker PREP entries, settings, stringtable and postInit wiring."""

    def test_prep_registers_the_tracker_functions(self):
        for name in ("trackerDraw", "trackerProject", "trackerUpdate"):
            self.assertIn(f"PREPS(hud,{name});", PREP_SRC, name)

    def test_the_tracker_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(trackerEnabled,"AEE HUD","Tracker",false)',
            SETTINGS_SRC,
        )

    def test_the_suppression_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(trackerSuppressIcons,"AEE HUD","Tracker",false)',
            SETTINGS_SRC,
        )

    def test_the_tracker_stringtable_keys_exist(self):
        for key in (
            "trackerEnabled_Name",
            "trackerEnabled_Description",
            "trackerSuppressIcons_Name",
            "trackerSuppressIcons_Description",
            "trackerInterval_Name",
            "trackerInterval_Description",
        ):
            self.assertIn(f"STR_AEE_Optics_{key}", STRINGTABLE_SRC)

    def test_the_postinit_starts_the_tracker(self):
        self.assertIn("FUNC(trackerUpdate)", POSTINIT_SRC)
        self.assertIn("FUNC(trackerDraw)", POSTINIT_SRC)


if __name__ == "__main__":
    unittest.main()
