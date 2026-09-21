#!/usr/bin/env python3
"""Stamina-to-animation coupling tests (issue #212).

Locks the movement-speed coupling physics in
fnc_applyMovementSpeed.sqf: fatigue/cold/load map to a speed
coefficient (0.75..1.0), the weakest factor governs, and the ACE3
advanced-fatigue guard prevents conflict.

The cold factor is per-unit: clothing insulation (clo, issue #119)
shifts the felt wind chill toward the air temperature before the
dexterity curve (90 + 2*WCT, Heus 1995) is applied.  The load is the
equipment library's total in kg (15 kg light patrol, 45 kg overloaded).

The maths is a Python mirror verified against the SOURCE text (the
#204 no-drift lesson).
"""

import math
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (
    REPO / "addons/physiology/functions/strain/fnc_applyMovementSpeed.sqf"
).read_text(encoding="utf-8")


def felt_wct(air_temp, wct, clo):
    """Mirror of the insulation correction: the felt wind chill moves
    toward the air temperature exponentially with clo."""
    return air_temp + (wct - air_temp) * math.exp(-clo)


def dexterity_from_wct(wct):
    """Mirror of the Heus 1995 curve (90 + 2*WCT, floor 10)."""
    return max(10.0, 90.0 + 2.0 * wct)


def factor(fatigue, air_temp, wct, clo, load_kg):
    """Mirror of the SQF: each maps to a speed, the weakest governs,
    clamped to 0.75..1.0."""
    fs = 0.75 + (1.0 - 0.75) * (fatigue - 0.3) / 0.7
    dex = dexterity_from_wct(felt_wct(air_temp, wct, clo))
    cs = 0.85 + (1.0 - 0.85) * (dex - 10.0) / 90.0
    ls = 1.0 + (0.85 - 1.0) * (max(15.0, min(45.0, load_kg)) - 15.0) / 30.0
    fs = max(0.75, min(1.0, fs))
    cs = max(0.85, min(1.0, cs))
    ls = max(0.85, min(1.0, ls))
    return max(0.75, min(1.0, min(fs, cs, ls)))


class TestSpeedCoupling(unittest.TestCase):
    def test_fresh_full_speed(self):
        # Fresh, warm (WCT = air temp), light load -> 1.0
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.75, 10.0), 1.0)

    def test_exhausted_slow(self):
        # Near-exhaustion (0.3) -> ~0.75, clamped at the floor
        self.assertAlmostEqual(factor(0.3, 15.0, 15.0, 0.75, 10.0), 0.75, places=2)

    def test_severe_cold_slow(self):
        # Air -40, WCT -60 (exposed): dexterity hits the 10 floor ->
        # ~0.85 even with a light uniform.
        self.assertAlmostEqual(factor(1.0, -40.0, -60.0, 0.75, 10.0), 0.85, places=2)

    def test_overloaded_slow(self):
        # 45 kg combat load -> ~0.85
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.75, 45.0), 0.85, places=2)

    def test_weakest_governs(self):
        # Fresh but overloaded -> load-limited (0.85), not fatigue
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.75, 45.0), 0.85, places=2)
        # Exhausted but light -> fatigue-limited (0.75)
        self.assertAlmostEqual(factor(0.3, 15.0, 15.0, 0.75, 10.0), 0.75, places=2)

    def test_monotone_in_fatigue(self):
        # Speed falls monotonically as fatigue drops
        self.assertLessEqual(
            factor(0.4, 15.0, 15.0, 0.75, 10.0), factor(0.8, 15.0, 15.0, 0.75, 10.0)
        )
        self.assertLessEqual(
            factor(0.3, 15.0, 15.0, 0.75, 10.0), factor(0.6, 15.0, 15.0, 0.75, 10.0)
        )

    def test_clamped_floor(self):
        # Never below 0.75 even at extreme fatigue + cold + load
        self.assertGreaterEqual(factor(0.0, -40.0, -60.0, 0.0, 50.0), 0.75)


class TestCloInsulation(unittest.TestCase):
    """The issue #119 insulation coupling: a winter-parka soldier moves
    better than a shirt-sleeve one in the same cold."""

    def test_insulation_helps_in_cold(self):
        # Air -20, WCT -35: clo 2.5 (parka) must beat clo 0.0 (shirt).
        naked = factor(1.0, -20.0, -35.0, 0.0, 10.0)
        parka = factor(1.0, -20.0, -35.0, 0.75, 10.0)
        self.assertGreater(parka, naked)

    def test_felt_wct_moves_toward_air(self):
        # clo 2.5 recovers ~92 % of the deficit; clo 0.75 ~53 %.
        self.assertAlmostEqual(felt_wct(-20.0, -35.0, 2.5), -21.1, delta=0.2)
        self.assertAlmostEqual(felt_wct(-20.0, -35.0, 0.75), -27.1, delta=0.2)

    def test_no_insulation_full_deficit(self):
        self.assertAlmostEqual(felt_wct(-20.0, -35.0, 0.0), -35.0, delta=0.01)


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

    def test_equipment_library_feeds_load(self):
        # The issue #119 library provides the kg load + clo insulation.
        self.assertIn("getEquipmentProperties", FNC)
        self.assertIn("_clo", FNC)

    def test_cold_uses_felt_wct(self):
        # The per-unit cold factor: insulation-corrected wind chill,
        # dexterity curve, 0..100 published scale.
        self.assertIn("exp (-_clo)", FNC)
        self.assertIn("90 + 2 * _feltWct", FNC)
        self.assertIn("[10.0, 100.0", FNC)


if __name__ == "__main__":
    unittest.main()
