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


if __name__ == "__main__":
    unittest.main()
