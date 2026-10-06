#!/usr/bin/env python3
"""Perception aggregation kernel (task 7).

fnc_perceptionSample is executed from its real SQF through
tools/tests/sqf_lite.py.  The kernel is pure: it reads no world state, so every
test seeds the value map by hand.

The schema is parsed from the source, so a schema change that the tests do not
know about fails here rather than drifting silently.  One fixture is run per
schema field: the field is supplied alone and its value must land at the field
index while every other field keeps its graded default.

Run: python3 -m unittest tools.tests.test_perception_sample -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SAMPLE = (
    REPO / "addons" / "optics" / "functions" / "perception" / "fnc_perceptionSample.sqf"
)

# The schema, in return order.  Asserted equal to the source list.
EXPECTED_SCHEMA = [
    "sceneLux",
    "adaptedLux",
    "eyeAperture",
    "pupilMm",
    "mesopicWeight",
    "appliedGrade",
    "cameraTint",
    "nvgState",
    "thermalState",
    "uvIndex",
    "stressState",
    "injuryState",
    "activeEffects",
    "eyeAdaptationState",
]

# The graded defaults, in schema order, mirrored from the kernel header.
DEFAULTS = [
    1,
    1,
    8,
    4.9,
    1,
    [1, 1, 0, 0],
    [1, 1, 1, 1],
    [False, 0, 0, 0, False],
    [False, 0, 0, 0, 0],
    0,
    [0, 0, 0, 0],
    [0, 0],
    [],
    [0, 0, 0, 0],
]

# One distinct value per schema field.
VALUES = [
    12.5,
    3.25,
    21.0,
    5.5,
    0.75,
    [1.1, 1.2, 0.1, 0.05],
    [0.9, 0.8, 0.7, 1.0],
    [True, 2.0, "TIER2", 3.0, True],
    [True, 1.0, 2.0, 31.5, 0.4],
    7.0,
    [30.0, -5.0, 0.2, 0.1],
    [1.0, 0.5],
    ["solarGlare", "mirage"],
    [0.5, 1.5, 1.0, 9.0],
]


def source_schema():
    text = SAMPLE.read_text(encoding="utf-8")
    block = re.search(r"private _schema = \[(.*?)\];", text, re.DOTALL)
    return re.findall(r'"([^"]+)"', block.group(1))


def sample(pairs):
    return run_sqf(SAMPLE, [pairs])


class TestSchema(unittest.TestCase):
    def test_source_schema_matches_the_expected_order(self):
        self.assertEqual(source_schema(), EXPECTED_SCHEMA)

    def test_schema_has_fourteen_fields(self):
        self.assertEqual(len(EXPECTED_SCHEMA), 14)


class TestReturnShape(unittest.TestCase):
    def test_length_equals_the_schema_length(self):
        result = sample([[k, v] for k, v in zip(EXPECTED_SCHEMA, VALUES)])
        self.assertEqual(len(result), len(EXPECTED_SCHEMA))

    def test_full_fixture_returns_every_supplied_value(self):
        result = sample([[k, v] for k, v in zip(EXPECTED_SCHEMA, VALUES)])
        for index, (key, value) in enumerate(zip(EXPECTED_SCHEMA, VALUES)):
            with self.subTest(field=key):
                self.assertEqual(result[index], value)


class TestDefaults(unittest.TestCase):
    def test_empty_map_returns_the_defaults(self):
        self.assertEqual(sample([]), DEFAULTS)

    def test_every_default_lands_in_schema_order(self):
        result = sample([])
        self.assertEqual(len(result), len(DEFAULTS))


class TestOneFixturePerField(unittest.TestCase):
    """One fixture per schema field: the field alone, everything else default."""

    def test_single_field_lands_at_its_index(self):
        for index, (key, value) in enumerate(zip(EXPECTED_SCHEMA, VALUES)):
            with self.subTest(field=key):
                result = sample([[key, value]])
                self.assertEqual(result[index], value)
                for other in range(len(EXPECTED_SCHEMA)):
                    if other != index:
                        self.assertEqual(result[other], DEFAULTS[other])


class TestMalformedInput(unittest.TestCase):
    def test_a_short_pair_is_skipped(self):
        # A one-element pair cannot carry a value, so the field keeps its
        # default.
        self.assertEqual(sample([["sceneLux"]]), DEFAULTS)

    def test_an_unknown_key_is_ignored(self):
        result = sample([["notAField", 999]])
        self.assertEqual(result, DEFAULTS)

    def test_the_first_matching_pair_wins(self):
        result = sample([["uvIndex", 1.0], ["uvIndex", 9.0]])
        self.assertEqual(result[EXPECTED_SCHEMA.index("uvIndex")], 1.0)


if __name__ == "__main__":
    unittest.main()
