#!/usr/bin/env python3
"""Weather front kernel tests (issue #15).

Executes the real SQF kernels through tools/tests/sqf_lite.py, so a failure
is a source failure, not a mirror drift.  The source-contract methods read
the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_weather_front -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ATMOS = ROOT / "addons" / "atmos" / "functions"
CORE = ROOT / "addons" / "core" / "functions"

FRONT = ATMOS / "physics" / "fnc_calculateWeatherFront.sqf"
DISTANCE = ATMOS / "physics" / "fnc_calculateFrontDistance.sqf"
PHASE = ATMOS / "physics" / "fnc_calculateFrontPhase.sqf"
WIND = ATMOS / "physics" / "fnc_calculateFrontWind.sqf"
CONSUMER = ATMOS / "state" / "fnc_updateWeatherFront.sqf"
TICK = CORE / "fnc_updateEnvironment.sqf"
CLOUD = ATMOS / "physics" / "fnc_calculateCloudDevelopment.sqf"
UPDATE_WIND = ATMOS / "state" / "fnc_updateWind.sqf"
SETTINGS = ROOT / "addons" / "atmos" / "initSettings.inc.sqf"


def front(mission_time, seed):
    return run_sqf(FRONT, [mission_time, seed])


def distance(observer, anchor, bearing, front_dist):
    return run_sqf(DISTANCE, [observer, anchor, bearing, front_dist])


def phase(dist_km, half_width):
    return run_sqf(PHASE, [dist_km, half_width])


def rotate(wind_vec, veer):
    return run_sqf(WIND, [wind_vec, veer])


class TestFrontStateMachine(unittest.TestCase):
    """The Bergen life cycle as a pure function of mission time and seed."""

    CYCLE = 604800

    def test_stationary_at_the_cycle_start(self):
        # phase 0 -> the first stage, a stationary front below 5 km/h.
        state = front(0, 0.0)
        self.assertEqual(state[0], "stationary")
        self.assertLess(state[1], 5)

    def test_mature_stage_is_a_cold_front(self):
        # phase 0.40 sits in the mature stage (0.30-0.55).
        state = front(0.40 * self.CYCLE, 0.0)
        self.assertEqual(state[0], "cold")
        # cold front speed 30-60 km/h, zone 50-100 km, veer 40-90 deg.
        self.assertGreaterEqual(state[1], 30)
        self.assertLessEqual(state[1], 60)
        self.assertGreaterEqual(state[4], 40)
        self.assertLessEqual(state[4], 90)

    def test_warm_front_moves_about_half_as_fast_as_cold(self):
        warm = front(0.20 * self.CYCLE, 0.0)
        cold = front(0.40 * self.CYCLE, 0.0)
        self.assertEqual(warm[0], "warm")
        self.assertEqual(cold[0], "cold")
        # The issue: warm fronts move about half as fast as cold fronts.
        ratio = warm[1] / cold[1]
        self.assertGreater(ratio, 0.4)
        self.assertLess(ratio, 0.7)

    def test_life_cycle_order(self):
        seen = []
        for p in (0.0, 0.2, 0.4, 0.7, 0.9):
            t = p * self.CYCLE
            seen.append(front(t, 0.0)[0])
        self.assertEqual(seen, ["stationary", "warm", "cold", "occluded", "stationary"])

    def test_temperature_contrast_in_range(self):
        # The issue: contrast 5-15 C.
        for p in (0.2, 0.4, 0.7):
            state = front(p * self.CYCLE, 0.0)
            self.assertGreaterEqual(state[2], 5)
            self.assertLessEqual(state[2], 15)

    def test_warm_front_warm_side_is_behind(self):
        # A warm front has the warm air behind it (warmSide = -1); a cold
        # front has the warm air ahead (warmSide = +1).
        self.assertEqual(front(0.20 * self.CYCLE, 0.0)[8], -1)
        self.assertEqual(front(0.40 * self.CYCLE, 0.0)[8], 1)

    def test_deterministic(self):
        # Same mission time + seed -> same front (the issue's determinism
        # requirement; no publicVariable).
        self.assertEqual(front(123456, 0.7), front(123456, 0.7))

    def test_seed_offsets_the_cycle(self):
        # Two seeds must not share a front at the same instant.
        self.assertNotEqual(front(0, 0.0)[9], front(0, 0.9)[9])

    def test_front_advances_with_time(self):
        # Within a stage the front position advances along the bearing.
        a = front(0.31 * self.CYCLE, 0.0)[10]
        b = front(0.40 * self.CYCLE, 0.0)[10]
        self.assertGreater(b, a)


class TestFrontDistance(unittest.TestCase):
    """Signed distance to the front line."""

    def test_on_the_line_is_zero(self):
        self.assertAlmostEqual(distance([0, 0], [0, 0], 90, 0), 0.0)

    def test_metres_to_kilometres(self):
        # 1000 m east of the anchor, front moving east (bearing 90): the
        # observer is 1 km ahead of the line.
        self.assertAlmostEqual(distance([1000, 0], [0, 0], 90, 0), 1.0)

    def test_behind_the_line_is_negative(self):
        # The front has advanced 300 km east; the observer is 300 km behind.
        self.assertAlmostEqual(distance([0, 0], [0, 0], 90, 300), -300.0)

    def test_bearing_rotates_the_normal(self):
        # Bearing 0 (north): an observer 1000 m north is 1 km ahead.
        self.assertAlmostEqual(distance([0, 1000], [0, 0], 0, 0), 1.0)


class TestFrontPhase(unittest.TestCase):
    """The phase factor -1..+1."""

    def test_on_the_line(self):
        self.assertAlmostEqual(phase(0, 50), 0.0)

    def test_half_way(self):
        self.assertAlmostEqual(phase(25, 50), 0.5)

    def test_clamped_ahead(self):
        self.assertAlmostEqual(phase(1000, 50), 1.0)

    def test_clamped_behind(self):
        self.assertAlmostEqual(phase(-1000, 50), -1.0)

    def test_zero_width_has_no_zone(self):
        self.assertAlmostEqual(phase(10, 0), 0.0)


class TestFrontWind(unittest.TestCase):
    """The clockwise veer at a cold front (FAA AC 00-6B)."""

    def test_zero_veer_keeps_the_vector(self):
        v = rotate([-5.0, 5.0], 0)
        self.assertAlmostEqual(v[0], -5.0, places=6)
        self.assertAlmostEqual(v[1], 5.0, places=6)

    def test_veer_is_clockwise_from_ssw_to_wnw(self):
        # A cold front veers the wind from SSW (from 200 deg) to WNW (from
        # 290 deg): a 90 deg clockwise veer.  Build the SSW vector.
        mag = 5.0
        toward = math.radians(200 - 180)  # wind blows toward 20 deg
        base = [mag * math.sin(toward), mag * math.cos(toward)]
        v = rotate(base, 90)
        from_deg = (math.degrees(math.atan2(v[0], v[1])) + 180) % 360
        self.assertAlmostEqual(from_deg, 290, delta=0.01)

    def test_magnitude_is_preserved(self):
        v = rotate([3.0, 4.0], 47)
        self.assertAlmostEqual(math.hypot(v[0], v[1]), 5.0, places=6)

    def test_zero_wind_is_unchanged(self):
        v = rotate([0.0, 0.0], 60)
        self.assertEqual(v, [0.0, 0.0])


class TestFrontWiring(unittest.TestCase):
    """The tick consumer and the kernel forcing reads."""

    def test_tick_calls_the_front_update(self):
        src = TICK.read_text(encoding="utf-8")
        front = src.find("call EFUNC(atmos,updateWeatherFront)")
        self.assertGreater(front, -1, "the front update is not called")
        # It must run after updatePressure and before calculatePressureTrend,
        # so the 3-hour trend buffer sees the perturbed pressure.
        self.assertLess(src.find("call EFUNC(atmos,updatePressure)"), front)
        self.assertLess(front, src.find("call EFUNC(atmos,calculatePressureTrend)"))

    def test_update_wind_reads_the_front_veer(self):
        src = UPDATE_WIND.read_text(encoding="utf-8")
        self.assertIn("frontWindVeerDeg", src)
        self.assertIn("calculateFrontWind", src)

    def test_cloud_development_reads_the_front_term(self):
        src = CLOUD.read_text(encoding="utf-8")
        self.assertIn("frontCloudTerm", src)

    def test_consumer_publishes_the_front_state(self):
        src = CONSUMER.read_text(encoding="utf-8")
        for name in (
            "frontActive",
            "frontType",
            "frontPhase",
            "frontDistanceKm",
            "frontSpeedKmh",
            "frontBearingDeg",
            "frontContrastC",
            "frontWindVeerDeg",
            "frontCloudTerm",
            "frontPrecipRate",
            "frontPrecipPhase",
        ):
            self.assertIn(name, src, f"{name} is not published")

    def test_consumer_perturbs_temperature_and_pressure(self):
        src = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("currentTemperature", src)
        self.assertIn("currentPressure", src)

    def test_gated_on_real_weather(self):
        src = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("realWeatherActive", src)

    def test_setting_is_declared(self):
        src = SETTINGS.read_text(encoding="utf-8")
        self.assertIn("weatherFrontsEnabled", src)


if __name__ == "__main__":
    unittest.main()
