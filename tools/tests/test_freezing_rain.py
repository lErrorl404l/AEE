#!/usr/bin/env python3
"""Freezing rain (fnc_calculateFreezingRain): the phase from the wet-bulb
model and the Jones 1998 radial ice accretion.

Run: python3 -m unittest tools.tests.test_freezing_rain -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

K = REPO / "addons/thermal/functions/environment/fnc_calculateFreezingRain.sqf"


def run(phase, rain):
    store = {}
    g = {
        "missionNamespace": {"__QEGVAR__core_precipitationPhase": phase},
        "rain": rain,
        "ENGINE_RAIN_FULL_MMH": 25,
        "setVariable": lambda *a: store.update({a[-1][0]: a[-1][1]}) if isinstance(a[-1], list) else None,
    }
    out = run_sqf(K, [], g)
    return out, store


class TestFreezingRain(unittest.TestCase):
    def test_source_uses_the_phase_and_jones(self):
        src = K.read_text(encoding="utf-8")
        self.assertIn("QEGVAR(core,precipitationPhase)", src)
        self.assertIn("1000 / (pi * 900)", src)
        self.assertIn("6.35", src)
        self.assertNotIn("overcast > 0.6", src)

    def test_jones_accretion(self):
        # 2.5 mm/h of freezing rain: 2.5 * 1000 / (pi 900) = 0.884 mm/h radial.
        self.assertAlmostEqual(2.5 * 1000 / (math.pi * 900), 0.884, places=3)


if __name__ == "__main__":
    unittest.main()
