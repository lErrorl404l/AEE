#!/usr/bin/env python3
"""Survival pressure model tests (issue #75, the will to live).

Executes the real SQF kernels through tools/tests/sqf_lite.py, so a band-edge
failure is a source failure, not a mirror drift.  The source-contract methods
read the engine wiring, which the harness cannot execute: the reader reads
EGVAR, which the harness does not resolve.

Run: python3 -m unittest tools.tests.test_ai_survival -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PH = ROOT / "addons" / "physiology" / "functions" / "state"
AI = ROOT / "addons" / "ai" / "functions"

COLD = PH / "fnc_coldStress.sqf"
HEAT = PH / "fnc_heatStress.sqf"
PRESSURE = PH / "fnc_survivalPressure.sqf"
STATE = PH / "fnc_survivalState.sqf"
ACTION = AI / "fnc_survivalAction.sqf"
NEED = AI / "fnc_survivalNeed.sqf"


def cold(wct):
    return run_sqf(COLD, [wct])


def heat(wbgt):
    return run_sqf(HEAT, [wbgt])


def pressure(*risks):
    return run_sqf(PRESSURE, list(risks))


def action(p):
    return run_sqf(ACTION, [p])


class TestColdStressBands(unittest.TestCase):
    """TB MED 508 wind-chill anchors: -28 = 0.3, -40 = 0.6, -48 = 0.8,
    -55 = 1.0, and 0 at the top of the low band (-10 C)."""

    def test_no_risk_at_or_above_the_low_band(self):
        for wct in (15, 0, -9, -10):
            with self.subTest(wct=wct):
                self.assertAlmostEqual(cold(wct), 0.0, places=4)

    def test_the_anchors(self):
        self.assertAlmostEqual(cold(-28), 0.3, places=4)
        self.assertAlmostEqual(cold(-40), 0.6, places=4)
        self.assertAlmostEqual(cold(-48), 0.8, places=4)
        self.assertAlmostEqual(cold(-55), 1.0, places=4)

    def test_the_interior_is_linear(self):
        self.assertAlmostEqual(cold(-19), 0.15, places=4)  # -10 .. -28
        self.assertAlmostEqual(cold(-34), 0.45, places=4)  # -28 .. -40
        self.assertAlmostEqual(cold(-44), 0.7, places=4)  # -40 .. -48
        self.assertAlmostEqual(cold(-51.5), 0.9, places=4)  # -48 .. -55

    def test_below_the_extreme_band_saturates(self):
        self.assertAlmostEqual(cold(-70), 1.0, places=4)

    def test_colder_never_lowers_the_risk(self):
        xs = [x * 0.5 for x in range(-140, 41)]
        vals = [cold(x) for x in xs]
        for a, b in zip(vals, vals[1:]):
            self.assertGreaterEqual(a, b - 1e-9)


class TestHeatStressBands(unittest.TestCase):
    """TB MED 507 / ISO 7243 WBGT anchors: 29 = 0.3, 34 = 0.6, 38 = 0.8,
    and 0 at the top of the safe category (18 C)."""

    def test_no_risk_at_or_below_the_safe_category(self):
        for wbgt in (0, 10, 18):
            with self.subTest(wbgt=wbgt):
                self.assertAlmostEqual(heat(wbgt), 0.0, places=4)

    def test_the_anchors(self):
        self.assertAlmostEqual(heat(29), 0.3, places=4)
        self.assertAlmostEqual(heat(34), 0.6, places=4)
        self.assertAlmostEqual(heat(38), 0.8, places=4)

    def test_the_interior_is_linear(self):
        self.assertAlmostEqual(heat(23.5), 0.15, places=4)  # 18 .. 29
        self.assertAlmostEqual(heat(31.5), 0.45, places=4)  # 29 .. 34
        self.assertAlmostEqual(heat(36), 0.7, places=4)  # 34 .. 38

    def test_the_unsourced_upper_anchor_is_45(self):
        # The issue gives no WBGT for full pressure, so 45 C is the bounded
        # clamp (UNSOURCED, named in the kernel docstring).
        self.assertAlmostEqual(heat(45), 1.0, places=4)
        self.assertAlmostEqual(heat(60), 1.0, places=4)

    def test_hotter_never_lowers_the_risk(self):
        xs = [x * 0.5 for x in range(-20, 121)]
        vals = [heat(x) for x in xs]
        for a, b in zip(vals, vals[1:]):
            self.assertLessEqual(a, b + 1e-9)


class TestSurvivalPressure(unittest.TestCase):
    """survivalPressure = max of the five hazards, clamped 0..1."""

    def test_returns_the_strongest_hazard(self):
        self.assertAlmostEqual(pressure(0.1, 0.2, 0.9, 0.3, 0.0), 0.9, places=4)
        self.assertAlmostEqual(pressure(0.4, 0.8, 0.1, 0.2, 0.0), 0.8, places=4)

    def test_all_zero_is_zero(self):
        self.assertAlmostEqual(pressure(0, 0, 0, 0, 0), 0.0, places=4)

    def test_a_single_hazard_dominates(self):
        self.assertAlmostEqual(pressure(0, 0, 0, 0, 0.7), 0.7, places=4)

    def test_out_of_range_inputs_clamp(self):
        self.assertAlmostEqual(pressure(2.0, 0, 0, 0, 0), 1.0, places=4)
        self.assertAlmostEqual(pressure(-1, -1, -1, -1, -1), 0.0, places=4)


class TestSurvivalActionBands(unittest.TestCase):
    """Action bands: 0 normal, 1 cover, 2 break contact, 3 survival.  The
    lower edge of a band is inclusive."""

    def test_normal_band(self):
        for p in (0.0, 0.15, 0.29):
            with self.subTest(p=p):
                self.assertEqual(action(p), 0)

    def test_cover_band(self):
        for p in (0.3, 0.45, 0.59):
            with self.subTest(p=p):
                self.assertEqual(action(p), 1)

    def test_break_contact_band(self):
        for p in (0.6, 0.7, 0.79):
            with self.subTest(p=p):
                self.assertEqual(action(p), 2)

    def test_survival_band(self):
        for p in (0.8, 0.9, 1.0):
            with self.subTest(p=p):
                self.assertEqual(action(p), 3)

    def test_out_of_range_pressure_clamps(self):
        self.assertEqual(action(1.5), 3)
        self.assertEqual(action(-0.5), 0)


class TestBehaviourIntegration(unittest.TestCase):
    """The issue's behaviour test at the kernel level: cold + wind drives
    the survival route, and heat drives a survival action."""

    def test_cold_wind_drives_the_survival_route(self):
        # Wind chill -55 C is full cold stress; with no other hazard the
        # survival pressure is 1.0 and the action is 3 (route to survival).
        p = pressure(0, 0, cold(-55), 0, 0)
        self.assertAlmostEqual(p, 1.0, places=4)
        self.assertEqual(action(p), 3)

    def test_heat_drives_a_survival_action(self):
        # WBGT 45 C is full heat stress.
        p = pressure(0, 0, 0, heat(45), 0)
        self.assertAlmostEqual(p, 1.0, places=4)
        self.assertEqual(action(p), 3)

    def test_a_mild_hazard_keeps_normal_behaviour(self):
        # Wind chill -20 C is a mild cold stress, under the 0.3 cover edge.
        p = pressure(0, 0, cold(-20), 0, 0)
        self.assertLess(p, 0.3)
        self.assertEqual(action(p), 0)


class TestSourceContracts(unittest.TestCase):
    """The engine wiring the harness cannot execute."""

    def test_state_reads_the_five_published_hazards(self):
        text = STATE.read_text(encoding="utf-8")
        for ref in (
            "QEGVAR(strain,dehydrationRisk)",
            "QEGVAR(core,currentHypoxiaRisk)",
            "QEGVAR(core,windChillTemp)",
            "QEGVAR(core,currentWBGT)",
            "QGVAR(fatigueFactor)",
        ):
            self.assertIn(ref, text, f"fnc_survivalState does not read {ref}")

    def test_state_calls_the_three_kernels_and_publishes(self):
        text = STATE.read_text(encoding="utf-8")
        self.assertIn("FUNC(coldStress)", text)
        self.assertIn("FUNC(heatStress)", text)
        self.assertIn("FUNC(survivalPressure)", text)
        self.assertIn("setVariable [QGVAR(survivalPressure)", text)

    def test_state_gates_on_physiology_enabled(self):
        text = STATE.read_text(encoding="utf-8")
        self.assertIn("QEGVAR(core,physiologyEnabled)", text)

    def test_physiology_preps_the_four_functions(self):
        text = (ROOT / "addons" / "physiology" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        for prep in (
            "PREPS(state,coldStress)",
            "PREPS(state,heatStress)",
            "PREPS(state,survivalPressure)",
            "PREPS(state,survivalState)",
        ):
            self.assertIn(prep, text)

    def test_physiology_ticks_the_state_once_a_second(self):
        text = (ROOT / "addons" / "physiology" / "XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("[FUNC(survivalState), 1] call CBA_fnc_addPerFrameHandler", text)

    def test_ai_preps_the_behaviour_functions(self):
        text = (ROOT / "addons" / "ai" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(survivalAction)", text)
        self.assertIn("PREP(survivalNeed)", text)

    def test_ai_tick_honours_the_survival_flag(self):
        text = (AI / "fnc_aiTick.sqf").read_text(encoding="utf-8")
        self.assertIn("QGVAR(survivalDriven)", text)
        self.assertIn("FUNC(survivalNeed)", text)

    def test_need_bridge_reads_the_pressure_and_writes_the_need(self):
        text = NEED.read_text(encoding="utf-8")
        self.assertIn("QEGVAR(physiology,survivalPressure)", text)
        self.assertIn("setVariable [QGVAR(need)", text)

    def test_ai_declares_the_physiology_dependency(self):
        text = (ROOT / "addons" / "ai" / "config.cpp").read_text(encoding="utf-8")
        self.assertIn('"aee_physiology"', text)


if __name__ == "__main__":
    unittest.main()
