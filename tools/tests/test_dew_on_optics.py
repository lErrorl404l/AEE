#!/usr/bin/env python3
"""Lens fogging (fnc_calculateDewOnOptics): the lumped optic against the
dew point, Hilpert convection and Idso sky radiation, run from the real SQF.

Run: python3 -m unittest tools.tests.test_dew_on_optics -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

K = REPO / "addons/optics/functions/sensor/fnc_calculateDewOnOptics.sqf"


def run(t, rh, wind, overcast, steps=40):
    ns = {
        "__QEGVAR__core_currentTemperature": t,
        "__QEGVAR__core_currentHumidity": rh,
        "__QEGVAR__core_currentWind": [wind, 0],
        "__QEGVAR__core_updateInterval": 60,
        "__QGVAR__dewAccumRate": 0.05,
        "__QGVAR__dewDecayRate": 0.02,
    }

    g = {"missionNamespace": ns, "overcast": overcast, "random": lambda x: 0.0}
    out = 0
    for _ in range(steps):
        out = run_sqf(K, [], g)
    return out, ns.get("__QGVAR__lensTemperature")


class TestDew(unittest.TestCase):
    def test_calm_clear_humid_night_fogs(self):
        fog, t_lens = run(10, 95, 0.5, 0)
        self.assertGreater(fog, 0.5)
        self.assertLess(t_lens, 9.2)

    def test_wind_keeps_the_lens_at_the_air(self):
        self.assertEqual(run(10, 95, 6, 0)[0], 0)

    def test_overcast_stops_radiative_cooling(self):
        self.assertEqual(run(10, 95, 0.5, 1)[0], 0)

    def test_dry_air_never_fogs(self):
        self.assertEqual(run(20, 50, 0.5, 0)[0], 0)


if __name__ == "__main__":
    unittest.main()
