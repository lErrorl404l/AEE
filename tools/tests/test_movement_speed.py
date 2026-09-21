#!/usr/bin/env python3
"""Stamina-to-animation coupling tests (issue #212).

Locks the movement-speed coupling physics in
fnc_applyMovementSpeed.sqf: fatigue/cold/load map to a speed
coefficient (0.75..1.0), the weakest factor governs, and the ACE3
advanced-fatigue guard prevents conflict.

The cold factor is a HAND function (issue #119): the hand feels its own
wind chill insulated by the handwear (Gonzalez 1998: light 0.86, heavy
1.05, mitten 1.46 clo), loses dexterity with cold-exposure duration
(Daanen 2009: manual loss = 0.162 x WCET x exposure^0.38) and pays a
glove-thickness penalty even in warmth (Bensel 1993: test time rises
linearly with thickness, grip anchor -31 % at 3.1 mm).  The load is the
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


def hand_wct(air_temp, wct, glove_clo):
    """Mirror of the hand-temperature correction: the hand feels the
    wind chill insulated by the handwear clo."""
    return air_temp + (wct - air_temp) * math.exp(-glove_clo)


def daanen_loss(hand_t, exposure_sec):
    """Mirror of the Daanen 2009 manual dexterity loss:
    0.162 x WCET x exposure_min^0.38 (Ind Health 47:262)."""
    exp_min = exposure_sec / 60.0
    return 0.162 * max(0.0, -hand_t) * (exp_min**0.38)


def bensel_loss(glove_clo):
    """Mirror of the Bensel 1993 glove-thickness penalty: thickness mm
    maps from the handwear clo (light ~1 mm, mitten ~3.5 mm), and each
    mm costs ~10 % dexterity (the -31 % at 3.1 mm grip anchor)."""
    if glove_clo <= 0.1:
        return 0.0
    thickness = 1.0 + (glove_clo - 0.86) * (3.5 - 1.0) / (1.46 - 0.86)
    return thickness * 10.0


def dexterity(air_temp, wct, glove_clo, exposure_sec):
    """Mirror of the SQF: Heus 1995 curve on the hand temperature,
    minus the Daanen cold-exposure loss and the Bensel glove penalty,
    clamped 10..100."""
    h = hand_wct(air_temp, wct, glove_clo)
    return max(
        10.0,
        min(
            100.0,
            90.0 + 2.0 * h - daanen_loss(h, exposure_sec) - bensel_loss(glove_clo),
        ),
    )


def factor(fatigue, air_temp, wct, glove_clo, load_kg, exposure_sec=600):
    """Mirror of the SQF: each maps to a speed, the weakest governs,
    clamped to 0.75..1.0."""
    fs = 0.75 + (1.0 - 0.75) * (fatigue - 0.3) / 0.7
    dex = dexterity(air_temp, wct, glove_clo, exposure_sec)
    cs = 0.85 + (1.0 - 0.85) * (dex - 10.0) / 90.0
    ls = 1.0 + (0.85 - 1.0) * (max(15.0, min(45.0, load_kg)) - 15.0) / 30.0
    fs = max(0.75, min(1.0, fs))
    cs = max(0.85, min(1.0, cs))
    ls = max(0.85, min(1.0, ls))
    return max(0.75, min(1.0, min(fs, cs, ls)))


class TestSpeedCoupling(unittest.TestCase):
    def test_fresh_full_speed(self):
        # Fresh, warm (WCT = air temp), light load -> 1.0
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.86, 10.0), 1.0, places=3)

    def test_exhausted_slow(self):
        # Near-exhaustion (0.3) -> ~0.75, clamped at the floor
        self.assertAlmostEqual(factor(0.3, 15.0, 15.0, 0.86, 10.0), 0.75, places=2)

    def test_severe_cold_slow(self):
        # Air -40, WCT -60, no gloves, 30 min exposure: dexterity hits
        # the 10 floor -> ~0.85.
        self.assertAlmostEqual(
            factor(1.0, -40.0, -60.0, 0.0, 10.0, 1800), 0.85, places=2
        )

    def test_overloaded_slow(self):
        # 45 kg combat load -> ~0.85
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.86, 45.0), 0.85, places=2)

    def test_weakest_governs(self):
        # Fresh but overloaded -> load-limited (0.85), not fatigue
        self.assertAlmostEqual(factor(1.0, 15.0, 15.0, 0.86, 45.0), 0.85, places=2)
        # Exhausted but light -> fatigue-limited (0.75)
        self.assertAlmostEqual(factor(0.3, 15.0, 15.0, 0.86, 10.0), 0.75, places=2)

    def test_monotone_in_fatigue(self):
        # Speed falls monotonically as fatigue drops
        self.assertLessEqual(
            factor(0.4, 15.0, 15.0, 0.86, 10.0), factor(0.8, 15.0, 15.0, 0.86, 10.0)
        )
        self.assertLessEqual(
            factor(0.3, 15.0, 15.0, 0.86, 10.0), factor(0.6, 15.0, 15.0, 0.86, 10.0)
        )

    def test_clamped_floor(self):
        # Never below 0.75 even at extreme fatigue + cold + load
        self.assertGreaterEqual(factor(0.0, -40.0, -60.0, 0.0, 50.0, 3600), 0.75)


class TestGlovePhysics(unittest.TestCase):
    """The issue #119 hand-dexterity physics: Daanen exposure loss,
    Bensel thickness penalty, Gonzalez handwear clo."""

    def test_gloves_help_in_cold(self):
        # Air -20, WCT -35, 30 min: a LIGHT glove (0.86 clo) keeps more
        # dexterity than a bare hand.  (At severe cold the bare hand
        # numbs to the 10 floor; the light glove stays workable.)
        naked = factor(1.0, -20.0, -35.0, 0.0, 10.0, 1800)
        light = factor(1.0, -20.0, -35.0, 0.86, 10.0, 1800)
        self.assertGreater(light, naked)

    def test_exposure_worsens_dexterity(self):
        # The Daanen duration term: longer cold exposure loses more
        # dexterity (sub-linear, ^0.38).  Mild cold so neither hits
        # the floor.
        d10 = dexterity(-10.0, -20.0, 0.0, 600)
        d60 = dexterity(-10.0, -20.0, 0.0, 3600)
        self.assertGreater(d10, d60)

    def test_bensel_penalty_even_warm(self):
        # Even in warmth, a mitten costs dexterity vs a light glove.
        bare = dexterity(15.0, 15.0, 0.0, 0)
        mitt = dexterity(15.0, 15.0, 1.46, 0)
        self.assertGreater(bare, mitt)

    def test_hand_wct_moves_toward_air(self):
        # Mitten recovers ~77 % of the deficit; bare feels the full WCT.
        self.assertAlmostEqual(hand_wct(-20.0, -35.0, 1.46), -23.48, delta=0.05)
        self.assertAlmostEqual(hand_wct(-20.0, -35.0, 0.0), -35.0, delta=0.01)

    def test_daanen_equation_value(self):
        # Daanen 2009 manual: 0.162 x 20 x (30 min)^0.38 = ~11.8 points.
        self.assertAlmostEqual(daanen_loss(-20.0, 1800), 11.8, delta=0.5)

    def test_bensel_grip_anchor(self):
        # The SQF maps mitten clo 1.46 -> 3.5 mm -> ~35 % penalty
        # (the -31 % at 3.1 mm grip anchor).  A light glove (1 mm) is
        # ~10 %.
        self.assertAlmostEqual(bensel_loss(1.46), 35.0, delta=1.0)
        self.assertGreater(bensel_loss(1.46), bensel_loss(0.86))


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
        # The issue #119 library provides the kg load.
        self.assertIn("getEquipmentProperties", FNC)
        self.assertIn("_load = _combined select 0", FNC)

    def test_hand_dexterity_physics(self):
        # The per-unit cold factor is a HAND function: glove-insulated
        # hand temperature, Daanen exposure loss, Bensel thickness
        # penalty, 0..100 dexterity scale.
        self.assertIn("getGloveProperties", FNC)
        self.assertIn("_handWct", FNC)
        self.assertIn("coldExposureSec", FNC)
        self.assertIn("_daanenLoss", FNC)
        self.assertIn("_benselLoss", FNC)
        self.assertIn("[10.0, 100.0", FNC)


if __name__ == "__main__":
    unittest.main()
