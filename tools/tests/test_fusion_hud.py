#!/usr/bin/env python3
"""Fusion compass tape tests (port of whale_ecoti_llll).

The fusion HUD display is display-bound: it raises an RscTitles overlay and
writes control positions, so it cannot run headless.  Its source contract is
locked here instead:

  * addons/thermal/RscTitles.hpp declares GVAR(fusionHud) with the source idc
    layout (heading 920001, mark 920002, 13 labels 920011-23, 25 ticks
    920031-55, 8 cardinal letters 920061-68, corners 920101-103).
  * addons/thermal/functions/hud/ holds the ported tape drivers.
  * The drivers read aee data (getEyeState bearing, mapGridPosition, getPosASL,
    dayTime, the aee environment state) and not the source's invented values.
  * The setting, stringtable keys, PREP entries and postInit wiring exist.

Run: python3 -m unittest tools.tests.test_fusion_hud -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


def code_only(src: str) -> str:
    """Strip block and line comments so assertions test code, not prose."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    return src


REPO = Path(__file__).parents[2]
THERMAL = REPO / "addons" / "thermal"
HUD = THERMAL / "functions" / "hud"
RSC_SRC = (THERMAL / "RscTitles.hpp").read_text(encoding="utf-8")
PREP_SRC = (THERMAL / "XEH_PREP.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (THERMAL / "initSettings.inc.sqf").read_text(encoding="utf-8")
STRINGTABLE_SRC = (THERMAL / "stringtable.xml").read_text(encoding="utf-8")
POSTINIT_SRC = (THERMAL / "XEH_postInit.sqf").read_text(encoding="utf-8")

ACTIVE_SRC = (HUD / "fnc_hudTapeActive.sqf").read_text(encoding="utf-8")
BUILD_SRC = (HUD / "fnc_hudTapeBuild.sqf").read_text(encoding="utf-8")
BOOT_SRC = (HUD / "fnc_hudTapeBoot.sqf").read_text(encoding="utf-8")
DRAW_SRC = (HUD / "fnc_hudTapeDraw.sqf").read_text(encoding="utf-8")
INFO_SRC = (HUD / "fnc_hudTapeInfo.sqf").read_text(encoding="utf-8")

ALL_SRC = "\n".join(
    [
        RSC_SRC,
        ACTIVE_SRC,
        BUILD_SRC,
        BOOT_SRC,
        DRAW_SRC,
        INFO_SRC,
    ]
)

FORBIDDEN_PROVENANCE = (
    "Agent:",
    "opencode",
    "claude",
    "anthropic",
    "openai",
    "deepseek",
    "hephaestus",
)


class TestDisplayClass(unittest.TestCase):
    def test_display_class_declared(self) -> None:
        self.assertIn("class GVAR(fusionHud)", RSC_SRC)

    def test_display_stores_handle_on_load(self) -> None:
        self.assertIn("GVAR(fusionHudDisplay) = _this select 0", RSC_SRC)
        self.assertIn("GVAR(fusionHudDisplay) = displayNull", RSC_SRC)

    def test_centre_mark_idc(self) -> None:
        self.assertIn("idc = 920001", RSC_SRC)
        self.assertIn("idc = 920002", RSC_SRC)

    def test_the_source_box_is_restored_as_edges(self) -> None:
        # The source box (idc 910001) is restored as its four EDGES; the old
        # single full-panel fill stays gone.
        self.assertNotIn("AEEFusionHudGlass", RSC_SRC)
        for idc in (910001, 910002, 910003, 910004):
            self.assertIn(f"idc = {idc}", RSC_SRC)

    def test_all_tape_control_idc(self) -> None:
        for base, count in ((920011, 13), (920031, 25), (920061, 8)):
            for i in range(count):
                self.assertIn(f"idc = {base + i}", RSC_SRC)

    def test_corner_readout_idc(self) -> None:
        for idc in (920101, 920102, 920103):
            self.assertIn(f"idc = {idc}", RSC_SRC)

    def test_centring_style_is_in_config(self) -> None:
        # Arma has no ctrlSetStyle, so style = 2 (centre) must be in config.
        self.assertIn("style = 2", RSC_SRC)

    def test_no_raster_asset(self) -> None:
        self.assertNotIn(".paa", ALL_SRC)
        self.assertNotIn(".ogg", ALL_SRC)


class TestDrivers(unittest.TestCase):
    def test_driver_files_exist(self) -> None:
        for name in (
            "fnc_hudTapeActive.sqf",
            "fnc_hudTapeBuild.sqf",
            "fnc_hudTapeBoot.sqf",
            "fnc_hudTapeDraw.sqf",
            "fnc_hudTapeInfo.sqf",
        ):
            self.assertTrue((HUD / name).is_file(), name)

    def test_prep_entries(self) -> None:
        for leaf in (
            "hudTapeActive",
            "hudTapeBuild",
            "hudTapeBoot",
            "hudTapeDraw",
            "hudTapeInfo",
        ):
            self.assertIn(f"PREPS(hud,{leaf})", PREP_SRC)

    def test_build_raises_the_display_class(self) -> None:
        self.assertIn("cutRsc [QGVAR(fusionHud)", BUILD_SRC)
        self.assertIn("cutText", BUILD_SRC)

    def test_draw_uses_aee_bearing(self) -> None:
        self.assertIn("EFUNC(core,getEyeState)", DRAW_SRC)
        self.assertIn("atan2", DRAW_SRC)
        # The source's camera pair is replaced, not duplicated.
        self.assertNotIn("positionCameraToWorld", code_only(DRAW_SRC))

    def test_draw_reads_boot_profile(self) -> None:
        self.assertIn("QGVAR(hudTapeBootProfile)", DRAW_SRC)

    def test_info_uses_aee_data(self) -> None:
        self.assertIn("mapGridPosition", INFO_SRC)
        self.assertIn("getPosASL", INFO_SRC)
        self.assertIn("dayTime", INFO_SRC)
        for var in (
            "currentTemperature",
            "currentHumidity",
            "currentWindStr",
            "currentWindDir",
        ):
            self.assertIn(f"QEGVAR(core,{var})", INFO_SRC)

    def test_info_does_not_invent_lat_lon(self) -> None:
        # The source derived an invented latitude/longitude from the map config.
        code = code_only(INFO_SRC)
        self.assertNotIn("latitude", code)
        self.assertNotIn("longitude", code)

    def test_active_gates_on_fusion(self) -> None:
        self.assertIn("QGVAR(fusionHud)", ACTIVE_SRC)
        self.assertIn("QGVAR(fusionMode)", ACTIVE_SRC)
        self.assertIn("currentVisionMode", ACTIVE_SRC)

    def test_boot_owns_two_flashes(self) -> None:
        self.assertEqual(BOOT_SRC.count("0.10"), BOOT_SRC.count("0.10"))
        self.assertIn("[[0.10, 0.14], [0.40, 0.14]]", BOOT_SRC)

    def test_every_function_has_header_and_include(self) -> None:
        for src in (ACTIVE_SRC, BUILD_SRC, BOOT_SRC, DRAW_SRC, INFO_SRC):
            self.assertIn('#include "..\\..\\script_component.hpp"', src)


class TestIntegration(unittest.TestCase):
    def test_setting_declared(self) -> None:
        self.assertIn("AEE_SETTING_CHECKBOX(fusionHud", SETTINGS_SRC)

    def test_stringtable_keys(self) -> None:
        self.assertIn("STR_AEE_Thermal_fusionHud_Name", STRINGTABLE_SRC)
        self.assertIn("STR_AEE_Thermal_fusionHud_Description", STRINGTABLE_SRC)

    def test_postinit_wires_the_draw_worker(self) -> None:
        self.assertIn('addMissionEventHandler ["Draw3D"', POSTINIT_SRC)
        self.assertIn("FUNC(hudTapeBoot)", POSTINIT_SRC)
        self.assertIn("FUNC(hudTapeDraw)", POSTINIT_SRC)
        self.assertIn("FUNC(hudTapeInfo)", POSTINIT_SRC)
        self.assertIn("CBA_fnc_addPerFrameHandler", POSTINIT_SRC)

    def test_no_provenance(self) -> None:
        lowered = ALL_SRC.lower()
        for token in FORBIDDEN_PROVENANCE:
            self.assertNotIn(token.lower(), lowered)


if __name__ == "__main__":
    unittest.main()
