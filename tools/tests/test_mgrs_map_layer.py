#!/usr/bin/env python3
"""MGRS map-layer regression tests (2026-10-08).

Three live map defects, with the root cause and the test that proves each fix.

Defect 1  The grid numbers were missing.  AEE declares the CfgFontFamilies
          families AEEFont and AEEFontMono, but their .fxy and .paa glyph
          files do not ship (the FontToTGA operator step is not run).  The
          engine draws NO text for such a family, so the engine grid numbers
          (fontGrid) and every AEE overlay label (the drawIcon font) were
          blank.  Fix: the overlay picks the AEE family only when its glyph
          files exist, else an engine family; the config does not point an
          engine surface at the glyphless family.
Defect 2  The cursor still showed the engine grid number, because the AEE
          readout was drawn in the same blank font.  The engine tooltip
          (RscMapControlTooltip, idc 2350) is hidden and the AEE MGRS readout
          is drawn in its rectangle.  Fix: the readout font is usable.
Defect 3  The precision and the grid interval were hardcoded.  Fix: the
          displayed scale (visible span against the world size) picks the
          digit count and the finest interval; the operator can pin it.

RUNTIME tests execute the real SQF through tools/tests/sqf_lite.py.  CONTRACT
tests pin the source shape where the harness cannot reach the engine.  Both
fail on the defective source and pass on the fixed source.

Run: python3 -m unittest tools.tests.test_mgrs_map_layer -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OPTICS = ROOT / "addons" / "optics"
HUD = OPTICS / "functions" / "hud"
GEO = ROOT / "addons" / "core" / "functions" / "geo"

MGRS_MAP_SRC = (HUD / "fnc_mgrsMapDraw.sqf").read_text(encoding="utf-8")
GRID_SRC = (HUD / "fnc_mgrsGridLines.sqf").read_text(encoding="utf-8")
FONT_FAMILY_SRC = (HUD / "fnc_mgrsFontFamily.sqf").read_text(encoding="utf-8")
FONT_USABLE_SRC = (HUD / "fnc_fontFamilyUsable.sqf").read_text(encoding="utf-8")
PRECISION_SRC = (HUD / "fnc_mgrsMapPrecision.sqf").read_text(encoding="utf-8")
CONFIG_SRC = (OPTICS / "config.cpp").read_text(encoding="utf-8")
DISP_SRC = (OPTICS / "config_mapdisplays.hpp").read_text(encoding="utf-8")
LOC_SRC = (OPTICS / "config_locationtypes.hpp").read_text(encoding="utf-8")
RSCTITLES_SRC = (OPTICS / "RscTitles.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (OPTICS / "initSettings.inc.sqf").read_text(encoding="utf-8")
STRINGTABLE_SRC = (OPTICS / "stringtable.xml").read_text(encoding="utf-8")
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")

TABLES = run_sqf(ROOT / "addons" / "core" / "data" / "mgrs_tables.sqf", [])

ALTIS = [
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


def _latlon(lat, lon):
    return run_sqf(GEO / "fnc_latLonToUtm.sqf", [lat, lon])


def _utmlatlon(e, n, z, h):
    return run_sqf(GEO / "fnc_utmToLatLon.sqf", [e, n, z, h])


def _format_mgrs(e, n, z, p, lat):
    return run_sqf(
        GEO / "fnc_formatMgrs.sqf", [e, n, z, p, lat], {"aee_core_mgrsTables": TABLES}
    )


def _world_to_mgrs(pos, anchor, prec):
    return run_sqf(
        GEO / "fnc_worldToMgrs.sqf",
        [pos, anchor, prec],
        {
            "__FUNC__latLonToUtm": _latlon,
            "__FUNC__formatMgrs": _format_mgrs,
            "aee_core_mgrsTables": TABLES,
        },
    )


def _utm_to_world(e, n, z, h, anchor):
    return run_sqf(
        GEO / "fnc_utmToWorld.sqf",
        [e, n, z, h, anchor],
        {"__FUNC__utmToLatLon": _utmlatlon},
    )


def grid(anchor, rect, base_interval=0):
    """Run the real grid planner with the real core conversion kernels."""
    return run_sqf(
        HUD / "fnc_mgrsGridLines.sqf",
        [anchor, rect, base_interval],
        {
            "__EFUNC__core_worldToMgrs": _world_to_mgrs,
            "__EFUNC__core_utmToWorld": _utm_to_world,
            "__EFUNC__core_formatMgrs": _format_mgrs,
            "aee_core_mgrsTables": TABLES,
        },
    )


def precision(map_size, span):
    return run_sqf(HUD / "fnc_mgrsMapPrecision.sqf", [map_size, span])


def font_family(mono, usable):
    return run_sqf(
        HUD / "fnc_mgrsFontFamily.sqf",
        [mono],
        {"__FUNC__fontFamilyUsable": lambda *_: usable},
    )


def font_usable(family, glyph_exists):
    return run_sqf(
        HUD / "fnc_fontFamilyUsable.sqf",
        [family],
        {
            "configFile": "config",
            "getArray": lambda path: [r"z\aee\addons\optics\data\fonts\x\AEEFont9"],
            "fileExists": lambda path: glyph_exists,
        },
    )


def cursor_text(ref, elev):
    return run_sqf(HUD / "fnc_mgrsCursorText.sqf", [ref, elev])


class TestDefect1GridLabels(unittest.TestCase):
    """The grid labels are produced with the MGRS digit group, and drawn."""

    def test_grid_labels_are_produced_with_the_mgrs_digit_group(self):
        # The visible 2 km square at the Altis centre.  The planner must
        # return labels, and each label text must be the digit group that
        # matches the chosen interval (NGA MGRS 2009: 6 digits = 100 m).
        half = 1000
        c = ALTIS[3] / 2
        rect = [c - half, c - half, c + half, c + half]
        segments, labels, interval = grid(ALTIS, rect)
        self.assertGreater(len(segments), 0, "no grid segments")
        self.assertGreater(len(labels), 0, "no grid labels")
        self.assertIn(interval, (10, 100, 1000, 10000, 100000))
        per_axis = round(5 - math.log10(interval))
        self.assertGreaterEqual(per_axis, 1)
        for pos, text, _major in labels:
            self.assertEqual(len(pos), 3, pos)
            self.assertTrue(text.isdigit(), f"label {text!r} is not digits")
            self.assertEqual(
                len(text), per_axis, f"label {text!r} must carry {per_axis} digits"
            )

    def test_grid_interval_follows_the_world_interval_floor(self):
        # The same 200 m view, with a 100 m floor and a 10 m floor.  The 10 m
        # floor yields a finer interval, so the world size drives the grid.
        c = ALTIS[3] / 2
        rect = [c - 50, c - 50, c + 50, c + 50]
        _s1, _l1, coarse = grid(ALTIS, rect, 100)
        _s2, _l2, fine = grid(ALTIS, rect, 10)
        self.assertEqual(coarse, 100)
        self.assertEqual(fine, 10)
        self.assertLess(fine, coarse)

    def test_the_handler_draws_each_label(self):
        # The labels must reach a draw call, not only be computed.
        self.assertIn('_x params ["_pos", "_label", "_major"];', MGRS_MAP_SRC)
        self.assertIn("_map drawIcon", MGRS_MAP_SRC)
        self.assertIn("} forEach _labels;", MGRS_MAP_SRC)
        self.assertIn('_label, 1, _size, _font, "center"', MGRS_MAP_SRC)

    def test_the_overlay_font_is_chosen_by_glyph_presence(self):
        # Red-before: the old code gated the font on isClass only, which is
        # true for a family whose glyph files are absent.
        self.assertNotIn(
            'isClass (configFile >> "CfgFontFamilies" >> "AEEFontMono")',
            MGRS_MAP_SRC,
        )
        self.assertIn("FUNC(mgrsFontFamily)", MGRS_MAP_SRC)

    def test_the_config_does_not_point_engine_text_at_a_glyphless_family(self):
        # Red-before: fontGrid/fontNames/font were all "AEEFont".
        for name, src in (
            ("config.cpp", CONFIG_SRC),
            ("config_mapdisplays.hpp", DISP_SRC),
            ("config_locationtypes.hpp", LOC_SRC),
            ("RscTitles.hpp", RSCTITLES_SRC),
        ):
            with self.subTest(source=name):
                self.assertNotIn('fontGrid = "AEEFont";', src)
                self.assertNotIn('fontNames = "AEEFont";', src)
                self.assertNotIn('font = "AEEFont";', src)
                self.assertNotIn('font = "AEEFontMono";', src)


class TestDefect1FontFallback(unittest.TestCase):
    """The overlay font falls back to the engine family when glyphs are absent."""

    def test_font_family_falls_back_when_the_glyphs_are_absent(self):
        # No family is usable in the stub, so the last-resort engine family.
        self.assertEqual(font_family(True, False), "TahomaB")
        self.assertEqual(font_family(False, False), "TahomaB")

    def test_font_family_uses_the_aee_family_when_the_glyphs_ship(self):
        self.assertEqual(font_family(True, True), "AEEFontMono")
        self.assertEqual(font_family(False, True), "AEEFont")

    def test_font_family_usable_is_false_when_the_glyph_file_is_absent(self):
        self.assertFalse(font_usable("AEEFontMono", False))

    def test_font_family_usable_is_true_when_the_glyph_file_exists(self):
        self.assertTrue(font_usable("AEEFontMono", True))

    def test_the_font_check_reads_the_glyph_files(self):
        self.assertIn("getArray (configFile", FONT_USABLE_SRC)
        self.assertIn('".fxy"', FONT_USABLE_SRC)


class TestDefect2CursorReadout(unittest.TestCase):
    """The cursor readout is the MGRS reference, not the engine grid number."""

    def test_cursor_readout_carries_the_mgrs_reference(self):
        written = _world_to_mgrs([15360, 15360, 0], ALTIS, 8)
        ref = written[0]
        text = cursor_text(ref, 123)
        self.assertIn(ref, text)
        self.assertIn(" m", text)

    def test_cursor_readout_is_never_empty(self):
        self.assertEqual(cursor_text("", 12), "ELEV 12 m")

    def test_the_engine_readout_is_hidden_with_its_children(self):
        # The engine tooltip group (idc 2350) and its Info child (idc 235002)
        # are hidden so only the aee readout shows.
        self.assertIn("displayCtrl 2350", MGRS_MAP_SRC)
        self.assertIn("displayCtrl 235002", MGRS_MAP_SRC)
        self.assertIn("ctrlShow false", MGRS_MAP_SRC)

    def test_the_readout_is_drawn_at_the_cursor(self):
        self.assertIn("_map ctrlMapScreenToWorld _mouse", MGRS_MAP_SRC)
        self.assertIn("call FUNC(mgrsMarkerText)", MGRS_MAP_SRC)
        self.assertIn("call FUNC(mgrsCursorText)", MGRS_MAP_SRC)

    def test_the_gps_readout_is_drawn_on_the_map(self):
        # The hand-held GPS readout is covered by the open map display, so the
        # overlay draws the MGRS reference on the map when an ItemGPS is held.
        self.assertIn('"ItemGPS" in (assignedItems _player)', MGRS_MAP_SRC)
        self.assertIn('"GPS  " + _gpsRef', MGRS_MAP_SRC)


class TestDefect3PrecisionByScale(unittest.TestCase):
    """The precision and interval follow the displayed scale and the setting."""

    def test_small_world_without_a_view_is_six_figure(self):
        self.assertEqual(precision(8192, 0), [6, 100])

    def test_large_world_without_a_view_is_eight_figure(self):
        self.assertEqual(precision(30720, 0), [8, 10])

    def test_a_zoomed_in_view_is_eight_figure(self):
        # A 30 km world seen across 2 km is an eighth of the world: 10 m.
        self.assertEqual(precision(30720, 2048), [8, 10])

    def test_a_wide_view_is_six_figure(self):
        self.assertEqual(precision(30720, 8192), [6, 100])

    def test_the_draw_handler_uses_the_scale_rule(self):
        # Red-before: the precision was read from a fixed setting only.
        self.assertIn("FUNC(mgrsMapPrecision)", MGRS_MAP_SRC)
        self.assertIn("QGVAR(mgrsPrecisionAuto)", MGRS_MAP_SRC)

    def test_the_precision_kernel_cites_the_standard(self):
        self.assertIn("NGA MGRS", PRECISION_SRC)
        self.assertIn("FM 3-25.26", PRECISION_SRC)


class TestDefect5Straightness(unittest.TestCase):
    """The drawn grid line is straight.  The projection is affine (measured to
    better than 0.13 m over 8 km), so the planner densifies each line and the
    segments of one line are collinear."""

    def test_the_planner_densifies_each_line_with_the_visible_span(self):
        # The count is adaptive so the joint deviation stays under a map pixel
        # at every zoom; the old fixed single-step chord is gone.
        self.assertIn("sqrt (_span / 40)", GRID_SRC)
        self.assertNotIn("private _samples = 3;", GRID_SRC)

    def test_consecutive_segments_of_a_line_are_collinear(self):
        c = ALTIS[3] / 2
        rect = [c - 1000, c - 1000, c + 1000, c + 1000]
        segments, _labels, _interval = grid(ALTIS, rect)
        self.assertGreater(len(segments), 4)
        joins = 0
        for i in range(len(segments) - 1):
            a0, a1, _am = segments[i]
            b0, b1, _bm = segments[i + 1]
            if a1[:2] != b0[:2]:
                continue  # the next segment starts a new line
            v1 = (a1[0] - a0[0], a1[1] - a0[1])
            v2 = (b1[0] - b0[0], b1[1] - b0[1])
            cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
            # the lateral offset at the join, in metres; sub-pixel at every
            # zoom (the main map is about 0.03 m per pixel at maximum zoom)
            deviation = cross / min(math.hypot(*v1), math.hypot(*v2))
            self.assertLess(
                deviation, 0.02, f"kink of {deviation:.5f} m at segment {i}"
            )
            joins += 1
        self.assertGreater(joins, 0, "no join points found")


class TestWiring(unittest.TestCase):
    """The new kernels are registered and the setting is declared."""

    def test_prep_registers_the_new_kernels(self):
        for name in (
            "fontFamilyUsable",
            "mgrsEffectivePrecision",
            "mgrsFontFamily",
            "mgrsMapPrecision",
        ):
            self.assertIn(f"PREPS(hud,{name});", PREP_SRC, name)

    def test_the_auto_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(mgrsPrecisionAuto,"AEE HUD","Displays",true)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in ("mgrsPrecisionAuto_Name", "mgrsPrecisionAuto_Description"):
            self.assertIn(f"STR_AEE_Optics_{key}", STRINGTABLE_SRC)


if __name__ == "__main__":
    unittest.main()
