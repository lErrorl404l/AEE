#!/usr/bin/env python3
"""AEE NATO/OPFOR map symbology kernel tests.

Executes the REAL pure kernels through tools/tests/sqf_lite.py and pins the
real CfgMarkers registration in addons/optics/config.cpp:

  addons/optics/functions/symbology/fnc_symbolPalette.sqf
  addons/optics/functions/symbology/fnc_symbolFrame.sqf
  addons/optics/functions/symbology/fnc_symbolIcon.sqf
  addons/optics/functions/symbology/fnc_symbolResolve.sqf
  addons/optics/functions/symbology/fnc_symbologyMarkerType.sqf
  addons/optics/functions/symbology/fnc_symbologyMarkerColor.sqf

The symbols are real engine map markers, so the map layer applies them with
the local marker commands and draws nothing on the map control.

Run: python3 -m unittest tools.tests.test_symbology -v
"""

from __future__ import annotations

import re
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
MARKER_TYPE_KERNEL = SYM / "fnc_symbologyMarkerType.sqf"
MARKER_COLOR_KERNEL = SYM / "fnc_symbologyMarkerColor.sqf"
CATEGORY_KERNEL = SYM / "fnc_symbolCategory.sqf"
MARKER_CAT_KERNEL = SYM / "fnc_symbologyMarkerCategory.sqf"
UNIT_CAT_KERNEL = SYM / "fnc_symbologyUnitCategory.sqf"
AFFILIATION_KERNEL = SYM / "fnc_symbologyAffiliation.sqf"
PALETTE_FRIENDLY_KERNEL = SYM / "fnc_symbologyPaletteFriendly.sqf"
TABLES_SQF = OPTICS / "data" / "symbology_tables.sqf"
MARKERS = OPTICS / "data" / "markers"
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")
SYM_TABLES = run_sqf(TABLES_SQF, [])
FAMILIES = SYM_TABLES[4]
GLYPHS = SYM_TABLES[5]
MARKER_CAT_SRC = MARKER_CAT_KERNEL.read_text(encoding="utf-8")
UNIT_CAT_SRC = UNIT_CAT_KERNEL.read_text(encoding="utf-8")
AFFILIATION_SRC = AFFILIATION_KERNEL.read_text(encoding="utf-8")
SYM_MARKERS_KERNEL = SYM / "fnc_symbologyMarkers.sqf"
SYM_MARKERS_SRC = SYM_MARKERS_KERNEL.read_text(encoding="utf-8")
SYM_APPLY_SRC = (SYM / "fnc_symbologyMarkersApply.sqf").read_text(encoding="utf-8")
SYM_RESTORE_SRC = (SYM / "fnc_symbologyMarkersRestore.sqf").read_text(encoding="utf-8")
SYM_WORLD_KERNEL = SYM / "fnc_symbologyWorldDraw.sqf"
SYM_WORLD_SRC = SYM_WORLD_KERNEL.read_text(encoding="utf-8")
HUD_MARKERS_SRC = (OPTICS / "functions" / "hud" / "fnc_hudMarkers.sqf").read_text(
    encoding="utf-8"
)
POSTINIT_SRC = (OPTICS / "XEH_postInit.sqf").read_text(encoding="utf-8")
CONFIG_SRC = (OPTICS / "config.cpp").read_text(encoding="utf-8")
FAMILY_SRC = (OPTICS / "config_family.hpp").read_text(encoding="utf-8")
MARKERS_SRC = (OPTICS / "config_markers.hpp").read_text(encoding="utf-8")
RSCTITLES_SRC = (OPTICS / "RscTitles.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (OPTICS / "initSettings.inc.sqf").read_text(encoding="utf-8")
STRINGTABLE_SRC = (OPTICS / "stringtable.xml").read_text(encoding="utf-8")
MGRS_MAP_SRC = (OPTICS / "functions" / "hud" / "fnc_mgrsMapDraw.sqf").read_text(
    encoding="utf-8"
)
MGRS_FONT_SRC = (OPTICS / "functions" / "hud" / "fnc_mgrsFontFamily.sqf").read_text(
    encoding="utf-8"
)
FONTS = OPTICS / "data" / "fonts"

# Every committed symbology source, for the provenance guard.
ALL_SYM_SRC = "\n".join(
    [
        PALETTE_KERNEL.read_text(encoding="utf-8"),
        FRAME_KERNEL.read_text(encoding="utf-8"),
        ICON_KERNEL.read_text(encoding="utf-8"),
        RESOLVE_KERNEL.read_text(encoding="utf-8"),
        MARKER_TYPE_KERNEL.read_text(encoding="utf-8"),
        MARKER_COLOR_KERNEL.read_text(encoding="utf-8"),
        CATEGORY_KERNEL.read_text(encoding="utf-8"),
        MARKER_CAT_SRC,
        UNIT_CAT_SRC,
        AFFILIATION_SRC,
        PALETTE_FRIENDLY_KERNEL.read_text(encoding="utf-8"),
        SYM_MARKERS_SRC,
        SYM_APPLY_SRC,
        SYM_RESTORE_SRC,
        SYM_WORLD_SRC,
        TABLES_SQF.read_text(encoding="utf-8"),
        HUD_MARKERS_SRC,
        POSTINIT_SRC,
        CONFIG_SRC,
        RSCTITLES_SRC,
        MGRS_MAP_SRC,
        SETTINGS_SRC,
        STRINGTABLE_SRC,
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

# The six symbology settings and their group, default and subcategory.
SYMBOLOGY_SETTINGS = (
    ("symbologyEnabled", "AEE HUD", "Symbology", "false"),
    ("symbologyPalette", "AEE HUD", "Symbology", None),
    ("symbologyUnits", "AEE HUD", "Symbology", "true"),
    ("symbologyMarkers", "AEE HUD", "Symbology", "true"),
    ("symbologySuppress", "AEE HUD", "Symbology", "true"),
    ("symbologyFont", "AEE HUD", "Symbology", "true"),
)

# The engine's own NATO glyphs per b_ / o_ / n_ family, from the shipped
# config (Addons/ui_f.pbo config.cpp).  The produced AEE textures are the rest.
VANILLA_GLYPHS = frozenset(
    {
        "unknown",
        "inf",
        "motor_inf",
        "mech_inf",
        "armor",
        "recon",
        "air",
        "plane",
        "uav",
        "naval",
        "med",
        "art",
        "mortar",
        "hq",
        "support",
        "maint",
        "service",
        "installation",
        "antiair",
    }
)


def palette(affiliation, pal):
    return run_sqf(PALETTE_KERNEL, [affiliation, pal], {})


def frame(affiliation, dimension):
    return run_sqf(FRAME_KERNEL, [affiliation, dimension], {})


def icon(icon_id):
    return run_sqf(ICON_KERNEL, [icon_id], {})


def marker_type(affiliation, category, dimension="land", echelon="unknown", pal="NATO"):
    """Run the real marker-type kernel against the real generated table."""
    return run_sqf(
        MARKER_TYPE_KERNEL,
        [affiliation, category, dimension, echelon, pal],
        {"aee_optics_symbologyTables": SYM_TABLES},
    )


def marker_color(affiliation, pal):
    return run_sqf(MARKER_COLOR_KERNEL, [affiliation, pal], {})


def resolve(side, category, affiliation, echelon, pal):
    """Run the real resolver with the real marker kernels injected."""
    globals_ = {
        "__FUNC__symbologyMarkerType": lambda aff, cat, dim, ech, p: run_sqf(
            MARKER_TYPE_KERNEL,
            [aff, cat, dim, ech, p],
            {"aee_optics_symbologyTables": SYM_TABLES},
        ),
        "__FUNC__symbologyMarkerColor": lambda aff, p: run_sqf(
            MARKER_COLOR_KERNEL, [aff, p], {}
        ),
    }
    return run_sqf(
        RESOLVE_KERNEL, [side, category, affiliation, echelon, pal], globals_
    )


def category(value, kind="marker"):
    """Run the real category kernel against the real generated table."""
    return run_sqf(
        CATEGORY_KERNEL, [value, kind], {"aee_optics_symbologyTables": SYM_TABLES}
    )


def marker_category(marker_type_name):
    """Run the real marker adapter with the real category kernel injected."""
    globals_ = {
        "__FUNC__symbolCategory": lambda value, kind: run_sqf(
            CATEGORY_KERNEL, [value, kind], {"aee_optics_symbologyTables": SYM_TABLES}
        ),
    }
    return run_sqf(MARKER_CAT_KERNEL, ["", marker_type_name], globals_)


def affiliation(colour, friendly):
    return run_sqf(AFFILIATION_KERNEL, ["", colour, friendly], {})


def palette_friendly(pal, local_side):
    return run_sqf(PALETTE_FRIENDLY_KERNEL, [pal, local_side], {})


class TestSymbolPalette(unittest.TestCase):
    """fnc_symbolPalette, executed: the draw tint is neutral.

    Every AEE texture carries its own colour, so the tint must leave it
    untouched.  The affiliation and the palette are carried but do not change
    the tint; the affiliation colour is applied through the marker type.
    """

    def test_the_tint_is_neutral_for_every_affiliation(self):
        for affiliation_name in ("friend", "hostile", "neutral", "unknown"):
            with self.subTest(affiliation=affiliation_name):
                self.assertEqual(palette(affiliation_name, "NATO"), [1, 1, 1, 1])

    def test_the_palette_does_not_change_the_tint(self):
        for pal in ("NATO", "OPFOR", "Auto", "bogus"):
            with self.subTest(palette=pal):
                self.assertEqual(palette("hostile", pal), [1, 1, 1, 1])


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
        for affiliation_name in ("friend", "hostile", "neutral", "unknown"):
            for dimension in ("land", "air", "subsurface"):
                with self.subTest(affiliation=affiliation_name, dimension=dimension):
                    for polyline in frame(affiliation_name, dimension):
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
        rising = [prim for prim in out if prim[1][1][1] > prim[1][0][1]]
        falling = [prim for prim in out if prim[1][1][1] < prim[1][0][1]]
        self.assertEqual(len(rising), 1)
        self.assertEqual(len(falling), 1)

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


class TestSymbolMarkerType(unittest.TestCase):
    """fnc_symbologyMarkerType, executed: affiliation + category -> type."""

    def test_the_family_follows_the_affiliation(self):
        self.assertEqual(marker_type("friend", "infantry"), "AEE_b_inf")
        self.assertEqual(marker_type("hostile", "armour"), "AEE_o_armor")
        self.assertEqual(marker_type("neutral", "rotary"), "AEE_n_air")
        self.assertEqual(marker_type("unknown", "medical"), "AEE_u_med")

    def test_an_unknown_category_is_the_unknown_glyph(self):
        self.assertEqual(marker_type("friend", "bogus"), "AEE_b_unknown")

    def test_every_category_has_a_glyph_token(self):
        for category_name, glyph, _grade, _source in GLYPHS:
            with self.subTest(category=category_name):
                self.assertEqual(marker_type("friend", category_name), f"AEE_b_{glyph}")

    def test_the_type_names_a_registered_marker_class(self):
        for _affiliation_name, family, _grade, _source in FAMILIES:
            for category_name, glyph, _grade2, _source2 in GLYPHS:
                with self.subTest(family=family, category=category_name):
                    self.assertIn(
                        f"class AEE_{family}_{glyph}:", FAMILY_SRC
                    )


class TestSymbolMarkerColor(unittest.TestCase):
    """fnc_symbologyMarkerColor, executed: the class is neutral.

    Every AEE texture carries its own colour, so the CfgMarkerColors class is
    ColorAEE (white), which leaves the texture untouched.  The affiliation
    colour is carried by the texture, selected by the marker type.
    """

    def test_the_class_is_neutral_for_every_affiliation(self):
        for affiliation_name in ("friend", "hostile", "neutral", "unknown"):
            with self.subTest(affiliation=affiliation_name):
                self.assertEqual(marker_color(affiliation_name, "NATO"), "ColorAEE")

    def test_the_palette_does_not_change_the_class(self):
        for pal in ("NATO", "OPFOR", "Auto", "bogus"):
            with self.subTest(palette=pal):
                self.assertEqual(marker_color("friend", pal), "ColorAEE")

    def test_the_param_type_sample_is_a_string(self):
        # The rest of the tree uses [""] as the string sample, not ["Auto"].
        src = MARKER_COLOR_KERNEL.read_text(encoding="utf-8")
        self.assertIn('["_palette", "NATO", [""]]', src)
        self.assertNotIn('["Auto"]', src)


class TestSymbolResolve(unittest.TestCase):
    """fnc_symbolResolve, executed: inputs -> marker type and colour."""

    def test_a_hostile_armour_symbol_is_the_hostile_texture(self):
        spec = resolve("east", "armour", "hostile", "squad", "NATO")
        self.assertEqual(spec[0], "hostile")
        self.assertEqual(spec[1], "AEE_o_armor")
        self.assertEqual(spec[2], "ColorAEE")
        self.assertEqual(spec[3], "squad")

    def test_a_friendly_infantry_symbol_is_the_friendly_texture(self):
        spec = resolve("west", "infantry", "friend", "company", "NATO")
        self.assertEqual(spec[1], "AEE_b_inf")
        self.assertEqual(spec[2], "ColorAEE")

    def test_the_palette_no_longer_flips_the_marker_colour(self):
        # The affiliation colour lives in the texture; the palette only picks
        # the friendly side, which the caller resolves before this call.
        spec = resolve("west", "infantry", "friend", "company", "OPFOR")
        self.assertEqual(spec[2], "ColorAEE")

    def test_neutral_and_unknown_carry_the_neutral_class(self):
        self.assertEqual(
            resolve("", "infantry", "neutral", "team", "NATO")[2], "ColorAEE"
        )
        self.assertEqual(
            resolve("", "infantry", "unknown", "team", "NATO")[2], "ColorAEE"
        )

    def test_an_unknown_category_falls_back_to_the_unknown_glyph(self):
        spec = resolve("", "bogus", "friend", "squad", "NATO")
        self.assertEqual(spec[1], "AEE_b_unknown")


class TestSymbolCategory(unittest.TestCase):
    """fnc_symbolCategory, executed: engine name -> class category."""

    def test_the_shipped_marker_types_map(self):
        for marker_type_name, expected in (
            ("b_inf", "infantry"),
            ("o_armor", "armour"),
            ("n_inf", "infantry"),
            ("c_air", "rotary"),
            ("hd_dot", "waypoint"),
            ("group_3", "unknown"),
            ("flag_NATO", "unknown"),
            ("GroundSupport_CAS_WEST", "support"),
        ):
            with self.subTest(marker_type=marker_type_name):
                self.assertEqual(category(marker_type_name), expected)

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
        for marker_type_name, expected in (
            ("b_inf", "infantry"),
            ("o_armor", "armour"),
            ("n_inf", "infantry"),
            ("hd_dot", "waypoint"),
        ):
            with self.subTest(marker_type=marker_type_name):
                self.assertEqual(marker_category(marker_type_name), expected)

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


class TestSymbologyMarkerConfig(unittest.TestCase):
    """The real CfgMarkers registration, pinned against the table."""

    def test_the_marker_class_group_is_declared(self):
        self.assertIn("class CfgMarkerClasses {", CONFIG_SRC)
        self.assertIn("class AEE_Friend_Land {", CONFIG_SRC)
        self.assertIn('displayName = "AEE Friend - Land";', CONFIG_SRC)

    def test_the_base_class_is_not_a_usable_icon(self):
        self.assertIn("class AEE_MarkerBase {", CONFIG_SRC)
        self.assertIn("scope = 0;", CONFIG_SRC)
        self.assertIn('markerClass = "AEE_Unknown_Other";', CONFIG_SRC)

    def test_every_family_glyph_pair_is_registered_selectable(self):
        for _affiliation_name, family, _grade, _source in FAMILIES:
            for category_name, glyph, _grade2, _source2 in GLYPHS:
                with self.subTest(family=family, category=category_name):
                    self.assertIn(
                        f"class AEE_{family}_{glyph}:", FAMILY_SRC
                    )
        pairs = len(FAMILIES) * len(GLYPHS)
        self.assertEqual(FAMILY_SRC.count("class AEE_"), pairs)

    def test_every_marker_carries_the_size_shadow_and_side(self):
        self.assertIn("size = 32;", CONFIG_SRC)
        self.assertIn("shadow = 0;", CONFIG_SRC)
        self.assertIn("color[] = {1, 1, 1, 1};", CONFIG_SRC)

    def test_the_marker_tint_is_neutral(self):
        # Every AEE texture carries its own colours, so the engine tint is
        # white.  ColorAEE is the neutral class the kernels select.
        self.assertIn("class ColorAEE { color[] = {1, 1, 1, 1}; };", CONFIG_SRC)
        for side in ("side = 0;", "side = 1;", "side = 2;"):
            self.assertIn(side, FAMILY_SRC)

    def test_no_marker_points_at_an_engine_texture(self):
        # Every AEE marker texture is a real .paa under data/markers.  A
        # pointer at an engine texture loses the symbol the engine ships.
        for source in (CONFIG_SRC, FAMILY_SRC, MARKERS_SRC):
            self.assertNotIn("\\A3\\ui_f\\data\\map\\markers", source)

    def test_the_produced_textures_reference_the_aee_data_dir(self):
        # The five glyphs the catalogue does not publish inherit AEE_MarkerBase
        # and point at the AEE-produced texture under data/markers.
        for family in ("b", "o", "n", "u"):
            for _category_name, glyph, _grade, _source in GLYPHS:
                if glyph not in ("eng", "sig", "sup", "sub", "dot"):
                    continue
                with self.subTest(family=family, glyph=glyph):
                    self.assertIn(
                        f'icon = "\\z\\aee\\addons\\optics\\data\\markers\\'
                        f'AEE_{family}_{glyph}.paa";',
                        FAMILY_SRC,
                    )

    def test_every_referenced_produced_texture_exists(self):
        produced = [
            line
            for source in (MARKERS_SRC, FAMILY_SRC)
            for line in source.splitlines()
            if line.strip().startswith("icon = ")
            and "\\z\\aee\\addons\\optics\\data\\markers\\" in line
        ]
        self.assertTrue(produced)
        for line in produced:
            path = line.split('"')[1]
            parts = path.lstrip("\\").split("\\")
            self.assertTrue((REPO.joinpath(*parts[2:])).is_file(), path)


class TestSymbologyMarkersContract(unittest.TestCase):
    """The map layer applies real markers and draws nothing on the control."""

    def test_the_map_event_is_hooked(self):
        self.assertIn('addMissionEventHandler ["Map"', SYM_MARKERS_SRC)

    def test_the_engine_indicators_are_suppressed_where_allowed(self):
        self.assertIn("disableMapIndicators [true, true, true, true]", SYM_APPLY_SRC)

    def test_the_engine_indicators_are_restored_on_close(self):
        # disableMapIndicators is a persistent LOCAL effect, not scoped to the
        # map display, so the map close must reverse it or the engine
        # indicators stay hidden for the rest of the session.
        self.assertIn(
            "disableMapIndicators [false, false, false, false]", SYM_RESTORE_SRC
        )

    def test_the_mission_markers_are_converted_locally(self):
        self.assertIn("allMapMarkers", SYM_APPLY_SRC)
        self.assertIn("setMarkerTypeLocal", SYM_APPLY_SRC)
        self.assertIn("setMarkerColorLocal", SYM_APPLY_SRC)

    def test_the_original_type_and_colour_are_recorded_and_restored(self):
        self.assertIn("markerType _name", SYM_APPLY_SRC)
        self.assertIn("markerColor _name", SYM_APPLY_SRC)
        self.assertIn("setMarkerTypeLocal _type", SYM_RESTORE_SRC)
        self.assertIn("setMarkerColorLocal _colour", SYM_RESTORE_SRC)

    def test_the_unit_markers_are_created_and_deleted_locally(self):
        self.assertIn("createMarkerLocal", SYM_APPLY_SRC)
        self.assertIn("setMarkerPosLocal", SYM_APPLY_SRC)
        self.assertIn("deleteMarkerLocal", SYM_APPLY_SRC)
        self.assertIn("deleteMarkerLocal", SYM_RESTORE_SRC)

    def test_no_global_marker_command_is_called(self):
        for forbidden in (
            " setMarkerType ",
            " setMarkerColor ",
            " setMarkerText ",
            " setMarkerPos ",
            " setMarkerAlpha ",
            " deleteMarker ",
            " setMarkerType(",
            " setMarkerColor(",
        ):
            self.assertNotIn(forbidden, SYM_APPLY_SRC, forbidden)
            self.assertNotIn(forbidden, SYM_RESTORE_SRC, forbidden)

    def test_there_is_no_symbol_draw_handler(self):
        # The symbols are real markers, so nothing is painted on the control.
        for forbidden in ('ctrlAddEventHandler ["Draw"', "drawPolygon", "drawLine"):
            self.assertNotIn(forbidden, SYM_MARKERS_SRC, forbidden)
            self.assertNotIn(forbidden, SYM_APPLY_SRC, forbidden)

    def test_the_rescan_is_a_one_second_per_frame_handler(self):
        self.assertIn("CBA_fnc_addPerFrameHandler", SYM_MARKERS_SRC)
        self.assertIn("CBA_fnc_removePerFrameHandler", SYM_MARKERS_SRC)

    def test_the_symbols_are_built_from_the_resolver(self):
        for adapter in (
            "FUNC(symbologyMarkerCategory)",
            "FUNC(symbologyAffiliation)",
            "FUNC(symbolResolve)",
            "FUNC(symbologyUnitCategory)",
        ):
            self.assertIn(adapter, SYM_APPLY_SRC, adapter)


class TestSymbologyWorldDrawContract(unittest.TestCase):
    """fnc_symbologyWorldDraw draws the real texture and gates the range."""

    def test_the_worker_is_a_draw3d_handler(self):
        self.assertIn('addMissionEventHandler ["Draw3D"', SYM_WORLD_SRC)

    def test_the_real_marker_texture_is_drawn(self):
        self.assertIn("drawIcon3D", SYM_WORLD_SRC)
        self.assertIn('configFile >> "CfgMarkers"', SYM_WORLD_SRC)
        self.assertIn(">> _markerType >>", SYM_WORLD_SRC)

    def test_the_worker_no_longer_draws_vector_lines(self):
        self.assertNotIn("drawLine3D", SYM_WORLD_SRC)
        self.assertNotIn("FUNC(symbolDrawPlan)", SYM_WORLD_SRC)

    def test_the_label_carries_the_font_parameter(self):
        self.assertIn('_font, "center"', SYM_WORLD_SRC)

    def test_the_symbols_are_drawn_out_to_a_set_range(self):
        self.assertIn("#define SYMBOLOGY_WORLD_RANGE", SYM_WORLD_SRC)
        self.assertIn("<= SYMBOLOGY_WORLD_RANGE", SYM_WORLD_SRC)

    def test_the_unit_list_is_rebuilt_at_most_once_a_second(self):
        self.assertIn("symbologyWorldTime", SYM_WORLD_SRC)
        self.assertIn("(_now - _last) > 1", SYM_WORLD_SRC)
        self.assertIn("allUnits", SYM_WORLD_SRC)

    def test_the_worker_states_the_engine_icons_cannot_be_suppressed(self):
        self.assertIn("cannot be suppressed", SYM_WORLD_SRC)

    def test_the_worker_calls_the_resolver(self):
        self.assertIn("FUNC(symbolResolve)", SYM_WORLD_SRC)

    def test_the_palette_is_resolved_before_the_resolver(self):
        # "Auto" must resolve to NATO/OPFOR before the resolver calls, as the
        # map layer does, so the 3D layer and the map layer pass the same
        # palette.
        self.assertIn("_resolvedPalette", SYM_WORLD_SRC)
        self.assertIn(
            '["NATO", "OPFOR"] select (_friendly isEqualTo "EAST")', SYM_WORLD_SRC
        )
        self.assertIn("_resolvedPalette, _playerDimension", SYM_WORLD_SRC)
        self.assertIn("_resolvedPalette, _dimension", SYM_WORLD_SRC)
        self.assertIn("_spec select 0, _resolvedPalette", SYM_WORLD_SRC)


class TestHudMarkersFrameContract(unittest.TestCase):
    """fnc_hudMarkers draws the real marker texture in front of its label."""

    def test_the_texture_is_read_from_the_marker_type(self):
        self.assertIn("FUNC(symbolResolve)", HUD_MARKERS_SRC)
        self.assertIn('configFile >> "CfgMarkers"', HUD_MARKERS_SRC)
        self.assertIn("drawIcon3D", HUD_MARKERS_SRC)

    def test_the_frame_no_longer_draws_vector_lines(self):
        self.assertNotIn("drawLine3D", HUD_MARKERS_SRC)
        self.assertNotIn("FUNC(symbolDrawPlan)", HUD_MARKERS_SRC)

    def test_the_texture_is_gated_on_the_symbology_setting(self):
        self.assertIn("symbologyEnabled", HUD_MARKERS_SRC)

    def test_the_affiliation_is_computed_against_the_palette_side(self):
        # Without the friendly side the third argument defaults to WEST, so
        # an EAST player read every marker against WEST.
        self.assertIn("call FUNC(symbologyPaletteFriendly)", HUD_MARKERS_SRC)
        self.assertIn(
            '[_name, "", _friendly] call FUNC(symbologyAffiliation)', HUD_MARKERS_SRC
        )
        self.assertIn("_resolvedPalette", HUD_MARKERS_SRC)


class TestSymbolPostInit(unittest.TestCase):
    """The map and world workers are wired from postInit."""

    def test_the_map_worker_is_wired(self):
        self.assertIn("[] call FUNC(symbologyMarkers)", POSTINIT_SRC)

    def test_the_world_worker_is_wired(self):
        self.assertIn("[] call FUNC(symbologyWorldDraw)", POSTINIT_SRC)


class TestSymbologyIndicatorTeardown(unittest.TestCase):
    """The optics Ended teardown reverses the indicator suppression too."""

    def test_the_ended_handler_calls_the_restore(self):
        preinit = (OPTICS / "XEH_preInit.sqf").read_text(encoding="utf-8")
        self.assertIn('addMissionEventHandler ["Ended"', preinit)
        self.assertIn("[] call FUNC(symbologyMarkersRestore)", preinit)
        self.assertIn("hasInterface", preinit)


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

    def test_the_marker_type_and_colour_prep_entries_exist(self):
        self.assertIn("PREPS(symbology,symbologyMarkerType)", PREP_SRC)
        self.assertIn("PREPS(symbology,symbologyMarkerColor)", PREP_SRC)

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

    def test_the_marker_layer_prep_entries_exist(self):
        for name in (
            "symbologyMarkers",
            "symbologyMarkersApply",
            "symbologyMarkersRestore",
            "symbologyWorldDraw",
        ):
            self.assertIn(f"PREPS(symbology,{name})", PREP_SRC)

    def test_the_removed_kernels_have_no_prep_entry(self):
        self.assertNotIn("PREPS(symbology,symbolDrawPlan)", PREP_SRC)
        self.assertNotIn("PREPS(symbology,symbologyMapDraw)", PREP_SRC)


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

    def test_the_map_grid_font_is_left_to_the_engine_until_the_glyphs_ship(self):
        # The AEE fonts need the FontToTGA operator step.  Until the glyph
        # files exist the engine draws no text, so the config must not point
        # an engine surface at them.
        self.assertIn("class RscMapControl {", CONFIG_SRC)
        self.assertNotIn('fontGrid = "AEEFont";', CONFIG_SRC)
        self.assertNotIn('fontNames = "AEEFont";', CONFIG_SRC)

    def test_the_referenced_paths_carry_no_extension(self):
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

    def test_the_world_draw_gates_the_font_on_the_setting(self):
        self.assertIn("QGVAR(symbologyFont)", SYM_WORLD_SRC)

    def test_the_mgrs_readout_uses_the_monospaced_family(self):
        self.assertIn("FUNC(mgrsFontFamily)", MGRS_MAP_SRC)
        self.assertIn("QGVAR(symbologyFont)", MGRS_MAP_SRC)
        self.assertIn("AEEFontMono", MGRS_FONT_SRC)

    def test_the_hud_controls_use_the_engine_families_until_the_glyphs_ship(self):
        # Same ceiling: no text renders in a family whose glyph files are
        # absent, so the HUD controls use engine families for now.
        self.assertNotIn('font = "AEEFont";', RSCTITLES_SRC)
        self.assertNotIn('font = "AEEFontMono";', RSCTITLES_SRC)
        self.assertIn('font = "RobotoCondensed";', RSCTITLES_SRC)

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


class TestSymbologySettingsContract(unittest.TestCase):
    """The six symbology settings and their stringtable keys exist."""

    def test_every_setting_is_registered_in_the_symbology_group(self):
        for name, category_name, subcategory, _default in SYMBOLOGY_SETTINGS:
            with self.subTest(setting=name):
                self.assertIn(f'"{category_name}", "{subcategory}"', SETTINGS_SRC, name)

    def test_every_checkbox_carries_its_default(self):
        for name, _category, _subcategory, default in SYMBOLOGY_SETTINGS:
            if default is None:
                continue
            with self.subTest(setting=name):
                self.assertIn(
                    f'AEE_SETTING_CHECKBOX({name},"AEE HUD","Symbology",{default})',
                    SETTINGS_SRC,
                    name,
                )

    def test_the_palette_setting_is_a_list_of_three(self):
        self.assertIn("QGVAR(symbologyPalette),", SETTINGS_SRC)
        self.assertIn('"LIST",', SETTINGS_SRC)
        self.assertIn('[["NATO", "OPFOR", "Auto"]', SETTINGS_SRC)

    def test_every_setting_has_a_stringtable_name_and_description(self):
        for name, _category, _subcategory, _default in SYMBOLOGY_SETTINGS:
            for suffix in ("_Name", "_Description"):
                with self.subTest(setting=name, suffix=suffix):
                    self.assertIn(f"STR_AEE_Optics_{name}{suffix}", STRINGTABLE_SRC)

    def test_the_stringtable_keys_are_sorted(self):
        keys = re.findall(r'<Key ID="(STR_AEE_Optics_\w+)"', STRINGTABLE_SRC)
        self.assertEqual(keys, sorted(keys), "stringtable keys are not sorted")
        symbology_keys = [key for key in keys if "symbology" in key.lower()]
        self.assertTrue(symbology_keys, "no symbology stringtable keys")
        self.assertEqual(symbology_keys, sorted(symbology_keys))


class TestSymbologyProvenanceGuard(unittest.TestCase):
    """No agent, model or tooling provenance is committed in the layer."""

    def test_no_provenance_leaked(self):
        for token in FORBIDDEN_PROVENANCE:
            self.assertNotIn(token, ALL_SYM_SRC, token)


class TestMarkerTexturesCarryColour(unittest.TestCase):
    """The marker textures keep their own colour; a white mask must fail.

    The defect was every texture flattened to a monochrome white mask, so the
    frame and the glyph were one colour.  These tests prove the catalogue
    rasteriser keeps the source colour and that a committed .paa is not a white
    mask.
    """

    # A six-digit hex colour in a source SVG.
    HEX = re.compile(r"#([0-9a-fA-F]{6})")

    def _coloured_source(self, affiliation):
        """A catalogue source for the affiliation whose SVG carries a hue."""
        import json

        catalogue = json.loads(
            (REPO / "data" / "symbology" / "nato_catalogue.json").read_text(
                encoding="utf-8"
            )
        )
        root = REPO / "data" / "symbology" / "sources" / "svg"
        for entry in catalogue["entries"]:
            if entry.get("affil") != affiliation:
                continue
            src = root / str(entry["dir"]) / str(entry["file"])
            if not src.is_file():
                continue
            text = src.read_text(encoding="utf-8", errors="replace")
            for token in self.HEX.findall(text):
                r, g, b = (int(token[i : i + 2], 16) for i in (0, 2, 4))
                if max(r, g, b) - min(r, g, b) > 40:
                    return src
        return None

    def test_the_catalogue_rasteriser_keeps_the_source_colour(self):
        sys.path.insert(0, str(REPO))
        from tools import gen_symbology_catalogue as gen

        for affiliation in ("Friend", "Hostile", "Neutral", "Unknown"):
            src = self._coloured_source(affiliation)
            if src is None:
                self.skipTest(f"no coloured {affiliation} source in the pull")
            with self.subTest(affiliation=affiliation):
                art = gen._rasterise(src).convert("RGBA")
                opaque = [px[:3] for px in art.getdata() if px[3] >= 128]
                self.assertTrue(opaque, "the render is empty")
                self.assertFalse(
                    all(min(px) >= 200 for px in opaque),
                    "the render is a monochrome white mask",
                )
                self.assertTrue(
                    any(max(px) - min(px) > 24 for px in opaque),
                    "the render lost its colour",
                )

    def test_a_committed_texture_is_not_a_white_mask(self):
        import json
        import shutil
        import subprocess
        import tempfile

        from PIL import Image

        hemtt = shutil.which("hemtt")
        if hemtt is None:
            self.skipTest("hemtt not on PATH")

        catalogue_config = (OPTICS / "config_markers.hpp").read_text(encoding="utf-8")
        names = re.findall(
            r"^\s*class (AEE_\w+): AEE_MarkerBase", catalogue_config, re.M
        )
        picked: dict[str, str] = {}
        for name in names:
            token = name.split("_")[1] if "_" in name else ""
            if token.startswith("X"):
                token = token[1:]
            if token and token[0] in "FHNU" and token[0] not in picked:
                picked[token[0]] = name
        self.assertEqual(sorted(picked), ["F", "H", "N", "U"], "affiliations missing")

        with tempfile.TemporaryDirectory() as tmp:
            for aff, name in picked.items():
                paa = MARKERS / f"{name}.paa"
                self.assertTrue(paa.is_file(), f"{name}.paa missing")
                out = Path(tmp) / f"{name}.png"
                result = subprocess.run(
                    [hemtt, "utils", "paa", "convert", str(paa), str(out)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, f"paa convert failed: {name}")
                image = Image.open(out).convert("RGBA")
                opaque = [px[:3] for px in image.getdata() if px[3] >= 128]
                self.assertTrue(opaque, f"{name}: no opaque pixels")
                self.assertFalse(
                    all(min(px) >= 200 for px in opaque),
                    f"{name}: monochrome white mask",
                )


if __name__ == "__main__":
    unittest.main()
