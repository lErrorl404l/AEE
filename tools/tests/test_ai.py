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
PRUNE = AI / "fnc_disturbancePrune.sqf"
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


def prune(cells, now, cap=256, horizon=120):
    # The harness strips the preprocessor header, so the half-life macro is
    # injected as a global.  The engine expands it to 45 at build time.
    return run_sqf(
        PRUNE,
        [cells, now, cap, horizon],
        globals_={
            "__FUNC__stimulusDecay": lambda m, a, h: run_sqf(DECAY, [m, a, h]),
            "AI_STIMULUS_HALF_LIFE": 45,
        },
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


def _seed_field(now, cells, magnitude=1.0):
    # Distinct cells at a 50 m step, so each key is unique.
    return [
        [key([i * 50, 0, 0], 50), magnitude, now - age] for i, age in enumerate(cells)
    ]


class TestDisturbancePrune(unittest.TestCase):
    """The field bound: an age prune then a decayed-magnitude cap."""

    def test_the_bound_holds_over_a_long_field(self):
        # 2000 cells, times spread over 600 s.  Only the last 120 s survive
        # the age prune, and the survivors still exceed the 256 cap.
        now = 600.0
        field = _seed_field(now, [i * 0.3 for i in range(2000)])
        result = prune(field, now, 256, 120)
        self.assertLessEqual(len(result), 256)
        for entry in result:
            self.assertLessEqual(now - (entry[2]), 120)

    def test_a_new_over_cap_field_returns_exactly_the_cap(self):
        # 2000 new cells: the age prune keeps all of them, so the cap alone
        # must return exactly 256 entries.
        now = 500.0
        field = _seed_field(now, [0.0 for _ in range(2000)])
        result = prune(field, now, 256, 120)
        self.assertEqual(len(result), 256)
        self.assertEqual(len({tuple(entry[0]) for entry in result}), 256)

    def test_a_small_field_is_returned_unchanged(self):
        # A field at or below the cap must pass through untouched, so the
        # existing apply and sample semantics do not change.
        now = 120.0
        field = [[key([0, 0, 0]), 0.5, 100], [key([60, 0, 0]), 0.4, 110]]
        result = prune(field, now, 256, 120)
        self.assertEqual(result, field)
        # A cap-selecting regression would return 256 here.
        self.assertNotEqual(len(result), 256)

    def test_the_cap_prefers_the_larger_decayed_magnitude(self):
        # The older cell has the larger raw magnitude but the smaller decayed
        # value, so the cap keeps the newer cell.
        now = 100.0
        strong_old = [key([0, 0, 0]), 1.0, 55]  # age 45, decayed 0.5
        weak_new = [key([60, 0, 0]), 0.6, 100]  # age 0, decayed 0.6
        result = prune([strong_old, weak_new], now, 1, 120)
        self.assertEqual(result, [weak_new])

    def test_stale_cells_are_dropped_before_the_cap(self):
        now = 1000.0
        stale = [key([0, 0, 0]), 1.0, 800]
        fresh = [key([60, 0, 0]), 0.2, 990]
        result = prune([stale, fresh], now, 256, 120)
        self.assertEqual(result, [fresh])


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


AI_DIR = ROOT / "addons" / "ai"


class TestAiSourceContracts(unittest.TestCase):
    """The engine wiring the harness cannot execute."""

    def test_init_ai_gates_on_has_interface(self):
        text = (AI / "fnc_initAI.sqf").read_text(encoding="utf-8")
        self.assertIn("hasInterface", text)

    def test_no_object_creation_or_do_move(self):
        forbidden = ("createVehicle", "createVehicleLocal", "doMove", "doStop")
        for path in AI_DIR.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.name} contains {token}")

    def test_force_decide_hook_is_read(self):
        text = (AI / "fnc_aiTick.sqf").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("aee_ai_forceDecide"), 1)

    def test_both_field_owners_prune_with_the_shared_policy(self):
        wildlife_tick = (
            ROOT / "addons" / "wildlife" / "functions" / "fnc_wildlifeTick.sqf"
        )
        for path in (wildlife_tick, AI / "fnc_receiveStimulus.sqf"):
            text = path.read_text(encoding="utf-8")
            calls = [line for line in text.splitlines() if "disturbancePrune" in line]
            self.assertTrue(calls, f"{path.name} does not call disturbancePrune")
            self.assertTrue(
                any(
                    "AI_CELL_CAP" in line and "AI_CELL_HORIZON" in line
                    for line in calls
                ),
                f"{path.name} does not pass the cap and the horizon",
            )


if __name__ == "__main__":
    unittest.main()
