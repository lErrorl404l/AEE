#!/usr/bin/env python3
"""Meteor shower data, kernels, renderer and wiring (issue #122).

The meteor layer reuses the starfield's coordinate maths and night/cloud
state.  This suite locks:

  - the generated IMO Table 5 data contract (gen_meteor_showers.py);
  - the shared sidereal-time kernel (fnc_siderealTime) against a Python
    Meeus mirror, executed from the real SQF via sqf_lite;
  - the pure meteor kernels (fnc_radiantHorizontal, fnc_showerIsActive,
    fnc_meteorRate) and the composite (fnc_meteorState), executed from the
    real SQF with the sub-kernels injected through globals;
  - the client renderer contract (a #lightpoint + #particlesource emitter,
    no sound, no line drawing, no BIS_fnc_sunriseSunsetTime);
  - the wiring (PREPS, setting, stringtable, postInit, runner, Makefile, CI).
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "validation"))

from gen_meteor_showers import parse_showers  # noqa: E402
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SENSOR = ROOT / "addons" / "environmental" / "functions" / "astronomy"

SHOWERS_SRC = SENSOR / "fnc_meteorShowers.sqf"
IMO_SRC = ROOT / "data" / "astronomy" / "sources" / "imo_cal2025.txt"
SIDEREAL = SENSOR / "fnc_siderealTime.sqf"
RADIANT = SENSOR / "fnc_radiantHorizontal.sqf"
ACTIVE = SENSOR / "fnc_showerIsActive.sqf"
RATE = SENSOR / "fnc_meteorRate.sqf"
STATE = SENSOR / "fnc_meteorState.sqf"
REGISTRAR = SENSOR / "fnc_renderMeteors.sqf"
WORKER = SENSOR / "fnc_updateMeteors.sqf"

PREP = ROOT / "addons" / "environmental" / "XEH_PREP.hpp"
POSTINIT = ROOT / "addons" / "environmental" / "XEH_postInit.sqf"
SETTINGS = ROOT / "addons" / "environmental" / "initSettings.inc.sqf"
STRINGTABLE = ROOT / "addons" / "environmental" / "stringtable.xml"
RUNNER = ROOT / "tools" / "run_tests.py"
MAKEFILE = ROOT / "Makefile"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def rows():
    return parse_showers(IMO_SRC.read_text(encoding="utf-8"))


class TestMeteorShowersData(unittest.TestCase):
    """The generated IMO Table 5 data is complete and traceable."""

    def test_count_is_eight(self):
        self.assertEqual(len(rows()), 8)

    def test_codes_unique_and_expected(self):
        codes = [r[0] for r in rows()]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(
            codes, ["QUA", "LYR", "ETA", "PER", "ORI", "LEO", "GEM", "URS"]
        )

    def test_anchor_gem_zhr(self):
        gem = [r for r in rows() if r[0] == "GEM"][0]
        self.assertEqual(gem[13], 150)

    def test_anchor_qua_lambda(self):
        qua = [r for r in rows() if r[0] == "QUA"][0]
        self.assertAlmostEqual(qua[8], 283.15, places=6)

    def test_anchor_rows(self):
        # Exact IMO Table 5 values for the two end-of-year showers.
        qua = [r for r in rows() if r[0] == "QUA"][0]
        self.assertEqual(qua[:8], ("QUA", "Quadrantids", 12, 28, 1, 12, 1, 3))
        self.assertEqual(qua[9:], (230, 49, 41, 2.1, 80))
        urs = [r for r in rows() if r[0] == "URS"][0]
        self.assertEqual(urs[:8], ("URS", "Ursids", 12, 17, 12, 26, 12, 22))
        self.assertEqual(urs[9:], (217, 76, 33, 2.8, 10))

    def test_negative_declination_normalised(self):
        eta = [r for r in rows() if r[0] == "ETA"][0]
        self.assertEqual(eta[10], -1)

    def test_generated_file_matches_source(self):
        text = SHOWERS_SRC.read_text(encoding="utf-8")
        self.assertIn("private _showers = [", text)
        self.assertNotIn("],\n];", text)
        self.assertEqual(text.count('["'), 8)


def sidereal_lst(date, time_s):
    """Independent Meeus Ch. 12 mirror of fnc_siderealTime (degrees)."""
    y, mo, d = date
    jd = (
        2451545.0
        + 367 * y
        - math.floor(7 * (y + math.floor((mo + 9) / 12)) / 4)
        + math.floor(275 * mo / 9)
        + d
        - 0.5
    )
    jd0 = math.floor(jd - 0.5) + 0.5
    s = jd0 - 2451545.0
    t2 = s / 36525.0
    gmst0 = 280.46061837 + 360.98564736629 * s + 0.000387933 * t2 * t2
    hours = time_s / 3600
    lst = math.fmod(gmst0 + 360 * hours / 24.03, 360)
    if lst < 0:
        lst += 360
    return lst


class TestSiderealTime(unittest.TestCase):
    """fnc_siderealTime runs from the real SQF and matches a Meeus mirror."""

    CASES = [
        ((2025, 1, 1), 0.0),
        ((2025, 1, 1), 43200.0),
        ((2025, 3, 20), 3600.0),
        ((2025, 6, 15), 7200.0),
        ((2025, 9, 1), 80100.0),
        ((2025, 12, 31), 79200.0),
        ((2026, 2, 28), 1800.0),
    ]

    def test_matches_meeus_mirror(self):
        for date, seconds in self.CASES:
            with self.subTest(date=date, seconds=seconds):
                got = run_sqf(SIDEREAL, [list(date)], globals_={"time": seconds})
                self.assertAlmostEqual(got, sidereal_lst(date, seconds), places=6)

    def test_within_zero_360(self):
        for date, seconds in self.CASES:
            got = run_sqf(SIDEREAL, [list(date)], globals_={"time": seconds})
            self.assertGreaterEqual(got, 0.0)
            self.assertLess(got, 360.0)

    def test_advances_with_ut(self):
        a = run_sqf(SIDEREAL, [[2025, 9, 1]], globals_={"time": 0.0})
        b = run_sqf(SIDEREAL, [[2025, 9, 1]], globals_={"time": 3600.0})
        delta = math.fmod(b - a, 360.0)
        self.assertAlmostEqual(delta, 360.0 / 24.03, places=4)

    def test_catalog_uses_kernel(self):
        text = (SENSOR / "fnc_getStarCatalog.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(siderealTime)", text)
        # The 9050-star loop stays inline: no per-star function call.
        self.assertNotIn(
            "call FUNC(siderealTime)", text.split("forEach _catalog")[0][-400:]
        )


def radiant_horizontal(ra, dec, lat, lst):
    """Python mirror of fnc_radiantHorizontal."""
    ha = lst - ra
    if ha > 180:
        ha -= 360
    if ha < -180:
        ha += 360
    alt = math.degrees(
        math.asin(
            math.sin(math.radians(dec)) * math.sin(math.radians(lat))
            + math.cos(math.radians(dec))
            * math.cos(math.radians(lat))
            * math.cos(math.radians(ha))
        )
    )
    az = math.degrees(
        math.atan2(
            math.sin(math.radians(ha)),
            math.cos(math.radians(ha)) * math.sin(math.radians(lat))
            - math.tan(math.radians(dec)) * math.cos(math.radians(lat)),
        )
    )
    az = math.fmod(az, 360)
    if az < 0:
        az += 360
    return [alt, az]


QUA_ROW = ["QUA", "Quadrantids", 12, 28, 1, 12, 1, 3, 283.15, 230, 49, 41, 2.1, 80]
LYR_ROW = ["LYR", "April Lyrids", 4, 14, 4, 30, 4, 22, 32.32, 271, 34, 49, 2.1, 18]


class TestRadiantHorizontal(unittest.TestCase):
    """fnc_radiantHorizontal executes from the real SQF and matches the mirror."""

    def test_pole_above_latitude(self):
        got = run_sqf(RADIANT, [0, 90, 47, 0])
        self.assertAlmostEqual(got[0], 47, places=6)

    def test_hour_angle_zero_dec_equal_lat_is_zenith(self):
        got = run_sqf(RADIANT, [100, 45, 45, 100])
        self.assertAlmostEqual(got[0], 90, places=6)

    def test_below_horizon_negative(self):
        got = run_sqf(RADIANT, [0, -90, 45, 0])
        self.assertAlmostEqual(got[0], -45, places=6)

    def test_matches_mirror(self):
        for ra, dec, lat, lst in [
            (230, 49, 45, 100),
            (48, 58, 52, 300),
            (271, 34, 30, 0),
            (338, -1, 40, 400),
        ]:
            with self.subTest(ra=ra, dec=dec, lat=lat, lst=lst):
                got = run_sqf(RADIANT, [ra, dec, lat, lst])
                want = radiant_horizontal(ra, dec, lat, lst)
                self.assertAlmostEqual(got[0], want[0], places=6)
                self.assertAlmostEqual(got[1], want[1], places=6)

    def test_azimuth_range(self):
        for lst in range(0, 360, 30):
            got = run_sqf(RADIANT, [230, 49, 45, lst])
            self.assertGreaterEqual(got[1], 0)
            self.assertLess(got[1], 360)


class TestShowerIsActive(unittest.TestCase):
    """Inclusive windows, including the Quadrantid year-end wrap."""

    def _active(self, month, day, row):
        return run_sqf(ACTIVE, [month, day, row])

    def test_qua_wraps_year_end(self):
        self.assertTrue(self._active(12, 28, QUA_ROW))
        self.assertTrue(self._active(1, 12, QUA_ROW))
        self.assertTrue(self._active(1, 3, QUA_ROW))

    def test_qua_outside(self):
        self.assertFalse(self._active(1, 13, QUA_ROW))
        self.assertFalse(self._active(12, 27, QUA_ROW))

    def test_lyr_plain_window(self):
        self.assertTrue(self._active(4, 14, LYR_ROW))
        self.assertTrue(self._active(4, 30, LYR_ROW))
        self.assertFalse(self._active(4, 13, LYR_ROW))
        self.assertFalse(self._active(5, 1, LYR_ROW))


class TestMeteorRate(unittest.TestCase):
    """N = ZHR * sin(alt) * r^(limitingMag - 6.5); UNSOURCED, test-locked."""

    def test_below_horizon_zero(self):
        self.assertEqual(run_sqf(RATE, [80, 2.1, -1, 6.5]), 0)
        self.assertEqual(run_sqf(RATE, [80, 2.1, 0, 6.5]), 0)

    def test_reference_magnitude_overhead(self):
        got = run_sqf(RATE, [80, 2.1, 90, 6.5])
        self.assertAlmostEqual(got, 80.0, places=6)

    def test_altitude_scaling(self):
        got = run_sqf(RATE, [80, 2.1, 30, 6.5])
        self.assertAlmostEqual(got, 80 * math.sin(math.radians(30)), places=6)

    def test_increases_with_altitude(self):
        r10 = run_sqf(RATE, [100, 2.2, 10, 6.5])
        r30 = run_sqf(RATE, [100, 2.2, 30, 6.5])
        r60 = run_sqf(RATE, [100, 2.2, 60, 6.5])
        self.assertLess(r10, r30)
        self.assertLess(r30, r60)

    def test_increases_with_limiting_magnitude(self):
        dim = run_sqf(RATE, [80, 2.1, 30, 5.0])
        reference = run_sqf(RATE, [80, 2.1, 30, 6.5])
        dark = run_sqf(RATE, [80, 2.1, 30, 8.0])
        self.assertLess(dim, reference)
        self.assertLess(reference, dark)

    def test_population_index_power(self):
        got = run_sqf(RATE, [100, 2.2, 90, 7.5])
        self.assertAlmostEqual(got, 100 * 2.2, places=6)


def injections(sidereal=None):
    """The four sub-kernels for fnc_meteorState, each wrapping run_sqf."""
    return {
        "__FUNC__siderealTime": sidereal
        or (lambda date: run_sqf(SIDEREAL, [date], globals_={"time": 0.0})),
        "__FUNC__showerIsActive": lambda m, d, s: run_sqf(ACTIVE, [m, d, s]),
        "__FUNC__radiantHorizontal": lambda ra, dec, lat, lst: run_sqf(
            RADIANT, [ra, dec, lat, lst]
        ),
        "__FUNC__meteorRate": lambda zhr, r, alt, lim: run_sqf(
            RATE, [zhr, r, alt, lim]
        ),
    }


class TestMeteorState(unittest.TestCase):
    """fnc_meteorState composes the four kernels (injected) from real SQF."""

    def test_active_overhead(self):
        inj = injections(sidereal=lambda date: 230.0)
        state = run_sqf(STATE, [[2025, 1, 3], 49.0, 6.5, QUA_ROW], globals_=inj)
        self.assertTrue(state[0])
        self.assertAlmostEqual(state[1], 90.0, places=4)
        self.assertGreater(state[3], 0)

    def test_inactive_out_of_window_rate_zero(self):
        state = run_sqf(
            STATE, [[2025, 9, 1], 40.0, 6.5, QUA_ROW], globals_=injections()
        )
        self.assertFalse(state[0])
        self.assertEqual(state[3], 0)

    def test_below_horizon_rate_zero(self):
        inj = injections(sidereal=lambda date: 230.0 + 180.0)
        state = run_sqf(STATE, [[2025, 1, 3], 0.0, 6.5, QUA_ROW], globals_=inj)
        self.assertLess(state[1], 0)
        self.assertEqual(state[3], 0)

    def test_rate_matches_rate_kernel(self):
        inj = injections(sidereal=lambda date: 230.0)
        state = run_sqf(STATE, [[2025, 1, 3], 49.0, 6.0, QUA_ROW], globals_=inj)
        want = run_sqf(RATE, [QUA_ROW[13], QUA_ROW[12], state[1], 6.0])
        self.assertAlmostEqual(state[3], want, places=6)


class TestMeteorRendererContract(unittest.TestCase):
    """The client worker is a light + particle emitter: no sound, no lines."""

    def setUp(self):
        self.registrar = REGISTRAR.read_text(encoding="utf-8")
        worker = WORKER.read_text(encoding="utf-8")
        # Strip comments: a comment naming a forbidden call must not trip the
        # contract, but the code must not contain one either.
        code = re.sub(r"/\*.*?\*/", "", worker, flags=re.DOTALL)
        self.code = re.sub(r"//[^\n]*", "", code)

    def test_registrar_is_client_and_idempotent(self):
        self.assertIn("hasInterface", self.registrar)
        self.assertIn("meteorPFH", self.registrar)
        self.assertIn("isNil", self.registrar)
        self.assertIn("CBA_fnc_addPerFrameHandler", self.registrar)

    def test_emitters(self):
        self.assertIn('"#lightpoint"', self.code)
        self.assertIn('"#particlesource"', self.code)
        self.assertIn("cl_basic", self.code)
        self.assertIn("setDropInterval", self.code)
        self.assertIn("setLightUseFlare", self.code)

    def test_gates(self):
        self.assertIn("dynamicMeteors", self.code)
        self.assertIn("currentSunElevation", self.code)
        self.assertIn("getSmoothedWeather", self.code)
        self.assertIn("0.8", self.code)

    def test_no_sound_explosion_or_line(self):
        for forbidden in (
            "drawLine3D",
            "say3D",
            "playSound",
            "BIS_fnc_sunriseSunsetTime",
        ):
            self.assertNotIn(forbidden, self.code)

    def test_local_objects_only(self):
        self.assertIn('"Land_Battery_F" createVehicleLocal', self.code)
        self.assertNotRegex(self.code, r"\bcreateVehicle\b(?!Local)")

    def test_uses_shared_state(self):
        self.assertIn("QEGVAR(core,currentSunElevation)", self.code)
        self.assertIn("EFUNC(core,getSmoothedWeather)", self.code)
        self.assertIn("FUNC(meteorState)", self.code)

    def test_flare_reaches_the_spawn_radius(self):
        # The starfield works because flareMaxDist (7500) > starRadius (5000).
        # The meteor spawns at 6000-9000 m, so a 2000 m flare range (the
        # reference value) would make it invisible.  Guard the fix.
        self.assertIn("METEOR_FLARE_MAX_DIST", self.code)

    def test_debug_force_hook(self):
        self.assertIn("meteorForce", self.code)

    def test_speed_converts_km_s_to_m_s(self):
        # V-infinity is km/s; setVelocity takes m/s.  The worker must convert
        # before applying the cosmetic factor (regression guard for the review
        # finding that otherwise reads as a slow dot, not a streak).
        self.assertIn("* 1000 * METEOR_SPEED_FACTOR", self.code)

    def test_no_ground_illumination(self):
        # Match the starfield design: the flare is the point, the ambient
        # stays black so the field does not light the ground.
        self.assertIn("setLightAmbient [0, 0, 0]", self.code)


class TestMeteorWiring(unittest.TestCase):
    """PREPS, setting, stringtable, postInit, runner and gate wiring."""

    def test_preps_registered(self):
        prep = PREP.read_text(encoding="utf-8")
        for entry in (
            "meteorShowers",
            "meteorRate",
            "meteorState",
            "radiantHorizontal",
            "showerIsActive",
            "siderealTime",
            "renderMeteors",
            "updateMeteors",
        ):
            self.assertIn(f"PREPS(astronomy,{entry})", prep)

    def test_setting_registered(self):
        text = SETTINGS.read_text(encoding="utf-8")
        self.assertIn(
            'AEE_SETTING_CHECKBOX(dynamicMeteors,"AEE Environmental","Display",true)',
            text,
        )

    def test_stringtable_keys(self):
        text = STRINGTABLE.read_text(encoding="utf-8")
        self.assertIn("STR_AEE_Environmental_dynamicMeteors_Name", text)
        self.assertIn("STR_AEE_Environmental_dynamicMeteors_Description", text)
        self.assertIn("<Original>Dynamic Meteors</Original>", text)
        # Sort order: dynamicMeteors before dynamicStars.
        self.assertLess(
            text.index("dynamicMeteors_Name"), text.index("dynamicStars_Description")
        )

    def test_postinit_calls_render(self):
        text = POSTINIT.read_text(encoding="utf-8")
        after_stars = text.index("[] call FUNC(renderDynamicStars);")
        self.assertGreater(text.index("[] call FUNC(renderMeteors);"), after_stars)

    def test_runner_lists_suite(self):
        self.assertIn("tools/tests/test_meteors.py", RUNNER.read_text(encoding="utf-8"))

    def test_makefile_and_ci_name_check(self):
        invocation = "python3 tools/validation/gen_meteor_showers.py --check"
        self.assertIn(invocation, MAKEFILE.read_text(encoding="utf-8"))
        self.assertIn(invocation, CI.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
