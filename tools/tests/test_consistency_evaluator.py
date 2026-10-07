#!/usr/bin/env python3
"""Pure consistency evaluator (task 13).

fnc_evaluateConsistency is executed from its real SQF through
tools/tests/sqf_lite.py with fixture value maps.  The same file proves the
SQF table and data/consistency/invariants.json are in lockstep: the compiled
in constant is parsed and compared to the JSON, field for field.

Fixtures (no world):
  clean       every row passes, overallPass true.
  disagree    INV-2 ground-chain divergence: modulesInDisagreement 2.
  predicates  one fixture per predicate, positive and negative.

Run: python3 -m unittest tools.tests.test_consistency_evaluator
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "addons" / "core" / "functions" / "fnc_evaluateConsistency.sqf"
SQF_TABLE = REPO / "addons" / "core" / "functions" / "fnc_consistencyLoadTable.sqf"
JSON_TABLE = REPO / "data" / "consistency" / "invariants.json"

ROW_ORDER = [
    "id",
    "name",
    "producers",
    "predicate",
    "tolerance",
    "severity",
    "grade",
    "note",
]

# A clean fixture: every invariant agrees.  It is a night scene, so INV-1's
# night-scoped comparison runs rather than skipping out of scope.
CLEAN = [
    ["aee_core_illuminanceLux", 100.0],
    ["aee_optics_eyeSceneLux", 100.0],
    ["aee_core_currentTemperature", 15.0],
    ["aee_core_groundSurfaceTemp", 14.0],
    ["aee_core_avgGroundTemp", 15.0],
    ["aee_core_currentSunElevation", -30.0],
    ["aee_thermal_skyBandTempC", -20.0],
    ["aee_core_lightIsNight", True],
    ["aee_environmental_nightClassification", 4.0],
]

# The operator RPT (/ext/SteamLibrary/.../Arma3_x64_2026-10-07_16-56-15.rpt)
# is the pre-eye-fix build.  The core side of INV-1 is unchanged by the eye
# fix: core illuminanceLux 0.5302 lx at night (recovered from the INV-1
# failure-line drift, 46.4727 - 45.9425).  The eye fix (98d1f17) gates the
# engine local term by sun elevation, so the eye composes the physical sky:
# core ambientLux 0.142886 lx times the sky fraction plus the core dynamic
# term, which totals the core illuminance.  The healthy night pair is the
# like-for-like physical-sky model.
RPT_NIGHT = [
    ["aee_core_illuminanceLux", 0.5302],
    ["aee_optics_eyeSceneLux", 0.5302],
    ["aee_core_currentTemperature", 17.5],
    ["aee_core_groundSurfaceTemp", 16.0],
    ["aee_core_avgGroundTemp", 15.7872],
    ["aee_core_currentSunElevation", -31.4263],
    ["aee_thermal_skyBandTempC", -0.443878],
    ["aee_core_lightIsNight", True],
    ["aee_environmental_nightClassification", 4.0],
]


def evaluate(values):
    table = run_sqf(SQF_TABLE, [])
    return run_sqf(EVAL, [table, values])


def rows_by_id(result):
    return {row[0]: row for row in result[1]}


def sqf_table():
    return run_sqf(SQF_TABLE, [])


def json_table():
    raw = json.loads(JSON_TABLE.read_text(encoding="utf-8"))
    return [[row[key] for key in ROW_ORDER] for row in raw]


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestLockstep(unittest.TestCase):
    def test_sqf_table_matches_the_json(self):
        self.assertEqual(sqf_table(), json_table())


class TestCleanFixture(unittest.TestCase):
    def test_all_pass(self):
        overall, verdicts = evaluate(CLEAN)
        self.assertTrue(overall)
        self.assertEqual(len(verdicts), 3)
        for row in verdicts:
            with self.subTest(row=row[0]):
                self.assertTrue(row[1], f"{row[0]} failed: {row[2]}")
                self.assertEqual(row[3], 0)

    def test_verdict_shape(self):
        _, verdicts = evaluate(CLEAN)
        for row in verdicts:
            self.assertEqual(len(row), 4)
            self.assertIsInstance(row[0], str)
            self.assertIsInstance(row[1], bool)
            self.assertIsInstance(row[2], str)
            self.assertIsInstance(row[3], (int, float))


class TestThreeWayDisagreement(unittest.TestCase):
    def _disagreeing(self):
        values = [list(pair) for pair in CLEAN]
        for i, pair in enumerate(values):
            if pair[0] == "aee_core_currentTemperature":
                values[i][1] = 0.0
            if pair[0] in (
                "aee_core_groundSurfaceTemp",
                "aee_core_avgGroundTemp",
            ):
                values[i][1] = 100.0
        return values

    def test_inv2_counts_two_modules(self):
        overall, verdicts = evaluate(self._disagreeing())
        rows = rows_by_id((overall, verdicts))
        self.assertFalse(overall)
        self.assertFalse(rows["INV-2"][1])
        self.assertEqual(rows["INV-2"][3], 2)

    def test_only_inv2_fails(self):
        _, verdicts = evaluate(self._disagreeing())
        failed = [row[0] for row in verdicts if not row[1]]
        self.assertEqual(failed, ["INV-2"])


class TestPredicates(unittest.TestCase):
    def test_night_scene_agreement_positive(self):
        _, verdicts = evaluate(CLEAN)
        self.assertTrue(rows_by_id((False, verdicts))["INV-1"][1])

    def test_night_scene_agreement_negative(self):
        # The eye scene collapses away from the core illuminance at night:
        # a real divergence, so INV-1 must fire.
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_optics_eyeSceneLux":
                pair[1] = 0.0
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-1"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)

    def test_night_scene_agreement_is_out_of_scope_in_day(self):
        # In daylight the two sides use different light sources, so the row
        # is out of scope and passes however far the scene sits from the core.
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_core_lightIsNight":
                pair[1] = False
            if pair[0] == "aee_optics_eyeSceneLux":
                pair[1] = 80000.0
            if pair[0] == "aee_core_currentSunElevation":
                pair[1] = 30.0
            if pair[0] == "aee_environmental_nightClassification":
                pair[1] = 0.0
        _, verdicts = evaluate(values)
        self.assertTrue(rows_by_id((False, verdicts))["INV-1"][1])

    def test_daynight_positive(self):
        _, verdicts = evaluate(CLEAN)
        self.assertTrue(rows_by_id((False, verdicts))["INV-5"][1])

    def test_daynight_negative(self):
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_core_currentSunElevation":
                pair[1] = 30.0
            if pair[0] == "aee_environmental_nightClassification":
                pair[1] = 0.0
            # lightIsNight stays True, so the night flag disagrees.
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-5"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)

    def test_no_data_is_not_a_failure(self):
        values = [pair for pair in CLEAN if pair[0] != "aee_core_lightIsNight"]
        overall, verdicts = evaluate(values)
        for vid in ("INV-1", "INV-5"):
            row = rows_by_id((overall, verdicts))[vid]
            self.assertTrue(row[1])
            self.assertEqual(row[2], "no-data")


class TestRptReplay(unittest.TestCase):
    """The operator RPT night session must produce no genuine failure."""

    def test_the_rpt_night_pair_passes(self):
        overall, verdicts = evaluate(RPT_NIGHT)
        self.assertTrue(overall, [row for row in verdicts if not row[1]])

    def test_the_pre_fix_scene_still_fires(self):
        # The pre-fix eye scene read 46.45 lx at night (an indoor-scale engine
        # term), against a core illuminance of 0.5302 lx.  The rebind compares
        # the eye's own scene, so the historical divergence still raises INV-1.
        values = [list(pair) for pair in RPT_NIGHT]
        for pair in values:
            if pair[0] == "aee_optics_eyeSceneLux":
                pair[1] = 46.4537
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-1"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)


class TestPurity(unittest.TestCase):
    def test_no_world_reads_and_no_module_calls(self):
        code = strip_comments(EVAL.read_text(encoding="utf-8"))
        self.assertNotIn("getVariable", code)
        self.assertNotIn("missionNamespace", code)
        self.assertNotIn("setVariable", code)
        self.assertNotIn("FUNC(", code)
        self.assertNotIn("EFUNC(", code)

    def test_takes_the_table_and_the_value_map(self):
        code = strip_comments(EVAL.read_text(encoding="utf-8"))
        self.assertIn('"_table"', code)
        self.assertIn('"_values"', code)


if __name__ == "__main__":
    unittest.main()
