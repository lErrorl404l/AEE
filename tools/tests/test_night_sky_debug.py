#!/usr/bin/env python3
"""Night-sky debug surface: pure kernels, log line, force hooks, renderers.

The operator cannot see meteors, the aurora or the Milky Way, so this change
adds one force hook per feature, one consolidated "sky state" log line, and
the two missing visuals.  This suite locks:

  - the pure galactic kernels (fnc_galacticToEquatorial,
    fnc_galacticToHorizontal) and the gate kernel (fnc_skyGateReason),
    executed from their real SQF through tools/tests/sqf_lite.py;
  - the consolidated log line and its environment-tick wiring;
  - the five force hooks and their owning files;
  - the aurora, Milky Way and faint-star renderers;
  - the settings, stringtable, docs and suite wiring.

Later tasks append their classes to this file.
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SENSOR = ROOT / "addons" / "environmental" / "functions" / "astronomy"

GALACTIC_EQUATORIAL = SENSOR / "fnc_galacticToEquatorial.sqf"
GALACTIC_HORIZONTAL = SENSOR / "fnc_galacticToHorizontal.sqf"
SKY_GATE_REASON = SENSOR / "fnc_skyGateReason.sqf"


def galactic_to_equatorial(l_deg, b_deg):
    """Python mirror of fnc_galacticToEquatorial (IAU 1958 galactic frame)."""
    ra_ngp = 192.85948
    de_ngp = 27.12825
    l_ncp = 122.93192
    dl = math.radians(l_ncp - l_deg)
    b = math.radians(b_deg)
    de = math.radians(de_ngp)
    sin_dec = math.sin(de) * math.sin(b) + math.cos(de) * math.cos(b) * math.cos(dl)
    y = math.cos(b) * math.sin(dl)
    x = math.cos(de) * math.sin(b) - math.sin(de) * math.cos(b) * math.cos(dl)
    ra = ra_ngp + math.degrees(math.atan2(y, x))
    ra = math.fmod(ra, 360)
    if ra < 0:
        ra += 360
    dec = math.degrees(math.asin(sin_dec))
    return [ra, dec]


class TestGalacticToEquatorial(unittest.TestCase):
    """Sgr A* anchors and the pole cases, run from the real SQF."""

    def test_galactic_centre_anchor(self):
        got = run_sqf(GALACTIC_EQUATORIAL, [0, 0])
        self.assertAlmostEqual(got[0], 266.405, delta=0.05)
        self.assertAlmostEqual(got[1], -28.936, delta=0.05)

    def test_north_galactic_pole_anchor(self):
        got = run_sqf(GALACTIC_EQUATORIAL, [0, 90])
        self.assertAlmostEqual(got[0], 192.859, delta=0.02)
        self.assertAlmostEqual(got[1], 27.128, delta=0.02)

    def test_north_celestial_pole(self):
        # l_NCP, b_NGP is the north celestial pole by construction.
        got = run_sqf(GALACTIC_EQUATORIAL, [122.93192, 27.12825])
        self.assertAlmostEqual(got[1], 90, delta=0.02)

    def test_ra_always_in_range(self):
        for l_deg, b_deg in [(0, 0), (90, 30), (250, -45), (359, 89), (180, -80)]:
            with self.subTest(l=l_deg, b=b_deg):
                got = run_sqf(GALACTIC_EQUATORIAL, [l_deg, b_deg])
                self.assertGreaterEqual(got[0], 0)
                self.assertLess(got[0], 360)

    def test_matches_mirror(self):
        for l_deg, b_deg in [(0, 0), (90, 30), (250, -45), (10, 75)]:
            with self.subTest(l=l_deg, b=b_deg):
                got = run_sqf(GALACTIC_EQUATORIAL, [l_deg, b_deg])
                want = galactic_to_equatorial(l_deg, b_deg)
                self.assertAlmostEqual(got[0], want[0], places=6)
                self.assertAlmostEqual(got[1], want[1], places=6)


def galactic_to_horizontal(l_deg, b_deg, lst_deg, lat_deg):
    """Python mirror of fnc_galacticToHorizontal."""
    ra, dec = galactic_to_equatorial(l_deg, b_deg)
    ha = lst_deg - ra
    if ha > 180:
        ha -= 360
    if ha < -180:
        ha += 360
    alt = math.degrees(
        math.asin(
            math.sin(math.radians(dec)) * math.sin(math.radians(lat_deg))
            + math.cos(math.radians(dec))
            * math.cos(math.radians(lat_deg))
            * math.cos(math.radians(ha))
        )
    )
    az = (
        math.degrees(
            math.atan2(
                math.sin(math.radians(ha)),
                math.cos(math.radians(ha)) * math.sin(math.radians(lat_deg))
                - math.tan(math.radians(dec)) * math.cos(math.radians(lat_deg)),
            )
        )
        + 180.0
    )
    az = math.fmod(az, 360)
    if az < 0:
        az += 360
    return [alt, az]


def galactic_horizontal_injections():
    """FUNC(galacticToEquatorial) injected from its real SQF."""
    return {
        "__FUNC__galacticToEquatorial": lambda l, b: run_sqf(
            GALACTIC_EQUATORIAL, [l, b]
        ),
    }


class TestGalacticToHorizontal(unittest.TestCase):
    """fnc_galacticToHorizontal composes the equatorial kernel from real SQF."""

    def test_zenith_case(self):
        # LST equals the object's RA and latitude equals its Dec: zenith.
        got = run_sqf(
            GALACTIC_HORIZONTAL,
            [0, 0, 266.405, -28.936],
            globals_=galactic_horizontal_injections(),
        )
        self.assertAlmostEqual(got[0], 90, delta=0.05)

    def test_ranges(self):
        got = run_sqf(
            GALACTIC_HORIZONTAL,
            [0, 0, 0, 45],
            globals_=galactic_horizontal_injections(),
        )
        self.assertGreaterEqual(got[0], -90)
        self.assertLessEqual(got[0], 90)
        self.assertGreaterEqual(got[1], 0)
        self.assertLess(got[1], 360)

    def test_matches_mirror(self):
        for l_deg, b_deg in [(0, 0), (90, 30), (250, -45)]:
            with self.subTest(l=l_deg, b=b_deg):
                got = run_sqf(
                    GALACTIC_HORIZONTAL,
                    [l_deg, b_deg, 120.0, 45.0],
                    globals_=galactic_horizontal_injections(),
                )
                want = galactic_to_horizontal(l_deg, b_deg, 120.0, 45.0)
                self.assertAlmostEqual(got[0], want[0], places=6)
                self.assertAlmostEqual(got[1], want[1], places=6)


class TestSkyGateReason(unittest.TestCase):
    """Every reason code is produced from the real SQF."""

    def _gate(self, feature, **kw):
        args = [
            feature,
            kw.get("settingOn", True),
            kw.get("forceOn", False),
            kw.get("sunElev", -30),
            kw.get("overcast", 0.0),
            kw.get("kpIndex", 7),
            kw.get("daytime", 22),
            kw.get("latDeg", 65),
            kw.get("ovalLimit", 55),
            kw.get("nelm", 6.5),
            kw.get("meteorActive", True),
        ]
        return run_sqf(SKY_GATE_REASON, args)

    def test_stars_night(self):
        self.assertEqual(self._gate("stars", sunElev=0), [False, "NIGHT"])

    def test_stars_overcast(self):
        self.assertEqual(self._gate("stars", overcast=0.8), [False, "OVERCAST"])

    def test_stars_on(self):
        self.assertEqual(self._gate("stars"), [True, "ON"])

    def test_meteors_night(self):
        self.assertEqual(self._gate("meteors", sunElev=10), [False, "NIGHT"])

    def test_meteors_overcast(self):
        self.assertEqual(self._gate("meteors", overcast=0.9), [False, "OVERCAST"])

    def test_meteors_no_shower(self):
        self.assertEqual(
            self._gate("meteors", meteorActive=False), [False, "NO_SHOWER"]
        )

    def test_meteors_on(self):
        self.assertEqual(self._gate("meteors"), [True, "ON"])

    def test_aurora_night(self):
        self.assertEqual(self._gate("aurora", sunElev=0), [False, "NIGHT"])

    def test_aurora_overcast(self):
        self.assertEqual(self._gate("aurora", overcast=0.3), [False, "OVERCAST"])

    def test_aurora_kp(self):
        self.assertEqual(self._gate("aurora", kpIndex=4), [False, "KP"])

    def test_aurora_daytime(self):
        self.assertEqual(self._gate("aurora", daytime=12), [False, "DAYTIME"])

    def test_aurora_latitude(self):
        self.assertEqual(
            self._gate("aurora", latDeg=55, ovalLimit=55), [False, "LATITUDE"]
        )

    def test_aurora_on(self):
        self.assertEqual(self._gate("aurora"), [True, "ON"])

    def test_milkyway_night(self):
        self.assertEqual(self._gate("milkyway", sunElev=0), [False, "NIGHT"])

    def test_milkyway_overcast(self):
        self.assertEqual(self._gate("milkyway", overcast=0.8), [False, "OVERCAST"])

    def test_milkyway_nelm(self):
        self.assertEqual(self._gate("milkyway", nelm=4.9), [False, "NELM"])

    def test_milkyway_on(self):
        self.assertEqual(self._gate("milkyway"), [True, "ON"])

    def test_forced_beats_physical_gates(self):
        for feature in ("stars", "meteors", "aurora", "milkyway"):
            with self.subTest(feature=feature):
                self.assertEqual(
                    self._gate(feature, forceOn=True, sunElev=10, overcast=1.0),
                    [True, "FORCED"],
                )

    def test_setting_beats_force(self):
        self.assertEqual(
            self._gate("stars", settingOn=False, forceOn=True), [False, "SETTING"]
        )


if __name__ == "__main__":
    unittest.main()
