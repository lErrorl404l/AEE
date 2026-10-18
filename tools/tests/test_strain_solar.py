#!/usr/bin/env python3
"""Strain solar and dehydration kernels (issues #304, #307).

#304.  fnc_calculateUVIndex reads EGVAR(core,currentSunElevation), the Meeus
solar elevation the lighting tick publishes for the mission date and the
world latitude/longitude.  The kernel used to rebuild a latitude-free
diurnal sine from dayTime, so the peak index landed at the wrong time and
the wrong latitude.

#307.  The dehydration band curve reaches 1.0 at a 6 % body-mass deficit.
The survival-pressure header states the anchors (TB MED 507; StatPearls:
2 % = 0.3, 4 % = 0.6, 6 % = 1.0).  The curve used to saturate at 0.75,
below the 0.8 the ACE3 medical integration gates on.

Both classes execute the shipped SQF through sqf_lite.  Nothing here is a
hand-transcribed model of the kernel.
"""

import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STRAIN = ROOT / "addons" / "strain" / "functions" / "strain"
UV = STRAIN / "fnc_calculateUVIndex.sqf"
DEHYDRATION = STRAIN / "fnc_calculateDehydrationRisk.sqf"
ASTRO = ROOT / "addons" / "lib" / "functions" / "astronomy" / "fnc_astroPosition.sqf"
CLOCK = ROOT / "addons" / "lib" / "functions" / "astronomy" / "fnc_gameClockToUT.sqf"
CIVIL = ROOT / "addons" / "lib" / "functions" / "fnc_civilDayNumber.sqf"

# The harness resolves QEGVAR/QGVAR to a stable placeholder string.
SUN_ELEV = "__QEGVAR__core_currentSunElevation"
REFERENCE_ALT = "__QEGVAR__core_referenceAltitude"
OZONE = "__QGVAR__ozoneDU"

# Gagge two-node reference man (addons/lib/functions/fnc_unitMetabolicRate.sqf).
REFERENCE_MASS_KG = 70.0


# ─── UV index (#304) ───────────────────────────────────────────────────────


def sun_elevation(date, clock_h, lat, lon):
    """The published solar elevation, in degrees, for a date and a place.

    Runs the real lib kernels the lighting tick runs, so the test exercises
    the same producer the kernel reads in the mission.
    """
    astro = lambda *a: run_sqf(ASTRO, list(a))  # noqa: E731
    civil = lambda *a: run_sqf(CIVIL, list(a))  # noqa: E731
    clock = lambda *a: run_sqf(  # noqa: E731
        CLOCK,
        list(a),
        globals_={
            "__FUNC__astroPosition": astro,
            "__FUNC__civilDayNumber": civil,
        },
    )
    ut = clock(list(date), clock_h, lon)
    return astro(ut[0], ut[1], lat, lon)[2]


def uv_index(elev, overcast=0.0, ozone=300.0, altitude=0.0, date=(2025, 6, 21)):
    """Run the shipped UV kernel with the core elevation bound."""
    ns = {SUN_ELEV: elev, REFERENCE_ALT: altitude, OZONE: ozone}
    return run_sqf(
        UV,
        [],
        globals_={
            "overcast": overcast,
            "date": list(date),
            "missionNamespace": ns,
            "CBA_fnc_currentUnit": lambda: None,
            "isNull": lambda obj: obj is None,
        },
    )


def madronich_clear_sky(elev, date=(2025, 6, 21), ozone=300.0):
    """The published clear-sky index for an elevation (Madronich 2007).

    12.50 * mu0^2.42 * (ozone/300)^-1.23 with the +/-3.3 % Earth-Sun
    distance term the kernel header cites.
    """
    mu0 = max(math.sin(math.radians(elev)), 0.0)
    if mu0 <= 0:
        return 0
    year, month, day = date
    doy = math.floor(275 * month / 9) - 2 * math.floor((month + 9) / 12) + day - 30
    dist = 1 + 0.033 * math.cos(math.radians(360 * (doy - 3) / 365))
    return round(12.50 * mu0**2.42 * (ozone / 300) ** -1.23 * dist)


class TestUVIndexFollowsTheRealSun(unittest.TestCase):
    """The index is driven by the published elevation, not a local model."""

    def test_mid_latitude_summer_noon(self):
        # Athens, 38 N, 21 June: the sun transits at about 75 deg, and the
        # published clear-sky index for that elevation is 11.
        elev = sun_elevation((2025, 6, 21), 12.0, 38.0, 23.7)
        self.assertAlmostEqual(elev, 75.4, delta=1.0)
        self.assertEqual(uv_index(elev, date=(2025, 6, 21)), 11)

    def test_high_latitude_winter_noon_is_near_zero(self):
        # 60 N on 21 December: the noon sun reaches about 6.5 deg, so the
        # index is 0.  The old latitude-free sine reported the summer peak
        # (12) on every date and every latitude.
        elev = sun_elevation((2025, 12, 21), 12.0, 60.0, 25.0)
        self.assertLess(elev, 10.0)
        self.assertLessEqual(uv_index(elev, date=(2025, 12, 21)), 1)

    def test_the_elevation_is_in_degrees(self):
        # 30 deg reads 2 and 90 deg reads 12 (Madronich: 12.5 * mu0^2.42).
        # A radians/degrees mix-up or a local diurnal model cannot produce
        # both, and the radian reading of 30 deg would read 12.
        self.assertEqual(uv_index(30.0), madronich_clear_sky(30.0))
        self.assertEqual(uv_index(90.0), madronich_clear_sky(90.0))
        self.assertEqual(uv_index(30.0), 2)
        self.assertEqual(uv_index(90.0), 12)

    def test_below_the_horizon_is_zero(self):
        self.assertEqual(uv_index(-90.0), 0)
        self.assertEqual(uv_index(-5.0), 0)

    def test_an_unset_elevation_reads_zero(self):
        # Before the first lighting tick the core value is unset.  The
        # fallback must read 0, not a latitude-free guess.
        value = run_sqf(
            UV,
            [],
            globals_={
                "overcast": 0.0,
                "date": [2025, 6, 21],
                "missionNamespace": {},
                "CBA_fnc_currentUnit": lambda: None,
                "isNull": lambda obj: obj is None,
            },
        )
        self.assertEqual(value, 0)

    def test_a_non_number_elevation_reads_zero(self):
        self.assertEqual(uv_index("nope"), 0)

    def test_no_local_diurnal_model_remains(self):
        src = UV.read_text(encoding="utf-8")
        self.assertIn("currentSunElevation", src)
        self.assertNotIn("dayTime", src)
        self.assertNotIn("_dayFraction", src)


# ─── Dehydration curve (#307) ──────────────────────────────────────────────

CASE_RE = re.compile(
    r"case\s*\((?P<cond>[^)]*)\)\s*:\s*\{\s*(?P<val>[^}]*?)\s*\}", re.S
)
DEFAULT_RE = re.compile(r"default\s*:?\s*\{\s*(?P<val>[^}]*?)\s*\}", re.S)


def risk_bands():
    """The shipped band map: its cases, in file order, and its default."""
    text = DEHYDRATION.read_text(encoding="utf-8")
    start = text.index("─── Risk calculation")
    end = text.index("─── Heat stroke overlay")
    block = text[start:end]
    cases = [(c, v) for c, v in CASE_RE.findall(block)]
    default = DEFAULT_RE.search(block)
    if not cases or default is None:
        raise AssertionError(f"could not read the band map from {DEHYDRATION}")
    return cases, default.group("val")


def risk_from_bands(deficit, cases=None, default=None):
    """Run the shipped band expressions through sqf_lite at one deficit.

    The case conditions and the case values are copied verbatim from the
    source file; only the switch wrapper is rewritten as nested if/else
    because the harness does not implement switch.
    """
    if cases is None:
        cases, default = risk_bands()
    expr = default
    for cond, value in reversed(cases):
        expr = f"if ({cond}) then {{ {value} }} else {{ {expr} }}"
    src = f"_deficit = {float(deficit)!r};\nprivate _risk = {expr};\n_risk\n"
    with tempfile.NamedTemporaryFile("w", suffix=".sqf", delete=False) as fh:
        fh.write(src)
        path = fh.name
    return run_sqf(path, [])


class TestDehydrationCurve(unittest.TestCase):
    """The band curve reaches the header anchors and the ACE3 gate."""

    def litres(self, percent):
        return REFERENCE_MASS_KG * percent / 100.0

    def test_two_percent_anchor(self):
        self.assertAlmostEqual(risk_from_bands(1.4), 0.3, places=6)

    def test_four_percent_anchor(self):
        self.assertAlmostEqual(risk_from_bands(2.8), 0.6, places=6)

    def test_six_percent_anchor_reaches_one(self):
        self.assertAlmostEqual(risk_from_bands(self.litres(6)), 1.0, places=6)

    def test_well_hydrated_is_zero(self):
        self.assertEqual(risk_from_bands(0.0), 0)
        self.assertEqual(risk_from_bands(0.4), 0)

    def test_monotonic_and_bounded(self):
        previous = -1.0
        for step in range(0, 81):
            risk = risk_from_bands(step / 10.0)
            self.assertGreaterEqual(risk, previous, f"not monotonic at {step / 10.0} L")
            self.assertGreaterEqual(risk, 0.0)
            self.assertLessEqual(risk, 1.0)
            previous = risk

    def test_the_ace3_gate_is_reachable_from_fluid_loss(self):
        # compat_ace3/fnc_integrateMedical.sqf:103 gates on _risk > 0.8.
        self.assertGreater(risk_from_bands(self.litres(6)), 0.8)
        self.assertGreater(risk_from_bands(4.2), 0.8)

    def test_the_ceiling_is_not_the_old_cap(self):
        self.assertNotAlmostEqual(risk_from_bands(4.2), 0.75, places=6)
        self.assertAlmostEqual(risk_from_bands(5.0), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
