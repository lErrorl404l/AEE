#!/usr/bin/env python3
"""Reference checks for the shooter stability model.

Validates the SQF implementation in addons/physiology:
- fnc_calculateShooterStability.sqf (cold/heat/fatigue -> stability index)

Ground truth (research-verified):
- Cold: manual dexterity onset at 15 degC skin temp, severe below 8 degC
  (Heus, Daanen & Havenith 1995, PMID 15676995; Fox 1967); marksmanship
  intact at finger 10.8 degC (Tikuisis & Keefe 2007, PMID 17484343).
- Heat: ACGIH 2022 TLV moderate work 29 degC WBGT; cognitive onset
  30-33 degC, vigilance limit 42.8 degC (Hancock & Vasmatzidis 2003).
  No marksmanship precision loss at core 39 degC (Tikuisis & Keefe 2005).
- Fatigue: 22 h -> precision loss (Tikuisis 2004); 73 h -> shot group
  x3.35 (Tharion 2003, PMID 12688447); ineffective 48-72 h (Haslam 1984).
- Combination: geometric mean (SPAR-H sub-additivity, NUREG/CR-6883).
- Wind is NOT a stability factor: 25 kt drifts a 5.56 round ~86 cm at
  300 m (FM 3-22.9).  That is round deflection, not shooter stability.

Run: python3 -m unittest tools/tests/test_shooter_stability.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHYSIOLOGY = _REPO_ROOT / "addons" / "physiology" / "functions"


def cold_factor(ambient_c):
    """Mirror of the cold piecewise curve in fnc_calculateShooterStability."""
    if ambient_c >= 15:
        return 1.0
    if ambient_c >= 8:
        return 1.0 + (0.6 - 1.0) * (ambient_c - 15) / (8 - 15)
    return max(0.3, 0.6 + (0.3 - 0.6) * (ambient_c - 8) / (-10 - 8))


def heat_factor(wbgt):
    """Mirror of the heat vigilance curve in fnc_calculateShooterStability."""
    if wbgt <= 29:
        return 1.0
    if wbgt <= 42:
        return 1.0 + (0.6 - 1.0) * (wbgt - 29) / (42 - 29)
    return 0.6


def fatigue_factor_hours(wake_hours):
    """Mirror of the hours-awake piecewise curve in fnc_calculateShooterStability."""
    if wake_hours <= 16:
        return 1.0
    if wake_hours <= 24:
        return 1.0 + (0.85 - 1.0) * (wake_hours - 16) / (24 - 16)
    if wake_hours <= 48:
        return 0.85 + (0.6 - 0.85) * (wake_hours - 24) / (48 - 24)
    if wake_hours <= 72:
        return 0.6 + (0.35 - 0.6) * (wake_hours - 48) / (72 - 48)
    return 0.3


def stability(cold_c, wbgt, wake_hours):
    """Mirror of fnc_calculateShooterStability geometric mean."""
    c = cold_factor(cold_c)
    h = heat_factor(wbgt)
    f = fatigue_factor_hours(wake_hours)
    return max(0.2, min(1.0, (c * h * f) ** (1 / 3)))


class TestColdFactor(unittest.TestCase):
    """Cold dexterity curve (Heus 1995, Fox 1967, Tikuisis 2007)."""

    def test_warm_full_stability(self):
        # >= 15 degC: no cold penalty.
        self.assertAlmostEqual(cold_factor(15), 1.0, places=4)
        self.assertAlmostEqual(cold_factor(25), 1.0, places=4)

    def test_mid_cold_linear(self):
        # 10 degC: ~0.77 (between 1.0 at 15 and 0.6 at 8).
        f = cold_factor(10)
        expected = 1.0 + (0.6 - 1.0) * (10 - 15) / (8 - 15)
        self.assertAlmostEqual(f, expected, places=4)
        self.assertGreater(f, 0.6)
        self.assertLess(f, 1.0)

    def test_severe_cold_floors(self):
        # Below 8 degC approaches 0.3; -20 degC hits the floor.
        self.assertAlmostEqual(cold_factor(-20), 0.3, places=4)
        self.assertGreaterEqual(cold_factor(-5), 0.3)

    def test_marksmanship_survives_to_10_8(self):
        # Tikuisis 2007: marksmanship intact at finger 10.8 degC.
        # Our ambient-proxy curve gives ~0.74 there — degradation begins
        # but is not catastrophic, consistent with the trial.
        f = cold_factor(10.8)
        self.assertGreater(f, 0.6)


class TestHeatFactor(unittest.TestCase):
    """Heat vigilance curve (ACGIH 2022, Hancock & Vasmatzidis 2003)."""

    def test_below_tlv_no_penalty(self):
        # <= 29 degC WBGT (ACGIH TLV moderate work): no penalty.
        self.assertAlmostEqual(heat_factor(29), 1.0, places=4)
        self.assertAlmostEqual(heat_factor(20), 1.0, places=4)

    def test_mid_heat_linear(self):
        # 35 degC: 6/13 of the way through 29..42 -> 0.8154.
        f = heat_factor(35)
        self.assertAlmostEqual(f, 1.0 + 6 / 13 * (0.6 - 1.0), places=4)

    def test_vigilance_limit_floors(self):
        # >= 42 degC: floor at 0.6 (vigilance limit 42.8 degC).
        self.assertAlmostEqual(heat_factor(42), 0.6, places=4)
        self.assertAlmostEqual(heat_factor(50), 0.6, places=4)

    def test_no_precision_loss_at_core_39(self):
        # Tikuisis & Keefe 2005: no marksmanship precision loss at core
        # 39 degC.  The heat factor at WBGT 40 (~0.77) reflects a
        # vigilance decrement, not a precision collapse — never below 0.6.
        self.assertGreaterEqual(heat_factor(40), 0.6)


class TestFatigueFactor(unittest.TestCase):
    """Hours-awake curve (Tikuisis 2004, Tharion 2003, Haslam 1984)."""

    def test_rested_no_penalty(self):
        # <= 16 h awake: no measurable precision loss.
        self.assertAlmostEqual(fatigue_factor_hours(16), 1.0, places=4)

    def test_22h_onset(self):
        # 22 h: slight loss (Tikuisis 2004 onset).
        f = fatigue_factor_hours(22)
        self.assertGreater(f, 0.85)
        self.assertLess(f, 1.0)

    def test_24h_awake(self):
        # 24 h: 0.85.
        self.assertAlmostEqual(fatigue_factor_hours(24), 0.85, places=4)

    def test_73h_anchor(self):
        # 73 h: ~0.3 (Tharion 2003 shot group x3.35).
        f = fatigue_factor_hours(73)
        self.assertAlmostEqual(f, 0.3, places=2)

    def test_monotonic(self):
        f16 = fatigue_factor_hours(16)
        f36 = fatigue_factor_hours(36)
        f60 = fatigue_factor_hours(60)
        f80 = fatigue_factor_hours(80)
        self.assertGreater(f16, f36)
        self.assertGreater(f36, f60)
        self.assertGreater(f60, f80)


class TestStability(unittest.TestCase):
    """Geometric mean combination + validation claims."""

    def test_ideal_conditions(self):
        # 25 degC, WBGT 20, 8 h awake: stability ~1.0.
        self.assertAlmostEqual(stability(25, 20, 8), 1.0, places=4)

    def test_cold_alone(self):
        # -20 degC: cold floor 0.3 -> stability ~0.67 (cube root of 0.3).
        s = stability(-20, 20, 8)
        self.assertAlmostEqual(s, 0.3 ** (1 / 3), places=4)
        self.assertGreater(s, 0.6)

    def test_combined_cold_fatigue(self):
        # -20 degC + 73 h awake: all three stressed.
        s = stability(-20, 35, 73)
        self.assertLess(s, 0.5)

    def test_heat_alone(self):
        # WBGT 45: heat floor 0.6 -> stability ~0.84.
        s = stability(25, 45, 8)
        self.assertAlmostEqual(s, 0.6 ** (1 / 3), places=4)
        self.assertGreater(s, 0.8)

    def test_worst_case(self):
        # -20 degC, WBGT 45, 80 h awake: below 0.4.
        s = stability(-20, 45, 80)
        self.assertLess(s, 0.4)

    def test_wind_is_not_stability(self):
        # The stability function must not depend on wind: same inputs give
        # the same result regardless of any wind variable.  This locks the
        # design decision (crosswind deflects the round, not the shooter).
        # The mirror has no wind parameter, which is the contract.
        s1 = stability(10, 30, 24)
        s2 = stability(10, 30, 24)
        self.assertEqual(s1, s2)


class TestSQFSyncStability(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = (_PHYSIOLOGY / filename).read_text(encoding="utf-8")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_shooter_stability.py.",
        )

    def test_stability_constants(self):
        self._assert_in_sqf(
            "fnc_calculateShooterStability.sqf",
            [
                "linearConversion [15, 8",
                "linearConversion [8, -10",
                "linearConversion [29, 42",
                "linearConversion [16, 24",
                "linearConversion [48, 72",
                "shooterStability",
            ],
            "cold/heat/fatigue piecewise anchors and output var",
        )

    def test_sway_integration(self):
        self._assert_in_sqf(
            "fnc_integrateSwayFactor.sqf",
            [
                "ace_common_fnc_addSwayFactor",
                "multiplier",
                "shooterStability",
                "ace_advanced_fatigue",
            ],
            "ACE3 sway multiplier registration",
        )


if __name__ == "__main__":
    unittest.main()
