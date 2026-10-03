#!/usr/bin/env python3
"""Fusion thermal-outline overlay tests (issue #204).

Executes the REAL SQF kernels through sqf_lite:

  addons/thermal/functions/outline/fnc_outlineTopo.sqf
  addons/thermal/functions/outline/fnc_outlineSkeleton.sqf
  addons/thermal/functions/outline/fnc_outlineSensorLod.sqf

The engine-reading functions fnc_outlineCanvas, fnc_outlineCollect,
fnc_outlineDraw and fnc_outlineToggle cannot run without an engine, so their
source contract is locked here instead: the config declares the RscMapControl
canvas, the setting and the stringtable keys exist, every function is PREPed,
and the draw path is driven by aee's field gate and device resolver, not a
hardcoded field of view.  The draw path must reach for the capsule-union
topology (FUNC(outlineTopo)) and must not reach for the removed convex hull.

The topo kernel exercises the interpreter extensions added for it: the vector
commands, `mod`, the degree trig functions, findIf, continue and the lazy
`&& { ... }` block.

Run: python3 -m unittest tools.tests.test_outline_overlay -v
"""

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

OUTLINE = REPO / "addons" / "thermal" / "functions" / "outline"
TOPO_KERNEL = OUTLINE / "fnc_outlineTopo.sqf"
SKELETON_KERNEL = OUTLINE / "fnc_outlineSkeleton.sqf"
SENSOR_LOD_KERNEL = OUTLINE / "fnc_outlineSensorLod.sqf"
GEAR_KERNEL = OUTLINE / "fnc_outlineGearRadius.sqf"
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

# A camera looking down +Y with a right-handed screen basis.  One pixel of
# tangent is 0.001, so the sampling density is generous.
CAM = [0, 0, 0]
VF = [0, 1, 0]
VR = [1, 0, 0]
VU = [0, 0, 1]
PX_TAN = 0.001


def _capsule(x: float, r: float, rb: float | None = None) -> list:
    """A vertical capsule at range 10, radius r (optionally tapered)."""
    if rb is None:
        rb = r
    return [[x, 10, -0.5], [0, 0, 1], [1, 0, 0], [0, 1, 0], r, rb]


def _topo(capsules: list) -> list:
    return run_sqf(TOPO_KERNEL, [capsules, CAM, VF, VR, VU, PX_TAN, False], {})


def _lod(height_px: float) -> float:
    return run_sqf(SENSOR_LOD_KERNEL, [height_px], {})


def _skeleton() -> list:
    return run_sqf(SKELETON_KERNEL, [], {})


def _gear(
    r: float, rb: float, ext: float, role: int, gh: int, gv: int, gp: bool, infl: float
) -> list:
    """fnc_outlineGearRadius: gear-adjusted [ext, rA, rB]."""
    return run_sqf(GEAR_KERNEL, [r, rb, ext, role, gh, gv, gp, infl], {})


def _run_source(source: str):
    """Run an inline SQF program from a temporary file."""
    with tempfile.NamedTemporaryFile("w", suffix=".sqf", delete=False) as fh:
        fh.write(source)
        path = fh.name
    try:
        return run_sqf(path, [], {})
    finally:
        Path(path).unlink(missing_ok=True)


class TestOutlineTopo(unittest.TestCase):
    """fnc_outlineTopo, executed: the capsule-union silhouette topology."""

    def test_two_overlapping_capsules_share_a_non_empty_union(self):
        topo = _topo([_capsule(-0.3, 0.4), _capsule(0.3, 0.4)])
        self.assertEqual(len(topo), 2)
        # Each capsule keeps a visible arc where the other does not hide it.
        self.assertNotEqual(topo[0], [])
        self.assertNotEqual(topo[1], [])
        self.assertGreater(sum(len(poly) for poly in topo[0]), 0)
        self.assertGreater(sum(len(poly) for poly in topo[1]), 0)

    def test_a_capsule_fully_inside_another_has_no_polylines(self):
        topo = _topo([_capsule(0.0, 0.6), _capsule(0.0, 0.1)])
        self.assertEqual(topo[1], [])
        self.assertNotEqual(topo[0], [])

    def test_an_empty_descriptor_yields_no_polylines(self):
        topo = _topo([[], _capsule(0.0, 0.4)])
        self.assertEqual(topo[0], [])
        self.assertNotEqual(topo[1], [])

    def test_points_are_three_parameter_capsule_coordinates(self):
        topo = _topo([_capsule(0.0, 0.4)])
        for poly in topo[0]:
            for point in poly:
                self.assertEqual(len(point), 3)

    def test_tapered_capsules_are_accepted(self):
        topo = _topo([_capsule(0.0, 0.4, 0.2)])
        self.assertEqual(len(topo), 1)
        self.assertNotEqual(topo[0], [])


class TestVectorBuiltins(unittest.TestCase):
    """The vector, modulo and trig builtins the topo kernel needs."""

    def test_the_builtins_return_the_expected_values(self):
        out = _run_source(
            "private _cx = [1, 0, 0] vectorCrossProduct [0, 1, 0];\n"
            "private _n = vectorNormalized [0, 0, 4];\n"
            "private _m = vectorMagnitude [3, 4, 0];\n"
            "private _c = ceil 1.2;\n"
            "private _co = cos 60;\n"
            "private _si = sin 30;\n"
            "private _mo = 7 mod 3;\n"
            "[_cx, _n, _m, _c, _co, _si, _mo]\n"
        )
        cross, norm, mag, ceil_v, cos_v, sin_v, mod_v = out
        self.assertEqual(cross, [0, 0, 1])
        self.assertAlmostEqual(norm[2], 1.0)
        self.assertAlmostEqual(mag, 5.0)
        self.assertEqual(ceil_v, 2)
        self.assertAlmostEqual(cos_v, 0.5, places=6)
        self.assertAlmostEqual(sin_v, 0.5, places=6)
        self.assertAlmostEqual(mod_v, 1.0)


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
    """fnc_outlineSkeleton, executed: four full level-of-detail structures."""

    def test_there_are_four_levels(self):
        self.assertEqual(len(_skeleton()), 4)

    def test_each_level_has_the_full_structure(self):
        for level in _skeleton():
            with self.subTest(level=level):
                self.assertGreaterEqual(len(level), 5)
                self.assertIsInstance(level[0], list)  # boneList
                self.assertIsInstance(level[1], list)  # capList
                self.assertIsInstance(level[2], list)  # probes
                self.assertIsInstance(level[3], list)  # pmap
                self.assertIsInstance(level[4], (int, float))

    def test_every_capsule_is_a_descriptor(self):
        for level in _skeleton():
            for cap in level[1]:
                with self.subTest(cap=cap):
                    self.assertGreaterEqual(len(cap), 4)

    def test_the_bone_lists_shrink_with_distance(self):
        levels = _skeleton()
        self.assertEqual(len(levels[0][0]), 16)
        self.assertEqual(len(levels[1][0]), 16)
        self.assertEqual(len(levels[2][0]), 7)
        self.assertEqual(len(levels[3][0]), 4)

    def test_every_bone_level_starts_with_the_head(self):
        for level in _skeleton():
            with self.subTest(level=level):
                self.assertEqual(level[0][0], "head")

    def test_the_near_levels_carry_the_three_body_roles(self):
        roles = {cap[5] for cap in _skeleton()[0][1]}
        self.assertEqual(roles, {0, 1, 2, 3})

    def test_the_backpack_points_are_inside_the_bone_list(self):
        levels = _skeleton()
        for level in levels[:3]:
            bone_count = len(level[0])
            for idx in level[5]:
                self.assertLess(idx, bone_count)


class TestOutlineGearRadius(unittest.TestCase):
    """fnc_outlineGearRadius, executed: the source's gear tables and blur.

    Copied from fn_drawOutlines.sqf:434-452 (role cases) and :466 (the _infl
    add).  The kernels values are the source's own; the tests fix them.
    """

    def test_no_gear_only_adds_the_sensor_blur(self):
        out = _gear(0.16, 0.19, 0.0, 0, 0, 0, False, 0.05)
        self.assertAlmostEqual(out[0], 0.0)
        self.assertAlmostEqual(out[1], 0.21)
        self.assertAlmostEqual(out[2], 0.24)

    def test_a_helmet_inflates_the_head_and_extends_it(self):
        # role 1, _gH 2: radii +0.012, ext +0.045.
        out = _gear(0.105, 0.095, 0.11, 1, 2, 0, False, 0.05)
        self.assertAlmostEqual(out[0], 0.155)
        self.assertAlmostEqual(out[1], 0.167)
        self.assertAlmostEqual(out[2], 0.157)

    def test_a_soft_cover_uses_the_smaller_head_table(self):
        # role 1, _gH 1: radii +0.005, ext +0.02.
        out = _gear(0.105, 0.095, 0.11, 1, 1, 0, False, 0.05)
        self.assertAlmostEqual(out[0], 0.13)
        self.assertAlmostEqual(out[1], 0.16)
        self.assertAlmostEqual(out[2], 0.15)

    def test_a_plate_carrier_inflates_the_torso(self):
        # role 2, _gV 2: both radii +0.03, no extension change.
        out = _gear(0.16, 0.19, 0.0, 2, 0, 2, False, 0.05)
        self.assertAlmostEqual(out[0], 0.0)
        self.assertAlmostEqual(out[1], 0.24)
        self.assertAlmostEqual(out[2], 0.27)

    def test_a_light_rig_uses_the_smaller_torso_table(self):
        out = _gear(0.16, 0.19, 0.0, 2, 0, 1, False, 0.05)
        self.assertAlmostEqual(out[1], 0.222)
        self.assertAlmostEqual(out[2], 0.252)

    def test_a_pack_capsule_without_a_backpack_collapses(self):
        # role 3, _gP false: radii forced to 0.02, then + blur.
        out = _gear(0.15, 0.13, 0.0, 3, 0, 0, False, 0.05)
        self.assertAlmostEqual(out[1], 0.07)
        self.assertAlmostEqual(out[2], 0.07)

    def test_a_pack_capsule_with_a_backpack_keeps_its_radii(self):
        out = _gear(0.15, 0.13, 0.0, 3, 0, 0, True, 0.05)
        self.assertAlmostEqual(out[1], 0.20)
        self.assertAlmostEqual(out[2], 0.18)

    def test_the_blur_is_added_after_the_gear_delta(self):
        without = _gear(0.16, 0.19, 0.0, 0, 0, 0, False, 0.0)
        with_blur = _gear(0.16, 0.19, 0.0, 0, 0, 0, False, 0.12)
        self.assertAlmostEqual(with_blur[1] - without[1], 0.12)
        self.assertAlmostEqual(with_blur[2] - without[2], 0.12)

    def test_the_blur_is_capped_at_the_source_value(self):
        # The cap lives in fnc_outlineDraw as (_mpp * 0.5) min 0.12; the kernel
        # itself takes whatever it is given.
        out = _gear(0.16, 0.19, 0.0, 0, 0, 0, False, 0.12)
        self.assertAlmostEqual(out[1], 0.28)


class TestOutlineGearPort(unittest.TestCase):
    """The engine-bound draw path reads the gear the source reads.

    fnc_outlineDraw cannot run headless, so the source contract is locked: it
    must detect headgear / vest / backpack, read the armor protection the same
    way, cache for 3 s, inflate the backpack points, add the _infl sensor blur,
    and delegate the tables to FUNC(outlineGearRadius).  The old header line
    that excused the omission must be gone.
    """

    def test_the_draw_path_detects_the_gear(self):
        for token in (
            "headgear _obj",
            "vest _obj",
            "backpack _obj",
            'isKindOf "CAManBase"',
            "HitpointsProtectionInfo",
            '"Head"',
            '"Chest"',
            '"Body"',
            "outlineGearMap",
        ):
            self.assertIn(token, DRAW_SRC, token)

    def test_the_gear_reads_are_cached_for_three_seconds(self):
        self.assertIn("QGVAR(outlineGear)", DRAW_SRC)
        self.assertIn("((diag_tickTime) - (_gr select 0)) > 3", DRAW_SRC)

    def test_the_draw_path_inflates_the_backpack_points(self):
        self.assertIn("[0, -0.22, 0]", DRAW_SRC)
        self.assertIn("[0, -0.20, 0.15]", DRAW_SRC)
        self.assertIn("if (_gP) then {", DRAW_SRC)

    def test_the_draw_path_applies_the_sensor_blur(self):
        self.assertIn("_infl = (_mpp * 0.5) min 0.12", DRAW_SRC)
        self.assertIn(
            "[_rCap, _rBCap, _ext, _role, _gH, _gV, _gP, _infl] call FUNC(outlineGearRadius)",
            DRAW_SRC,
        )
        self.assertIn("_ext = _adj select 0;", DRAW_SRC)

    def test_the_omission_excuse_is_gone(self):
        self.assertNotIn("Deliberate omissions", DRAW_SRC)
        self.assertNotIn("gear pass is not ported", DRAW_SRC)
        self.assertIn("is ported from the same source", DRAW_SRC)


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
            "outlineTopo",
            "outlineSkeleton",
            "outlineSensorLod",
            "outlineGearRadius",
            "outlineCanvas",
            "outlineCollect",
            "outlineDraw",
            "outlineToggle",
        ):
            self.assertIn(f"PREPS(outline,{name});", PREP_SRC, name)

    def test_the_removed_hull_is_not_registered(self):
        self.assertNotIn("outlineHull", PREP_SRC)

    def test_the_draw_path_is_driven_by_our_field_and_device(self):
        self.assertIn("call FUNC(fusionFovGate)", DRAW_SRC)
        self.assertIn("call FUNC(resolveFusionDevice)", DRAW_SRC)
        self.assertIn("_pair select 2", DRAW_SRC)

    def test_the_draw_path_has_no_hardcoded_field(self):
        for token in ("_DECLARED_HALF_ANGLE_DEG", "_hmdLower", 'case "BNVD-FUSED"'):
            self.assertNotIn(token, DRAW_SRC, token)

    def test_the_draw_path_uses_the_capsule_union_not_the_hull(self):
        self.assertIn("call FUNC(outlineCollect)", DRAW_SRC)
        self.assertIn("call FUNC(outlineSensorLod)", DRAW_SRC)
        self.assertIn("call FUNC(outlineTopo)", DRAW_SRC)
        self.assertIn("call FUNC(outlineSkeleton)", DRAW_SRC)
        self.assertNotIn("call FUNC(outlineHull)", DRAW_SRC)

    def test_the_draw_path_keeps_the_source_occlusion(self):
        self.assertIn("checkVisibility", DRAW_SRC)
        self.assertIn("lineIntersectsSurfaces", DRAW_SRC)
        self.assertIn('isKindOf "CAManBase"', DRAW_SRC)

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


class TestOutlineWorkerWiring(unittest.TestCase):
    """The outline has a per-frame caller.

    The silent-outline defect: FUNC(outlineDraw) computed the segments but no
    event ever called it, so the canvas stayed empty and the RPT held no
    "fusion outline" line.  The source runs its draw worker on the mission
    Draw3D event; these contracts pin that registration.
    """

    def test_the_thermal_postinit_registers_a_draw3d_worker(self):
        src = (REPO / "addons" / "thermal" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn('addMissionEventHandler ["Draw3D"', src)
        self.assertIn("FUNC(outlineDraw)", src)
        self.assertIn("hasInterface", src)

    def test_the_postinit_event_handler_is_declared(self):
        src = (REPO / "addons" / "thermal" / "CfgEventHandlers.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("Extended_PostInit_EventHandlers", src)
        self.assertIn("COMPILE_SCRIPT(XEH_postInit)", src)

    def test_the_toggle_logs_the_state_change(self):
        self.assertIn('"fusion outline: display raised"', TOGGLE_SRC)
        self.assertIn('"fusion outline: display cleared"', TOGGLE_SRC)


class TestOutlineCollectorCacheKey(unittest.TestCase):
    """The collector's per-object cache key must be one Arma 3 can hash.

    BIKI HashMap, "Unsupported Key Types": a HashMap rejects Object keys.  The
    supported key types are Array, Boolean, Code, Config, Namespace, NaN,
    Number, Side and String only.  An Object key raised "Error Type Object" on
    getOrDefault and on set at every object, every frame - 85,921 errors in a
    2.5 minute run, split 42,961 at the read and 42,960 at the write.  The
    collector now derives a String key with str _obj and drives both the read
    and the write with it, so a written entry is a cache hit on the next pass.
    """

    def test_the_cache_no_longer_keys_by_object(self):
        # The raw-object key is the fault.  It must be gone from both sinks.
        self.assertNotIn("_cache getOrDefault [_obj,", COLLECT_SRC)
        self.assertNotIn("_cache set [_obj,", COLLECT_SRC)

    def test_the_cache_round_trip_uses_one_object_derived_key(self):
        # One key variable, derived from the object with str, feeds the read
        # and the write.  The round-trip is therefore a hit, not a miss.
        self.assertIn("private _objKey = str _obj;", COLLECT_SRC)
        self.assertIn("_cache getOrDefault [_objKey, []", COLLECT_SRC)
        self.assertIn("_cache set [_objKey, [_now, _isHot]]", COLLECT_SRC)

    def test_the_selection_temperature_map_keeps_a_string_key(self):
        # The neighbouring QGVAR(selTemperature) read already builds a String
        # key from the object.  It must stay a String and never the raw object.
        self.assertIn(
            '_selMap getOrDefault [format ["%1|%2", _obj, _selName], -999]',
            COLLECT_SRC,
        )


if __name__ == "__main__":
    unittest.main()
