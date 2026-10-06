#!/usr/bin/env python3
"""P79 thermal-startup probe contract.

The probe measures the AGC first-pass jump against a stated bound.  The
measurement must be a real first publication: the AGC state is reset and the
pass runs in ONE unscheduled tick.  The thermal pass is a live per-frame
handler, and a per-frame handler is unscheduled, so a direct call from the
probe's scheduled script is preempted mid-function, the live pass republishes
the window, and the pass measured is a warm window (the seed never runs).  The
probe read 1.2 to 27.8 levels across identical runs at one commit before this
change.

Run: python3 -m unittest tools.tests.test_p79_probe_contract -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROBE = (
    REPO / "tests/docker/missions/aee_test.Stratis/aee_p79_thermal_startup_probe.sqf"
)


class TestP79ProbeContract(unittest.TestCase):
    """The first-pass measurement is a real, deterministic first publication."""

    @classmethod
    def setUpClass(cls):
        cls.text = PROBE.read_text(encoding="utf-8")
        cls.start = cls.text.index("private _first = [-1, -1, 0];")
        cls.end = cls.text.index("] call CBA_fnc_addPerFrameHandler", cls.start)

    def test_the_first_pass_runs_in_one_unscheduled_tick(self):
        # A one-shot per-frame handler owns the reset AND the pass, so the live
        # per-frame thermal pass cannot republish the window between them.
        self.assertIn("CBA_fnc_addPerFrameHandler", self.text)
        self.assertIn("CBA_fnc_removePerFrameHandler", self.text)
        body = self.text[self.start : self.end]
        self.assertIn('setVariable ["aee_thermal_agcRadMin", -1];', body)
        self.assertIn("[] call _fnAGC;", body)

    def test_no_scheduled_first_pass_call_remains(self):
        # The old direct call from the scheduled script measured a warm window.
        self.assertNotIn("[] call _fnAGC;", self.text[: self.start])

    def test_the_bound_is_not_widened(self):
        # The fix makes the measurement real; it must not relax the bound.
        self.assertIn("_STATED_JUMP_LEVELS = 20", self.text)


if __name__ == "__main__":
    unittest.main()
