"""Geolocation physics mirror (issue #179).

Mirrors the single-world-geolocation source:
  fnc_getGeoAnchor.sqf + fnc_buildGeoAnchor.sqf -> get_world_location()
  fnc_calculateSolarRadiation.sqf hour-angle term -> solar_hour_angle()
  fnc_calculateCompassDeviation.sqf longitude source -> WMM lookup (already
                                                          mirrored in test_maritime)

The sourced geo anchor takes the world centre from mapArea[] when a usable
box is present, else from the CfgWorlds latitude/longitude keys.  The BIS
latitude convention is INVERTED (positive = south), so the fallback negates
it and consumers see the true geographic sign (positive = north).
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

BUILD = ROOT / "addons" / "lib" / "functions" / "geo" / "fnc_buildGeoAnchor.sqf"

# Known CfgWorlds anchors (re-read from the installed configs, 2026-10-06).
# BIS CfgWorlds latitude: negative = north, positive = south.
# map_area is the raw mapArea[] value when the world ships a box, else None.
# mapArea order is [lonWest, latSouth, lonEast, latNorth] per BIS
# fn_posDegtoWorld; Tanoa ships its box in the opposite order, so it is not a
# usable box and Tanoa falls back to the keys.
ALTIS_MAPAREA = [25.011957, 39.718452, 25.481527, 40.094578]
TANOA_MAPAREA = [-20.267975, 174.00284, -20.135265, 174.14566]

WORLD_ANCHORS = {
    # name: (cfg_lat, cfg_lon, zone, map_area, true_lat, lon)
    "Stratis": (-35.097, 16.482, 35, None, 35.097, 16.482),
    "Altis": (-35.152, 16.661, 35, ALTIS_MAPAREA, 39.906515, 25.246742),
    "Tanoa": (17.698, 178.783, 60, TANOA_MAPAREA, -17.698, 178.783),
    "Kerama": (-26.0, 127.0, 31, None, 26.0, 127.0),
    "tem_kujari": (-12.0, 13.0, 33, None, 12.0, 13.0),
}


def _usable_box(map_area):
    """Mirror of the mapArea validity rule in fnc_buildGeoAnchor.sqf."""
    if not map_area or len(map_area) != 4:
        return False
    lon_w, lat_s, lon_e, lat_n = map_area
    return (
        lon_w < lon_e
        and lat_s < lat_n
        and -180 <= lon_w
        and lon_e <= 180
        and -90 <= lat_s
        and lat_n <= 90
    )


def get_world_location(cfg_lat, cfg_lon, cfg_zone, map_area=None):
    """Mirror of fnc_getWorldLocation.sqf via FUNC(getGeoAnchor).

    Returns [latSignedTrue, magnitudeDeg, lonDeg, mapZone].  The centre
    comes from a usable mapArea box, else the sign-corrected CfgWorlds key.
    """
    if _usable_box(map_area):
        signed = (map_area[1] + map_area[3]) / 2
        lon = (map_area[0] + map_area[2]) / 2
    else:
        signed = -cfg_lat  # BIS: negative = north -> negate to true sign
        lon = cfg_lon
    if signed == 0:
        signed = 40  # missing/zero latitude -> temperate default (SQF parity)
    return [signed, abs(signed), lon, cfg_zone]


def solar_hour_angle(hour, lon, zone):
    """Mirror of the hour-angle term in fnc_calculateSolarRadiation.sqf.

    hourAngle = (hour - 12) * 15 + (lon - zoneMeridian)
    zoneMeridian = (zone - 1) * 6 - 177   (central meridian of the UTM zone)
    """
    zone_meridian = (zone - 1) * 6 - 177 if zone > 0 else 0
    return (hour - 12) * 15 + (lon - zone_meridian)


class TestGetWorldLocation(unittest.TestCase):
    """The shared source must return the TRUE geographic sign."""

    def test_bis_inverted_sign_corrected(self):
        for name, (
            cfg_lat,
            cfg_lon,
            zone,
            map_area,
            true_lat,
            _,
        ) in WORLD_ANCHORS.items():
            loc = get_world_location(cfg_lat, cfg_lon, zone, map_area)
            self.assertAlmostEqual(loc[0], true_lat, places=3, msg=f"{name} true sign")
            self.assertAlmostEqual(
                loc[1], abs(true_lat), places=3, msg=f"{name} magnitude"
            )

    def test_northern_maps_positive(self):
        # Stratis, Altis, Kerama are northern -> positive after correction.
        for name in ("Stratis", "Altis", "Kerama"):
            row = WORLD_ANCHORS[name]
            loc = get_world_location(*row[:3], row[3])
            self.assertGreater(loc[0], 0, f"{name} should be north-positive")

    def test_southern_map_negative(self):
        # Tanoa is southern -> negative after correction.
        row = WORLD_ANCHORS["Tanoa"]
        loc = get_world_location(*row[:3], row[3])
        self.assertLess(loc[0], 0, "Tanoa should be south-negative")

    def test_zero_falls_back_temperate(self):
        # A missing latitude (0) must fall back to 40 N, not remain 0.
        loc = get_world_location(0, 0, 0)
        self.assertEqual(loc[0], 40)
        self.assertEqual(loc[1], 40)

    def test_stale_keys_not_used_when_maparea_present(self):
        # Altis's latitude/longitude keys are stale (35.152 N, 16.661 E).
        # With a usable mapArea box the anchor takes the box centre instead.
        row = WORLD_ANCHORS["Altis"]
        loc = get_world_location(*row[:3], row[3])
        self.assertAlmostEqual(loc[0], 39.906515, places=3)
        self.assertAlmostEqual(loc[2], 25.246742, places=3)
        self.assertNotAlmostEqual(loc[2], 16.661, places=3)

    def test_maparea_centre_is_the_anchor(self):
        # The box centre maps to the anchor latitude and longitude.
        row = WORLD_ANCHORS["Altis"]
        loc = get_world_location(*row[:3], row[3])
        self.assertAlmostEqual(loc[0], (39.718452 + 40.094578) / 2, places=6)
        self.assertAlmostEqual(loc[2], (25.011957 + 25.481527) / 2, places=6)

    def test_unusable_maparea_falls_back_to_keys(self):
        # Tanoa ships mapArea in [lat,lon] order; read in the authoritative
        # [lon,lat] order the latitude is ~174, so it falls back to the keys.
        row = WORLD_ANCHORS["Tanoa"]
        loc = get_world_location(*row[:3], row[3])
        self.assertAlmostEqual(loc[0], -17.698, places=3)
        self.assertAlmostEqual(loc[2], 178.783, places=3)


class TestGeolocationSourceContract(unittest.TestCase):
    def test_getworldlocation_uses_geo_anchor(self):
        src = (
            ROOT / "addons" / "lib" / "functions" / "fnc_getWorldLocation.sqf"
        ).read_text(encoding="utf-8")
        # The call form, not the bare name in a comment, proves the migration.
        self.assertIn("call FUNC(getGeoAnchor)", src)


class TestSolarHourAngle(unittest.TestCase):
    """Solar noon must drift with real longitude (defect 1 of #179)."""

    def test_solar_noon_on_zone_meridian(self):
        # On the zone meridian the correction is zero: noon stays at 12:00.
        zone = 35
        meridian = (zone - 1) * 6 - 177  # 27 E
        self.assertEqual(solar_hour_angle(12, meridian, zone), 0)

    def test_noon_offset_west_of_meridian(self):
        # oski_corran-class: lon west of zone meridian -> noon later.
        # zone 30 -> meridian -3; lon -5.22 -> hour angle negative at 12:00,
        # i.e. the sun peaks after 12:00 local time.
        ha = solar_hour_angle(12, -5.22, 30)
        self.assertLess(ha, 0)
        # 2.22 deg west of meridian -> ~8.9 min later: ha = -2.22 deg.
        self.assertAlmostEqual(ha, -2.22, places=2)

    def test_noon_offset_east_of_meridian(self):
        # lon east of the zone meridian -> noon earlier (positive angle at
        # 12:00, peak before 12:00).
        ha = solar_hour_angle(12, 40.0, 35)  # 13 deg east of meridian 27
        self.assertGreater(ha, 0)
        self.assertAlmostEqual(ha, 13.0, places=2)

    def test_old_bug_pinned_noon(self):
        # The old formula (hour - 12) * 15 ignored longitude entirely;
        # this asserts the corrected formula actually moves the peak.
        # At 12:00 on a 5.22 W map the old angle was 0; new is -2.22.
        self.assertNotEqual(solar_hour_angle(12, -5.22, 30), 0)


class TestRealAnchorMatchesMirror(unittest.TestCase):
    """The Python mirror must match the shipped pure builder (issue #179).

    The mirror is only trustworthy while it agrees with the REAL kernel.
    This runs fnc_buildGeoAnchor.sqf through the harness for every shipped
    world and compares the anchor centre to both the mirror and the known
    true coordinate.
    """

    def test_builder_matches_mirror_for_every_shipped_world(self):
        for name, (
            cfg_lat,
            cfg_lon,
            zone,
            map_area,
            true_lat,
            true_lon,
        ) in WORLD_ANCHORS.items():
            anchor = run_sqf(BUILD, [30720, zone, map_area or [], cfg_lat, cfg_lon])
            mirror = get_world_location(cfg_lat, cfg_lon, zone, map_area)
            self.assertAlmostEqual(anchor[0], mirror[0], places=6, msg=f"{name} lat")
            self.assertAlmostEqual(anchor[1], mirror[2], places=6, msg=f"{name} lon")
            self.assertAlmostEqual(
                anchor[0], true_lat, places=3, msg=f"{name} true lat"
            )
            self.assertAlmostEqual(
                anchor[1], true_lon, places=3, msg=f"{name} true lon"
            )


if __name__ == "__main__":
    unittest.main()
