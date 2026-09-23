"""Vehicle rollover threshold physics (issue #108).

The threshold is a pure function of the Static Stability Factor, the ground
slope and the dynamic factor, so it is evaluated here against the published
formulas rather than in-game.

Sources:
  SSF = T / (2h)                      NHTSA Rollover Resistance.
  a_crit = g(SSF cos t - sin t)       Gillespie, Fundamentals of Vehicle
                                      Dynamics, eq. [4]; ERDC TR-05-6;
                                      STO-TR-AVT-248 (NRMM side-slope).
  dynamic factor 0.7-0.9, default 0.8
  V_crit = sqrt(g R SSF)              steady turn, a_lat = V^2 / R.

A NOTE ON THE ISSUE'S TEST VECTORS. The issue writes
"SSF 1.1, theta=20 deg -> 0.69 g (37% cut)" but attaches it to the formula
that includes the 0.8 dynamic factor, which gives 0.553 g. 0.69 g is the
STATIC slope-corrected value; the 0.8 factor is then applied on top. The
SQF returns both, and both are pinned below, so the ambiguity cannot hide.
"""

import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THRESHOLD = (
    ROOT / "addons" / "mobility" / "functions" / "fnc_calculateRolloverThreshold.sqf"
)
SSF_FILE = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateSSF.sqf"
APPLY = ROOT / "addons" / "mobility" / "functions" / "fnc_applyRollover.sqf"

G = 9.80665


def static_g(ssf, slope_deg):
    t = math.radians(slope_deg)
    return ssf * math.cos(t) - math.sin(t)


class TestPublishedFormulas(unittest.TestCase):
    """The laws, evaluated independently of the SQF."""

    def test_ssf_definition(self):
        # SSF = T / (2h). A 1.82 m track and a 0.83 m CG gives ~1.1.
        self.assertAlmostEqual(1.82 / (2 * 0.83), 1.096, delta=0.01)

    def test_slope_correction_test_vector(self):
        # SSF 1.1 at 20 deg: the static, slope-corrected threshold.
        self.assertAlmostEqual(static_g(1.1, 20), 0.692, delta=0.005)
        # The issue's "37% cut": (1.1 - 0.692) / 1.1 = 37%.
        self.assertAlmostEqual((1.1 - static_g(1.1, 20)) / 1.1 * 100, 37, delta=0.5)

    def test_dynamic_factor_applied(self):
        # 0.8 * 0.692 = 0.553 g, the applied threshold.
        self.assertAlmostEqual(static_g(1.1, 20) * 0.8, 0.553, delta=0.005)

    def test_steady_turn_critical_speed(self):
        # SSF 1.1, R = 30 m: V_crit = sqrt(g R SSF) = 18.0 m/s.
        v_crit = math.sqrt(G * 30 * 1.1)
        self.assertAlmostEqual(v_crit, 18.0, delta=0.1)
        self.assertAlmostEqual(v_crit * 3.6, 64.8, delta=0.5)

    def test_mrap_sightly_less_stable_than_a_car(self):
        # MRAP SSF ~0.7 against a car's ~1.4: the MRAP lifts at half the g.
        self.assertAlmostEqual(0.7 * 0.8, 0.56, delta=0.01)
        self.assertAlmostEqual(1.4 * 0.8, 1.12, delta=0.01)
        self.assertLess(0.7, 1.4)

    def test_steep_bank_lifts_on_the_slope_alone(self):
        # Above atan(SSF) the threshold is negative: the vehicle tips on the
        # slope with no lateral acceleration. The SQF clamps at zero.
        tip_angle = math.degrees(math.atan(0.7))
        self.assertAlmostEqual(tip_angle, 35.0, delta=0.5)
        self.assertLess(static_g(0.7, 45), 0)


class TestSqfImplementsTheFormulas(unittest.TestCase):
    """Read the SOURCE; do not mirror it."""

    def setUp(self):
        self.src = THRESHOLD.read_text(encoding="utf-8")

    def test_slope_form(self):
        self.assertIn("(_ssf * cos _theta) - (sin _theta)", self.src)

    def test_dynamic_factor_applied_to_static(self):
        self.assertIn("_staticG * _dynamicFactor", self.src)

    def test_negative_threshold_clamped(self):
        self.assertIn("if (_staticG < 0) then { _staticG = 0; }", self.src)

    def test_returns_both_thresholds(self):
        # [static, applied, factor] so the issue's two numbers are both real.
        self.assertIn("[_staticG, _appliedG, _dynamicFactor]", self.src)

    def test_no_ssf_returns_zero(self):
        self.assertIn("if (_ssf <= 0) exitWith { [0, 0, _dynamicFactor] }", self.src)


class TestSsfFromGeometry(unittest.TestCase):
    """SSF is not a config property in vanilla, so the source is explicit."""

    def setUp(self):
        self.src = SSF_FILE.read_text(encoding="utf-8")

    def test_uses_runtime_centre_of_mass(self):
        self.assertIn("getCenterOfMass", self.src)

    def test_has_a_class_table_with_fallback(self):
        # Dynamic lookup by isKindOf, not a hardcoded vehicle name.
        self.assertIn("isKindOf", self.src)
        self.assertIn("_trackTable", self.src)

    def test_clamps_the_result(self):
        self.assertIn("_ssf max 0.3 min 2.0", self.src)

    def test_aircraft_are_excluded(self):
        self.assertIn('isKindOf "Air"', self.src)


class TestApplierIsSustainedAndLocal(unittest.TestCase):
    """The two design rules that make the feature correct."""

    def setUp(self):
        self.src = APPLY.read_text(encoding="utf-8")

    def test_uses_add_torque(self):
        # setVectorUp does not persist on a live vehicle, so the roll must
        # use a physical impulse. The header names setVectorUp in prose, so
        # check the CALL, not the string.
        self.assertIn("addTorque", self.src)
        self.assertNotIn("setVectorUp _", self.src)
        self.assertNotIn("setVectorDirAndUp", self.src)

    def test_condition_is_sustained_not_single_frame(self):
        self.assertIn("rolloverHoldFrames", self.src)
        self.assertIn("_held", self.src)

    def test_local_physics_only(self):
        self.assertIn("if (!local _vehicle) exitWith { false }", self.src)

    def test_lateral_acceleration_is_v_times_omega(self):
        self.assertIn("_speed * (abs _omega)", self.src)

    def test_no_publicvariable(self):
        self.assertNotIn("publicVariable", self.src)


if __name__ == "__main__":
    unittest.main()
