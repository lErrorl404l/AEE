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


def radio_propagation_index(
    freq_hz, dist_m, temp_c, rh, pressure_hpa, sun_night, biome=""
):
    """Mirror of fnc_calculateRadioPropagation.sqf (Friis + ducting).

    sun_night: True when the sun is down (sunOrMoon == -1).
    biome: the AEE biome code, used for the terrain-loss list.
    """
    fspl = (20 * log10(dist_m)) + (20 * log10(freq_hz)) - 147.55

    duct_bonus = 0.0
    if temp_c > 25 and sun_night:
        duct_bonus += min((temp_c - 25) / 20, 0.5) * 6
    if rh > 60:
        duct_bonus += ((rh - 50) / 10) * 0.05 * 6
    if pressure_hpa > 1020:
        duct_bonus += ((pressure_hpa - 1013) / 10) * 0.02 * 6

    absorption = 0.0
    if temp_c > 30 and rh < 30:
        absorption = 2
    # HF ionospheric absorption is gated on frequency below 30 MHz.
    if freq_hz < 30e6:
        absorption += 0  # mirror keeps the hook; the value is mission state

    terrain_loss = 0.0
    if biome in ["UMa", "Uhd", "Uhb", "Uhi", "Cfa", "Cfb", "Cfc", "Dfa", "Dfb"]:
        terrain_loss = 3

    link_budget = 37 - fspl - terrain_loss + duct_bonus - absorption
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

    def test_warm_night_ducting_boost(self):
        day = radio_propagation_index(1e8, 5000, 28, 50, 1013, False)
        night = radio_propagation_index(1e8, 5000, 28, 50, 1013, True)
        self.assertGreater(night, day)

    def test_humidity_boost(self):
        dry = radio_propagation_index(1e8, 5000, 15, 50, 1013, False)
        humid = radio_propagation_index(1e8, 5000, 15, 80, 1013, False)
        self.assertGreater(humid, dry)

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


if __name__ == "__main__":
    unittest.main()
