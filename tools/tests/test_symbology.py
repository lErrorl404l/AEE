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
CATEGORY_KERNEL = SYM / "fnc_symbolCategory.sqf"
TABLES_SQF = OPTICS / "data" / "symbology_tables.sqf"
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")
SYM_TABLES = run_sqf(TABLES_SQF, [])


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


def category(value, kind="marker"):
    """Run the real category kernel against the real generated table."""
    return run_sqf(
        CATEGORY_KERNEL, [value, kind], {"aee_optics_symbologyTables": SYM_TABLES}
    )


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

    def test_the_category_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolCategory)", PREP_SRC)


if __name__ == "__main__":
    unittest.main()
