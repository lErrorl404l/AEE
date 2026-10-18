#!/usr/bin/env python3
"""Rain drops on a lens (fnc_calculateRainOnOptics): the ISO 15927-3 / Lacy
wind-driven rain flux on a vertical lens, Marshall-Palmer drops, and the
wetted-fraction growth law, from the real SQF.

Run: python3 -m unittest tools.tests.test_rain_on_optics
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

K = REPO / "addons/optics/functions/sensor/fnc_calculateRainOnOptics.sqf"


def step(rain, wind, prev=0.0, dt=60):
    ns = {"__QGVAR__rainOnOptics": prev, "__QEGVAR__core_updateInterval": dt,
          "__QEGVAR__core_currentWind": [wind, 0], "__QGVAR__rainDecayRate": 0.02,
          "__QEGVAR__core_opticsEnabled": True}
    return run_sqf(K, [], {"missionNamespace": ns, "rain": rain, "ENGINE_RAIN_FULL_MMH": 25})


class TestRainOnOptics(unittest.TestCase):
    def test_growth_law(self):
        r, v, dt = 10.0, 5.0, 60
        q = (2 / 9) * v * r ** (8 / 9) / 1000 / 3600
        d0 = 0.89e-3 * r ** 0.21
        a = (d0 ** 3 / 4) ** (1 / 3)
        self.assertAlmostEqual(step(r / 25, v, 0, dt), 1 - math.exp(-q * dt / (2 / 3 * a)), places=9)

    def test_windier_rain_wets_faster(self):
        self.assertGreater(step(0.4, 8), step(0.4, 1))

    def test_dry_weather_clears(self):
        self.assertAlmostEqual(step(0, 3, 0.5, 5), 0.48, places=9)


if __name__ == "__main__":
    unittest.main()
