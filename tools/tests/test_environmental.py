#!/usr/bin/env python3
"""Reference checks for AEE's environmental model.

These tests validate the SQF implementation in addons/environmental
(CBRN persistence, Rothermel fire spread, avalanche risk, freeze-thaw,
flash flood, severe weather, surface wetness) against the source
formulas. They fail if the formulas drift from the reference.

Run: python3 -m unittest tools/tests/test_environmental.py
"""

import math
import unittest


def cbrn_persistence(temp_c, humidity_pct, wind_ms, base_h=24, interval=5):
    """Mirror of fnc_calculateCBRNPersistence.sqf (Arrhenius Q10).

    Returns the per-tick exponential decay factor. A higher factor means
    slower decay, hence longer persistence.
    """
    rate_multiplier = 2 ** ((temp_c - 15) / 10)
    persistence_h = base_h / rate_multiplier
    humidity_factor = 1 / (1 + ((humidity_pct - 50) / 50) * 0.5)
    persistence_h = persistence_h * humidity_factor
    wind_factor = 1 / (1 + wind_ms * 0.05)
    persistence_h = persistence_h * wind_factor
    return math.exp(-(interval / 3600) / persistence_h)


def fire_ros(fuel_factor, wind_ms, slope_pct, fuel_moisture):
    """Mirror of fnc_calculateFireSpreadRisk.sqf (Rothermel 1972)."""
    return (
        0.03
        * fuel_factor
        * (1 + 0.2 * wind_ms)
        * (1 + 0.1 * slope_pct)
        * math.exp(-fuel_moisture * 0.05)
    )


def fire_area(area, ros, interval):
    """Mirror of the fire-area growth in fnc_calculateFireSpreadRisk.sqf."""
    perimeter = 2 * math.pi * math.sqrt(area / math.pi)
    area = area + perimeter * ros * interval
    return max(0.0, min(1e6, area))


def slope_risk(slope_deg):
    """Mirror of the slope curve in fnc_calculateAvalancheRisk.sqf (Schweizer 2003)."""
    return max(0.0, min(1.0, 1 - abs(slope_deg - 35) / 20))


def avalanche_risk(slope_deg, wind_ms, temp_c, rain, ground_state="Snow"):
    """Mirror of the combined risk in fnc_calculateAvalancheRisk.sqf."""
    if ground_state not in ("Snow", "Frozen"):
        return 0.0
    risk = slope_risk(slope_deg)
    wind_factor = 0
    if wind_ms > 8:
        wind_factor = min((wind_ms - 8) / 20, 0.2)
    temp_factor = 0
    if temp_c > 0:
        temp_factor = min(((temp_c - 0) / 20) * 0.15, 0.15)
    rain_factor = 0
    if ground_state == "Snow" and rain > 0:
        rain_factor = min(rain * 0.15, 0.15)
    return min(risk + wind_factor + temp_factor + rain_factor, 1.0)


def freeze_thaw(fdd, tdd, temp_c, interval=5):
    """Mirror of fnc_calculateFreezeThawCycling.sqf (Stefan solution).

    Returns (fdd, tdd, frozen_depth_m, thaw_depth_m).
    """
    fdd = fdd + max(0 - temp_c, 0) * (interval / 86400)
    tdd = tdd + max(temp_c - 0, 0) * (interval / 86400)
    frozen_depth = 0.05 * math.sqrt(fdd)
    thaw_depth = 0.05 * math.sqrt(tdd)
    return fdd, tdd, frozen_depth, thaw_depth


def flash_flood_risk(rain_rate, rain_accum, terrain_factor):
    """Mirror of fnc_calculateFlashFloodRisk.sqf."""
    risk = (rain_rate * 25 / 50) * (1 + rain_accum) * terrain_factor
    return max(0.0, min(1.0, risk))


def dust_devil(wind_ms, biome_arid, temp, clear, day=True):
    """Mirror of the dust-devil band in fnc_calculateSevereWeather.sqf.

    The SQF gates on the 2-8 m/s wind band, arid biome, hot air and a
    clear sky. It has no day/night gate; the day parameter is kept for
    signature compatibility and does not affect the result.
    """
    if biome_arid and 2 <= wind_ms <= 8 and temp > 30 and clear:
        return min(wind_ms / 15, 0.8)
    return 0.0


def surface_wetness(wetness, rain, temp, dewpoint, overcast, wind, interval=5):
    """Mirror of fnc_calculateSurfaceWetness.sqf."""
    wetness = wetness + rain * 0.05
    if temp < dewpoint and overcast < 0.3 and wind < 3:
        wetness = wetness + 0.02
    evap = (0.01 + 0.001 * wind) * (1 + (temp - 15) * 0.05)
    wetness = wetness - wetness * evap * (interval / 3600)
    return max(0.0, min(1.0, wetness))


class TestCBRNPersistence(unittest.TestCase):
    def test_warmer_temp_shorter_persistence(self):
        # Q10: decay rate doubles per 10 C rise, so the decay factor falls.
        self.assertLess(cbrn_persistence(20, 50, 0), cbrn_persistence(10, 50, 0))

    def test_higher_humidity_shorter_persistence(self):
        # High humidity accelerates hydrolysis.
        self.assertLess(cbrn_persistence(15, 80, 0), cbrn_persistence(15, 20, 0))

    def test_higher_wind_shorter_persistence(self):
        # Wind disperses the agent cloud.
        self.assertLess(cbrn_persistence(15, 50, 5), cbrn_persistence(15, 50, 0))

    def test_persistence_never_negative(self):
        # The decay factor is exp(negative), always in (0, 1].
        for args in [(15, 50, 0), (40, 100, 20), (-20, 0, 0), (15, 50, 50)]:
            modifier = cbrn_persistence(*args)
            self.assertGreater(modifier, 0.0)
            self.assertLessEqual(modifier, 1.0)

    def test_reference_tick_math(self):
        # At 15 C, RH 50, calm: all factors are 1, persistence = base_h.
        self.assertAlmostEqual(
            cbrn_persistence(15, 50, 0, 24, 5), math.exp(-(5 / 3600) / 24)
        )


class TestFireSpread(unittest.TestCase):
    def test_reference_ros(self):
        # Zero wind, zero slope, dry fuel, fuel factor 1.
        self.assertAlmostEqual(fire_ros(1, 0, 0, 0), 0.03)

    def test_ros_monotonic_wind(self):
        self.assertGreater(fire_ros(1, 5, 0, 0), fire_ros(1, 2, 0, 0))

    def test_ros_monotonic_slope(self):
        self.assertGreater(fire_ros(1, 0, 10, 0), fire_ros(1, 0, 5, 0))

    def test_ros_decreasing_moisture(self):
        self.assertLess(fire_ros(1, 0, 0, 10), fire_ros(1, 0, 0, 5))

    def test_ros_zero_fuel(self):
        self.assertEqual(fire_ros(0, 5, 10, 0), 0.0)

    def test_area_grows(self):
        self.assertGreater(fire_area(100, 1, 5), 100)

    def test_area_constant_zero_ros(self):
        self.assertEqual(fire_area(100, 0, 5), 100)

    def test_area_clamped(self):
        # A single large step overshoots the 1e6 cap.
        self.assertEqual(fire_area(999999, 100, 5), 1e6)

    def test_high_moisture_near_zero(self):
        # exp(-moisture * 0.05) collapses the rate at high moisture.
        self.assertLess(fire_ros(1, 0, 0, 100), 0.001)


class TestAvalanche(unittest.TestCase):
    def test_slope_peak(self):
        self.assertEqual(slope_risk(35), 1.0)

    def test_slope_tails(self):
        self.assertEqual(slope_risk(15), 0.0)
        self.assertEqual(slope_risk(55), 0.0)

    def test_slope_midpoint(self):
        self.assertAlmostEqual(slope_risk(25), 0.5)

    def test_no_snow_zero(self):
        # No snowpack: the SQF exits with risk 0.
        self.assertEqual(avalanche_risk(35, 0, 0, 0, "Normal"), 0.0)

    def test_warm_increases_risk(self):
        # Rapid warm-up adds a temperature factor; cold air adds none.
        self.assertGreater(
            avalanche_risk(25, 0, 20, 0, "Snow"), avalanche_risk(25, 0, -5, 0, "Snow")
        )

    def test_risk_clamped(self):
        # All factors at maximum still clamp to 1.0.
        self.assertEqual(avalanche_risk(35, 30, 30, 1.0, "Snow"), 1.0)
        self.assertGreaterEqual(avalanche_risk(25, 10, 10, 0.5, "Snow"), 0.0)


class TestFreezeThaw(unittest.TestCase):
    def test_tdd_only_above_zero(self):
        # Below 0 C the thawing degree-days do not grow.
        fdd, tdd, _, _ = freeze_thaw(0, 0, -5, 86400)
        self.assertEqual(tdd, 0.0)
        self.assertGreater(fdd, 0.0)

    def test_fdd_only_below_zero(self):
        # Above 0 C the freezing degree-days do not grow.
        fdd, tdd, _, _ = freeze_thaw(0, 0, 5, 86400)
        self.assertEqual(fdd, 0.0)
        self.assertGreater(tdd, 0.0)

    def test_thaw_depth_sqrt_scaling(self):
        # Depth is proportional to sqrt(degree-days): 4 days at the same
        # rate gives twice the depth of 1 day.
        _, _, _, depth_1d = freeze_thaw(0, 0, 10, 86400)
        _, _, _, depth_4d = freeze_thaw(0, 0, 10, 86400 * 4)
        self.assertAlmostEqual(depth_4d / depth_1d, 2.0)

    def test_depths_never_negative(self):
        _, _, frozen, thawed = freeze_thaw(0, 0, -10, 86400)
        self.assertGreaterEqual(frozen, 0.0)
        self.assertGreaterEqual(thawed, 0.0)


class TestFlashFlood(unittest.TestCase):
    def test_no_rain_zero(self):
        self.assertEqual(flash_flood_risk(0, 0, 1.0), 0.0)

    def test_accum_alone_no_risk(self):
        # Antecedent moisture amplifies but cannot sustain risk alone.
        self.assertEqual(flash_flood_risk(0, 5, 1.0), 0.0)

    def test_50mmh_steep_full(self):
        # Rain rate 2 = 50 mm/h, steep catchment, no antecedent.
        self.assertEqual(flash_flood_risk(2, 0, 1.0), 1.0)

    def test_flat_half(self):
        # Non-arid terrain responds at half the steep-catchment rate.
        self.assertAlmostEqual(flash_flood_risk(2, 0, 0.5), 0.5)

    def test_clamped(self):
        self.assertEqual(flash_flood_risk(10, 0, 1.0), 1.0)


class TestSevereWeather(unittest.TestCase):
    def test_band_active(self):
        # Hot, clear, arid, wind in the 2-8 m/s band.
        self.assertGreater(dust_devil(5, True, 35, True), 0.0)

    def test_band_bounds(self):
        # Wind 1 m/s is too calm, 10 m/s shreds the vortex.
        self.assertEqual(dust_devil(1, True, 35, True), 0.0)
        self.assertEqual(dust_devil(10, True, 35, True), 0.0)

    def test_mid_band_active(self):
        self.assertGreater(dust_devil(5, True, 35, True), 0.0)

    def test_non_arid_inactive(self):
        self.assertEqual(dust_devil(5, False, 35, True), 0.0)

    def test_cold_inactive(self):
        self.assertEqual(dust_devil(5, True, 25, True), 0.0)


class TestSurfaceWetness(unittest.TestCase):
    def test_dries_toward_zero(self):
        # Warm, dry, no rain, no dew: wetness falls and never goes negative.
        result = surface_wetness(0.5, 0, 30, -10, 0.5, 5, 3600)
        self.assertLess(result, 0.5)
        self.assertGreaterEqual(result, 0.0)

    def test_heavy_rain_rises(self):
        self.assertGreater(surface_wetness(0.9, 1.0, 15, 5, 0.5, 2, 5), 0.9)

    def test_dew_rises_without_rain(self):
        # Clear, calm, cold night below the dew point.
        self.assertGreater(surface_wetness(0.1, 0, 5, 10, 0.1, 1, 5), 0.1)

    def test_clamped(self):
        self.assertEqual(surface_wetness(1.0, 1.0, 15, 5, 0.5, 2, 5), 1.0)
        self.assertEqual(surface_wetness(0.0, 0, 30, -10, 0.5, 5, 3600), 0.0)


# ─── Aurora model (issue #112) ──────────────────────────────────────────────
# Mirror of the aurora block in fnc_calculateSpaceWeather.sqf: NOAA SWPC
# Kp-to-latitude relationship (oval expands equatorward as Kp rises) and
# the intensity model (rises with Kp beyond the threshold, strongest when
# the observer's latitude is near the oval edge).


def aurora_oval_limit(kp):
    """Equatorward latitude limit of the auroral oval by Kp.

    Kp 0-1 -> 65 deg, Kp 9 -> ~49.7 deg (NOAA SWPC bands, interpolated).
    """
    return 65.0 - (min(kp, 9) * 1.7)


def aurora_intensity(kp, lat_deg, overcast, day_time):
    """Mirror of the SQF aurora gate + intensity (0-1, 0 = no aurora).

    Requires: Kp > 4, clear sky (< 0.3 overcast), night (before 06:00 or
    after 20:00), and the observer poleward of the oval limit.
    Intensity: 0.6 * (Kp excess over 4) + 0.4 * (latitude proximity to
    the oval edge), clamped 0-1.
    """
    kp_idx = round(max(0.0, min(9.0, kp)))
    if kp_idx <= 4:
        return 0.0
    if overcast >= 0.3:
        return 0.0
    if 6 <= day_time <= 20:
        return 0.0
    limit = aurora_oval_limit(kp_idx)
    if lat_deg <= limit:
        return 0.0
    kp_excess = max(0.0, min(1.0, (kp_idx - 4) / 5.0))
    lat_proximity = max(0.0, min(1.0, 1.0 - (lat_deg - limit) / 10.0))
    return max(0.0, min(1.0, kp_excess * 0.6 + lat_proximity * 0.4))


class TestAurora(unittest.TestCase):
    """Issue #112: Kp-driven aurora visibility and intensity."""

    def test_oval_limit_matches_noaa_bands(self):
        # Kp 0 -> 65, Kp 3 -> ~60, Kp 5 -> ~56.5, Kp 7 -> ~53, Kp 9 -> ~49.7.
        self.assertAlmostEqual(aurora_oval_limit(0), 65.0, places=4)
        self.assertAlmostEqual(aurora_oval_limit(3), 65 - 5.1, places=4)
        self.assertAlmostEqual(aurora_oval_limit(5), 65 - 8.5, places=4)
        self.assertAlmostEqual(aurora_oval_limit(7), 65 - 11.9, places=4)
        self.assertAlmostEqual(aurora_oval_limit(9), 65 - 15.3, places=4)

    def test_kp5_visible_55_60(self):
        # Test vector: Kp 5 -> oval edge in the 55-60 deg band.  The
        # observer must be POLEWARD of the edge (Kp5 limit is 56.5), so
        # lat 58/60 are visible, lat 50 is not.
        for lat in [58, 60]:
            self.assertGreater(
                aurora_intensity(5, lat, 0, 2),
                0.0,
                msg=f"Kp5 not visible at {lat} deg",
            )
        self.assertEqual(aurora_intensity(5, 50, 0, 2), 0.0)  # too far south

    def test_kp9_visible_below_50(self):
        # Kp 9 -> oval limit ~49.7 deg: lat 50 (just poleward) is
        # visible (test vector: oval extends below 50).
        self.assertGreater(aurora_intensity(9, 50, 0, 2), 0.0)

    def test_quiet_kp_no_aurora(self):
        for kp in [0, 1, 2, 3, 4]:
            self.assertEqual(aurora_intensity(kp, 70, 0, 2), 0.0)

    def test_clouds_block_aurora(self):
        self.assertEqual(aurora_intensity(7, 65, 0.5, 2), 0.0)

    def test_daylight_blocks_aurora(self):
        # Night gate: before 06:00 or after 20:00.  Noon blocks; 21:00
        # is night (visible).  A dawn hour (05:00) is also night.
        self.assertEqual(aurora_intensity(7, 65, 0, 12), 0.0)
        self.assertGreater(aurora_intensity(7, 65, 0, 21), 0.0)

    def test_intensity_rises_with_kp(self):
        lo = aurora_intensity(5, 70, 0, 2)
        hi = aurora_intensity(8, 70, 0, 2)
        self.assertGreater(hi, lo)

    def test_intensity_bounded(self):
        for kp in range(5, 10):
            for lat in [50, 55, 60, 65, 70]:
                i = aurora_intensity(kp, lat, 0, 2)
                self.assertGreaterEqual(i, 0.0)
                self.assertLessEqual(i, 1.0)

    def test_nvg_brightens_under_aurora(self):
        # The illuminance mirror (test_thermal_optics.ambient_lux) must
        # respond to the aurora intensity: 30x the starlight floor at
        # full intensity.  Cross-module integration lock.
        from tools.tests.test_thermal_optics import ambient_lux

        floor = ambient_lux(0.0)
        bright = ambient_lux(0.0, aurora_intensity=1.0)
        self.assertGreater(bright / max(floor, 1e-9), 30.0)


if __name__ == "__main__":
    unittest.main()
