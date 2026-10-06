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
FORMAT = GEO / "fnc_formatMgrs.sqf"
PARSE = GEO / "fnc_parseMgrs.sqf"
PREP = ROOT / "addons" / "core" / "XEH_PREP.hpp"
PREINIT = ROOT / "addons" / "core" / "XEH_preInit.sqf"
TABLES = ROOT / "addons" / "core" / "data" / "mgrs_tables.sqf"


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
        # The northern hemisphere and the equator.
        for lat, lon in [
            (40.7128, -74.0060),
            (39.906515, 25.246742),
            (0.0, 0.0),
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
        # The southern hemisphere carries the 10000000 false northing.
        for lat, lon in [(-33.8688, 151.2093), (-17.698, 178.783)]:
            e, n, zone, hemi = forward(lat, lon)
            self.assertEqual(hemi, "south")
            back_lat, back_lon = inverse(e, n, zone, hemi)
            self.assertLess(
                metres_between(lat, lon, back_lat, back_lon),
                0.001,
                f"southern round-trip {lat},{lon} drifted",
            )
        # The Sydney fixture also holds to the strict 1e-7 degree tolerance.
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


def mgrs_globals():
    """The real generated letter tables and the real inverse UTM kernel."""
    return {
        "aee_core_mgrsTables": run_sqf(TABLES, []),
        "__FUNC__utmToLatLon": lambda e, n, z, h: run_sqf(INVERSE, [e, n, z, h]),
    }


def format_mgrs(easting, northing, zone, precision, latitude):
    return run_sqf(
        FORMAT, [easting, northing, zone, precision, latitude], mgrs_globals()
    )


def parse_mgrs(text):
    return run_sqf(PARSE, [text], mgrs_globals())


# MGRS vectors.  (easting, northing, zone, latitude, MGRS string)
#
# Vector 1 is the figure example published in the NGA MGRS guidance
# (Modified February 2009): 15SWC8081751205 at one-metre refinement.  Its
# latitude comes from PROJ cs2cs, which maps 580817 4251205, zone 15N, to
# 38.405426 N.
#
# Vector 2 is the same guidance's published UTM pair for 92 W 38 N:
# 587798 m E, 4206287 m N, zone 15.  PROJ cs2cs maps that pair back to
# 38.000002 N, 92.000005 W, confirming the pair.  The string is the
# published lettering applied to the published UTM.
#
# Vectors 3 and 4 are independent: the UTM is from PROJ cs2cs, the MGRS
# string is from the NGA GeoTrans implementation (the `mgrs` Python package,
# MGRSPrecision=5), a separate oracle.  Vector 4 (New York) is an EVEN zone,
# so it is the vector that proves the AA even-zone row offset of five.
NGA_FIGURE = (580817, 4251205, 15, 38.405426, "15SWC8081751205")
NGA_92W38N = (587798, 4206287, 15, 38.000002, "15SWC8779806287")
ALTIS_CENTRE_MGRS = (350134.3482, 4418852.6483, 35, 39.906515, "35SLE5013418852")
NYC_MGRS = (583959.3723, 4507350.9982, 18, 40.7128, "18TWL8395907350")
MGRS_VECTORS = [NGA_FIGURE, NGA_92W38N, ALTIS_CENTRE_MGRS, NYC_MGRS]


class TestFormatMgrs(unittest.TestCase):
    def test_known_mgrs_vectors(self):
        for easting, northing, zone, latitude, expected in MGRS_VECTORS:
            got = format_mgrs(easting, northing, zone, 10, latitude)
            self.assertEqual(got, expected, f"{easting},{northing} zone {zone}")

    def test_even_zone_uses_row_offset_five(self):
        # New York is zone 18 (even).  Its 100 km row is L, which is A + 10:
        # the row index 5 shifted by the AA offset of 5.  Without the offset
        # the square would be WF, not WL.
        easting, northing, zone, latitude, expected = NYC_MGRS
        got = format_mgrs(easting, northing, zone, 10, latitude)
        self.assertEqual(got[3:5], "WL")
        self.assertEqual(got, expected)

    def test_truncates_and_never_rounds(self):
        # Within square WC: easting 580899.0 and northing 4251299.0.  At 100 m
        # precision the digit groups are 808 and 512, the TRUNCATED values.
        # A rounding formatter would give 809 and 513.
        got = format_mgrs(580899, 4251299, 15, 6, 38.405426)
        self.assertEqual(got, "15SWC808512")
        self.assertNotEqual(got, "15SWC809513")

    def test_precision_digit_counts(self):
        # 2/4/6/8/10 digits is 10 km / 1 km / 100 m / 10 m / 1 m.
        for precision in (2, 4, 6, 8, 10):
            got = format_mgrs(580817, 4251205, 15, precision, 38.405426)
            self.assertEqual(len(got), 5 + precision)
            self.assertTrue(got.startswith("15SWC"))

    def test_out_of_range_returns_empty(self):
        self.assertEqual(format_mgrs(580817, 4251205, 0, 10, 38.0), "")
        self.assertEqual(format_mgrs(580817, 4251205, 61, 10, 38.0), "")
        self.assertEqual(format_mgrs(580817, 4251205, 15, 7, 38.0), "")


class TestParseMgrs(unittest.TestCase):
    def test_known_mgrs_vectors(self):
        for easting, northing, zone, _latitude, text in MGRS_VECTORS:
            got = parse_mgrs(text)
            self.assertEqual(got[2], zone)
            self.assertAlmostEqual(got[0], easting, delta=1.0)
            self.assertAlmostEqual(got[1], northing, delta=1.0)

    def test_parse_returns_band(self):
        self.assertEqual(parse_mgrs("15SWC8081751205")[3], "S")
        self.assertEqual(parse_mgrs("18TWL8395907350")[3], "T")

    def test_round_trip_through_parse(self):
        for easting, northing, zone, latitude, text in MGRS_VECTORS:
            got = format_mgrs(*parse_mgrs(text)[:3], 10, latitude)
            self.assertEqual(got, text)

    def test_malformed_returns_empty(self):
        self.assertEqual(parse_mgrs(""), [])
        self.assertEqual(parse_mgrs("15S"), [])
        self.assertEqual(parse_mgrs("15SWC123"), [])
        self.assertEqual(parse_mgrs("99SWC8081751205"), [])

    def test_letter_inside_the_digits_returns_empty(self):
        # A letter inside the east or north digit group must be malformed
        # input, not a wrong coordinate.  The old accumulator returned a
        # coordinate for each of these.
        self.assertEqual(parse_mgrs("15SWCABCDE12345"), [])
        self.assertEqual(parse_mgrs("15SWC12345ABCDE"), [])
        self.assertEqual(parse_mgrs("15SWC12A45B7890"), [])


class TestMgrsSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,formatMgrs)", prep)
        self.assertIn("PREPS(geo,parseMgrs)", prep)

    def test_preinit_loads_the_generated_table(self):
        preinit = PREINIT.read_text(encoding="utf-8")
        self.assertIn("mgrs_tables.sqf", preinit)
        self.assertIn("aee_core_mgrsTables", preinit)

    def test_format_records_the_latitude_deviation(self):
        src = FORMAT.read_text(encoding="utf-8")
        self.assertIn("DESIGN DEVIATION", src)
        self.assertIn("_latitude", src)
        # The digits label the south-west corner and are truncated.
        self.assertIn("TRUNCATED", src)

    def test_parse_calls_the_inverse_utm_kernel(self):
        src = PARSE.read_text(encoding="utf-8")
        # Assert the CALL FORM, not the bare name, which also sits in comments.
        self.assertIn("call FUNC(utmToLatLon)", src)
        self.assertIn("aee_core_mgrsTables", src)


class TestMgrsTableIntegrity(unittest.TestCase):
    """The generated letter table equals the published MGRS lettering.

    Each row of addons/core/data/mgrs_tables.sqf is one table.  The
    published sets are from DMA TM 8358.1, DMA TM 8358.2 and the NGA MGRS
    guidance (Modified February 2009).  One test per table row, so a
    mutation of one row turns exactly one test red.
    """

    @classmethod
    def setUpClass(cls):
        # Run the REAL generated table through the harness.  A letter
        # outside the published set would break the MGRS kernels.
        cls.tables = run_sqf(TABLES, [])

    def test_band_letters_row_is_the_published_set(self):
        self.assertEqual(self.tables[0], list("CDEFGHJKLMNPQRSTUVWX"))

    def test_column_sets_row_is_the_published_sets(self):
        self.assertEqual(
            self.tables[1],
            [list("ABCDEFGH"), list("JKLMNPQR"), list("STUVWXYZ")],
        )

    def test_row_letters_row_is_the_published_set(self):
        self.assertEqual(self.tables[2], list("ABCDEFGHJKLMNPQRSTUV"))

    def test_even_zone_row_offset_row_is_the_aa_offset(self):
        # The AA scheme (WGS84) starts even zones at F, index 5.
        self.assertEqual(self.tables[3], 5)

    def test_zone_strings_row_is_01_to_60(self):
        self.assertEqual(self.tables[4], [f"{zone:02d}" for zone in range(1, 61)])

    def test_digit_characters_row_is_0_to_9(self):
        self.assertEqual(self.tables[5], list("0123456789"))


if __name__ == "__main__":
    unittest.main()
