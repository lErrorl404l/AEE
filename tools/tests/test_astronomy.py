#!/usr/bin/env python3
"""Sun and moon positions against JPL Horizons.

The kernel addons/lib/functions/astronomy/fnc_astroPosition.sqf is EXECUTED
(tools/tests/sqf_lite.py) and compared with JPL Horizons observer
ephemerides (topocentric, airless) saved under data/astronomy/validation:
Lemnos (Altis) January 2024 and Fiji (Tanoa) June 2035.

Every run is in float32, the engine's number type.  Tolerances: sun 0.05 deg (Meeus low accuracy is ~0.01 deg); moon 0.6 deg
(Astronomical Almanac low-precision series, ~0.3 deg plus parallax).

Run: python3 -m unittest tools.tests.test_astronomy
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.tests.sqf_lite import run_sqf  # noqa: E402

KERNEL = REPO / "addons/lib/functions/astronomy/fnc_astroPosition.sqf"
CLOCK = REPO / "addons/lib/functions/astronomy/fnc_gameClockToUT.sqf"
VAL = REPO / "data/astronomy/validation"
SITES = {"lemnos_2024-01-15": (39.9, 25.25), "fiji_2035-06-20": (-17.70, 178.78)}
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def julian_day(y: int, m: int, d: int, ut_h: float) -> float:
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5 + ut_h / 24


def day_ut(jd: float) -> tuple[int, float]:
    """[days since 2000-01-01 00:00 UT, UT hours] of a Julian Day."""
    d = jd - 2451544.5
    dn = math.floor(d)
    return dn, (d - dn) * 24


def horizons(body: int, site: str):
    text = (VAL / f"horizons_{body}_{site}.txt").read_text(encoding="utf-8")
    rows = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    for row in rows:
        cols = [c.strip() for c in row.split(",")]
        date, clock = cols[0].split()
        y, mon, d = date.split("-")
        hh, mm = map(int, clock.split(":"))
        yield julian_day(int(y), MONTHS[mon], int(d), hh + mm / 60), float(cols[5]), float(cols[6])


def ang_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def kernel(jd: float, lat: float, lon: float):
    dn, ut = day_ut(jd)
    return run_sqf(KERNEL, [dn, ut, lat, lon], {}, float32=True)


class TestAgainstHorizons(unittest.TestCase):
    def _check(self, body: int, alt_i: int, az_i: int, tol: float):
        for site, (lat, lon) in SITES.items():
            for jd, az, alt in horizons(body, site):
                got = kernel(jd, lat, lon)
                self.assertLess(abs(got[alt_i] - alt), tol, f"{site} body {body} alt at JD {jd}")
                if abs(alt) < 85:
                    self.assertLess(ang_diff(got[az_i], az), tol / max(math.cos(math.radians(alt)), 0.2),
                                    f"{site} body {body} az at JD {jd}")

    def test_sun(self):
        self._check(10, 2, 3, 0.05)

    def test_moon(self):
        self._check(301, 5, 6, 0.6)


class TestGameClock(unittest.TestCase):
    def test_noon_is_solar_transit(self):
        # The engine's 12:00 is local apparent noon: the sun must transit
        # (azimuth 180 in the north, 0/360 in the south) at clock 12:00.
        for date, lat, lon in (([2024, 1, 15], 39.9, 25.25), ([2035, 6, 21], -17.7, 178.78),
                               ([2035, 11, 3], 54.0, 23.0)):
            astro = lambda *a: run_sqf(KERNEL, list(a), {}, float32=True)  # noqa: E731
            dn, ut = run_sqf(CLOCK, [date, 12.0, lon], {"__FUNC__astroPosition": astro}, float32=True)
            res = astro(dn, ut, lat, lon)
            az = res[3]
            target = 180 if lat > res[4] else 0
            self.assertLess(ang_diff(az, target), 0.05, f"{date} transit azimuth {az}")


if __name__ == "__main__":
    unittest.main()
