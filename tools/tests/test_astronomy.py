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
CIVIL = REPO / "addons/lib/functions/fnc_civilDayNumber.sqf"
VAL = REPO / "data/astronomy/validation"
SITES = {"lemnos_2024-01-15": (39.9, 25.25), "fiji_2035-06-20": (-17.70, 178.78)}
MONTHS = {
    m: i + 1
    for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())
}


def julian_day(y: int, m: int, d: int, ut_h: float) -> float:
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (y + 4716))
        + math.floor(30.6001 * (m + 1))
        + d
        + b
        - 1524.5
        + ut_h / 24
    )


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
        yield (
            julian_day(int(y), MONTHS[mon], int(d), hh + mm / 60),
            float(cols[5]),
            float(cols[6]),
        )


def ang_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def meeus_sun_apparent(dn: int, ut_h: float):
    """The kernel's sun arguments (Meeus ch. 25) in doubles.

    Returns (L0, alpha, eps, dpsi): mean longitude, apparent right ascension,
    true obliquity and the leading nutation in longitude, in degrees.
    """
    days = dn - 0.5 + ut_h / 24
    t = days / 36525
    l0 = (280.46646 + 0.98564736016 * days + 0.0003032 * t * t) % 360
    m = (357.52911 + 0.98560028172 * days - 0.0001537 * t * t) % 360
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(math.radians(m))
        + (0.019993 - 0.000101 * t) * math.sin(math.radians(2 * m))
        + 0.000289 * math.sin(math.radians(3 * m))
    )
    omega = 125.04 - 0.05295376 * days
    dpsi = -0.00478 * math.sin(math.radians(omega))
    lam = l0 + c - 0.00569 + dpsi
    eps0 = (
        23 + (26 + ((21.448 - t * (46.815 + t * (0.00059 - 0.001813 * t))) / 60)) / 60
    )
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    alpha = (
        math.degrees(
            math.atan2(
                math.cos(math.radians(eps)) * math.sin(math.radians(lam)),
                math.cos(math.radians(lam)),
            )
        )
        % 360
    )
    return l0, alpha, eps, dpsi


def nutation_eot_minutes(dn: int, ut_h: float) -> float:
    """The dpsi*cos(eps) term of Meeus 28.1, in minutes of time."""
    _l0, _alpha, eps, dpsi = meeus_sun_apparent(dn, ut_h)
    return 4 * dpsi * math.cos(math.radians(eps))


def meeus_equation_of_time(dn: int, ut_h: float) -> float:
    """Meeus (1998) eq. 28.1: E = L0 - 0.0057183 - alpha + dpsi*cos(eps)."""
    l0, alpha, eps, dpsi = meeus_sun_apparent(dn, ut_h)
    e = l0 - 0.0057183 - alpha + dpsi * math.cos(math.radians(eps))
    return 4 * ((e + 180) % 360 - 180)


# Instants where the nutation in longitude is near its extreme (Omega at 90 or
# 270 deg), so the dpsi*cos(eps) term is at its largest.
EOT_INSTANTS = ((7460, 6.5), (10864, 18.25), (14258, 0.0), (4066, 12.0))


class TestEquationOfTime(unittest.TestCase):
    """F9: the equation of time carries the nutation term (Meeus 28.1).

    The kernel's apparent solar longitude already holds the leading nutation in
    longitude dpsi (Meeus 25.9); the equation of time needs dpsi*cos(eps) as
    well, or it is short by up to 0.0044 deg, about 1 s.
    """

    def test_the_test_instants_are_sensitive_to_the_term(self):
        for dn, ut in EOT_INSTANTS:
            with self.subTest(dn=dn):
                self.assertGreater(abs(nutation_eot_minutes(dn, ut)), 0.01)

    def test_matches_meeus_28_1(self):
        for dn, ut in EOT_INSTANTS:
            with self.subTest(dn=dn, ut=ut):
                got = run_sqf(KERNEL, [dn, ut, 0.0, 0.0], {}, float32=True)[1]
                self.assertAlmostEqual(got, meeus_equation_of_time(dn, ut), delta=0.005)


def kernel(jd: float, lat: float, lon: float):
    dn, ut = day_ut(jd)
    return run_sqf(KERNEL, [dn, ut, lat, lon], {}, float32=True)


class TestAgainstHorizons(unittest.TestCase):
    def _check(self, body: int, alt_i: int, az_i: int, tol: float):
        for site, (lat, lon) in SITES.items():
            for jd, az, alt in horizons(body, site):
                got = kernel(jd, lat, lon)
                self.assertLess(
                    abs(got[alt_i] - alt), tol, f"{site} body {body} alt at JD {jd}"
                )
                if abs(alt) < 85:
                    self.assertLess(
                        ang_diff(got[az_i], az),
                        tol / max(math.cos(math.radians(alt)), 0.2),
                        f"{site} body {body} az at JD {jd}",
                    )

    def test_sun(self):
        self._check(10, 2, 3, 0.05)

    def test_moon(self):
        self._check(301, 5, 6, 0.6)


class TestGameClock(unittest.TestCase):
    def test_noon_is_solar_transit(self):
        # The engine's 12:00 is local apparent noon: the sun must transit
        # (azimuth 180 in the north, 0/360 in the south) at clock 12:00.
        for date, lat, lon in (
            ([2024, 1, 15], 39.9, 25.25),
            ([2035, 6, 21], -17.7, 178.78),
            ([2035, 11, 3], 54.0, 23.0),
        ):
            astro = lambda *a: run_sqf(KERNEL, list(a), {}, float32=True)  # noqa: E731
            civil = lambda *a: run_sqf(CIVIL, list(a), {}, float32=True)  # noqa: E731
            dn, ut = run_sqf(
                CLOCK,
                [date, 12.0, lon],
                {"__FUNC__astroPosition": astro, "__FUNC__civilDayNumber": civil},
                float32=True,
            )
            res = astro(dn, ut, lat, lon)
            az = res[3]
            target = 180 if lat > res[4] else 0
            self.assertLess(ang_diff(az, target), 0.05, f"{date} transit azimuth {az}")


if __name__ == "__main__":
    unittest.main()
