#!/usr/bin/env python3
"""Altimeter standard-altitude tests (issue #294).

Executes the REAL kernel through tools/tests/sqf_lite.py, so a failure is a
source failure and not a mirror drift.

The defect: FUNC(openAltimeter) added ``(1013.25 - pressure) * 30`` to a
metre altitude.  The 30 is FEET per hPa, about 8.3 m, so the HUD "Std Alt"
read 3.6 times too large (a 10 hPa deficit added 300 m instead of 83 m).
The driver now calls FUNC(standardAltitude), which derives metres per hPa
from the ISA sea-level density and standard gravity.

Run: python3 -m unittest tools.tests.test_actions_altimeter -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import constants_defines, run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ACTIONS = REPO / "addons" / "actions"
FUNCS = ACTIONS / "functions"

KERNEL = FUNCS / "fnc_standardAltitude.sqf"
DRIVER = FUNCS / "fnc_openAltimeter.sqf"

ISA_HPA = 1013.25
# 100 Pa per hPa / (rho0 * g) - the same derivation the kernel performs.
METRES_PER_HPA = 100 / (
    constants_defines()["AERO_ISA_SEA_LEVEL_DENSITY"]
    * constants_defines()["STANDARD_GRAVITY"]
)


def standard_altitude(altitude_m, pressure_hpa):
    return run_sqf(KERNEL, [altitude_m, pressure_hpa])


class TestStandardAltitude(unittest.TestCase):
    """The factor is metres per hPa, not feet per hPa."""

    def test_a_ten_hpa_deficit_adds_about_83_metres(self):
        # The issue vector.  With the old factor of 30 this reads 300.
        self.assertAlmostEqual(standard_altitude(1000, ISA_HPA - 10), 1083.24, places=1)

    def test_the_sea_level_factor_is_metres_per_hpa(self):
        # 8.324 m per hPa (27.3 ft).  30 ft/hPa would give 9.144 and 30 m/hPa
        # would give 30: both fail here.
        factor = standard_altitude(0, ISA_HPA - 1)
        self.assertAlmostEqual(factor, METRES_PER_HPA, places=4)
        self.assertGreater(factor, 8.0)
        self.assertLess(factor, 8.7)

    def test_the_old_reading_was_3_6_times_too_large(self):
        self.assertAlmostEqual(30.0 / standard_altitude(0, ISA_HPA - 1), 3.6, places=1)

    def test_standard_pressure_leaves_the_altitude_alone(self):
        self.assertAlmostEqual(standard_altitude(2500, ISA_HPA), 2500.0, places=6)

    def test_a_high_pressure_subtracts(self):
        self.assertAlmostEqual(standard_altitude(1000, ISA_HPA + 10), 916.76, places=1)

    def test_altitude_is_metres_at_any_level(self):
        # The offset is a function of pressure alone, so it is the same for a
        # sea-level and a mountain reading.
        low = standard_altitude(0, ISA_HPA - 5)
        high = standard_altitude(4000, ISA_HPA - 5)
        self.assertAlmostEqual(high - low, 4000.0, places=3)

    def test_the_kernel_defaults_to_isa_sea_level_pressure(self):
        self.assertAlmostEqual(run_sqf(KERNEL, [1234]), 1234.0, places=6)


class TestAltimeterWiring(unittest.TestCase):
    """The engine wiring the harness cannot execute."""

    def test_the_driver_uses_the_kernel(self):
        text = DRIVER.read_text(encoding="utf-8")
        self.assertIn("FUNC(standardAltitude)", text)

    def test_the_driver_keeps_no_feet_per_hpa_factor(self):
        # The defect was the raw factor 30 in the driver; it must stay in the
        # kernel as a derivation, never come back as a literal here.
        text = DRIVER.read_text(encoding="utf-8")
        self.assertNotIn("* 30", text)

    def test_the_kernel_derives_the_factor_from_shared_constants(self):
        # Comments explain the derivation, so the scan reads the code only.
        code = re.sub(
            r"/\*.*?\*/", "", KERNEL.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        self.assertIn("AERO_ISA_SEA_LEVEL_DENSITY", code)
        self.assertIn("STANDARD_GRAVITY", code)
        self.assertNotIn("0.3048", code)
        self.assertNotIn("9.144", code)
        self.assertNotIn("30", code)


if __name__ == "__main__":
    unittest.main()
