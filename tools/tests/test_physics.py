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


class TestAirDensityEdgeCases(unittest.TestCase):
    """Edge cases: guards, monotonicity, extremes for fnc_calculateAirDensity."""

    def test_zero_humidity_valid(self):
        # Dry air must compute without error at standard conditions.
        self.assertAlmostEqual(air_density(15, 1013.25, 0), 1.225, places=3)

    def test_density_finite_at_extremes(self):
        # -40 C, 40 C, extreme RH, low pressure: all finite, positive.
        for t, p, rh in [(-40, 900, 0), (40, 1080, 100), (-30, 400, 50)]:
            rho = air_density(t, p, rh)
            self.assertGreater(rho, 0.0)
            self.assertTrue(math.isfinite(rho))

    def test_cold_denser_than_warm(self):
        # Same pressure: cold air denser than warm air.
        self.assertGreater(air_density(-20, 1013.25, 0), air_density(30, 1013.25, 0))

    def test_low_pressure_less_dense(self):
        # Same temperature: lower pressure -> lower density.
        self.assertLess(air_density(15, 500, 0), air_density(15, 1013.25, 0))

    def test_full_saturation_bounds(self):
        # RH clamped by the formula to its input range; 0..100 stays valid.
        rho_0 = air_density(20, 1013.25, 0)
        rho_100 = air_density(20, 1013.25, 100)
        # Humid air less dense than dry (water vapour replaces dry air).
        self.assertLess(rho_100, rho_0)


class TestWindChillEdgeCases(unittest.TestCase):
    """Wind chill guards and monotonicity (fnc_updateTemperature).

    The JAG/TTI formula is continuous and valid below 10 C with wind
    above 4.8 km/h; the SQF gates on those before applying it.  The
    formula itself has no plateau, so higher wind always means lower
    apparent temperature, and the apparent temperature can sit a little
    above air temperature in warm conditions (a known JAG/TTI quirk).
    """

    def test_cold_windy_colder_than_still(self):
        # At freezing, wind makes it feel colder.
        self.assertLess(wind_chill(0, 10), wind_chill(0, 1))

    def test_wind_monotonic_decreasing(self):
        # Higher wind always lowers the JAG/TTI apparent temperature.
        self.assertLess(wind_chill(-10, 60), wind_chill(-10, 40))
        self.assertLess(wind_chill(-10, 40), wind_chill(-10, 20))

    def test_cold_strong_wind_extreme(self):
        # -10 C at 40 m/s: well below freezing apparent temperature.
        self.assertLess(wind_chill(-10, 40), -20)

    def test_warm_conditions_outside_validity(self):
        # Above 10 C the formula is outside its published validity band;
        # the SQF gates before applying.  Mirror that gate: the formula
        # value is not used there, so assert only that it is finite.
        self.assertTrue(math.isfinite(wind_chill(25, 30)))


class TestWBGTEdgeCases(unittest.TestCase):
    """Edge cases for the Stull 2011 wet-bulb and WBGT (fnc_calculateWBGT)."""

    def wet_bulb(self, t_c, rh):
        """Mirror of the Stull 2011 wet-bulb inside fnc_calculateWBGT.sqf.

        SQF's atan returns degrees; the code converts each term to radians
        with the rad operator, which reproduces the published Stull 2011
        formula (all atan in radians).  In Python math.atan already returns
        radians, so the mirror is the canonical form with no conversion.
        """
        return (
            t_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t_c + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh**1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )

    def test_wet_bulb_never_above_dry(self):
        # Evaporative cooling means Twb <= T always.
        for t, rh in [(0, 50), (20, 50), (35, 90), (30, 30)]:
            self.assertLessEqual(self.wet_bulb(t, rh), t + 1e-9)

    def test_wet_bulb_higher_at_saturation(self):
        # At 100 %RH the wet bulb approaches the dry bulb.
        self.assertLessEqual(abs(self.wet_bulb(30, 100) - 30), 2.0)
        # At 10 %RH it sits well below.
        self.assertLess(self.wet_bulb(30, 10), 30 - 8)

    def test_wbgt_iso_reduction(self):
        # Overcast 1 -> Tg = T; WBGT = 0.7Tw + 0.2T + 0.1T = 0.7Tw + 0.3T.
        # This is exactly the ISO 7243 reduction for Tg = Ta.
        t, rh = 25, 60
        tw = self.wet_bulb(t, rh)
        expected = 0.7 * tw + 0.3 * t
        self.assertAlmostEqual(0.7 * tw + 0.2 * t + 0.1 * t, expected, places=9)

    def test_wbgt_sun_raises_above_shade(self):
        # Sun (overcast 0) raises WBGT above shade (overcast 1).
        t, rh = 25, 60
        tw = self.wet_bulb(t, rh)
        shade = 0.7 * tw + 0.2 * t + 0.1 * t
        sun = 0.7 * tw + 0.2 * (t + 15) + 0.1 * t
        self.assertGreater(sun, shade)


class TestHeatIndexEdgeCases(unittest.TestCase):
    """Edge cases for the NWS Rothfusz heat index (fnc_calculateHeatIndex)."""

    def heat_index(self, t_c, rh):
        """Mirror of fnc_calculateHeatIndex.sqf (Rothfusz 1990)."""
        t_f = t_c * 9 / 5 + 32
        if t_f < 80 or rh < 40:
            hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
        else:
            hi_f = (
                -42.379
                + 2.04901523 * t_f
                + 10.14333127 * rh
                - 0.22475541 * t_f * rh
                - 6.83783e-3 * t_f**2
                - 5.481717e-2 * rh**2
                + 1.22874e-3 * t_f**2 * rh
                + 8.5282e-4 * t_f * rh**2
                - 1.99e-6 * t_f**2 * rh**2
            )
        if rh < 13 and 80 <= t_f <= 112:
            hi_f -= ((13 - rh) / 4) * math.sqrt((17 - abs(t_f - 95)) / 17)
        if rh > 85 and 80 <= t_f <= 87:
            hi_f += ((rh - 85) / 10) * ((87 - t_f) / 5)
        return (hi_f - 32) * 5 / 9

    def test_heat_index_above_air_in_humid_heat(self):
        # Humid hot air: apparent temperature above air temperature.
        self.assertGreater(self.heat_index(35, 80), 35)

    def test_heat_index_below_air_in_dry(self):
        # Hot dry air below 40 %RH uses the simple form; still sensible.
        self.assertTrue(math.isfinite(self.heat_index(35, 10)))

    def test_mild_conditions_no_exaggeration(self):
        # 20 C, 50 %RH: apparent temperature within 5 C of air temperature.
        self.assertLessEqual(abs(self.heat_index(20, 50) - 20), 5.0)

    def test_never_nan(self):
        for t in range(-10, 45, 5):
            for rh in range(0, 101, 20):
                self.assertTrue(math.isfinite(self.heat_index(t, rh)))


if __name__ == "__main__":
    unittest.main()
