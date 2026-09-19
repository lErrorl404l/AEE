"""Geolocation physics mirror (issue #179).

Mirrors the single-world-geolocation source:
  fnc_getWorldLocation.sqf   -> get_world_location()      [lat, lon, zone]
  fnc_calculateSolarRadiation.sqf hour-angle term        -> solar_hour_angle()
  fnc_calculateCompassDeviation.sqf longitude source     -> WMM lookup (already
                                                            mirrored in test_maritime)

The BIS CfgWorlds latitude convention is INVERTED (positive = south).
get_world_location() negates it so consumers see the true geographic
sign (positive = north), matching the SQF implementation.
"""

import math
import unittest

# Known CfgWorlds anchors (verified from installed configs, 2026-09-19).
# BIS CfgWorlds latitude: negative = north, positive = south.
WORLD_ANCHORS = {
    # name: (cfg_lat, cfg_lon, zone, true_lat_expected)
    "Stratis": (-35.097, 16.482, 35, 35.097),
    "Altis": (-35.152, 16.661, 35, 35.152),
    "Tanoa": (17.698, 178.783, 60, -17.698),
    "Kerama": (-26.0, 127.0, 31, 26.0),
    "tem_kujari": (-12.0, 13.0, 33, 12.0),
}


def get_world_location(cfg_lat, cfg_lon, cfg_zone):
    """Mirror of fnc_getWorldLocation.sqf.

    Returns [latSignedTrue, magnitudeDeg, lonDeg, mapZone] with the BIS
    inverted sign corrected: positive latitude = north.
    """
    signed = -cfg_lat  # BIS: negative = north -> negate to true sign
    if signed == 0:
        signed = 40  # missing/zero latitude -> temperate default (SQF parity)
    return [signed, abs(signed), cfg_lon, cfg_zone]


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
        for name, (cfg_lat, _, _, true_lat) in WORLD_ANCHORS.items():
            loc = get_world_location(cfg_lat, 0, 0)
            self.assertAlmostEqual(loc[0], true_lat, places=3, msg=f"{name} true sign")
            self.assertAlmostEqual(
                loc[1], abs(true_lat), places=3, msg=f"{name} magnitude"
            )

    def test_northern_maps_positive(self):
        # Stratis, Altis, Kerama are northern -> positive after correction.
        for name in ("Stratis", "Altis", "Kerama"):
            loc = get_world_location(*WORLD_ANCHORS[name][:3])
            self.assertGreater(loc[0], 0, f"{name} should be north-positive")

    def test_southern_map_negative(self):
        # Tanoa is southern -> negative after correction.
        loc = get_world_location(*WORLD_ANCHORS["Tanoa"][:3])
        self.assertLess(loc[0], 0, "Tanoa should be south-negative")

    def test_zero_falls_back_temperate(self):
        # A missing latitude (0) must fall back to 40 N, not remain 0.
        loc = get_world_location(0, 0, 0)
        self.assertEqual(loc[0], 40)
        self.assertEqual(loc[1], 40)


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


if __name__ == "__main__":
    unittest.main()
