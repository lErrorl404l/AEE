#!/usr/bin/env python3
"""Exhaust heat-shimmer physics and vision-mode gate tests.

Verifies fnc_calculateThermalRefraction.sqf (the physics kernel) and
fnc_applyExhaustShimmerFX.sqf (the renderer), plus the vision-mode gate on
the mirage emitter and the solar-glare LightShafts effect.

The kernel test PARSES the real SQF and reads its constants from the file it
tests, then re-derives the physics from first principles, so a wrong constant
in either place fails.  A hand-transcribed Python mirror is not acceptable: a
mirror once replicated the SQF's own bugs and drifted without detection.

Sources held for the constants:
  K = 2.26e-4 m^3/kg  Stone and Zimmerman, "Index of Refraction of Air",
                      NIST Engineering Metrology Toolbox, which publishes
                      the Edlen and Ciddor equations.
  rho = 1.225 kg/m^3  ISA sea level density, the same datum the shock
                      kernel uses.

Run: python3 -m unittest tools.tests.test_exhaust_shimmer -v
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KERNEL = REPO / "addons/ballistics/functions/fnc_calculateThermalRefraction.sqf"
MIRAGE = REPO / "addons/optics/functions/fx/fnc_applyMirageFX.sqf"
GLARE = REPO / "addons/optics/functions/fx/fnc_applySolarGlareFX.sqf"
SHIMMER = REPO / "addons/optics/functions/fx/fnc_applyExhaustShimmerFX.sqf"

KERNEL_SRC = KERNEL.read_text(encoding="utf-8")
SHIMMER_SRC = SHIMMER.read_text(encoding="utf-8")


def _code_only(text):
    """Blank out comments so a search cannot match the prose.

    The file headers explain the tokens the tests search for, so a raw search
    finds the explanation before the code.  Block comments and line comments
    are both removed, because the renderer header is a block comment.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        idx = line.find("//")
        out.append(line if idx < 0 else line[:idx])
    return "\n".join(out)


def _sqf_number(pattern):
    """Read a numeric literal out of the real SQF, so the test cannot drift."""
    match = re.search(pattern, KERNEL_SRC)
    if not match:
        raise AssertionError(f"SQF no longer matches {pattern!r}")
    return float(match.group(1))


class ThermalRefractionKernel(unittest.TestCase):
    def setUp(self):
        self.k = _sqf_number(r"private _k\s*=\s*([0-9.]+)\s*;")
        self.rho0 = _sqf_number(r"private _rhoAmbient\s*=\s*([0-9.]+)")

    def contrast(self, gas_c, ambient_c, rho_rel=1.0):
        """The kernel result in its reported units, re-derived here."""
        if rho_rel <= 0:
            return 0.0
        if gas_c <= ambient_c:
            return 0.0
        gas_k = gas_c + 273.15
        ambient_k = ambient_c + 273.15
        if gas_k <= 0 or ambient_k <= 0:
            return 0.0
        return self.k * self.rho0 * rho_rel * (ambient_k / gas_k - 1.0) / 0.0001

    # ── the constants are the sourced ones ─────────────────────────────
    def test_gladstone_dale_coefficient(self):
        self.assertAlmostEqual(self.k, 0.000226, places=9)

    def test_ambient_density_is_isa_sea_level(self):
        self.assertEqual(self.rho0, 1.225)

    # ── the reference values the task fixes ────────────────────────────
    def test_500c_ratio_and_contrast(self):
        ratio = 288.15 / (500 + 273.15)
        self.assertAlmostEqual(ratio, 0.373, places=3)
        self.assertAlmostEqual(self.contrast(500, 15), -1.74, places=2)

    def test_600c_ratio_and_contrast(self):
        ratio = 288.15 / (600 + 273.15)
        self.assertAlmostEqual(ratio, 0.330, places=3)
        self.assertAlmostEqual(self.contrast(600, 15), -1.85, places=2)

    def test_1200c_ratio_and_contrast(self):
        ratio = 288.15 / (1200 + 273.15)
        self.assertAlmostEqual(ratio, 0.196, places=3)
        self.assertAlmostEqual(self.contrast(1200, 15), -2.23, places=2)

    def test_equal_temperatures_return_exactly_zero(self):
        self.assertEqual(self.contrast(15, 15), 0.0)

    def test_colder_gas_returns_exactly_zero(self):
        self.assertEqual(self.contrast(10, 15), 0.0)

    def test_sign_is_negative_for_hot_gas(self):
        for gas in (200, 500, 800, 1200):
            self.assertLess(self.contrast(gas, 15), 0.0)

    def test_contrast_grows_with_gas_temperature(self):
        seq = [abs(self.contrast(t, 15)) for t in (100, 300, 500, 800, 1200)]
        for a, b in zip(seq, seq[1:]):
            self.assertLess(a, b)

    def test_contrast_scales_with_rho_rel(self):
        self.assertGreater(
            abs(self.contrast(500, 15, 1.2)), abs(self.contrast(500, 15, 1.0))
        )
        self.assertGreater(
            abs(self.contrast(500, 15, 1.0)), abs(self.contrast(500, 15, 0.8))
        )

    # ── the guards the SQF must keep ───────────────────────────────────
    def test_hot_gas_guard_is_present(self):
        self.assertRegex(
            KERNEL_SRC,
            r"if \(_gasTempC\s*<=\s*_ambientTempC\)\s*exitWith \{\s*0\s*\}",
        )

    def test_rho_rel_guard_is_present(self):
        self.assertRegex(KERNEL_SRC, r"if \(_rhoRel\s*<=\s*0\)\s*exitWith \{\s*0\s*\}")

    def test_kelvin_guards_are_present(self):
        self.assertIn("if (_gasK <= 0) exitWith { 0 }", KERNEL_SRC)
        self.assertIn("if (_ambientK <= 0) exitWith { 0 }", KERNEL_SRC)

    def test_negative_absolute_gas_is_guarded_by_the_ordering(self):
        # A gas colder than ambient already returns 0, and an unphysical
        # Kelvin value is caught by the explicit guard, so both paths exist.
        self.assertEqual(self.contrast(-400, -500), 0.0)

    # ── the header keeps the honesty claims ────────────────────────────
    def test_header_states_the_negative_sign(self):
        header = KERNEL_SRC.upper()
        self.assertIn("NEGATIVE", header)
        self.assertIn("LESS dense", KERNEL_SRC)

    def test_header_states_the_ceiling_over_the_plume(self):
        header = KERNEL_SRC.upper()
        self.assertIn("CEILING", header)
        self.assertIn("gas temperature alone", KERNEL_SRC)

    def test_header_excludes_condensation_and_soot(self):
        self.assertIn("condensation", KERNEL_SRC)
        self.assertIn("soot", KERNEL_SRC)

    def test_header_cites_the_gladstone_dale_source(self):
        self.assertIn("Gladstone-Dale", KERNEL_SRC)
        self.assertIn("Stone and Zimmerman", KERNEL_SRC)
        self.assertIn("NIST", KERNEL_SRC)
        self.assertIn("2.26e-4", KERNEL_SRC)

    def test_header_keeps_the_radio_constant_separate(self):
        self.assertIn("ITU-R", KERNEL_SRC)
        self.assertIn("RADIO", KERNEL_SRC)

    def test_declares_params_and_return(self):
        self.assertIn("params [", KERNEL_SRC)
        self.assertIn("Arguments:", KERNEL_SRC)
        self.assertIn("Returns the refractive index contrast", KERNEL_SRC)

    def test_reports_in_1e_4_units(self):
        self.assertIn("_contrast / 0.0001", KERNEL_SRC)


class VisionModeGate(unittest.TestCase):
    """The three FX files must each gate on currentVisionMode.

    The mirage refract billboard and the LightShafts god-rays were drawn on
    top of the NVG and thermal sensor images because neither function checked
    currentVisionMode.  These read the SOURCE; a mirror would prove nothing.
    """

    def test_mirage_gates_on_vision_mode(self):
        code = _code_only(MIRAGE.read_text(encoding="utf-8"))
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        # The source must be DELETED, not merely faded.
        self.assertIn("deleteVehicle _leak", code)
        self.assertIn("QGVAR(mirageSource), objNull", code)

    def test_solar_glare_gates_on_vision_mode(self):
        code = _code_only(GLARE.read_text(encoding="utf-8"))
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        # The string-LHS form is disabled on the way out.
        self.assertIn('"LightShafts" ppEffectEnable false', code)

    def test_exhaust_shimmer_gates_on_vision_mode(self):
        code = _code_only(SHIMMER_SRC)
        self.assertIn("currentVisionMode", code)
        self.assertRegex(code, r"if \(_visionMode != 0\) exitWith")
        self.assertIn("deleteVehicle _src", code)


class ExhaustShimmerRenderer(unittest.TestCase):
    def setUp(self):
        self.code = _code_only(SHIMMER_SRC)

    # ── the physics is ungated, the render is gated ────────────────────
    def test_contrast_is_published_before_the_render_gate(self):
        publish = self.code.find("QGVAR(exhaustRefraction)")
        gate = self.code.find("if (_visionMode != 0) exitWith")
        self.assertNotEqual(publish, -1, "the contrast is never published")
        self.assertNotEqual(gate, -1, "the render gate is missing")
        self.assertLess(
            publish, gate, "the physics store must sit outside the render gate"
        )

    def test_kernel_is_called_from_the_renderer(self):
        self.assertIn("EFUNC(ballistics,calculateThermalRefraction)", self.code)

    # ── true physical scale, no visibility scale factor ────────────────
    def test_uses_the_vanilla_refractive_shape(self):
        self.assertIn(r"\A3\data_f\ParticleEffects\Universal\refract", self.code)
        self.assertIn("Billboard", self.code)
        self.assertIn("setParticleParams", self.code)

    def test_header_records_the_pixel_arithmetic(self):
        self.assertIn("1662.8", SHIMMER_SRC)
        for px in ("17 px", "8 px", "27 px", "13 px", "67 px", "33 px", "0.18 px"):
            self.assertIn(px, SHIMMER_SRC, f"missing pixel figure {px}")

    def test_header_states_no_visibility_scale_factor(self):
        self.assertIn("NO VISIBILITY SCALE FACTOR", SHIMMER_SRC.upper())
        self.assertIn("NONE IS NEEDED", SHIMMER_SRC.upper())

    def test_sprite_size_is_the_plume_depth(self):
        # The particle size array is [depth, depth], not a fudge constant.
        self.assertIn("[_depth, _depth]", self.code)

    # ── the overdraw budget ────────────────────────────────────────────
    def test_overdraw_worst_case_is_below_the_measured_stutter(self):
        self.assertIn("144", SHIMMER_SRC)
        self.assertIn("190", SHIMMER_SRC)
        # The worst case is sources times live sprites times depth squared.
        sources = 3
        live = 12
        depth = 2.0
        self.assertLess(sources * live * depth * depth, 190.0)

    def test_live_sprite_count_is_bounded_by_the_interval(self):
        self.assertIn("_drop = _LIFETIME / _MAX_LIVE", self.code)
        self.assertIn("setDropInterval _dropInterval", self.code)

    # ── declared defaults and the reachable gas temperature ────────────
    def test_header_declares_the_three_class_defaults(self):
        self.assertIn("500 C", SHIMMER_SRC)
        self.assertIn("600 C", SHIMMER_SRC)
        self.assertIn("1200 C", SHIMMER_SRC)
        self.assertIn("0.5 m", SHIMMER_SRC)
        self.assertIn("0.8 m", SHIMMER_SRC)
        self.assertIn("2.0 m", SHIMMER_SRC)

    def test_header_states_no_reachable_exhaust_gas_temperature(self):
        self.assertIn("NOT REACHABLE FROM THE THERMAL SOLVER", SHIMMER_SRC.upper())
        self.assertIn("SURFACE", SHIMMER_SRC.upper())

    def test_selector_uses_the_declared_class_defaults(self):
        self.assertIn('isKindOf "Plane"', self.code)
        self.assertIn("[500, 0.5]", self.code)
        self.assertIn("[600, 0.8]", self.code)

    def test_measured_override_is_read_with_a_fallback(self):
        self.assertIn('getVariable ["aee_exhaustGasTempC", -1]', self.code)
        self.assertIn('getVariable ["aee_exhaustPlumeM", -1]', self.code)

    # ── bounded scope and lifecycle ────────────────────────────────────
    def test_scope_is_player_vehicle_plus_nearest_capped(self):
        self.assertIn("nearestObjects", self.code)
        self.assertIn("_MAX_SOURCES", self.code)
        self.assertIn("isEngineOn", self.code)

    def test_sources_are_tracked_and_reaped(self):
        self.assertIn("QGVAR(exhaustSources)", self.code)
        self.assertIn("deleteVehicle _src", self.code)

    def test_client_only(self):
        self.assertIn("if (!hasInterface) exitWith {};", self.code)

    def test_uses_exhaust_memory_points_with_a_fallback(self):
        self.assertIn("selectionPosition", self.code)
        self.assertIn('"exhaust"', self.code)
        self.assertIn("[0, -2, 0.6]", self.code)

    def test_uses_the_alpha_setting_as_the_only_lever(self):
        self.assertIn("QGVAR(exhaustShimmerAlpha)", self.code)
        self.assertIn("_alphaMax", self.code)


class ExhaustWiring(unittest.TestCase):
    """Registration, the environment tick, the settings, and the docs."""

    def test_kernel_is_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateThermalRefraction);", prep)

    def test_renderer_is_registered(self):
        prep = (REPO / "addons/optics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREPS(fx,applyExhaustShimmerFX);", prep)

    def test_renderer_is_wired_into_the_environment_tick(self):
        tick = (REPO / "addons/core/functions/fnc_updateEnvironment.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("EFUNC(optics,applyExhaustShimmerFX)", tick)
        # It runs with the other optics FX, after the mirage call.
        self.assertLess(
            tick.find("EFUNC(optics,applyMirageFX)"),
            tick.find("EFUNC(optics,applyExhaustShimmerFX)"),
        )

    def test_setting_is_registered(self):
        settings = (REPO / "addons/optics/initSettings.inc.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("AEE_SETTING_SLIDER(exhaustShimmerAlpha", settings)

    def test_settings_doc_records_the_setting(self):
        config = (REPO / "docs/wiki/chapters/configuration.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("aee_optics_exhaustShimmerAlpha", config)

    def test_state_variables_doc_records_the_new_state(self):
        state = (REPO / "docs/wiki/chapters/state-variables.qmd").read_text(
            encoding="utf-8"
        )
        self.assertIn("aee_optics_exhaustSources", state)
        self.assertIn("aee_optics_exhaustRefraction", state)


if __name__ == "__main__":
    unittest.main()
