#!/usr/bin/env python3
"""Diurnal air temperature: Parton & Logan (1981), APSIM implementation.

The day-and-night formula in fnc_updateTemperature.sqf is checked against
the published example of the APSIM port (weaana::diurnalT, maxt 20,
mint 10, doy 1, latitude -10 (radians, as the example passes it), A 1.5, B 4, C 1: 10.609 C at 01:00 and
19.328 C at 12:30), with the APSIM day length.  The runtime then uses the
real day length from the sun's declination.

Run: python3 -m unittest tools.tests.test_diurnal_temperature
"""

from __future__ import annotations

import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = (REPO / "addons/thermal/functions/environment/fnc_updateTemperature.sqf").read_text(encoding="utf-8")


def apsim_day_length(doy: int, lat_rad: float) -> float:
    delt = 0.4014 * math.sin(2 * math.pi * (doy - 77.0) / 365.0)
    t1 = math.sqrt(1.0 - (-math.tan(lat_rad) * delt) ** 2)
    t2 = -math.tan(lat_rad) * math.tan(delt)
    return math.atan2(t1, t2) / math.pi * 24.0


def parton_logan(tmax, tmin, hour, day_len, a=1.5, b=4.0, c=1.0):
    """The formula as written in fnc_updateTemperature.sqf."""
    rise = 12 - day_len / 2 + c
    sset = 12 + day_len / 2
    if rise <= hour < sset:
        return tmin + (tmax - tmin) * math.sin(math.pi * (hour - rise) / (day_len + 2 * a))
    since = hour - sset if hour >= sset else (24 - sset) + hour
    tset = tmin + (tmax - tmin) * math.sin(math.pi * (day_len - c) / (day_len + 2 * a))
    return tmin + (tset - tmin) * math.exp(-b * since / (24 - day_len))


class TestPartonLogan(unittest.TestCase):
    def test_reproduces_the_apsim_example(self):
        # weaana takes latitude in radians; its example passes -10 (radians).
        y = apsim_day_length(1, -10.0)
        self.assertAlmostEqual(parton_logan(20, 10, 1.0, y), 10.60904, places=4)
        # weaana output element 116 (hour 12.5): 19.32782
        self.assertAlmostEqual(parton_logan(20, 10, 12.5, y), 19.32782, places=4)

    def test_sqf_carries_the_formula(self):
        for token in ("private _A = 1.5;", "private _B = 4;", "private _C = 1;",
                      "(sin (180 * (_hour - _rise) / (_dayLen + 2 * _A)))",
                      "exp (-_B * _since / (24 - _dayLen))", "(sin -0.833)"):
            self.assertIn(token, SRC)

    def test_no_invented_air_temperature_terms(self):
        for token in ("4 * overcast", "_surfaceMod", "_windChillJAGTTI", "[0, 3] select _inShade"):
            self.assertNotIn(token, SRC)

    def test_peak_follows_noon_and_minimum_follows_sunrise(self):
        y = 12.0
        temps = [(h / 10, parton_logan(30, 15, h / 10, y)) for h in range(0, 240)]
        peak_h = max(temps, key=lambda t: t[1])[0]
        low_h = min(temps, key=lambda t: t[1])[0]
        self.assertTrue(13.0 <= peak_h <= 15.0, peak_h)
        self.assertTrue(6.0 <= low_h <= 7.5, low_h)


if __name__ == "__main__":
    unittest.main()
