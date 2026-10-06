#!/usr/bin/env python3
"""WGS84 / UTM kernel tests (MGRS wave 1, task 2).

Runs the REAL forward and inverse kernels
  addons/core/functions/geo/fnc_latLonToUtm.sqf
  addons/core/functions/geo/fnc_utmToLatLon.sqf
through tools/tests/sqf_lite.py.

The series is the transverse Mercator expansion in DMA TM 8358.2 with the
WGS84 ellipsoid (a=6378137, 1/f=298.257223563, k0=0.9996, FE=500000,
FN=0 north / 10000000 south).  The known-coordinate fixtures are published
WGS84 UTM values produced by PROJ (cs2cs), which is the authoritative
reference implementation.

Task 4 extends this file with the MGRS lettering tests.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "addons" / "core" / "functions" / "geo"
FORWARD = GEO / "fnc_latLonToUtm.sqf"
INVERSE = GEO / "fnc_utmToLatLon.sqf"
PREP = ROOT / "addons" / "core" / "XEH_PREP.hpp"


def forward(lat, lon):
    return run_sqf(FORWARD, [lat, lon])


def inverse(easting, northing, zone, hemisphere):
    return run_sqf(INVERSE, [easting, northing, zone, hemisphere])


def metres_between(lat1, lon1, lat2, lon2):
    """Local tangent-plane distance, metres, good over short spans."""
    mid = math.radians((lat1 + lat2) / 2)
    dx = (lon1 - lon2) * 111320.0 * math.cos(mid)
    dy = (lat1 - lat2) * 111320.0
    return math.hypot(dx, dy)


# Published WGS84 UTM values from PROJ cs2cs (2026-10-06).
NYC = (40.7128, -74.0060, 18, "north", 583959.3723, 4507350.9982)
SYDNEY = (-33.8688, 151.2093, 56, "south", 334368.6336, 6250948.3454)
ALTIS_CENTRE = (39.906515, 25.246742, 35, "north", 350134.3482, 4418852.6483)
EQUATOR = (0.0, 0.0, 31, "north", 166021.4431, 0.0)


class TestForwardKernel(unittest.TestCase):
    def test_known_wgs84_reference_nyc(self):
        e, n, zone, hemi = forward(NYC[0], NYC[1])
        self.assertEqual(zone, NYC[2])
        self.assertEqual(hemi, NYC[3])
        self.assertAlmostEqual(e, NYC[4], delta=1.0)
        self.assertAlmostEqual(n, NYC[5], delta=1.0)

    def test_known_wgs84_reference_altis_centre(self):
        e, n, zone, hemi = forward(ALTIS_CENTRE[0], ALTIS_CENTRE[1])
        self.assertEqual(zone, ALTIS_CENTRE[2])
        self.assertEqual(hemi, "north")
        self.assertAlmostEqual(e, ALTIS_CENTRE[4], delta=1.0)
        self.assertAlmostEqual(n, ALTIS_CENTRE[5], delta=1.0)

    def test_southern_false_northing_applied(self):
        e, n, zone, hemi = forward(SYDNEY[0], SYDNEY[1])
        self.assertEqual(zone, 56)
        self.assertEqual(hemi, "south")
        # The 10000000 false northing makes the value positive and large.
        self.assertGreater(n, 5000000)
        self.assertAlmostEqual(e, SYDNEY[4], delta=1.0)
        self.assertAlmostEqual(n, SYDNEY[5], delta=1.0)

    def test_equator_zone_and_northing_zero(self):
        e, n, zone, hemi = forward(EQUATOR[0], EQUATOR[1])
        self.assertEqual(zone, 31)
        self.assertEqual(hemi, "north")
        self.assertAlmostEqual(n, 0.0, delta=1.0)
        self.assertAlmostEqual(e, EQUATOR[4], delta=1.0)

    def test_zone_clamped_to_1_and_60(self):
        self.assertEqual(forward(0.0, -180.0)[2], 1)
        self.assertEqual(forward(0.0, 180.0)[2], 60)


class TestInverseKernel(unittest.TestCase):
    def test_round_trip_within_1mm(self):
        for lat, lon in [
            (40.7128, -74.0060),
            (-33.8688, 151.2093),
            (39.906515, 25.246742),
            (0.0, 0.0),
            (-17.698, 178.783),
            (54.0, 23.0),
        ]:
            e, n, zone, hemi = forward(lat, lon)
            back_lat, back_lon = inverse(e, n, zone, hemi)
            self.assertLess(
                metres_between(lat, lon, back_lat, back_lon),
                0.001,
                f"round-trip {lat},{lon} drifted",
            )

    def test_southern_round_trip(self):
        e, n, zone, hemi = forward(SYDNEY[0], SYDNEY[1])
        back_lat, back_lon = inverse(e, n, zone, hemi)
        self.assertAlmostEqual(back_lat, SYDNEY[0], places=7)
        self.assertAlmostEqual(back_lon, SYDNEY[1], places=7)


class TestUtmSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,latLonToUtm)", prep)
        self.assertIn("PREPS(geo,utmToLatLon)", prep)

    def test_wgs84_constants_present(self):
        src = FORWARD.read_text(encoding="utf-8")
        self.assertIn("6378137", src)
        self.assertIn("298.257223563", src)
        self.assertIn("0.9996", src)
        self.assertIn("500000", src)


if __name__ == "__main__":
    unittest.main()
