#!/usr/bin/env python3
"""Engine environment bridge tests (issue #141).

AEE computes the physics; these bridges render it with the engine
environment commands.  This suite mirrors each bridge's gate and output
mapping, and a source-check class reads the SQF text so a bridge cannot
silently stop calling its command.

The constants are parsed out of the SQF, not copied: if a bridge changes
its threshold or scale the mirror follows.

Run: python3 -m unittest tools.tests.test_engine_bridges
"""

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "addons" / "atmos" / "functions" / "state"

RAINBOW_SQF = STATE / "fnc_updateRainbow.sqf"
WAVES_SQF = STATE / "fnc_updateEngineWaves.sqf"
LIGHTNINGS_SQF = STATE / "fnc_updateEngineLightnings.sqf"
APERTURE_SQF = STATE / "fnc_updateAperture.sqf"
LOCAL_WIND_SQF = STATE / "fnc_updateLocalWindParams.sqf"
SIMUL_SQF = STATE / "fnc_updateSimulWeatherLayers.sqf"


def _read(path):
    return path.read_text(encoding="utf-8")


def _const(text, name):
    """Read `private _name = <number>;` out of the SQF."""
    m = re.search(rf"_{re.escape(name)}\s*=\s*([0-9]*\.?[0-9]+)\s*;", text)
    if m is None:
        raise AssertionError(f"constant _{name} not found in source")
    return float(m.group(1))


# ─── Constants parsed from the SQF ────────────────────────────────────────
_RAINBOW = _read(RAINBOW_SQF)
_WAVES = _read(WAVES_SQF)
_LIGHTNINGS = _read(LIGHTNINGS_SQF)
_APERTURE = _read(APERTURE_SQF)
_LOCAL_WIND = _read(LOCAL_WIND_SQF)
_SIMUL = _read(SIMUL_SQF)

MAX_SUN_ELEV = _const(_RAINBOW, "maxSunElev")
FULL_SCALE_M = _const(_WAVES, "fullScaleMetres")
MIN_LUX = _const(_APERTURE, "minLux")
MAX_LUX = _const(_APERTURE, "maxLux")
NIGHT_STANDARD = _const(_APERTURE, "nightStandard")
DAY_STANDARD = _const(_APERTURE, "dayStandard")
MIN_FACTOR = _const(_APERTURE, "minFactor")
MAX_FACTOR = _const(_APERTURE, "maxFactor")
GRAVITY = _const(_LOCAL_WIND, "g")
DISABLE_PARAM = _const(_LOCAL_WIND, "disableParam")


def linear_conversion(a, b, x, a_res, b_res, clamp=True):
    """SQF linearConversion, including the descending case."""
    if a == b:
        return a_res
    t = (x - a) / (b - a)
    if clamp:
        t = max(0.0, min(1.0, t))
    return a_res + t * (b_res - a_res)


# ─── Mirrors ──────────────────────────────────────────────────────────────


def rainbow_value(sun_elev, rain, facing_anti):
    """Mirror of fnc_updateRainbow: all three conditions gate the bow."""
    if sun_elev < MAX_SUN_ELEV and rain > 0 and facing_anti:
        return 1
    return 0


def waves_value(significant_height_m):
    """Mirror of fnc_updateEngineWaves: normalise to the model ceiling."""
    hs = max(0.0, min(FULL_SCALE_M, significant_height_m))
    return hs / FULL_SCALE_M


def lightning_value(risk):
    """Mirror of fnc_updateEngineLightnings: direct 0..1 scale."""
    return max(0.0, min(1.0, risk))


def aperture_params(lux):
    """Mirror of fnc_updateAperture: returns (min, standard, max)."""
    lux = max(MIN_LUX, min(MAX_LUX, lux))
    ev = math.log10(lux)
    standard = linear_conversion(-3, 5, ev, NIGHT_STANDARD, DAY_STANDARD, True)
    return standard * MIN_FACTOR, standard, standard * MAX_FACTOR


def local_wind_params(mass_kg, rho=1.225):
    """Mirror of fnc_updateLocalWindParams: returns (strength, diameter)."""
    if mass_kg <= 0:
        return DISABLE_PARAM, DISABLE_PARAM
    rho = max(0.1, min(1.5, rho))
    radius = 3 + min(mass_kg / 12000.0, 1.0) * 8
    diameter = 2 * radius
    thrust = mass_kg * GRAVITY
    v_induced = math.sqrt(thrust / (2 * rho * math.pi * radius * radius))
    return max(v_induced, DISABLE_PARAM), diameter


class TestRainbow(unittest.TestCase):
    """The wiki note is the gate: rain, low sun, opposite the sun."""

    def test_all_conditions_show_the_bow(self):
        self.assertEqual(rainbow_value(20, 0.5, True), 1)

    def test_high_sun_fails_alone(self):
        # At 42 deg the bow apex reaches the horizon; above it, no bow.
        self.assertEqual(rainbow_value(MAX_SUN_ELEV, 0.5, True), 0)
        self.assertEqual(rainbow_value(50, 0.5, True), 0)

    def test_no_rain_fails_alone(self):
        self.assertEqual(rainbow_value(20, 0, True), 0)

    def test_facing_the_sun_fails_alone(self):
        self.assertEqual(rainbow_value(20, 0.5, False), 0)

    def test_threshold_is_42_deg(self):
        self.assertEqual(MAX_SUN_ELEV, 42)


class TestWaves(unittest.TestCase):
    """Sea state to the engine wave scale."""

    def test_half_metre_maps_to_documented_value(self):
        # 0.5 m significant wave height -> 0.5 / 15 = 0.0333 on 0..1.
        self.assertAlmostEqual(waves_value(0.5), 0.5 / 15.0, places=6)

    def test_calm_is_zero(self):
        self.assertEqual(waves_value(0.0), 0.0)

    def test_above_ceiling_saturates(self):
        self.assertEqual(waves_value(30.0), 1.0)

    def test_monotonic(self):
        self.assertLess(waves_value(0.5), waves_value(2.0))
        self.assertLess(waves_value(2.0), waves_value(8.0))


class TestLightnings(unittest.TestCase):
    """Strike risk to the engine lightning scale."""

    def test_risk_is_direct(self):
        self.assertAlmostEqual(lightning_value(0.7), 0.7, places=6)

    def test_clamped(self):
        self.assertEqual(lightning_value(-1.0), 0.0)
        self.assertEqual(lightning_value(5.0), 1.0)


class TestAperture(unittest.TestCase):
    """min <= standard <= max for every illuminance, night wider than day."""

    def test_ordering_never_inverts(self):
        sweep = [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000]
        for lux in sweep:
            lo, std, hi = aperture_params(lux)
            self.assertLessEqual(lo, std, f"min > standard at {lux} lux")
            self.assertLessEqual(std, hi, f"standard > max at {lux} lux")

    def test_night_wider_than_day(self):
        # Higher aperture value = wider (wiki night example [2, 8, 14]).
        _, night_std, _ = aperture_params(0.001)
        _, day_std, _ = aperture_params(100000)
        self.assertGreater(night_std, day_std)

    def test_standard_is_monotonic(self):
        prev = None
        for lux in [0.001, 0.1, 10, 1000, 100000]:
            _, std, _ = aperture_params(lux)
            if prev is not None:
                self.assertLessEqual(std, prev)
            prev = std

    def test_wiki_night_anchor(self):
        # The night standard is the wiki's 8 at the starlight floor.
        _, std, _ = aperture_params(MIN_LUX)
        self.assertAlmostEqual(std, NIGHT_STANDARD, places=6)

    def test_stands_down_while_a_vision_sensor_is_active(self):
        """The naked-eye aperture must not fight the sensor's fixed exposure.

        NVGs and thermal set a FIXED exposure, because the eye looks at a
        tube whose AGC holds the output near constant whatever the scene
        does.  A scene-derived value would pump up and down as the scene
        brightened.  This asserts the stand-down gate is present and keys on
        the LIVE engine vision mode.
        """
        text = APERTURE_SQF.read_text(encoding="utf-8")
        # Strip the doc comment: it explains the arbitration and names the
        # rejected flags, so a whole-file search would match the prose.
        code = text[text.index("*/") + 2 :] if "*/" in text else text

        self.assertIn("currentVisionMode", code, "sensor stand-down gate is missing")

        gate_line = re.search(r"if\s*\([^)]*currentVisionMode[^)]*\)\s*exitWith", code)
        self.assertIsNotNone(gate_line, "no live gate statement found")

        call = re.search(r"^\s*setApertureNew\s*\[", code, re.M)
        self.assertIsNotNone(call, "no setApertureNew call found")
        self.assertLess(
            gate_line.start(), call.start(), "the gate is after the write it guards"
        )

        # Not on the latched flags: they clear only in the sensor exit
        # branch, so they can go stale and freeze the aperture.
        self.assertNotIn("nvgGrainActive", code)
        self.assertNotIn("thermalActive", code)

    def test_uses_the_four_element_form(self):
        """setApertureNew is [minimum, standard, maximum, luminance].

        The BI wiki documents four elements in both the 2013 and the 2024
        captures, and every example uses four.  The reset form is a single
        element, setApertureNew [-1].  A three-element call is invalid.
        """
        text = APERTURE_SQF.read_text(encoding="utf-8")
        match = re.search(r"setApertureNew\s*\[([^\]]+)\]", text)
        self.assertIsNotNone(match, "no setApertureNew call found")
        elements = [part for part in match.group(1).split(",") if part.strip()]
        self.assertEqual(len(elements), 4, f"expected 4 elements, got {len(elements)}")


class TestLocalWindParams(unittest.TestCase):
    """Rotor thrust to the visual downwash pair."""

    def test_thrust_gives_a_positive_strength(self):
        strength, diameter = local_wind_params(3000.0)
        self.assertGreater(strength, DISABLE_PARAM)
        self.assertGreater(diameter, 0.0)

    def test_zero_thrust_disables(self):
        self.assertEqual(local_wind_params(0.0), (DISABLE_PARAM, DISABLE_PARAM))

    def test_heavy_airframe_has_a_wider_disc(self):
        # Diameter grows with the rotor-radius estimate.  The induced
        # velocity itself is not monotonic in mass: a heavy-lift rotor has
        # a larger disc, so it accelerates the same air less.
        _, light_diameter = local_wind_params(3000.0)
        _, heavy_diameter = local_wind_params(12000.0)
        self.assertGreater(heavy_diameter, light_diameter)

    def test_disable_value_is_the_wiki_pair(self):
        self.assertEqual(DISABLE_PARAM, 0.0001)


class TestSourceChecks(unittest.TestCase):
    """Each bridge must actually call its engine command."""

    def _assert_gated(self, text):
        self.assertIn("hasInterface", text, "bridge is not client-gated")

    def test_rainbow_calls_setRainbow(self):
        self.assertIn("setRainbow", _RAINBOW)
        self._assert_gated(_RAINBOW)
        self.assertIn("_maxSunElev", _RAINBOW)
        self.assertIn("_facingAnti", _RAINBOW)
        self.assertIn("_rain", _RAINBOW)

    def test_waves_calls_setWaves(self):
        self.assertIn("setWaves", _WAVES)
        self._assert_gated(_WAVES)
        self.assertIn("waveHeight_m", _WAVES)
        self.assertIn("Manual Override", _WAVES)

    def test_lightnings_calls_setLightnings(self):
        self.assertIn("setLightnings", _LIGHTNINGS)
        self._assert_gated(_LIGHTNINGS)
        self.assertIn("currentLightningRisk", _LIGHTNINGS)
        self.assertIn("Manual Override", _LIGHTNINGS)

    def test_aperture_calls_setApertureNew(self):
        self.assertIn("setApertureNew", _APERTURE)
        self._assert_gated(_APERTURE)
        self.assertIn("illuminanceLux", _APERTURE)
        self.assertIn("HDR", _APERTURE)
        self.assertIn("mission start", _APERTURE)

    def test_local_wind_calls_setLocalWindParams(self):
        self.assertIn("setLocalWindParams", _LOCAL_WIND)
        self._assert_gated(_LOCAL_WIND)
        self.assertIn("Helicopter", _LOCAL_WIND)
        self.assertIn("nearEntities", _LOCAL_WIND)

    def test_simul_calls_setSimulWeatherLayers(self):
        self.assertIn("setSimulWeatherLayers", _SIMUL)
        self._assert_gated(_SIMUL)
        self.assertIn("simulWeatherLayers", _SIMUL)


if __name__ == "__main__":
    unittest.main()
