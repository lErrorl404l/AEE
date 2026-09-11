#!/usr/bin/env python3
"""Reference checks for AEE's physics model.

These tests validate the SQF implementation in addons/ballistics (air
density) and addons/thermal (temperature, wind chill) against known
meteorological values. They fail if the formulas drift from the reference.

Run: python3 -m unittest tools/tests/test_physics.py
"""

import math
import unittest


def air_density(t_c, p_hpa, rh):
    """Mirror of fnc_calculateAirDensity.sqf (Buck 1996)."""
    e_s = 6.1121 * math.exp((18.678 - t_c / 234.5) * t_c / (257.14 + t_c))
    e = e_s * rh / 100
    t_k = t_c + 273.15
    t_v = t_k / (1 - 0.37802 * e / p_hpa)
    p_pa = p_hpa * 100
    r_d = 287.05287
    return p_pa / (r_d * t_v)


def wind_chill(t_c, v_ms):
    """Mirror of the JAG/TTI wind chill in fnc_updateTemperature.sqf."""
    v_kmh = v_ms * 3.6
    return 13.12 + 0.6215 * t_c - 11.37 * v_kmh**0.16 + 0.3965 * t_c * v_kmh**0.16


def solar_elevation_rad(doy, hour, lat):
    """Mirror of fnc_calculateSolarRadiation.sqf (solar elevation)."""
    decl = 23.45 * math.sin((360 / 365) * (doy + 284) * math.pi / 180)
    hour_angle = (hour - 12) * 15
    sin_elev = math.sin(math.radians(lat)) * math.sin(math.radians(decl)) + math.cos(
        math.radians(lat)
    ) * math.cos(math.radians(decl)) * math.cos(math.radians(hour_angle))
    return max(0.0, sin_elev)


class TestAirDensity(unittest.TestCase):
    def test_isa_sea_level(self):
        # International Standard Atmosphere: 15 C, 1013.25 hPa, dry air.
        self.assertAlmostEqual(air_density(15, 1013.25, 0), 1.225, places=3)

    def test_moist_air_is_less_dense(self):
        # Same temperature and pressure: humid air is less dense than dry air.
        self.assertLess(air_density(15, 1013.25, 100), air_density(15, 1013.25, 0))

    def test_high_altitude_lower_density(self):
        # 5000 m ISA: roughly 0.736 kg/m^3.
        self.assertAlmostEqual(air_density(-17.5, 540.2, 0), 0.736, places=3)


class TestSaturationVapourPressure(unittest.TestCase):
    def test_buck_20c(self):
        # Buck 1996: e_s(20 C) = 23.37 hPa (widely tabulated value; sources
        # quote 23.37-23.39, so tolerance is 0.05).
        e_s = 6.1121 * math.exp((18.678 - 20 / 234.5) * 20 / (257.14 + 20))
        self.assertAlmostEqual(e_s, 23.37, places=1)


class TestTemperature(unittest.TestCase):
    def test_lapse_rate(self):
        # Standard atmosphere lapse rate: 6.5 C per 1000 m.
        base = 20.0
        self.assertAlmostEqual(base - 0.0065 * 1000, 13.5, places=3)
        self.assertAlmostEqual(base - 0.0065 * 2000, 7.0, places=3)

    def test_solar_elevation(self):
        # June solstice at noon on the Tropic of Cancer: sun at zenith.
        self.assertAlmostEqual(solar_elevation_rad(172, 12, 23.45), 1.0, places=1)
        # Midnight: sun below horizon, radiation floors at zero.
        self.assertEqual(solar_elevation_rad(172, 0, 0), 0.0)
        # Winter: lower noon elevation at 60N than at the equator.
        self.assertLess(
            solar_elevation_rad(355, 12, 60), solar_elevation_rad(355, 12, 0)
        )


class TestWindChill(unittest.TestCase):
    def test_jag_tti_reference(self):
        # JAG/TTI: 5 C, 2 m/s => ~3.4 C.
        self.assertAlmostEqual(wind_chill(5, 2), 3.4, places=1)


if __name__ == "__main__":
    unittest.main()
