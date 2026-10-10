#!/usr/bin/env python3
"""Native engine-AI hearing tests (issue #74).

Executes the real SQF range kernel through tools/tests/sqf_lite.py, so a
failure is a source failure, not a mirror drift.  The source-contract methods
read the engine wiring the harness cannot execute: the propagation-index read,
the reveal injection and the CBA gate.

Run: python3 -m unittest tools.tests.test_ai_hearing -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "addons" / "ai"
FUNCS = AI / "functions"

HEARING_RANGE = FUNCS / "fnc_hearingRange.sqf"
REVEAL = FUNCS / "fnc_revealSound.sqf"
INIT_HEARING = FUNCS / "fnc_initHearing.sqf"


def hearing_range(base_range, index):
    return run_sqf(HEARING_RANGE, [base_range, index])


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


if __name__ == "__main__":
    unittest.main()
