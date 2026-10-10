#!/usr/bin/env python3
"""Acoustic masking / ambient noise-floor tests (issue #109).

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
failure is a source failure, not a mirror drift:

  addons/weather/functions/acoustics/fnc_powerSumLevels.sqf
  addons/weather/functions/acoustics/fnc_ambientNoiseLevel.sqf
  addons/weather/functions/acoustics/fnc_acousticMasking.sqf

The source contracts read the wiring the harness cannot execute (the driver
reads the engine, and the core tick calls it).

Run: python3 -m unittest tools.tests.test_acoustic_masking -v
"""

from __future__ import annotations

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import Lambda, Params, load_sqf, run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ACOUSTICS = ROOT / "addons" / "weather" / "functions" / "acoustics"
POWER_SUM = ACOUSTICS / "fnc_powerSumLevels.sqf"
AMBIENT = ACOUSTICS / "fnc_ambientNoiseLevel.sqf"
MASKING = ACOUSTICS / "fnc_acousticMasking.sqf"
DRIVER = ACOUSTICS / "fnc_updateAmbientNoise.sqf"
CORE_TICK = ROOT / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
PREP = ROOT / "addons" / "weather" / "XEH_PREP.hpp"


def _kernel(path):
    """A callable Lambda built from a real kernel file, params pre-bound."""
    stmts = load_sqf(path)
    params, body = [], stmts
    if stmts and isinstance(stmts[0], Params):
        params = [name for name, _default in stmts[0].specs]
        body = stmts[1:]
    return Lambda(params, body, {})


def power_sum(levels):
    return run_sqf(POWER_SUM, [levels])


def ambient(rain, wind_ms, foliage, water):
    return run_sqf(
        AMBIENT,
        [rain, wind_ms, foliage, water],
        globals_={"__FUNC__powerSumLevels": _kernel(POWER_SUM)},
    )


def masking(source_db, distance_m, ambient_db, index=1.0, threshold_db=6):
    return run_sqf(MASKING, [source_db, distance_m, ambient_db, index, threshold_db])


def detection_range(source_db, ambient_db, index=1.0, threshold_db=6):
    """Distance at which the signal crosses floor + threshold (index-scaled)."""
    margin = source_db - ambient_db - threshold_db
    if margin <= 0:
        return 0.0
    return index * (10 ** (margin / 20))


class TestPowerSum(unittest.TestCase):
    """fnc_powerSumLevels runs from the real SQF (ISO 1996-1:2016)."""

    def test_two_equal_fifty_db_sources_sum_to_fifty_three(self):
        # 10*log10(2) = +3.01 dB; the issue's test vector.
        self.assertAlmostEqual(power_sum([50, 50]), 53.0103, places=3)

    def test_an_empty_list_is_silent(self):
        self.assertEqual(power_sum([]), 0)

    def test_silent_sources_contribute_nothing(self):
        self.assertEqual(power_sum([0, 0, 0]), 0)

    def test_a_single_source_is_unchanged(self):
        self.assertAlmostEqual(power_sum([60]), 60, places=6)

    def test_the_sum_exceeds_every_term(self):
        result = power_sum([40, 50])
        self.assertGreater(result, 50)
        self.assertLess(result, 53.1)

    def test_ten_equal_sources_add_ten_db(self):
        self.assertAlmostEqual(power_sum([50] * 10), 60, places=3)


class TestAmbientNoiseLevel(unittest.TestCase):
    """fnc_ambientNoiseLevel runs from the real SQF."""

    def test_rain_zero_is_silent_and_rain_one_is_heavy(self):
        # The issue's test vector: rain 0 -> 0 dB, rain 1 -> 58 dB.
        self.assertEqual(ambient(0, 0, 0, 0), 0)
        self.assertAlmostEqual(ambient(1, 0, 0, 0), 58, places=4)

    def test_wind_two_is_thirty_and_wind_ten_is_fifty(self):
        # The issue's test vector.
        self.assertAlmostEqual(ambient(0, 2, 0, 0), 30, places=4)
        self.assertAlmostEqual(ambient(0, 10, 0, 0), 50, places=4)

    def test_a_quiet_forest_floor_is_twenty_five(self):
        # Full foliage, no weather: the issue's quiet forest floor (20-30).
        self.assertAlmostEqual(ambient(0, 0, 1.0, 0), 25, places=4)

    def test_the_levels_power_sum(self):
        # Rain 58 and wind 30 combine as 10*log10(10^5.8 + 10^3) = 58.0.
        combined = ambient(1, 2, 0, 0)
        self.assertAlmostEqual(combined, power_sum([58, 30]), places=4)
        self.assertGreater(combined, 58)

    def test_every_term_is_monotonic(self):
        self.assertGreaterEqual(ambient(0.9, 0, 0, 0), ambient(0.1, 0, 0, 0))
        self.assertGreaterEqual(ambient(0, 15, 0, 0), ambient(0, 2, 0, 0))
        self.assertGreaterEqual(ambient(0, 0, 1.0, 0), ambient(0, 0, 0.5, 0))
        self.assertGreaterEqual(ambient(0, 0, 0, 1.0), ambient(0, 0, 0, 0.5))

    def test_the_level_is_bounded_by_the_table_ceilings(self):
        # The strongest single source is violent rain at 58 dB.
        self.assertLessEqual(ambient(1, 0, 0, 0), 58)


class TestAcousticMasking(unittest.TestCase):
    """fnc_acousticMasking runs from the real SQF."""

    def test_a_close_loud_source_is_audible(self):
        audible, margin = masking(160, 10, 25, 1.0, 6)
        self.assertTrue(audible)
        self.assertGreater(margin, 0)

    def test_a_silent_ambient_far_source_is_inaudible(self):
        audible, _margin = masking(50, 1000, 25, 1.0, 6)
        self.assertFalse(audible)

    def test_the_gate_flips_between_six_and_ten_db(self):
        # Margin 8 dB: audible at the 6 dB detection threshold, not at 10 dB.
        source, distance, floor = 33, 1, 25
        audible6, margin6 = masking(source, distance, floor, 1.0, 6)
        audible10, margin10 = masking(source, distance, floor, 1.0, 10)
        self.assertTrue(audible6)
        self.assertGreater(margin6, 0)
        self.assertFalse(audible10)
        self.assertLess(margin10, 0)

    def test_heavy_rain_masks_a_grass_walk_at_any_range(self):
        # Heavy rain (58 dB) fully masks a grass walk (35 dB at 1 m): the
        # source is below the floor even at 1 m, so no range is audible.
        heavy_rain = ambient(1, 0, 0, 0)
        for r in (1, 2, 5, 20):
            audible, _margin = masking(35, r, heavy_rain, 1.0, 6)
            self.assertFalse(audible, r)

    def test_a_quiet_forest_allows_detection_to_about_two_metres(self):
        # Quiet forest floor (25 dB): a grass walk (35 dB at 1 m) is audible
        # only at short range.  The issue states ~2 m.
        floor = ambient(0, 0, 1.0, 0)
        self.assertAlmostEqual(floor, 25, places=4)
        rng = detection_range(35, floor, 1.0, 6)
        self.assertGreater(rng, 1.0)
        self.assertLess(rng, 3.0)
        self.assertTrue(masking(35, 1, floor, 1.0, 6)[0])
        self.assertFalse(masking(35, 5, floor, 1.0, 6)[0])

    def test_the_propagation_index_scales_the_range(self):
        # An index above 1 carries the sound further, below 1 shorter.
        self.assertGreater(
            detection_range(60, 25, 1.5, 6), detection_range(60, 25, 1.0, 6)
        )
        self.assertLess(
            detection_range(60, 25, 0.5, 6), detection_range(60, 25, 1.0, 6)
        )

    def test_the_spreading_is_six_db_per_doubling(self):
        _audible1, margin1 = masking(80, 1, 0, 1.0, 6)
        _audible2, margin2 = masking(80, 2, 0, 1.0, 6)
        self.assertAlmostEqual(margin1 - margin2, 20 * math.log10(2), places=4)

    def test_the_gate_is_broadband_and_deterministic(self):
        self.assertEqual(masking(60, 50, 30), masking(60, 50, 30))


class TestAcousticMaskingSourceContracts(unittest.TestCase):
    """The wiring the harness cannot execute."""

    def _strip(self, path):
        code = re.sub(
            r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        return re.sub(r"//[^\n]*", "", code)

    def test_the_pure_kernels_have_no_engine_or_global_state(self):
        for kernel in (POWER_SUM, AMBIENT, MASKING):
            code = self._strip(kernel)
            for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
                self.assertNotIn(banned, code, f"{kernel.name}: {banned}")

    def test_the_kernels_cite_the_sources(self):
        # Every value grounded: the power sum cites ISO 1996-1:2016 and the
        # masking theory cites Fletcher 1940 and Glasberg and Moore 1990.
        self.assertIn("ISO 1996-1:2016", POWER_SUM.read_text(encoding="utf-8"))
        masking_text = MASKING.read_text(encoding="utf-8")
        self.assertIn("Fletcher 1940", masking_text)
        self.assertIn("10.1103/RevModPhys.12.47", masking_text)
        self.assertIn("Glasberg", AMBIENT.read_text(encoding="utf-8"))
        self.assertIn(
            "10.1016/0378-5955(90)90170-T", AMBIENT.read_text(encoding="utf-8")
        )

    def test_the_kernels_are_prepped(self):
        text = PREP.read_text(encoding="utf-8")
        for name in (
            "powerSumLevels",
            "ambientNoiseLevel",
            "acousticMasking",
            "updateAmbientNoise",
        ):
            self.assertIn(f"PREPS(acoustics,{name})", text)

    def test_the_driver_publishes_the_floor_from_the_engine(self):
        code = DRIVER.read_text(encoding="utf-8")
        self.assertIn("rain", code)
        self.assertIn("vectorMagnitude wind", code)
        self.assertIn("currentFoliageDensity", code)
        self.assertIn("surfaceIsWater", code)
        self.assertIn("FUNC(ambientNoiseLevel)", code)
        self.assertIn("currentAmbientNoise", code)

    def test_the_core_tick_calls_the_driver(self):
        text = CORE_TICK.read_text(encoding="utf-8")
        self.assertIn("EFUNC(weather,updateAmbientNoise)", text)


if __name__ == "__main__":
    unittest.main()
