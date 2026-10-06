#!/usr/bin/env python3
"""Perception source contracts (task 16).

The perception kernels are pure and run under sqf_lite in their own suites.
This module locks the wiring the harness cannot execute:

  * the PERCEPTION_SCHEMA length in fnc_perceptionSample.sqf;
  * the PREPS(perception, ...) registrations in addons/optics/XEH_PREP.hpp;
  * an Annex C row for every aee_optics_perception* name the driver publishes.

Run: python3 -m unittest tools.tests.test_perception_contracts -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERCEPTION = REPO / "addons" / "optics" / "functions" / "perception"
SAMPLE = PERCEPTION / "fnc_perceptionSample.sqf"
UPDATE = PERCEPTION / "fnc_perceptionUpdate.sqf"
XEH_PREP = REPO / "addons" / "optics" / "XEH_PREP.hpp"
ANNEX_C = REPO / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"

EXPECTED_SCHEMA_LENGTH = 14

# The kernels that must stay PREP-registered.
EXPECTED_PREPS = [
    "perceptionParams",
    "perceptionSample",
    "perceptionAdaptState",
    "perceptionUpdate",
    "perceptionDetectDeviation",
]


def source_schema():
    text = SAMPLE.read_text(encoding="utf-8")
    block = re.search(r"private _schema = \[(.*?)\];", text, re.DOTALL)
    return re.findall(r'"([^"]+)"', block.group(1))


def published_names():
    text = UPDATE.read_text(encoding="utf-8")
    leaves = re.findall(r"setVariable\s*\[\s*QGVAR\((\w+)\)", text)
    return [f"aee_optics_{leaf}" for leaf in leaves]


class TestSchemaContract(unittest.TestCase):
    def test_schema_length(self):
        self.assertEqual(len(source_schema()), EXPECTED_SCHEMA_LENGTH)

    def test_schema_names_are_unique(self):
        schema = source_schema()
        self.assertEqual(len(set(schema)), len(schema))

    def test_header_states_the_schema_length(self):
        text = SAMPLE.read_text(encoding="utf-8")
        self.assertIn(
            f"PERCEPTION_SCHEMA - the fixed field order the kernel returns ({EXPECTED_SCHEMA_LENGTH} fields)",
            text,
        )


class TestPrepContract(unittest.TestCase):
    def test_every_perception_kernel_is_prepped(self):
        source = XEH_PREP.read_text(encoding="utf-8")
        for name in EXPECTED_PREPS:
            with self.subTest(kernel=name):
                self.assertIn(f"PREPS(perception,{name})", source)

    def test_every_prepped_perception_kernel_has_a_source_file(self):
        source = XEH_PREP.read_text(encoding="utf-8")
        for name in re.findall(r"PREPS\(perception,(\w+)\)", source):
            with self.subTest(kernel=name):
                self.assertTrue((PERCEPTION / f"fnc_{name}.sqf").exists())


class TestAnnexCContract(unittest.TestCase):
    # The six names the plan requires to be documented in Annex C.
    REQUIRED_PUBLISHES = [
        "aee_optics_perceptionState",
        "aee_optics_perceptionLine",
        "aee_optics_perceptionLux",
        "aee_optics_perceptionAperture",
        "aee_optics_perceptionGrade",
        "aee_optics_perceptionFlags",
    ]

    # Internal cursors the driver writes but does not document as API.
    INTERNAL_PUBLISHES = {
        "aee_optics_perceptionPrevTimeToAdapt",
        "aee_optics_perceptionLast",
        "aee_optics_perceptionLogged",
    }

    def test_the_required_publishes_are_documented(self):
        annex = ANNEX_C.read_text(encoding="utf-8")
        published = set(published_names())
        for name in self.REQUIRED_PUBLISHES:
            with self.subTest(name=name):
                self.assertIn(name, published)
                self.assertIn(f"`{name}`", annex)

    def test_no_publish_is_neither_documented_nor_internal(self):
        documented = set(self.REQUIRED_PUBLISHES)
        for name in published_names():
            with self.subTest(name=name):
                self.assertTrue(
                    name in documented or name in self.INTERNAL_PUBLISHES,
                    f"{name} is published with no Annex C row and no internal reason",
                )


if __name__ == "__main__":
    unittest.main()
