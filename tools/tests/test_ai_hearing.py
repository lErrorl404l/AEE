#!/usr/bin/env python3
"""Native engine-AI hearing tests (issue #74).

Executes the real SQF range kernel through tools/tests/sqf_lite.py, so a
failure is a source failure, not a mirror drift.  The source-contract methods
read the engine wiring the harness cannot execute: the propagation-index read,
the reveal injection and the CBA gate.

Run: python3 -m unittest tools.tests.test_ai_hearing -v
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "addons" / "ai"
FUNCS = AI / "functions"

HEARING_RANGE = FUNCS / "fnc_hearingRange.sqf"
HEARING_SCAN_DUE = FUNCS / "fnc_hearingScanDue.sqf"
REVEAL = FUNCS / "fnc_revealSound.sqf"
INIT_HEARING = FUNCS / "fnc_initHearing.sqf"
COMPONENT_HEADER = AI / "script_component.hpp"
ENGINE_COMMANDS_DOC = ROOT / "docs" / "engine" / "engine-commands-and-features.md"


def hearing_range(base_range, index):
    return run_sqf(HEARING_RANGE, [base_range, index])


def hearing_scan_due(now, last_scan, rate):
    return run_sqf(HEARING_SCAN_DUE, [now, last_scan, rate])


def header_define(name):
    """The numeric value of a #define in the ai component header."""
    match = re.search(
        rf"^#define\s+{name}\s+([0-9]+(?:\.[0-9]+)?)",
        COMPONENT_HEADER.read_text(encoding="utf-8"),
        re.M,
    )
    if not match:
        raise AssertionError(f"{name} is not defined in {COMPONENT_HEADER.name}")
    return float(match.group(1))


def sqf_code(path):
    """The .sqf with its comments removed, so a contract tests code only."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestHearingRange(unittest.TestCase):
    """The kernel scales the baseline range by AEE's propagation index."""

    def test_baseline_index_keeps_the_range(self):
        self.assertAlmostEqual(hearing_range(400, 1.0), 400.0)

    def test_a_favourable_index_extends_the_range(self):
        self.assertAlmostEqual(hearing_range(400, 2.0), 800.0)

    def test_a_poor_index_shortens_the_range(self):
        self.assertAlmostEqual(hearing_range(400, 0.3), 120.0)

    def test_the_index_clamps_to_the_published_band(self):
        self.assertAlmostEqual(hearing_range(400, 5.0), 800.0)
        self.assertAlmostEqual(hearing_range(400, 0.1), 120.0)

    def test_a_negative_baseline_is_zero(self):
        self.assertAlmostEqual(hearing_range(-5, 1.0), 0.0)

    def test_a_mid_index_interpolates(self):
        self.assertAlmostEqual(hearing_range(400, 1.5), 600.0)


class TestHearingSourceContracts(unittest.TestCase):
    """The engine wiring the harness cannot execute."""

    def test_reveal_reads_the_aee_propagation_index(self):
        text = REVEAL.read_text(encoding="utf-8")
        self.assertIn("currentSoundPropagation", text)
        self.assertIn("EGVAR(weather", text)

    def test_reveal_injects_with_reveal_not_a_hearing_scale(self):
        text = REVEAL.read_text(encoding="utf-8")
        self.assertIn("reveal [", text)
        # The engine hearing is not scaled directly: no config write and no
        # audibleFire assignment, only the reveal injection.
        self.assertNotIn("audibleFire =", text)
        self.assertNotIn("setVariable", text)

    def test_init_installs_the_fired_handler_on_every_man(self):
        text = INIT_HEARING.read_text(encoding="utf-8")
        self.assertIn("isServer", text)
        self.assertIn("installObjectEngineHandler", text)
        self.assertIn('"CAManBase", "Fired"', text)
        # Fired is unit-local, so a client-owned player raises it on the client
        # and the server-side class handler never sees it (issue #239).
        self.assertIn("installPlayerEngineHandler", text)
        self.assertIn('["Fired",', text)

    def test_the_client_reveal_runs_on_the_ai_machine(self):
        """The reveal only updates knowledge where it runs (issue #239)."""
        text = INIT_HEARING.read_text(encoding="utf-8")
        self.assertIn("remoteExecCall [QFUNC(revealSound), 2]", text)

    def test_the_host_does_not_reveal_one_shot_twice(self):
        """The class handler already covers the host's own player (issue #239)."""
        text = INIT_HEARING.read_text(encoding="utf-8")
        self.assertRegex(text, r"hasInterface\s*&&\s*\{\s*!isServer\s*\}")

    def test_the_setting_gates_the_handler(self):
        text = INIT_HEARING.read_text(encoding="utf-8")
        self.assertIn("nativeHearing", text)
        settings = (AI / "initSettings.inc.sqf").read_text(encoding="utf-8")
        self.assertIn("AEE_SETTING_CHECKBOX(nativeHearing", settings)
        self.assertIn("false)", settings)

    def test_post_init_starts_the_hearing_layer(self):
        text = (AI / "XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn("initHearing", text)

    def test_config_declares_the_weather_dependency(self):
        text = (AI / "config.cpp").read_text(encoding="utf-8")
        self.assertIn('"aee_weather"', text)

    def test_no_compat_addon_and_no_third_party_ai_mods(self):
        for path in AI.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for token in ("compat_", "lambs", "vcom"):
                self.assertNotIn(token, text, f"{path.name} references {token}")


class TestHearingScanRateLimit(unittest.TestCase):
    """Issue #272: the per-shot full-radius scan is rate limited."""

    def test_the_first_scan_is_due(self):
        self.assertTrue(hearing_scan_due(10.0, -1e9, 4))

    def test_a_shot_inside_the_window_is_not_due(self):
        self.assertFalse(hearing_scan_due(10.1, 10.0, 4))

    def test_a_shot_at_the_window_edge_is_due(self):
        self.assertTrue(hearing_scan_due(10.25, 10.0, 4))

    def test_the_window_is_the_reciprocal_of_the_rate(self):
        self.assertTrue(hearing_scan_due(10.5, 10.0, 2))
        self.assertFalse(hearing_scan_due(10.49, 10.0, 2))

    def test_a_zero_rate_never_scans_and_does_not_divide_by_zero(self):
        self.assertFalse(hearing_scan_due(11.0, 10.0, 0))


class TestHearingScanContracts(unittest.TestCase):
    """The throttle wiring the harness cannot execute."""

    def test_reveal_passes_the_policy_scan_rate_to_the_kernel(self):
        text = REVEAL.read_text(encoding="utf-8")
        self.assertIn("FUNC(hearingScanDue)", text)
        self.assertIn("AI_HEARING_SCAN_RATE", text)

    def test_the_throttle_state_is_kept_by_the_machine_that_scans(self):
        text = REVEAL.read_text(encoding="utf-8")
        self.assertIn("lastSoundScan", text)

    def test_the_scan_rate_is_a_named_positive_constant(self):
        self.assertGreater(header_define("AI_HEARING_SCAN_RATE"), 0)

    def test_the_scan_kernel_is_prepared(self):
        prep = (AI / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(hearingScanDue);", prep)

    def test_the_scan_kernel_is_pure(self):
        text = sqf_code(HEARING_SCAN_DUE)
        for token in ("missionNamespace", "getVariable", "GVAR", "EGVAR"):
            self.assertNotIn(token, text, f"the kernel reaches {token}")


class TestHearingForgettingContract(unittest.TestCase):
    """Issue #271: AEE relies on the engine's own knowledge reset."""

    def test_reveal_does_not_call_forget_target(self):
        """forgetTarget resets the whole group's information about a target.

        It would erase the engine's own contact, including a visual one, so the
        decision is to leave the forgetting to the engine.
        """
        self.assertNotIn("forgetTarget", sqf_code(REVEAL))

    def test_the_decision_records_the_engine_reset_it_relies_on(self):
        text = REVEAL.read_text(encoding="utf-8")
        self.assertIn("knowsAbout", text)
        self.assertIn("120", text)

    def test_the_engine_reference_still_records_that_reset(self):
        """The reliance is sound only while the sourced claim holds."""
        doc = ENGINE_COMMANDS_DOC.read_text(encoding="utf-8")
        self.assertIn("120 s without sight", doc)
        self.assertRegex(doc, r"resets\s+to zero")

    def test_the_injected_knowledge_stays_below_side_identification(self):
        """The band tells the AI a shot happened, never which side fired."""
        self.assertLess(header_define("AI_HEARING_REVEAL_MAX"), 1.5)


if __name__ == "__main__":
    unittest.main()
