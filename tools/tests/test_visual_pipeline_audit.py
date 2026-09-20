#!/usr/bin/env python3
"""Triple audit of every visual effect (issue #204).

Visual code is the most fragile layer - a wrong sign, a swapped
channel, a clipped value renders as a subtle (or blinding) error the
user only sees in game.  Every post-processing effect, the thermal
display, the sensor chain, and the fusion overlay get THREE checks:

 1. SQF-parameter audit: the actual values in the SQF source are
    parsed and checked against sane ranges (no negative tints, no
    inverted channels, priorities unique).
 2. Simulation: the modelled pipeline (radiance -> AGC -> heat colour
    -> CC -> inversion) is run and the output asserted against the
    physics (hot bright in WHOT, dark in BHOT).
 3. Regression locks: the invariants that have already broken once
    (the negative CC matrix, the un-neutralised inversion) are locked
    so they cannot regress.

The regression this guards: the CC tint [3.84,-0.46,-2.72,-0.06] had
NEGATIVE green/blue channels, which INVERTED the scene - the hot
barrel rendered black in WHOT and the display flipped with polarity
(the in-game 'barrel is still black' / 'screen is blinding white in
BHOT' report).
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
from simulate_visual_pipeline import (  # noqa: E402
    agc_map,
    colour_correction,
    heat_colour,
    invert,
    planck_band_radiance,
)

REPO = Path(__file__).resolve().parents[2]
SQF = (
    REPO / "addons" / "thermal" / "functions" / "display" / "fnc_applyThermalVision.sqf"
)

CC_NEUTRAL = {
    "brightness": 1.16,
    "contrast": 0.62,
    "offset": 0.0,
    "black": [0, 0, 0, 0],
    "white": [1, 1, 1, 0],
    "tint": [0.33, 0.33, 0.33, 0],
    "blend": [0, 0, 0, 0, 0, 0, 4.0],
}


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


class TestVisualPipelineTripleAudit(unittest.TestCase):
    # ─── 1. SQF-parameter audit ──────────────────────────────────────────
    def test_sqf_cc_uses_neutral_tint(self):
        text = SQF.read_text(encoding="utf-8")
        self.assertIn("[0.33, 0.33, 0.33, 0]", text)
        self.assertIn("[0, 0, 0, 0, 0, 0, 4]", text)

    def test_sqf_cc_no_negative_channels(self):
        text = SQF.read_text(encoding="utf-8")
        # No tint array with a negative channel anywhere in the file.
        for m in re.finditer(r"\[([-\d.,\s]+)\]", text):
            nums = [float(x) for x in m.group(1).split(",") if x.strip()]
            if len(nums) >= 4 and any(n < 0 for n in nums[:4]):
                self.fail(f"negative tint channel in {m.group(0)}")

    def test_sqf_inversion_neutralises_before_disable(self):
        text = SQF.read_text(encoding="utf-8")
        self.assertIn("_hInv ppEffectAdjust [0, 0, 0]", text)
        self.assertIn("_hInv ppEffectEnable false", text)
        # The neutral adjust must come BEFORE the disable.
        adj = text.index("_hInv ppEffectAdjust [0, 0, 0]")
        dis = text.index("_hInv ppEffectEnable false")
        self.assertLess(adj, dis)

    def test_sqf_priorities_unique(self):
        text = SQF.read_text(encoding="utf-8")
        # The ppEffect create list: ["EffectType", priority, QGVAR(...)]
        prios = [
            int(m.group(2))
            for m in re.finditer(r'\[\s*"([A-Za-z]+)"\s*,\s*(\d+)\s*,', text)
        ]
        self.assertGreaterEqual(len(prios), 5)  # vig/blur/grain/CC/inv
        seen = set()
        for p in prios:
            self.assertNotIn(p, seen, f"duplicate priority {p}")
            seen.add(p)

    # ─── 2. Simulation assertions ────────────────────────────────────────
    def test_sim_hot_bright_whot(self):
        tex = heat_colour(0.95)
        whot = colour_correction(tex, CC_NEUTRAL)
        self.assertGreater(lum(whot), 0.5)

    def test_sim_hot_dark_bhot(self):
        tex = heat_colour(0.95)
        bhot = invert(colour_correction(tex, CC_NEUTRAL))
        self.assertLess(lum(bhot), 0.5)

    def test_sim_cold_dark_whot(self):
        tex = heat_colour(0.05)
        whot = colour_correction(tex, CC_NEUTRAL)
        self.assertLess(lum(whot), 0.5)

    def test_sim_sensor_monotonic(self):
        # Radiance must increase with temperature (the Planck curve).
        r1 = planck_band_radiance(5, 0.92)
        r2 = planck_band_radiance(120, 0.92)
        self.assertGreater(r2, r1)
        # AGC must map the hottest scene object to near-full brightness.
        rads = [planck_band_radiance(t, 0.92) for t in (5, 32, 120)]
        b_hot = agc_map(max(rads), min(rads), max(rads))
        b_cold = agc_map(min(rads), min(rads), max(rads))
        self.assertGreater(b_hot, 0.9)
        self.assertLess(b_cold, 0.1)

    def test_sim_cc_output_not_clipped(self):
        # The neutral CC must not clip to pure white/black for the scene.
        for t in (5, 32, 120):
            rad = planck_band_radiance(t, 0.92)
            b = agc_map(
                rad, planck_band_radiance(5, 0.92), planck_band_radiance(120, 0.92)
            )
            whot = colour_correction(heat_colour(b), CC_NEUTRAL)
            l = lum(whot)
            self.assertGreater(l, 0.1)
            self.assertLess(l, 0.95)

    # ─── 3. Regression locks ─────────────────────────────────────────────
    def test_regression_negative_matrix_gone(self):
        # The negative tint must not appear as an ACTIVE CC value.  The
        # explanatory comment may reference it (documentation), so check
        # the adjust block specifically has no negative channels.
        text = SQF.read_text(encoding="utf-8")
        # Find the ppEffectAdjust call and verify no negative tint.
        adj_block = text[text.index("_hCC ppEffectAdjust") :]
        adj_block = adj_block[: adj_block.index("_hCC ppEffectCommit")]
        self.assertIn("[0.33, 0.33, 0.33, 0]", adj_block)
        self.assertNotIn("-0.46", adj_block)
        self.assertNotIn("-2.72", adj_block)

    def test_regression_display_sim_gated(self):
        # The simulator must be wired into the test suite.
        run_tests = (REPO / "tools" / "run_tests.py").read_text(encoding="utf-8")
        self.assertIn("test_visual_pipeline_audit", run_tests)


if __name__ == "__main__":
    unittest.main()
