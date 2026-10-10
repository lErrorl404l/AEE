#!/usr/bin/env python3
"""Reference checks for AEE's astronomical illumination and seeing models.

These tests validate the SQF implementation in addons/optics and
addons/environmental against known physical values.  They mirror the
exact formulas in the SQF source so that any drift breaks the tests.

Covers:
  - DEF Stan 61-027 night classification (classifyNight)
  - Krisciunas & Schaefer (1991) lunar illuminance (calculateLunarIllumination)
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
# The retired `environmental` addon split into lighting, weather and
# persistence; the astronomy tests read functions from more than one.
_ENV_ROOTS = (
    _REPO_ROOT / "addons" / "lighting" / "functions",
    _REPO_ROOT / "addons" / "weather" / "functions",
    _REPO_ROOT / "addons" / "persistence" / "functions",
)


def _read_recursive(base, name):
    """Read an SQF function file, resolving categorised subfolders (issue
    #203).  The function NAME is flat (aee_<mod>_fnc_<name>)."""
    if (base / name).exists():
        return _read_recursive(base, name)
    for f in base.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(f"{name} not found under {base}")


def _read_sqf(name, addon="optics"):
    """Read an SQF function file.  The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced."""
    if addon == "optics":
        return _read_recursive(_OPTICS, name)
    for root in _ENV_ROOTS:
        try:
            return _read_recursive(root, name)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"{name} not found under the environmental split")


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


# ─── Krisciunas & Schaefer (1991) lunar illumination mirrors ───────────────


def ks_lunar_lux(phase):
    """Mirror of fnc_calculateLunarIllumination.sqf (K&S 1991 magnitude law).

    Phase angle = |180 * (1 - 2*phase)| degrees (0 at full, 180 at new).
    Moon magnitude: m = -12.73 + 0.026|alpha| + 4e-9 * alpha^4.
    Illuminance:    E = 10^(-0.4 * (m + 14.18)) lux.
    The mod adds a 0.001 lux starlight floor and clamps to [0, 300].
    """
    phase_angle = abs(180 * (1 - 2 * phase))
    moon_mag = -12.73 + 0.026 * phase_angle + 4e-9 * (phase_angle**4)
    lux = 10 ** (-0.4 * (moon_mag + 14.18))
    return max(0.0, min(300.0, 0.001 + lux))


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


# ─── Star catalog sort mirror ──────────────────────────────────────────────


def sort_visible_by_altitude(stars):
    """Mirror of the sort in fnc_getStarCatalog.sqf.

    Each star is [name, altitude, azimuth, magnitude].  The SQF sorts a
    keyed copy with the altitude first, descending, so the highest
    altitude is element 0.  Sorting the raw items would order by the name
    string instead (issue #54).
    """
    return sorted(stars, key=lambda s: s[1], reverse=True)


# ─── Precession epoch mirror ───────────────────────────────────────────────


def precession_centuries(date):
    """Mirror of the precession _T in fnc_getStarCatalog.sqf.

    Day number to the Julian Day at 0h UT (Meeus, Astronomical Algorithms,
    Ch. 7, base 1721013.5), then Julian centuries since J2000.0 as
    (JD - 2451545.0) / 36525.  The old J2000 base returned about 20.25
    centuries at 2025 instead of 0.25.
    """
    y, mo, d = date
    jd = (
        1721013.5
        + 367 * y
        - math.floor(7 * (y + math.floor((mo + 9) / 12)) / 4)
        + math.floor(275 * mo / 9)
        + d
    )
    return (jd - 2451545.0) / 36525.0


def precession_angles(date):
    """IAU 1976 precession angles in degrees (Meeus Ch. 21; Lieske et al. 1977).

    Returns (zeta, z, theta) in degrees.  The constants are arcseconds per
    Julian century from J2000.0.  The old SQF used annual-arcsec constants
    applied per century, so every angle was about 100 times too small.
    """
    t = precession_centuries(date)
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t**3) / 3600.0
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t**3) / 3600.0
    theta = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t**3) / 3600.0
    return zeta, z, theta


def precess_j2000(ra_deg, dec_deg, date):
    """Mirror of the per-star precession in fnc_getStarCatalog.sqf.

    Standard equatorial rotation (Meeus Ch. 21, eq. 21.4).  SQF trig is
    degree-native, so the angles feed sin/cos directly.
    """
    zeta, z, theta = precession_angles(date)
    ra_z = math.radians(ra_deg + zeta)
    dec = math.radians(dec_deg)
    th = math.radians(theta)
    a = math.cos(dec) * math.sin(ra_z)
    b = math.cos(th) * math.cos(dec) * math.cos(ra_z) - math.sin(th) * math.sin(dec)
    c = math.sin(th) * math.cos(dec) * math.cos(ra_z) + math.cos(th) * math.sin(dec)
    return math.degrees(math.atan2(a, b)) + z, math.degrees(math.asin(c))


def precess_j2000_matrix(ra_deg, dec_deg, date):
    """Independent precession via the explicit rotation matrix (Meeus 21.5).

    A different code path from eq. 21.4, so agreement validates the transform.
    """
    zeta, z, theta = (math.radians(x) for x in precession_angles(date))
    cz, sz = math.cos(z), math.sin(z)
    cZ, sZ = math.cos(zeta), math.sin(zeta)
    ct, st = math.cos(theta), math.sin(theta)
    p11 = cZ * ct * cz - sZ * sz
    p12 = -cZ * ct * sz - sZ * cz
    p13 = -cZ * st
    p21 = sZ * ct * cz + cZ * sz
    p22 = -sZ * ct * sz + cZ * cz
    p23 = -sZ * st
    p31 = st * cz
    p32 = -st * sz
    p33 = ct
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    x = math.cos(dec) * math.cos(ra)
    y = math.cos(dec) * math.sin(ra)
    zz = math.sin(dec)
    x2 = p11 * x + p12 * y + p13 * zz
    y2 = p21 * x + p22 * y + p23 * zz
    z2 = p31 * x + p32 * y + p33 * zz
    return math.degrees(math.atan2(y2, x2)) % 360.0, math.degrees(math.asin(z2))


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
            addon="env",
        )

    # ── Lunar illumination (fnc_calculateLunarIllumination.sqf) ──
    def test_lunar_phase_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["29.530588853", "8777"],
            "synodic month and reference new moon",
            addon="env",
        )

    def test_ks_magnitude_law(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["-12.73", "0.026", "4e-9", "14.18"],
            "Krisciunas & Schaefer magnitude law",
            addon="env",
        )

    def test_lux_scale_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLunarIllumination.sqf",
            ["0.001 + _lux", "_lux max 0 min 300"],
            "lunar lux scale",
            addon="env",
        )

    # ── Limiting magnitude (fnc_calculateLimitingMagnitude.sqf) ──
    def test_limiting_magnitude_constants(self):
        self._assert_in_sqf(
            "fnc_calculateLimitingMagnitude.sqf",
            ["6.5 - log (_ambientLux / 0.001", "0.2 + 1.3", "0.9"],
            "NELM baseline and seeing penalty",
            addon="env",
        )

    # ── Star catalog sort order (fnc_getStarCatalog.sqf) ──
    def test_star_catalog_sorts_by_altitude(self):
        """The visible-star sort must key on altitude, not the name (#54)."""
        text = _read_sqf("fnc_getStarCatalog.sqf", addon="env")
        self.assertNotIn(
            "_visible sort false",
            text,
            "fnc_getStarCatalog.sqf: alphabetical sort restored (issue #54)",
        )
        self._assert_in_sqf(
            "fnc_getStarCatalog.sqf",
            ["[(_x select 1), _x]", "_keyed sort true"],
            "altitude-keyed descending sort",
            addon="env",
        )

    def test_star_catalog_has_no_fabricated_canopus_b(self):
        """Canopus_b is not a BSC5 entry and must not reappear (#55)."""
        text = _read_sqf("fnc_getStarCatalog.sqf", addon="env")
        self.assertNotIn(
            "Canopus_b",
            text,
            "fnc_getStarCatalog.sqf: fabricated Canopus_b star restored (issue #55)",
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


class TestLunarIllumination(unittest.TestCase):
    """Krisciunas & Schaefer (1991) lunar illuminance in lux."""

    def test_new_moon_starlight_floor(self):
        """New moon (phase=0) → starlight floor ~0.001 lux."""
        lux = ks_lunar_lux(0.0)
        self.assertGreaterEqual(lux, 0.001)
        self.assertLess(lux, 0.002)

    def test_full_moon_matches_published(self):
        """Full moon (phase=0.5) → ~0.26 lux, the published K&S value."""
        lux = ks_lunar_lux(0.5)
        self.assertGreater(lux, 0.20)
        self.assertLess(lux, 0.35)

    def test_quarter_moon_matches_published(self):
        """Quarter moon (phase=0.25) → ~0.025 lux, the published value."""
        lux = ks_lunar_lux(0.25)
        self.assertGreater(lux, 0.01)
        self.assertLess(lux, 0.05)

    def test_last_quarter_symmetric(self):
        """Last quarter (phase=0.75) → symmetric with first quarter."""
        self.assertAlmostEqual(ks_lunar_lux(0.75), ks_lunar_lux(0.25), places=6)

    def test_crescent_moon(self):
        """Crescent (phase=0.125) → low illuminance."""
        lux = ks_lunar_lux(0.125)
        self.assertGreater(lux, 0.001)
        self.assertLess(lux, 0.01)

    def test_gibbous_moon(self):
        """Gibbous (phase=0.375) → high illuminance, below full moon."""
        lux = ks_lunar_lux(0.375)
        self.assertGreater(lux, 0.05)
        self.assertLess(lux, ks_lunar_lux(0.5))

    def test_peak_at_full_moon(self):
        """Peak illuminance is at phase=0.5 (full moon)."""
        vals = [(p / 100, ks_lunar_lux(p / 100)) for p in range(0, 101)]
        peak_phase = max(vals, key=lambda x: x[1])
        self.assertAlmostEqual(peak_phase[0], 0.5, places=1)

    def test_monotonic_rise_to_full(self):
        """Illuminance rises monotonically from new to full moon."""
        prev = ks_lunar_lux(0.0)
        for p in range(1, 51):
            current = ks_lunar_lux(p / 100)
            self.assertGreater(current, prev)
            prev = current

    def test_lux_never_negative(self):
        """Illuminance stays non-negative across all phases."""
        for p in range(0, 101):
            self.assertGreaterEqual(ks_lunar_lux(p / 100), 0.0)


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
        """Star azimuth from north, clockwise, in degrees."""
        dec = math.radians(dec_deg)
        lat = math.radians(lat_deg)
        ha = math.radians(ha_deg)
        az = math.degrees(
            math.atan2(
                math.sin(ha),
                math.cos(ha) * math.sin(lat) - math.tan(dec) * math.cos(lat),
            )
        )
        # Meeus Ch. 13 measures azimuth from the south, westward; shift to
        # the north-clockwise convention fnc_starDirection consumes.
        return (az + 180.0) % 360.0

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

    def test_azimuth_south_at_meridian(self):
        """A star south of the zenith (ha=0) is due south: azimuth 180."""
        az = self._azimuth(30.0, 50.0, 0)
        self.assertAlmostEqual(az, 180.0, places=6)

    def test_azimuth_east_at_minus_90(self):
        """A star at hour angle -90 (rising) is due east: azimuth 90."""
        az = self._azimuth(0.0, 45.0, -90.0)
        self.assertAlmostEqual(az, 90.0, places=6)


class TestPrecessionCenturies(unittest.TestCase):
    """The precession epoch _T is true centuries since J2000.0.

    fnc_getStarCatalog.sqf derives T from a day-number Julian Day.  The
    J2000 base (2451545.0 - 0.5) gave about 20.25 centuries at 2025 and
    over-applied the precession angle by about 0.11 degrees.  The JD at
    0h UT base (1721013.5) gives about 0.25.
    """

    def test_2025_is_a_quarter_century(self):
        """The old J2000 base returned ~20.25, not ~0.25."""
        self.assertAlmostEqual(precession_centuries((2025, 1, 1)), 0.25, places=2)

    def test_one_decade_is_a_tenth_century(self):
        a = precession_centuries((2025, 1, 1))
        b = precession_centuries((2035, 1, 1))
        self.assertAlmostEqual(b - a, 0.1, delta=0.002)

    def test_source_uses_rational_julian_day_base(self):
        """Drift-lock: the SQF precession base must be 1721013.5."""
        text = _read_sqf("fnc_getStarCatalog.sqf", addon="env")
        self.assertIn("1721013.5 + 367 * _year", text)
        self.assertNotIn("2451545.0 + 367 * _year", text)


class TestPrecessionModel(unittest.TestCase):
    """IAU 1976 precession angles and the standard rotation (Meeus Ch. 21).

    The old constants were annual arcseconds applied per century, so every
    angle was about 100 times too small (theta 0.0014 deg instead of
    0.139 deg at T = 0.25).
    """

    STARS = [
        (0.0, 0.0),
        (101.287, -16.716),  # Sirius
        (279.235, 38.784),  # Vega
        (41.054063, 49.228469),  # theta Persei (Meeus example 21.b)
        (350.0, -80.0),
    ]
    DATE = (2025, 1, 1)

    def test_theta_at_quarter_century(self):
        """2004.3109 * 0.25 / 3600 = 0.139 deg, not the old 0.0014."""
        _, _, theta = precession_angles(self.DATE)
        self.assertAlmostEqual(theta, 2004.3109 * 0.25 / 3600.0, places=4)

    def test_zeta_z_at_quarter_century(self):
        zeta, z, _ = precession_angles(self.DATE)
        self.assertAlmostEqual(zeta, 2306.2181 * 0.25 / 3600.0, places=4)
        self.assertAlmostEqual(z, 2306.2181 * 0.25 / 3600.0, places=4)

    def test_source_uses_iau_1976_angles(self):
        """Drift-lock: the SQF must carry the IAU 1976 constants."""
        text = _read_sqf("fnc_getStarCatalog.sqf", addon="env")
        for const in (
            "2306.2181",
            "0.30188",
            "0.017998",
            "1.09468",
            "0.018203",
            "2004.3109",
            "0.42665",
            "0.041833",
        ):
            self.assertIn(const, text)
        self.assertNotIn("20.043109", text)
        self.assertNotIn("2.5976176", text)

    def test_source_uses_standard_rotation(self):
        """Drift-lock: the Meeus 21.4 rotation, not the old simplified form."""
        text = _read_sqf("fnc_getStarCatalog.sqf", addon="env")
        self.assertIn("cos _thetaDeg * _cosDec * cos _raZeta", text)
        self.assertIn("sin _thetaDeg * _cosDec * cos _raZeta", text)
        self.assertNotIn("cos (_raDeg - _zDeg)", text)

    def test_atan2_form_matches_rotation_matrix(self):
        for ra, dec in self.STARS:
            with self.subTest(ra=ra, dec=dec):
                a = precess_j2000(ra, dec, self.DATE)
                b = precess_j2000_matrix(ra, dec, self.DATE)
                self.assertAlmostEqual(
                    math.remainder(a[0] - b[0], 360.0), 0.0, places=4
                )
                self.assertAlmostEqual(a[1], b[1], places=4)

    def test_quarter_century_shift_is_physical(self):
        """A J2000 star at (0, 0) moves ~0.32 deg in RA by 2025.

        The old 100x-small constants gave ~0.0007 deg.
        """
        ra, dec = precess_j2000(0.0, 0.0, self.DATE)
        self.assertAlmostEqual(ra, 0.320342, places=4)
        self.assertAlmostEqual(dec, 0.139184, places=4)

    def test_j2000_is_identity(self):
        for ra, dec in self.STARS:
            got = precess_j2000(ra, dec, (2000, 1, 1))
            self.assertAlmostEqual(math.remainder(got[0] - ra, 360.0), 0.0, places=2)
            self.assertAlmostEqual(got[1], dec, places=2)


class TestStarCatalogSortOrder(unittest.TestCase):
    """Visible stars are sorted by altitude, highest first (issue #54)."""

    def test_sorted_descending_by_altitude(self):
        stars = [
            ["Sirius", 12.0, 180.0, -1.46],
            ["Vega", 74.0, 90.0, 0.03],
            ["Polaris", 52.0, 0.0, 2.02],
            ["Canopus", 31.0, 200.0, -0.74],
        ]
        alts = [s[1] for s in sort_visible_by_altitude(stars)]
        self.assertEqual(alts, sorted(alts, reverse=True))

    def test_highest_altitude_first(self):
        stars = [
            ["Sirius", 12.0, 180.0, -1.46],
            ["Vega", 74.0, 90.0, 0.03],
            ["Polaris", 52.0, 0.0, 2.02],
        ]
        self.assertEqual(sort_visible_by_altitude(stars)[0][0], "Vega")

    def test_not_alphabetical(self):
        """Regression for #54: the result must not be name-ordered."""
        stars = [
            ["Arcturus", 20.0, 180.0, -0.05],
            ["Betelgeuse", 80.0, 170.0, 0.42],
            ["Vega", 50.0, 90.0, 0.03],
        ]
        names = [s[0] for s in sort_visible_by_altitude(stars)]
        self.assertNotEqual(names, sorted(names))

    def test_empty_catalog(self):
        self.assertEqual(sort_visible_by_altitude([]), [])


if __name__ == "__main__":
    unittest.main()
