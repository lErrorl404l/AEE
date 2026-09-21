#!/usr/bin/env python3
"""Tests for aee_core_fnc_readState (issue #162 consolidation).

Executes the REAL fnc_readState.sqf through sqf_lite - the type-guarded
state read with the #154 'never 0 for a gate' rule.  A Python mirror
would drift (the issue #204 lesson); executing the source tests the
source.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf

FNC = Path(__file__).parents[2] / "addons/core/functions/fnc_readState.sqf"


def sqf_is_equal_type(a, b):
    """SQF isEqualType: numbers are one type regardless of int/float
    (Python splits them; SQF does not)."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return True
    return type(a) is type(b)


def run(key, default, value, type_=0, never_zero=False):
    """Run the real fnc with a controlled missionNamespace.

    sqf_lite resolves the binary `missionNamespace getVariable [k, d]`
    as a Call(getVariable, [ns, [k, d]]) - the namespace object and the
    arg array are both passed to the callable.
    """
    store = {key: value}
    globs = {
        "getVariable": lambda ns, arr: store.get(arr[0], arr[1]),
        "isEqualType": sqf_is_equal_type,
        "missionNamespace": store,
        "true": True,
        "false": False,
    }
    return run_sqf(FNC, [key, default, type_, never_zero], globs)


class TestReadState(unittest.TestCase):
    def test_returns_stored_value(self):
        self.assertEqual(run("aee_x", 5, 3.5, 1), 3.5)

    def test_missing_returns_default(self):
        self.assertEqual(run("aee_missing", 7, None, 1), 7)

    def test_wrong_type_returns_default(self):
        # stored value is a string but caller wants a number
        self.assertEqual(run("aee_bad", 0.5, "junk", 1), 0.5)

    def test_never_zero_replaces_zero_gate(self):
        # stored 0 (a silent kill) -> the sane default, not 0
        self.assertEqual(run("aee_gate", 1.5, 0, 1, True), 1.5)

    def test_never_zero_keeps_legit_zero(self):
        # a true zero stored is NOT a gate failure when neverZero=False
        self.assertEqual(run("aee_zero_ok", 1.5, 0, 1, False), 0)

    def test_any_type_passes_through(self):
        self.assertEqual(run("aee_arr", [], [1, 2, 3]), [1, 2, 3])

    def test_string_type_check(self):
        self.assertEqual(run("aee_str", "d", "v", 2), "v")
        self.assertEqual(run("aee_str", "d", 42, 2), "d")

    def test_empty_key_returns_default(self):
        self.assertEqual(run("", 9, "anything"), 9)


if __name__ == "__main__":
    unittest.main()
