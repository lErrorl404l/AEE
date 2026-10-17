#!/usr/bin/env python3
"""GPS model tests: the real constellation, geometry, range error and fix.

Runs the REAL pure kernels through tools/tests/sqf_lite.py, in the engine's
float32 where precision matters, against the Python reference in
tools/gen_gnss.py:

  fnc_gnssSatellites   the GPS SPS PS (2020) constellation at an instant
  fnc_gnssDop          the cofactor matrix (G^T G)^-1 (SPS PS App. A.8.2)
  fnc_gnssUere         FAA SPS PAN #125 measured range error by geomagnetic
                       latitude, scaled by the solar cycle
  fnc_gnssErrorEllipse covariance, eigen axes, CEP and 2DRMS
  fnc_gnssErrorStep    first-order Gauss-Markov error, tau 240 s
                       (Abu Ali & Abu-Elkheir, Sensors 15 (2015) 15540)
  fnc_gnssFixState     3D / 2D / no fix and the u-blox M8 TTFF

The datalink is tested in test_datalink.py.

Run: python3 -m unittest tools.tests.test_gnss -v
"""

from __future__ import annotations

import json
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqf_lite import run_sqf  # noqa: E402
from tools import gen_gnss as gen  # noqa: E402

GEO = ROOT / "addons" / "lib" / "functions" / "geo"
TABLES = GEO / "fnc_gnssTables.sqf"
SATS = GEO / "fnc_gnssSatellites.sqf"
DOP = GEO / "fnc_gnssDop.sqf"
UERE = GEO / "fnc_gnssUere.sqf"
ELLIPSE = GEO / "fnc_gnssErrorEllipse.sqf"
STEP = GEO / "fnc_gnssErrorStep.sqf"
FIXSTATE = GEO / "fnc_gnssFixState.sqf"
PREP = ROOT / "addons" / "lib" / "XEH_PREP.hpp"
UPDATE_SRC = (ROOT / "addons/hud/functions/hud/fnc_trackerUpdate.sqf").read_text(
    encoding="utf-8"
)


def _tables():
    return run_sqf(TABLES, [])


G = {"__FUNC__gnssTables": _tables}
T = _tables()


def satellites(dn, ut_h, lat, lon, alt_km=0.0, f32=True):
    return run_sqf(SATS, [dn, ut_h, lat, lon, -1, alt_km], G, float32=f32)


def dop(rows):
    return run_sqf(DOP, [rows], {}, float32=True)


def ellipse(d, uere):
    return run_sqf(ELLIPSE, [d, uere], {})


def fix_state(dt, count, prev):
    return run_sqf(FIXSTATE, [dt, count, prev])


class TestGeneratedTables(unittest.TestCase):
    def test_runtime_table_is_fresh(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_preps(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "gnssTables",
            "gnssSatellites",
            "gnssDop",
            "gnssUere",
            "gnssErrorEllipse",
            "gnssErrorStep",
            "gnssFixState",
        ):
            self.assertIn(f"PREPS(geo,{name})", prep)


class TestConstellation(unittest.TestCase):
    """The float32 SQF sky matches the double-precision reference."""

    CASES = [  # (dn since 2000-01-01, UT h, lat, lon)
        (9393, 6.5, 51.5, -0.1),  # 2025-09-20, London
        (9393, 18.25, -33.9, 151.2),  # Sydney
        (10200, 0.0, 0.0, 30.0),  # 2027-12-05, equator
        (8000, 12.0, 70.0, 20.0),  # 2021-11-26, Tromso
    ]

    def test_hdop_matches_the_reference(self):
        c = json.loads(gen.CONS.read_text(encoding="utf-8"))
        for dn, ut, lat, lon in self.CASES:
            with self.subTest(dn=dn, lat=lat):
                days = (dn - T["epochDay"]) + (ut - T["epochHours"]) / 24
                ref = gen.dops(c, lat, lon, days)
                sky = satellites(dn, ut, lat, lon)
                self.assertEqual(len(sky), ref[2])
                d = dop(sky)
                hdop = math.sqrt(d[1] + d[2])
                self.assertAlmostEqual(hdop, ref[0], delta=0.01)
                self.assertAlmostEqual(math.sqrt(d[4]), ref[1], delta=0.02)

    def test_every_direction_is_a_unit_vector_above_the_mask(self):
        for e, n, u in satellites(9393, 6.5, 51.5, -0.1):
            self.assertAlmostEqual(e * e + n * n + u * u, 1.0, delta=1e-4)
            self.assertGreaterEqual(math.degrees(math.asin(u)), 5.0 - 0.01)

    def test_a_typical_sky_has_eight_to_twelve_satellites(self):
        # SPS PS 2020 3.6: >= 6 in view 100 % of the time at a 5 deg mask.
        for dn, ut, lat, lon in self.CASES:
            self.assertTrue(6 <= len(satellites(dn, ut, lat, lon)) <= 14)

    def test_the_observer_height_enters_the_sky(self):
        """F8: a receiver on a hill or in the air sees a wider sky.

        The observer ECEF must take the receiver height, not the ellipsoid
        surface.  The reference (tools/gen_gnss.py) is the independent check.
        """
        c = json.loads(gen.CONS.read_text(encoding="utf-8"))
        dn, ut, lat, lon = 9393, 6.5, 51.5, -0.1
        days = (dn - T["epochDay"]) + (ut - T["epochHours"]) / 24
        low = satellites(dn, ut, lat, lon)
        self.assertEqual(low, satellites(dn, ut, lat, lon, 0.0))
        for alt in (3.0, 10.0, 400.0):
            with self.subTest(alt_km=alt):
                ref = gen.dops(c, lat, lon, days, alt_km=alt)
                sky = satellites(dn, ut, lat, lon, alt)
                self.assertNotEqual(sky, low)
                self.assertEqual(len(sky), ref[2])
                d = dop(sky)
                self.assertAlmostEqual(math.sqrt(d[1] + d[2]), ref[0], delta=0.01)
                self.assertAlmostEqual(math.sqrt(d[4]), ref[1], delta=0.02)


class TestDop(unittest.TestCase):
    def test_fewer_than_four_is_no_solution(self):
        self.assertEqual(dop([[0, 0, 1], [1, 0, 0], [0, 1, 0]])[1], -1)

    def test_a_wall_stretches_the_error_across_it(self):
        # Drop every satellite to the east: the east variance grows.
        sky = satellites(9393, 6.5, 51.5, -0.1)
        full = dop(sky)
        west = [s for s in sky if s[0] <= 0.2]
        if len(west) >= 4:
            part = dop(west)
            self.assertGreater(part[1] / part[2], full[1] / full[2])

    def test_altitude_hold_row_gives_a_2d_solution(self):
        three = satellites(9393, 6.5, 51.5, -0.1)[:3]
        d = dop(three + [[0, 0, 1, 0]])
        self.assertEqual(d[0], 4)
        self.assertGreater(d[1], 0)


class TestUere(unittest.TestCase):
    def test_measured_bands(self):
        mid = run_sqf(UERE, [50, T["ssnRef"]], G)
        eia = run_sqf(UERE, [15, T["ssnRef"]], G)
        self.assertTrue(1.0 < mid < 1.5, mid)
        self.assertGreater(eia, 3 * mid)

    def test_solar_maximum_raises_the_error(self):
        self.assertGreater(run_sqf(UERE, [50, 200], G), run_sqf(UERE, [50, 5], G))


class TestUereBandGap(unittest.TestCase):
    """F5: the band table has no 10-20 degree entry (no FAA site fell in it).

    The entries are 10-degree bin medians keyed by the bin centre, so the 5 and
    25 degree entries are 20 degrees apart.  Below the first centre and above
    the last one the nearest median holds; between two entries the value is
    their straight line.  The gap is data, not arithmetic: it must be stated,
    never read as a resolved equatorial peak.
    """

    def test_below_the_first_centre_holds_the_first_median(self):
        first = run_sqf(UERE, [5, T["ssnRef"]], G)
        for mlat in (0.0, -4.9, 4.99):
            with self.subTest(mlat=mlat):
                self.assertAlmostEqual(
                    run_sqf(UERE, [mlat, T["ssnRef"]], G), first, places=9
                )

    def test_above_the_last_centre_holds_the_last_median(self):
        last = run_sqf(UERE, [75, T["ssnRef"]], G)
        for mlat in (75.01, 85.0, 90.0):
            with self.subTest(mlat=mlat):
                self.assertAlmostEqual(
                    run_sqf(UERE, [mlat, T["ssnRef"]], G), last, places=9
                )

    def test_the_gap_is_the_straight_line_between_its_neighbours(self):
        five = run_sqf(UERE, [5, T["ssnRef"]], G)
        twenty_five = run_sqf(UERE, [25, T["ssnRef"]], G)
        for mlat, weight in ((15.0, 0.5), (10.0, 0.25), (20.0, 0.75)):
            with self.subTest(mlat=mlat):
                want = five * (1 - weight) + twenty_five * weight
                self.assertAlmostEqual(
                    run_sqf(UERE, [mlat, T["ssnRef"]], G), want, places=6
                )

    def test_the_missing_band_is_stated_in_the_table_and_the_consumer(self):
        src = UERE.read_text(encoding="utf-8")
        table = TABLES.read_text(encoding="utf-8")
        self.assertIn("10-20 degree bin", src)
        self.assertIn("interpolation", src)
        self.assertIn("10-20 degree bin", table)
        # The gap is real: no band centre sits between 5 and 25 degrees.
        self.assertNotIn([15, 3.0], [list(b) for b in T["uereBands"]])
        centres = [b[0] for b in T["uereBands"]]
        self.assertEqual(centres, sorted(centres))
        self.assertEqual(centres[:2], [5, 25])


class TestErrorEllipse(unittest.TestCase):
    def test_against_the_closed_form(self):
        q = [8, 0.5, 0.8, 0.2, 2.0]
        u = 1.3
        sE, sN, sU, a, b, orient, cep, r95, cen = ellipse(q, u)
        self.assertAlmostEqual(sE, u * math.sqrt(0.5), places=5)
        self.assertAlmostEqual(sN, u * math.sqrt(0.8), places=5)
        self.assertAlmostEqual(sU, u * math.sqrt(2.0), places=5)
        m = (0.5 + 0.8) / 2
        r = math.hypot((0.5 - 0.8) / 2, 0.2)
        self.assertAlmostEqual(a, u * math.sqrt(m + r), places=5)
        self.assertAlmostEqual(b, u * math.sqrt(m - r), places=5)
        self.assertAlmostEqual(r95, 2 * u * math.sqrt(1.3), places=5)
        self.assertAlmostEqual(cep, 0.59 * (a + b), places=5)
        # Major axis bearing: eigenvector of [[qEE, qEN], [qEN, qNN]].
        ang = 0.5 * math.degrees(math.atan2(2 * 0.2, 0.5 - 0.8))
        self.assertAlmostEqual(orient, (90 - ang) % 180, places=3)

    def test_circular_geometry_points_north(self):
        out = ellipse([8, 1, 1, 0, 1], 2)
        self.assertAlmostEqual(out[3], out[4], places=6)

    def test_east_west_spread_points_east(self):
        self.assertAlmostEqual(ellipse([8, 4, 1, 0, 1], 1)[5], 90, places=4)
        self.assertAlmostEqual(ellipse([8, 1, 4, 0, 1], 1)[5], 0, places=4)

    def test_no_solution(self):
        self.assertEqual(ellipse([3, -1, -1, -1, -1], 1.3)[7], -1)


class TestErrorStep(unittest.TestCase):
    ELL = [3.0, 2.0, 5.0, 3.0, 2.0, 90, 0, 0, 0.0]

    def test_first_draw_is_the_fix_covariance(self):
        # u2 = 0: z1 = r, z2 = 0.
        e, n = run_sqf(STEP, [[], self.ELL, 1, math.exp(-0.5), 0])
        self.assertAlmostEqual(e, 3.0, places=4)
        self.assertAlmostEqual(n, 0.0, places=4)

    def test_gauss_markov_decay(self):
        # With w = 0 (u1 = 1, so r = 0) the error decays by exp(-dt / 240).
        e, n = run_sqf(STEP, [[10, -4], self.ELL, 60, 1, 0.3])
        self.assertAlmostEqual(e, 10 * math.exp(-0.25), places=4)
        self.assertAlmostEqual(n, -4 * math.exp(-0.25), places=4)

    def test_stationary_variance(self):
        rnd = random.Random(7)
        err = []
        x = []
        for _ in range(3000):
            x = run_sqf(STEP, [x, self.ELL, 30, rnd.random(), rnd.random()])
            err.append(x)
        ve = sum(p[0] ** 2 for p in err[200:]) / len(err[200:])
        vn = sum(p[1] ** 2 for p in err[200:]) / len(err[200:])
        self.assertAlmostEqual(math.sqrt(ve), 3.0, delta=0.4)
        self.assertAlmostEqual(math.sqrt(vn), 2.0, delta=0.3)


class TestFixState(unittest.TestCase):
    def test_satellite_counts(self):
        # A receiver holding a fix (timeSinceFix 0) reports its counts at once:
        # 8 satellites 3D, 3 satellites 2D, fewer no fix.
        self.assertEqual(fix_state(1, 8, [0, 0])[0], "ok")
        self.assertEqual(fix_state(1, 3, [0, 0])[0], "degraded")
        self.assertEqual(fix_state(1, 2, [0, 0])[0], "none")

    def test_the_first_fix_is_a_cold_start(self):
        # F6: a receiver switching on holds no almanac or ephemeris, so the
        # first call with satellites in view is the 26 s cold start, not "ok".
        quality, since, acquire = fix_state(1, 8, [])
        self.assertEqual(quality, "none")
        self.assertAlmostEqual(since, 1.0)
        self.assertAlmostEqual(acquire, 25.0)

    def test_the_first_fix_arrives_after_26_seconds(self):
        state = []
        seconds = 0
        quality = "none"
        while seconds < 60:
            quality, since, acquire = fix_state(1, 8, state)
            state = [since, acquire]
            seconds += 1
            if quality == "ok":
                break
        self.assertEqual(quality, "ok")
        self.assertEqual(seconds, 26)

    def test_a_short_outage_is_a_hot_start(self):
        s = [0, 0]
        for _ in range(30):
            s = fix_state(1, 0, s)[1:]
        q1, since, acq = fix_state(0.5, 8, s)
        self.assertEqual(q1, "none")
        self.assertAlmostEqual(acq, 0.5)
        self.assertEqual(fix_state(0.5, 8, [since, acq])[0], "ok")

    def test_a_long_outage_is_a_cold_start(self):
        out = fix_state(1, 8, [5 * 3600, 0])
        self.assertEqual(out[0], "none")
        self.assertAlmostEqual(out[2], 25)
        self.assertIn("UBX-15031086", FIXSTATE.read_text(encoding="utf-8"))


class TestTrackerUsesTheModel(unittest.TestCase):
    def test_wiring(self):
        for token in (
            "gnssSatellites",
            "gnssDop",
            "gnssUere",
            "gnssErrorEllipse",
            "gnssErrorStep",
            "gnssFixState",
            "gameClockToUT",
            "terrainIntersectASL",
            "lineIntersectsSurfaces",
            "QEGVAR(weather,sunspotNumber)",
            "QEGVAR(weather,geomagneticLatitude)",
        ):
            self.assertIn(token, UPDATE_SRC)
        for token in ("UNSOURCED", "currentHumidity", "nearestTerrainObjects"):
            self.assertNotIn(token, UPDATE_SRC)


if __name__ == "__main__":
    unittest.main()
