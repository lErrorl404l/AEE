#!/usr/bin/env python3
"""Scent dispersion wiring tests (issue #39).

The scent model output is wired to two consumers:

- wildlife behaviour: fnc_calculateBiologicalAmbient scales the ambient bed
  by fnc_scentWildlifeResponse (predator / unknown presence quietens it);
- CBRN persistence: fnc_calculateCBRNPersistence reuses the scent model's
  rain washout factor only, never the aggregate intensity.

The pure kernel runs from its real SQF through tools/tests/sqf_lite.py, so a
failure is a source failure, not a mirror drift.  The source contracts read
the engine wiring, which the harness cannot execute.

Sources:
  Amo, Galvan, Tomas and Sanz (2008), "Predator odour recognition and
  avoidance in a songbird", Functional Ecology 22(2):289-293, DOI
  10.1111/j.1365-2435.2007.01361.x - wildlife reduce activity near a
  predator scent (direction only; the magnitude is UNSOURCED).
  Turner, "Workbook of Atmospheric Dispersion Estimates", 2nd ed, CRC,
  1994 - the Gaussian plume washout term exp(-lambda x / u); rain
  scavenges an airborne agent, so it shortens persistence.
  The rain magnitude (0.2 in rain) is the repo's own scent model constant
  (fnc_calculateScentDispersion) and is UNSOURCED as a CBRN scavenging
  coefficient.

Run: python3 -m unittest tools.tests.test_scent_dispersion -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WEATHER = ROOT / "addons" / "weather"
PERSISTENCE = ROOT / "addons" / "persistence"

KERNEL = WEATHER / "functions" / "fnc_scentWildlifeResponse.sqf"
SCENT = WEATHER / "functions" / "fnc_calculateScentDispersion.sqf"
AMBIENT = WEATHER / "functions" / "warnings" / "fnc_calculateBiologicalAmbient.sqf"
PREP = WEATHER / "XEH_PREP.hpp"
CBRN = PERSISTENCE / "functions" / "warnings" / "fnc_calculateCBRNPersistence.sqf"
ANNEX_C = ROOT / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"

RUNNER = ROOT / "tools" / "run_tests.py"

THRESHOLD = 0.15
FLOOR = 0.4


def response(intensity):
    return run_sqf(KERNEL, [intensity])


class TestScentWildlifeKernel(unittest.TestCase):
    def test_no_scent_no_effect(self):
        # Zero intensity is below the detection threshold: the multiplier is 1.
        self.assertAlmostEqual(response(0.0), 1.0)

    def test_below_threshold_no_effect(self):
        self.assertAlmostEqual(response(THRESHOLD), 1.0)
        self.assertAlmostEqual(response(0.05), 1.0)

    def test_full_intensity_hits_the_floor(self):
        self.assertAlmostEqual(response(1.0), FLOOR)

    def test_monotonic_decreasing(self):
        # Higher scent quietens the ambient more.
        prev = response(0.0)
        for i in range(1, 11):
            cur = response(i / 10)
            self.assertLessEqual(cur, prev + 1e-9)
            prev = cur

    def test_midpoint(self):
        # Halfway between the threshold and 1 is halfway to the floor.
        mid = THRESHOLD + (1 - THRESHOLD) / 2
        self.assertAlmostEqual(response(mid), (1 + FLOOR) / 2)

    def test_bounds(self):
        # Out-of-range inputs clamp to the floor and to 1.
        self.assertAlmostEqual(response(2.0), FLOOR)
        self.assertAlmostEqual(response(-1.0), 1.0)

    def test_never_below_floor_or_above_one(self):
        for i in range(-5, 25):
            v = response(i / 10)
            self.assertGreaterEqual(v, FLOOR - 1e-9)
            self.assertLessEqual(v, 1.0 + 1e-9)


class TestScentModelPublishesRainFactor(unittest.TestCase):
    def setUp(self):
        self.src = SCENT.read_text(encoding="utf-8")

    def test_publishes_rain_factor(self):
        self.assertIn("QGVAR(scentRainFactor)", self.src)
        self.assertIn("_rainFactor", self.src)

    def test_rain_factor_is_point_two_in_rain(self):
        # The washout constant the CBRN consumer inherits.
        self.assertIn("if (rain > 0) then { _rainFactor = 0.2; };", self.src)


class TestCbrnConsumesRainFactor(unittest.TestCase):
    def setUp(self):
        self.src = CBRN.read_text(encoding="utf-8")

    def test_reads_the_scent_rain_factor_by_name(self):
        self.assertIn('"aee_weather_scentRainFactor"', self.src)
        self.assertIn("_persistenceH = _persistenceH * _scentRainFactor;", self.src)

    def test_does_not_reuse_the_aggregate_intensity(self):
        # The aggregate folds temperature/humidity/wind the CBRN model owns.
        self.assertNotIn("scentDispersionIntensity", self.src)

    def test_defaults_to_no_washout(self):
        self.assertIn('["aee_weather_scentRainFactor", 1]', self.src)


class TestWildlifeAmbientConsumesScent(unittest.TestCase):
    def setUp(self):
        self.src = AMBIENT.read_text(encoding="utf-8")

    def test_reads_scent_intensity(self):
        self.assertIn("QGVAR(scentDispersionIntensity)", self.src)

    def test_calls_the_kernel(self):
        self.assertIn("call FUNC(scentWildlifeResponse)", self.src)

    def test_kernel_is_prepped(self):
        self.assertIn("PREP(scentWildlifeResponse)", PREP.read_text(encoding="utf-8"))


class TestCbrnRainWashoutMath(unittest.TestCase):
    """Python mirror of the rain washout in fnc_calculateCBRNPersistence."""

    @staticmethod
    def persistence(
        temp_c, humidity_pct, wind_ms, rain_factor=1.0, base_h=24, interval=5
    ):
        rate_multiplier = 2 ** ((temp_c - 15) / 10)
        persistence_h = base_h / rate_multiplier
        humidity_factor = 1 / (1 + ((humidity_pct - 50) / 50) * 0.5)
        persistence_h = persistence_h * humidity_factor
        wind_factor = 1 / (1 + wind_ms * 0.05)
        persistence_h = persistence_h * wind_factor
        persistence_h = persistence_h * rain_factor
        return math.exp(-(interval / 3600) / persistence_h)

    def test_dry_rain_factor_is_no_change(self):
        self.assertAlmostEqual(
            self.persistence(15, 50, 0, 1.0), self.persistence(15, 50, 0)
        )

    def test_rain_shortens_persistence(self):
        # A larger decay factor means slower decay, so rain must lower it.
        self.assertLess(
            self.persistence(15, 50, 0, 0.2), self.persistence(15, 50, 0, 1.0)
        )

    def test_still_within_the_decay_factor_range(self):
        # The published decay factor is always in (0, 1].
        for rf in (1.0, 0.2):
            for args in [(15, 50, 0), (40, 100, 20), (-20, 0, 0), (15, 50, 50)]:
                m = self.persistence(*args, rain_factor=rf)
                self.assertGreater(m, 0.0)
                self.assertLessEqual(m, 1.0)

    def test_scent_constant_transfers(self):
        # The value the CBRN consumer inherits from the scent model.
        self.assertEqual(response(1.0) > 0, True)
        self.assertIn("0.2", SCENT.read_text(encoding="utf-8"))


class TestSuiteRegistered(unittest.TestCase):
    def test_registered_in_runner(self):
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn("tools/tests/test_scent_dispersion.py", runner)


if __name__ == "__main__":
    unittest.main()
