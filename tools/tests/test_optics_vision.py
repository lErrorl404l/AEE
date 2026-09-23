#!/usr/bin/env python3
"""Vision-driven view distance physics tests (issue #138).

Mirrors fnc_calculateViewDistance.sqf: extinction coefficients from fog/
haze/rain, Koschmieder visibility, horizon from eye height, Johnson
acuity cap, night sensitivity.  The test vectors come from the issue
spec (Blackwell 1946, Johnson 1958, Koschmieder).

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


def horizon_m(eye_height_rel_m):
    """Horizon at eye height: sqrt(2*R*e), R = 6371 km (m)."""
    eh = max(eye_height_rel_m, 1.0)
    return 1000.0 * math.sqrt(2.0 * 6371.0 * (eh / 1000.0))


ACUITY_M = 1e6  # Johnson DRI is target resolution, not a scene cap (see SQF comment)


def night_limit_m(nelm, sun_down):
    """Night sensitivity: 100 + (NELM-2)*300 m below NELM 6."""
    if sun_down and nelm < 6:
        return 100.0 + (nelm - 2.0) * 300.0
    return 1e6


def view_distance_m(
    fog=0.0,
    haze=0.0,
    rain_mmh=0.0,
    nelm=6.5,
    sun_down=0,
    eye_height=1.7,
    cap=12000.0,
):
    """The full driver: min(horizon, Koschmieder, night, cap)."""
    s = sigma_total(fog, haze, rain_mmh)
    vis = koschmieder_vis_m(s)
    hor = horizon_m(eye_height)
    night = night_limit_m(nelm, sun_down)
    return max(min(hor, vis, ACUITY_M, night, cap), 150.0)


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
        v_clear = view_distance_m(haze=0.0, sun_down=0)
        v_rain = view_distance_m(haze=0.0, rain_mmh=25.0, sun_down=0)
        self.assertLess(v_rain, 2000)
        self.assertLess(v_rain, v_clear)

    def test_light_rain_small_effect(self):
        v_clear = view_distance_m(haze=0.0, sun_down=0)
        v_drizzle = view_distance_m(haze=0.0, rain_mmh=1.0, sun_down=0)
        # sigma 0.21 -> V 18.6 km: still above the horizon.
        self.assertEqual(v_drizzle, v_clear)

    def test_rain_adds_to_fog(self):
        # Fog 0.5 (sigma 5, V 780 m) plus heavy rain: tighter still.
        v_fog = view_distance_m(fog=0.5, sun_down=0)
        v_fog_rain = view_distance_m(fog=0.5, rain_mmh=25.0, sun_down=0)
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


class TestHorizon(unittest.TestCase):
    def test_standing_eye_height(self):
        # 1.7 m -> ~4.65 km.
        h = horizon_m(1.7)
        self.assertAlmostEqual(h, 4654.0, delta=50)

    def test_vehicle_eye_height(self):
        # 3 m -> ~6.2 km.
        h = horizon_m(3.0)
        self.assertAlmostEqual(h, 6182.0, delta=50)


class TestNightLimit(unittest.TestCase):
    def test_day_no_limit(self):
        self.assertEqual(night_limit_m(5.0, 0), 1e6)

    def test_night_nelm4(self):
        # Issue vector: night NELM 4 -> 700 m.
        self.assertAlmostEqual(night_limit_m(4.0, 1), 700.0)

    def test_night_nelm65_no_penalty(self):
        # Dark sky: no night cap.
        self.assertEqual(night_limit_m(6.5, 1), 1e6)


class TestDriver(unittest.TestCase):
    def test_clear_day(self):
        # Clear, day: horizon-limited (~4.7 km).
        v = view_distance_m(haze=0.0, sun_down=0)
        self.assertAlmostEqual(v, horizon_m(1.7), delta=100)

    def test_haze_02(self):
        # Issue vector: clear haze 0.2 -> 11.3 km (the horizon at 1.7 m).
        # Koschmieder V for haze 0.2 is 19.5 km, so the horizon dominates.
        v = view_distance_m(haze=0.2, sun_down=0)
        self.assertAlmostEqual(v, horizon_m(1.7), delta=100)

    def test_fog_05(self):
        v = view_distance_m(fog=0.5, sun_down=0)
        self.assertAlmostEqual(v, 782.4, places=0)

    def test_fog_08(self):
        v = view_distance_m(fog=0.8, sun_down=0)
        self.assertAlmostEqual(v, 489.0, places=0)

    def test_night_nelm4(self):
        # Night NELM 4 with light haze: night cap 700 m dominates.
        v = view_distance_m(haze=0.1, nelm=4.0, sun_down=1)
        self.assertAlmostEqual(v, 700.0, places=0)

    def test_monotonic_in_fog(self):
        vs = [view_distance_m(fog=f, sun_down=0) for f in [0.0, 0.2, 0.5, 0.8, 1.0]]
        for a, b in zip(vs, vs[1:]):
            self.assertGreaterEqual(a, b, "view distance rose with fog")

    def test_floor_150(self):
        v = view_distance_m(fog=5.0, sun_down=0)  # sigma 50 -> 78 m -> floored
        self.assertEqual(v, 150.0)

    def test_no_acuity_hard_cap(self):
        # Johnson DRI is target resolution, not a scene view-distance cap:
        # the horizon limits a high vantage, not 6.2 km (issue spec: haze
        # 0.2 -> 11.3 km).
        v = view_distance_m(haze=0.0, sun_down=0, eye_height=100.0)
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
        self.post_init = (
            Path("addons/optics/XEH_postInit.sqf").read_text(encoding="utf-8")
        )
        self.teardown = (
            Path("addons/optics/functions/vision/fnc_teardownSensors.sqf").read_text(
                encoding="utf-8"
            )
        )

    def test_death_tears_down_rather_than_exiting(self):
        """The !alive guard must call the teardown, not silently exit.

        The old form was a bare `if (... || !alive _player) exitWith {};`
        which skipped the tick and left the session running forever.
        """
        guard = re.search(
            r'if \(isNil "_player"(.*?)\) exitWith \{(.*?)\n            \};', self.post_init, re.S
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

    def test_teardown_clears_the_unit_key(self):
        """The unit key must not survive the session, or the next session
        compares against a stale unit and tears itself down at once."""
        self.assertIn("GVAR(sensorUnit) = nil", self.teardown)

    def test_both_paths_use_one_teardown(self):
        """The event and the handler must share the sequence, so the two
        cannot drift apart."""
        self.assertIn("call FUNC(teardownSensors)", self.post_init)
        # No inline teardown left in the event.
        self.assertNotIn('[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler', self.post_init)
        self.assertIn("[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler", self.teardown)


if __name__ == "__main__":
    unittest.main()
