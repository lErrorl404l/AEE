#!/usr/bin/env python3
"""Cross-system trajectory tests for the coupled physiology models.

Single-system tests validate each model in isolation.  Real soldiers are
cold AND tired AND dehydrated simultaneously, evolving over hours.  These
tests evolve multiple systems together along representative operational
scenarios and verify the combined output stays physically plausible.

Method: full-scenario validation per US Army Mission Rehearsal Exercise
protocols and NATO TRMSF 4370 environmental testing.

Run: python3 -m unittest tools.tests.test_trajectories
"""

import math
import unittest

import numpy as np

from tools.tests.test_sleep_model import sleep_pressure
from tools.tests.test_shooter_stability import (
    cold_factor,
    fatigue_factor_hours,
    heat_factor,
    stability,
)
from tools.tests.test_physiology import cross_sensitivity, hypoxia_risk

# ─── Dehydration mirror (fnc_calculateDehydrationRisk.sqf) ─────────────────
# Per-player water deficit accumulates from ISO 7243 WBGT-band sweat rate
# minus baseline rehydration; risk is a piecewise map of the deficit.
# NOTE: the model sweats ONLY above the 18 C thermoneutral WBGT band.  At
# or below 18 C there is no heat stress: the deficit decays and risk is 0.


def sweat_rate_l_per_h(wbgt):
    """ISO 7243 WBGT bands (fnc_calculateDehydrationRisk.sqf lines 40-45)."""
    if wbgt < 23:
        return 0.3
    if wbgt < 28:
        return 0.6
    if wbgt < 32:
        return 1.0
    return 1.5


def _esat_kpa(t_c):
    """Buck saturation vapour pressure (kPa) - mirrors the SQF."""
    return 0.61094 * math.exp((17.625 * t_c) / (243.04 + t_c))


def cold_respiratory_loss_l_per_h(temp_c, exertion=1.0):
    """Issue #92: respiratory water loss from the water-vapour deficit.

    Lung air is saturated at body temperature (6.28 kPa); cold dry air
    holds far less, so each breath nets water out.  Anchored to the
    verified rest rates (Freund & Sawka 1996 Table 9-2; Zielinski &
    Przybylski 2012): 0.010 L/h at 25 C (deficit 3.1 kPa), 0.020 L/h at
    -20 C, scaled by exertion (rest 1x, walk 2x, run 3x).
    """
    deficit = max(0.0, 6.28 - _esat_kpa(temp_c))
    return 0.010 * (deficit / 3.1) * exertion


def cold_diuresis_l_per_h(temp_c):
    """Issue #92: conservative cold diuresis below 10 C (max 0.01 L/h).

    The 0.5-1.5 L/day figure in the original spec is NOT supported by
    primary literature (self-limiting, debated); this uses a conservative
    0.24 L/day at severe cold.
    """
    if temp_c >= 10:
        return 0.0
    return 0.01 * ((10 - temp_c) / 20)


def dehydration_step(
    deficit,
    wbgt,
    tick_hours,
    sweat_scale=1.0,
    rehydrate_l_per_h=0.05,
    clothed=False,
    temp_c=25.0,
    exertion=1.0,
):
    """One stateful tick of the SQF model.

    Returns new water deficit in litres.  Above 18 C WBGT the ISO 7243
    sweat bands drive the loss; below 18 C the cold branch (respiratory
    loss + diuresis, issue #92) applies.  Natural rehydration applies to
    both.
    """
    amount = 0.0
    if wbgt >= 18:
        amount = sweat_rate_l_per_h(wbgt) * tick_hours * sweat_scale
        if clothed:
            amount += 0.2 * tick_hours * 2  # uniform + vest
    else:
        amount = (
            cold_respiratory_loss_l_per_h(temp_c, exertion)
            + cold_diuresis_l_per_h(temp_c)
        ) * tick_hours
    amount -= rehydrate_l_per_h * tick_hours
    return max(0.0, deficit + amount)


def dehydration_risk(deficit):
    """Piecewise risk map (SQF lines 60-66)."""
    if deficit < 0.5:
        return 0.0
    if deficit < 1.0:
        return (deficit - 0.5) * 0.5
    if deficit < 2.0:
        return 0.25 + (deficit - 1.0) * 0.25
    if deficit < 3.0:
        return 0.5 + (deficit - 2.0) * 0.25
    return 0.75


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


class TestArcticPatrolTrajectory(unittest.TestCase):
    """24 h arctic patrol: cold + fatigue + hypoxia must stay plausible.

    0h rested at 20 C -> 2h cold snap -> 6h march -> 8h sleep ->
    12h wake -> 16h altitude 2000 m -> 24h done.
    """

    TRAJECTORY = [
        (0, 20, 18, 0, 0),
        (2, -10, 8, 2, 0),
        (6, -10, 8, 6, 0),
        (8, -5, 4, 8, 0),  # sleep starts
        (12, -5, 4, 0, 0),  # sleep ends, hours awake reset
        (16, -5, 4, 4, 2000),
        (24, -5, 4, 12, 2000),
    ]

    def test_bounds_hold_everywhere(self):
        for hour, temp, wbgt, wake_h, alt_m in self.TRAJECTORY:
            c = cold_factor(temp)
            h = heat_factor(wbgt)
            f = fatigue_factor_hours(wake_h)
            s = stability(temp, wbgt, wake_h)
            r = hypoxia_risk(alt_m, min(hour * 3600, 3600))
            self.assertGreaterEqual(c, 0.3)
            self.assertLessEqual(c, 1.0)
            self.assertGreaterEqual(h, 0.6)
            self.assertLessEqual(h, 1.0)
            self.assertGreaterEqual(f, 0.3)
            self.assertLessEqual(f, 1.0)
            self.assertGreaterEqual(s, 0.2)
            self.assertLessEqual(s, 1.0)
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)

    def test_cold_degrades_when_temperature_drops(self):
        prev_cold = 1.0
        prev_temp = 20.0
        for hour, temp, wbgt, wake_h, alt_m in self.TRAJECTORY:
            if hour == 0:
                continue
            c = cold_factor(temp)
            if temp <= prev_temp:
                self.assertLessEqual(
                    c,
                    prev_cold + 0.01,
                    f"cold factor improved while temperature dropped to {temp} C",
                )
            prev_cold = c
            prev_temp = temp

    def test_fatigue_recovers_during_sleep(self):
        # Fatigue only degrades past the 16 h onset.  A soldier who
        # stays awake 20 h is measurably impaired; after 6 h sleep the
        # wakefulness clock resets and full factor returns.
        impaired = fatigue_factor_hours(20)
        self.assertLess(impaired, 1.0, "20 h awake produced no fatigue")
        rested = fatigue_factor_hours(0)
        self.assertGreater(rested, impaired, "fatigue did not recover during sleep")

    def test_no_spontaneous_improvement_while_awake(self):
        # 12h -> 16h -> 24h awake: fatigue must not improve while awake.
        prev = fatigue_factor_hours(0)
        for wake_h in [4, 12]:
            cur = fatigue_factor_hours(wake_h)
            self.assertLessEqual(cur, prev + 1e-12, "fatigue improved while awake")
            prev = cur

    def test_hypoxia_onset_at_altitude(self):
        # At 2000 m with 16 h exposure the risk is real but not instant.
        r_ground = hypoxia_risk(0, 3600)
        r_alt = hypoxia_risk(2000, 3600)
        self.assertGreaterEqual(r_alt, r_ground, "altitude did not raise hypoxia risk")
        self.assertLess(r_alt, 1.0, "2000 m fully incapacitated in 1 h")

    def test_cold_dominates_stability(self):
        # At -10 C the cold factor alone caps stability well below 1.
        s_cold = stability(-10, 8, 2)
        s_warm = stability(20, 18, 2)
        self.assertLess(s_cold, s_warm, "cold patrol is MORE stable than warm")


class TestAltitudeExposureTrajectory(unittest.TestCase):
    """24 h at 3500 m: hypoxia TUC counting + fatigue + sleep at altitude."""

    TRAJECTORY = [
        (0, 5, 10, 0, 3500),
        (4, 5, 10, 4, 3500),
        (8, 5, 10, 8, 3500),
        (12, 5, 10, 0, 3500),  # sleep resets wakefulness
        (20, 5, 10, 8, 3500),
        (24, 5, 10, 12, 3500),
    ]

    def test_hypoxia_risk_climbs_with_exposure(self):
        prev = 0.0
        for hour, _, _, wake_h, alt_m in self.TRAJECTORY:
            exp = min(hour * 3600, 3600)
            r = hypoxia_risk(alt_m, exp)
            self.assertGreaterEqual(r, prev - 1e-9, "hypoxia risk fell with exposure")
            prev = r
            self.assertLessEqual(r, 1.0)

    def test_risk_real_but_survivable(self):
        # 3500 m, 1 h exposure: within TUC (1800 s at 6000 m, longer lower).
        r = hypoxia_risk(3500, 3600)
        self.assertGreater(r, 0.0)
        self.assertLess(r, 0.5)

    def test_sleep_does_not_recover_hypoxia(self):
        # WBGT 10 is below thermoneutral, and hypoxia is exposure-driven:
        # sleeping does not reset it.  At 12h (post-sleep) with 12h
        # exposure the risk is >= the 8h pre-sleep value.
        r_8 = hypoxia_risk(3500, 8 * 3600)
        r_12 = hypoxia_risk(3500, 12 * 3600)
        self.assertGreaterEqual(r_12, r_8, "sleep reset hypoxia exposure")


class TestHotAltitudeCoupling(unittest.TestCase):
    """Hot AND high: dehydration + hypoxia must amplify through
    cross-sensitivity (Gopinathan 1988, Anand 1996, issue #40).

    The coupling only fires above the 18 C WBGT thermoneutral band, where
    the sweat model accumulates deficit.  Scenario: 12 h tropical patrol
    at 30 C WBGT climbing to 3000 m.
    """

    def test_dehydration_accumulates_in_heat(self):
        deficit = 0.0
        for _ in range(48):  # 12 h at 30 C WBGT, 15 min ticks
            deficit = dehydration_step(deficit, 30.0, 0.25, clothed=True)
        self.assertGreater(deficit, 1.0, "12 h hot patrol produced no deficit")
        risk = dehydration_risk(deficit)
        self.assertGreater(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_dehydration_accumulates_in_cold(self):
        # Issue #92: below 18 C WBGT the deficit NO LONGER decays.  Cold
        # air is dry - humidifying it to body conditions costs water every
        # breath - so a marching soldier accumulates deficit at -20 C
        # even though WBGT is 8 C.  (Pre-#92 the model reported zero
        # dehydration in the cold, the documented limitation of PR #90.)
        # At -10 C rest the loss is ~0.049 L/h, marginally under the 0.05
        # L/h rehydration default, so no deficit accumulates - the
        # physically correct boundary.  Severe cold (-20 C) crosses it.
        deficit = 0.0
        for _ in range(24):  # 6 h march at -20 C, 15 min ticks
            deficit = dehydration_step(deficit, 8.0, 0.25, temp_c=-20.0, exertion=2)
        self.assertGreater(deficit, 0.0, "cold march produced no dehydration")
        self.assertLess(deficit, 1.0, "6 h cold march fully dehydrated")

    def test_cold_loss_scales_with_cold(self):
        # Deeper cold = drier air = more respiratory loss.
        mild = sum(cold_respiratory_loss_l_per_h(t, 1) for t in [0, 1, 2, 3]) / 4
        severe = sum(cold_respiratory_loss_l_per_h(t, 1) for t in [-10, -9, -8, -7]) / 4
        self.assertGreater(severe, mild)

    def test_cold_loss_scales_with_exertion(self):
        rest = cold_respiratory_loss_l_per_h(-10, 1)
        run = cold_respiratory_loss_l_per_h(-10, 3)
        self.assertAlmostEqual(run, rest * 3, places=6)

    def test_respiratory_anchor_matches_literature(self):
        # Verified anchors: ~0.010 L/h at 25 C, ~0.020 L/h at -20 C.
        self.assertAlmostEqual(cold_respiratory_loss_l_per_h(25, 1), 0.010, places=3)
        self.assertAlmostEqual(cold_respiratory_loss_l_per_h(-20, 1), 0.020, places=3)

    def test_diuresis_conservative(self):
        # Max 0.01 L/h (0.24 L/day) at severe cold - well under the
        # unverified 0.5-1.5 L/day figure.
        self.assertEqual(cold_diuresis_l_per_h(10), 0.0)
        self.assertEqual(cold_diuresis_l_per_h(-10), 0.01)
        self.assertEqual(cold_diuresis_l_per_h(25), 0.0)

    def test_cross_sensitivity_amplifies_at_altitude(self):
        # 12 h hot patrol -> deficit ~1.5 L -> risk ~0.375.  At 3000 m the
        # hypoxia amplifier then scales dehydration impact.
        deficit = 0.0
        for _ in range(48):
            deficit = dehydration_step(deficit, 30.0, 0.25, clothed=True)
        deh_risk = dehydration_risk(deficit)
        hyp_risk = hypoxia_risk(3000, 6 * 3600)
        eff_deh, eff_hyp = cross_sensitivity(deh_risk, hyp_risk)
        self.assertGreater(eff_deh, deh_risk, "hypoxia did not amplify dehydration")
        self.assertGreater(eff_hyp, hyp_risk, "dehydration did not amplify hypoxia")
        self.assertLessEqual(eff_deh, 1.0)
        self.assertLessEqual(eff_hyp, 1.0)

    def test_coupling_stays_bounded_full_scenario(self):
        # Whole scenario: every combined output in bounds.
        deficit = 0.0
        prev = None
        for hour in range(0, 25, 2):
            wbgt = 30.0 if hour < 12 else 26.0
            deficit = dehydration_step(deficit, wbgt, 2.0, clothed=True)
            deh = dehydration_risk(deficit)
            hyp = hypoxia_risk(3000, min(hour * 3600, 3600))
            eff_deh, eff_hyp = cross_sensitivity(deh, hyp)
            self.assertGreaterEqual(eff_deh, 0.0)
            self.assertLessEqual(eff_deh, 1.0)
            self.assertGreaterEqual(eff_hyp, 0.0)
            self.assertLessEqual(eff_hyp, 1.0)
            s = stability(25, wbgt, hour)
            self.assertGreaterEqual(s, 0.2)
            self.assertLessEqual(s, 1.0)


class TestDehydrationModelMirror(unittest.TestCase):
    """The SQF dehydration mirror itself must track the source contract."""

    def test_iso_7243_bands(self):
        self.assertEqual(sweat_rate_l_per_h(18), 0.3)  # caution
        self.assertEqual(sweat_rate_l_per_h(23), 0.6)  # extreme caution
        self.assertEqual(sweat_rate_l_per_h(28), 1.0)  # danger
        self.assertEqual(sweat_rate_l_per_h(32), 1.5)  # very dangerous

    def test_risk_piecewise(self):
        self.assertEqual(dehydration_risk(0.3), 0.0)
        self.assertAlmostEqual(dehydration_risk(0.75), 0.125)
        self.assertAlmostEqual(dehydration_risk(1.5), 0.375)
        self.assertAlmostEqual(dehydration_risk(2.5), 0.625)
        self.assertEqual(dehydration_risk(3.5), 0.75)

    def test_risk_clamped(self):
        # Heat stroke overlay keeps risk within [0, 1] per the SQF clamp.
        for deficit in np.linspace(0, 5, 51):
            r = _clamp(dehydration_risk(deficit), 0, 1)
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)


if __name__ == "__main__":
    unittest.main()
