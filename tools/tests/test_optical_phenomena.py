#!/usr/bin/env python3
"""Reference checks for AEE's atmospheric optical phenomena.

These tests validate the SQF implementation of the ice-crystal halo
(addons/atmos/functions/physics/fnc_calculateHalo.sqf) and the green flash
(addons/optics/functions/sensor/fnc_calculateGreenFlash.sqf) against the
source formulas. They mirror the exact formulas in the SQF source so any
drift breaks the tests, and they pin the consumer wiring (the environment
tick and the module state lines).

Sources:
  - Tape, W. (1994) Atmospheric Halos, Antarctic Research Series 64
    (prism minimum deviation).
  - Warren, S. G. and Brandt, R. E. (2008) Optical constants of ice,
    JGR 113 D14220 (hexagonal ice refractive index).
  - Young, A. T. (SDSU) green flashes and mirages.
  - Issue #12 (2026-09-16) green-flash model and constants.

Run: python3 -m unittest tools.tests.test_optical_phenomena -v
"""

import math
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_ATMOS = _REPO / "addons" / "atmos" / "functions"
_OPTICS = _REPO / "addons" / "optics" / "functions"
_CORE = _REPO / "addons" / "core" / "functions"


def _read(base, name):
    direct = base / name
    if direct.exists():
        return direct.read_text(encoding="utf-8")
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


def halo_sqf():
    return _read(_ATMOS, "fnc_calculateHalo.sqf")


def green_flash_sqf():
    return _read(_OPTICS, "fnc_calculateGreenFlash.sqf")


# ─── Halo: prism minimum deviation ─────────────────────────────────────────
# Warren and Brandt 2008: hexagonal ice, red 656 nm = 1.306, blue 486 nm = 1.317.
N_RED = 1.306
N_BLUE = 1.317


def minimum_deviation(n, apex_deg):
    """D_min = 2*asin(n*sin(A/2)) - A, in degrees (Tape 1994)."""
    half = math.radians(apex_deg / 2)
    return 2 * math.degrees(math.asin(n * math.sin(half))) - apex_deg


def halo_radii():
    return (
        minimum_deviation(N_RED, 60),
        minimum_deviation(N_BLUE, 60),
        minimum_deviation(N_RED, 90),
        minimum_deviation(N_BLUE, 90),
    )


def halo_intensity(sun_elev_deg, overcast):
    if sun_elev_deg > 0 and overcast > 0.1:
        return min(1.0, max(0.0, (1 - overcast) * math.sin(math.radians(sun_elev_deg))))
    return 0.0


def sundog_offset(sun_elev_deg, overcast, vanish_elev=61.0):
    """Parhelion azimuth offset, or None when no parhelion shows."""
    if not (0 < sun_elev_deg <= vanish_elev) or overcast <= 0.1:
        return None
    cos_elev = math.cos(math.radians(sun_elev_deg))
    if cos_elev <= 1e-3:
        return None
    cos_az = (
        math.cos(math.radians(22)) - math.sin(math.radians(sun_elev_deg)) ** 2
    ) / cos_elev**2
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))


# ─── Green flash: refraction dispersion ────────────────────────────────────
HORIZON_REFRACTION_DEG = 0.57
DISPERSION_FRACTION = 0.025
SUN_SINK_RATE_DEG_PER_S = 0.25 / 60


def green_flash_duration():
    return (HORIZON_REFRACTION_DEG * DISPERSION_FRACTION) / SUN_SINK_RATE_DEG_PER_S


def green_flash_intensity(sun_elev, haze, gradient, overcast):
    if not (-1 < sun_elev < 2):
        return 0.0
    if gradient > -100:
        return 0.0
    if not (haze < 0.3 and overcast < 0.3):
        return 0.0
    proximity = max(0.0, 1 - abs(sun_elev - 0.5) / 1.5)
    mirage = min(1.0, ((-gradient) - 100) / 100)
    clear = min(1.0, 1 - haze / 0.3)
    return max(0.0, min(1.0, proximity * mirage * clear * (1 - overcast)))


class TestHaloRadii(unittest.TestCase):
    def test_22_degree_halo(self):
        inner, outer, _, _ = halo_radii()
        # The 22-degree halo sits at the 60-degree prism minimum deviation.
        self.assertAlmostEqual(inner, 21.8, delta=0.4)
        self.assertLess(inner, outer)
        self.assertLess(outer - inner, 1.5)  # small chromatic width

    def test_46_degree_halo(self):
        _, _, inner, outer = halo_radii()
        # The 46-degree halo sits at the 90-degree prism minimum deviation.
        self.assertAlmostEqual(inner, 45.8, delta=1.2)
        self.assertLess(inner, outer)

    def test_red_inside_blue(self):
        # The red index is lower, so the red minimum deviation is the inner edge.
        inner22, outer22, inner46, outer46 = halo_radii()
        self.assertLess(inner22, outer22)
        self.assertLess(inner46, outer46)


class TestHaloIntensity(unittest.TestCase):
    def test_night_zero(self):
        self.assertEqual(halo_intensity(-10, 0.3), 0.0)

    def test_no_cloud_zero(self):
        self.assertEqual(halo_intensity(30, 0.05), 0.0)

    def test_clear_day_positive(self):
        self.assertGreater(halo_intensity(30, 0.3), 0.0)

    def test_thick_cloud_dimmer(self):
        self.assertGreater(halo_intensity(30, 0.2), halo_intensity(30, 0.7))

    def test_clamped(self):
        self.assertLessEqual(halo_intensity(90, 0.1), 1.0)
        self.assertGreaterEqual(halo_intensity(1, 0.99), 0.0)


class TestSundog(unittest.TestCase):
    def test_at_horizon_is_22(self):
        self.assertAlmostEqual(sundog_offset(0.5, 0.3), 22.0, delta=0.5)

    def test_spreads_with_elevation(self):
        self.assertGreater(sundog_offset(30, 0.3), sundog_offset(5, 0.3))

    def test_vanishes_above_61(self):
        self.assertIsNone(sundog_offset(65, 0.3))

    def test_no_cloud_none(self):
        self.assertIsNone(sundog_offset(20, 0.05))


class TestGreenFlash(unittest.TestCase):
    def test_duration_matches_sun_sink(self):
        # The rim crosses the horizon in about 3-4 s (issue #12).
        self.assertGreater(green_flash_duration(), 3.0)
        self.assertLess(green_flash_duration(), 4.0)

    def test_peak_near_horizon(self):
        peak = green_flash_intensity(0.5, 0.0, -200, 0.0)
        self.assertGreater(peak, 0.5)
        self.assertLessEqual(peak, 1.0)

    def test_high_sun_zero(self):
        self.assertEqual(green_flash_intensity(30, 0.0, -200, 0.0), 0.0)

    def test_no_mirage_zero(self):
        # A standard gradient (-39 N/km) has no mirage, so no green flash.
        self.assertEqual(green_flash_intensity(0.5, 0.0, -39, 0.0), 0.0)

    def test_haze_kills_it(self):
        self.assertEqual(green_flash_intensity(0.5, 0.4, -200, 0.0), 0.0)

    def test_stronger_mirage_brighter(self):
        self.assertGreater(
            green_flash_intensity(0.5, 0.0, -200, 0.0),
            green_flash_intensity(0.5, 0.0, -120, 0.0),
        )


class TestSqfSync(unittest.TestCase):
    """The SQF source must contain the constants the mirrors rely on."""

    def test_halo_constants(self):
        src = halo_sqf()
        for fragment in [
            "_nRed = 1.306",
            "_nBlue = 1.317",
            "2 * asin (_nRed * (sin 30)) - 60",
            "2 * asin (_nBlue * (sin 45)) - 90",
            "_sundogVanishElev = 61",
        ]:
            self.assertIn(fragment, src, f"halo SQF missing: {fragment}")

    def test_green_flash_constants(self):
        src = green_flash_sqf()
        for fragment in [
            "_horizonRefractionDeg = 0.57",
            "_dispersionFraction = 0.025",
            "_sunSinkRateDegPerS = 0.25 / 60",
            "_gradient <= -100",
            "_haze < 0.3",
            "_sunElev > -1",
            "_sunElev < 2",
        ]:
            self.assertIn(fragment, src, f"green-flash SQF missing: {fragment}")


class TestWiring(unittest.TestCase):
    """The new kernels have a producer, a consumer and a declared dependency."""

    def test_tick_calls_both_kernels(self):
        env = _read(_CORE, "fnc_updateEnvironment.sqf")
        self.assertIn("EFUNC(atmos,calculateHalo)", env)
        self.assertIn("EFUNC(optics,calculateGreenFlash)", env)
        # One producer for the refraction state the green flash reads.
        self.assertIn("EFUNC(atmos,calculateRefraction)", env)

    def test_state_lines_read_the_published_values(self):
        atmos_dump = _read(_ATMOS, "fnc_dumpState.sqf")
        for name in (
            "haloIntensity",
            "haloActive",
            "halo22InnerDeg",
            "sundogOffsetDeg",
        ):
            self.assertIn(
                f"QGVAR({name})", atmos_dump, f"atmos dumpState misses {name}"
            )
        optics_dump = _read(_OPTICS, "fnc_dumpState.sqf")
        for name in ("greenFlashIntensity", "greenFlashActive", "greenFlashDurationS"):
            self.assertIn(
                f"QGVAR({name})", optics_dump, f"optics dumpState misses {name}"
            )

    def test_optics_declares_the_atmos_dependency(self):
        cfg = (_REPO / "addons" / "optics" / "config.cpp").read_text(encoding="utf-8")
        self.assertIn('"aee_atmos"', cfg)


if __name__ == "__main__":
    unittest.main()
