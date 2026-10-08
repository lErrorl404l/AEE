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

# Stratis ships no usable mapArea box, so its anchor falls back to the
# CfgWorlds keys and FUNC(utmToWorld) uses the local tangent plane.
STRATIS = [35.097, 16.482, 35, 8192, 0, 0, 0, 0, "cfgworlds"]


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

    def test_the_engine_readout_is_hidden(self):
        # The engine tooltip group (idc 2350) is hidden.  The config neutralises
        # its render, so the hide is a first line of defence.
        self.assertIn("displayCtrl 2350", MGRS_MAP_SRC)
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
    """A drawn grid line is cardinal: axis-aligned and straight.

    The grid is the map-axis grid, not the true MGRS grid.  A vertical line
    sits at one constant world x and a horizontal line at one constant world
    y.  The map control maps world to screen with a LINEAR transform, so an
    axis-aligned world line is a straight screen line by construction, with
    zero tilt from the cardinal axes.  ADR-030 records the switch from the
    true MGRS grid and the operator's reason: the map is north up, the compass
    and a real paper map read cardinal, and the base engine's own grid is
    cardinal.
    """

    def _plan(self):
        c = ALTIS[3] / 2
        return grid(ALTIS, [c - 1000, c - 1000, c + 1000, c + 1000])

    def test_the_emitted_lines_are_axis_aligned(self):
        segments, _labels, _interval = self._plan()
        self.assertGreater(len(segments), 4)
        vertical = horizontal = 0
        for a, b, _major in segments:
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            if abs(dx) < 1e-6:
                self.assertGreater(abs(dy), 1e-6, f"degenerate vertical line {a}")
                vertical += 1
            else:
                self.assertEqual(dy, 0.0, f"line is not cardinal: {a} -> {b}")
                horizontal += 1
        self.assertGreater(vertical, 0, "no vertical line")
        self.assertGreater(horizontal, 0, "no horizontal line")

    def test_the_lines_have_zero_tilt_from_the_cardinal_axes(self):
        # The tilt is the off-axis component of the line direction.  A
        # vertical line has no x-component and a horizontal line no
        # y-component, so the tilt is zero on both.  Red-before: the true MGRS
        # line was tilted by the grid convergence (+0.85 deg on Stratis).
        segments, _labels, _interval = self._plan()
        for a, b, _major in segments:
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            tilt = abs(dx) if abs(dx) < 1e-6 else abs(dy)
            self.assertEqual(tilt, 0.0, f"nonzero tilt on {a} -> {b}")

    def test_the_interval_is_a_world_metre_step(self):
        # The lines land on whole world-metre steps, so the grid is cardinal
        # in world coordinates, not projected from UTM.
        segments, _labels, interval = self._plan()
        self.assertIn(interval, (10, 100, 1000, 10000, 100000))
        for a, b, _major in segments:
            dx = b[0] - a[0]
            coord = a[0] if abs(dx) < 1e-6 else a[1]
            self.assertAlmostEqual(coord / interval, round(coord / interval), places=6)

    def test_each_line_carries_its_positional_mgrs_label(self):
        # A cardinal line has no single grid value, so the label is positional:
        # the MGRS digit group at a fixed point of the line.  Every line gets
        # one at BOTH ends (top and bottom, left and right), so the digit count
        # matches the interval.
        segments, labels, interval = self._plan()
        per_axis = round(5 - math.log10(interval))
        self.assertEqual(len(labels), 2 * len(segments))
        for pos, text, _major in labels:
            self.assertEqual(len(pos), 3, pos)
            self.assertTrue(text.isdigit(), f"label {text!r} is not digits")
            self.assertEqual(
                len(text), per_axis, f"label {text!r} must be {per_axis} digits"
            )

    def test_the_planner_draws_one_segment_per_line(self):
        # Red-before: the planner projected each line through FUNC(utmToWorld)
        # and split it on a measured bend.  A cardinal line needs neither.
        self.assertNotIn("utmToWorld", GRID_SRC)
        self.assertNotIn("_samples", GRID_SRC)
        self.assertNotIn("_dev > _pixel", GRID_SRC)
        self.assertIn(
            "_segments pushBack [[_line, _yMin, 0], [_line, _yMax, 0], _major];",
            GRID_SRC,
        )

    def test_the_emitted_plan_has_no_interior_joint(self):
        segments, _labels, _interval = self._plan()
        self.assertGreater(len(segments), 4)
        # An interior joint is a shared endpoint between consecutive segments
        # of one line.  One axis-aligned segment per line has none.
        joins = sum(
            1
            for i in range(len(segments) - 1)
            if segments[i][1][:2] == segments[i + 1][0][:2]
        )
        self.assertEqual(joins, 0, "an interior joint would bead at the seam")


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


# ── The engine edge-number rule (CStaticMap::DrawGrid) ───────────────────────
# Faithful transcription of the number placement in the open-sourced engine
# (BohemiaInteractive/CWR, engine/Poseidon/UI/Map/UIMap.cpp:1971-2045).  The
# control units are anisotropic: x/w are fractions of the screen WIDTH and y/h
# of the screen HEIGHT, so the row (northing) spacing is wScreen/hScreen times
# the column (easting) spacing.  Each number is drawn at half a grid spacing
# from its line and clipped to the control rect, so it is visible only while
# the spacing sits inside a band.  AEE cannot change DrawGrid; this pins the
# rule that defect 2 follows from.


def drawgrid_edge_numbers(
    scale_x, w, h, size_grid, width, step, size_land, w_screen, h_screen
):
    """Return (x_fld, z_fld, row_visible, col_visible) for the first line.

    The first grid line sits at the control edge (zBeg ~= _y), so the first
    row number's top is 0.5*(zFld - size_grid) and the first column number's
    left is 0.5*(xFld - width), each clipped to the control rect.
    """
    scale_y = (h_screen / w_screen) * scale_x  # Precalculate()
    x_fld = abs((1.0 / scale_x) * (step / size_land))
    z_fld = abs((1.0 / scale_y) * (step / size_land))
    row_top = 0.5 * (z_fld - size_grid)
    row_visible = row_top >= 0.0 and (row_top + size_grid) <= h
    col_left = 0.5 * (x_fld - width)
    col_visible = col_left >= 0.0 and (col_left + width) <= w
    return x_fld, z_fld, row_visible, col_visible


class TestDefect2EdgeNumberClip(unittest.TestCase):
    """The engine clips its own northing numbers at close zoom.

    CStaticMap::DrawGrid places each edge number at half a grid spacing from
    its line and clips to the control rect.  Because the control units are
    anisotropic (x/w = screen width, y/h = screen height), the row spacing is
    wScreen/hScreen times the column spacing, so the northing (left/right)
    numbers leave the control before the easting (top/bottom) ones.  That is
    the operator's report: at close zoom the top and bottom numbers still show
    and the left and right disappear.
    """

    W, H = 1.0, 0.9  # the map control, as screen fractions
    SIZE_GRID = 0.04
    WIDTH = 0.1  # a three-character "000" easting at sizeExGrid 0.04
    STEP = 100.0  # Altis Grid Zoom1 stepX/stepY
    SIZE_LAND = 30720.0  # Altis mapSize
    WSCREEN, HSCREEN = 1920, 1080

    def _visible(self, scale_x):
        return drawgrid_edge_numbers(
            scale_x,
            self.W,
            self.H,
            self.SIZE_GRID,
            self.WIDTH,
            self.STEP,
            self.SIZE_LAND,
            self.WSCREEN,
            self.HSCREEN,
        )

    def test_the_row_spacing_carries_the_screen_aspect(self):
        # Precalculate() sets _scaleY = (hScreen/wScreen)*_scaleX, so for equal
        # steps the row spacing is wScreen/hScreen times the column spacing.
        x_fld, z_fld, _row, _col = self._visible(0.01)
        self.assertAlmostEqual(z_fld / x_fld, self.WSCREEN / self.HSCREEN, places=6)

    def test_both_axes_show_at_a_wide_zoom(self):
        _x, _z, row, col = self._visible(0.02)
        self.assertTrue(row, "northing numbers show when the rows are close")
        self.assertTrue(col, "easting numbers show when the columns are close")

    def test_the_operator_sees_easting_but_not_northing_at_close_zoom(self):
        _x, _z, row, col = self._visible(0.003)
        self.assertFalse(row, "northing (left/right) numbers clip at close zoom")
        self.assertTrue(col, "easting (top/bottom) numbers still show")

    def test_the_northing_band_ends_before_the_easting_band(self):
        # The row band's upper limit, in xFld, precedes the column band's, so a
        # zoom exists where only the easting numbers remain.  If the two bands
        # ended together the defect could not happen.
        row_limit = (2 * self.H - self.SIZE_GRID) * self.HSCREEN / self.WSCREEN
        col_limit = 2 * self.W - self.WIDTH
        self.assertLess(row_limit, col_limit)


class TestDefect1TooltipNeutralised(unittest.TestCase):
    """The engine cursor tooltip is neutralised at the config.

    Closed engine C++ fills and shows RscMapControlTooltip after the map
    control's Draw event, so the script hide loses the race.  The config makes
    the Info text and its backdrop transparent, so nothing renders even when
    the engine shows the control.
    """

    def test_the_tooltip_group_restates_its_parent(self):
        # A bare reopen of a class that has a parent strips it.
        self.assertIn(
            "class RscMapControlTooltip: RscControlsGroupNoScrollbars", CONFIG_SRC
        )

    def test_the_tooltip_info_text_is_transparent(self):
        flat = " ".join(CONFIG_SRC.split())
        self.assertIn(
            "class Info: RscStructuredText { colorText[] = {0, 0, 0, 0}; }", flat
        )

    def test_the_tooltip_box_is_transparent(self):
        flat = " ".join(CONFIG_SRC.split())
        self.assertIn(
            "class Background: RscText { colorBackground[] = {0, 0, 0, 0}; }", flat
        )

    def test_the_tooltip_backdrop_is_transparent(self):
        flat = " ".join(CONFIG_SRC.split())
        self.assertIn(
            "class InfoBackground: RscStructuredText { colorBackground[] = {0, 0, 0, 0}; }",
            flat,
        )

    def test_the_runtime_hide_is_kept(self):
        # The config neutralises the render; the runtime hide stays as the
        # first line of defence.
        self.assertIn("displayCtrl 2350", MGRS_MAP_SRC)
        self.assertIn("_engineReadout ctrlShow false", MGRS_MAP_SRC)


class TestDefect2EdgeRulerComplete(unittest.TestCase):
    """The AEE ruler is complete at all four edges.

    The engine's own DrawGrid clips its northing numbers at close zoom, so AEE
    supplies the missing left and right reference by labelling every line at
    both ends.
    """

    def _plan(self):
        c = ALTIS[3] / 2
        return grid(ALTIS, [c - 1000, c - 1000, c + 1000, c + 1000])

    def test_the_kernel_labels_both_ends_of_every_line(self):
        self.assertIn(
            "_labels pushBack [[_line, _yMax, 0], _easting, _major];", GRID_SRC
        )
        self.assertIn(
            "_labels pushBack [[_line, _yMin, 0], _easting, _major];", GRID_SRC
        )
        self.assertIn(
            "_labels pushBack [[_xMax, _line, 0], _northing, _major];", GRID_SRC
        )
        self.assertIn(
            "_labels pushBack [[_xMin, _line, 0], _northing, _major];", GRID_SRC
        )

    def test_every_line_end_carries_a_label(self):
        # The easting reads at the top and bottom, the northing at the left and
        # right, so a label sits at each endpoint of every emitted line.
        segments, labels, _interval = self._plan()
        ends = {(round(p[0], 3), round(p[1], 3)) for p, _t, _m in labels}
        for a, b, _major in segments:
            for end in (a, b):
                key = (round(end[0], 3), round(end[1], 3))
                self.assertIn(key, ends, f"line end {key} is unlabelled")


if __name__ == "__main__":
    unittest.main()
