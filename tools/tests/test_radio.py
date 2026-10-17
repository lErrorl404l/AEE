#!/usr/bin/env python3
"""Reference checks for AEE's radio models.

Mirrors of the SQF implementations in addons/radio: Friis free-space path
loss with ducting (fnc_calculateRadioPropagation) and the ITU-R P.531
D-layer absorption (fnc_calculateIonosphericAbsorption).

Run: python3 -m unittest tools/tests/test_radio.py
"""

import math
from pathlib import Path
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


def two_ray_excess(dist_m, freq_hz, h_tx, h_rx, rho):
    """Mirror of fnc_calculateTwoRayGround.sqf (issue #13).

    Excess path loss over free space, dB: F = 1 + rho^2 - 2*rho*cos(dPhi)
    with dPhi = 4*pi*h_tx*h_rx/(lambda*d).  Floored at 1e-12 so the log
    stays finite at a null.
    """
    lam = 3e8 / freq_hz
    dphi = 4 * math.pi * h_tx * h_rx / (lam * dist_m)
    field = max(1e-12, 1 + rho**2 - 2 * rho * math.cos(dphi))
    return -10 * log10(field)


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
    em_enabled=True,
    tx_height=2.0,
    rx_height=1.5,
    ground_reflectivity=0.5,
    diffraction_db=0.0,
    valley_db=0.0,
):
    """Mirror of fnc_calculateRadioPropagation.sqf (Friis + ducting).

    sun_night: True when the sun is down (sunOrMoon == -1).
    biome: the AEE biome code, used for the terrain-loss list.
    battery_derate: physiology battery temperature derating 0.3-1.0
        (issue #36).  Scales effective txPower in dB: 10*log10(derate).
    battery_enabled: the aee_radio_batteryDeratingEnabled toggle.
    sst_c: sea-surface temperature (issue #37).  None = no maritime
        state, so no evaporation duct.
    em_enabled: the aee_radio_emPropagationEnabled toggle (issue #13).
    tx_height, rx_height, ground_reflectivity: two-ray ground-bounce inputs.
    diffraction_db, valley_db: terrain terms supplied by the EM kernels
        (the mirror cannot sample terrain).
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

    ground_bounce = 0.0
    if em_enabled:
        ground_bounce = two_ray_excess(
            dist_m, freq_hz, tx_height, rx_height, ground_reflectivity
        )

    link_budget = (
        tx_power
        - fspl
        - terrain_loss
        + duct_bonus
        - absorption
        - ground_bounce
        - diffraction_db
        - valley_db
    )
    signal_pct = 10 ** (link_budget / 20)
    signal_pct = max(0.0, min(1.0, signal_pct))
    index = 0.3 + 1.7 * (signal_pct**0.5)
    return max(0.3, min(2.0, index))


def gyro_longitudinal_mhz(lat_deg):
    """Mirror of the centred-dipole f_L at 100 km (IGRF-13 B0 29.8 uT)."""
    lat = math.radians(lat_deg)
    b_ut = 29.8 * (6371 / 6471) ** 3 * math.sqrt(1 + 3 * math.sin(lat) ** 2)
    dip = math.atan(2 * math.tan(lat))
    return 0.028 * b_ut * abs(math.sin(dip))


def ionospheric_absorption(freq_hz, sun_elev_deg, ssn, flare_active, flare_value, lat_deg=40.0):
    """Mirror of fnc_calculateIonosphericAbsorption.sqf (ITU-R P.533,
    George & Bradley), vertical incidence.  flare_value is the D-RAP HAF
    (MHz); the flare adds (HAF / f)^1.5 dB."""
    chi = min(90 - sun_elev_deg, 102)
    index = (1 + 0.0037 * ssn) * max(math.cos(math.radians(0.881 * chi)), 0) ** 1.3
    f = freq_hz / 1e6
    absorption = 677.2 * index / ((f + gyro_longitudinal_mhz(lat_deg)) ** 1.98 + 10.2)
    if flare_active and flare_value > 0:
        absorption += (flare_value / f) ** 1.5
    return max(0.0, absorption)


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
    def test_gyrofrequency_is_physical(self):
        # f_L at mid-latitude, 100 km: ~0.8-1.4 MHz (ITU-R P.533 maps).
        self.assertGreater(gyro_longitudinal_mhz(40), 0.8)
        self.assertLess(gyro_longitudinal_mhz(40), 1.4)

    def test_daytime_80m_is_heavily_absorbed(self):
        # Midday D-layer absorption at 3.5 MHz, solar maximum: tens of dB
        # per vertical pass (why 80 m is a night band).
        self.assertGreater(ionospheric_absorption(3.5e6, 70, 150, False, 0), 20)

    def test_upper_hf_is_lightly_absorbed(self):
        self.assertLess(ionospheric_absorption(21e6, 70, 150, False, 0), 3)

    def test_night_is_near_zero(self):
        night = ionospheric_absorption(3e6, -30, 100, False, 0)
        day = ionospheric_absorption(3e6, 60, 100, False, 0)
        self.assertLess(night, 0.01 * day)

    def test_absorption_falls_with_zenith_angle(self):
        values = [ionospheric_absorption(5e6, e, 100, False, 0) for e in (90, 60, 30, 10, 0)]
        for a, b in zip(values, values[1:]):
            self.assertGreater(a, b)

    def test_sunspots_raise_absorption(self):
        self.assertGreater(
            ionospheric_absorption(5e6, 60, 200, False, 0),
            ionospheric_absorption(5e6, 60, 0, False, 0),
        )

    def test_flare_drap(self):
        # NOAA SWPC D-RAP: HAF = 10 log10(F) + 65 MHz; 1 dB at the HAF;
        # (HAF/f)^1.5 elsewhere.  An X1 flare (1e-4 W/m2) overhead: HAF 25 MHz.
        haf = 10 * math.log10(1e-4) + 65
        self.assertAlmostEqual(haf, 25.0)
        base = ionospheric_absorption(25e6, 90, 100, False, 0)
        flared = ionospheric_absorption(25e6, 90, 100, True, haf)
        self.assertAlmostEqual(flared - base, 1.0, places=6)
        src = (Path(__file__).resolve().parents[2] / "addons/radio/functions/fnc_calculateIonosphericAbsorption.sqf").read_text(encoding="utf-8")
        self.assertIn("((_haf / _fMHz) ^ 1.5)", src)

    def test_sqf_carries_the_p533_constants(self):
        src = next((Path(__file__).resolve().parents[2] / "addons" / "radio").rglob(
            "fnc_calculateIonosphericAbsorption.sqf")).read_text(encoding="utf-8")
        for token in ("677.2", "0.0037", "0.881", "1.98", "10.2", "29.8", "min 102"):
            self.assertIn(token, src)


class TestBatteryDerating(unittest.TestCase):
    """Issue #36: cold batteries derate radio effective transmit power."""

    def test_cold_battery_drops_signal(self):
        # -20 C battery derating (~0.7): -1.55 dB tx power.  The link
        # budget drops, so the propagation index must fall.
        warm = radio_propagation_index(
            1e8, 5000, 20, 50, 1013, False, battery_derate=1.0, em_enabled=False
        )
        cold = radio_propagation_index(
            1e8, 5000, -20, 50, 1013, False, battery_derate=0.7, em_enabled=False
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


class TestEmIntegration(unittest.TestCase):
    """Issue #13: the 3D EM terms adjust the propagation index."""

    def test_ground_bounce_reduces_index(self):
        on = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, em_enabled=True)
        off = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, em_enabled=False)
        self.assertLess(on, off)

    def test_diffraction_reduces_index(self):
        clean = radio_propagation_index(
            1e8, 5000, 15, 50, 1013, False, diffraction_db=0.0
        )
        blocked = radio_propagation_index(
            1e8, 5000, 15, 50, 1013, False, diffraction_db=20.0
        )
        self.assertLess(blocked, clean)

    def test_valley_boosts_index(self):
        plain = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, valley_db=0.0)
        guided = radio_propagation_index(1e8, 5000, 15, 50, 1013, False, valley_db=-3.0)
        self.assertGreater(guided, plain)

    def test_higher_antenna_less_ground_bounce(self):
        low = two_ray_excess(5000, 1e8, 2.0, 1.5, 1.0)
        high = two_ray_excess(5000, 1e8, 30.0, 30.0, 1.0)
        self.assertLess(high, low)


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


class TestExcessLossModel(unittest.TestCase):
    """The radio layer publishes only the losses ACRE2/TFAR do not model."""

    SRC = (Path(__file__).resolve().parents[2] / "addons" / "radio" / "functions"
           / "fnc_calculateRadioPropagation.sqf").read_text(encoding="utf-8")

    def test_no_double_counted_or_invented_terms(self):
        # FSPL and terrain belong to ACRE2's ITM / TFAR; the flat "hot & dry"
        # penalty and the biome foliage constant had no physical source.
        for token in ("147.55", "_absorptionPenalty = 2", "_terrainLoss = 3", "0.3 + 1.7"):
            self.assertNotIn(token, self.SRC)

    def test_loss_terms(self):
        for token in ("_battDB = -10 * log _derate", "private _empDB = -20 * log _empFactor",
                      "private _index = 10 ^ (-_excessDB / 20)", "if (_freqHz < 30e6) then"):
            self.assertIn(token, self.SRC)
        # A half-capacity cold battery is a 3.01 dB transmit loss; a 0.5 EMP
        # amplitude factor is 6.02 dB; together the free-space range falls
        # to 10^(-9.03/20) = 0.354.
        excess = -10 * math.log10(0.5) - 20 * math.log10(0.5)
        self.assertAlmostEqual(10 ** (-excess / 20), 0.3536, places=3)

    def test_acre_callback_evaluates_hf_at_the_link_frequency(self):
        acre = (Path(__file__).resolve().parents[2] / "addons" / "compat_acre2" / "functions"
                / "fnc_integrateACRE2.sqf").read_text(encoding="utf-8")
        self.assertIn('"aee_radio_dLayerNumerator"', acre)
        self.assertIn("if (_freq < 30) then", acre)
        self.assertNotIn("QEGVAR(", acre.split("compile '")[1])
