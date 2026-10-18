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
    """Python mirror of the rain washout in fnc_calculateCBRNPersistence.

    The kernel's only environmental factor besides the per-agent Arrhenius
    temperature term is the rain washout the scent model publishes.  The
    invented humidity and wind factors are gone (no published value).
    """

    @staticmethod
    def persistence(
        temp_c=15.0,
        delta_hvap_jmol=0.0,
        rain_factor=1.0,
        base_h=24,
        interval=5,
    ):
        rate_multiplier = 1.0
        if delta_hvap_jmol != 0:
            temp_k = max(temp_c + 273.15, 1.0)
            rate_multiplier = math.exp(
                -(delta_hvap_jmol / 8.314462618) * (1.0 / temp_k - 1.0 / 298.15)
            )
        persistence_h = (base_h / rate_multiplier) * rain_factor
        return math.exp(-(interval / 3600) / persistence_h)

    def test_dry_rain_factor_is_no_change(self):
        self.assertAlmostEqual(
            self.persistence(15.0, 80.3e3, 1.0), self.persistence(15.0, 80.3e3)
        )

    def test_rain_shortens_persistence(self):
        # A larger decay factor means slower decay, so rain must lower it.
        self.assertLess(
            self.persistence(15.0, 80.3e3, 0.2), self.persistence(15.0, 80.3e3, 1.0)
        )

    def test_still_within_the_decay_factor_range(self):
        # The published decay factor is always in (0, 1].
        for rf in (1.0, 0.2):
            for args in ((15.0, 80.3e3), (40.0, 24.8e3), (-20.0, 55.2e3), (15.0, 0.0)):
                with self.subTest(args=args, rain_factor=rf):
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
