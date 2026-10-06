#!/usr/bin/env python3
"""Pure consistency evaluator (task 13).

fnc_evaluateConsistency is executed from its real SQF through
tools/tests/sqf_lite.py with fixture value maps.  The same file proves the
SQF table and data/consistency/invariants.json are in lockstep: the compiled
in constant is parsed and compared to the JSON, field for field.

Fixtures (no world):
  clean       every row passes, overallPass true.
  disagree    INV-2 three-way divergence: modulesInDisagreement 3.
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

# A clean fixture: every invariant agrees.
CLEAN = [
    ["aee_core_illuminanceLux", 100.0],
    ["aee_optics_eyeAdaptedLux", 100.0],
    ["aee_optics_eyeAperture", 34.25],
    ["aee_core_currentTemperature", 15.0],
    ["aee_thermal_groundNodeStack", 16.0],
    ["aee_core_groundSurfaceTemp", 14.0],
    ["aee_core_avgGroundTemp", 15.0],
    ["aee_core_currentWindStr", 5.0],
    ["aee_environmental_scentDispersionIntensity", 0.5],
    ["aee_core_currentTurbulence", 0.3],
    ["aee_thermal_humanCoreTempC", 37.0],
    ["aee_core_coreBodyTemp", 37.5],
    ["aee_core_currentSunElevation", 30.0],
    ["aee_thermal_skyBandTempC", -20.0],
    ["aee_core_lightIsNight", False],
    ["aee_environmental_nightClassification", 0.0],
    ["aee_core_currentWindStrRef", [4.0, 0.4, 0.2]],
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
        self.assertEqual(len(verdicts), 5)
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
                "aee_thermal_groundNodeStack",
                "aee_core_groundSurfaceTemp",
                "aee_core_avgGroundTemp",
            ):
                values[i][1] = 100.0
        return values

    def test_inv2_counts_three_modules(self):
        overall, verdicts = evaluate(self._disagreeing())
        rows = rows_by_id((overall, verdicts))
        self.assertFalse(overall)
        self.assertFalse(rows["INV-2"][1])
        self.assertEqual(rows["INV-2"][3], 3)

    def test_only_inv2_fails(self):
        _, verdicts = evaluate(self._disagreeing())
        failed = [row[0] for row in verdicts if not row[1]]
        self.assertEqual(failed, ["INV-2"])


class TestPredicates(unittest.TestCase):
    def test_aperture_matches_lux_positive(self):
        _, verdicts = evaluate(CLEAN)
        self.assertTrue(rows_by_id((False, verdicts))["INV-1"][1])

    def test_aperture_matches_lux_negative(self):
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_optics_eyeAperture":
                pair[1] = 5.0
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-1"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)

    def test_aperture_uses_supplied_bounds(self):
        # A wider band is supplied, so the same aperture now agrees.
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_optics_eyeAperture":
                pair[1] = 5.0
        values.append(["aee_optics_eyeApertureBounds", [-3, 5, 5, 5]])
        _, verdicts = evaluate(values)
        self.assertTrue(rows_by_id((False, verdicts))["INV-1"][1])

    def test_monotone_with_wind_positive(self):
        _, verdicts = evaluate(CLEAN)
        self.assertTrue(rows_by_id((False, verdicts))["INV-3"][1])

    def test_monotone_with_wind_negative(self):
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_environmental_scentDispersionIntensity":
                pair[1] = 0.1  # wind rose, scent fell
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-3"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)

    def test_daynight_positive(self):
        _, verdicts = evaluate(CLEAN)
        self.assertTrue(rows_by_id((False, verdicts))["INV-5"][1])

    def test_daynight_negative(self):
        values = [list(pair) for pair in CLEAN]
        for pair in values:
            if pair[0] == "aee_core_currentSunElevation":
                pair[1] = -30.0
            if pair[0] == "aee_environmental_nightClassification":
                pair[1] = 4.0
            # lightIsNight stays False, so the night flag disagrees.
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-5"]
        self.assertFalse(row[1])
        self.assertEqual(row[3], 1)

    def test_no_data_is_not_a_failure(self):
        values = [pair for pair in CLEAN if pair[0] != "aee_core_coreBodyTemp"]
        overall, verdicts = evaluate(values)
        row = rows_by_id((overall, verdicts))["INV-4"]
        self.assertTrue(row[1])
        self.assertEqual(row[2], "no-data")

    def test_no_reference_is_not_a_failure(self):
        values = [pair for pair in CLEAN if pair[0] != "aee_core_currentWindStrRef"]
        _, verdicts = evaluate(values)
        row = rows_by_id((False, verdicts))["INV-3"]
        self.assertTrue(row[1])
        self.assertEqual(row[2], "no-reference")


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
