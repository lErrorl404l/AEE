#!/usr/bin/env python3
"""MKK thermal-display adoption checks.

The mechanisms are ported from MKK thermal_improvement (workshop
3753145363): the rain lens-film WetDistortion, the sensor pixelation
Resolution effect, and the isotherm/highlight palette modes.  These
tests execute the REAL pure kernels with the shared SQF interpreter and
check the wiring contracts in fnc_applyThermalVision.

Run: python3 -m unittest tools.tests.test_thermal_display_mkk -v
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
_DISPLAY = REPO / "addons" / "thermal" / "functions" / "display"
_WET = _DISPLAY / "fnc_thermalWetDistortionParams.sqf"
_RES = _DISPLAY / "fnc_thermalResolutionParams.sqf"
_PALETTE = _DISPLAY / "fnc_thermalPalette.sqf"
_VISION = _DISPLAY / "fnc_applyThermalVision.sqf"
_CREATE = _DISPLAY / "fnc_createThermalPPEffects.sqf"
_PREP = REPO / "addons" / "thermal" / "XEH_PREP.hpp"
_SETTINGS = REPO / "addons" / "thermal" / "initSettings.inc.sqf"

# The engine's fixed WetDistortion coefficients (BIKI Post Process Effects,
# WetDistortion defaults), identical to the MKK vector tail.
_WET_TAIL = [4.10, 3.70, 2.50, 1.85, 0.0054, 0.0041, 0.0090, 0.0070, 0.5, 0.3, 10, 6]
_MKK_AMP = 0.08  # MKK shipped vehicle config (CfgVehicles.hpp:128)


class TestWetDistortionKernel(unittest.TestCase):
    """fnc_thermalWetDistortionParams: the rain-on-lens parameter builder."""

    def _run(self, wetness, max_amp=None):
        args = [wetness] if max_amp is None else [wetness, max_amp]
        return run_sqf(_WET, args, {})

    def test_dry_is_a_neutral_vector(self):
        v = self._run(0)
        self.assertEqual(len(v), 15)
        self.assertEqual(v[:3], [0, 0, 0])

    def test_full_wet_is_the_mkk_vector(self):
        v = self._run(1)
        self.assertEqual(v[:3], [_MKK_AMP, _MKK_AMP, _MKK_AMP])
        self.assertEqual(v[3:], _WET_TAIL)

    def test_monotone_in_rain(self):
        firsts = [self._run(r)[0] for r in (0, 0.25, 0.5, 0.75, 1.0)]
        self.assertEqual(firsts, sorted(firsts))
        self.assertGreater(firsts[-1], firsts[0])

    def test_zero_amplitude_disables(self):
        self.assertEqual(self._run(1, 0)[:3], [0, 0, 0])

    def test_wetness_is_clamped(self):
        self.assertEqual(self._run(2)[:3], self._run(1)[:3])
        self.assertEqual(self._run(-1)[:3], [0, 0, 0])

    def test_custom_max_amplitude_scales_the_first_three(self):
        v = self._run(0.5, 0.4)
        self.assertAlmostEqual(v[0], 0.2)
        self.assertAlmostEqual(v[2], 0.2)
        self.assertEqual(v[3:], _WET_TAIL)


class TestResolutionKernel(unittest.TestCase):
    """fnc_thermalResolutionParams: detector height -> the engine argument."""

    def test_pas13_v1_320x240(self):
        self.assertEqual(run_sqf(_RES, [320, 240], {}), [240])

    def test_envgb_640x480(self):
        self.assertEqual(run_sqf(_RES, [640, 480], {}), [480])

    def test_cooled_1280x1024(self):
        self.assertEqual(run_sqf(_RES, [1280, 1024], {}), [1024])

    def test_absent_device_is_disabled(self):
        self.assertEqual(run_sqf(_RES, [0, 0], {}), [])

    def test_negative_height_is_disabled(self):
        self.assertEqual(run_sqf(_RES, [640, -1], {}), [])


class TestIsothermPalettes(unittest.TestCase):
    """fnc_thermalPalette: the MKK isotherm/highlight modes."""

    # MKK _getHighlightBaseColor (fnc_setThermalMaterials.sqf:112-119).
    HUES = {
        2: [1, 0.10, 0.08],  # ISOTHERM_RED
        3: [0.10, 1, 0.12],  # ISOTHERM_GREEN
        4: [1, 0.82, 0.10],  # ISOTHERM_YELLOW
        5: [1, 0.10, 1],  # ISOTHERM_MAGENTA
        6: [1, 0.52, 0.20],  # PALETTE_SEPIA
    }

    def _run(self, n, palette, polarity=0):
        return run_sqf(_PALETTE, [n, palette, polarity], {})

    def test_below_the_window_midpoint_is_cold(self):
        for palette in self.HUES:
            self.assertEqual(self._run(0.2, palette), [0, 0, 0], f"palette {palette}")

    def test_at_or_above_the_midpoint_takes_the_mkk_hue(self):
        for palette, hue in self.HUES.items():
            self.assertEqual(self._run(1.0, palette), hue, f"palette {palette}")

    def test_polarity_flips_the_threshold(self):
        self.assertEqual(self._run(0.0, 2, 1), [1, 0.10, 0.08])
        self.assertEqual(self._run(1.0, 2, 1), [0, 0, 0])

    def test_ember_and_grey_are_unchanged(self):
        self.assertEqual(self._run(0.0, 0), [0.0, 0.0, 0.0])
        self.assertEqual(self._run(1.0, 0), [1.0, 1.0, 1.0])
        self.assertEqual(self._run(0.0, 1), [0.0, 0.0, 0.0])
        self.assertEqual(self._run(1.0, 1), [1.0, 1.0, 1.0])


def _code_only(text):
    """Strip SQF comments so a source lock cannot match header prose."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestMKKDisplayWiring(unittest.TestCase):
    """The adopted effects are wired into the live thermal stack."""

    @classmethod
    def setUpClass(cls):
        cls.vision = _VISION.read_text(encoding="utf-8")
        # The create table moved off the per-entry path into its own function
        # (the first-entry stall fix); read both so the wiring is checked.
        cls.create = _CREATE.read_text(encoding="utf-8")
        cls.prep = _PREP.read_text(encoding="utf-8")
        cls.settings = _SETTINGS.read_text(encoding="utf-8")

    def test_wet_distortion_is_created(self):
        self.assertIn(
            '["WetDistortion",    305, QGVAR(ppHandle_Thermal_WetDistortion)]',
            self.create,
        )

    def test_resolution_is_created(self):
        self.assertIn(
            '["Resolution",      3000, QGVAR(ppHandle_Thermal_Resolution)]',
            self.create,
        )

    def test_kernels_are_called_from_the_driver(self):
        self.assertIn("call FUNC(thermalWetDistortionParams)", self.vision)
        self.assertIn("call FUNC(thermalResolutionParams)", self.vision)

    def test_wet_driver_reads_aee_weather(self):
        # The amplitude is driven by AEE's own rain and fog state.
        self.assertIn("getSmoothedWeather", self.vision)
        self.assertIn("EGVAR(core,currentFogDensity)", self.vision)

    def test_resolution_driver_reads_the_aee_device_resolver(self):
        self.assertIn("EFUNC(thermal,getThermalDeviceProperties)", self.vision)
        self.assertIn("_device select 1", self.vision)

    def test_new_handles_are_torn_down_and_reenabled(self):
        # Read, create, destroy-on-recreate, teardown and the ppOn disable
        # list must all name the new handles.  The create table now lives in
        # fnc_createThermalPPEffects; the teardown and the ppOn list stay in
        # the driver, so count across both files.
        combined = self.create + self.vision
        self.assertGreaterEqual(combined.count("ppHandle_Thermal_WetDistortion"), 4)
        self.assertGreaterEqual(combined.count("ppHandle_Thermal_Resolution"), 4)

    def test_priorities_are_unique_across_the_stacks(self):
        files = [
            "addons/optics/functions/vision/fnc_managePostProcess.sqf",
            "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf",
            "addons/thermal/functions/display/fnc_createThermalPPEffects.sqf",
        ]
        seen = {}
        for rel in files:
            text = (REPO / rel).read_text(encoding="utf-8")
            for m in re.finditer(r'\["(\w+)",\s*(\d+)', text):
                effect, prio = m.group(1), int(m.group(2))
                self.assertNotIn(prio, seen, f"priority collision: {prio} in {rel}")
                seen[prio] = f"{rel}:{effect}"

    def test_prep_registers_the_kernels(self):
        self.assertIn("PREPS(display,thermalWetDistortionParams);", self.prep)
        self.assertIn("PREPS(display,thermalResolutionParams);", self.prep)

    def test_settings_are_registered(self):
        self.assertIn("thermalWetDistortion", self.settings)
        self.assertIn("thermalPixelation", self.settings)

    def test_palette_setting_offers_the_isotherm_modes(self):
        self.assertIn("Isotherm red", self.settings)
        self.assertIn("Sepia", self.settings)

    def test_no_mkk_binary_asset_is_referenced(self):
        for path in (_WET, _RES):
            text = path.read_text(encoding="utf-8")
            for ext in (".paa", ".rvmat", ".p3d", ".ogg"):
                self.assertNotIn(ext, text, f"{path.name} references {ext}")
        # The palette edit is pure numbers; strip its header prose first.
        palette = _code_only(_PALETTE.read_text(encoding="utf-8"))
        for ext in (".paa", ".rvmat", ".p3d", ".ogg"):
            self.assertNotIn(ext, palette, f"fnc_thermalPalette code references {ext}")


if __name__ == "__main__":
    unittest.main()
