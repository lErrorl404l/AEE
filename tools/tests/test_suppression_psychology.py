#!/usr/bin/env python3
"""Combat-stress psychology kernel tests (issue #110).

Executes the shipped SQF kernels through tools/tests/sqf_lite.py, so a test
failure is a source failure, not a mirror drift.  The source-contract methods
pin the issue's UNSOURCED constants so a silent edit fails here.

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
    def test_full_suppression_is_max_stress(self):
        self.assertAlmostEqual(stress(1.0, 0.0, 0.0), 1.0)

    def test_weights_are_the_issue_spec(self):
        # 0.4 + 0.3*0.5 + 0.3*0.5 = 0.7
        self.assertAlmostEqual(stress(0.4, 0.5, 0.5), 0.7)

    def test_stress_is_clamped_to_one(self):
        self.assertAlmostEqual(stress(1.0, 1.0, 1.0), 1.0)

    def test_zero_inputs_give_zero(self):
        self.assertAlmostEqual(stress(0.0, 0.0, 0.0), 0.0)


class TestCombatMorale(unittest.TestCase):
    def test_full_casualties_halve_morale(self):
        # 1 - 0.5*1 - 0.3*0 = 0.5
        self.assertAlmostEqual(morale(1.0, 0.0, 0.0), 0.5)

    def test_casualty_and_fatigue_combine(self):
        # 1 - 0.5*0.5 - 0.3*1 = 0.45
        self.assertAlmostEqual(morale(0.5, 1.0, 0.0), 0.45)

    def test_morale_floors_at_zero(self):
        # 1 - 0.5 - 0.3 = 0.2
        self.assertAlmostEqual(morale(1.0, 1.0, 0.0), 0.2)

    def test_mission_bonus_raises_morale(self):
        self.assertAlmostEqual(morale(0.5, 0.0, 0.2), 0.95)

    def test_morale_caps_at_one(self):
        self.assertAlmostEqual(morale(0.0, 0.0, 1.0), 1.0)


class TestDecisionMultipliers(unittest.TestCase):
    def test_low_band_is_unity(self):
        self.assertEqual(multipliers(0.3), [1.0, 1.0, 1.0, 1.0])

    def test_mid_band(self):
        self.assertEqual(multipliers(0.5), [0.9, 0.8, 0.7, 0.6])

    def test_high_band(self):
        self.assertEqual(multipliers(0.7), [0.7, 0.5, 0.4, 0.3])

    def test_extreme_band(self):
        self.assertEqual(multipliers(0.9), [0.5, 0.3, 0.2, 0.1])

    def test_band_boundaries(self):
        self.assertEqual(multipliers(0.4), [0.9, 0.8, 0.7, 0.6])
        self.assertEqual(multipliers(0.6), [0.7, 0.5, 0.4, 0.3])
        self.assertEqual(multipliers(0.8), [0.5, 0.3, 0.2, 0.1])


class TestEffectiveSpotting(unittest.TestCase):
    def test_product(self):
        self.assertAlmostEqual(effective_spotting(0.8, 0.4), 0.32)

    def test_full_skills_are_unchanged(self):
        self.assertAlmostEqual(effective_spotting(1.0, 1.0), 1.0)


class TestMoraleAction(unittest.TestCase):
    def test_high_morale_holds(self):
        self.assertEqual(gate(0.9, 0.5), 0)

    def test_low_morale_breaks(self):
        self.assertEqual(gate(0.2, 0.0), 2)

    def test_mid_morale_seeks_cover(self):
        self.assertEqual(gate(0.25, 0.5), 1)

    def test_high_courage_holds_the_line(self):
        # morale 0.16, courage 1.0: effective 0.16 + 0.5*0.2 = 0.26 -> cover
        self.assertEqual(gate(0.16, 1.0), 1)
        # morale 0.16, courage 0.0: effective 0.16 - 0.1 = 0.06 -> break
        self.assertEqual(gate(0.16, 0.0), 2)

    def test_break_boundary(self):
        # morale 0.15 at courage 0.5 is exactly the break threshold: not below
        self.assertEqual(gate(0.15, 0.5), 1)


class TestSourceContract(unittest.TestCase):
    """The issue's UNSOURCED constants stay pinned in the source."""

    def test_stress_weights(self):
        text = STRESS.read_text(encoding="utf-8")
        self.assertIn("_W_FATIGUE = 0.3", text)
        self.assertIn("_W_CASUALTY = 0.3", text)

    def test_morale_weights(self):
        text = MORALE.read_text(encoding="utf-8")
        self.assertIn("_W_CASUALTY = 0.5", text)
        self.assertIn("_W_FATIGUE = 0.3", text)

    def test_multiplier_table(self):
        text = MULT.read_text(encoding="utf-8")
        for row in (
            "[1.0, 1.0, 1.0, 1.0]",
            "[0.9, 0.8, 0.7, 0.6]",
            "[0.7, 0.5, 0.4, 0.3]",
            "[0.5, 0.3, 0.2, 0.1]",
        ):
            self.assertIn(row, text)

    def test_gate_thresholds(self):
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("_COVER_MORALE = 0.30", text)
        self.assertIn("_BREAK_MORALE = 0.15", text)
        self.assertIn("_COURAGE_WEIGHT = 0.2", text)


if __name__ == "__main__":
    unittest.main()
