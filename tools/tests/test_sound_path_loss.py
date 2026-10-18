#!/usr/bin/env python3
"""Outdoor sound path loss, ISO 9613-2:1996 (fnc_soundPathLoss) and the
propagation index built on it (fnc_updateSoundPropagation).

Run: python3 -m unittest tools.tests.test_sound_path_loss -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

LOSS = REPO / "addons/lib/functions/acoustics/fnc_soundPathLoss.sqf"
ABS = REPO / "addons/lib/functions/acoustics/fnc_atmosphericAbsorption.sqf"
DRIVER = REPO / "addons/weather/functions/terrain/fnc_updateSoundPropagation.sqf"


def loss(d, hs=1.5, hr=1.5, alpha=0.0, g=1.0, fol=0.0):
    return run_sqf(LOSS, [d, hs, hr, alpha, g, fol])


class TestIso9613(unittest.TestCase):
    def test_divergence(self):
        self.assertAlmostEqual(loss(100, g=0), 40.0, places=6)

    def test_air_absorption_is_linear_in_distance(self):
        self.assertAlmostEqual(loss(1000, g=0, alpha=0.002) - loss(1000, g=0), 2.0, places=6)

    def test_ground_equation_10(self):
        d, hm = 500, 1.5
        agr = max(0, 4.8 - (2 * hm / d) * (17 + 300 / d))
        self.assertAlmostEqual(loss(d) - loss(d, g=0), agr, places=6)
        self.assertAlmostEqual(loss(5) - loss(5, g=0), 0, places=6)

    def test_foliage_table_a1_at_500_hz(self):
        base = loss(300, g=0)
        self.assertAlmostEqual(loss(300, g=0, fol=5) - base, 0, places=6)
        self.assertAlmostEqual(loss(300, g=0, fol=15) - base, 1, places=6)
        self.assertAlmostEqual(loss(300, g=0, fol=100) - base, 5, places=6)
        self.assertAlmostEqual(loss(300, g=0, fol=500) - base, 10, places=6)

    def test_absorption_reference_value(self):
        # ISO 9613-1 Table 1 order: ~1.9 dB/km at 500 Hz, 10 C, 70 % RH.
        self.assertAlmostEqual(run_sqf(ABS, [500, 10, 70, 1013.25]) * 1000, 1.9, delta=0.15)


class TestDriver(unittest.TestCase):
    def test_no_invented_weather_factors(self):
        src = DRIVER.read_text(encoding="utf-8")
        self.assertIn("soundPathLoss", src)
        for gone in ("InversionBoost", "_windSpeed * 0.04", "rain * 0.5"):
            self.assertNotIn(gone, src)


if __name__ == "__main__":
    unittest.main()
