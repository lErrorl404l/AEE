#!/usr/bin/env python3
"""Contract: the consistency monitor never warns on a passing invariant.

The operator RPT ``Arma3_x64_2026-10-08_18-55-33.rpt`` carried 173
``[AEE][core][WARN] consistency: INV-1/2/5`` lines, every one with
``health all-up``.  The values inside the lines prove the rows PASSED:
INV-1 in daylight shows ``aee_core_lightIsNight=false``, so its night-scoped
predicate skipped the comparison; INV-2 shows only two of three producers, so
it is no-data; INV-5 shows the sun above the horizon with classification 0.
The WARN came from the strict branch, which fired on ``_drift > 0`` alone.

Two contracts fix that, and this test pins both:

  1. A passing row is emitted at INFO, never at WARN.
  2. Strict reports only a residual: a row that PASSED with a drift inside
     its tolerance and a full comparison.  A no-data row made no comparison,
     and an out-of-scope row (INV-1 in daylight) left the tolerance, so
     neither is reported.

The monitor reads the world and the engine log, so it cannot run in
``sqf_lite``; this test reads the monitor source and checks the emission
structure.  Complements ``test_consistency_evaluator.py`` (the pure kernel)
and ``aee_p101_consistency_probe.sqf`` (the headless probe).
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / "addons" / "core" / "functions" / "fnc_runConsistencyCheck.sqf"

WARN_CALL = "[_line] call FUNC(consistencyLog);"
INFO_CALL = '[_line, "INFO"] call FUNC(consistencyLog);'


def strip_comments(text: str) -> str:
    """Blank ``//`` and ``/* */`` comments, preserving offsets and strings."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def block_at(code: str, open_idx: int) -> tuple[str, int]:
    """``code[open_idx]`` must be ``{``; return (inner text, index of ``}``)."""
    if code[open_idx] != "{":
        raise AssertionError("expected an opening brace")
    depth = 0
    i = open_idx
    while i < len(code):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return code[open_idx + 1 : i], i
        i += 1
    raise AssertionError("unbalanced braces in the monitor")


class TestConsistencyLogLevel(unittest.TestCase):
    def setUp(self):
        self.code = strip_comments(MONITOR.read_text(encoding="utf-8"))

    def test_a_failing_row_warns_and_a_passing_row_informs(self):
        self.assertIn(WARN_CALL, self.code)
        self.assertIn(INFO_CALL, self.code)

        idx = self.code.index("if (!_rowPass) then {")
        inner, end = block_at(self.code, self.code.index("{", idx))
        # The WARN emitter is the failing branch and only the failing branch.
        self.assertIn(WARN_CALL, inner)
        self.assertNotIn(INFO_CALL, inner)

        # The INFO emitter is the else branch, the passing row.
        rest = self.code[end:]
        else_idx = rest.index("else {")
        else_open = end + else_idx + len("else ")
        else_inner, _ = block_at(self.code, else_open)
        self.assertIn(INFO_CALL, else_inner)
        self.assertNotIn(WARN_CALL, else_inner)

    def test_strict_is_gated_to_a_tolerance_bounded_residual(self):
        # The old condition warned on any drift, including a passing row that
        # never compared its producers.
        self.assertNotIn("_strict && _drift > 0", self.code)
        self.assertIn("_strictResidual", self.code)
        self.assertIn("_drift <= _tolerance", self.code)
        self.assertIn('_detail != "no-data"', self.code)


if __name__ == "__main__":
    unittest.main()
