#!/usr/bin/env python3
"""Laser target marker tests (port of A3TI/LTM).

Executes the REAL pure geometry through sqf_lite:

  addons/nightvision/functions/ltm/fnc_ltmBeamSegments.sqf

The engine-reading functions fnc_ltmCreate, fnc_ltmDraw, fnc_ltmPFH,
fnc_ltmToggle, fnc_ltmToggleMode and fnc_ltmInit cannot run without an
engine, so their source contract is locked here instead: the draw function
uses drawLine3D, the create function reads laserTarget, the PFH gates on
night vision mode 1, no source refers to a p3d asset, and the setting, PREP
entries, keybinds and postInit wiring exist.

Run: python3 -m unittest tools.tests.test_ltm -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

LTM = REPO / "addons" / "nightvision" / "functions" / "ltm"
SEGMENT_KERNEL = LTM / "fnc_ltmBeamSegments.sqf"
SEGMENT_SRC = SEGMENT_KERNEL.read_text(encoding="utf-8")
CREATE_SRC = (LTM / "fnc_ltmCreate.sqf").read_text(encoding="utf-8")
DRAW_SRC = (LTM / "fnc_ltmDraw.sqf").read_text(encoding="utf-8")
PFH_SRC = (LTM / "fnc_ltmPFH.sqf").read_text(encoding="utf-8")
TOGGLE_SRC = (LTM / "fnc_ltmToggle.sqf").read_text(encoding="utf-8")
MODE_SRC = (LTM / "fnc_ltmToggleMode.sqf").read_text(encoding="utf-8")
INIT_SRC = (LTM / "fnc_ltmInit.sqf").read_text(encoding="utf-8")
PREP_SRC = (REPO / "addons" / "nightvision" / "XEH_PREP.hpp").read_text(
    encoding="utf-8"
)
SETTINGS_SRC = (REPO / "addons" / "nightvision" / "initSettings.inc.sqf").read_text(
    encoding="utf-8"
)
STRINGTABLE_SRC = (REPO / "addons" / "nightvision" / "stringtable.xml").read_text(
    encoding="utf-8"
)
POSTINIT_SRC = (REPO / "addons" / "nightvision" / "XEH_postInit.sqf").read_text(
    encoding="utf-8"
)
EVENTS_SRC = (REPO / "addons" / "nightvision" / "CfgEventHandlers.hpp").read_text(
    encoding="utf-8"
)
ALL_LTM_SRC = "\n".join(
    [
        SEGMENT_SRC,
        CREATE_SRC,
        DRAW_SRC,
        PFH_SRC,
        TOGGLE_SRC,
        MODE_SRC,
        INIT_SRC,
    ]
)

COUNT = 21
STEP = 500
ORIGIN = [1000.0, 2000.0, 50.0]
TARGET = [ORIGIN[0] + 10000.0, ORIGIN[1], ORIGIN[2] + 100.0]


def _segments(origin, target, count=COUNT, step=STEP):
    return run_sqf(SEGMENT_KERNEL, [origin, target, count, step], {})


def _on_line(point, a, b, tol=1e-6):
    """Distance from the point to the line a-b, in metres."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    cx = dy * (point[2] - a[2]) - dz * (point[1] - a[1])
    cy = dz * (point[0] - a[0]) - dx * (point[2] - a[2])
    cz = dx * (point[1] - a[1]) - dy * (point[0] - a[0])
    return math.sqrt(cx * cx + cy * cy + cz * cz) < tol


class TestLtmBeamSegments(unittest.TestCase):
    """fnc_ltmBeamSegments, executed: the 21-dash laser line."""

    def test_a_known_line_gives_twenty_one_segments(self):
        self.assertEqual(len(_segments(ORIGIN, TARGET)), 21)

    def test_every_segment_has_two_three_parameter_endpoints(self):
        for seg in _segments(ORIGIN, TARGET):
            with self.subTest(seg=seg):
                self.assertEqual(len(seg), 2)
                self.assertEqual(len(seg[0]), 3)
                self.assertEqual(len(seg[1]), 3)

    def test_every_endpoint_lies_on_the_laser_line(self):
        for seg in _segments(ORIGIN, TARGET):
            for point in seg:
                with self.subTest(point=point):
                    self.assertTrue(_on_line(point, ORIGIN, TARGET))

    def test_the_first_dash_starts_at_the_origin(self):
        seg = _segments(ORIGIN, TARGET)[0]
        for axis in range(3):
            self.assertAlmostEqual(seg[0][axis], ORIGIN[axis], places=6)

    def test_the_dashes_are_evenly_spaced(self):
        starts = [seg[0] for seg in _segments(ORIGIN, TARGET)]
        for i in range(len(starts) - 1):
            with self.subTest(i=i):
                self.assertAlmostEqual(
                    math.dist(starts[i], starts[i + 1]), STEP, places=3
                )

    def test_each_dash_is_the_step_long(self):
        for seg in _segments(ORIGIN, TARGET):
            with self.subTest(seg=seg):
                self.assertAlmostEqual(math.dist(seg[0], seg[1]), STEP, places=3)

    def test_a_null_origin_returns_nothing(self):
        self.assertEqual(_segments([], TARGET), [])

    def test_a_null_target_returns_nothing(self):
        self.assertEqual(_segments(ORIGIN, []), [])

    def test_a_degenerate_line_returns_nothing(self):
        self.assertEqual(_segments(ORIGIN, ORIGIN), [])

    def test_a_zero_count_returns_nothing(self):
        self.assertEqual(_segments(ORIGIN, TARGET, 0, STEP), [])


class TestLtmSourceContract(unittest.TestCase):
    """The engine readers carry the source's mechanisms."""

    def test_the_draw_function_uses_drawline3d(self):
        self.assertIn("drawLine3D", DRAW_SRC)

    def test_the_create_function_reads_the_laser_target(self):
        self.assertIn("laserTarget", CREATE_SRC)

    def test_the_create_function_syncs_the_blink(self):
        self.assertIn("time mod LTM_BLINK_INTERVAL", CREATE_SRC)

    def test_the_pfh_gates_on_night_vision_mode_one(self):
        self.assertIn("currentVisionMode", PFH_SRC)
        self.assertIn("isEqualTo 1", PFH_SRC)

    def test_the_pfh_has_the_interface_guard(self):
        self.assertIn("hasInterface", PFH_SRC)

    def test_no_source_references_a_p3d_asset(self):
        self.assertNotIn(".p3d", ALL_LTM_SRC)

    def test_the_toggle_gates_on_the_air_vehicle_types(self):
        for token in ('"Plane"', '"UAV"', '"Helicopter"', '"LandVehicle"'):
            self.assertIn(token, TOGGLE_SRC, token)

    def test_the_mode_toggle_cycles_blink_and_steady(self):
        self.assertIn("mod 2", MODE_SRC)

    def test_the_init_registers_the_draw_event(self):
        self.assertIn('addMissionEventHandler ["Draw3D"', INIT_SRC)

    def test_the_init_registers_the_vision_mode_event(self):
        self.assertIn('"visionMode"', INIT_SRC)
        self.assertIn("CBA_fnc_addPlayerEventHandler", INIT_SRC)


class TestLtmWiring(unittest.TestCase):
    """The setting, PREP entries, keybinds and postInit wiring exist."""

    def test_prep_registers_every_ltm_function(self):
        for name in (
            "ltmBeamSegments",
            "ltmCreate",
            "ltmDraw",
            "ltmPFH",
            "ltmToggle",
            "ltmToggleMode",
            "ltmInit",
        ):
            self.assertIn(f"PREPS(ltm,{name});", PREP_SRC, name)

    def test_the_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(ltmEnabled,"AEE HUD","Displays",false)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in (
            "ltmEnabled_Name",
            "ltmEnabled_Description",
            "ltmToggle",
            "ltmToggleMode",
        ):
            self.assertIn(f"STR_AEE_NightVision_{key}", STRINGTABLE_SRC)

    def test_the_postinit_has_the_module_guard(self):
        self.assertIn("AEE_MODULE_POST_INIT", POSTINIT_SRC)

    def test_the_postinit_calls_the_ltm_init(self):
        self.assertIn("FUNC(ltmInit)", POSTINIT_SRC)

    def test_the_event_handler_declares_postinit(self):
        self.assertIn("Extended_PostInit_EventHandlers", EVENTS_SRC)

    def test_the_two_keybinds_are_registered(self):
        self.assertIn("CBA_fnc_addKeybind", POSTINIT_SRC)
        self.assertIn('"LTMToggle"', POSTINIT_SRC)
        self.assertIn('"LTMToggleMode"', POSTINIT_SRC)


if __name__ == "__main__":
    unittest.main()
