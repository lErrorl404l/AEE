#!/usr/bin/env python3
"""CBRN agent plume dispersion tests (issue #105).

Runs the REAL SQF kernels through the sqf_lite interpreter (issue #204) and
checks the issue's test vectors, so a constant change in the SQF fails here.

Sources (see each kernel header):
  Gaussian plume / puff   Turner, Workbook of Atmospheric Dispersion
                          Estimates, EPA AP-26 (1970).
  Dispersion coefficients Briggs (1973), Diffusion Estimation for Small
                          Emissions, ATDL.
  Stability class         Pasquill, via Turner AP-26 Table 1.
  Agent parameters        FM 3-11, Chemical Operations (2003), Table 4-1.

Run: python3 -m unittest tools.tests.test_cbrn_plume -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

ADDON = REPO / "addons" / "weather"
DISP = ADDON / "functions" / "dispersion"

STABILITY = DISP / "fnc_getStabilityClass.sqf"
COEFF = DISP / "fnc_getDispersionCoefficients.sqf"
PLUME = DISP / "fnc_calculatePlumeConcentration.sqf"
PUFF = DISP / "fnc_calculatePuffConcentration.sqf"
DECAY = DISP / "fnc_calculateCbrnDecay.sqf"
AGENT = DISP / "fnc_getCbrnAgent.sqf"
DOSE = DISP / "fnc_calculateCbrnDose.sqf"

UPDATE_ENV = REPO / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
PREP = ADDON / "XEH_PREP.hpp"
INIT_SETTINGS = ADDON / "initSettings.inc.sqf"
STRINGTABLE = ADDON / "stringtable.xml"
DRIVER = DISP / "fnc_updateCbrnPlume.sqf"


class TestStabilityClass(unittest.TestCase):
    def test_day_strong_low_wind_is_A(self):
        # Issue vector: day strong insolation, 1 m/s -> A.
        self.assertEqual(run_sqf(STABILITY, [1.0, 800, 0, True, 999]), "A")

    def test_night_overcast_moderate_wind_is_D(self):
        # Issue vector: night overcast, 4 m/s -> D.
        self.assertEqual(run_sqf(STABILITY, [4.0, 0, 6, False, 999]), "D")

    def test_day_slight_low_wind_is_B(self):
        # Slight insolation (solar < 350), calm -> B (day table col 0).
        self.assertEqual(run_sqf(STABILITY, [1.0, 100, 0, True, 999]), "B")

    def test_night_clear_calm_is_F(self):
        self.assertEqual(run_sqf(STABILITY, [1.0, 0, 0, False, 999]), "F")

    def test_gradient_method_takes_precedence(self):
        # A measured superadiabatic gradient is class A regardless of wind.
        self.assertEqual(run_sqf(STABILITY, [10.0, 0, 8, False, -2.5]), "A")
        # A strong inversion is class F.
        self.assertEqual(run_sqf(STABILITY, [10.0, 0, 8, False, 2.0]), "F")

    def test_class_always_in_range(self):
        for wind in (0.5, 2.5, 4.0, 5.5, 7.0):
            for solar in (0, 400, 900):
                cls = run_sqf(STABILITY, [wind, solar, 0, True, 999])
                self.assertIn(cls, "ABCDEF")


class TestBriggsCoefficients(unittest.TestCase):
    def test_issue_vector_class_D(self):
        # Issue vector: Briggs rural D, x = 1 km -> sigma_y 76.3, sigma_z 37.9.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        self.assertAlmostEqual(sy, 76.3, places=1)
        self.assertAlmostEqual(sz, 37.9, places=1)

    def test_sigma_grows_with_distance(self):
        sy1, sz1 = run_sqf(COEFF, [500, "D", False])
        sy2, sz2 = run_sqf(COEFF, [2000, "D", False])
        self.assertLess(sy1, sy2)
        self.assertLess(sz1, sz2)

    def test_urban_doubles_sigma_y(self):
        rural_y, _ = run_sqf(COEFF, [1000, "D", False])
        urban_y, _ = run_sqf(COEFF, [1000, "D", True])
        self.assertAlmostEqual(urban_y, rural_y * 2, places=4)

    def test_class_A_spreads_more_than_F(self):
        # The unstable class has the larger crosswind spread at short range.
        ay, _ = run_sqf(COEFF, [500, "A", False])
        fy, _ = run_sqf(COEFF, [500, "F", False])
        self.assertGreater(ay, fy)


class TestPlumeConcentration(unittest.TestCase):
    def test_issue_vector_ground_source(self):
        # Issue vector: Q=100000, U=5, rural D at 1 km, ground source
        # -> C = 2.20 mg/m3.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        c = run_sqf(PLUME, [100000, 5, sy, sz, 0, 0, 0])
        self.assertAlmostEqual(c, 2.20, places=1)

    def test_issue_vector_elevated_height(self):
        # Issue vector: H = 50 m -> C = 0.92 mg/m3.
        sy, sz = run_sqf(COEFF, [1000, "D", False])
        c = run_sqf(PLUME, [100000, 5, sy, sz, 50, 0, 0])
        self.assertAlmostEqual(c, 0.92, places=1)

    def test_ground_source_matches_closed_form(self):
        # Ground source, ground level: C = Q/(pi U sigma_y sigma_z).
        import math

        sy, sz = 20.0, 10.0
        c = run_sqf(PLUME, [1000, 3, sy, sz, 0, 0, 0])
        self.assertAlmostEqual(c, 1000 / (math.pi * 3 * sy * sz), places=6)

    def test_crosswind_decays(self):
        sy, sz = 20.0, 10.0
        centre = run_sqf(PLUME, [1000, 3, sy, sz, 0, 0, 0])
        off = run_sqf(PLUME, [1000, 3, sy, sz, 0, 30, 0])
        self.assertLess(off, centre)


class TestPuffConcentration(unittest.TestCase):
    def test_centre_matches_closed_form(self):
        import math

        c = run_sqf(PUFF, [1000, 20, 20, 10, 0, 0])
        self.assertAlmostEqual(
            c, 1000 / ((2 * math.pi) ** 1.5 * 20 * 20 * 10), places=6
        )

    def test_off_centre_decays(self):
        centre = run_sqf(PUFF, [1000, 20, 20, 10, 0, 0])
        off = run_sqf(PUFF, [1000, 20, 20, 10, 40, 0])
        self.assertLess(off, centre)


class TestDecay(unittest.TestCase):
    def test_exactly_half_after_one_half_life(self):
        # Issue vector: exactly 0.5 * C0 after one half-life.
        c = run_sqf(DECAY, [100.0, 36.0, 36.0])
        self.assertAlmostEqual(c, 50.0, places=6)

    def test_vx_half_life_is_36h(self):
        # FM 3-11: VX is the persistent agent (days-weeks) -> 36 h.
        self.assertAlmostEqual(run_sqf(DECAY, [1.0, 36.0, 36.0]), 0.5, places=6)

    def test_gb_decays_in_an_hour(self):
        self.assertAlmostEqual(run_sqf(DECAY, [1.0, 1.0, 1.0]), 0.5, places=6)


class TestAgentTable(unittest.TestCase):
    def test_vx_parameters(self):
        row = run_sqf(AGENT, ["VX"])
        self.assertEqual(row[0], 10)  # LCt50 mg*min/m3
        self.assertAlmostEqual(row[1], 0.0007)  # VP mmHg
        self.assertAlmostEqual(row[3], 36)  # half-life h

    def test_gb_parameters(self):
        row = run_sqf(AGENT, ["GB"])
        self.assertEqual(row[0], 85)  # midpoint of 70-100
        self.assertAlmostEqual(row[3], 1)

    def test_cg_is_minutes(self):
        row = run_sqf(AGENT, ["CG"])
        self.assertAlmostEqual(row[3], 0.1667, places=3)

    def test_case_insensitive(self):
        self.assertEqual(run_sqf(AGENT, ["vx"]), run_sqf(AGENT, ["VX"]))

    def test_unknown_defaults_to_H(self):
        self.assertEqual(run_sqf(AGENT, ["XX"]), run_sqf(AGENT, ["H"]))


class TestDose(unittest.TestCase):
    def test_issue_vector_vx_lethal_in_4_5_min(self):
        # Issue vector: VX (LCt50 10) at 2.20 mg/m3 is lethal in ~4.5 min
        # (10 / 2.20 = 4.545 min).  Just past 4.5 min it crosses LCt50.
        dt = 4.55 * 60
        _, lethal, _ = run_sqf(DOSE, [0, 2.20, dt, 10, 0])
        self.assertTrue(lethal)
        # At 4.4 min (9.68 mg*min/m3) it has not yet reached LCt50.
        _, below, _ = run_sqf(DOSE, [0, 2.20, 4.4 * 60, 10, 0])
        self.assertFalse(below)

    def test_not_lethal_below_lct50(self):
        _, lethal, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        self.assertFalse(lethal)

    def test_incapacitated_at_one_tenth_lct50(self):
        # 0.1 * LCt50 = 1.0 -> 2.20 mg/m3 for 1 min gives 2.2 -> incapacitated.
        _, _, inc = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        self.assertTrue(inc)

    def test_protection_scales_the_dose(self):
        full, _, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0])
        blocked, _, _ = run_sqf(DOSE, [0, 2.20, 60, 10, 0.95])
        self.assertLess(blocked, full)

    def test_dose_accumulates(self):
        new, _, _ = run_sqf(DOSE, [5.0, 2.20, 60, 10, 0])
        self.assertAlmostEqual(new, 5.0 + 2.20, places=6)


class TestWiring(unittest.TestCase):
    """Source locks: the kernels are PREP'd, scheduled and configured."""

    def test_kernels_are_prepared(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "getStabilityClass",
            "getDispersionCoefficients",
            "calculatePlumeConcentration",
            "calculatePuffConcentration",
            "calculateCbrnDecay",
            "getCbrnAgent",
            "calculateCbrnDose",
            "startCbrnRelease",
            "updateCbrnPlume",
        ):
            self.assertIn(f"PREPS(dispersion,{name})", prep)

    def test_tick_calls_the_driver(self):
        env = UPDATE_ENV.read_text(encoding="utf-8")
        self.assertIn("EFUNC(weather,updateCbrnPlume)", env)

    def test_setting_registered_and_read(self):
        self.assertIn("CbrnPlumeEnabled", INIT_SETTINGS.read_text(encoding="utf-8"))
        self.assertIn("GVAR(CbrnPlumeEnabled)", DRIVER.read_text(encoding="utf-8"))

    def test_stringtable_has_the_setting_strings(self):
        st = STRINGTABLE.read_text(encoding="utf-8")
        self.assertIn("STR_AEE_Weather_CbrnPlumeEnabled_Name", st)
        self.assertIn("STR_AEE_Weather_CbrnPlumeEnabled_Description", st)

    def test_driver_reuses_the_existing_wind_and_protection(self):
        driver = DRIVER.read_text(encoding="utf-8")
        self.assertIn("EGVAR(core,currentWind)", driver)
        self.assertIn("EFUNC(persistence,getCbrnProtection)", driver)


if __name__ == "__main__":
    unittest.main()
