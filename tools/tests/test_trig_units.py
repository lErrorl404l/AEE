#!/usr/bin/env python3
"""Degrees-vs-radians guard for the physics trig kernels.

SQF sin/cos/tan take DEGREES and asin/acos/atan/atan2 return DEGREES.
A class of bugs converted degrees to radians (via `* pi / 180` or the
magic constants 0.0174532925 / 57.2957795) and then fed those radians to
the degree-based trig, silently corrupting the physics. This suite pins
the two pure kernels that were fixed, and source-locks the rest so a
regression to a radian conversion fails the gate.

Run: python3 -m unittest tools.tests.test_trig_units -v
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"

MAGNETIC = ADDONS / "magnetism" / "functions" / "fnc_calculateMagneticAnomaly.sqf"
ROLLOVER = ADDONS / "mobility" / "functions" / "fnc_calculateRolloverThreshold.sqf"


def dipole_nanotesla(sensor, source, moment, tilt_deg):
    """Python mirror of fnc_calculateMagneticAnomaly (degree-based)."""
    r = math.dist(sensor, source)
    if r < 0.1:
        return 0.0
    dx = sensor[0] - source[0]
    dz = sensor[2] - source[2]
    axis_x = math.sin(math.radians(tilt_deg))
    axis_z = math.cos(math.radians(tilt_deg))
    cos_theta = (dx * axis_x + dz * axis_z) / r
    r3 = r * r * r
    # SI flux density: B = (mu0/4pi) * M / r^3 * sqrt(1 + 3cos^2 theta).
    # mu0/4pi = 1e-7 T m / A.  The mu0 factor is required: without it the
    # expression is the magnetic field strength H (A/m), ~795775x too large.
    return (1e-7 * moment / r3) * math.sqrt(1 + 3 * cos_theta * cos_theta) * 1e9


def static_g(ssf, slope_deg):
    """Python mirror of the rollover static threshold (degree-based)."""
    t = math.radians(slope_deg)
    return ssf * math.cos(t) - math.sin(t)


class TestMagneticAnomalyExecutesInDegrees(unittest.TestCase):
    """The dipole kernel is executed from the real SQF."""

    def test_vertical_dipole_above_source(self):
        # Tilt 0: axis is vertical; a sensor directly above reads cos(theta)=1.
        got = run_sqf(MAGNETIC, [[0, 0, 2], [0, 0, 0], 1000, 0])
        want = dipole_nanotesla([0, 0, 2], [0, 0, 0], 1000, 0)
        self.assertAlmostEqual(got, want, places=6)

    def test_tilted_dipole_distinguishes_degrees_from_radians(self):
        # At 30 deg tilt the axis components are sin/cos of 30 DEGREES.
        # A radian-converted bug would give axis_x ~0.009 instead of 0.5,
        # collapsing the field, so a sensor on the tilt axis reads it.
        got = run_sqf(MAGNETIC, [[10, 0, 5], [0, 0, 0], 5000, 30])
        want = dipole_nanotesla([10, 0, 5], [0, 0, 0], 5000, 30)
        self.assertAlmostEqual(got, want, places=6)

    def test_horizontal_tilt_90(self):
        got = run_sqf(MAGNETIC, [[0, 0, 1], [0, 0, 0], 1000, 90])
        want = dipole_nanotesla([0, 0, 1], [0, 0, 0], 1000, 90)
        self.assertAlmostEqual(got, want, places=6)

    def test_inside_source_returns_zero(self):
        self.assertEqual(run_sqf(MAGNETIC, [[0.01, 0, 0], [0, 0, 0], 1000, 0]), 0)


class TestRolloverThresholdExecutesInDegrees(unittest.TestCase):
    """The rollover kernel is executed from the real SQF."""

    def test_static_threshold_matches_published_vector(self):
        # SSF 1.1 at 20 deg: 0.692 g (issue #108 test vector).
        res = run_sqf(ROLLOVER, [1.1, 20, 0.8])
        self.assertAlmostEqual(res[0], static_g(1.1, 20), places=5)

    def test_applied_g_is_static_times_factor(self):
        res = run_sqf(ROLLOVER, [1.1, 20, 0.8])
        self.assertAlmostEqual(res[1], static_g(1.1, 20) * 0.8, places=5)

    def test_steep_slope_clamps_at_zero(self):
        # Above atan(SSF) the static term is negative and clamps to zero.
        res = run_sqf(ROLLOVER, [0.7, 60, 0.8])
        self.assertEqual(res[0], 0)


class TestNoRadianConversionRemains(unittest.TestCase):
    """Source-lock: the degree-based form must not regress to radians."""

    SITES = {
        "addons/lighting/functions/astronomy/fnc_calculateSolarRadiation.sqf": [
            "_haRad",
            "_latRad",
            "_declRad",
        ],
        "addons/magnetism/functions/fnc_calculateMagneticAnomaly.sqf": ["_tiltRad"],
        "addons/thermal/functions/surface/fnc_isPositionShadowed.sqf": ["_azR", "_elR"],
        "addons/thermal/functions/display/fnc_getSelectionSunExposure.sqf": [
            "_azRad",
            "_elevRad",
        ],
        "addons/weather/functions/biome/fnc_getSmoothedBiome.sqf": [
            "_rad =",
            "sin _rad",
            "cos _rad",
        ],
        "addons/persistence/functions/warnings/fnc_calculateAvalancheRisk.sqf": [
            "_psi"
        ],
        "addons/lighting/functions/astronomy/fnc_getStarCatalog.sqf": [
            "_latRad",
            "_raRad",
            "_decRad",
            "_haRad",
            "_altRad",
            "_zRad",
            "_thetaRad",
        ],
    }

    def test_no_radian_variables_remain(self):
        for rel, names in self.SITES.items():
            src = (ROOT / rel).read_text(encoding="utf-8")
            for name in names:
                self.assertNotIn(name, src, f"{rel} still references {name}")

    def test_no_radians_to_degrees_constant_on_inverse_trig(self):
        # applyRollover must not multiply acos (already degrees) by 57.2957795.
        src = (ROOT / "addons/mobility/functions/fnc_applyRollover.sqf").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("* 57.2957795", src)

    def test_rollover_uses_degrees_directly(self):
        src = (
            ROOT / "addons/mobility/functions/fnc_calculateRolloverThreshold.sqf"
        ).read_text(encoding="utf-8")
        self.assertNotIn("0.0174532925", src)
        self.assertIn("cos _slopeDeg", src)
        self.assertIn("sin _slopeDeg", src)


if __name__ == "__main__":
    unittest.main()
