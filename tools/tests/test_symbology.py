#!/usr/bin/env python3
"""AEE NATO/OPFOR map symbology kernel tests.

Executes the REAL pure kernels through tools/tests/sqf_lite.py:

  addons/optics/functions/symbology/fnc_symbolPalette.sqf
  addons/optics/functions/symbology/fnc_symbolFrame.sqf

Each kernel is argument-driven, so a fixture call proves it with no engine.

Run: python3 -m unittest tools.tests.test_symbology -v
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
SYM = OPTICS / "functions" / "symbology"
PALETTE_KERNEL = SYM / "fnc_symbolPalette.sqf"
FRAME_KERNEL = SYM / "fnc_symbolFrame.sqf"
ICON_KERNEL = SYM / "fnc_symbolIcon.sqf"
RESOLVE_KERNEL = SYM / "fnc_symbolResolve.sqf"
DRAW_PLAN_KERNEL = SYM / "fnc_symbolDrawPlan.sqf"
CATEGORY_KERNEL = SYM / "fnc_symbolCategory.sqf"
MARKER_CAT_KERNEL = SYM / "fnc_symbologyMarkerCategory.sqf"
UNIT_CAT_KERNEL = SYM / "fnc_symbologyUnitCategory.sqf"
AFFILIATION_KERNEL = SYM / "fnc_symbologyAffiliation.sqf"
PALETTE_FRIENDLY_KERNEL = SYM / "fnc_symbologyPaletteFriendly.sqf"
TABLES_SQF = OPTICS / "data" / "symbology_tables.sqf"
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")
SYM_TABLES = run_sqf(TABLES_SQF, [])
MARKER_CAT_SRC = MARKER_CAT_KERNEL.read_text(encoding="utf-8")
UNIT_CAT_SRC = UNIT_CAT_KERNEL.read_text(encoding="utf-8")
AFFILIATION_SRC = AFFILIATION_KERNEL.read_text(encoding="utf-8")
SYM_MAP_KERNEL = SYM / "fnc_symbologyMapDraw.sqf"
SYM_MAP_SRC = SYM_MAP_KERNEL.read_text(encoding="utf-8")
SYM_WORLD_KERNEL = SYM / "fnc_symbologyWorldDraw.sqf"
SYM_WORLD_SRC = SYM_WORLD_KERNEL.read_text(encoding="utf-8")
HUD_MARKERS_SRC = (OPTICS / "functions" / "hud" / "fnc_hudMarkers.sqf").read_text(
    encoding="utf-8"
)
POSTINIT_SRC = (OPTICS / "XEH_postInit.sqf").read_text(encoding="utf-8")
CONFIG_SRC = (OPTICS / "config.cpp").read_text(encoding="utf-8")
RSCTITLES_SRC = (OPTICS / "RscTitles.hpp").read_text(encoding="utf-8")
MGRS_MAP_SRC = (OPTICS / "functions" / "hud" / "fnc_mgrsMapDraw.sqf").read_text(
    encoding="utf-8"
)
FONTS = OPTICS / "data" / "fonts"


def palette(affiliation, pal):
    return run_sqf(PALETTE_KERNEL, [affiliation, pal], {})


def frame(affiliation, dimension):
    return run_sqf(FRAME_KERNEL, [affiliation, dimension], {})


def icon(icon_id):
    return run_sqf(ICON_KERNEL, [icon_id], {})


def resolve(side, category, affiliation, echelon, pal):
    """Run the real resolver with the real colour kernel injected."""
    globals_ = {
        "__FUNC__symbolPalette": lambda aff, p: run_sqf(PALETTE_KERNEL, [aff, p], {}),
    }
    return run_sqf(
        RESOLVE_KERNEL, [side, category, affiliation, echelon, pal], globals_
    )


def draw_plan(spec):
    """Run the real draw-plan kernel with the real frame and icon kernels."""
    globals_ = {
        "__FUNC__symbolFrame": lambda aff, dim: run_sqf(FRAME_KERNEL, [aff, dim], {}),
        "__FUNC__symbolIcon": lambda icon_id: run_sqf(ICON_KERNEL, [icon_id], {}),
    }
    return run_sqf(DRAW_PLAN_KERNEL, [spec], globals_)


def category(value, kind="marker"):
    """Run the real category kernel against the real generated table."""
    return run_sqf(
        CATEGORY_KERNEL, [value, kind], {"aee_optics_symbologyTables": SYM_TABLES}
    )


def marker_category(marker_type):
    """Run the real marker adapter with the real category kernel injected."""
    globals_ = {
        "__FUNC__symbolCategory": lambda value, kind: run_sqf(
            CATEGORY_KERNEL, [value, kind], {"aee_optics_symbologyTables": SYM_TABLES}
        ),
    }
    return run_sqf(MARKER_CAT_KERNEL, ["", marker_type], globals_)


def affiliation(colour, friendly):
    return run_sqf(AFFILIATION_KERNEL, ["", colour, friendly], {})


def palette_friendly(pal, local_side):
    return run_sqf(PALETTE_FRIENDLY_KERNEL, [pal, local_side], {})


class TestSymbolPalette(unittest.TestCase):
    """fnc_symbolPalette, executed: affiliation and palette -> RGBA."""

    def test_hostile_nato_is_red(self):
        self.assertEqual(palette("hostile", "NATO"), [1, 0, 0, 1])

    def test_friend_nato_is_cyan(self):
        self.assertEqual(palette("friend", "NATO"), [0, 1, 1, 1])

    def test_neutral_nato_is_green(self):
        self.assertEqual(palette("neutral", "NATO"), [0, 1, 0, 1])

    def test_unknown_nato_is_yellow(self):
        self.assertEqual(palette("unknown", "NATO"), [1, 1, 0, 1])

    def test_friend_opfor_is_red(self):
        self.assertEqual(palette("friend", "OPFOR"), [1, 0, 0, 1])

    def test_hostile_opfor_is_cyan(self):
        self.assertEqual(palette("hostile", "OPFOR"), [0, 1, 1, 1])

    def test_auto_returns_the_nato_set(self):
        self.assertEqual(palette("friend", "Auto"), [0, 1, 1, 1])
        self.assertEqual(palette("hostile", "Auto"), [1, 0, 0, 1])

    def test_an_unknown_palette_falls_back_to_nato(self):
        self.assertEqual(palette("friend", "bogus"), [0, 1, 1, 1])


class TestSymbolFrame(unittest.TestCase):
    """fnc_symbolFrame, executed: affiliation + dimension -> polylines."""

    def test_friend_land_is_one_rectangle(self):
        out = frame("friend", "land")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], [[-1, -0.6], [1, -0.6], [1, 0.6], [-1, 0.6]])

    def test_hostile_land_is_a_diamond_on_the_axes(self):
        out = frame("hostile", "land")
        self.assertEqual(out[0], [[0, -1], [1, 0], [0, 1], [-1, 0]])

    def test_friend_air_has_a_domed_top_edge(self):
        top = frame("friend", "air")[0]
        self.assertGreater(len(top), 4)
        self.assertTrue(any(point[1] > 0.6 for point in top))

    def test_unknown_land_is_a_four_lobe_quatrefoil(self):
        top = frame("unknown", "land")[0]
        self.assertGreater(len(top), 8)
        spans = [
            max(point[0] for point in top) - min(point[0] for point in top),
            max(point[1] for point in top) - min(point[1] for point in top),
        ]
        self.assertGreater(spans[0], 0.9)
        self.assertGreater(spans[1], 0.9)

    def test_subsurface_curves_the_bottom_edge(self):
        bottom = frame("friend", "subsurface")[0]
        self.assertTrue(any(point[1] < -0.6 for point in bottom))

    def test_every_frame_point_stays_in_the_unit_box(self):
        for affiliation in ("friend", "hostile", "neutral", "unknown"):
            for dimension in ("land", "air", "subsurface"):
                with self.subTest(affiliation=affiliation, dimension=dimension):
                    for polyline in frame(affiliation, dimension):
                        for point in polyline:
                            self.assertLessEqual(abs(point[0]), 1.0)
                            self.assertLessEqual(abs(point[1]), 1.0)


class TestSymbolIcon(unittest.TestCase):
    """fnc_symbolIcon, executed: icon id -> vector primitives."""

    ICON_IDS = (
        "infantry",
        "armour",
        "motorised",
        "artillery",
        "engineer",
        "signal",
        "medical",
        "supply",
        "support",
        "recon",
        "air_defence",
        "fixed_wing",
        "rotary",
        "uav",
        "sea_surface",
        "subsurface",
        "installation",
        "hq",
        "waypoint",
        "unknown",
    )

    def test_infantry_is_two_crossed_lines(self):
        out = icon("infantry")
        self.assertEqual(len(out), 2)
        self.assertTrue(all(prim[0] == "line" for prim in out))

    def test_armour_is_one_ellipse(self):
        out = icon("armour")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], "ellipse")

    def test_unknown_is_empty(self):
        self.assertEqual(icon("unknown"), [])

    def test_every_curated_class_returns_primitives(self):
        for icon_id in self.ICON_IDS:
            with self.subTest(icon_id=icon_id):
                self.assertIsInstance(icon(icon_id), list)

    def test_every_primitive_stays_in_the_inner_box(self):
        for icon_id in self.ICON_IDS:
            for kind, points in icon(icon_id):
                with self.subTest(icon_id=icon_id, kind=kind):
                    if kind == "ellipse":
                        centre, axes, _angle = points
                        self.assertLessEqual(abs(centre[0]) + axes[0], 0.55 + 1e-9)
                        self.assertLessEqual(abs(centre[1]) + axes[1], 0.55 + 1e-9)
                    else:
                        for x, y in points:
                            self.assertLessEqual(abs(x), 0.55 + 1e-9)
                            self.assertLessEqual(abs(y), 0.55 + 1e-9)


class TestSymbolResolve(unittest.TestCase):
    """fnc_symbolResolve, executed: inputs -> one symbol specification."""

    def test_a_hostile_armour_symbol_is_a_red_diamond(self):
        spec = resolve("east", "armour", "hostile", "squad", "NATO")
        self.assertEqual(spec[0], "hostile")
        self.assertEqual(spec[1], "diamond")
        self.assertEqual(spec[2], "land")
        self.assertEqual(spec[3], [1, 0, 0, 1])
        self.assertEqual(spec[4], "armour")
        self.assertEqual(spec[5], "squad")

    def test_a_friendly_infantry_symbol_is_a_rectangle(self):
        spec = resolve("west", "infantry", "friend", "company", "NATO")
        self.assertEqual(spec[1], "rect")
        self.assertEqual(spec[3], [0, 1, 1, 1])
        self.assertEqual(spec[4], "infantry")

    def test_the_palette_swap_flips_the_friendly_colour(self):
        spec = resolve("west", "infantry", "friend", "company", "OPFOR")
        self.assertEqual(spec[3], [1, 0, 0, 1])

    def test_neutral_is_a_square_and_unknown_is_a_quatrefoil(self):
        self.assertEqual(
            resolve("", "infantry", "neutral", "team", "NATO")[1], "square"
        )
        self.assertEqual(
            resolve("", "infantry", "unknown", "team", "NATO")[1], "quatrefoil"
        )

    def test_the_dimension_follows_the_category(self):
        for category, dimension in (
            ("armour", "land"),
            ("fixed_wing", "air"),
            ("rotary", "air"),
            ("uav", "air"),
            ("sea_surface", "sea"),
            ("subsurface", "subsurface"),
            ("installation", "installation"),
        ):
            with self.subTest(category=category):
                spec = resolve("", category, "friend", "squad", "NATO")
                self.assertEqual(spec[2], dimension)

    def test_an_unknown_category_falls_back_to_the_empty_icon(self):
        spec = resolve("", "bogus", "friend", "squad", "NATO")
        self.assertEqual(spec[4], "unknown")


class TestSymbolCategory(unittest.TestCase):
    """fnc_symbolCategory, executed: engine name -> class category."""

    def test_the_shipped_marker_types_map(self):
        for marker_type, expected in (
            ("b_inf", "infantry"),
            ("o_armor", "armour"),
            ("n_inf", "infantry"),
            ("c_air", "rotary"),
            ("hd_dot", "waypoint"),
            ("group_3", "unknown"),
            ("flag_NATO", "unknown"),
            ("GroundSupport_CAS_WEST", "support"),
        ):
            with self.subTest(marker_type=marker_type):
                self.assertEqual(category(marker_type), expected)

    def test_an_unknown_marker_type_is_unknown(self):
        self.assertEqual(category("bogus_marker"), "unknown")

    def test_a_vehicle_class_maps(self):
        self.assertEqual(category("Men", "class"), "infantry")
        self.assertEqual(category("Armored", "class"), "armour")
        self.assertEqual(category("Air", "class"), "rotary")

    def test_an_unknown_vehicle_class_is_unknown(self):
        self.assertEqual(category("Bogus", "class"), "unknown")


class TestSymbolAdapters(unittest.TestCase):
    """The engine adapters, executed through their test seams."""

    def test_the_marker_adapter_maps_the_shipped_types(self):
        for marker_type, expected in (
            ("b_inf", "infantry"),
            ("o_armor", "armour"),
            ("n_inf", "infantry"),
            ("hd_dot", "waypoint"),
        ):
            with self.subTest(marker_type=marker_type):
                self.assertEqual(marker_category(marker_type), expected)

    def test_the_affiliation_adapter_maps_the_colour_classes(self):
        self.assertEqual(affiliation("ColorWEST", "WEST"), "friend")
        self.assertEqual(affiliation("ColorEAST", "WEST"), "hostile")
        self.assertEqual(affiliation("ColorGUER", "WEST"), "neutral")
        self.assertEqual(affiliation("ColorCIV", "WEST"), "neutral")
        self.assertEqual(affiliation("ColorUNKNOWN", "WEST"), "unknown")

    def test_the_affiliation_follows_the_friendly_side(self):
        self.assertEqual(affiliation("ColorWEST", "EAST"), "hostile")
        self.assertEqual(affiliation("ColorEAST", "EAST"), "friend")

    def test_the_palette_friendly_adapter_resolves_the_side(self):
        self.assertEqual(palette_friendly("NATO", "EAST"), "WEST")
        self.assertEqual(palette_friendly("OPFOR", "WEST"), "EAST")
        self.assertEqual(palette_friendly("Auto", "EAST"), "EAST")
        self.assertEqual(palette_friendly("Auto", "WEST"), "WEST")


class TestSymbolAdapterContracts(unittest.TestCase):
    """The engine adapters carry the engine reads and call the pure kernels."""

    def test_the_marker_adapter_reads_marker_type(self):
        self.assertIn("markerType", MARKER_CAT_SRC)

    def test_the_marker_adapter_calls_the_category_kernel(self):
        self.assertIn("call FUNC(symbolCategory)", MARKER_CAT_SRC)

    def test_the_affiliation_adapter_reads_get_marker_colour(self):
        self.assertIn("getMarkerColor", AFFILIATION_SRC)

    def test_the_unit_adapter_reads_the_vehicle_class(self):
        self.assertIn("typeOf", UNIT_CAT_SRC)
        self.assertIn("vehicleClass", UNIT_CAT_SRC)
        self.assertIn("unitClass", UNIT_CAT_SRC)

    def test_the_unit_adapter_calls_the_category_kernel(self):
        self.assertIn("call FUNC(symbolCategory)", UNIT_CAT_SRC)


class TestSymbolDrawPlan(unittest.TestCase):
    """fnc_symbolDrawPlan, executed: spec -> ordered draw primitives."""

    SPEC = ["friend", "rect", "land", [0, 1, 1, 1], "infantry", "squad"]

    def test_the_frame_primitives_come_first(self):
        plan = draw_plan(self.SPEC)
        self.assertEqual(plan[0][0], "poly")
        self.assertEqual(plan[0][2], "frame")
        self.assertEqual(plan[0][1], [[-1, -0.6], [1, -0.6], [1, 0.6], [-1, 0.6]])

    def test_the_icon_primitives_come_next(self):
        plan = draw_plan(self.SPEC)
        icon_prims = [prim for prim in plan if prim[2] == "icon"]
        self.assertEqual(len(icon_prims), 2)
        self.assertTrue(all(prim[0] == "line" for prim in icon_prims))

    def test_the_plan_has_a_closed_rectangle_and_two_crossed_lines(self):
        plan = draw_plan(self.SPEC)
        rect = plan[0][1]
        self.assertEqual(len(rect), 4)
        crossed = [prim for prim in plan if prim[2] == "icon"]
        self.assertEqual(len(crossed), 2)
        # One line rises left to right, the other falls: a saltire.
        self.assertGreater(crossed[0][1][1][1] - crossed[0][1][0][1], 0)
        self.assertLess(crossed[1][1][1][1] - crossed[1][1][0][1], 0)

    def test_every_primitive_kind_is_drawable(self):
        for spec in (
            self.SPEC,
            ["hostile", "diamond", "air", [1, 0, 0, 1], "armour", "company"],
            ["unknown", "quatrefoil", "land", [1, 1, 0, 1], "bogus", "corps"],
        ):
            with self.subTest(spec=spec):
                for kind, points, hint in draw_plan(spec):
                    self.assertIn(kind, ("line", "poly", "ellipse"))
                    self.assertIn(hint, ("frame", "icon"))
                    self.assertIsInstance(points, list)

    def test_a_squad_adds_one_echelon_dot(self):
        plan = draw_plan(self.SPEC)
        dots = [prim for prim in plan if prim[0] == "ellipse" and prim[2] == "frame"]
        self.assertEqual(len(dots), 1)

    def test_an_unknown_echelon_adds_no_mark(self):
        plan = draw_plan(
            ["friend", "rect", "land", [0, 1, 1, 1], "infantry", "unknown"]
        )
        marks = [
            prim
            for prim in plan
            if prim[2] == "frame" and prim[1] != plan[0][1] and len(prim[1]) != 1
        ]
        self.assertEqual(marks, [])

    def test_label_anchors_are_single_point_polys(self):
        plan = draw_plan(self.SPEC)
        anchors = [prim for prim in plan if prim[0] == "poly" and len(prim[1]) == 1]
        self.assertEqual(len(anchors), 2)

    def test_the_kernel_calls_no_engine_draw_command(self):
        src = DRAW_PLAN_KERNEL.read_text(encoding="utf-8")
        for forbidden in ("drawLine", "drawPolygon", "drawEllipse", "drawIcon"):
            self.assertNotIn(forbidden, src)


class TestSymbologyMapDrawContract(unittest.TestCase):
    """fnc_symbologyMapDraw carries the engine wiring and the local restore."""

    def test_the_draw_handler_is_attached_to_the_map_control(self):
        self.assertIn('ctrlAddEventHandler ["Draw"', SYM_MAP_SRC)
        self.assertIn("findDisplay 12", SYM_MAP_SRC)
        self.assertIn("displayCtrl 51", SYM_MAP_SRC)

    def test_the_engine_indicators_are_suppressed_where_allowed(self):
        self.assertIn("disableMapIndicators [true, true, true, true]", SYM_MAP_SRC)

    def test_every_marker_is_hidden_locally(self):
        self.assertIn("allMapMarkers", SYM_MAP_SRC)
        self.assertIn("setMarkerAlphaLocal 0", SYM_MAP_SRC)

    def test_the_original_alpha_is_recorded_and_restored(self):
        self.assertIn("markerAlpha _name", SYM_MAP_SRC)
        self.assertIn("setMarkerAlphaLocal (_x select 1)", SYM_MAP_SRC)

    def test_the_geometry_is_converted_from_the_unit_box(self):
        self.assertIn("ctrlMapWorldToScreen", SYM_MAP_SRC)
        self.assertIn("ctrlMapScreenToWorld", SYM_MAP_SRC)

    def test_the_frame_icon_and_label_are_drawn(self):
        self.assertIn("drawPolygon", SYM_MAP_SRC)
        self.assertIn("drawLine", SYM_MAP_SRC)
        self.assertIn("drawEllipse", SYM_MAP_SRC)
        self.assertIn("drawIcon", SYM_MAP_SRC)

    def test_no_global_marker_command_is_called(self):
        for forbidden in (
            "setMarkerAlpha(",
            "setMarkerColor",
            "setMarkerText",
            "setMarkerPos",
            "deleteMarker",
        ):
            self.assertNotIn(forbidden, SYM_MAP_SRC)

    def test_no_texture_path_is_drawn(self):
        self.assertIn('drawIcon [\n                    "", _colour', SYM_MAP_SRC)

    def test_the_label_carries_the_font_parameter(self):
        self.assertIn('_font, "center"', SYM_MAP_SRC)

    def test_the_markers_player_and_units_are_drawn(self):
        for adapter in (
            "FUNC(symbologyMarkerCategory)",
            "FUNC(symbologyAffiliation)",
            "FUNC(symbolResolve)",
            "FUNC(symbolDrawPlan)",
            "FUNC(symbologyUnitCategory)",
        ):
            self.assertIn(adapter, SYM_MAP_SRC)


class TestSymbologyWorldDrawContract(unittest.TestCase):
    """fnc_symbologyWorldDraw carries the Draw3D wiring and the range gate."""

    def test_the_worker_is_a_draw3d_handler(self):
        self.assertIn('addMissionEventHandler ["Draw3D"', SYM_WORLD_SRC)

    def test_the_frame_and_glyph_are_drawn_as_3d_lines(self):
        self.assertIn("drawLine3D", SYM_WORLD_SRC)

    def test_the_label_carries_the_font_parameter(self):
        self.assertIn("drawIcon3D", SYM_WORLD_SRC)
        self.assertIn('_font, "center"', SYM_WORLD_SRC)

    def test_the_symbols_are_drawn_out_to_a_set_range(self):
        self.assertIn("#define SYMBOLOGY_WORLD_RANGE", SYM_WORLD_SRC)
        self.assertIn("<= SYMBOLOGY_WORLD_RANGE", SYM_WORLD_SRC)

    def test_the_unit_list_is_rebuilt_at_most_once_a_second(self):
        self.assertIn("symbologyWorldTime", SYM_WORLD_SRC)
        self.assertIn("(_now - _last) > 1", SYM_WORLD_SRC)
        self.assertIn("allUnits", SYM_WORLD_SRC)

    def test_the_worker_states_the_engine_icons_cannot_be_suppressed(self):
        # The honest ceiling is recorded, so the worker makes no false claim
        # to remove the engine's own 3D unit icons.
        self.assertIn("cannot be suppressed", SYM_WORLD_SRC)

    def test_the_worker_calls_the_resolver_and_the_draw_plan(self):
        self.assertIn("FUNC(symbolResolve)", SYM_WORLD_SRC)
        self.assertIn("FUNC(symbolDrawPlan)", SYM_WORLD_SRC)


class TestHudMarkersFrameContract(unittest.TestCase):
    """fnc_hudMarkers draws the symbol frame in front of its text label."""

    def test_the_frame_is_built_from_the_draw_plan(self):
        self.assertIn("FUNC(symbolDrawPlan)", HUD_MARKERS_SRC)

    def test_the_frame_is_drawn_as_3d_lines(self):
        self.assertIn("drawLine3D", HUD_MARKERS_SRC)

    def test_the_frame_is_gated_on_the_symbology_setting(self):
        self.assertIn("symbologyEnabled", HUD_MARKERS_SRC)


class TestSymbolPostInit(unittest.TestCase):
    """The map and world workers are wired from postInit."""

    def test_the_map_worker_is_wired(self):
        self.assertIn("[] call FUNC(symbologyMapDraw)", POSTINIT_SRC)

    def test_the_world_worker_is_wired(self):
        self.assertIn("[] call FUNC(symbologyWorldDraw)", POSTINIT_SRC)


class TestSymbolPrep(unittest.TestCase):
    """Every symbology kernel is registered for CBA_fnc_prep."""

    def test_the_palette_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolPalette)", PREP_SRC)

    def test_the_frame_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolFrame)", PREP_SRC)

    def test_the_icon_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolIcon)", PREP_SRC)

    def test_the_resolve_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolResolve)", PREP_SRC)

    def test_the_draw_plan_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolDrawPlan)", PREP_SRC)

    def test_the_category_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolCategory)", PREP_SRC)

    def test_the_adapter_prep_entries_exist(self):
        for name in (
            "symbologyMarkerCategory",
            "symbologyUnitCategory",
            "symbologyAffiliation",
            "symbologyPaletteFriendly",
        ):
            self.assertIn(f"PREPS(symbology,{name})", PREP_SRC)


class TestSymbologyFontWiring(unittest.TestCase):
    """The AEE font is wired into the config and the draw layer."""

    def test_the_font_families_are_declared(self):
        self.assertIn("class CfgFontFamilies {", CONFIG_SRC)
        self.assertIn("class AEEFont {", CONFIG_SRC)
        self.assertIn("class AEEFontMono {", CONFIG_SRC)

    def test_the_families_carry_a_fonts_list_and_a_space_width(self):
        self.assertIn("fonts[] = {", CONFIG_SRC)
        self.assertIn("spaceWidth = 0.9;", CONFIG_SRC)
        self.assertIn("spaceWidth = 0.5;", CONFIG_SRC)

    def test_the_map_grid_font_is_repointed_at_load_time(self):
        self.assertIn("class RscMapControl {", CONFIG_SRC)
        self.assertIn('fontGrid = "AEEFont";', CONFIG_SRC)

    def test_the_referenced_paths_carry_no_extension(self):
        # A fonts[] entry names a path with no extension; the engine appends
        # the .fxy and the .paa.
        self.assertIn(
            "z\\aee\\addons\\optics\\data\\fonts\\rajdhani\\AEEFont9", CONFIG_SRC
        )
        self.assertIn(
            "z\\aee\\addons\\optics\\data\\fonts\\b612mono\\AEEFontMono9", CONFIG_SRC
        )
        for line in CONFIG_SRC.splitlines():
            stripped = line.strip()
            if stripped.startswith('"z\\aee\\addons\\optics\\data\\fonts\\'):
                self.assertFalse(stripped.endswith('.fxy",'))
                self.assertFalse(stripped.endswith('.paa",'))

    def test_the_draw_functions_gate_the_font_on_the_setting(self):
        self.assertIn("QGVAR(symbologyFont)", SYM_MAP_SRC)
        self.assertIn("QGVAR(symbologyFont)", SYM_WORLD_SRC)

    def test_the_mgrs_readout_uses_the_monospaced_family(self):
        self.assertIn("AEEFontMono", MGRS_MAP_SRC)
        self.assertIn("QGVAR(symbologyFont)", MGRS_MAP_SRC)

    def test_the_hud_controls_name_the_aee_families(self):
        self.assertIn('font = "AEEFont";', RSCTITLES_SRC)
        self.assertIn('font = "AEEFontMono";', RSCTITLES_SRC)

    def test_the_ofl_text_and_the_ttf_are_committed_for_each_family(self):
        for family in ("rajdhani", "b612mono"):
            with self.subTest(family=family):
                self.assertTrue((FONTS / family / "OFL.txt").is_file())
        self.assertTrue((FONTS / "rajdhani" / "Rajdhani-Regular.ttf").is_file())
        self.assertTrue((FONTS / "rajdhani" / "Rajdhani-Bold.ttf").is_file())
        self.assertTrue((FONTS / "b612mono" / "B612Mono-Regular.ttf").is_file())

    def test_every_ofl_file_carries_the_licence(self):
        for family in ("rajdhani", "b612mono"):
            with self.subTest(family=family):
                text = (FONTS / family / "OFL.txt").read_text(encoding="utf-8")
                self.assertIn("SIL OPEN FONT LICENSE Version 1.1", text)


if __name__ == "__main__":
    unittest.main()
