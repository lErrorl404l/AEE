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
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")


def palette(affiliation, pal):
    return run_sqf(PALETTE_KERNEL, [affiliation, pal], {})


def frame(affiliation, dimension):
    return run_sqf(FRAME_KERNEL, [affiliation, dimension], {})


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


class TestSymbolPrep(unittest.TestCase):
    """Every symbology kernel is registered for CBA_fnc_prep."""

    def test_the_palette_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolPalette)", PREP_SRC)

    def test_the_frame_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolFrame)", PREP_SRC)


if __name__ == "__main__":
    unittest.main()
