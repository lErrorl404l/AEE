#!/usr/bin/env python3
"""Producer source contract (task 14).

Every value the cross-module consistency harness reads must be produced and
consumed.  This locks the three new producers in place:

  aee_thermal_humanCoreTempC  published by fnc_solveTwoNodeSelection.sqf
  aee_core_coreBodyTemp       published by fnc_coreBodyTemp.sqf
  aee_thermal_skyBandTempC    published by fnc_calculateBandRadiance.sqf

A name is WRITTEN when a setVariable call in an addon resolves to it.  A name
is READ when a getVariable call resolves to it, or when it is declared as a
producer in data/consistency/invariants.json: the declarative table is the
consumer contract the runtime monitor (task 15) reads into the value map, and
the compiled-in SQF twin (fnc_consistencyLoadTable.sqf) names the same
variables.  The two thermal producers have no direct getVariable yet because
the runtime monitor is a later task; the table is their declared consumer.

Run: python3 -m unittest tools.tests.test_producer_contract
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
JSON_TABLE = REPO / "data" / "consistency" / "invariants.json"
SQF_TABLE = REPO / "addons" / "core" / "functions" / "fnc_consistencyLoadTable.sqf"

NEW_NAMES = [
    "aee_thermal_humanCoreTempC",
    "aee_core_coreBodyTemp",
    "aee_thermal_skyBandTempC",
]

# setVariable / getVariable first argument: a literal aee_ name or a GVAR /
# EGVAR / QGVAR / QEGVAR macro.
_CALL = re.compile(
    r"(?P<kind>setVariable|getVariable)\s*\[\s*"
    r'(?P<arg>"aee_[A-Za-z0-9_]+"|(?:Q?EGVAR|Q?GVAR)\([^)]*\))'
)


def _resolve(arg: str, addon: str) -> str:
    if arg.startswith('"'):
        return arg.strip('"')
    m = re.match(r"[QE]?EGVAR\((\w+),(\w+)\)", arg)
    if m:
        return f"aee_{m.group(1)}_{m.group(2)}"
    m = re.match(r"[QE]?GVAR\((\w+)\)", arg)
    return f"aee_{addon}_{m.group(1)}"


def _sources():
    for path in sorted(ADDONS.rglob("*.sqf")):
        addon = path.relative_to(ADDONS).parts[0]
        text = re.sub(
            r"//[^\n]*", "", path.read_text(encoding="utf-8", errors="replace")
        )
        yield addon, path, text


def _written(name: str) -> list[str]:
    hits = []
    for addon, path, text in _sources():
        for m in _CALL.finditer(text):
            if (
                m.group("kind") == "setVariable"
                and _resolve(m.group("arg"), addon) == name
            ):
                hits.append(str(path.relative_to(REPO)))
    return hits


def _read(name: str) -> list[str]:
    hits = []
    for addon, path, text in _sources():
        for m in _CALL.finditer(text):
            if (
                m.group("kind") == "getVariable"
                and _resolve(m.group("arg"), addon) == name
            ):
                hits.append(str(path.relative_to(REPO)))
    return hits


class TestNewProducers(unittest.TestCase):
    def test_each_new_name_is_written(self):
        for name in NEW_NAMES:
            with self.subTest(name=name):
                self.assertTrue(_written(name), f"{name} is produced by nothing")

    def test_each_new_name_has_a_declared_consumer(self):
        # The task 14 contract: written and read.  The declarative table is
        # the consumer contract for the runtime monitor, and the compiled-in
        # SQF twin names the same variables.  The table lands with tasks 12
        # and 13, so this check runs once it is present.
        if not JSON_TABLE.exists() or not SQF_TABLE.exists():
            self.skipTest("consumer table not present yet (task 12/13)")
        declared = {
            variable
            for row in json.loads(JSON_TABLE.read_text(encoding="utf-8"))
            for _, variable in row["producers"]
        }
        sqf = SQF_TABLE.read_text(encoding="utf-8")
        for name in NEW_NAMES:
            with self.subTest(name=name):
                consumed = bool(_read(name)) or name in declared
                self.assertTrue(consumed, f"{name} has no read and no table consumer")
                self.assertIn(name, sqf, f"{name} is not in the compiled-in table")


class TestKATOrphanFix(unittest.TestCase):
    """aee_core_coreBodyTemp fixes the orphan read at fnc_integrateKAT.sqf:37."""

    def test_the_kat_reader_is_present(self):
        kat = REPO / "addons" / "compat_kat" / "functions" / "fnc_integrateKAT.sqf"
        self.assertIn("aee_core_coreBodyTemp", kat.read_text(encoding="utf-8"))

    def test_core_produces_what_kat_reads(self):
        self.assertTrue(_written("aee_core_coreBodyTemp"))
        self.assertTrue(_read("aee_core_coreBodyTemp"))


if __name__ == "__main__":
    unittest.main()
