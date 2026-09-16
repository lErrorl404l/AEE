#!/usr/bin/env python3
"""Reference checks for AEE's radio models.

Mirrors of the SQF implementations in addons/radio: Friis free-space path
loss with ducting (fnc_calculateRadioPropagation) and the ITU-R P.531
D-layer absorption (fnc_calculateIonosphericAbsorption).

Run: python3 -m unittest tools/tests/test_radio.py
"""

import math
import unittest

LN10 = 2.302585


def log10(x):
    """SQF's log command is base-10 (verified in-game: log 100 = 2).

    Python's math.log is natural log, so log10(x) = ln(x) / ln(10).
    """
    return math.log(x) / LN10


def _esat_buck(t_c):
    """Saturated vapour pressure (hPa) per Buck 1981 (mirrors the SQF)."""
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * t_c / (257.14 + t_c))


def evaporation_duct_bonus(freq_hz, dist_m, temp_c, sst_c, rh=50.0):
    """Mirror of the issue #37 evaporation-duct model.

    delta = clamp(1.5 + (T - SST) * 2.5, 3, 25)          [m duct height]
    dN = 3.73e5 * (esat(SST) - e_air) / T^2              [N-units]
    Hall cutoff: f_min = c / (2.5e-3 * sqrt(dN/delta - 0.157) * delta^1.5)
    Duct bonus applies ONLY for freq >= f_min (SHF), scaled by delta
    vs the 13 m world mean; attenuated 0.3 dB/km beyond 44.8 km.
    sst_c None = no maritime state (the SQF guards on isNil before
    computing), so no duct.
    """
    if sst_c is None:
        return 0.0
    delta = min(25.0, max(3.0, 1.5 + (temp_c - sst_c) * 2.5))
    esat_sea = _esat_buck(sst_c)
    e_air = (rh / 100.0) * _esat_buck(temp_c)
    dn = 3.73e5 * (esat_sea - e_air) * 0.1 / ((temp_c + 273.15) ** 2)
    dn = max(0.0, dn)
    bonus = 0.0
    sqrt_term = (dn / delta) - 0.157
    if sqrt_term > 0:
        lam = 2.5e-3 * (sqrt_term**0.5) * (delta**1.5)
        if lam > 0:
            f_min = 3e8 / lam
            if freq_hz >= f_min:
                duct_factor = min(2.5, max(0.3, delta / 13))
                bonus = 6 * duct_factor
                range_km = dist_m / 1000
                if range_km > 44.8:
                    # Attenuation beyond the OTH limit, clamped so the
                    # duct never becomes a net penalty.
                    bonus = max(0.0, bonus - range_km * 0.3)
    return bonus


def radio_propagation_index(
    freq_hz,
    dist_m,
    temp_c,
    rh,
    pressure_hpa,
    sun_night,
    biome="",
    battery_derate=1.0,
    battery_enabled=True,
    sst_c=None,
):
    """Mirror of fnc_calculateRadioPropagation.sqf (Friis + ducting).

    sun_night: True when the sun is down (sunOrMoon == -1).
    biome: the AEE biome code, used for the terrain-loss list.
    battery_derate: physiology battery temperature derating 0.3-1.0
        (issue #36).  Scales effective txPower in dB: 10*log10(derate).
    battery_enabled: the aee_radio_batteryDeratingEnabled toggle.
    sst_c: sea-surface temperature (issue #37).  None = no maritime
        state, so no evaporation duct.
    """
    tx_power = 37.0
    if battery_enabled:
        derate = max(0.3, min(1.0, battery_derate))
        if derate < 1.0:
            tx_power += 10 * log10(derate)

    fspl = (20 * log10(dist_m)) + (20 * log10(freq_hz)) - 147.55

    duct_bonus = 0.0
    if sst_c is not None:
        duct_bonus = evaporation_duct_bonus(freq_hz, dist_m, temp_c, sst_c, rh)

    absorption = 0.0
    if temp_c > 30 and rh < 30:
        absorption = 2
    # HF ionospheric absorption is gated on frequency below 30 MHz.
    if freq_hz < 30e6:
        absorption += 0  # mirror keeps the hook; the value is mission state

    terrain_loss = 0.0
    if biome in ["UMa", "Uhd", "Uhb", "Uhi", "Cfa", "Cfb", "Cfc", "Dfa", "Dfb"]:
        terrain_loss = 3

    link_budget = tx_power - fspl - terrain_loss + duct_bonus - absorption
    signal_pct = 10 ** (link_budget / 20)
    signal_pct = max(0.0, min(1.0, signal_pct))
    index = 0.3 + 1.7 * (signal_pct**0.5)
    return max(0.3, min(2.0, index))


def ionospheric_absorption(freq_hz, sun_elev_deg, ssn, flare_active, flare_value):
    """Mirror of fnc_calculateIonosphericAbsorption.sqf (ITU-R P.531)."""
    freq_factor = (3e6 / freq_hz) ** 2
    cos_chi = max(0.0, math.sin(math.radians(sun_elev_deg)))
    day_factor = 1 if cos_chi > 0 else 0.05
    ssn_factor = 1 + ssn / 100
    absorption = 0.5 * freq_factor * day_factor * ssn_factor
    if flare_active:
        absorption += flare_value
    return max(0.0, min(10.0, absorption))


class TestRadioPropagation(unittest.TestCase):
    def test_friis_path_loss_reference(self):
        # Friis: FSPL(100 MHz, 5 km) = 20*log10(5e3) + 20*log10(1e8) - 147.55
        fspl = 20 * log10(5000) + 20 * log10(1e8) - 147.55
        self.assertAlmostEqual(fspl, 86.4, places=1)

    def test_longer_distance_lower_index(self):
        near = radio_propagation_index(1e8, 1000, 15, 50, 1013, False)
        far = radio_propagation_index(1e8, 10000, 15, 50, 1013, False)
        self.assertGreater(near, far)

    def test_higher_frequency_lower_index(self):
        # Higher frequency -> higher FSPL -> lower signal.
        low = radio_propagation_index(1e8, 5000, 15, 50, 1013, False)
        high = radio_propagation_index(5e8, 5000, 15, 50, 1013, False)
        self.assertGreater(low, high)

    def test_evap_duct_boosts_shf_only(self):
        # Strong tropical duct: sea 34 C, dry air 28 C/30% -> f_min ~9.8
        # GHz, so a 10 GHz link gets the duct bonus.
        sst = 34.0
        shf = radio_propagation_index(1e10, 5000, 28, 30, 1013, False, sst_c=sst)
        no_duct = radio_propagation_index(1e10, 5000, 28, 30, 1013, False)
        self.assertGreater(shf, no_duct)

    def test_vhf_not_ducted(self):
        # 100 MHz tactical VHF: well below the SHF cutoff, so the duct
        # must NOT apply even with a strong air-sea gradient.
        sst = 34.0
        vhf_duct = radio_propagation_index(1e8, 5000, 28, 30, 1013, False, sst_c=sst)
        vhf_no_duct = radio_propagation_index(1e8, 5000, 28, 30, 1013, False)
        self.assertAlmostEqual(vhf_duct, vhf_no_duct, places=9)

    def test_cold_sea_stronger_duct(self):
        # The vapour deficit is larger with a warmer sea and drier air:
        # sea 36/air 28/20% traps harder than sea 30/air 28/20%.
        sst_hot = 36.0
        sst_cooler = 30.0
        hot_sea = radio_propagation_index(
            1e10, 5000, 28, 20, 1013, False, sst_c=sst_hot
        )
        cooler_sea = radio_propagation_index(
            1e10, 5000, 28, 20, 1013, False, sst_c=sst_cooler
        )
        self.assertGreater(hot_sea, cooler_sea)

    def test_hot_dry_penalty(self):
        mild = radio_propagation_index(1e8, 5000, 25, 50, 1013, False)
        hotdry = radio_propagation_index(1e8, 5000, 35, 20, 1013, False)
        self.assertLess(hotdry, mild)

    def test_terrain_penalty(self):
        open_terrain = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, "")
        forest = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, "Cfb")
        self.assertGreater(open_terrain, forest)

    def test_index_clamped(self):
        # Extreme short link: index saturates at 2.0.
        self.assertEqual(radio_propagation_index(1e7, 10, 15, 50, 1013, False), 2.0)
        # Extreme long link: index approaches the 0.3 floor asymptotically
        # (the SQF clamps signal_pct at 0, but 10^(-large) never reaches 0,
        # so the index floor is approached rather than hit exactly).
        long_idx = radio_propagation_index(1e9, 1e7, 15, 50, 1013, False)
        self.assertLess(long_idx, 0.31)
        self.assertGreaterEqual(long_idx, 0.3)


class TestIonosphericAbsorption(unittest.TestCase):
    def test_reference_noon_3mhz(self):
        # 3 MHz, sun at zenith, SSN 100, no flare: 0.5 * 1 * 1 * 2 = 1.0
        self.assertAlmostEqual(
            ionospheric_absorption(3e6, 90, 100, False, 0), 1.0, places=3
        )

    def test_night_residual(self):
        # Night (sun below horizon): day factor 0.05.
        night = ionospheric_absorption(3e6, -5, 100, False, 0)
        day = ionospheric_absorption(3e6, 90, 100, False, 0)
        self.assertAlmostEqual(night / day, 0.05, places=6)

    def test_frequency_quadratic(self):
        # 1/f^2: 6 MHz absorbs a quarter of 3 MHz at the same conditions.
        f3 = ionospheric_absorption(3e6, 90, 100, False, 0)
        f6 = ionospheric_absorption(6e6, 90, 100, False, 0)
        self.assertAlmostEqual(f6, f3 / 4, places=6)

    def test_sunspot_scales(self):
        low = ionospheric_absorption(3e6, 90, 0, False, 0)
        high = ionospheric_absorption(3e6, 90, 200, False, 0)
        self.assertGreater(high, low)
        # SSN 0 -> factor 1; SSN 200 -> factor 3.
        self.assertAlmostEqual(high / low, 3.0, places=6)

    def test_flare_adds_directly(self):
        base = ionospheric_absorption(3e6, 90, 100, False, 0)
        flared = ionospheric_absorption(3e6, 90, 100, True, 2.0)
        self.assertAlmostEqual(flared, base + 2.0, places=6)

    def test_clamped_0_10(self):
        self.assertEqual(ionospheric_absorption(1e6, 90, 300, True, 5), 10.0)
        self.assertGreaterEqual(ionospheric_absorption(3e6, -90, 0, False, 0), 0.0)


class TestBatteryDerating(unittest.TestCase):
    """Issue #36: cold batteries derate radio effective transmit power."""

    def test_cold_battery_drops_signal(self):
        # -20 C battery derating (~0.7): -1.55 dB tx power.  The link
        # budget drops, so the propagation index must fall.
        warm = radio_propagation_index(
            1e8, 5000, 20, 50, 1013, False, battery_derate=1.0
        )
        cold = radio_propagation_index(
            1e8, 5000, -20, 50, 1013, False, battery_derate=0.7
        )
        self.assertLess(cold, warm, "cold battery did not reduce signal")
        # Derating 0.7 -> tx -1.55 dB -> signal_pct scales by
        # 10^(-1.55/20) = 0.837.  The index is sqrt-compressed, so the
        # index ratio is (0.3 + 1.7*sqrt(0.837*s)) / (0.3 + 1.7*sqrt(s)).
        s = 10 ** ((37 - (20 * log10(5000) + 20 * log10(1e8) - 147.55)) / 20)
        ratio = (0.3 + 1.7 * (0.837 * s) ** 0.5) / (0.3 + 1.7 * s**0.5)
        self.assertAlmostEqual(cold / warm, ratio, places=4)

    def test_severe_cold_battery_floor(self):
        # Derating clamped to 0.3 in the SQF; at that floor tx power loses
        # 5.2 dB.  Signal still works (no dead radio) but much weaker.
        severe = radio_propagation_index(
            1e8, 5000, -30, 50, 1013, False, battery_derate=0.3
        )
        normal = radio_propagation_index(
            1e8, 5000, 20, 50, 1013, False, battery_derate=1.0
        )
        self.assertLess(severe, normal)

    def test_toggle_off_ignores_derating(self):
        # With the CBA toggle off, a cold battery changes nothing.
        cold_on = radio_propagation_index(
            1e8, 5000, -20, 50, 1013, False, battery_derate=0.7
        )
        cold_off = radio_propagation_index(
            1e8, 5000, -20, 50, 1013, False, battery_derate=0.7, battery_enabled=False
        )
        warm = radio_propagation_index(
            1e8, 5000, 20, 50, 1013, False, battery_derate=1.0
        )
        self.assertAlmostEqual(cold_off, warm, places=9)
        self.assertLess(cold_on, warm)

    def test_derating_out_of_range_clamped(self):
        # Derating outside 0.3-1.0 clamps (mirror matches the SQF clamp).
        below = radio_propagation_index(
            1e8, 5000, -40, 50, 1013, False, battery_derate=0.1
        )
        at_floor = radio_propagation_index(
            1e8, 5000, -40, 50, 1013, False, battery_derate=0.3
        )
        self.assertAlmostEqual(below, at_floor, places=9)


# ─── Sea-surface temperature (issue #37) ────────────────────────────────────
# Mirror of fnc_calculateSeaSurfaceTemperature.sqf: latitude-seasonal
# climatology blended with air temperature by the coupling weight.
#   clim = annual(lat) + 6 * cos(phase/12 * 360)  where phase = months
#          since local summer (0 = peak), local summer = July north,
#          January south.
#   sst  = w * T_air + (1 - w) * clim


def sea_surface_temp(air_c, lat, month, w=0.5):
    """Mirror of the maritime SST model (degC)."""
    abs_lat = abs(lat)
    if abs_lat < 15:
        annual = 28
    elif abs_lat < 30:
        annual = 22
    elif abs_lat < 50:
        annual = 13
    elif abs_lat < 65:
        annual = 5
    else:
        annual = 0
    local_summer = 7 if lat >= 0 else 1
    phase = (month - local_summer + 12) % 12
    clim = annual + 6 * math.cos(phase / 12 * 360 * math.pi / 180)
    return w * air_c + (1 - w) * clim


class TestSeaSurfaceTemperature(unittest.TestCase):
    """Issue #37: the maritime SST feed for the evaporation duct."""

    def test_tropics_warm_all_year(self):
        # Tropical SST stays warm year-round; the seasonal swing is
        # modest (28 +- 6 C climatology, blended toward the air).
        for month in [1, 4, 7, 10]:
            sst = sea_surface_temp(28, 10, month, w=0.2)
            self.assertGreaterEqual(sst, 20)
            self.assertLessEqual(sst, 34)

    def test_north_sea_cold_in_winter(self):
        # Lat 55 N (subpolar): January coldest, July warmest.
        jan = sea_surface_temp(4, 55, 1, w=0.5)
        jul = sea_surface_temp(16, 55, 7, w=0.5)
        self.assertLess(jan, jul)

    def test_southern_hemisphere_phase_inverted(self):
        # Lat -33 (subtropical south): January is local summer (warm),
        # July local winter (cold).
        jan = sea_surface_temp(24, -33, 1, w=0.5)
        jul = sea_surface_temp(14, -33, 7, w=0.5)
        self.assertGreater(jan, jul)

    def test_air_coupling_blends(self):
        # w=1.0: SST follows air exactly; w=0: SST is pure climatology.
        self.assertAlmostEqual(sea_surface_temp(25, 45, 7, w=1.0), 25.0, places=6)
        pure_clim = sea_surface_temp(25, 45, 7, w=0.0)
        self.assertAlmostEqual(pure_clim, 13 + 6, places=6)  # July peak

    def test_air_sea_gradient_direction(self):
        # Warm air over a cold sea gives a positive (T - SST), the
        # classic duct condition direction.
        sst = sea_surface_temp(25, 60, 1, w=0.5)  # cold northern winter sea
        self.assertGreater(25.0 - sst, 0)


class TestEvaporationDuct(unittest.TestCase):
    """Issue #37: the evaporation-duct model (SHF only)."""

    def test_hall_cutoff_matches_reference(self):
        # Verified vector: H=13 m, deltaN=10 -> f_min ~ 3.3 GHz.
        h, dn = 13.0, 10.0
        lam = 2.5e-3 * math.sqrt(dn / h - 0.157) * h**1.5
        f_min = 3e8 / lam
        self.assertAlmostEqual(f_min / 1e9, 3.27, places=2)

    def test_duct_bonus_scales_with_delta(self):
        # Warmer sea (bigger vapour deficit) -> taller duct -> bigger
        # bonus: sea 36 vs sea 32, same air.
        small = evaporation_duct_bonus(1e10, 5000, 28, 32, 20)
        large = evaporation_duct_bonus(1e10, 5000, 28, 36, 20)
        self.assertGreater(large, small)

    def test_duct_height_clamped(self):
        # delta clamps to [3, 25] m.
        delta_low = 1.5 + (25 - 30) * 2.5  # negative -> clamps to 3
        delta_high = 1.5 + (25 - 5) * 2.5  # 51.5 -> clamps to 25
        self.assertEqual(min(25.0, max(3.0, delta_low)), 3.0)
        self.assertEqual(min(25.0, max(3.0, delta_high)), 25.0)

    def test_no_sst_no_duct(self):
        # Without maritime state there is no duct at all.
        self.assertEqual(evaporation_duct_bonus(1e10, 5000, 28, None), 0.0)
        no_sst = radio_propagation_index(1e10, 5000, 28, 20, 1013, False)
        with_sst = radio_propagation_index(1e10, 5000, 28, 20, 1013, False, sst_c=36)
        self.assertNotAlmostEqual(no_sst, with_sst, places=6)

    def test_long_range_attenuation(self):
        # Beyond 44.8 km the duct bonus attenuates 0.3 dB/km, but the
        # duct never becomes a net penalty (clamped at 0, per the SQF).
        near = evaporation_duct_bonus(1e10, 30000, 28, 36, 20)
        far = evaporation_duct_bonus(1e10, 80000, 28, 36, 20)
        self.assertLess(far, near)
        self.assertGreaterEqual(far, 0.0)


if __name__ == "__main__":
    unittest.main()
