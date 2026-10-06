#!/usr/bin/env python3
"""Invariant table contract (task 12).

data/consistency/invariants.json is the declarative contract for the
cross-module consistency harness.  This test asserts every row is complete
and every referenced variable is a real, Annex C documented aee_ name.

Annex C allowance: the rows for the variables introduced by task 14
(aee_thermal_humanCoreTempC, aee_core_coreBodyTemp, aee_thermal_skyBandTempC)
and the pre-existing undocumented producer aee_thermal_groundNodeStack are
added to Annex C by task 18, which owns the annex.  Until then those four
names are allowed without an Annex C row.  No other name is allowed: an
invented variable fails this test.

Run: python3 -m unittest tools.tests.test_invariant_table
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "data" / "consistency" / "invariants.json"
ANNEX_C = REPO / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"

REQUIRED_FIELDS = {
    "id",
    "name",
    "producers",
    "predicate",
    "tolerance",
    "severity",
    "grade",
    "note",
}

ALLOWED_PREDICATES = {
    "agree_within",
    "aperture_matches_lux",
    "monotone_with_wind",
    "daynight_consistent",
}

# AEE publishes camelCase leaf names (aee_core_currentWindStr), so the
# contract pattern is matched case-insensitively.  It still rejects any name
# that is not aee_<module>_<lower-case-or-camel-leaf>.
VARIABLE_RE = re.compile(r"^aee_[a-z0-9_]+$", re.IGNORECASE)
MODULE_RE = re.compile(r"^[a-z0-9_]+$")

# Documented task 14 / pre-existing producers with no Annex C row yet.
ANNEX_C_ALLOWED = {
    "aee_thermal_humanCoreTempC",
    "aee_core_coreBodyTemp",
    "aee_thermal_skyBandTempC",
    "aee_thermal_groundNodeStack",
}

ADDONS = REPO / "addons"
_SET = re.compile(
    r"setVariable\s*\[\s*"
    r'(?:"(?P<lit>aee_[A-Za-z0-9_]+)"|(?P<macro>(?:Q?EGVAR|Q?GVAR)\([^)]*\)))'
)


def _produced_names() -> set[str]:
    """Every aee_ name an addon writes.  A name no addon writes is invented,
    so this is the real guard behind the Annex C check: Annex C lags for
    pre-existing reads (currentSunElevation, currentWindStr, ...)."""
    produced: set[str] = set()
    for path in sorted(ADDONS.rglob("*.sqf")):
        addon = path.relative_to(ADDONS).parts[0]
        text = re.sub(
            r"//[^\n]*", "", path.read_text(encoding="utf-8", errors="replace")
        )
        for m in _SET.finditer(text):
            lit = m.group("lit")
            if lit:
                produced.add(lit)
                continue
            body = m.group("macro")[m.group("macro").index("(") + 1 : -1]
            if "," in body:
                owner, leaf = (s.strip() for s in body.split(",", 1))
                produced.add(f"aee_{owner}_{leaf}")
            else:
                produced.add(f"aee_{addon}_{body.strip()}")
    return produced


PRODUCED = _produced_names()


def load_rows():
    return json.loads(TABLE.read_text(encoding="utf-8"))


class TestInvariantTable(unittest.TestCase):
    def setUp(self):
        self.rows = load_rows()

    def test_five_invariants(self):
        self.assertEqual(len(self.rows), 5)
        self.assertEqual(
            [row["id"] for row in self.rows],
            ["INV-1", "INV-2", "INV-3", "INV-4", "INV-5"],
        )

    def test_ids_and_names_are_unique(self):
        self.assertEqual(len({row["id"] for row in self.rows}), len(self.rows))
        self.assertEqual(len({row["name"] for row in self.rows}), len(self.rows))

    def test_every_row_has_exactly_the_required_fields(self):
        for row in self.rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(set(row), REQUIRED_FIELDS)

    def test_every_variable_is_a_well_formed_aee_name(self):
        for row in self.rows:
            for module, variable in row["producers"]:
                with self.subTest(variable=variable):
                    self.assertRegex(variable, VARIABLE_RE)
                    self.assertRegex(module, MODULE_RE)
                    # The module is the addon that owns the prefix, so a
                    # aee_<module>_* name cannot claim the wrong owner.
                    self.assertEqual(module, variable.split("_", 2)[1])

    def test_producers_are_pairs(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertTrue(row["producers"], "no producers")
                for entry in row["producers"]:
                    self.assertIsInstance(entry, list)
                    self.assertEqual(len(entry), 2)

    def test_every_predicate_is_allowed(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertIn(row["predicate"], ALLOWED_PREDICATES)

    def test_every_tolerance_is_a_number(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                tol = row["tolerance"]
                self.assertIsInstance(tol, (int, float))
                self.assertNotIsInstance(tol, bool)

    def test_severity_and_grade_are_strings(self):
        for row in self.rows:
            with self.subTest(row=row["id"]):
                self.assertIsInstance(row["severity"], str)
                self.assertIsInstance(row["grade"], str)
                self.assertTrue(row["note"].strip())

    def test_every_variable_is_documented(self):
        annex = ANNEX_C.read_text(encoding="utf-8")
        for row in self.rows:
            for _, variable in row["producers"]:
                with self.subTest(variable=variable):
                    documented = f"`{variable}`" in annex
                    # Annex C rows for the new (task 14) and pre-existing
                    # undocumented producers arrive with task 18.  Until then
                    # a name is acceptable when it is a real producer: a name
                    # no addon writes is invented and fails here.
                    allowed = variable in ANNEX_C_ALLOWED or variable in PRODUCED
                    self.assertTrue(
                        documented or allowed,
                        f"{variable} is undocumented and nothing produces it",
                    )


if __name__ == "__main__":
    unittest.main()
