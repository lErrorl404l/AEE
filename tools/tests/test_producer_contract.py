#!/usr/bin/env python3
"""Producer source contract.

Every value the cross-module consistency harness reads must be produced by an
addon and named in the compiled-in invariant table.  The declarative table
(data/consistency/invariants.json) is the consumer contract the runtime monitor
(task 15) reads into the value map, and the compiled-in SQF twin
(fnc_consistencyLoadTable.sqf) names the same variables.

A name is WRITTEN when a setVariable call in an addon resolves to it.

The KAT orphan fix is locked separately: aee_core_coreBodyTemp is written by
core and read by compat_kat, so it is a real producer even though no invariant
names it after the INV-4 removal.

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
SQF_TABLE = (
    REPO / "addons" / "diagnostics" / "functions" / "fnc_consistencyLoadTable.sqf"
)

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


def harness_producers() -> set[str]:
    """Every producer the invariant table names, from the JSON contract."""
    return {
        variable
        for row in json.loads(JSON_TABLE.read_text(encoding="utf-8"))
        for _, variable in row["producers"]
    }


class TestHarnessProducers(unittest.TestCase):
    def test_the_table_names_producers(self):
        self.assertTrue(harness_producers())

    def test_each_harness_producer_is_written(self):
        for name in sorted(harness_producers()):
            with self.subTest(name=name):
                self.assertTrue(_written(name), f"{name} is produced by nothing")

    def test_each_harness_producer_is_in_the_compiled_table(self):
        sqf = SQF_TABLE.read_text(encoding="utf-8")
        for name in sorted(harness_producers()):
            with self.subTest(name=name):
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
