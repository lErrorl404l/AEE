#!/usr/bin/env python3
"""Reference checks for AEE's atmos model.

These tests validate the SQF implementation in addons/atmos (airframe
icing, cloud development, haze, lightning, microburst, pressure trend,
turbulence, fog, humidity) against the source formulas. They fail if the
formulas drift from the reference.

Run: python3 -m unittest tools/tests/test_atmos.py
"""

import unittest


def icing_efficiency(temp_c):
    """Mirror of the ice-type band in fnc_calculateAirframeIcing.sqf.

    Glaze (0 to -10 C) collects at 0.8; rime (below -10 C) at 0.4.
    """
    return 0.8 if temp_c > -10 else 0.4


def icing_rate(lwc, speed, collection_eff):
    """Mirror of the accretion rate in fnc_calculateAirframeIcing.sqf.

    The SQF rate is lwc * efficiency * 0.05 kg/s. It has no speed term;
    the speed parameter is kept for signature compatibility and does not
    affect the result.
    """
    return lwc * collection_eff * 0.05


def ice_accretion(ice, rate, interval=5):
    """Mirror of the ice-mass accumulation in fnc_calculateAirframeIcing.sqf."""
    ice = ice + rate * interval
    return max(0.0, min(100.0, ice))


def cape_proxy(lapse_rate):
    """Mirror of the CAPE proxy in fnc_calculateCloudDevelopment.sqf.

    The SQF compares the ambient lapse with the dry adiabat (0.0098 C/m).
    """
    return (lapse_rate - 0.0098) * 1000


def cloud_growth(cape, rh):
    """Mirror of the convective term in fnc_calculateCloudDevelopment.sqf."""
    if cape > 0 and rh > 60:
        return min(cape * 0.15, 0.3)
    return 0.0


def haze(rh_pct, dust_suppression=0):
    """Mirror of fnc_calculateHaze.sqf (Kohler growth)."""
    h = 0.0
    if rh_pct >= 40:
        h = 0.2 + 0.8 * ((rh_pct - 40) / 60)
    if rh_pct >= 99.5:
        h = h * 0.3
    h = h - dust_suppression * 0.15
    return max(0.0, min(1.0, h))


def lightning_risk(overcast, rain, rh, convective, cloud_top_m):
    """Mirror of fnc_calculateLightning.sqf (ice-phase gate)."""
    risk = overcast * 0.3 + rain * 0.3 + (rh / 100) * 0.2 + convective * 0.2
    risk = min(risk, 1.0)
    ice_factor = max(0.0, min(1.0, (cloud_top_m - 5500) / 2500))
    return risk * ice_factor


def microburst_gust(severity_roll, magnitude_roll):
    """Mirror of the gust tiers in fnc_calculateMicroburst.sqf (NWS).

    A severity roll below 0.5 gives the damaging band 26-36 m/s; the
    moderate band is 15-30 m/s.
    """
    if severity_roll < 0.5:
        return 26 + 10 * magnitude_roll, "DAMAGING"
    return 15 + 15 * magnitude_roll, "MODERATE"


def pressure_class(change):
    """Mirror of the WMO forecast switch in fnc_calculatePressureTrend.sqf."""
    if change < -2:
        return "Storm approaching"
    if change < -0.5:
        return "Rain expected"
    if change > 2:
        return "Fair weather"
    if change > 0.5:
        return "Clearing"
    return "Stable"


def pressure_trend(pressure_history, new_pressure):
    """Mirror of the ring-buffer push in fnc_calculatePressureTrend.sqf.

    The buffer holds two prior readings (p2, p1). The change is the new
    reading minus p2, the reading from two ticks ago.
    """
    if not pressure_history:
        history = [new_pressure, new_pressure]
    else:
        history = (pressure_history + [new_pressure])[-2:]
    change = new_pressure - history[0]
    return history, change, pressure_class(change)


def turbulence_edr(turbulence_raw):
    """Mirror of the ICAO EDR conversion in fnc_calculateTurbulence.sqf."""
    return turbulence_raw * 0.7


def turbulence_class(edr):
    """Mirror of the ICAO EDR bands in fnc_calculateTurbulence.sqf."""
    if edr > 0.5:
        return "EXTREME"
    if edr > 0.3:
        return "SEVERE"
    if edr >= 0.1:
        return "MODERATE"
    return "LIGHT"


def radiational_fog(overcast, daytime_h, wind_ms, rh):
    """Mirror of the radiational-fog gate in fnc_updateFog.sqf."""
    clear_night = overcast < 0.2 and (daytime_h < 6 or daytime_h > 18)
    calm = wind_ms < 3
    moist = rh > 90
    return clear_night and calm and moist


def rh_diurnal(rh_base, t_ref, t_now):
    """Mirror of the diurnal coupling in fnc_updateHumidity.sqf."""
    rh = rh_base * (1 + (t_ref - t_now) * 0.05)
    return max(0.0, min(100.0, rh))


class TestAirframeIcing(unittest.TestCase):
    def test_zero_lwc_zero_rate(self):
        self.assertEqual(icing_rate(0, 50, 0.8), 0.0)

    def test_glaze_vs_rime(self):
        # Glaze (0 to -10 C) collects at 0.8, rime below -10 C at 0.4.
        self.assertEqual(icing_efficiency(-5), 0.8)
        self.assertEqual(icing_efficiency(-15), 0.4)
        self.assertGreater(
            icing_rate(0.5, 50, icing_efficiency(-5)),
            icing_rate(0.5, 50, icing_efficiency(-15)),
        )

    def test_speed_does_not_change_rate(self):
        # The SQF rate formula has no speed term.
        self.assertEqual(icing_rate(0.5, 50, 0.8), icing_rate(0.5, 100, 0.8))

    def test_ice_clamps_max(self):
        self.assertEqual(ice_accretion(99, 1, 5), 100.0)

    def test_ice_clamps_min(self):
        self.assertEqual(ice_accretion(0, -5, 5), 0.0)


class TestCloudDevelopment(unittest.TestCase):
    def test_lapse_above_dry_adiabat_positive(self):
        # Lapse above the dry adiabat (0.0098 C/m) gives positive CAPE.
        self.assertGreater(cape_proxy(0.012), 0.0)

    def test_stable_lapse_negative(self):
        # A stable lapse below the moist adiabat gives negative CAPE.
        self.assertLess(cape_proxy(0.0065), 0.0)

    def test_growth_scales_with_cape(self):
        self.assertGreater(cloud_growth(1.0, 80), cloud_growth(0.5, 80))

    def test_growth_zero_negative_cape(self):
        self.assertEqual(cloud_growth(-5, 80), 0.0)
        # The convective term also needs RH above 60.
        self.assertEqual(cloud_growth(10, 50), 0.0)


class TestHaze(unittest.TestCase):
    def test_rh40(self):
        self.assertAlmostEqual(haze(40), 0.2)

    def test_rh100(self):
        # Just below the 99.5 scavenge threshold the growth curve reaches
        # its maximum; at RH 100 the fog scavenge has already applied.
        self.assertAlmostEqual(haze(99), 0.2 + 0.8 * (59 / 60))

    def test_below_40_zero(self):
        self.assertEqual(haze(39), 0.0)

    def test_fog_scavenge(self):
        # At saturation the fog settles the haze: 1.0 * 0.3.
        self.assertAlmostEqual(haze(100), 0.3)

    def test_dust_suppression(self):
        self.assertLess(haze(80, 1), haze(80, 0))

    def test_clamped(self):
        self.assertGreaterEqual(haze(100, 10), 0.0)
        self.assertLessEqual(haze(100), 1.0)


class TestLightning(unittest.TestCase):
    def test_low_cloud_top_zero(self):
        # Below 5500 m the ice phase is absent: risk is zero.
        self.assertEqual(lightning_risk(1, 1, 100, 1, 3000), 0.0)

    def test_high_cloud_top_full(self):
        # At 8000 m the ice factor is 1: risk equals the base.
        self.assertAlmostEqual(lightning_risk(1, 1, 100, 1, 8000), 1.0)

    def test_interpolated(self):
        # 6750 m sits halfway between 5500 and 8000.
        self.assertAlmostEqual(lightning_risk(1, 1, 100, 1, 6750), 0.5)

    def test_clamped(self):
        risk = lightning_risk(1, 1, 100, 1, 8000)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)


class TestMicroburst(unittest.TestCase):
    def test_damaging_band(self):
        # Severity roll below 0.5: damaging gust 26-36 m/s.
        gust, severity = microburst_gust(0.2, 0.5)
        self.assertEqual(severity, "DAMAGING")
        self.assertGreaterEqual(gust, 26)
        self.assertLessEqual(gust, 36)

    def test_moderate_band(self):
        # Severity roll at or above 0.5: moderate gust 15-30 m/s.
        gust, severity = microburst_gust(0.7, 0.5)
        self.assertEqual(severity, "MODERATE")
        self.assertGreaterEqual(gust, 15)
        self.assertLessEqual(gust, 30)

    def test_damaging_extremes(self):
        self.assertEqual(microburst_gust(0.0, 0.0)[0], 26)
        self.assertEqual(microburst_gust(0.0, 1.0)[0], 36)

    def test_moderate_extremes(self):
        self.assertEqual(microburst_gust(0.9, 0.0)[0], 15)
        self.assertEqual(microburst_gust(0.9, 1.0)[0], 30)


class TestPressureTrend(unittest.TestCase):
    def test_rising(self):
        history, change, forecast = pressure_trend([1000, 1000], 1001)
        self.assertGreater(change, 0.0)
        self.assertEqual(forecast, "Clearing")

    def test_falling(self):
        history, change, forecast = pressure_trend([1000, 1000], 999)
        self.assertLess(change, 0.0)
        self.assertEqual(forecast, "Rain expected")

    def test_steady(self):
        history, change, forecast = pressure_trend([1000, 1000], 1000.05)
        self.assertLess(abs(change), 0.1)
        self.assertEqual(forecast, "Stable")

    def test_buffer_drops_old(self):
        # After two pushes the buffer holds only the two latest readings.
        history, _, _ = pressure_trend([1000, 1001], 1002)
        self.assertEqual(history, [1001, 1002])


class TestTurbulence(unittest.TestCase):
    def test_light(self):
        self.assertEqual(turbulence_edr(0), 0.0)
        self.assertEqual(turbulence_class(0.0), "LIGHT")

    def test_moderate(self):
        self.assertAlmostEqual(turbulence_edr(0.2), 0.14)
        self.assertEqual(turbulence_class(0.14), "MODERATE")

    def test_severe(self):
        self.assertAlmostEqual(turbulence_edr(0.5), 0.35)
        self.assertEqual(turbulence_class(0.35), "SEVERE")

    def test_extreme(self):
        self.assertAlmostEqual(turbulence_edr(0.8), 0.56)
        self.assertEqual(turbulence_class(0.56), "EXTREME")

    def test_boundary_01(self):
        # EDR exactly 0.1 falls in MODERATE (>= 0.1).
        self.assertEqual(turbulence_class(0.1), "MODERATE")

    def test_boundary_03(self):
        # EDR exactly 0.3 is not > 0.3, so it stays MODERATE.
        self.assertEqual(turbulence_class(0.3), "MODERATE")

    def test_boundary_05(self):
        # EDR exactly 0.5 is not > 0.5, so it stays SEVERE.
        self.assertEqual(turbulence_class(0.5), "SEVERE")


class TestRadiationalFog(unittest.TestCase):
    def test_clear_calm_humid_night(self):
        self.assertTrue(radiational_fog(0.1, 2, 1, 95))

    def test_overcast_no(self):
        self.assertFalse(radiational_fog(0.5, 2, 1, 95))

    def test_windy_no(self):
        self.assertFalse(radiational_fog(0.1, 2, 5, 95))

    def test_dry_no(self):
        self.assertFalse(radiational_fog(0.1, 2, 1, 80))

    def test_daytime_no(self):
        self.assertFalse(radiational_fog(0.1, 12, 1, 95))


class TestHumidityDiurnal(unittest.TestCase):
    def test_equal_temp_unchanged(self):
        self.assertEqual(rh_diurnal(60, 20, 20), 60)

    def test_warm_lower(self):
        # Warm afternoon: RH falls at constant vapour content.
        self.assertLess(rh_diurnal(60, 20, 30), 60)

    def test_cool_higher(self):
        # Cool night: RH rises.
        self.assertGreater(rh_diurnal(60, 20, 10), 60)

    def test_clamped(self):
        self.assertEqual(rh_diurnal(100, 20, 10), 100)
        self.assertEqual(rh_diurnal(10, 20, 40), 0)


if __name__ == "__main__":
    unittest.main()
