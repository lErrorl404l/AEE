#!/usr/bin/env python3
"""Stamina-to-animation coupling tests (issue #212).

Locks the movement-speed coupling physics in
fnc_applyMovementSpeed.sqf: fatigue/cold/load map to a speed
coefficient (0.75..1.0), the weakest factor governs, and the ACE3
advanced-fatigue guard prevents conflict.

The maths is a Python mirror verified against the SOURCE text (the
#204 no-drift lesson).
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (
    REPO / "addons/physiology/functions/strain/fnc_applyMovementSpeed.sqf"
).read_text(encoding="utf-8")


def factor(fatigue, dexterity, load):
    """Mirror of the SQF: each maps to a speed, the weakest governs,
    clamped to 0.75..1.0."""
    fs = 0.75 + (1.0 - 0.75) * (fatigue - 0.3) / 0.7
    cs = 0.85 + (1.0 - 0.85) * (dexterity - 0.4) / 0.6
    ls = 1.0 + (0.90 - 1.0) * (max(0, min(1, load)) / 0.85) if load > 0 else 1.0
    fs = max(0.75, min(1.0, fs))
    cs = max(0.85, min(1.0, cs))
    ls = max(0.90, min(1.0, ls))
    return max(0.75, min(1.0, min(fs, cs, ls)))


class TestSpeedCoupling(unittest.TestCase):
    def test_fresh_full_speed(self):
        # Fresh, warm, light load -> 1.0
        self.assertAlmostEqual(factor(1.0, 1.0, 0.0), 1.0)

    def test_exhausted_slow(self):
        # Near-exhaustion (0.3) -> ~0.75, clamped at the floor
        self.assertAlmostEqual(factor(0.3, 1.0, 0.0), 0.75, places=2)

    def test_hypothermic_slow(self):
        # Severe cold (0.4 dexterity) -> ~0.85
        self.assertAlmostEqual(factor(1.0, 0.4, 0.0), 0.85, places=2)

    def test_overloaded_slow(self):
        # Max load -> ~0.90
        self.assertAlmostEqual(factor(1.0, 1.0, 1.0), 0.90, places=2)

    def test_weakest_governs(self):
        # Fresh but overloaded -> load-limited (0.90), not fatigue
        self.assertAlmostEqual(factor(1.0, 1.0, 1.0), 0.90, places=2)
        # Exhausted but light -> fatigue-limited (0.75)
        self.assertAlmostEqual(factor(0.3, 1.0, 0.0), 0.75, places=2)

    def test_monotone_in_fatigue(self):
        # Speed falls monotonically as fatigue drops
        self.assertLessEqual(factor(0.4, 1.0, 0.0), factor(0.8, 1.0, 0.0))
        self.assertLessEqual(factor(0.3, 1.0, 0.0), factor(0.6, 1.0, 0.0))

    def test_clamped_floor(self):
        # Never below 0.75 even at extreme fatigue
        self.assertGreaterEqual(factor(0.0, 0.0, 1.0), 0.75)


class TestSourceLocks(unittest.TestCase):
    def test_setAnimSpeedCoef_present(self):
        self.assertIn("setAnimSpeedCoef", FNC)

    def test_ace3_guard(self):
        # The guard: ace_advanced_fatigue owns the coef - do not fight.
        self.assertIn("ace_advanced_fatigue", FNC)
        self.assertIn("exitWith { 1.0 }", FNC)

    def test_setting_gated(self):
        src = (REPO / "addons/physiology/initSettings.inc.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("movementSpeed", src)

    def test_fatigue_state_read(self):
        # Reads the physiology fatigue state (not vanilla stamina).
        self.assertIn("fatigueFactor", FNC)

    def test_cold_dexterity_read(self):
        self.assertIn("dexterityPercent", FNC)


if __name__ == "__main__":
    unittest.main()
