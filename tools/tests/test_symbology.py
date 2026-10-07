#!/usr/bin/env python3
"""AEE NATO/OPFOR map symbology kernel tests.

Executes the REAL pure kernels through tools/tests/sqf_lite.py:

  addons/optics/functions/symbology/fnc_symbolPalette.sqf

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
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")


def palette(affiliation, pal):
    return run_sqf(PALETTE_KERNEL, [affiliation, pal], {})


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


class TestSymbolPrep(unittest.TestCase):
    """Every symbology kernel is registered for CBA_fnc_prep."""

    def test_the_palette_prep_entry_exists(self):
        self.assertIn("PREPS(symbology,symbolPalette)", PREP_SRC)


if __name__ == "__main__":
    unittest.main()
