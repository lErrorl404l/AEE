#!/usr/bin/env python3
"""World geographic anchor contract and kernel tests (MGRS wave 1, task 1).

Runs the REAL addons/core/functions/geo/fnc_buildGeoAnchor.sqf through
tools/tests/sqf_lite.py with fixtures that supply the raw CfgWorlds values.

The anchor schema is 9 elements:
  [latCentre, lonCentre, zone, mapSize, lonWest, latSouth, lonEast, latNorth,
   sourceToken]

mapArea[] element order is authoritative from BIS itself.  The shipped
Addons/functions_f/a3/functions_f/Map/fn_posDegtoWorld.sqf reads
  [mapArea select 0, mapArea select 1] -> bottom-left
  [mapArea select 2, mapArea select 3] -> top-right
and passes each pair to bis_fnc_posDegToUTM, whose parameter 0 is longitude
and parameter 1 is latitude.  Therefore
  mapArea = [lonWest, latSouth, lonEast, latNorth].
Re-read from the installed world configs on 2026-10-06.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "addons" / "core" / "functions" / "geo" / "fnc_buildGeoAnchor.sqf"
READER = ROOT / "addons" / "core" / "functions" / "geo" / "fnc_getGeoAnchor.sqf"
PREP = ROOT / "addons" / "core" / "XEH_PREP.hpp"

# Shipped mapArea values, re-read from the installed game on 2026-10-06.
ALTIS_MAPAREA = [25.011957, 39.718452, 25.481527, 40.094578]  # [lonW,latS,lonE,latN]
TANOA_MAPAREA = [-20.267975, 174.00284, -20.135265, 174.14566]  # stored [lat,lon]


def build(map_size, zone, map_area, lat, lon):
    """Run the real pure builder with the raw CfgWorlds values."""
    return run_sqf(BUILD, [map_size, zone, map_area, lat, lon])


class TestBuildGeoAnchor(unittest.TestCase):
    def test_schema_length_is_nine(self):
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(len(anchor), 9)

    def test_altis_uses_map_area_centre(self):
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(anchor[8], "mapArea")
        self.assertAlmostEqual(anchor[0], (39.718452 + 40.094578) / 2, places=6)
        self.assertAlmostEqual(anchor[1], (25.011957 + 25.481527) / 2, places=6)
        self.assertEqual(anchor[2], 35)
        self.assertEqual(anchor[3], 30720)
        self.assertAlmostEqual(anchor[4], 25.011957, places=6)
        self.assertAlmostEqual(anchor[5], 39.718452, places=6)
        self.assertAlmostEqual(anchor[6], 25.481527, places=6)
        self.assertAlmostEqual(anchor[7], 40.094578, places=6)

    def test_element_order_is_longitude_then_latitude(self):
        # Reading the box as [lat,lon,...] would place Altis near 25 N 40 E.
        # The centre equals the mean of the boxed lon/lat pair only when the
        # order is [lon,lat,lon,lat].
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertAlmostEqual(anchor[0], 39.906515, places=6)  # latitude
        self.assertAlmostEqual(anchor[1], 25.246742, places=6)  # longitude

    def test_absent_box_falls_back_to_cfgworlds(self):
        anchor = build(8192, 35, [], -35.097, 16.482)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertAlmostEqual(anchor[0], 35.097, places=3)  # negate BIS key
        self.assertAlmostEqual(anchor[1], 16.482, places=3)
        self.assertEqual(anchor[2], 35)
        self.assertEqual(anchor[3], 8192)
        self.assertEqual(anchor[4:8], [0, 0, 0, 0])

    def test_stale_keys_not_used_when_box_present(self):
        # Altis's latitude/longitude keys are stale (16.661 E, 35.152 N); with
        # mapArea present the anchor must use the box, not the keys.
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(anchor[8], "mapArea")
        self.assertNotAlmostEqual(anchor[0], 35.152, places=3)
        self.assertNotAlmostEqual(anchor[1], 16.661, places=3)

    def test_degenerate_box_falls_back(self):
        # A zero-area box (west == east) is not usable.
        anchor = build(30720, 35, [25.0, 39.0, 25.0, 40.0], -35.152, 16.661)
        self.assertEqual(anchor[8], "cfgworlds")

    def test_out_of_range_latitude_falls_back(self):
        # Tanoa ships mapArea as [lat,lon]; read in the authoritative
        # [lon,lat] order its latitude is ~174, which is not a latitude, so
        # Tanoa falls back to the CfgWorlds keys.
        anchor = build(15360, 60, TANOA_MAPAREA, 17.698, 178.783)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertAlmostEqual(anchor[0], -17.698, places=3)
        self.assertAlmostEqual(anchor[1], 178.783, places=3)

    def test_zero_latitude_falls_back_temperate(self):
        anchor = build(0, 0, [], 0, 0)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertEqual(anchor[0], 40)
        self.assertEqual(anchor[1], 0)
        self.assertEqual(anchor[2], 0)
        self.assertEqual(anchor[3], 0)


class TestGeoAnchorSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,buildGeoAnchor)", prep)
        self.assertIn("PREPS(geo,getGeoAnchor)", prep)

    def test_builder_records_authoritative_order(self):
        src = BUILD.read_text(encoding="utf-8")
        self.assertIn("[lonWest, latSouth, lonEast, latNorth]", src)
        self.assertIn("fn_posDegtoWorld", src)

    def test_reader_publishes_anchor_and_calls_builder(self):
        src = READER.read_text(encoding="utf-8")
        self.assertIn("FUNC(buildGeoAnchor)", src)
        self.assertIn("aee_core_geoAnchor", src)
        self.assertIn('configFile >> "CfgWorlds" >> worldName', src)


if __name__ == "__main__":
    unittest.main()
