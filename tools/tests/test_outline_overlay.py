#!/usr/bin/env python3
"""Fusion thermal-outline overlay tests (issue #204).

Executes the REAL SQF kernels through sqf_lite:

  addons/thermal/functions/outline/fnc_outlineHull.sqf
  addons/thermal/functions/outline/fnc_outlineSkeleton.sqf
  addons/thermal/functions/outline/fnc_outlineSensorLod.sqf

The engine-reading functions fnc_outlineCanvas, fnc_outlineCollect,
fnc_outlineDraw and fnc_outlineToggle cannot run without an engine, so their
source contract is locked here instead: the config declares the RscMapControl
canvas, the setting and the stringtable keys exist, every function is PREPed,
and the draw path is driven by aee's field gate and device resolver, not a
hardcoded field of view.

The hull kernel exercises the interpreter extensions added for it: forEach,
pushBack, deleteAt, sort, while and the boolean words.

Run: python3 -m unittest tools.tests.test_outline_overlay -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

OUTLINE = REPO / "addons" / "thermal" / "functions" / "outline"
HULL_KERNEL = OUTLINE / "fnc_outlineHull.sqf"
SKELETON_KERNEL = OUTLINE / "fnc_outlineSkeleton.sqf"
SENSOR_LOD_KERNEL = OUTLINE / "fnc_outlineSensorLod.sqf"
CANVAS_SRC = (OUTLINE / "fnc_outlineCanvas.sqf").read_text(encoding="utf-8")
COLLECT_SRC = (OUTLINE / "fnc_outlineCollect.sqf").read_text(encoding="utf-8")
DRAW_SRC = (OUTLINE / "fnc_outlineDraw.sqf").read_text(encoding="utf-8")
TOGGLE_SRC = (OUTLINE / "fnc_outlineToggle.sqf").read_text(encoding="utf-8")
PREP_SRC = (REPO / "addons" / "thermal" / "XEH_PREP.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (REPO / "addons" / "thermal" / "initSettings.inc.sqf").read_text(
    encoding="utf-8"
)
RSC_SRC = (REPO / "addons" / "thermal" / "RscTitles.hpp").read_text(encoding="utf-8")
STRINGTABLE_SRC = (REPO / "addons" / "thermal" / "stringtable.xml").read_text(
    encoding="utf-8"
)
POSTINIT_SRC = (REPO / "addons" / "optics" / "XEH_postInit.sqf").read_text(
    encoding="utf-8"
)


def _hull(points: list[list[float]]) -> list[float]:
    return run_sqf(HULL_KERNEL, [points], {})


def _lod(height_px: float) -> float:
    return run_sqf(SENSOR_LOD_KERNEL, [height_px], {})


def _skeleton() -> list[list[str]]:
    return run_sqf(SKELETON_KERNEL, [], {})


class TestOutlineHull(unittest.TestCase):
    """fnc_outlineHull, executed: the Andrew monotone chain."""

    def test_a_square_gives_four_hull_indices(self):
        hull = _hull([[0, 0], [0, 10], [10, 0], [10, 10]])
        self.assertEqual(len(hull), 4)
        self.assertEqual({int(i) for i in hull}, {0, 1, 2, 3})

    def test_an_interior_point_is_excluded(self):
        hull = _hull([[0, 0], [0, 10], [10, 0], [10, 10], [5, 5]])
        self.assertEqual(len(hull), 4)
        self.assertNotIn(4, {int(i) for i in hull})

    def test_fewer_than_three_points_returns_every_index(self):
        self.assertEqual([int(i) for i in _hull([[0, 0], [1, 1]])], [0, 1])
        self.assertEqual([int(i) for i in _hull([[3, 4]])], [0])
        self.assertEqual(_hull([]), [])

    def test_collinear_points_degrade_without_error(self):
        hull = _hull([[0, 0], [1, 1], [2, 2], [3, 3]])
        self.assertEqual(len(hull), 2)
        self.assertEqual({int(i) for i in hull}, {0, 3})

    def test_a_negative_extent_keeps_the_corner(self):
        hull = _hull([[-5, -5], [-5, 5], [5, -5], [5, 5]])
        self.assertEqual(len(hull), 4)


class TestOutlineSensorLod(unittest.TestCase):
    """fnc_outlineSensorLod, executed: the four sensor thresholds."""

    def test_the_full_detail_boundary(self):
        self.assertEqual(_lod(59.9), 1)
        self.assertEqual(_lod(60), 0)
        self.assertEqual(_lod(120), 0)

    def test_the_medium_boundary(self):
        self.assertEqual(_lod(24), 2)
        self.assertEqual(_lod(25), 1)

    def test_the_simplified_boundary(self):
        self.assertEqual(_lod(9), 3)
        self.assertEqual(_lod(10), 2)

    def test_a_blob_below_ten(self):
        self.assertEqual(_lod(0), 3)


class TestOutlineSkeleton(unittest.TestCase):
    """fnc_outlineSkeleton, executed: four bone lists."""

    def test_there_are_four_levels(self):
        self.assertEqual(len(_skeleton()), 4)

    def test_the_levels_shrink_with_distance(self):
        levels = _skeleton()
        self.assertEqual(len(levels[0]), 16)
        self.assertEqual(len(levels[1]), 16)
        self.assertEqual(len(levels[2]), 7)
        self.assertEqual(len(levels[3]), 4)

    def test_every_level_starts_with_the_head(self):
        for level in _skeleton():
            with self.subTest(level=level):
                self.assertEqual(level[0], "head")


class TestOutlineConfigContract(unittest.TestCase):
    """The canvas, the setting and the stringtable are declared."""

    def test_the_display_class_owns_a_map_control_canvas(self):
        self.assertIn("class GVAR(fusionOutline)", RSC_SRC)
        self.assertIn("class AEEOutlineCanvas: RscMapControl", RSC_SRC)
        self.assertIn("class RscMapControl;", RSC_SRC)

    def test_the_canvas_colours_are_all_zero(self):
        for key in (
            "colorBackground[]",
            "colorOutside[]",
            "colorSea[]",
            "colorText[]",
            "colorForest[]",
            "colorRocks[]",
            "colorRoads[]",
        ):
            self.assertIn(f"{key} = {{0, 0, 0, 0}};", RSC_SRC, key)

    def test_the_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(fusionOutline,"AEE Thermal","Fusion",true)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in ("fusionOutline_Name", "fusionOutline_Description"):
            self.assertIn(f"STR_AEE_Thermal_{key}", STRINGTABLE_SRC)

    def test_the_outline_display_is_idc_1301(self):
        self.assertIn("idc = 1301;", RSC_SRC)
        self.assertIn("displayCtrl 1301", CANVAS_SRC)


class TestOutlineWiring(unittest.TestCase):
    """Registration, the NVG dispatch and the teardown path."""

    def test_prep_registers_every_outline_function(self):
        for name in (
            "outlineHull",
            "outlineSkeleton",
            "outlineSensorLod",
            "outlineCanvas",
            "outlineCollect",
            "outlineDraw",
            "outlineToggle",
        ):
            self.assertIn(f"PREPS(outline,{name});", PREP_SRC, name)

    def test_the_draw_path_is_driven_by_our_field_and_device(self):
        self.assertIn("call FUNC(fusionFovGate)", DRAW_SRC)
        self.assertIn("call FUNC(resolveFusionDevice)", DRAW_SRC)
        self.assertIn("_pair select 2", DRAW_SRC)

    def test_the_draw_path_has_no_hardcoded_field(self):
        for token in ("_DECLARED_HALF_ANGLE_DEG", "_hmdLower", 'case "BNVD-FUSED"'):
            self.assertNotIn(token, DRAW_SRC, token)

    def test_the_draw_path_reads_the_collected_hot_list(self):
        self.assertIn("call FUNC(outlineCollect)", DRAW_SRC)
        self.assertIn("call FUNC(outlineHull)", DRAW_SRC)
        self.assertIn("call FUNC(outlineSensorLod)", DRAW_SRC)

    def test_the_collector_is_not_camanbase_only(self):
        self.assertIn("QGVAR(selTemperature)", COLLECT_SRC)
        for token in ('"CAManBase"', '"Car"', '"Tank"', '"StaticWeapon"', '"Air"'):
            self.assertIn(token, COLLECT_SRC, token)
        self.assertNotIn('["CAManBase", _range]', COLLECT_SRC)

    def test_the_toggle_raises_and_lowers_the_display(self):
        self.assertIn('cutRsc [QGVAR(fusionOutline), "PLAIN", 0, false]', TOGGLE_SRC)
        self.assertIn('cutText ["", "PLAIN"]', TOGGLE_SRC)
        self.assertIn("QGVAR(outlineOn)", TOGGLE_SRC)

    def test_the_nvg_dispatch_drives_the_outline(self):
        self.assertIn("[true] call EFUNC(thermal,outlineToggle);", POSTINIT_SRC)
        self.assertIn("[false] call EFUNC(thermal,outlineToggle);", POSTINIT_SRC)


if __name__ == "__main__":
    unittest.main()
