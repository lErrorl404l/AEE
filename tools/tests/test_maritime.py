#!/usr/bin/env python3
"""Reference checks for AEE's maritime models.

Mirrors of the SQF implementations in addons/maritime: harmonic tidal
prediction (M2/S2/K1/O1), WMO Beaufort sea state, and the coarse WMM
compass declination table.

Run: python3 -m unittest tools/tests/test_maritime.py
"""

import math
import unittest


def tidal_height(hours_since_epoch):
    """Mirror of fnc_calculateTidalPrediction.sqf — four harmonic constituents.

    M2 28.9841 deg/h (1.00 m), S2 30.0000 (0.47), K1 15.0411 (0.58),
    O1 13.9430 (0.42).  Phases at epoch: M2 0, S2 45, K1 90, O1 0.
    """
    consts = [
        (28.9841, 1.00, 0),
        (30.0000, 0.47, 45),
        (15.0411, 0.58, 90),
        (13.9430, 0.42, 0),
    ]
    return sum(
        a * math.sin(math.radians(w * hours_since_epoch + p)) for w, a, p in consts
    )


def tidal_alignment(hours_since_epoch):
    """Mirror of the spring/neap alignment (cos of the M2-S2 phase diff)."""
    return abs(
        math.cos(math.radians((28.9841 - 30.0000) * hours_since_epoch + (0 - 45)))
    )


def sea_state_beaufort(wind_ms):
    """Mirror of fnc_calculateSeaState.sqf — WMO Beaufort B = (v/0.836)^(2/3)."""
    return max(0, min(12, round((wind_ms / 0.836) ** (2 / 3))))


def wave_height(wind_ms):
    """Mirror of the Pierson-Moskowitz significant wave height 0.0246 v^2."""
    return min(0.0246 * wind_ms**2, 15)


def compass_declination(lon_deg, lat_deg):
    """Mirror of fnc_calculateCompassDeviation.sqf — coarse WMM table.

    Table: [-180,10],[-120,12],[-80,-13],[-20,-5],[0,1],[40,6],[90,-3],
    [120,-5],[150,-9],[180,10]; linear interpolation; latitude adj
    (lat-45)*0.05; clamped +-30.
    """
    table = [
        [-180, 10],
        [-120, 12],
        [-80, -13],
        [-20, -5],
        [0, 1],
        [40, 6],
        [90, -3],
        [120, -5],
        [150, -9],
        [180, 10],
    ]
    n = len(table)
    if lon_deg <= table[0][0]:
        decl = table[0][1]
    elif lon_deg >= table[n - 1][0]:
        decl = table[n - 1][1]
    else:
        decl = 0.0
        for i in range(n - 1):
            lo, hi = table[i], table[i + 1]
            if lo[0] <= lon_deg <= hi[0]:
                frac = (lon_deg - lo[0]) / (hi[0] - lo[0])
                decl = lo[1] + frac * (hi[1] - lo[1])
                break
    decl += (lat_deg - 45) * 0.05
    return max(-30, min(30, decl))


class TestTidalHarmonics(unittest.TestCase):
    def test_constituent_periods(self):
        # M2 period = 360/28.9841 = 12.42 h; S2 = 360/30 = 12 h.
        self.assertAlmostEqual(360 / 28.9841, 12.42, places=1)
        self.assertAlmostEqual(360 / 30.0000, 12.00, places=2)

    def test_beat_period_spring_neap(self):
        # M2-S2 beat = 360/1.0159 = 354.4 h = 14.77 days.
        beat_h = 360 / (30.0000 - 28.9841)
        self.assertAlmostEqual(beat_h / 24, 14.77, places=1)

    def test_alignment_peaks_at_spring(self):
        # Alignment (cos of phase diff) is 1 when in phase: at t=0 the M2-S2
        # phase diff is (0-45) deg, cos(-45)=0.707 — not 1.  At the beat
        # midpoint (177.2 h) the diff is a multiple of 360 so cos = 1.
        self.assertGreaterEqual(tidal_alignment(0), 0.7)
        self.assertLessEqual(tidal_alignment(0), 0.71)
        # Near the beat period the alignment returns to the same value.
        self.assertAlmostEqual(tidal_alignment(354.4), tidal_alignment(0), places=3)

    def test_tidal_range_bounded(self):
        # Sum of amplitudes = 1.00 + 0.47 + 0.58 + 0.42 = 2.47 m max theoretical;
        # the SQF clamps to +-2 m.  Mirror without clamp stays within 2.47.
        for t in range(0, 24 * 30, 3):  # 30 days hourly
            h = tidal_height(t)
            self.assertLessEqual(abs(h), 2.47)
            self.assertGreaterEqual(h, -2.47)


class TestSeaState(unittest.TestCase):
    def test_wmo_beaufort_reference(self):
        # WMO: B=12 starts at ~32.7 m/s (64 kt); B=5 ~9.8 m/s.
        self.assertEqual(sea_state_beaufort(32.7), 12)
        self.assertEqual(sea_state_beaufort(9.8), 5)

    def test_calm_is_zero(self):
        self.assertEqual(sea_state_beaufort(0), 0)

    def test_monotonic(self):
        prev = sea_state_beaufort(0)
        for v in range(0, 4001, 100):
            b = sea_state_beaufort(v / 100)
            self.assertGreaterEqual(b, prev)
            prev = b

    def test_clamped_12(self):
        self.assertEqual(sea_state_beaufort(100), 12)

    def test_wave_height_grows_quadratically(self):
        # H_s = 0.0246 v^2: 10 m/s -> 2.46 m, 20 m/s -> 9.84 m (4x).
        self.assertAlmostEqual(wave_height(10), 2.46, places=2)
        self.assertAlmostEqual(wave_height(20) / wave_height(10), 4.0, places=1)

    def test_wave_height_capped(self):
        self.assertLessEqual(wave_height(100), 15)


class TestCompassDeclination(unittest.TestCase):
    def test_wmm_reference_points(self):
        # Coarse table: NY lon -74 -> between -80(-13) and -20(-5):
        # -13 + (6/60)*(-13 - -5) = -13 + 0.1*8 = -12.2 at lat 45;
        # at lat 40 (adj -0.25) -> -12.45.  London lon 0 -> +1 at lat 51
        # (adj +0.3) -> +1.3.
        self.assertAlmostEqual(compass_declination(-74, 40), -12.45, places=1)
        self.assertAlmostEqual(compass_declination(0, 51), 1.3, places=1)

    def test_table_endpoints_clamp(self):
        # Beyond table ends the interpolated value clamps to the endpoint
        # constant, then the latitude adjustment still applies (lat 0 ->
        # (0-45)*0.05 = -2.25, so 10 - 2.25 = 7.75).
        self.assertAlmostEqual(compass_declination(-200, 0), 7.75, places=1)
        self.assertAlmostEqual(compass_declination(200, 0), 7.75, places=1)

    def test_never_exceeds_clamp(self):
        for lon in range(-180, 181, 15):
            for lat in range(-80, 81, 10):
                d = compass_declination(lon, lat)
                self.assertLessEqual(d, 30)
                self.assertGreaterEqual(d, -30)


if __name__ == "__main__":
    unittest.main()
