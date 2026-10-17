#!/usr/bin/env python3
"""The thermal-host stand-down gate and its declared dependency.

Three fixes landed together and this suite pins them without a game:

1. The five normal-vision drivers stand down while the thermal host owns the
   image on the DTV day channel (vision mode 0).  Each driver must ask the
   thermal host predicate as well as the vision mode, or the sensor frame is
   repainted by the optical path (issue #299).
2. A handle variable is never reset to -1 while its engine effect is live.  The
   vision-mode handler destroys a live handle before it clears the store, or
   the engine effect is orphaned.
3. A cross-addon call is declared in CfgPatches requiredAddons.  The repo-wide
   dependency test is scoped to optics, ballistics and wildlife, so the thermal
   dependency that the vision, nightvision and optics drivers now carry is
   pinned here.

Run: python3 -m unittest tools.tests.test_pp_thermal_host_gate
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# The five normal-vision drivers that must stand down under the thermal host.
DRIVERS = (
    "vision/functions/vision/fnc_managePostProcess.sqf",
    "vision/functions/grade/fnc_applyBaseGrade.sqf",
    "vision/functions/vision/fnc_applyWeatherGrain.sqf",
    "nightvision/functions/fnc_applyNightGrain.sqf",
    "optics/functions/fx/fnc_applySolarGlareFX.sqf",
)

# The addons whose sources call into the thermal component.
THERMAL_CALLERS = ("vision", "nightvision", "optics")

VISION_MODE_HANDLER = ADDONS / "vision" / "XEH_postInit.sqf"

_CALL = re.compile(r"EFUNC\(\s*([a-z_]+)\s*,")
_REQUIRED_BLOCK = re.compile(r"requiredAddons\[\]\s*=\s*\{(.*?)\}", re.DOTALL)
_RESET = re.compile(r"setVariable\s*\[\s*_x\s*,\s*-1\s*\]")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


class TestThermalHostStandDown(unittest.TestCase):
    def test_each_driver_asks_the_thermal_host(self):
        for rel in DRIVERS:
            text = _read(ADDONS / rel)
            self.assertIn(
                "isThermalHostActive",
                text,
                f"{rel} does not stand down under the thermal host (issue #299)",
            )

    def test_the_driver_call_is_declared(self):
        for addon in THERMAL_CALLERS:
            text = _read(ADDONS / addon / "config.cpp")
            match = _REQUIRED_BLOCK.search(text)
            declared = set(re.findall(r'"([^"]+)"', match.group(1))) if match else set()
            calls_thermal = any(
                "thermal" in _CALL.findall(_read(path))
                for path in (ADDONS / addon).rglob("*.sqf")
            )
            if calls_thermal:
                self.assertIn(
                    "aee_thermal",
                    declared,
                    f"{addon} calls into thermal but does not list aee_thermal "
                    "in requiredAddons",
                )


class TestVisionModeResetLifecycle(unittest.TestCase):
    def test_a_live_handle_is_destroyed_before_its_store_is_cleared(self):
        lines = _read(VISION_MODE_HANDLER).splitlines()
        for index, line in enumerate(lines):
            if not _RESET.search(line):
                continue
            window = "\n".join(lines[max(0, index - 6) : index])
            self.assertIn(
                "ppEffectDestroy",
                window,
                "a handle store is set to -1 without a destroy in the same "
                f"branch: line {index + 1} of {VISION_MODE_HANDLER.name}",
            )


if __name__ == "__main__":
    unittest.main()
