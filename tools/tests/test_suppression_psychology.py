#!/usr/bin/env python3
"""Combat-stress psychology kernel tests (issue #110).

Executes the shipped SQF kernels through tools/tests/sqf_lite.py, so a test
failure is a source failure, not a mirror drift.  The source-contract methods
pin the sourced constants (FM 105-5 1967, Rowland 1986) so a silent edit fails here.

Run: python3 -m unittest tools.tests.test_suppression_psychology -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PSY = ROOT / "addons" / "strain" / "functions" / "psychology"

STRESS = PSY / "fnc_calculateStress.sqf"
MORALE = PSY / "fnc_calculateMorale.sqf"
MULT = PSY / "fnc_getDecisionMultipliers.sqf"
SPOT = PSY / "fnc_calculateEffectiveSpotting.sqf"
GATE = PSY / "fnc_getMoraleAction.sqf"


def stress(suppression, fatigue, casualty):
    return run_sqf(STRESS, [suppression, fatigue, casualty])


def morale(casualty, fatigue, bonus):
    return run_sqf(MORALE, [casualty, fatigue, bonus])


def multipliers(s):
    return run_sqf(MULT, [s])


def effective_spotting(skill, mult):
    return run_sqf(SPOT, [skill, mult])


def gate(m, courage):
    return run_sqf(GATE, [m, courage])


class TestCombatStress(unittest.TestCase):
    def test_stress_is_the_engine_suppression(self):
        self.assertAlmostEqual(stress(0.4, 0.5, 0.5), 0.4)
        self.assertEqual(stress(1.0, 0, 0), 1.0)
        self.assertEqual(stress(0, 0, 0), 0)


class TestMorale(unittest.TestCase):
    def test_forty_percent_casualties_is_the_breakpoint(self):
        # FM 105-5: breaking approaches certainty at ~40 % casualties.
        self.assertAlmostEqual(morale(0.40, 0, 0), 0.0, places=6)

    def test_twenty_percent_is_half(self):
        self.assertAlmostEqual(morale(0.20, 0, 0), 0.5, places=6)

    def test_fatigue_does_not_enter(self):
        self.assertAlmostEqual(morale(0.1, 1.0, 0), morale(0.1, 0.0, 0))

    def test_mission_bonus_and_clamps(self):
        self.assertAlmostEqual(morale(0.2, 0, 0.2), 0.7, places=6)
        self.assertEqual(morale(0, 0, 0.5), 1)
        self.assertEqual(morale(1, 0, 0), 0)


class TestDecisionMultipliers(unittest.TestCase):
    def test_calm_is_unity(self):
        self.assertEqual(multipliers(0), [1, 1, 1, 1])

    def test_full_stress_is_rowland_combat_effectiveness(self):
        # Rowland 1986: 1/7 to 1/10 of the field-trial effectiveness.
        acc = multipliers(1)[1]
        self.assertTrue(1 / 10 <= acc <= 1 / 7, acc)

    def test_linear_in_stress(self):
        self.assertAlmostEqual(multipliers(0.5)[1], 1 - 0.5 * 0.88, places=6)


class TestEffectiveSpotting(unittest.TestCase):
    def test_product(self):
        self.assertAlmostEqual(effective_spotting(0.8, 0.4), 0.32)


class TestMoraleGate(unittest.TestCase):
    def test_low_casualties_hold(self):
        self.assertEqual(gate(morale(0.1, 0, 0), 0.5), 0)

    def test_twenty_percent_halts(self):
        # FM 105-5: an attacker at ~20 % casualties halts.
        self.assertEqual(gate(morale(0.21, 0, 0), 0.5), 1)

    def test_forty_percent_breaks(self):
        self.assertEqual(gate(morale(0.40, 0, 0), 0.5), 2)


class TestSourceContract(unittest.TestCase):
    def test_constants_are_cited(self):
        self.assertIn("FM 105-5", MORALE.read_text(encoding="utf-8"))
        self.assertIn("_BREAK_CASUALTIES = 0.40", MORALE.read_text(encoding="utf-8"))
        self.assertIn("Rowland (1986)", MULT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
