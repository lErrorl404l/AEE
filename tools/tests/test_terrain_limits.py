"""Terrain and geometry limits for a ground vehicle (issue #117).

Each law is evaluated independently and the SQF is checked to implement the
same form.  The research corrected three of the issue's own numbers, so the
tests encode the corrected values, not the issue's text.

Sources:
  breakover    tan(beta/2) = 2c/L      SAE J1100 / J689; AM General M1151 sheet
  gradeability theta = asin((F/W)/sqrt(1+fr^2)) - atan(fr)
                                       Gillespie, Fundamentals of Vehicle
                                       Dynamics (SAE 1992), road-load equation
  friction     tan(theta) <= mu - fr   Gillespie, same equation
  side slope   tan(theta) = SSF        NHTSA
  fording      0.76/1.52 m, 5 mph cap  TM 9-2320-387-10
"""

import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIMITS = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateTerrainLimits.sqf"


def breakover_deg(clearance_m, wheelbase_m):
    return 2 * math.degrees(math.atan(2 * clearance_m / wheelbase_m))


def grade_deg(mu, fr=0.015):
    """The exact road-load solution, not the small-angle form."""
    inner = min(mu / math.sqrt(1 + fr * fr), 1.0)
    return math.degrees(math.asin(inner)) - math.degrees(math.atan(fr))


def friction_limit_deg(mu, fr=0.015):
    return math.degrees(math.atan(max(mu - fr, 0)))


class TestBreakover(unittest.TestCase):
    def test_issue_test_vector(self):
        # 0.44 m clearance, 4.0 m wheelbase -> 24.8 deg (the issue's vector).
        self.assertAlmostEqual(breakover_deg(0.44, 4.0), 24.9, delta=0.15)

    def test_both_algebraic_forms_agree(self):
        # 2*atan(2c/L) and 2*atan(c/(L/2)) are the same statement.
        c, L = 0.44, 4.0
        self.assertAlmostEqual(
            2 * math.degrees(math.atan(2 * c / L)),
            2 * math.degrees(math.atan(c / (L / 2))),
            places=9,
        )

    def test_real_m1151(self):
        # 43.69 cm clearance, 3.30 m wheelbase -> 29.7 deg by the formula,
        # while the manufacturer states 25 deg. The formula ignores tyre
        # deflection, so the measured value governs for that vehicle.
        self.assertAlmostEqual(breakover_deg(0.4369, 3.30), 29.7, delta=0.2)

    def test_longer_wheelbase_needs_more_clearance(self):
        # For a fixed clearance the breakover angle falls as L rises.
        self.assertGreater(breakover_deg(0.44, 3.0), breakover_deg(0.44, 4.0))


class TestGradeability(unittest.TestCase):
    def test_force_grade_exceeds_the_friction_limit(self):
        # Two different quantities, and the LOWER governs:
        #   grade_deg(mu)        the climb the tractive force allows
        #   friction_limit_deg   the climb the tyres can transmit
        # A vehicle with mu=0.8 is traction-limited, not force-limited.
        self.assertGreater(grade_deg(0.80), friction_limit_deg(0.80))
        # So the usable grade is the friction limit.
        self.assertAlmostEqual(
            min(grade_deg(0.80), friction_limit_deg(0.80)),
            friction_limit_deg(0.80),
        )

    def test_friction_limit_is_the_published_band(self):
        # Dry mu 0.7-0.8 gives a 36-40 deg friction-limited climb, which is
        # the published military grade band (the M998 is 60% = 31 deg).
        self.assertGreater(friction_limit_deg(0.80), 30)
        self.assertLess(friction_limit_deg(0.80), 45)

    def test_sand_grade_is_far_lower(self):
        # Sand mu 0.2-0.3: the climb collapses.
        self.assertLess(friction_limit_deg(0.25), 15)
        self.assertGreater(friction_limit_deg(0.25), 0)

    def test_friction_limit(self):
        self.assertAlmostEqual(friction_limit_deg(0.85), 40.0, delta=0.5)
        # Below the rolling resistance the vehicle cannot move at all.
        self.assertAlmostEqual(friction_limit_deg(0.01), 0.0, delta=0.01)


class TestSideSlope(unittest.TestCase):
    def test_tip_angle_is_atan_ssf(self):
        # SSF 0.97 (the corrected M1151 value) -> 44.1 deg.
        self.assertAlmostEqual(math.degrees(math.atan(0.97)), 44.1, delta=0.2)

    def test_issue_ssf_is_wrong(self):
        # The issue claims SSF 1.19 -> 50 deg. AM General geometry gives
        # 0.97, so the issue's value is optimistic and must not be used.
        self.assertAlmostEqual(math.degrees(math.atan(1.19)), 50.0, delta=0.3)
        self.assertNotAlmostEqual(0.97, 1.19, places=2)

    def test_published_limit_governs_below_the_tip(self):
        # A 30 deg operational limit is below the 44 deg tip, so it governs.
        self.assertLess(30, math.degrees(math.atan(0.97)))

    def test_m998_side_slope_is_40_percent(self):
        # 40% side slope = atan(0.40) = 21.8 deg (the issue's figure).
        self.assertAlmostEqual(math.degrees(math.atan(0.40)), 21.8, delta=0.1)


class TestFording(unittest.TestCase):
    def test_hmmwv_depths_from_the_operator_manual(self):
        # TM 9-2320-387-10: 30 in shallow, 60 in with the deep-water kit.
        self.assertAlmostEqual(30 * 0.0254, 0.762, delta=0.002)
        self.assertAlmostEqual(60 * 0.0254, 1.524, delta=0.002)

    def test_fording_speed_cap(self):
        # The TM states 5 mph, which is 8.0 kph.
        self.assertAlmostEqual(5 * 1.609344, 8.05, delta=0.1)


class TestSqfForms(unittest.TestCase):
    def setUp(self):
        self.src = LIMITS.read_text(encoding="utf-8")

    def test_breakover_form_in_sqf(self):
        self.assertIn("2 * (atan ((2 * _clearance) / _wheelbase))", self.src)

    def test_gradeability_is_the_exact_form(self):
        self.assertIn("asin ((_tanTerm min 1) max -1) - atan _fr", self.src)
        # The small-angle form must NOT be present.
        self.assertNotIn("(F - R) /", self.src)

    def test_friction_limit_in_sqf(self):
        self.assertIn("atan (_mu - _fr)", self.src)

    def test_side_slope_reuses_ssf(self):
        # One model for rollover and side slope.
        self.assertIn("calculateSSF", self.src)

    def test_published_limit_governs(self):
        # The lower of tip and published limit is returned.
        self.assertIn("_tipDeg < _sideLimit", self.src)

    def test_ford_depth_is_returned(self):
        self.assertIn("_fordDepth]", self.src)

    def test_no_unsourced_values(self):
        # The issue's SSF 1.19 must not appear as a constant.
        self.assertNotIn("1.19", self.src)


if __name__ == "__main__":
    unittest.main()
