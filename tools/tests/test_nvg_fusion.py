#!/usr/bin/env python3
"""Fusion gate, device pair and thermal-channel field tests (issue #204).

Executes the REAL SQF kernels through sqf_lite:

  addons/thermal/functions/fusion/fnc_fusionGateDecision.sqf
  addons/thermal/functions/fusion/fnc_fusionThermalField.sqf
  addons/thermal/functions/fusion/fnc_fusionBandIndex.sqf

The engine-reading functions fnc_isFusionCapable, fnc_resolveFusionDevice and
fnc_applyFusionOverlay cannot run without an engine, so their source contract
is locked here instead: the decision must delegate to the kernel, the device
pair must read both channels and the corpus thermal row, and the hardcoded
FOV switch must be gone.  The ECOTI corpus row from Todo 4 is loaded and
checked through the shared catalogue loader.

Run: python3 -m unittest tools.tests.test_nvg_fusion -v
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

from tools.validation import device_catalogue as catalogue  # noqa: E402

FUSION = REPO / "addons" / "thermal" / "functions" / "fusion"
GATE_KERNEL = FUSION / "fnc_fusionGateDecision.sqf"
FIELD_KERNEL = FUSION / "fnc_fusionThermalField.sqf"
BAND_KERNEL = FUSION / "fnc_fusionBandIndex.sqf"
FRAME_KERNEL = FUSION / "fnc_fusionFrameGeometry.sqf"
CAPABLE_SRC = (FUSION / "fnc_isFusionCapable.sqf").read_text(encoding="utf-8")
RESOLVER_SRC = (FUSION / "fnc_resolveFusionDevice.sqf").read_text(encoding="utf-8")
OVERLAY_SRC = (FUSION / "fnc_applyFusionOverlay.sqf").read_text(encoding="utf-8")
FILL_SRC = (FUSION / "fnc_applyFusionFill.sqf").read_text(encoding="utf-8")
UPDATE_SRC = (FUSION / "fnc_updateFusionFrame.sqf").read_text(encoding="utf-8")
PREP_SRC = (REPO / "addons" / "thermal" / "XEH_PREP.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (REPO / "addons" / "thermal" / "initSettings.inc.sqf").read_text(
    encoding="utf-8"
)
RSC_SRC = (REPO / "addons" / "thermal" / "RscTitles.hpp").read_text(encoding="utf-8")
STRINGTABLE_SRC = (REPO / "addons" / "thermal" / "stringtable.xml").read_text(
    encoding="utf-8"
)
CATALOGUE = json.loads(
    (REPO / "data" / "device" / "catalogue" / "thermal_devices.json").read_text(
        encoding="utf-8"
    )
)
DATA_DIR = REPO / "data" / "device"
OPTICS_POSTINIT_SRC = (REPO / "addons" / "optics" / "XEH_postInit.sqf").read_text(
    encoding="utf-8"
)


def _gate(vision_mode: float, has_thermal: bool, always_on: bool) -> bool:
    return bool(run_sqf(GATE_KERNEL, [vision_mode, has_thermal, always_on], {}))


def _field(device_label: str) -> list[object]:
    return run_sqf(FIELD_KERNEL, [device_label], {})


def _band(brightness: float) -> float:
    return run_sqf(BAND_KERNEL, [brightness], {})


def _frame(half_angle_deg: float, nvg_field_deg: float) -> float:
    return run_sqf(FRAME_KERNEL, [half_angle_deg, nvg_field_deg], {})


class TestFusionGateDecision(unittest.TestCase):
    """fnc_fusionGateDecision, executed: the capability matrix."""

    def test_a_thermal_channel_in_nvg_is_capable(self):
        self.assertTrue(_gate(1, True, False))

    def test_a_plain_nvg_is_not_capable(self):
        self.assertFalse(_gate(1, False, False))

    def test_a_non_nvg_mode_is_not_capable(self):
        self.assertFalse(_gate(0, True, False))
        self.assertFalse(_gate(2, True, False))

    def test_fusion_always_on_forces_in_nvg(self):
        self.assertTrue(_gate(1, False, True))

    def test_fusion_always_on_still_needs_the_nvg_base(self):
        self.assertFalse(_gate(0, True, True))
        self.assertFalse(_gate(2, False, True))


class TestFusionThermalField(unittest.TestCase):
    """fnc_fusionThermalField, executed: the device to field table."""

    def test_envgb_is_declared_and_does_not_take_17(self):
        half, source, axis = _field("ENVG-B")
        self.assertEqual(half, 20)
        self.assertEqual(source, "declared")
        self.assertEqual(axis, "declared")
        self.assertNotEqual(half, 17)

    def test_bnvd_fused_is_derived_diagonal_17(self):
        self.assertEqual(_field("BNVD-FUSED"), [17, "derived", "diagonal"])

    def test_ecoti_is_published_circular_15(self):
        self.assertEqual(_field("ECOTI"), [15, "published", "circular"])

    def test_an_unknown_device_takes_the_declared_default(self):
        self.assertEqual(_field("unknown"), [20, "declared", "declared"])


class TestFusionBandIndex(unittest.TestCase):
    """fnc_fusionBandIndex, executed: the 8-bit band map is monotone."""

    def test_the_band_is_monotone_over_the_range(self):
        bands = [_band(index / 32) for index in range(33)]
        self.assertEqual(bands, sorted(bands))
        self.assertEqual(bands[0], 0)
        self.assertEqual(bands[-1], 255)

    def test_the_band_endpoints_and_midpoint(self):
        self.assertEqual(_band(0.0), 0)
        self.assertEqual(_band(0.5), 128)
        self.assertEqual(_band(1.0), 255)

    def test_a_non_finite_input_is_the_darkest_band(self):
        self.assertEqual(_band(float("inf")), 0)
        self.assertEqual(_band(float("nan")), 0)


class TestCapabilitySourceContract(unittest.TestCase):
    """The engine reader delegates the decision to the executed kernel."""

    def test_the_reader_delegates_the_decision(self):
        self.assertIn(
            "[_visionMode, _hasThermal, _alwaysOn] call FUNC(fusionGateDecision)",
            CAPABLE_SRC,
        )

    def test_the_reader_reads_the_engine_state(self):
        for token in (
            "currentVisionMode _unit",
            "hmd _unit",
            'getArray (_cfg >> "visionMode")',
            '"thermalMode"',
            "fusionAlwaysOn",
        ):
            self.assertIn(token, CAPABLE_SRC, token)


class TestResolverSourceContract(unittest.TestCase):
    """The resolver returns both channels and reads the corpus thermal row."""

    def test_the_resolver_reads_both_channels(self):
        self.assertIn("getNvgDeviceProperties", RESOLVER_SRC)
        self.assertIn("getThermalDeviceProperties", RESOLVER_SRC)

    def test_the_resolver_reads_the_corpus_thermal_row(self):
        self.assertIn(
            '[_hmd, "thermal"] call EFUNC(nightvision,getDeviceMatch)', RESOLVER_SRC
        )
        self.assertIn("fusionThermalField", RESOLVER_SRC)

    def test_the_resolver_maps_the_fused_headset_tokens(self):
        self.assertIn('(_x == "nvgogglesb") || (_x == "envg")', RESOLVER_SRC)
        self.assertIn('_deviceLabel = "ENVG-B"', RESOLVER_SRC)
        self.assertIn('_x == "bnvd"', RESOLVER_SRC)
        self.assertIn('_deviceLabel = "BNVD-FUSED"', RESOLVER_SRC)
        self.assertIn('_deviceId == "ecoti"', RESOLVER_SRC)
        self.assertIn('_deviceLabel = "ECOTI"', RESOLVER_SRC)

    def test_the_resolver_returns_the_seven_element_pair(self):
        for token in (
            "_nvgRow",
            "_thermalRow",
            "_field select 0",
            "_field select 1",
            "_field select 2",
            "_deviceLabel",
            "_deviceId",
        ):
            self.assertIn(token, RESOLVER_SRC, token)


class TestOverlayUsesTheResolver(unittest.TestCase):
    """The hardcoded per-device FOV switch is replaced by the resolver."""

    def test_the_hardcoded_fov_switch_is_gone(self):
        self.assertNotIn('case "BNVD-FUSED"', OVERLAY_SRC)
        self.assertNotIn("_DECLARED_HALF_ANGLE_DEG", OVERLAY_SRC)
        self.assertNotIn("_hmdLower", OVERLAY_SRC)

    def test_the_overlay_reads_the_resolved_device_pair(self):
        self.assertIn("[_player] call FUNC(resolveFusionDevice)", OVERLAY_SRC)
        self.assertIn("_devicePair select 2", OVERLAY_SRC)
        self.assertIn("_devicePair select 6", OVERLAY_SRC)


class TestFunctionsAreRegistered(unittest.TestCase):
    def test_prep_registers_the_new_functions(self):
        for name in ("fusionGateDecision", "fusionThermalField", "resolveFusionDevice"):
            self.assertIn(f"PREPS(fusion,{name});", PREP_SRC)


class TestEcotiCorpusRow(unittest.TestCase):
    """The Todo 4 ECOTI row: published values only, no invented NETD."""

    def row(self) -> dict[str, object]:
        entries = CATALOGUE["entries"]
        assert isinstance(entries, list)
        for entry in entries:
            if entry["device_id"] == "ecoti":
                return entry
        raise AssertionError("the ECOTI corpus row is missing")

    def test_the_row_is_the_safran_ecoti(self):
        row = self.row()
        self.assertEqual(row["family"], "thermal")
        self.assertEqual(row["canonical_name"], "Safran Optics 1 ECOTI")
        self.assertEqual(row["maker"], "Safran Optics 1")

    def test_the_published_values_are_present_and_claimed(self):
        values = self.row()["values"]
        assert isinstance(values, dict)
        self.assertEqual(values["resolution_x"]["value"], 640)
        self.assertEqual(values["resolution_y"]["value"], 480)
        self.assertEqual(values["cooled"]["value"], "uncooled")
        self.assertEqual(values["weight_kg"]["value"], 0.125)
        for field in ("resolution_x", "resolution_y", "cooled", "weight_kg"):
            with self.subTest(field=field):
                self.assertEqual(values[field]["source"], "safran_ecoti_datasheet")
                self.assertEqual(values[field]["grade"], "claimed")
                self.assertEqual(
                    values[field]["unit"], catalogue.RUNTIME_FIELD_UNITS[field]
                )

    def test_the_unpublished_netd_is_not_invented_or_borrowed(self):
        values = self.row()["values"]
        assert isinstance(values, dict)
        self.assertNotIn("netd_c", values)
        self.assertNotIn("refresh_hz", values)

    def test_the_corpus_loads_with_no_error(self):
        self.assertEqual(catalogue.load(DATA_DIR).errors, [])


class TestFusionFrameGeometry(unittest.TestCase):
    """fnc_fusionFrameGeometry, executed: the frame is derived, not fixed."""

    def test_envgb_sits_at_the_field_edge(self):
        # ENVG-B: 20-degree channel, declared 40-degree device field.
        self.assertAlmostEqual(_frame(20, 40), 1.0, places=6)

    def test_bnvd_fused_uses_its_derived_half_angle(self):
        self.assertAlmostEqual(
            _frame(17, 40),
            math.tan(math.radians(17)) / math.tan(math.radians(20)),
            places=6,
        )

    def test_ecoti_uses_its_published_half_angle(self):
        self.assertAlmostEqual(
            _frame(15, 40),
            math.tan(math.radians(15)) / math.tan(math.radians(20)),
            places=6,
        )

    def test_the_frame_shrinks_with_the_half_angle(self):
        self.assertLess(_frame(15, 40), _frame(17, 40))
        self.assertLess(_frame(17, 40), _frame(20, 40))

    def test_the_angle_is_not_hardcoded_to_20(self):
        self.assertNotAlmostEqual(_frame(15, 40), _frame(20, 40))
        self.assertAlmostEqual(
            _frame(20, 80),
            math.tan(math.radians(20)) / math.tan(math.radians(40)),
            places=6,
        )

    def test_a_zero_angle_is_an_empty_frame(self):
        self.assertAlmostEqual(_frame(0, 40), 0.0, places=6)

    def test_a_field_wider_than_the_tube_is_clamped(self):
        self.assertAlmostEqual(_frame(45, 40), 1.0, places=6)


class TestFusionFrameWiring(unittest.TestCase):
    """The setting, the config class and the overlay caller are present."""

    def test_the_setting_is_registered_default_on(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(fusionFovFrame,"AEE Experimental","Fusion",true)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in ("fusionFovFrame_Name", "fusionFovFrame_Description"):
            self.assertIn(f"STR_AEE_Thermal_{key}", STRINGTABLE_SRC)

    def test_the_overlay_drives_the_frame_from_the_resolved_angle(self):
        self.assertIn(
            "[_frameOn && _fusionDevice, _thermalHalfAngleDeg, _nvgFieldDeg] call FUNC(updateFusionFrame)",
            OVERLAY_SRC,
        )
        self.assertIn("QGVAR(fusionFovFrame)", OVERLAY_SRC)

    def test_the_frame_is_torn_down_on_exit(self):
        self.assertIn("[false] call FUNC(updateFusionFrame);", OVERLAY_SRC)

    def test_the_display_class_is_owned_by_thermal(self):
        self.assertIn("class GVAR(fusionFrame)", RSC_SRC)
        self.assertIn("GVAR(fusionFrameDisplay)", RSC_SRC)

    def test_the_driver_reads_the_geometry_kernel(self):
        self.assertIn("call FUNC(fusionFrameGeometry)", UPDATE_SRC)

    def test_prep_registers_the_frame_functions(self):
        for name in ("fusionFrameGeometry", "updateFusionFrame"):
            self.assertIn(f"PREPS(fusion,{name});", PREP_SRC)


class TestFusionSolidFill(unittest.TestCase):
    """The solid fill: aee data in, source save/restore discipline kept."""

    def test_the_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(fusionSolidFill,"AEE Experimental","Fusion",false)',
            SETTINGS_SRC,
        )

    def test_the_stringtable_keys_exist(self):
        for key in ("fusionSolidFill_Name", "fusionSolidFill_Description"):
            self.assertIn(f"STR_AEE_Thermal_{key}", STRINGTABLE_SRC)

    def test_prep_registers_the_fill(self):
        self.assertIn("PREPS(fusion,applyFusionFill);", PREP_SRC)

    def test_the_fill_reads_our_heat_list_and_field_gate(self):
        for token in (
            "call FUNC(outlineCollect)",
            "call FUNC(fusionFovGate)",
            "call FUNC(resolveFusionDevice)",
            "getEyeState",
        ):
            self.assertIn(token, FILL_SRC, token)

    def test_the_fill_keeps_the_source_save_and_restore(self):
        for token in (
            "getObjectTextures",
            "hiddenSelectionsTextures",
            "setObjectTexture",
            "QGVAR(fusionFillReg)",
            "QGVAR(fusionFillSig)",
            "fusionFillTexApplied",
        ):
            self.assertIn(token, FILL_SRC, token)

    def test_the_fill_has_the_exit_restore(self):
        self.assertIn('if (_mode == "EXIT") exitWith {', FILL_SRC)
        self.assertIn("restored %1 bodies on exit", FILL_SRC)

    def test_the_fill_carries_no_source_state_namespace(self):
        # The source mod is cited in the header.  What must not survive is the
        # source's own runtime state (missionNamespace variables and mode keys).
        for token in (
            "whale_ecoti_llll_mode",
            "whale_ecoti_llll_on",
            "whale_ecoti_llll_fillReg",
            "whale_ecoti_llll_fillSig",
            'missionNamespace setVariable ["whale',
        ):
            self.assertNotIn(token, FILL_SRC)

    def test_the_overlay_hands_over_and_restores_the_fill(self):
        self.assertIn("QGVAR(fusionSolidFill)", OVERLAY_SRC)
        self.assertIn("if (_fillOn) exitWith {", OVERLAY_SRC)
        self.assertIn("[_player] call FUNC(applyFusionFill)", OVERLAY_SRC)
        self.assertIn('[_player, "EXIT"] call FUNC(applyFusionFill)', OVERLAY_SRC)

    def test_the_fill_replaces_the_ladder_rather_than_stacking(self):
        # The fill branch must exit before the emissive sweep, so one body is
        # never painted by both the ladder and the solid texture.
        fill_at = OVERLAY_SRC.index("if (_fillOn) exitWith {")
        sweep_at = OVERLAY_SRC.index("call FUNC(takeThermalSweep)")
        self.assertLess(fill_at, sweep_at)


class TestFusionRestoreOnGateOff(unittest.TestCase):
    """Every gate-off transition restores what fusion painted.

    ROOT CAUSE.  The source's fn_thermalFill runs on EVERY Draw3D frame
    (fn_postInit.sqf:19) and pass 1 restores every registered body once _want
    is false (fn_thermalFill.sqf:76-96), so a painted body can never outlive
    the gate.  aee drives fnc_applyFusionOverlay from the sensor PFH, which
    only runs while vision mode is 1.  The PFH's own gate can drop while it
    stays alive - a switch to thermal (vision mode 2), a device that stops
    being fusion-capable, or fusion switched off - and the PFH never called
    the restore, so the painted setObjectTexture (solid fill) and
    setObjectMaterial (emissive ladder) stayed on the world.  The PFH now
    restores on every gate-off transition, and teardownSensors still owns the
    genuine return to normal vision, death and respawn.
    """

    def test_the_dirty_test_reads_both_registries(self):
        self.assertIn("QEGVAR(thermal,fusionFillReg)", OPTICS_POSTINIT_SRC)
        self.assertIn("QEGVAR(thermal,fusionOverlaySaved)", OPTICS_POSTINIT_SRC)

    def test_a_non_nvg_vision_mode_restores(self):
        # vision mode 2 (thermal) and any other non-NVG mode.
        self.assertIn("if ((_vm != 1) && _fusionDirty) then {", OPTICS_POSTINIT_SRC)

    def test_every_gate_off_branch_calls_the_exit_restore(self):
        # Three branches: not vision mode 1, capable but mode off, and the
        # device no longer fusion-capable.
        self.assertEqual(
            OPTICS_POSTINIT_SRC.count(
                '[_player, "EXIT"] call EFUNC(thermal,applyFusionOverlay);'
            ),
            3,
        )

    def test_the_restore_is_not_reached_when_fusion_is_active(self):
        # The dirty restore must sit behind the active check, so a fused tick
        # is never torn down.  The vm==1 && capable && mode==1 path paints.
        self.assertIn("[] call EFUNC(thermal,applyFusionOverlay);", OPTICS_POSTINIT_SRC)
        self.assertIn("[true] call EFUNC(thermal,outlineToggle);", OPTICS_POSTINIT_SRC)

    def test_the_overlay_exit_is_the_single_restore_owner(self):
        # Both registries are restored by the one EXIT block: the fill by its
        # own EXIT call and the ladder by the saved-material loop.
        self.assertIn('[_player, "EXIT"] call FUNC(applyFusionFill);', OVERLAY_SRC)
        self.assertIn("QGVAR(fusionOverlaySaved)", OVERLAY_SRC)

    def test_the_fill_exit_restore_does_not_need_a_live_player(self):
        # The restore runs before the isNull guard, so a dead or changed unit
        # still restores.  Order is the contract.
        exit_at = FILL_SRC.index('if (_mode == "EXIT") exitWith {')
        null_at = FILL_SRC.index("if (isNull _player) exitWith {};")
        self.assertLess(exit_at, null_at)


if __name__ == "__main__":
    unittest.main()
