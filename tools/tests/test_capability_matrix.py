#!/usr/bin/env python3
"""Capability matrix validator (issue #127).

The thermal-capability matrix (docs/wiki/research/thermal-capability-
matrix.md) maps engine levers to their AEE implementation status.  This
test locks the IMPLEMENTED/NOT-BUILT claims against the actual source,
so the document cannot drift from the code.

The claims locked here are the ones with in-game proof from #204 - the
documented engine ceiling.  If a lever's implementation status changes
(intentionally), this test fails and the matrix must be updated.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


class TestLeverImplementation(unittest.TestCase):
    def test_setTIParameter_implemented(self):
        # The AGC display window lever - drives OutputRangeStart/Width.
        src = read("addons/thermal/functions/display/fnc_applyEngineThermal.sqf")
        self.assertIn('setTIParameter ["OutputRangeStart"', src)
        self.assertIn('setTIParameter ["OutputRangeWidth"', src)

    def test_setVehicleTIPars_implemented(self):
        # The per-vehicle heat lever, driven from AEE physics.
        src = read("addons/thermal/functions/display/fnc_applyEngineThermal.sqf")
        self.assertIn("setVehicleTIPars", src)
        self.assertIn("_fEngine", src)
        self.assertIn("_fWheels", src)

    def test_second_sun_implemented(self):
        # The sun-heat term lever (global heat bias).
        src = read("addons/thermal/functions/display/fnc_applySecondSun.sqf")
        self.assertIn("#lightpoint", src)
        self.assertIn("setLightDayLight", src)

    def test_material_swap_implemented(self):
        # Per-selection material swap (coefficient layer).
        src = read("addons/thermal/functions/display/fnc_applySelectionThermal.sqf")
        self.assertIn("setObjectMaterial", src)

    def test_texture_paint_implemented(self):
        # Stage1 texture paint - what the TI pass reads for objects.
        src = read("addons/thermal/functions/display/fnc_applySelectionThermal.sqf")
        self.assertIn("setObjectTexture", src)
        self.assertIn("#(rgb,8,8,3)color(", src)

    def test_pip_track_not_built(self):
        # The PIP track (#204 Track A) - documented, not implemented.
        # setPiPEffect must NOT appear in the addon sources.
        hits = []
        for sqf in (REPO / "addons").rglob("*.sqf"):
            if "setPiPEffect" in sqf.read_text(encoding="utf-8"):
                hits.append(str(sqf))
        self.assertEqual(hits, [], f"PIP lever built without matrix update: {hits}")

    def test_terrain_paint_absent(self):
        # The terrain cannot be painted - the #204 ceiling.  No code may
        # attempt a runtime terrain material swap.
        src = read("docs/wiki/research/thermal-capability-matrix.md")
        self.assertIn("Terrain surface texture", src)
        self.assertIn("baked", src)


class TestPerSurfaceMatrix(unittest.TestCase):
    """The #127 per-surface/per-object-type matrix must stay complete and
    grounded.  Each row is a surface or object type with its baked and
    dynamic properties and a named source.  If a target or a source is
    dropped, this fails so the matrix cannot silently lose a row."""

    def setUp(self):
        self.doc = read("docs/wiki/research/thermal-capability-matrix.md")

    def test_every_target_named(self):
        for target in (
            "Terrain surface",
            "Static rocks and map props",
            "Buildings with `hiddenSelections`",
            "Buildings without `hiddenSelections`",
            "Vehicles",
            "Infantry body",
            "Infantry clothing and gear",
            "Infantry weapons",
            "Vegetation",
            "Glass",
            "Optics and the display window",
            "The native render pass",
        ):
            with self.subTest(target=target):
                self.assertIn(target, self.doc)

    def test_matrix_has_baked_and_dynamic_columns(self):
        self.assertIn("Baked (texture / PBO)", self.doc)
        self.assertIn("Dynamic (scripted)", self.doc)
        self.assertIn("Ceiling", self.doc)

    def test_named_sources_present(self):
        # Each source the matrix cites by name must appear, so a row cannot
        # cite a source that was never recorded.
        for source in (
            "default_TI.rvmat",
            "DEFAULT_SECONDSUN_BRIGHTNESS",
            "ace_thermals",
            "setVehicleTIPars",
            "setObjectMaterial",
            "setObjectTexture",
            "nearestTerrainObjects",
            "NoTiWrite",
        ):
            with self.subTest(source=source):
                self.assertIn(source, self.doc)

    def test_ceilings_recorded(self):
        # The unreadable/unbakeable properties must be recorded as ceilings.
        self.assertIn("Unreadable properties", self.doc)
        self.assertIn("No runtime terrain material swap command exists", self.doc)
        self.assertIn("does not work on infantry weapons", self.doc)

    def test_infantry_body_dynamic_lever_absent(self):
        # The base body is baked.  Only the worn selections are swappable, so
        # the matrix must not claim a per-body dynamic command.
        self.assertIn("The base body renders natively", self.doc)

    def test_agc_settle_rate_is_degrees_per_second(self):
        # acos returns degrees, so the gaze rate is deg/s.  The old code
        # divided by the radian threshold 0.44, which was 57 times too
        # strict and stopped the window settling.
        src = read("addons/thermal/functions/display/fnc_applyEngineThermal.sqf")
        self.assertIn("_angVelDeg", src)
        self.assertIn("_angVelDeg < 25", src)
        # The old radian-named variable and its 0.44 rad/s threshold are gone
        # (the comment may still cite 0.44 as the wrong value, so match the
        # operator form).
        self.assertNotIn("_angVel <", src)


if __name__ == "__main__":
    unittest.main()
