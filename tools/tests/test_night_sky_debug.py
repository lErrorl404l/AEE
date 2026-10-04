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


class TestSkyStateLogContract(unittest.TestCase):
    """The consolidated log line and its environment-tick wiring."""

    def setUp(self):
        self.logger = (SENSOR / "fnc_logSkyState.sqf").read_text(encoding="utf-8")
        self.core = (
            ROOT / "addons" / "core" / "functions" / "fnc_updateEnvironment.sqf"
        ).read_text(encoding="utf-8")

    def test_logger_shape(self):
        self.assertIn('"sky state | sun=', self.logger)
        self.assertIn("AEE_LOG_INFO", self.logger)
        self.assertIn("AEE_LOG_DEBUG", self.logger)
        self.assertIn("skyLogStarted", self.logger)

    def test_calls_gate_kernel_for_all_features(self):
        self.assertEqual(self.logger.count("call FUNC(skyGateReason)"), 4)
        for feature in ('"stars"', '"meteors"', '"aurora"', '"milkyway"'):
            self.assertIn(feature, self.logger)

    @staticmethod
    def _balanced(text, open_idx):
        depth = 0
        in_str = False
        i = open_idx
        while i < len(text):
            c = text[i]
            if in_str:
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c in "[({":
                depth += 1
            elif c in "])}":
                depth -= 1
                if depth == 0:
                    return text[open_idx : i + 1]
            i += 1
        raise AssertionError("unbalanced format array")

    @staticmethod
    def _top_level_commas(block):
        depth = 0
        in_str = False
        count = 0
        for c in block[1:-1]:
            if in_str:
                if c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c in "[({":
                depth += 1
            elif c in "])}":
                depth -= 1
            elif c == "," and depth == 0:
                count += 1
        return count

    def test_format_specifiers_match_arguments(self):
        start = self.logger.index('"sky state | sun=')
        fmt_end = self.logger.index('"', start + 1)
        fmt = self.logger[start : fmt_end + 1]
        specifiers = sorted(int(n) for n in re.findall(r"%(\d+)", fmt))
        self.assertEqual(specifiers, list(range(1, len(specifiers) + 1)))
        bracket = self.logger.index("[", self.logger.rindex("format", 0, start))
        block = self._balanced(self.logger, bracket)
        self.assertEqual(self._top_level_commas(block), len(specifiers))

    def test_core_wires_logger_after_catalog(self):
        self.assertIn("EFUNC(environmental,logSkyState)", self.core)
        self.assertLess(
            self.core.index("EFUNC(environmental,getStarCatalog)"),
            self.core.index("EFUNC(environmental,logSkyState)"),
        )

    def test_old_windowed_logs_removed(self):
        meteors = (SENSOR / "fnc_updateMeteors.sqf").read_text(encoding="utf-8")
        stars = (SENSOR / "fnc_starLightsSync.sqf").read_text(encoding="utf-8")
        self.assertNotIn("meteorLogAt", meteors)
        self.assertNotIn("starLogAt", stars)


class TestForceHooks(unittest.TestCase):
    """The debug hooks are documented in their owning files."""

    def test_stars_force_owned_by_star_sync(self):
        text = (SENSOR / "fnc_starLightsSync.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_environmental_starsForce", text)
        self.assertIn("effectiveNelm", text)
        self.assertIn("starEmitterCount", text)

    def test_sky_and_meteor_force_owned_by_meteor_worker(self):
        text = (SENSOR / "fnc_updateMeteors.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_environmental_skyForce", text)
        self.assertIn("aee_environmental_meteorForce", text)

    def test_aurora_force_owned_by_aurora_worker(self):
        text = (SENSOR / "fnc_updateAurora.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_environmental_auroraForce", text)

    def test_milkyway_force_owned_by_milkyway_worker(self):
        text = (SENSOR / "fnc_updateMilkyWay.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_environmental_milkyWayForce", text)

    def test_dead_hook_name_absent(self):
        # Build the banned name from parts: the literal must not appear here, or
        # the repository-wide grep that task 13 runs would match this test file.
        dead = "aee_optics_" + "meteorForce"
        hits = []
        for path in (ROOT / "addons").rglob("*.sqf"):
            if dead in path.read_text(encoding="utf-8"):
                hits.append(str(path))
        for path in (ROOT / "tools").rglob("*.py"):
            if dead in path.read_text(encoding="utf-8"):
                hits.append(str(path))
        self.assertEqual(hits, [])


class TestAuroraRenderer(unittest.TestCase):
    """The aurora worker is a local particle curtain, never a line or a light."""

    def setUp(self):
        worker = (SENSOR / "fnc_updateAurora.sqf").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/", "", worker, flags=re.DOTALL)
        self.code = re.sub(r"//[^\n]*", "", code)
        self.registrar = (SENSOR / "fnc_renderAurora.sqf").read_text(encoding="utf-8")

    def test_worker_emitter_shape(self):
        for token in (
            '"#particlesource"',
            "setParticleParams",
            "setParticleRandom",
            "setDropInterval",
            "cl_basic",
            "QGVAR(auroraIntensity)",
            "currentSunElevation",
        ):
            self.assertIn(token, self.code)

    def test_worker_no_line_or_global_object(self):
        self.assertNotIn("drawLine3D", self.code)
        self.assertNotRegex(self.code, r"\bcreateVehicle\b(?!Local)")

    def test_registrar_client_and_idempotent(self):
        self.assertIn("hasInterface", self.registrar)
        self.assertIn("auroraPFH", self.registrar)
        self.assertIn("isNil", self.registrar)
        self.assertIn("CBA_fnc_addPerFrameHandler", self.registrar)

    def test_wired(self):
        prep = (ROOT / "addons" / "environmental" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(astronomy,renderAurora)", prep)
        self.assertIn("PREPS(astronomy,updateAurora)", prep)
        post = (ROOT / "addons" / "environmental" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("[] call FUNC(renderAurora);", post)


class TestAuroraWiring(unittest.TestCase):
    """The aurora display setting and its stringtable keys."""

    def test_setting_and_strings(self):
        settings = (
            ROOT / "addons" / "environmental" / "initSettings.inc.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'AEE_SETTING_CHECKBOX(dynamicAurora,"AEE Environmental","Display",true)',
            settings,
        )
        st = (ROOT / "addons" / "environmental" / "stringtable.xml").read_text(
            encoding="utf-8"
        )
        self.assertIn("STR_AEE_Environmental_dynamicAurora_Name", st)
        self.assertIn("STR_AEE_Environmental_dynamicAurora_Description", st)


class TestMilkyWayRenderer(unittest.TestCase):
    """The Milky Way band follows the galactic plane as a Draw3D band."""

    def setUp(self):
        self.sampler = (SENSOR / "fnc_updateMilkyWay.sqf").read_text(encoding="utf-8")
        self.draw = (SENSOR / "fnc_drawMilkyWay.sqf").read_text(encoding="utf-8")
        self.registrar = (SENSOR / "fnc_renderMilkyWay.sqf").read_text(encoding="utf-8")

    def test_sampler_uses_kernels_and_setting(self):
        self.assertIn("FUNC(galacticToHorizontal)", self.sampler)
        self.assertIn("FUNC(siderealTime)", self.sampler)
        self.assertIn("dynamicMilkyWay", self.sampler)
        self.assertIn("milkyWayForce", self.sampler)

    def test_draw_uses_drawline3d_only(self):
        self.assertIn("drawLine3D", self.draw)
        self.assertNotIn("createVehicle", self.draw)
        self.assertNotIn('"#lightpoint"', self.draw)

    def test_registrar_client_and_draw3d(self):
        self.assertIn("hasInterface", self.registrar)
        self.assertIn("milkyWayPFH", self.registrar)
        self.assertIn("Draw3D", self.registrar)

    def test_wired(self):
        prep = (ROOT / "addons" / "environmental" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        for entry in ("renderMilkyWay", "updateMilkyWay", "drawMilkyWay"):
            self.assertIn(f"PREPS(astronomy,{entry})", prep)
        post = (ROOT / "addons" / "environmental" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("[] call FUNC(renderMilkyWay);", post)


class TestFaintStarBulk(unittest.TestCase):
    """The faint bulk is drawn with lines, not lights or icons."""

    def setUp(self):
        self.code = (SENSOR / "fnc_drawFaintStars.sqf").read_text(encoding="utf-8")
        self.reg = (SENSOR / "fnc_renderDynamicStars.sqf").read_text(encoding="utf-8")

    def test_shape(self):
        for token in (
            "FAINT_STAR_MAX",
            "FUNC(starDirection)",
            "FUNC(starMagnitude)",
            "drawLine3D",
            "STAR_LIGHT_MAX_MAG",
        ):
            self.assertIn(token, self.code)
        self.assertNotIn("drawIcon3D", self.code)
        self.assertNotIn("createVehicle", self.code)

    def test_registrar_registers_draw3d(self):
        self.assertIn("Draw3D", self.reg)
        self.assertIn("drawFaintStars", self.reg)

    def test_wired(self):
        prep = (ROOT / "addons" / "environmental" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(astronomy,drawFaintStars)", prep)


class TestMilkyWayWiring(unittest.TestCase):
    """The Milky Way display setting and its stringtable keys."""

    def test_setting_strings_and_hook(self):
        settings = (
            ROOT / "addons" / "environmental" / "initSettings.inc.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'AEE_SETTING_CHECKBOX(dynamicMilkyWay,"AEE Environmental","Display",true)',
            settings,
        )
        st = (ROOT / "addons" / "environmental" / "stringtable.xml").read_text(
            encoding="utf-8"
        )
        self.assertIn("STR_AEE_Environmental_dynamicMilkyWay_Name", st)
        self.assertIn("STR_AEE_Environmental_dynamicMilkyWay_Description", st)
        sampler = (SENSOR / "fnc_updateMilkyWay.sqf").read_text(encoding="utf-8")
        self.assertIn("milkyWayForce", sampler)


if __name__ == "__main__":
    unittest.main()
