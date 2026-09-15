#!/usr/bin/env python3
"""Reference checks for AEE's astronomical illumination and seeing models.

These tests validate the SQF implementation in addons/optics and
addons/environmental against known physical values.  They mirror the
exact formulas in the SQF source so that any drift breaks the tests.

Covers:
  - DEF Stan 61-027 night classification (classifyNight)
  - Baldet opposition surge (calculateLunarIllumination)
  - Naked-eye limiting magnitude (calculateLimitingMagnitude)
  - Star catalogue coordinate transform (getStarCatalog)

Run: python3 -m unittest tools.tests.test_astronomical -v
"""

import math
import unittest
from pathlib import Path

# Repo root: tools/tests/ -> up two levels.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_OPTICS = _REPO_ROOT / "addons" / "optics" / "functions"
_ENV = _REPO_ROOT / "addons" / "environmental" / "functions"


def _read_sqf(name, addon="optics"):
    """Read an SQF function file.  The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced."""
    base = _OPTICS if addon == "optics" else _ENV
    return (base / name).read_text(encoding="utf-8")


# ─── DEF Stan 61-027 night classification mirrors ──────────────────────────


def classify_night(sun_elev, moon_phase):
    """Mirror of fnc_classifyNight.sqf — DEF Stan 61-027 twilight zones.

    Returns integer 0-4:
      0 = Day (sunElev > -6)
      1 = Civil Twilight (-6 to -12)
      2 = Nautical Twilight (-12 to -18)
      3 = Full Night (sunElev < -18, moonPhase >= 10%)
      4 = Dark Night (sunElev < -18, moonPhase < 10%)
    """
    if sun_elev > -6:
        return 0
    elif sun_elev > -12:
        return 1
    elif sun_elev > -18:
        return 2
    else:
        if moon_phase < 0.10:
            return 4
        else:
            return 3


# ─── Baldet opposition surge mirrors ───────────────────────────────────────


def baldet_lunar_illumination(phase):
    """Mirror of fnc_calculateLunarIllumination.sqf Baldet correction.

    Standard Lambert: illumination = (1 - cos(360*phase)) / 2
    Baldet (1993): adds ~30% opposition surge near full moon.
    Phase angle = |180 * (1 - 2*phase)| degrees (0 at full, 180 at new).
    Surge = 1 + 0.30 * exp(-phaseAngle^2 / 450).
    """
    illumination = (1 - math.cos(math.radians(360 * phase))) / 2
    phase_angle = abs(180 * (1 - 2 * phase))
    surge = 1 + 0.30 * math.exp(-(phase_angle**2) / 450)
    return illumination * surge


def lambert_lunar_illumination(phase):
    """Standard Lambert sphere without Baldet correction (baseline)."""
    return (1 - math.cos(math.radians(360 * phase))) / 2


# ─── Limiting magnitude mirrors ────────────────────────────────────────────


def calculate_limiting_magnitude(ambient_lux, seeing):
    """Mirror of fnc_calculateLimitingMagnitude.sqf.

    mBase = 6.5 - log10(ambientLux / 0.001)
    seeingPenalty = 0.2 + 1.3 * (seeing - 0.1) / 0.9
    mLim = clamp(mBase - seeingPenalty, 2.0, 7.0)
    """
    m_base = 6.5 - math.log10(max(ambient_lux / 0.001, 1e-6))
    clamped_seeing = max(0.1, min(1.0, seeing))
    seeing_penalty = 0.2 + 1.3 * ((clamped_seeing - 0.1) / 0.9)
    m_lim = m_base - seeing_penalty
    return max(2.0, min(7.0, m_lim))


# ═══════════════════════════════════════════════════════════════════════════
# Test classes
# ═══════════════════════════════════════════════════════════════════════════


class TestSQFSync(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context, addon="optics"):
        text = _read_sqf(filename, addon)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_astronomical.py.",
        )

    # ── Night classification (fnc_classifyNight.sqf) ──
    def test_classify_thresholds(self):
        self._assert_in_sqf(
            "fnc_classifyNight.sqf",
            ["> -6", "> -12", "> -18", "< 0.10"],
            "DEF Stan twilight thresholds",
        )

    # ── Lunar illumination (fnc_calculateLunarIllumination.sqf) ──
    def test_lunar_phase_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["29.530588853", "8777", "(1 - cos (360 * _phase)) / 2"],
            "synodic month, reference new moon, Lambert sphere",
            addon="environmental",
        )

    def test_baldet_surge_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["abs (180 * (1 - 2 * _phase))", "0.30 * exp", "450"],
            "Baldet opposition surge",
            addon="environmental",
        )

    def test_lux_scale_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["0.001 + _illumination * 0.299", "0 max _lux min 300"],
            "lunar lux scale",
            addon="environmental",
        )

    # ── Limiting magnitude (fnc_calculateLimitingMagnitude.sqf) ──
    def test_limiting_magnitude_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLimitingMagnitude.sqf",
            ["6.5 - log (_ambientLux / 0.001", "0.2 + 1.3", "0.9"],
            "NELM baseline and seeing penalty",
        )


class TestClassifyNight(unittest.TestCase):
    """DEF Stan 61-027 twilight zone classification."""

    def test_day_high_sun(self):
        """Sun at +45 deg → Day."""
        self.assertEqual(classify_night(45, 0.5), 0)

    def test_day_horizon(self):
        """Sun at -1 deg → still Day (above -6)."""
        self.assertEqual(classify_night(-1, 0.5), 0)

    def test_civil_twilight_start(self):
        """Sun exactly at -6 deg → Civil Twilight."""
        self.assertEqual(classify_night(-6, 0.5), 1)

    def test_civil_twilight_mid(self):
        """Sun at -9 deg → Civil Twilight."""
        self.assertEqual(classify_night(-9, 0.5), 1)

    def test_nautical_twilight_start(self):
        """Sun exactly at -12 deg → Nautical Twilight."""
        self.assertEqual(classify_night(-12, 0.5), 2)

    def test_nautical_twilight_mid(self):
        """Sun at -15 deg → Nautical Twilight."""
        self.assertEqual(classify_night(-15, 0.5), 2)

    def test_astronomical_night_start(self):
        """Sun exactly at -18 deg → Full Night (moon above 10%)."""
        self.assertEqual(classify_night(-18, 0.5), 3)

    def test_full_night_bright_moon(self):
        """Sun -25 deg, moon 50% → Full Night."""
        self.assertEqual(classify_night(-25, 0.50), 3)

    def test_full_night_crescent(self):
        """Sun -20 deg, moon 15% → Full Night (between 10% and dark threshold)."""
        self.assertEqual(classify_night(-20, 0.15), 3)

    def test_dark_night(self):
        """Sun -25 deg, moon 5% → Dark Night."""
        self.assertEqual(classify_night(-25, 0.05), 4)

    def test_dark_night_new_moon(self):
        """Sun -30 deg, moon 0% → Dark Night."""
        self.assertEqual(classify_night(-30, 0.0), 4)

    def test_dark_night_boundary(self):
        """Moon phase exactly 10% → Full Night (not dark)."""
        self.assertEqual(classify_night(-25, 0.10), 3)

    def test_sun_at_minus17(self):
        """Sun at -17 deg → still Nautical (above -18)."""
        self.assertEqual(classify_night(-17, 0.5), 2)

    def test_solar_midnight(self):
        """Sun at -45 deg, no moon → Dark Night."""
        self.assertEqual(classify_night(-45, 0.0), 4)

    def test_polar_night(self):
        """Sun at -23 deg (polar night), full moon → Full Night."""
        self.assertEqual(classify_night(-23, 0.80), 3)


class TestBaldetLunarIllumination(unittest.TestCase):
    """Baldet (1993) opposition surge on lunar illumination."""

    def test_new_moon_zero(self):
        """New moon (phase=0) → zero illumination."""
        self.assertAlmostEqual(baldet_lunar_illumination(0.0), 0.0, places=6)

    def test_full_moon_above_lambert(self):
        """Full moon (phase=0.5) → Baldet surge makes it brighter than Lambert."""
        baldet = baldet_lunar_illumination(0.5)
        lambert = lambert_lunar_illumination(0.5)
        self.assertAlmostEqual(lambert, 1.0, places=6)
        self.assertGreater(baldet, lambert)

    def test_full_moon_surge_magnitude(self):
        """Full moon surge should be ~30% above Lambert = ~1.30."""
        baldet = baldet_lunar_illumination(0.5)
        self.assertAlmostEqual(baldet, 1.30, places=2)

    def test_first_quarter(self):
        """First quarter (phase=0.25) → ~0.5 illumination, minimal surge."""
        baldet = baldet_lunar_illumination(0.25)
        lambert = lambert_lunar_illumination(0.25)
        self.assertAlmostEqual(lambert, 0.5, places=4)
        # Surge at 90 deg phase angle is small
        self.assertGreater(baldet, lambert)
        self.assertLess(baldet, 0.6)

    def test_last_quarter(self):
        """Last quarter (phase=0.75) → symmetric with first quarter."""
        self.assertAlmostEqual(
            baldet_lunar_illumination(0.75), baldet_lunar_illumination(0.25), places=6
        )

    def test_crescent_moon(self):
        """Crescent (phase=0.125) → low illumination, moderate surge."""
        illum = baldet_lunar_illumination(0.125)
        self.assertGreater(illum, 0.0)
        self.assertLess(illum, 0.3)

    def test_gibbous_moon(self):
        """Gibbous (phase=0.375) → high illumination, moderate surge."""
        illum = baldet_lunar_illumination(0.375)
        self.assertGreater(illum, 0.7)
        self.assertLess(illum, 1.3)

    def test_surge_symmetric_around_full(self):
        """Surge is symmetric around full moon."""
        self.assertAlmostEqual(
            baldet_lunar_illumination(0.45), baldet_lunar_illumination(0.55), places=6
        )

    def test_surges_peaks_near_full(self):
        """Peak surge is within 5% of phase=0.5."""
        vals = [(p / 100, baldet_lunar_illumination(p / 100)) for p in range(0, 101)]
        peak_phase = max(vals, key=lambda x: x[1])
        self.assertAlmostEqual(peak_phase[0], 0.5, places=1)


class TestLimitingMagnitude(unittest.TestCase):
    """Naked-eye limiting magnitude from illuminance + seeing."""

    def test_starlight_good_seeing(self):
        """Starlight (0.001 lux) + excellent seeing (0.1) → ~6.3."""
        m_lim = calculate_limiting_magnitude(0.001, 0.1)
        self.assertAlmostEqual(m_lim, 6.3, places=1)

    def test_starlight_poor_seeing(self):
        """Starlight (0.001 lux) + terrible seeing (1.0) → ~5.0."""
        m_lim = calculate_limiting_magnitude(0.001, 1.0)
        self.assertAlmostEqual(m_lim, 5.0, places=1)

    def test_full_moon_good_seeing(self):
        """Full moon (0.3 lux) + excellent seeing → ~3.8."""
        m_lim = calculate_limiting_magnitude(0.3, 0.1)
        self.assertAlmostEqual(m_lim, 3.8, places=1)

    def test_full_moon_poor_seeing(self):
        """Full moon (0.3 lux) + terrible seeing → ~2.5."""
        m_lim = calculate_limiting_magnitude(0.3, 1.0)
        self.assertAlmostEqual(m_lim, 2.5, places=0)

    def test_quarter_moon(self):
        """Quarter moon (~0.03 lux) + moderate seeing (0.5) → ~4.2."""
        m_lim = calculate_limiting_magnitude(0.03, 0.5)
        self.assertAlmostEqual(m_lim, 4.2, places=0)

    def test_clamp_upper(self):
        """Very dark sky → clamped to 7.0."""
        m_lim = calculate_limiting_magnitude(0.0001, 0.1)
        self.assertLessEqual(m_lim, 7.0)

    def test_clamp_lower(self):
        """Very bright sky → clamped to 2.0."""
        m_lim = calculate_limiting_magnitude(10.0, 1.0)
        self.assertGreaterEqual(m_lim, 2.0)

    def test_seeing_clamped_low(self):
        """Seeing below 0.1 → clamped to 0.1."""
        m1 = calculate_limiting_magnitude(0.001, 0.0)
        m2 = calculate_limiting_magnitude(0.001, 0.1)
        self.assertAlmostEqual(m1, m2, places=6)

    def test_seeing_clamped_high(self):
        """Seeing above 1.0 → clamped to 1.0."""
        m1 = calculate_limiting_magnitude(0.001, 2.0)
        m2 = calculate_limiting_magnitude(0.001, 1.0)
        self.assertAlmostEqual(m1, m2, places=6)

    def test_monotonic_decrease_with_light(self):
        """More ambient light → lower limiting magnitude (fewer stars visible)."""
        prev = calculate_limiting_magnitude(0.001, 0.5)
        for lux in [0.01, 0.05, 0.1, 0.3, 1.0]:
            current = calculate_limiting_magnitude(lux, 0.5)
            self.assertLess(current, prev)
            prev = current

    def test_monotonic_decrease_with_seeing(self):
        """Worse seeing → lower limiting magnitude."""
        prev = calculate_limiting_magnitude(0.01, 0.1)
        for s in [0.3, 0.5, 0.7, 1.0]:
            current = calculate_limiting_magnitude(0.01, s)
            self.assertLessEqual(current, prev)
            prev = current


class TestStarCatalogVisibility(unittest.TestCase):
    """Star visibility calculations (coordinate transforms)."""

    def _lst(self, day_of_year, ut_hours):
        """Simplified local sidereal time (degrees)."""
        return (100.46 + 0.985647 * day_of_year + 15.0 * ut_hours) % 360

    def _altitude(self, dec_deg, lat_deg, ha_deg):
        """Star altitude from declination, latitude, hour angle."""
        dec = math.radians(dec_deg)
        lat = math.radians(lat_deg)
        ha = math.radians(ha_deg)
        alt = math.asin(
            math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha)
        )
        return math.degrees(alt)

    def _azimuth(self, dec_deg, lat_deg, ha_deg):
        """Star azimuth from declination, latitude, hour angle."""
        dec = math.radians(dec_deg)
        lat = math.radians(lat_deg)
        ha = math.radians(ha_deg)
        az = math.atan2(
            math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(dec) * math.cos(lat)
        )
        return math.degrees(az) % 360

    def test_sirius_visible_southern_hemisphere(self):
        """Sirius (Dec -16.7) visible from southern hemisphere at midnight."""
        lst = self._lst(0, 0)  # midnight UT, day 0
        ha = lst - 101.29  # Sirius RA in degrees
        alt = self._altitude(-16.716, -33.0, ha)  # Sydney latitude
        self.assertGreater(alt, 0)

    def test_polaris_near_pole(self):
        """Polaris (Dec +89.3) altitude ≈ latitude from northern hemisphere.

        Exact formula: asin(cos(dec-lat)) when ha=0 = 52.2 deg at lat 51.5.
        The simple approx lat+(dec-90) = 50.8 diverges near the pole.
        """
        alt = self._altitude(89.264, 51.5, 0)  # London latitude, hour angle 0
        self.assertAlmostEqual(alt, 52.2, delta=0.5)

    def test_star_below_horizon(self):
        """A southern star is invisible from high northern latitudes."""
        alt = self._altitude(-60.0, 60.0, 0)  # Achernar from Oslo
        self.assertLess(alt, 0)

    def test_altitude_varies_with_hour_angle(self):
        """Star altitude changes as it transits the meridian."""
        dec, lat = 45.0, 50.0
        alt_rising = self._altitude(dec, lat, -90)  # 6h before transit
        alt_transit = self._altitude(dec, lat, 0)  # at transit
        alt_setting = self._altitude(dec, lat, 90)  # 6h after transit
        self.assertGreater(alt_transit, alt_rising)
        self.assertGreater(alt_transit, alt_setting)

    def test_azimuth_north_at_meridian(self):
        """Star on the meridian (ha=0) has azimuth 0 or 180."""
        az = self._azimuth(30.0, 50.0, 0)
        self.assertTrue(abs(az) < 1 or abs(az - 180) < 1 or abs(az - 360) < 1)


if __name__ == "__main__":
    unittest.main()
