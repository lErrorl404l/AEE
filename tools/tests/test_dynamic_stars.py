#!/usr/bin/env python3
"""Dynamic starfield renderer kernels (issue #122).

The renderer converts the star catalog (aee_environmental_visibleStars: [name,
altDeg, azDeg, vmag]) to per-frame sky positions and brightness.  Two
pure kernels carry the physics and are executed here from their real SQF:

  - fnc_starDirection: alt/az -> world direction unit vector (east/north/up)
  - fnc_starMagnitude: vmag -> [sizeScale, alpha] (Pogson flux + bloom curve)

The catalog (fnc_getStarCatalog) already gates on the NELM and the horizon,
so the renderer does not re-apply either - it adds only the night and
overcast gates, which fnc_starLightsSync owns.  The light-emitter emission
itself is client-only and is a manual QA item; the maths is locked below.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SENSOR = ROOT / "addons" / "environmental" / "functions" / "astronomy"

DIRECTION = SENSOR / "fnc_starDirection.sqf"
MAGNITUDE = SENSOR / "fnc_starMagnitude.sqf"


def star_direction(alt_deg, az_deg):
    """Mirror of fnc_starDirection: [east, north, up] unit vector."""
    alt = math.radians(alt_deg)
    az = math.radians(az_deg)
    return [math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)]


def star_magnitude(vmag):
    """Mirror of fnc_starMagnitude: [sizeScale, alpha]."""
    alpha = max(0.0, min(1.0, 10 ** (-0.4 * vmag)))
    size = max(0.3, min(1.5, 1.5 - 0.25 * vmag))
    return [size, alpha]


class TestStarDirectionExecutes(unittest.TestCase):
    """fnc_starDirection runs from the real SQF and matches the mirror."""

    def test_zenith(self):
        got = run_sqf(DIRECTION, [90, 0])
        self.assertAlmostEqual(got[0], 0, places=6)
        self.assertAlmostEqual(got[1], 0, places=6)
        self.assertAlmostEqual(got[2], 1, places=6)

    def test_north_horizon(self):
        got = run_sqf(DIRECTION, [0, 0])
        self.assertAlmostEqual(got[0], 0, places=6)
        self.assertAlmostEqual(got[1], 1, places=6)
        self.assertAlmostEqual(got[2], 0, places=6)

    def test_east_horizon(self):
        got = run_sqf(DIRECTION, [0, 90])
        self.assertAlmostEqual(got[0], 1, places=6)
        self.assertAlmostEqual(got[1], 0, places=6)
        self.assertAlmostEqual(got[2], 0, places=6)

    def test_45_deg_45_az(self):
        got = run_sqf(DIRECTION, [45, 45])
        want = star_direction(45, 45)
        for a, b in zip(got, want):
            self.assertAlmostEqual(a, b, places=6)

    def test_negative_altitude_below_horizon(self):
        got = run_sqf(DIRECTION, [-30, 120])
        want = star_direction(-30, 120)
        for a, b in zip(got, want):
            self.assertAlmostEqual(a, b, places=6)

    def test_unit_length(self):
        got = run_sqf(DIRECTION, [33, 200])
        mag = math.sqrt(got[0] ** 2 + got[1] ** 2 + got[2] ** 2)
        self.assertAlmostEqual(mag, 1.0, places=6)


class TestStarMagnitudeExecutes(unittest.TestCase):
    """fnc_starMagnitude runs from the real SQF and matches the mirror."""

    def test_mag_zero_is_full_brightness_and_max_size(self):
        size, alpha = run_sqf(MAGNITUDE, [0])
        self.assertAlmostEqual(alpha, 1.0, places=6)
        self.assertAlmostEqual(size, 1.5, places=6)

    def test_sirius_clamps_at_full(self):
        size, alpha = run_sqf(MAGNITUDE, [-1.46])
        self.assertAlmostEqual(alpha, 1.0, places=6)
        self.assertAlmostEqual(size, 1.5, places=6)

    def test_mag_two_anchor(self):
        size, alpha = run_sqf(MAGNITUDE, [2])
        self.assertAlmostEqual(size, 1.0, places=6)
        self.assertAlmostEqual(alpha, 10**-0.8, places=6)

    def test_faint_star_fades(self):
        size, alpha = run_sqf(MAGNITUDE, [6])
        self.assertLess(alpha, 0.01)
        self.assertAlmostEqual(size, 0.3, places=6)

    def test_monotonic_brighter_is_bigger(self):
        bright = run_sqf(MAGNITUDE, [-1])
        faint = run_sqf(MAGNITUDE, [5])
        self.assertGreater(bright[1], faint[1])
        self.assertGreater(bright[0], faint[0])


class TestStarRendererUsesLightEmitters(unittest.TestCase):
    """The operator's direction: stars are engine light emitters, no texture.

    drawLine3D (colour-only) was the fallback, but the operator wants the
    engine's own light path.  A star is a local "#lightpoint" whose FLARE is
    the visible point (BIKI Light Source Tutorial): setLightUseFlare +
    setLightFlareSize + setLightFlareMaxDistance + a non-black setLightColor,
    with setLightAmbient black so the field does not light the ground.
    """

    def setUp(self):
        self.reg = (SENSOR / "fnc_renderDynamicStars.sqf").read_text(encoding="utf-8")
        self.sync = (SENSOR / "fnc_starLightsSync.sqf").read_text(encoding="utf-8")

    def test_registrar_is_client_and_idempotent(self):
        self.assertIn("hasInterface", self.reg)
        self.assertIn("dynamicStarsPFH", self.reg)
        self.assertIn("addPerFrameHandler", self.reg)

    def test_star_is_a_lightpoint(self):
        self.assertIn('"#lightpoint"', self.sync)
        self.assertIn("createVehicleLocal", self.sync)

    def test_flare_is_enabled_and_sized(self):
        self.assertIn("setLightUseFlare", self.sync)
        self.assertIn("setLightFlareSize", self.sync)
        self.assertIn("setLightFlareMaxDistance", self.sync)

    def test_no_scene_illumination(self):
        # A star lights the ground for all practical purposes not at all.
        self.assertIn("setLightAmbient [0, 0, 0]", self.sync)

    def test_night_and_disable_gates(self):
        self.assertIn("currentSunElevation", self.sync)
        self.assertIn("deleteVehicle", self.sync)

    def test_no_drawline3d_texture_fallback(self):
        self.assertNotIn("drawLine3D", self.reg)
        self.assertNotIn("drawLine3D", self.sync)

    def test_no_nelm_regate(self):
        # The catalog already gates on the limiting magnitude; the sync
        # worker must not re-check vmag against it (duplication).
        self.assertNotIn("limitingMagnitude", self.sync)


class TestStarLogging(unittest.TestCase):
    """The starfield is visible in a log (the no-logging defect)."""

    def setUp(self):
        self.reg = (SENSOR / "fnc_renderDynamicStars.sqf").read_text(encoding="utf-8")
        self.sync = (SENSOR / "fnc_starLightsSync.sqf").read_text(encoding="utf-8")

    def test_registrar_logs_once(self):
        self.assertIn("AEE_LOG_INFO", self.reg)
        self.assertIn('"starfield: light-emitter PFH registered"', self.reg)

    def test_sync_has_a_windowed_log(self):
        self.assertIn("AEE_LOG_DEBUG", self.sync)
        self.assertIn("starLogAt", self.sync)
        self.assertIn("starfield: %1 stars visible", self.sync)


if __name__ == "__main__":
    unittest.main()
