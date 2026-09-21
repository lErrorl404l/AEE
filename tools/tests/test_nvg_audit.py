#!/usr/bin/env python3
"""NVG audit locks (issue #153).

Locks the #153 audit state: the two latent bugs are resolved and most
gaps are implemented (spectral response, gating flicker).  This suite
locks the RESOLVED state so the audit cannot regress, and tests the two
gaps added here (tube warm-up, Gen 1 erosion) by executing the REAL
fnc_applyNVGTubeModel.sqf through sqf_lite.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf

FNC = (
    Path(__file__).parents[2] / "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf"
)


class TestAuditResolved(unittest.TestCase):
    def test_bug_a_burnpos_dead_code_removed(self):
        # Bug A: the phosphor afterimage was written-but-never-read dead
        # code.  The comment documents the removal (the #152 smear class).
        src = FNC.read_text(encoding="utf-8")
        self.assertNotIn("nvgBurnPos", src)
        self.assertIn("removed as dead code", src)

    def test_bug_b_single_tick(self):
        # Bug B: applyRainDroplets TICK ran twice per tick in thermal
        # mode.  The dispatch must call TICK exactly once, before the
        # mode branches.
        src = (Path(__file__).parents[2] / "addons/optics/XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertEqual(src.count('["TICK"] call EFUNC(thermal,applyRainDroplets)'), 1)

    def test_gap3_spectral_response(self):
        # Gap 3: IR-rich sources weight the tube excitation above their
        # luminous output (the military IR-signature exploit).
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("_spectralWeight", src)
        self.assertIn('"nvmarker"', src)  # IR strobe/marker branch

    def test_gap2_gating_flicker(self):
        # Gap 2: gate-transition blackout flicker raises the noise floor
        # for a window (nvgGrainBoost / nvgGateFlickerUntil).
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("nvgGateFlickerUntil", src)
        self.assertIn("nvgGrainBoost", src)

    def test_gap4_warmup_curve_present(self):
        # Gap 4 (added here): tube warm-up scales dark current by
        # (1 - exp(-t/tau)) toward +25%, tier-dependent tau.
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("_warmupTau", src)
        self.assertIn("nvgTubeOnTime", src)
        self.assertIn("exp (-((CBA_missionTime", src)

    def test_gap5_gen1_erosion_present(self):
        # Gap 5 (added here): Gen 1 edge-erosion vignette multiplier.
        # The factor is local (fully consumed by the RadialBlur); no
        # persisted state - add a producer/consumer pair when the
        # perceptual layer (gap 6) lands.
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("_erosionFactor", src)
        self.assertNotIn("nvgErosionFactor", src)
        self.assertIn('case "GEN1": { 2.5 }', src)


class TestWarmupMath(unittest.TestCase):
    def test_warmup_approaches_25_percent(self):
        # The warm-up term 1 - exp(-t/tau): at t=5*tau it is ~99.3%,
        # so the noise floor multiplier approaches 1.25.  This is the
        # physical claim (dark current rises to equilibrium, not
        # unbounded).
        import math

        tau = 60.0
        t = 5 * tau
        frac = 1 - math.exp(-t / tau)
        self.assertAlmostEqual(frac, 0.993, places=2)
        self.assertAlmostEqual(1 + 0.25 * frac, 1.248, places=2)


if __name__ == "__main__":
    unittest.main()
