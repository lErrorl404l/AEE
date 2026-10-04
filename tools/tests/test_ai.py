#!/usr/bin/env python3
"""AI substrate kernel tests (the reusable sense/decide/act/recover layer).

Executes the real SQF kernels through tools/tests/sqf_lite.py, so a test
failure is a source failure, not a mirror drift.  The source-contract
methods read the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_ai -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "addons" / "ai" / "functions"

DECAY = AI / "fnc_stimulusDecay.sqf"
KEY = AI / "fnc_disturbanceKey.sqf"
APPLY = AI / "fnc_disturbanceApply.sqf"
SAMPLE = AI / "fnc_disturbanceSample.sqf"
SENSE = AI / "fnc_agentSense.sqf"
DECIDE = AI / "fnc_agentDecide.sqf"


def decay(magnitude, age, half_life):
    return run_sqf(DECAY, [magnitude, age, half_life])


def key(pos, size=50):
    return run_sqf(KEY, [pos, size])


def apply(cells, cell_key, magnitude, now):
    return run_sqf(APPLY, [cells, cell_key, magnitude, now])


def sample(cells, cell_key, now, half_life):
    return run_sqf(
        SAMPLE,
        [cells, cell_key, now, half_life],
        globals_={"__FUNC__stimulusDecay": lambda m, a, h: run_sqf(DECAY, [m, a, h])},
    )


class TestStimulusDecay(unittest.TestCase):
    def test_age_zero_returns_the_magnitude(self):
        self.assertAlmostEqual(decay(1.0, 0, 45), 1.0)

    def test_age_equal_to_half_life_returns_half(self):
        self.assertAlmostEqual(decay(1.0, 45, 45), 0.5)

    def test_negative_age_clamps_to_one(self):
        self.assertAlmostEqual(decay(1.0, -45, 45), 1.0)

    def test_huge_age_returns_zero(self):
        self.assertAlmostEqual(decay(1.0, 100000, 45), 0.0)


class TestDisturbanceKey(unittest.TestCase):
    def test_same_cell_maps_to_the_same_key(self):
        self.assertEqual(key([0, 0, 0]), key([49, 49, 0]))

    def test_neighbour_cell_maps_to_a_different_key(self):
        self.assertNotEqual(key([0, 0, 0]), key([51, 51, 0]))


class TestDisturbanceField(unittest.TestCase):
    def test_apply_then_sample_at_age_zero(self):
        field = apply([], key([0, 0, 0]), 0.5, 10)
        self.assertAlmostEqual(sample(field, key([0, 0, 0]), 10, 45), 0.5)

    def test_apply_keeps_the_stronger_stimulus(self):
        field = apply([], key([0, 0, 0]), 0.5, 10)
        field = apply(field, key([0, 0, 0]), 0.2, 20)
        self.assertAlmostEqual(sample(field, key([0, 0, 0]), 20, 45), 0.5)

    def test_sample_missing_cell_is_zero(self):
        self.assertAlmostEqual(sample([], key([5, 5, 0]), 0, 45), 0.0)


def sense(disturbance, distance, need, senses):
    return run_sqf(SENSE, [disturbance, distance, need, senses])


def decide(state, thresholds):
    return run_sqf(DECIDE, [state, thresholds])


class TestAgentSense(unittest.TestCase):
    def test_player_at_zero_distance_is_full_proximity(self):
        self.assertEqual(sense(0, 0, 0, [100]), [0, 1, 0])

    def test_player_beyond_the_range_is_zero_proximity(self):
        self.assertEqual(sense(0, 1000, 0, [100]), [0, 0, 0])


class TestAgentDecide(unittest.TestCase):
    THRESHOLDS = [0.7, 0.3, 0.6, 0.2]

    def test_high_disturbance_flees(self):
        self.assertEqual(decide([0.9, 1, 0], self.THRESHOLDS), 3)

    def test_mid_disturbance_freezes(self):
        self.assertEqual(decide([0.5, 1, 0], self.THRESHOLDS), 4)

    def test_high_need_with_low_disturbance_drinks(self):
        self.assertEqual(decide([0.1, 1, 0.8], self.THRESHOLDS), 2)

    def test_low_need_with_low_disturbance_forages(self):
        self.assertEqual(decide([0.1, 1, 0.3], self.THRESHOLDS), 1)

    def test_rest(self):
        self.assertEqual(decide([0.0, 1, 0.1], self.THRESHOLDS), 0)


if __name__ == "__main__":
    unittest.main()
