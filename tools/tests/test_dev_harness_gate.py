#!/usr/bin/env python3
"""The four-layer dev trust gate returns true only when every layer holds.

``fnc_devGate`` is a pure kernel.  Its driver (``fnc_devGateLive``) reads the
engine conditions and passes them, so the truth table runs through the SQF
harness (``tools/tests/sqf_lite.py``) with no engine.

Layer 1 is structural (the dev project lives outside ``addons/``).  Layer 2 is
the addon-load exclusion.  Layer 3 is file patching AND the sentinel file AND
a dev host.  Layer 4 is the fixed verb whitelist and no compile of agent
input.  A false layer leaves the channel a silent no-op.

Run: python3 -m unittest tools.tests.test_dev_harness_gate
"""

from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "tools" / "dev-harness" / "addons" / "dev"
GATE = DEV / "functions" / "fnc_devGate.sqf"

# structural, addon-load, file-patching, sentinel, dev-host, surface.
LAYER_COUNT = 6


def _code_only(text: str) -> str:
    """Blank out line and block comments so a prose word is not a code hit."""
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


class TestDevGateTruthTable(unittest.TestCase):
    """The gate is true only for the all-true combination."""

    def test_true_only_when_every_layer_holds(self):
        for combo in itertools.product((False, True), repeat=LAYER_COUNT):
            with self.subTest(combo=combo):
                self.assertEqual(bool(run_sqf(GATE, list(combo))), all(combo))

    def test_all_true_is_true(self):
        self.assertTrue(run_sqf(GATE, [True] * LAYER_COUNT))

    def test_each_single_false_layer_fails(self):
        for index in range(LAYER_COUNT):
            layers = [True] * LAYER_COUNT
            layers[index] = False
            with self.subTest(failed_layer=index + 1):
                self.assertFalse(run_sqf(GATE, layers))


class TestDevGateSourceContract(unittest.TestCase):
    """The gate and its wiring hold the trust boundary."""

    def test_the_gate_never_compiles_agent_input(self):
        self.assertNotIn("compile", _code_only(GATE.read_text(encoding="utf-8")))

    def test_the_wiring_uses_the_gate_and_is_silent_on_failure(self):
        post = (DEV / "XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_dev_fnc_devGateLive", post)
        for token in ("diag_log", "AEE_LOG"):
            self.assertNotIn(token, post)


if __name__ == "__main__":
    unittest.main()
