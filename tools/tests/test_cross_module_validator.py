#!/usr/bin/env python3
"""Regression tests for the cross-module reference validator.

A false positive here failed CI.  optics declares its adaptation pools by
direct assignment (`GVAR(eyeState) = _step;`), a form the scanner did not
recognise as a declaration.  core declares a different variable under the
same bare name, so the scanner saw only core as owner and flagged optics'
own read as a cross-module bug.

The tests lock both directions of the fix:
  - a direct assignment is a declaration by the assigning module;
  - a read whose name is declared ONLY in another module is still a bug.

Run: python3 -m unittest tools.tests.test_cross_module_validator -v
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_cross_module as v  # noqa: E402


def _write(root: Path, addon: str, name: str, body: str) -> None:
    target = root / "addons" / addon / "functions"
    target.mkdir(parents=True, exist_ok=True)
    (target / name).write_text(body, encoding="utf-8")


class _Tree(unittest.TestCase):
    """Point the validator at a small temporary addons tree."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._saved = v.ADDONS
        v.ADDONS = self.root / "addons"

    def tearDown(self):
        v.ADDONS = self._saved
        self._tmp.cleanup()

    def _main(self) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = v.main()
        return rc, buf.getvalue()


class TestDirectAssignmentDeclaration(_Tree):
    def test_direct_assignment_is_a_declaration(self):
        """The false positive: the writer and the reader are the same module."""
        _write(
            self.root,
            "optics",
            "fnc_update.sqf",
            "GVAR(eyeState) = [1, 2];\n"
            "private _s = missionNamespace getVariable [QGVAR(eyeState), []];\n",
        )
        _write(
            self.root,
            "core",
            "fnc_other.sqf",
            "missionNamespace setVariable [QGVAR(eyeState), [0, 0]];\n",
        )
        self.assertIn("optics", v.scan_declarations().get("eyeState", set()))
        rc, out = self._main()
        self.assertEqual(rc, 0, out)
        self.assertIn("clean", out)

    def test_equality_is_not_a_declaration(self):
        """`GVAR(x) == y` is a read, so a foreign-only declaration still flags."""
        _write(
            self.root,
            "alpha",
            "fnc_a.sqf",
            "if (GVAR(mode) == 1) then {};\n"
            "private _m = missionNamespace getVariable [QGVAR(mode), 0];\n",
        )
        _write(
            self.root,
            "beta",
            "fnc_b.sqf",
            "missionNamespace setVariable [QGVAR(mode), 1];\n",
        )
        self.assertNotIn("alpha", v.scan_declarations().get("mode", set()))
        rc, out = self._main()
        self.assertEqual(rc, 1, out)
        self.assertIn("alpha: QGVAR(mode)", out)

    def test_cross_module_only_read_is_still_flagged(self):
        """The bug class the validator exists to catch is not weakened."""
        _write(
            self.root,
            "alpha",
            "fnc_a.sqf",
            "private _s = missionNamespace getVariable [QGVAR(shared), 0];\n",
        )
        _write(
            self.root,
            "beta",
            "fnc_b.sqf",
            "missionNamespace setVariable [QGVAR(shared), 1];\n",
        )
        rc, out = self._main()
        self.assertEqual(rc, 1, out)
        self.assertIn("alpha: QGVAR(shared)", out)

    def test_cross_module_assignment_is_not_an_own_declaration(self):
        """`EGVAR(other, x) = ...` names the OTHER module as owner."""
        _write(self.root, "alpha", "fnc_a.sqf", "EGVAR(beta, state) = [1];\n")
        self.assertNotIn("alpha", v.scan_declarations().get("state", set()))


if __name__ == "__main__":
    unittest.main()
