#!/usr/bin/env python3
"""Vision-driven view distance physics tests (issue #138).

Mirrors fnc_calculateViewDistance.sqf: extinction coefficients from fog/
haze/rain and Koschmieder visibility.  There is no horizon cap (RV4
renders a flat world and the eye-height horizon hides ridges and aircraft
that stand above it) and no night cap (lights stay visible at night).

Run: python3 -m unittest tools.tests.test_optics_vision
"""

import math
import re
import unittest
from pathlib import Path


def sigma_total(fog=0.0, haze=0.0, rain_mmh=0.0):
    """Extinction coefficients per km (SQF lines, spec formula).

    sigma_fog = fog * 10; sigma_haze = haze * 1.0;
    sigma_rain = 0.21 * R^0.74 (Atlas 1954), R in mm/h.
    """
    s = fog * 10.0 + haze * 1.0
    if rain_mmh > 0:
        s += 0.21 * rain_mmh**0.74
    return s


def koschmieder_vis_m(sigma):
    """Koschmieder: V = 3.912/sigma (km -> m).  300 km floor when clear."""
    if sigma > 0.001:
        return 3.912 / sigma * 1000.0
    return 300000.0


def geometric_visibility_m(eye_height_m, target_height_m, radius_km=6371.0):
    """Distance at which a target of height H sinks below the smooth-earth
    horizon: sqrt(2 R h_eye) + sqrt(2 R H)."""
    r = radius_km * 1000.0
    return math.sqrt(2 * r * eye_height_m) + math.sqrt(2 * r * target_height_m)


def view_distance_m(fog=0.0, haze=0.0, rain_mmh=0.0, cap=12000.0):
    """The full driver: min(Koschmieder, cap), floored at 150 m."""
    s = sigma_total(fog, haze, rain_mmh)
    vis = koschmieder_vis_m(s)
    return max(min(vis, cap), 150.0)


class TestExtinction(unittest.TestCase):
    def test_sigma_fog_scales_10(self):
        self.assertAlmostEqual(sigma_total(fog=0.5), 5.0)
        self.assertAlmostEqual(sigma_total(fog=1.0), 10.0)

    def test_sigma_haze_unit_scale(self):
        self.assertAlmostEqual(sigma_total(haze=0.2), 0.2)

    def test_sigma_additive(self):
        s = sigma_total(fog=0.5, haze=0.2)
        self.assertAlmostEqual(s, 5.0 + 0.2, places=4)


class TestRainExtinction(unittest.TestCase):
    def test_rain_atlas_sigma(self):
        # Atlas 1954: sigma = 0.21 * R^0.74, R in mm/h.
        self.assertAlmostEqual(sigma_total(rain_mmh=1.0), 0.21, places=4)
        self.assertAlmostEqual(sigma_total(rain_mmh=25.0), 0.21 * 25**0.74, places=3)

    def test_rain_reduces_visibility(self):
        # Heavy rain (25 mm/h): sigma_rain ~2.4 -> V ~1.6 km, far below
        # the clear horizon.
        v_clear = view_distance_m(haze=0.0)
        v_rain = view_distance_m(haze=0.0, rain_mmh=25.0)
        self.assertLess(v_rain, 2000)
        self.assertLess(v_rain, v_clear)

    def test_light_rain_small_effect(self):
        v_clear = view_distance_m(haze=0.0)
        v_drizzle = view_distance_m(haze=0.0, rain_mmh=1.0)
        # sigma 0.21 -> V 18.6 km: still beyond the 12 km cap.
        self.assertEqual(v_drizzle, v_clear)

    def test_rain_adds_to_fog(self):
        # Fog 0.5 (sigma 5, V 780 m) plus heavy rain: tighter still.
        v_fog = view_distance_m(fog=0.5)
        v_fog_rain = view_distance_m(fog=0.5, rain_mmh=25.0)
        self.assertLess(v_fog_rain, v_fog)


class TestKoschmieder(unittest.TestCase):
    def test_clear_floor(self):
        self.assertAlmostEqual(koschmieder_vis_m(0.0), 300000.0)

    def test_haze_02(self):
        # Issue vector: haze 0.2 -> 11.3 km horizon-limited; V = 19.5 km.
        v = koschmieder_vis_m(0.2)
        self.assertAlmostEqual(v, 3.912 / 0.2 * 1000, places=1)

    def test_fog_05(self):
        # Issue vector: fog 0.5 -> 780 m.
        v = koschmieder_vis_m(5.0)
        self.assertAlmostEqual(v, 3.912 / 5.0 * 1000, places=0)
        self.assertAlmostEqual(v, 782.4, places=0)

    def test_fog_08(self):
        # Issue vector: fog 0.8 -> 490 m.
        v = koschmieder_vis_m(8.0)
        self.assertAlmostEqual(v, 489.0, places=0)


class TestNoHorizonCap(unittest.TestCase):
    def test_terrain_and_aircraft_stand_above_the_eye_horizon(self):
        # A standing eye's own horizon is 4.65 km, but a 300 m ridge is
        # visible to ~66 km and an aircraft at 3,000 m to ~200 km.
        self.assertGreater(geometric_visibility_m(1.7, 300), 60000)
        self.assertGreater(geometric_visibility_m(1.7, 3000), 190000)

    def test_sqf_has_no_horizon_or_night_cap(self):
        src = (Path(__file__).resolve().parents[2] / "addons" / "vision" / "functions"
               / "vision" / "fnc_calculateViewDistance.sqf").read_text(encoding="utf-8")
        self.assertNotIn("_horizonM", src)
        self.assertNotIn("_nightM", src)
        self.assertNotIn("sunOrMoon < 0", src)


class TestDriver(unittest.TestCase):
    def test_clear_day_reaches_the_cap(self):
        self.assertEqual(view_distance_m(haze=0.0), 12000.0)

    def test_haze_02(self):
        # Koschmieder V for haze 0.2 is 19.6 km: the 12 km cap governs.
        self.assertEqual(view_distance_m(haze=0.2), 12000.0)

    def test_fog_05(self):
        self.assertAlmostEqual(view_distance_m(fog=0.5), 782.4, places=0)

    def test_fog_08(self):
        self.assertAlmostEqual(view_distance_m(fog=0.8), 489.0, places=0)

    def test_monotonic_in_fog(self):
        vs = [view_distance_m(fog=f) for f in [0.0, 0.2, 0.5, 0.8, 1.0]]
        for a, b in zip(vs, vs[1:]):
            self.assertGreaterEqual(a, b, "view distance rose with fog")

    def test_floor_150(self):
        v = view_distance_m(fog=5.0)  # sigma 50 -> 78 m -> floored
        self.assertEqual(v, 150.0)

    def test_no_acuity_hard_cap(self):
        # Johnson DRI is target resolution, not a scene view-distance cap.
        v = view_distance_m(haze=0.0)
        self.assertGreater(v, 6200.0)


class TestSensorSessionLifecycle(unittest.TestCase):
    """The sensor session must not outlive its unit (GAP-026).

    The "visionMode" player event was the only code that could tear the
    session down. A death, a respawn or a remote-control switch is not a
    vision-mode change, so the event never fired, and the per-frame handler
    plus the sensor flags and overlays stayed live into the respawn.

    These read the SOURCE. A mirror of the lifecycle would prove nothing
    about the lifecycle.
    """

    def setUp(self):
        self.post_init = Path("addons/vision/XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.teardown = Path(
            "addons/vision/functions/vision/fnc_teardownSensors.sqf"
        ).read_text(encoding="utf-8")

    def test_death_tears_down_rather_than_exiting(self):
        """The !alive guard must call the teardown, not silently exit.

        The old form was a bare `if (... || !alive _player) exitWith {};`
        which skipped the tick and left the session running forever.
        """
        guard = re.search(
            r'if \(isNil "_player"(.*?)\) exitWith \{(.*?)\n            \};',
            self.post_init,
            re.S,
        )
        self.assertIsNotNone(guard, "the PFH unit guard is missing")
        condition, handler = guard.group(1), guard.group(2)
        self.assertIn("!alive _player", condition)
        self.assertIn(
            "teardownSensors",
            handler,
            "death exits without tearing down: the session outlives the unit",
        )

    def test_session_is_keyed_to_a_unit(self):
        """A unit change must close the session."""
        self.assertIn("sensorUnit", self.post_init)
        self.assertIn("_player isNotEqualTo GVAR(sensorUnit)", self.post_init)

    def test_teardown_is_idempotent(self):
        """A second call must find no handler and return."""
        self.assertIn("if (isNil QGVAR(sensorPFH)) exitWith {}", self.teardown)

    def test_teardown_restores_exposure_before_the_idempotency_exit(self):
        """The setAperture reset must precede the isNil early exit.

        The NVG and thermal modules set a FIXED setAperture 15, and this is
        the only place that clears it.  Gated behind the idempotency exit,
        the camera keeps the night exposure whenever the sensor session is
        already gone, which is exactly when the reset matters.  The guard
        must still be present for the rest of the teardown, so this asserts
        the order rather than the absence.
        """
        reset = re.search(r"^\s*setAperture\s+-1\s*;", self.teardown, re.M)
        self.assertIsNotNone(reset, "the teardown does not restore the exposure")

        guard = re.search(
            r"if\s*\(isNil QGVAR\(sensorPFH\)\)\s*exitWith", self.teardown
        )
        self.assertIsNotNone(guard, "the idempotency guard is missing")

        self.assertLess(
            reset.start(),
            guard.start(),
            "setAperture -1 sits after the exit that skips it",
        )

    def test_teardown_clears_the_unit_key(self):
        """The unit key must not survive the session, or the next session
        compares against a stale unit and tears itself down at once."""
        self.assertIn("GVAR(sensorUnit) = nil", self.teardown)

    def test_both_paths_use_one_teardown(self):
        """The event and the handler must share the sequence, so the two
        cannot drift apart."""
        self.assertIn("call FUNC(teardownSensors)", self.post_init)
        # No inline teardown left in the event.
        self.assertNotIn(
            "[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler", self.post_init
        )
        self.assertIn(
            "[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler", self.teardown
        )


NVG_MODEL = Path(__file__).resolve().parents[2] / (
    "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf"
)


class TestNvgBrightSourceScanCache(unittest.TestCase):
    """The NVG bright-source scan is cached, not run every tick (perf).

    The O(n) nearestObjects scan plus the per-object config traversal is the
    dominant per-tick cost of the tube model.  It must be guarded by a
    time/distance cache so it does not run at the full PFH rate; the view
    angle and occlusion test stays per tick.
    """

    @classmethod
    def setUpClass(cls):
        cls.code = NVG_MODEL.read_text(encoding="utf-8")

    def test_scan_result_is_cached(self):
        self.assertIn("QGVAR(nvgBrightSources)", self.code)
        self.assertIn("QGVAR(nvgBrightScanTime)", self.code)
        self.assertIn("QGVAR(nvgBrightScanPos)", self.code)

    def test_scan_is_guarded_by_time_and_distance(self):
        m = re.search(
            r"if\s*\(\(diag_tickTime - _scanTime > ([0-9.]+)\)"
            r"\s*\|\|\s*\(\(_eye distance _scanPos\) > ([0-9.]+)\)\)",
            self.code,
        )
        self.assertIsNotNone(m, "no scan refresh guard found")
        self.assertLessEqual(float(m.group(1)), 1.0, "refresh longer than 1 s")
        self.assertLessEqual(float(m.group(2)), 50.0, "movement guard too loose")

    def test_nearest_objects_runs_once_and_behind_the_guard(self):
        self.assertEqual(self.code.count("nearestObjects"), 1)
        guard = self.code.index("_scanTime")
        scan = self.code.index("nearestObjects")
        loop = self.code.index("} forEach _brightSources;")
        self.assertLess(guard, scan, "the guard must precede the scan")
        self.assertLess(scan, loop, "the scan must feed the cached loop")

    def test_loop_iterates_the_cached_list(self):
        self.assertIn("_x params [\"_src\", \"_spectralWeight\"]", self.code)


if __name__ == "__main__":
    unittest.main()
